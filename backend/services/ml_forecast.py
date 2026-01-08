"""
ML-based Forecast Service for GrantRadar
Uses Prophet for time-series forecasting of grant deadlines.
"""
import logging
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Optional

import pandas as pd
from prophet import Prophet
from sqlalchemy import and_, extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import Grant
from backend.services.forecast import (
    calculate_confidence,
    calculate_recurrence_pattern,
    predict_next_opening,
)

logger = logging.getLogger(__name__)


@dataclass
class MLPredictionResult:
    """Result of an ML-based deadline prediction."""

    predicted_date: date
    confidence: float
    method: str  # 'ml' or 'rule_based'
    uncertainty_days: int  # +/- days
    lower_bound: Optional[date] = None
    upper_bound: Optional[date] = None


class GrantDeadlinePredictor:
    """ML-based grant deadline prediction using Prophet."""

    def __init__(self, min_data_points: int = 4):
        """
        Initialize predictor.

        Args:
            min_data_points: Minimum number of historical deadlines required
                           for training a Prophet model.
        """
        self.min_data_points = min_data_points
        # In-memory cache for trained models: {funder_name: (model, last_trained)}
        self._model_cache: dict[str, tuple[Prophet, datetime]] = {}
        # Cache expiry time (retrain after this duration)
        self._cache_expiry_hours = 24

    def _is_model_stale(self, funder_name: str) -> bool:
        """Check if the cached model is stale and needs retraining."""
        if funder_name not in self._model_cache:
            return True
        _, last_trained = self._model_cache[funder_name]
        expiry_time = last_trained + timedelta(hours=self._cache_expiry_hours)
        return datetime.utcnow() > expiry_time

    async def _get_funder_deadlines(
        self,
        db: AsyncSession,
        funder_name: str,
        years_lookback: int = 5,
    ) -> list[date]:
        """
        Fetch historical deadline dates for a specific funder.

        Args:
            db: Database session
            funder_name: Name of the funding agency
            years_lookback: How many years of historical data to fetch

        Returns:
            List of deadline dates sorted chronologically
        """
        cutoff_date = datetime.now() - timedelta(days=years_lookback * 365)

        query = (
            select(Grant.deadline)
            .where(
                and_(
                    Grant.agency == funder_name,
                    Grant.deadline.isnot(None),
                    Grant.created_at >= cutoff_date,
                )
            )
            .order_by(Grant.deadline.asc())
        )

        result = await db.execute(query)
        rows = result.all()

        # Extract dates, filtering out None values
        deadlines = []
        for row in rows:
            if row.deadline:
                deadline_date = (
                    row.deadline.date()
                    if isinstance(row.deadline, datetime)
                    else row.deadline
                )
                deadlines.append(deadline_date)

        return deadlines

    def _prepare_prophet_data(self, deadlines: list[date]) -> pd.DataFrame:
        """
        Prepare data for Prophet training.

        Prophet expects a DataFrame with columns:
        - 'ds': datetime column
        - 'y': value to predict

        For deadline prediction, we use day-of-year (1-365) as 'y'
        to capture annual seasonality patterns.

        Args:
            deadlines: List of historical deadline dates

        Returns:
            DataFrame formatted for Prophet
        """
        data = []
        for deadline in deadlines:
            data.append({
                'ds': pd.Timestamp(deadline),
                'y': deadline.timetuple().tm_yday,  # Day of year (1-365)
            })

        df = pd.DataFrame(data)
        return df

    def _create_prophet_model(self) -> Prophet:
        """
        Create and configure a Prophet model for deadline prediction.

        Returns:
            Configured Prophet model instance
        """
        model = Prophet(
            yearly_seasonality=True,
            weekly_seasonality=False,  # Grant deadlines don't follow weekly patterns
            daily_seasonality=False,
            interval_width=0.80,  # 80% confidence interval
            changepoint_prior_scale=0.05,  # Conservative changepoint detection
        )
        return model

    async def train_funder_model(
        self,
        db: AsyncSession,
        funder_name: str,
        force_retrain: bool = False,
    ) -> bool:
        """
        Train a Prophet model for a specific funder using their historical deadlines.

        Args:
            db: Database session
            funder_name: Name of the funding agency
            force_retrain: Force retraining even if cached model exists

        Returns:
            True if model was successfully trained, False if insufficient data
        """
        # Check cache first
        if not force_retrain and not self._is_model_stale(funder_name):
            logger.debug(f"Using cached model for funder: {funder_name}")
            return True

        # Fetch historical deadlines
        deadlines = await self._get_funder_deadlines(db, funder_name)

        if len(deadlines) < self.min_data_points:
            logger.warning(
                f"Insufficient data for funder '{funder_name}': "
                f"got {len(deadlines)}, need {self.min_data_points}"
            )
            return False

        # Prepare data and train model
        try:
            df = self._prepare_prophet_data(deadlines)
            model = self._create_prophet_model()

            # Suppress Prophet's verbose logging
            model.fit(df)

            # Cache the trained model
            self._model_cache[funder_name] = (model, datetime.utcnow())

            logger.info(
                f"Successfully trained model for funder '{funder_name}' "
                f"with {len(deadlines)} data points"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to train model for funder '{funder_name}': {e}")
            return False

    def predict_next_deadline(
        self,
        funder_name: str,
        periods_ahead: int = 1,
    ) -> tuple[date, float, tuple[date, date]]:
        """
        Predict next deadline for a funder using the trained Prophet model.

        Args:
            funder_name: Name of the funding agency
            periods_ahead: Number of periods (years) to forecast ahead

        Returns:
            Tuple of (predicted_date, confidence, (lower_bound, upper_bound))
            The bounds represent the uncertainty interval.

        Raises:
            ValueError: If no trained model exists for this funder
        """
        if funder_name not in self._model_cache:
            raise ValueError(
                f"No trained model for funder '{funder_name}'. "
                "Call train_funder_model first."
            )

        model, _ = self._model_cache[funder_name]

        # Create future dataframe for prediction
        # We predict for the next year(s) to find the next deadline
        today = date.today()
        future_dates = pd.date_range(
            start=today,
            periods=365 * periods_ahead,
            freq='D',
        )
        future_df = pd.DataFrame({'ds': future_dates})

        # Make predictions
        forecast = model.predict(future_df)

        # Find the predicted deadline (day with highest 'yhat' that represents
        # the typical deadline pattern)
        # We're looking for dates where the predicted day-of-year matches
        # the historical pattern

        # Get the most likely day-of-year based on predictions
        forecast['predicted_day_of_year'] = forecast['yhat'].round().astype(int).clip(1, 365)
        forecast['match_score'] = abs(
            forecast['ds'].dt.dayofyear - forecast['predicted_day_of_year']
        )

        # Find future dates where the actual day matches the predicted pattern
        # (match_score close to 0 means the date aligns with historical patterns)
        forecast['is_match'] = forecast['match_score'] <= 15  # Within 15 days tolerance

        matches = forecast[forecast['is_match']]

        if len(matches) == 0:
            # Fallback: find the date closest to the mean predicted day
            mean_day = int(forecast['yhat'].mean())
            for idx, row in forecast.iterrows():
                if row['ds'].dayofyear == mean_day and row['ds'].date() > today:
                    best_match = row
                    break
            else:
                # Last resort: use first future date
                best_match = forecast.iloc[0]
        else:
            # Use the first matching date
            best_match = matches.iloc[0]

        predicted_date = best_match['ds'].date()

        # Calculate confidence based on prediction uncertainty
        yhat_lower = best_match['yhat_lower']
        yhat_upper = best_match['yhat_upper']
        uncertainty_range = yhat_upper - yhat_lower

        # Convert uncertainty to confidence (lower uncertainty = higher confidence)
        # Scale: 0-30 days uncertainty -> 0.9-0.7 confidence
        max_uncertainty = 90  # days
        normalized_uncertainty = min(uncertainty_range / 2, max_uncertainty) / max_uncertainty
        confidence = round(0.9 - (0.2 * normalized_uncertainty), 2)
        confidence = max(0.5, min(confidence, 0.95))

        # Calculate date bounds based on uncertainty interval
        days_lower = int((yhat_lower - best_match['yhat']) / 2)
        days_upper = int((yhat_upper - best_match['yhat']) / 2)

        lower_bound = predicted_date + timedelta(days=days_lower)
        upper_bound = predicted_date + timedelta(days=days_upper)

        return predicted_date, confidence, (lower_bound, upper_bound)

    async def get_prediction_with_fallback(
        self,
        db: AsyncSession,
        funder_name: str,
    ) -> dict:
        """
        Try ML prediction first, fall back to rule-based if insufficient data.

        Args:
            db: Database session
            funder_name: Name of the funding agency

        Returns:
            Dictionary with prediction details:
            {
                'predicted_date': date,
                'confidence': float,
                'method': 'ml' | 'rule_based',
                'uncertainty_days': int,  # +/- days
                'lower_bound': date | None,
                'upper_bound': date | None,
            }
        """
        # Try to train/use ML model
        model_trained = await self.train_funder_model(db, funder_name)

        if model_trained:
            try:
                predicted_date, confidence, (lower_bound, upper_bound) = (
                    self.predict_next_deadline(funder_name)
                )

                uncertainty_days = (upper_bound - predicted_date).days

                return {
                    'predicted_date': predicted_date,
                    'confidence': confidence,
                    'method': 'ml',
                    'uncertainty_days': abs(uncertainty_days),
                    'lower_bound': lower_bound,
                    'upper_bound': upper_bound,
                }
            except Exception as e:
                logger.warning(
                    f"ML prediction failed for '{funder_name}', "
                    f"falling back to rule-based: {e}"
                )

        # Fallback to rule-based prediction
        return await self._get_rule_based_prediction(db, funder_name)

    async def _get_rule_based_prediction(
        self,
        db: AsyncSession,
        funder_name: str,
    ) -> dict:
        """
        Get rule-based prediction for funders with insufficient data.

        This uses the existing forecast.py logic as a fallback.

        Args:
            db: Database session
            funder_name: Name of the funding agency

        Returns:
            Dictionary with prediction details
        """
        # Fetch whatever historical data we have
        deadlines = await self._get_funder_deadlines(db, funder_name)

        if not deadlines:
            # No data at all - return generic prediction
            future_date = date.today() + timedelta(days=90)
            return {
                'predicted_date': future_date,
                'confidence': 0.3,
                'method': 'rule_based',
                'uncertainty_days': 60,
                'lower_bound': None,
                'upper_bound': None,
            }

        # Extract months from deadlines for pattern analysis
        typical_months = [d.month for d in deadlines]
        last_deadline = max(deadlines)

        # Use existing rule-based prediction (updated signature with historical_dates)
        predicted_date, deadline_month, day_confidence = predict_next_opening(
            typical_months=typical_months,
            historical_dates=deadlines,
            last_deadline=last_deadline,
            lookahead_months=12,
        )

        # Calculate confidence based on data quality
        unique_months = set(typical_months)
        consistency = len(unique_months) / max(len(typical_months), 1)
        years_span = (max(deadlines).year - min(deadlines).year) + 1 if len(deadlines) > 1 else 1

        confidence = calculate_confidence(
            grant_count=len(deadlines),
            years_span=years_span,
            consistency=1 - consistency,
        )

        # Calculate uncertainty based on data quality
        if len(deadlines) >= 3:
            uncertainty_days = 30
        elif len(deadlines) >= 2:
            uncertainty_days = 45
        else:
            uncertainty_days = 60

        return {
            'predicted_date': predicted_date,
            'confidence': confidence,
            'method': 'rule_based',
            'uncertainty_days': uncertainty_days,
            'lower_bound': None,
            'upper_bound': None,
        }

    async def batch_predict(
        self,
        db: AsyncSession,
        funder_names: list[str],
    ) -> dict[str, dict]:
        """
        Predict deadlines for multiple funders.

        Args:
            db: Database session
            funder_names: List of funder names to predict for

        Returns:
            Dictionary mapping funder names to prediction results
        """
        results = {}
        for funder_name in funder_names:
            results[funder_name] = await self.get_prediction_with_fallback(
                db, funder_name
            )
        return results

    async def get_all_funder_predictions(
        self,
        db: AsyncSession,
        min_grants: int = 2,
        lookahead_months: int = 12,
    ) -> list[dict]:
        """
        Get predictions for all funders with sufficient historical data.

        Args:
            db: Database session
            min_grants: Minimum number of grants to consider a funder
            lookahead_months: How far ahead to predict

        Returns:
            List of prediction dictionaries with funder information
        """
        # Get all funders with enough historical data
        query = (
            select(
                Grant.agency,
                func.count(Grant.id).label('grant_count'),
                func.max(Grant.deadline).label('last_deadline'),
            )
            .where(
                and_(
                    Grant.agency.isnot(None),
                    Grant.deadline.isnot(None),
                )
            )
            .group_by(Grant.agency)
            .having(func.count(Grant.id) >= min_grants)
        )

        result = await db.execute(query)
        rows = result.all()

        predictions = []
        today = date.today()
        cutoff_date = today + timedelta(days=lookahead_months * 30)

        for row in rows:
            funder_name = row.agency
            prediction = await self.get_prediction_with_fallback(db, funder_name)

            # Only include predictions within lookahead window
            if prediction['predicted_date'] <= cutoff_date:
                predictions.append({
                    'funder_name': funder_name,
                    'grant_count': row.grant_count,
                    'last_deadline': (
                        row.last_deadline.date()
                        if isinstance(row.last_deadline, datetime)
                        else row.last_deadline
                    ),
                    **prediction,
                })

        # Sort by predicted date
        predictions.sort(key=lambda x: x['predicted_date'])

        return predictions

    def clear_cache(self, funder_name: Optional[str] = None) -> None:
        """
        Clear cached models.

        Args:
            funder_name: Specific funder to clear, or None to clear all
        """
        if funder_name:
            self._model_cache.pop(funder_name, None)
            logger.info(f"Cleared cache for funder: {funder_name}")
        else:
            self._model_cache.clear()
            logger.info("Cleared all cached models")

    def get_cache_stats(self) -> dict:
        """
        Get statistics about the model cache.

        Returns:
            Dictionary with cache statistics
        """
        return {
            'cached_models': len(self._model_cache),
            'funder_names': list(self._model_cache.keys()),
            'cache_expiry_hours': self._cache_expiry_hours,
        }


# Global predictor instance for easy reuse
_predictor_instance: Optional[GrantDeadlinePredictor] = None


def get_predictor(min_data_points: int = 4) -> GrantDeadlinePredictor:
    """
    Get or create the global predictor instance.

    Args:
        min_data_points: Minimum data points required for ML training

    Returns:
        GrantDeadlinePredictor instance
    """
    global _predictor_instance
    if _predictor_instance is None:
        _predictor_instance = GrantDeadlinePredictor(min_data_points=min_data_points)
    return _predictor_instance
