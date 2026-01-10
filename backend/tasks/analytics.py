"""
GrantRadar Analytics Tasks

Celery tasks for computing system-wide and user-specific analytics metrics,
including grant discovery stats, match quality reports, and agent performance.

Tasks:
    - compute_daily_analytics: System-wide metrics (scheduled every 6 hours)
    - compute_user_analytics: User-specific engagement metrics
    - generate_match_quality_report: Match algorithm performance analysis
    - compute_agent_performance_metrics: Discovery and matching agent health
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Any, Optional

import redis
from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from backend.celery_app import celery_app, normal_task
from backend.core.config import settings
from backend.database import get_sync_db
from backend.models import AlertSent, Grant, Match, User

logger = logging.getLogger(__name__)

# Redis client for caching analytics results
redis_client = redis.from_url(settings.redis_url, decode_responses=True)

# Cache expiry times
CACHE_TTL_DAILY_ANALYTICS = 6 * 60 * 60  # 6 hours
CACHE_TTL_USER_ANALYTICS = 30 * 60  # 30 minutes
CACHE_TTL_REPORTS = 24 * 60 * 60  # 24 hours


# =============================================================================
# Helper Functions
# =============================================================================


def _cache_key(prefix: str, identifier: str = "") -> str:
    """Generate a consistent cache key for analytics data."""
    if identifier:
        return f"analytics:{prefix}:{identifier}"
    return f"analytics:{prefix}"


def _store_in_cache(key: str, data: dict[str, Any], ttl: int) -> None:
    """Store analytics data in Redis cache with TTL."""
    try:
        redis_client.setex(key, ttl, json.dumps(data))
        logger.debug(f"Cached analytics data: {key} (TTL: {ttl}s)")
    except Exception as e:
        logger.warning(f"Failed to cache analytics data: {e}")


def _get_from_cache(key: str) -> Optional[dict[str, Any]]:
    """Retrieve analytics data from Redis cache."""
    try:
        cached = redis_client.get(key)
        if cached:
            return json.loads(cached)
    except Exception as e:
        logger.warning(f"Failed to retrieve cached analytics: {e}")
    return None


def _calculate_percentage(numerator: int, denominator: int) -> float:
    """Safely calculate percentage, handling division by zero."""
    if denominator == 0:
        return 0.0
    return round((numerator / denominator) * 100, 2)


# =============================================================================
# System-Wide Analytics
# =============================================================================


@normal_task
@celery_app.task(bind=True, name="backend.tasks.analytics.compute_daily_analytics")
def compute_daily_analytics(self) -> dict[str, Any]:
    """
    Compute system-wide analytics metrics.

    Scheduled to run every 6 hours via Celery Beat. Calculates:
    - Total grants discovered (by source)
    - Total matches computed
    - Match score distribution
    - Alert delivery success rates
    - User engagement metrics

    Results are cached in Redis and can optionally be stored in a metrics table.

    Returns:
        dict: Analytics summary with all computed metrics
    """
    logger.info("Starting daily analytics computation")
    db: Session = get_sync_db()

    try:
        # Define time ranges for analysis
        now = datetime.utcnow()
        last_24h = now - timedelta(hours=24)
        last_7d = now - timedelta(days=7)
        now - timedelta(days=30)

        # ===== Grant Discovery Metrics =====
        # Total grants by source
        grants_by_source = db.query(Grant.source, func.count(Grant.id)).group_by(Grant.source).all()
        total_grants = sum(count for _, count in grants_by_source)

        # Recent grant discovery
        grants_last_24h = db.query(func.count(Grant.id)).filter(Grant.created_at >= last_24h).scalar() or 0

        grants_last_7d = db.query(func.count(Grant.id)).filter(Grant.created_at >= last_7d).scalar() or 0

        # Active grants (deadline not passed)
        active_grants = db.query(func.count(Grant.id)).filter(Grant.deadline >= now).scalar() or 0

        # ===== Match Computation Metrics =====
        # Total matches computed
        total_matches = db.query(func.count(Match.id)).scalar() or 0

        matches_last_24h = db.query(func.count(Match.id)).filter(Match.created_at >= last_24h).scalar() or 0

        matches_last_7d = db.query(func.count(Match.id)).filter(Match.created_at >= last_7d).scalar() or 0

        # ===== Match Score Distribution =====
        # Calculate score buckets
        score_buckets = {
            "0-20": 0,
            "20-40": 0,
            "40-60": 0,
            "60-80": 0,
            "80-90": 0,
            "90-100": 0,
        }

        # Convert match_score from 0-1 to 0-100 for bucketing
        matches = db.query(Match.match_score).all()
        for (score,) in matches:
            score_percent = score * 100
            if score_percent < 20:
                score_buckets["0-20"] += 1
            elif score_percent < 40:
                score_buckets["20-40"] += 1
            elif score_percent < 60:
                score_buckets["40-60"] += 1
            elif score_percent < 80:
                score_buckets["60-80"] += 1
            elif score_percent < 90:
                score_buckets["80-90"] += 1
            else:
                score_buckets["90-100"] += 1

        # Average match score
        avg_match_score = db.query(func.avg(Match.match_score)).scalar() or 0.0

        # ===== Alert Delivery Metrics =====
        # Total alerts sent
        total_alerts_sent = db.query(func.count(AlertSent.id)).scalar() or 0

        alerts_by_channel = db.query(AlertSent.channel, func.count(AlertSent.id)).group_by(AlertSent.channel).all()

        # Alert engagement rates
        total_opened = db.query(func.count(AlertSent.id)).filter(AlertSent.opened_at.isnot(None)).scalar() or 0

        total_clicked = db.query(func.count(AlertSent.id)).filter(AlertSent.clicked_at.isnot(None)).scalar() or 0

        open_rate = _calculate_percentage(total_opened, total_alerts_sent)
        click_rate = _calculate_percentage(total_clicked, total_alerts_sent)
        click_through_rate = _calculate_percentage(total_clicked, total_opened)

        # Recent alert activity
        alerts_last_24h = db.query(func.count(AlertSent.id)).filter(AlertSent.sent_at >= last_24h).scalar() or 0

        # ===== User Engagement Metrics =====
        # Total active users (users with matches)
        active_users = db.query(func.count(func.distinct(Match.user_id))).scalar() or 0

        # Total registered users
        total_users = db.query(func.count(User.id)).scalar() or 0

        # Users who took action on matches
        users_with_actions = (
            db.query(func.count(func.distinct(Match.user_id))).filter(Match.user_action.isnot(None)).scalar() or 0
        )

        user_engagement_rate = _calculate_percentage(users_with_actions, active_users)

        # User actions breakdown
        user_actions = (
            db.query(Match.user_action, func.count(Match.id))
            .filter(Match.user_action.isnot(None))
            .group_by(Match.user_action)
            .all()
        )

        # ===== Compile Analytics Summary =====
        analytics_summary = {
            "timestamp": now.isoformat(),
            "period": "daily",
            "grant_discovery": {
                "total_grants": total_grants,
                "active_grants": active_grants,
                "grants_by_source": dict(grants_by_source),
                "grants_last_24h": grants_last_24h,
                "grants_last_7d": grants_last_7d,
            },
            "match_computation": {
                "total_matches": total_matches,
                "matches_last_24h": matches_last_24h,
                "matches_last_7d": matches_last_7d,
                "avg_match_score": round(float(avg_match_score), 4),
                "score_distribution": score_buckets,
            },
            "alert_delivery": {
                "total_alerts_sent": total_alerts_sent,
                "alerts_last_24h": alerts_last_24h,
                "alerts_by_channel": dict(alerts_by_channel),
                "open_rate_percent": open_rate,
                "click_rate_percent": click_rate,
                "click_through_rate_percent": click_through_rate,
            },
            "user_engagement": {
                "total_users": total_users,
                "active_users": active_users,
                "users_with_actions": users_with_actions,
                "engagement_rate_percent": user_engagement_rate,
                "user_actions": dict(user_actions),
            },
        }

        # Cache the results
        cache_key = _cache_key("daily", now.strftime("%Y-%m-%d"))
        _store_in_cache(cache_key, analytics_summary, CACHE_TTL_DAILY_ANALYTICS)

        # Also store as "latest" for quick access
        latest_key = _cache_key("daily", "latest")
        _store_in_cache(latest_key, analytics_summary, CACHE_TTL_DAILY_ANALYTICS)

        logger.info(
            f"Daily analytics computed successfully. "
            f"Grants: {total_grants}, Matches: {total_matches}, "
            f"Alerts: {total_alerts_sent}, Active Users: {active_users}"
        )

        return analytics_summary

    except Exception as e:
        logger.error(f"Failed to compute daily analytics: {e}", exc_info=True)
        raise
    finally:
        db.close()


# =============================================================================
# User-Specific Analytics
# =============================================================================


@celery_app.task(bind=True, name="backend.tasks.analytics.compute_user_analytics")
def compute_user_analytics(self, user_id: str) -> dict[str, Any]:
    """
    Compute user-specific analytics metrics.

    Analyzes individual user engagement and match quality:
    - Match acceptance rate (saved/dismissed ratio)
    - Saved grants count
    - Application conversion rate
    - Average match scores over time
    - Alert engagement metrics

    Args:
        user_id: UUID of the user to analyze

    Returns:
        dict: User-specific analytics metrics
    """
    logger.info(f"Computing analytics for user {user_id}")
    db: Session = get_sync_db()

    try:
        # Check cache first
        cache_key = _cache_key("user", user_id)
        cached_data = _get_from_cache(cache_key)
        if cached_data:
            logger.debug(f"Returning cached analytics for user {user_id}")
            return cached_data

        # ===== User Match Statistics =====
        # Total matches for user
        total_matches = db.query(func.count(Match.id)).filter(Match.user_id == user_id).scalar() or 0

        if total_matches == 0:
            # Return empty metrics if no matches
            empty_metrics = {
                "user_id": user_id,
                "timestamp": datetime.utcnow().isoformat(),
                "total_matches": 0,
                "message": "No matches found for this user",
            }
            _store_in_cache(cache_key, empty_metrics, CACHE_TTL_USER_ANALYTICS)
            return empty_metrics

        # Match actions breakdown
        saved_count = (
            db.query(func.count(Match.id)).filter(and_(Match.user_id == user_id, Match.user_action == "saved")).scalar()
            or 0
        )

        dismissed_count = (
            db.query(func.count(Match.id))
            .filter(and_(Match.user_id == user_id, Match.user_action == "dismissed"))
            .scalar()
            or 0
        )

        applied_count = (
            db.query(func.count(Match.id))
            .filter(and_(Match.user_id == user_id, Match.user_action == "applied"))
            .scalar()
            or 0
        )

        # Calculate rates
        acceptance_rate = _calculate_percentage(saved_count, total_matches)
        dismissal_rate = _calculate_percentage(dismissed_count, total_matches)
        application_rate = _calculate_percentage(applied_count, total_matches)

        # Application conversion rate (applied / saved)
        conversion_rate = _calculate_percentage(applied_count, saved_count)

        # ===== Match Quality Metrics =====
        # Average match score
        avg_score = db.query(func.avg(Match.match_score)).filter(Match.user_id == user_id).scalar() or 0.0

        # Average score for saved matches
        avg_saved_score = (
            db.query(func.avg(Match.match_score))
            .filter(and_(Match.user_id == user_id, Match.user_action == "saved"))
            .scalar()
            or 0.0
        )

        # Average score for dismissed matches
        avg_dismissed_score = (
            db.query(func.avg(Match.match_score))
            .filter(and_(Match.user_id == user_id, Match.user_action == "dismissed"))
            .scalar()
            or 0.0
        )

        # High-quality matches (score > 0.8)
        high_quality_matches = (
            db.query(func.count(Match.id)).filter(and_(Match.user_id == user_id, Match.match_score > 0.8)).scalar() or 0
        )

        # ===== Alert Engagement =====
        # Get alerts for this user's matches
        user_alerts = (
            db.query(AlertSent).join(Match, AlertSent.match_id == Match.id).filter(Match.user_id == user_id).all()
        )

        total_alerts = len(user_alerts)
        opened_alerts = sum(1 for alert in user_alerts if alert.opened_at)
        clicked_alerts = sum(1 for alert in user_alerts if alert.clicked_at)

        user_open_rate = _calculate_percentage(opened_alerts, total_alerts)
        user_click_rate = _calculate_percentage(clicked_alerts, total_alerts)

        # ===== Time-Series Data =====
        # Match scores over the last 30 days (weekly buckets)
        now = datetime.utcnow()
        score_timeline = []
        for weeks_ago in range(4, -1, -1):
            start_date = now - timedelta(weeks=weeks_ago + 1)
            end_date = now - timedelta(weeks=weeks_ago)

            avg_weekly_score = (
                db.query(func.avg(Match.match_score))
                .filter(
                    and_(
                        Match.user_id == user_id,
                        Match.created_at >= start_date,
                        Match.created_at < end_date,
                    )
                )
                .scalar()
                or 0.0
            )

            matches_count = (
                db.query(func.count(Match.id))
                .filter(
                    and_(
                        Match.user_id == user_id,
                        Match.created_at >= start_date,
                        Match.created_at < end_date,
                    )
                )
                .scalar()
                or 0
            )

            score_timeline.append(
                {
                    "week_start": start_date.strftime("%Y-%m-%d"),
                    "avg_score": round(float(avg_weekly_score), 4),
                    "match_count": matches_count,
                }
            )

        # ===== Compile User Analytics =====
        user_analytics = {
            "user_id": user_id,
            "timestamp": now.isoformat(),
            "match_statistics": {
                "total_matches": total_matches,
                "saved_count": saved_count,
                "dismissed_count": dismissed_count,
                "applied_count": applied_count,
                "acceptance_rate_percent": acceptance_rate,
                "dismissal_rate_percent": dismissal_rate,
                "application_rate_percent": application_rate,
                "conversion_rate_percent": conversion_rate,
            },
            "match_quality": {
                "avg_match_score": round(float(avg_score), 4),
                "avg_saved_score": round(float(avg_saved_score), 4),
                "avg_dismissed_score": round(float(avg_dismissed_score), 4),
                "high_quality_matches": high_quality_matches,
                "high_quality_percentage": _calculate_percentage(high_quality_matches, total_matches),
            },
            "alert_engagement": {
                "total_alerts": total_alerts,
                "opened_alerts": opened_alerts,
                "clicked_alerts": clicked_alerts,
                "open_rate_percent": user_open_rate,
                "click_rate_percent": user_click_rate,
            },
            "score_timeline": score_timeline,
        }

        # Cache the results
        _store_in_cache(cache_key, user_analytics, CACHE_TTL_USER_ANALYTICS)

        logger.info(f"User analytics computed for {user_id}. Matches: {total_matches}, Acceptance: {acceptance_rate}%")

        return user_analytics

    except Exception as e:
        logger.error(f"Failed to compute user analytics for {user_id}: {e}", exc_info=True)
        raise
    finally:
        db.close()


# =============================================================================
# Match Quality Analysis
# =============================================================================


@celery_app.task(bind=True, name="backend.tasks.analytics.generate_match_quality_report")
def generate_match_quality_report(self) -> dict[str, Any]:
    """
    Generate comprehensive match quality report.

    Analyzes match algorithm performance based on user feedback:
    - Precision/recall metrics (estimated from user actions)
    - Score calibration analysis
    - False positive/negative rates
    - Improvement recommendations

    Returns:
        dict: Match quality report with performance metrics
    """
    logger.info("Generating match quality report")
    db: Session = get_sync_db()

    try:
        # Check cache first
        cache_key = _cache_key("match_quality_report", "latest")
        cached_report = _get_from_cache(cache_key)
        if cached_report:
            logger.debug("Returning cached match quality report")
            return cached_report

        # ===== Overall Match Statistics =====
        total_matches = db.query(func.count(Match.id)).scalar() or 0

        if total_matches == 0:
            empty_report = {
                "timestamp": datetime.utcnow().isoformat(),
                "total_matches": 0,
                "message": "No matches available for analysis",
            }
            return empty_report

        # Matches with user actions (labeled data)
        labeled_matches = db.query(func.count(Match.id)).filter(Match.user_action.isnot(None)).scalar() or 0

        labeling_rate = _calculate_percentage(labeled_matches, total_matches)

        # ===== Precision/Recall Estimation =====
        # True Positives: High score (>0.7) AND saved/applied
        true_positives = (
            db.query(func.count(Match.id))
            .filter(and_(Match.match_score > 0.7, Match.user_action.in_(["saved", "applied"])))
            .scalar()
            or 0
        )

        # False Positives: High score (>0.7) AND dismissed
        false_positives = (
            db.query(func.count(Match.id))
            .filter(and_(Match.match_score > 0.7, Match.user_action == "dismissed"))
            .scalar()
            or 0
        )

        # False Negatives: Low score (<=0.7) AND saved/applied
        false_negatives = (
            db.query(func.count(Match.id))
            .filter(and_(Match.match_score <= 0.7, Match.user_action.in_(["saved", "applied"])))
            .scalar()
            or 0
        )

        # True Negatives: Low score (<=0.7) AND dismissed
        true_negatives = (
            db.query(func.count(Match.id))
            .filter(and_(Match.match_score <= 0.7, Match.user_action == "dismissed"))
            .scalar()
            or 0
        )

        # Calculate precision and recall
        precision = _calculate_percentage(true_positives, true_positives + false_positives)
        recall = _calculate_percentage(true_positives, true_positives + false_negatives)

        # F1 score
        if precision + recall > 0:
            f1_score = round(2 * (precision * recall) / (precision + recall), 2)
        else:
            f1_score = 0.0

        # Accuracy
        total_labeled = true_positives + false_positives + false_negatives + true_negatives
        accuracy = _calculate_percentage(true_positives + true_negatives, total_labeled)

        # ===== Score Calibration Analysis =====
        # Analyze if match scores correlate with user actions
        score_buckets_analysis = {}

        score_ranges = [
            (0.0, 0.2, "0-20%"),
            (0.2, 0.4, "20-40%"),
            (0.4, 0.6, "40-60%"),
            (0.6, 0.8, "60-80%"),
            (0.8, 1.0, "80-100%"),
        ]

        for min_score, max_score, label in score_ranges:
            # Get matches in this score range
            bucket_matches = (
                db.query(Match)
                .filter(
                    and_(Match.match_score >= min_score, Match.match_score < max_score, Match.user_action.isnot(None))
                )
                .all()
            )

            if bucket_matches:
                saved_or_applied = sum(1 for m in bucket_matches if m.user_action in ["saved", "applied"])
                dismissed = sum(1 for m in bucket_matches if m.user_action == "dismissed")

                score_buckets_analysis[label] = {
                    "total_matches": len(bucket_matches),
                    "saved_or_applied": saved_or_applied,
                    "dismissed": dismissed,
                    "positive_rate_percent": _calculate_percentage(saved_or_applied, len(bucket_matches)),
                }

        # ===== Score Distribution Analysis =====
        avg_score_saved = (
            db.query(func.avg(Match.match_score)).filter(Match.user_action.in_(["saved", "applied"])).scalar() or 0.0
        )

        avg_score_dismissed = (
            db.query(func.avg(Match.match_score)).filter(Match.user_action == "dismissed").scalar() or 0.0
        )

        score_separation = round(float(avg_score_saved - avg_score_dismissed), 4)

        # ===== Feedback Analysis =====
        matches_with_feedback = db.query(func.count(Match.id)).filter(Match.user_feedback.isnot(None)).scalar() or 0

        # ===== Improvement Recommendations =====
        recommendations = []

        if precision < 70:
            recommendations.append(
                "Low precision detected. Consider increasing match score threshold "
                "or refining matching algorithm to reduce false positives."
            )

        if recall < 70:
            recommendations.append(
                "Low recall detected. The algorithm may be too conservative. "
                "Consider expanding match criteria or lowering threshold."
            )

        if score_separation < 0.1:
            recommendations.append(
                "Low score separation between saved and dismissed matches. The scoring function may need recalibration."
            )

        if labeling_rate < 20:
            recommendations.append(
                f"Only {labeling_rate}% of matches have user feedback. "
                "Encourage more user engagement to improve accuracy metrics."
            )

        # ===== Compile Report =====
        quality_report = {
            "timestamp": datetime.utcnow().isoformat(),
            "overview": {
                "total_matches": total_matches,
                "labeled_matches": labeled_matches,
                "labeling_rate_percent": labeling_rate,
            },
            "performance_metrics": {
                "precision_percent": precision,
                "recall_percent": recall,
                "f1_score": f1_score,
                "accuracy_percent": accuracy,
                "confusion_matrix": {
                    "true_positives": true_positives,
                    "false_positives": false_positives,
                    "true_negatives": true_negatives,
                    "false_negatives": false_negatives,
                },
            },
            "score_calibration": {
                "avg_score_saved": round(float(avg_score_saved), 4),
                "avg_score_dismissed": round(float(avg_score_dismissed), 4),
                "score_separation": score_separation,
                "bucket_analysis": score_buckets_analysis,
            },
            "feedback": {
                "matches_with_feedback": matches_with_feedback,
                "feedback_rate_percent": _calculate_percentage(matches_with_feedback, total_matches),
            },
            "recommendations": recommendations,
        }

        # Cache the report
        _store_in_cache(cache_key, quality_report, CACHE_TTL_REPORTS)

        logger.info(f"Match quality report generated. Precision: {precision}%, Recall: {recall}%, F1: {f1_score}")

        return quality_report

    except Exception as e:
        logger.error(f"Failed to generate match quality report: {e}", exc_info=True)
        raise
    finally:
        db.close()


# =============================================================================
# Agent Performance Metrics
# =============================================================================


@celery_app.task(bind=True, name="backend.tasks.analytics.compute_agent_performance_metrics")
def compute_agent_performance_metrics(self) -> dict[str, Any]:
    """
    Compute performance metrics for discovery and matching agents.

    Tracks operational health of the system:
    - Discovery agent success rates by source
    - Matching agent latency and throughput
    - Alert delivery metrics
    - System health indicators

    Returns:
        dict: Agent performance metrics and health status
    """
    logger.info("Computing agent performance metrics")
    db: Session = get_sync_db()

    try:
        # Check cache first
        cache_key = _cache_key("agent_performance", "latest")
        cached_metrics = _get_from_cache(cache_key)
        if cached_metrics:
            logger.debug("Returning cached agent performance metrics")
            return cached_metrics

        now = datetime.utcnow()
        last_24h = now - timedelta(hours=24)
        last_7d = now - timedelta(days=7)

        # ===== Discovery Agent Metrics =====
        # Grant discovery by source (last 24h and 7d)
        grants_24h_by_source = (
            db.query(Grant.source, func.count(Grant.id))
            .filter(Grant.created_at >= last_24h)
            .group_by(Grant.source)
            .all()
        )

        grants_7d_by_source = (
            db.query(Grant.source, func.count(Grant.id))
            .filter(Grant.created_at >= last_7d)
            .group_by(Grant.source)
            .all()
        )

        # Discovery rates (grants per hour)
        discovery_rate_24h = {}
        for source, count in grants_24h_by_source:
            discovery_rate_24h[source] = round(count / 24, 2)

        # Total discovery rate
        total_discovered_24h = sum(count for _, count in grants_24h_by_source)
        total_discovered_7d = sum(count for _, count in grants_7d_by_source)

        # Health check: Expected minimum discovery rates (configurable thresholds)
        discovery_health = {
            "status": "healthy",
            "issues": [],
        }

        # Check if discovery has stopped
        if total_discovered_24h == 0:
            discovery_health["status"] = "critical"
            discovery_health["issues"].append("No grants discovered in last 24 hours")
        elif total_discovered_24h < 10:
            discovery_health["status"] = "warning"
            discovery_health["issues"].append("Low discovery rate in last 24 hours")

        # ===== Matching Agent Metrics =====
        # Matches computed in last 24h
        matches_computed_24h = db.query(func.count(Match.id)).filter(Match.created_at >= last_24h).scalar() or 0

        matches_computed_7d = db.query(func.count(Match.id)).filter(Match.created_at >= last_7d).scalar() or 0

        # Matching throughput (matches per hour)
        matching_rate_24h = round(matches_computed_24h / 24, 2)

        # Average time to match (estimated from grant->match creation time)
        # This is a simplified metric - in production, you'd track task completion times
        avg_match_latency_estimate = "Not tracked"  # Would need task timing data

        # Matching health
        matching_health = {
            "status": "healthy",
            "issues": [],
        }

        # Check if matching is keeping up with discovery
        if total_discovered_24h > 0:
            match_to_discovery_ratio = matches_computed_24h / total_discovered_24h
            if match_to_discovery_ratio < 0.5:
                matching_health["status"] = "warning"
                matching_health["issues"].append(
                    f"Matching rate ({matches_computed_24h}) is low compared to discovery rate ({total_discovered_24h})"
                )

        # ===== Alert Delivery Metrics =====
        # Alerts sent in last 24h
        alerts_sent_24h = db.query(func.count(AlertSent.id)).filter(AlertSent.sent_at >= last_24h).scalar() or 0

        # Alert delivery by channel
        alerts_by_channel_24h = (
            db.query(AlertSent.channel, func.count(AlertSent.id))
            .filter(AlertSent.sent_at >= last_24h)
            .group_by(AlertSent.channel)
            .all()
        )

        # Alert engagement in last 24h
        alerts_opened_24h = (
            db.query(func.count(AlertSent.id))
            .filter(and_(AlertSent.sent_at >= last_24h, AlertSent.opened_at.isnot(None)))
            .scalar()
            or 0
        )

        alerts_clicked_24h = (
            db.query(func.count(AlertSent.id))
            .filter(and_(AlertSent.sent_at >= last_24h, AlertSent.clicked_at.isnot(None)))
            .scalar()
            or 0
        )

        # Alert delivery health
        alert_health = {
            "status": "healthy",
            "issues": [],
        }

        # Check if alerts are being sent
        if matches_computed_24h > 100 and alerts_sent_24h == 0:
            alert_health["status"] = "critical"
            alert_health["issues"].append("No alerts sent despite new matches")

        # ===== System Health Summary =====
        # Overall system health (worst status wins)
        health_statuses = [
            discovery_health["status"],
            matching_health["status"],
            alert_health["status"],
        ]

        if "critical" in health_statuses:
            overall_health = "critical"
        elif "warning" in health_statuses:
            overall_health = "warning"
        else:
            overall_health = "healthy"

        # ===== Compile Performance Report =====
        performance_metrics = {
            "timestamp": now.isoformat(),
            "overall_health": overall_health,
            "discovery_agent": {
                "health": discovery_health,
                "grants_discovered_24h": total_discovered_24h,
                "grants_discovered_7d": total_discovered_7d,
                "discovery_by_source_24h": dict(grants_24h_by_source),
                "discovery_by_source_7d": dict(grants_7d_by_source),
                "discovery_rate_per_hour": discovery_rate_24h,
            },
            "matching_agent": {
                "health": matching_health,
                "matches_computed_24h": matches_computed_24h,
                "matches_computed_7d": matches_computed_7d,
                "matching_rate_per_hour": matching_rate_24h,
                "avg_latency": avg_match_latency_estimate,
            },
            "alert_agent": {
                "health": alert_health,
                "alerts_sent_24h": alerts_sent_24h,
                "alerts_by_channel_24h": dict(alerts_by_channel_24h),
                "alerts_opened_24h": alerts_opened_24h,
                "alerts_clicked_24h": alerts_clicked_24h,
                "open_rate_24h_percent": _calculate_percentage(alerts_opened_24h, alerts_sent_24h),
                "click_rate_24h_percent": _calculate_percentage(alerts_clicked_24h, alerts_sent_24h),
            },
        }

        # Cache the metrics
        _store_in_cache(cache_key, performance_metrics, CACHE_TTL_REPORTS)

        logger.info(
            f"Agent performance metrics computed. "
            f"Health: {overall_health}, "
            f"Discovered: {total_discovered_24h}, "
            f"Matched: {matches_computed_24h}, "
            f"Alerts: {alerts_sent_24h}"
        )

        return performance_metrics

    except Exception as e:
        logger.error(f"Failed to compute agent performance metrics: {e}", exc_info=True)
        raise
    finally:
        db.close()


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "compute_daily_analytics",
    "compute_user_analytics",
    "generate_match_quality_report",
    "compute_agent_performance_metrics",
]
