"""
Winners Analytics Service for AI-powered analysis of funded grants.
Provides keyword extraction, abstract pattern analysis, and success prediction.
"""

import logging
import re
from collections import Counter
from typing import Optional

from openai import AsyncOpenAI

from backend.core.config import settings
from backend.services.cache import get_cached, set_cached
from backend.services.winners import get_winners_service, WinnersSearchRequest
from backend.schemas.winners import (
    AbstractAnalysisRequest,
    AbstractAnalysisResponse,
    AbstractPattern,
    KeywordAnalysisRequest,
    KeywordAnalysisResponse,
    KeywordCluster,
    KeywordItem,
    LanguageInsights,
    PredictionFactor,
    ProfileKeywordComparison,
    SuccessPredictionRequest,
    SuccessPredictionResponse,
    UserAbstractComparison,
)

logger = logging.getLogger(__name__)

# Common stop words to filter from keyword extraction
STOP_WORDS = {
    "the",
    "a",
    "an",
    "and",
    "or",
    "but",
    "in",
    "on",
    "at",
    "to",
    "for",
    "of",
    "with",
    "by",
    "from",
    "as",
    "is",
    "was",
    "are",
    "were",
    "been",
    "be",
    "have",
    "has",
    "had",
    "do",
    "does",
    "did",
    "will",
    "would",
    "could",
    "should",
    "may",
    "might",
    "must",
    "shall",
    "this",
    "that",
    "these",
    "those",
    "it",
    "its",
    "we",
    "our",
    "their",
    "they",
    "you",
    "your",
    "he",
    "she",
    "him",
    "her",
    "his",
    "which",
    "who",
    "whom",
    "what",
    "when",
    "where",
    "why",
    "how",
    "all",
    "each",
    "every",
    "both",
    "few",
    "more",
    "most",
    "other",
    "some",
    "such",
    "no",
    "not",
    "only",
    "own",
    "same",
    "so",
    "than",
    "too",
    "very",
    "can",
    "just",
    "also",
    "using",
    "used",
    "study",
    "studies",
    "aim",
    "aims",
    "project",
    "research",
    "proposed",
    "specific",
    "goal",
    "goals",
    "objective",
    "data",
    "analysis",
    "method",
    "methods",
    "approach",
    "approaches",
    "result",
    "results",
    "finding",
    "findings",
    "develop",
    "developed",
    "new",
    "novel",
    "first",
    "one",
    "two",
    "three",
    "role",
    "mechanism",
    "mechanisms",
    "understanding",
    "understand",
    "investigate",
    "examining",
}


class WinnersAnalyticsService:
    """
    AI-powered analytics service for funded grant analysis.

    Provides:
    - Keyword extraction and clustering
    - Abstract pattern analysis
    - Success probability prediction
    """

    def __init__(self):
        self.openai = None
        if settings.openai_api_key:
            self.openai = AsyncOpenAI(api_key=settings.openai_api_key)

    def _extract_keywords(self, text: str) -> list[str]:
        """Extract keywords from text."""
        if not text:
            return []

        # Lowercase and split
        words = re.findall(r"\b[a-zA-Z]{3,}\b", text.lower())

        # Filter stop words
        keywords = [w for w in words if w not in STOP_WORDS]

        return keywords

    def _extract_bigrams(self, text: str) -> list[str]:
        """Extract two-word phrases from text."""
        if not text:
            return []

        words = re.findall(r"\b[a-zA-Z]{3,}\b", text.lower())
        words = [w for w in words if w not in STOP_WORDS]

        bigrams = []
        for i in range(len(words) - 1):
            bigrams.append(f"{words[i]} {words[i + 1]}")

        return bigrams

    async def analyze_keywords(
        self,
        request: KeywordAnalysisRequest,
        user_profile_keywords: Optional[list[str]] = None,
    ) -> KeywordAnalysisResponse:
        """
        Analyze keywords in funded projects.

        Args:
            request: Analysis parameters
            user_profile_keywords: Optional user profile keywords for comparison

        Returns:
            Keyword analysis with top terms and clusters
        """
        cache_key = f"winners:keywords:{request.model_dump()}"
        cached = get_cached(cache_key, ttl_minutes=60)
        if cached:
            return KeywordAnalysisResponse(**cached)

        # Fetch funded projects
        winners_service = get_winners_service()

        search_request = WinnersSearchRequest(
            activity_codes=[request.mechanism] if request.mechanism else None,
            institute=request.institute,
            fiscal_years=request.fiscal_years,
            page=1,
            limit=100,  # Analyze 100 projects
        )

        result = await winners_service.search_projects(search_request)

        if not result.results:
            return KeywordAnalysisResponse(
                top_keywords=[],
                keyword_clusters=[],
                profile_comparison=None,
                projects_analyzed=0,
            )

        # Extract all keywords from abstracts
        all_keywords: list[str] = []
        all_bigrams: list[str] = []

        for project in result.results:
            if project.abstract:
                all_keywords.extend(self._extract_keywords(project.abstract))
                all_bigrams.extend(self._extract_bigrams(project.abstract))

        # Count frequencies
        keyword_counts = Counter(all_keywords)
        bigram_counts = Counter(all_bigrams)

        # Combine single words and bigrams, preferring bigrams
        combined_counts: Counter = Counter()
        for bigram, count in bigram_counts.most_common(50):
            combined_counts[bigram] = count

        for word, count in keyword_counts.most_common(100):
            # Skip if word is part of a top bigram
            in_bigram = any(word in bg for bg in combined_counts.keys())
            if not in_bigram:
                combined_counts[word] = count

        # Build keyword items
        total_projects = len(result.results)
        top_keywords = []

        for keyword, count in combined_counts.most_common(request.top_n):
            percentage = (count / total_projects) * 100 if total_projects > 0 else 0
            top_keywords.append(
                KeywordItem(
                    keyword=keyword,
                    frequency=count,
                    percentage=round(percentage, 1),
                    trending=None,  # Would need historical data
                )
            )

        # Build clusters (simplified - group by common stems)
        clusters = self._cluster_keywords(list(combined_counts.keys())[:50])

        # Profile comparison
        profile_comparison = None
        if request.compare_to_profile and user_profile_keywords:
            matching = [k for k in user_profile_keywords if k.lower() in combined_counts]
            top_missing = [
                k
                for k, _ in combined_counts.most_common(20)
                if k.lower() not in [pk.lower() for pk in user_profile_keywords]
            ][:10]

            match_score = (len(matching) / len(user_profile_keywords) * 100) if user_profile_keywords else 0

            profile_comparison = ProfileKeywordComparison(
                matching_keywords=matching,
                missing_keywords=top_missing,
                match_score=round(match_score, 1),
            )

        response = KeywordAnalysisResponse(
            top_keywords=top_keywords,
            keyword_clusters=clusters,
            profile_comparison=profile_comparison,
            projects_analyzed=total_projects,
        )

        set_cached(cache_key, response.model_dump())
        return response

    def _cluster_keywords(self, keywords: list[str]) -> list[KeywordCluster]:
        """Group keywords into thematic clusters (simplified)."""
        # Define some common research theme prefixes/categories
        theme_patterns = {
            "cancer": ["cancer", "tumor", "oncolog", "carcinoma", "metasta", "leukemia", "lymphoma"],
            "neuroscience": ["neural", "brain", "neuro", "cogniti", "cortex", "synap", "memory"],
            "genetics": ["gene", "genom", "dna", "rna", "genetic", "mutation", "expression"],
            "immunology": ["immune", "immun", "antibod", "t cell", "cytokine", "inflamm"],
            "cardiovascular": ["cardiac", "heart", "vascular", "blood", "cardio", "artery"],
            "infectious disease": ["virus", "viral", "bacteria", "infect", "pathogen", "vaccine"],
            "drug development": ["drug", "therapeutic", "pharmacol", "compound", "inhibitor"],
            "clinical": ["patient", "clinical", "trial", "treatment", "therapy", "outcome"],
            "methodology": ["method", "technique", "assay", "model", "approach", "protocol"],
            "technology": ["device", "imaging", "sensor", "diagnostic", "algorithm", "software"],
        }

        clusters = []
        used_keywords = set()

        for theme, patterns in theme_patterns.items():
            matching = []
            for kw in keywords:
                if kw in used_keywords:
                    continue
                if any(p in kw.lower() for p in patterns):
                    matching.append(kw)
                    used_keywords.add(kw)

            if matching:
                clusters.append(
                    KeywordCluster(
                        theme=theme.title(),
                        keywords=matching[:10],
                        project_count=len(matching),
                    )
                )

        return clusters[:8]  # Limit to top 8 clusters

    async def analyze_abstracts(
        self,
        request: AbstractAnalysisRequest,
    ) -> AbstractAnalysisResponse:
        """
        AI-powered analysis of successful abstract patterns.

        Args:
            request: Analysis parameters including optional user abstract

        Returns:
            Abstract patterns, language insights, and recommendations
        """
        cache_key = f"winners:abstracts:{request.mechanism}:{request.institute}"
        cached = get_cached(cache_key, ttl_minutes=120)
        if cached and not request.user_abstract:
            return AbstractAnalysisResponse(**cached)

        # Fetch funded projects
        winners_service = get_winners_service()

        search_request = WinnersSearchRequest(
            activity_codes=[request.mechanism],
            institute=request.institute,
            fiscal_years=request.fiscal_years,
            page=1,
            limit=50,
        )

        result = await winners_service.search_projects(search_request)

        # Collect abstracts
        abstracts = [p.abstract for p in result.results if p.abstract]

        if not abstracts:
            return AbstractAnalysisResponse(
                common_patterns=[],
                language_insights=LanguageInsights(
                    avg_length=0,
                    avg_sentences=0,
                    key_phrases=[],
                    action_verbs=[],
                    avoided_phrases=[],
                ),
                recommendations=[],
                user_comparison=None,
                abstracts_analyzed=0,
            )

        # Calculate basic language stats
        total_words = 0
        total_sentences = 0

        for abstract in abstracts:
            words = len(abstract.split())
            sentences = len(re.findall(r"[.!?]+", abstract))
            total_words += words
            total_sentences += max(sentences, 1)

        avg_length = total_words // len(abstracts)
        avg_sentences = total_sentences // len(abstracts)

        # Extract common patterns without AI
        common_patterns = self._extract_abstract_patterns(abstracts)

        # Extract key phrases
        all_keywords = []
        for abstract in abstracts:
            all_keywords.extend(self._extract_bigrams(abstract))

        phrase_counts = Counter(all_keywords)
        key_phrases = [phrase for phrase, _ in phrase_counts.most_common(20)]

        # Common action verbs in grant abstracts
        action_verbs = [
            "investigate",
            "examine",
            "determine",
            "develop",
            "establish",
            "characterize",
            "identify",
            "evaluate",
            "analyze",
            "test",
        ]

        language_insights = LanguageInsights(
            avg_length=avg_length,
            avg_sentences=avg_sentences,
            key_phrases=key_phrases,
            action_verbs=action_verbs,
            avoided_phrases=[
                "we believe",
                "hopefully",
                "attempt to",
                "try to",
                "may possibly",
                "it is our intention",
            ],
        )

        # Generate recommendations
        recommendations = [
            f"Target abstract length: {avg_length - 50} to {avg_length + 50} words",
            "Start with a clear problem statement and significance",
            "Use strong action verbs (investigate, determine, establish)",
            "Include specific aims or objectives clearly stated",
            "End with expected outcomes and impact",
        ]

        # User comparison if abstract provided
        user_comparison = None
        if request.user_abstract and self.openai:
            user_comparison = await self._compare_user_abstract(
                request.user_abstract,
                abstracts[:10],  # Compare against top 10
                request.mechanism,
            )

        response = AbstractAnalysisResponse(
            common_patterns=common_patterns,
            language_insights=language_insights,
            recommendations=recommendations,
            user_comparison=user_comparison,
            abstracts_analyzed=len(abstracts),
        )

        if not request.user_abstract:
            set_cached(cache_key, response.model_dump())

        return response

    def _extract_abstract_patterns(self, abstracts: list[str]) -> list[AbstractPattern]:
        """Extract common structural patterns from abstracts."""
        patterns = []

        # Check for common structural elements
        significance_count = sum(
            1
            for a in abstracts
            if any(term in a.lower() for term in ["significance", "important", "critical", "essential"])
        )
        if significance_count > len(abstracts) * 0.5:
            patterns.append(
                AbstractPattern(
                    pattern_type="structure",
                    description="Significance statement near beginning",
                    examples=["This research is significant because...", "Understanding X is critical for..."],
                    frequency=round(significance_count / len(abstracts) * 100, 1),
                )
            )

        # Check for hypothesis/objective patterns
        hypothesis_count = sum(
            1
            for a in abstracts
            if any(term in a.lower() for term in ["hypothesis", "hypothesize", "we propose", "objective"])
        )
        if hypothesis_count > len(abstracts) * 0.3:
            patterns.append(
                AbstractPattern(
                    pattern_type="structure",
                    description="Clear hypothesis or objective statement",
                    examples=["We hypothesize that...", "The central hypothesis is..."],
                    frequency=round(hypothesis_count / len(abstracts) * 100, 1),
                )
            )

        # Check for approach/methods patterns
        approach_count = sum(
            1 for a in abstracts if any(term in a.lower() for term in ["approach", "methodology", "using", "employ"])
        )
        if approach_count > len(abstracts) * 0.5:
            patterns.append(
                AbstractPattern(
                    pattern_type="approach",
                    description="Methodology or approach description",
                    examples=["Using X approach, we will...", "Our innovative methodology..."],
                    frequency=round(approach_count / len(abstracts) * 100, 1),
                )
            )

        # Check for impact/outcome patterns
        impact_count = sum(
            1
            for a in abstracts
            if any(term in a.lower() for term in ["impact", "outcome", "result in", "lead to", "advance"])
        )
        if impact_count > len(abstracts) * 0.4:
            patterns.append(
                AbstractPattern(
                    pattern_type="impact",
                    description="Expected outcomes and impact",
                    examples=["These studies will lead to...", "The expected impact includes..."],
                    frequency=round(impact_count / len(abstracts) * 100, 1),
                )
            )

        return patterns

    async def _compare_user_abstract(
        self,
        user_abstract: str,
        sample_abstracts: list[str],
        mechanism: str,
    ) -> Optional[UserAbstractComparison]:
        """Compare user's abstract against successful ones using AI."""
        if not self.openai:
            return None

        try:
            prompt = f"""Analyze this grant abstract for a {mechanism} application and compare it to successful funded grants.

USER'S ABSTRACT:
{user_abstract}

EXAMPLES OF SUCCESSFUL {mechanism} ABSTRACTS:
{chr(10).join([f"---{chr(10)}{a[:1000]}" for a in sample_abstracts[:3]])}

Provide a structured analysis:

1. STRENGTHS (3-5 points): What does this abstract do well?
2. GAPS (3-5 points): What's missing or could be improved?
3. SIMILARITY SCORE: Rate 0-100 how similar this is to successful abstracts
4. SUGGESTIONS (3-5 specific actionable recommendations)

Format your response as JSON:
{{
    "strengths": ["...", "..."],
    "gaps": ["...", "..."],
    "similarity_score": 75,
    "suggestions": ["...", "..."]
}}"""

            message = await self.openai.chat.completions.create(
                model=settings.llm_model,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )

            # Parse response
            response_text = message.choices[0].message.content

            # Extract JSON from response
            import json

            json_match = re.search(r"\{[^{}]+\}", response_text, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                return UserAbstractComparison(
                    strengths=data.get("strengths", []),
                    gaps=data.get("gaps", []),
                    similarity_score=float(data.get("similarity_score", 50)),
                    suggestions=data.get("suggestions", []),
                )

        except Exception as e:
            logger.error(f"Abstract comparison failed: {e}")

        return None

    async def predict_success(
        self,
        request: SuccessPredictionRequest,
    ) -> SuccessPredictionResponse:
        """
        Predict success probability based on historical patterns.

        Args:
            request: Prediction parameters

        Returns:
            Success probability with contributing factors
        """
        # Fetch similar funded projects
        winners_service = get_winners_service()

        search_request = WinnersSearchRequest(
            query=request.research_area,
            activity_codes=[request.mechanism],
            institute=request.institute,
            page=1,
            limit=50,
        )

        result = await winners_service.search_projects(search_request)

        # Calculate base probability from historical rates
        # R01 success rates are typically 20-25%, R21 around 15-20%
        mechanism_rates = {
            "R01": 22.0,
            "R21": 18.0,
            "R03": 25.0,
            "R15": 30.0,
            "K08": 35.0,
            "K23": 35.0,
            "K99": 30.0,
            "F31": 25.0,
            "F32": 28.0,
        }

        base_rate = mechanism_rates.get(request.mechanism.upper(), 20.0)

        # Adjust based on factors
        factors = []
        probability = base_rate

        # Factor 1: Similar funded projects found
        similar_count = len(result.results)
        if similar_count > 20:
            probability += 5
            factors.append(
                PredictionFactor(
                    factor="Research Area Activity",
                    impact="positive",
                    weight=0.15,
                    explanation=f"Found {similar_count} similar funded projects, indicating active funding in this area",
                )
            )
        elif similar_count < 5:
            probability -= 3
            factors.append(
                PredictionFactor(
                    factor="Research Area Activity",
                    impact="negative",
                    weight=0.10,
                    explanation="Few similar funded projects found, may be a less active funding area",
                )
            )

        # Factor 2: Previous awards
        if request.pi_previous_awards > 0:
            boost = min(request.pi_previous_awards * 5, 15)
            probability += boost
            factors.append(
                PredictionFactor(
                    factor="Track Record",
                    impact="positive",
                    weight=0.25,
                    explanation=f"PI has {request.pi_previous_awards} previous award(s), demonstrating successful track record",
                )
            )
        else:
            factors.append(
                PredictionFactor(
                    factor="Track Record",
                    impact="neutral",
                    weight=0.15,
                    explanation="No previous awards on record (new investigator)",
                )
            )

        # Factor 3: Institution
        if request.institution:
            # Check if institution appears in funded projects
            inst_matches = sum(
                1
                for p in result.results
                if p.organization and request.institution.lower() in (p.organization.name or "").lower()
            )
            if inst_matches > 5:
                probability += 5
                factors.append(
                    PredictionFactor(
                        factor="Institution",
                        impact="positive",
                        weight=0.15,
                        explanation=f"Institution has strong funding history in this area ({inst_matches} similar awards)",
                    )
                )

        # Factor 4: Keyword alignment
        if request.keywords and result.results:
            all_funded_keywords = []
            for p in result.results:
                if p.abstract:
                    all_funded_keywords.extend(self._extract_keywords(p.abstract))

            funded_keyword_set = set(all_funded_keywords)
            user_keywords = set(k.lower() for k in request.keywords)
            overlap = len(user_keywords & funded_keyword_set)

            if overlap > len(request.keywords) * 0.5:
                probability += 5
                factors.append(
                    PredictionFactor(
                        factor="Keyword Alignment",
                        impact="positive",
                        weight=0.15,
                        explanation=f"Good keyword overlap with funded projects ({overlap}/{len(request.keywords)} keywords match)",
                    )
                )

        # Clamp probability
        probability = max(5, min(95, probability))

        # Determine confidence
        if similar_count > 30:
            confidence = "high"
        elif similar_count > 10:
            confidence = "medium"
        else:
            confidence = "low"

        # Get similar funded projects
        similar_funded = result.results[:5]

        # Generate recommendations
        recommendations = []
        if probability < base_rate:
            recommendations.append("Consider strengthening alignment with funded research in this area")
        if request.pi_previous_awards == 0:
            recommendations.append("For new investigators, consider R21 or K-series mechanisms as stepping stones")
        if not request.keywords:
            recommendations.append("Ensure your proposal uses terminology common in funded grants in this area")

        recommendations.extend(
            [
                "Review abstracts of similar funded projects for structure and language patterns",
                "Consider reaching out to program officers to discuss your research direction",
            ]
        )

        return SuccessPredictionResponse(
            probability=round(probability, 1),
            confidence=confidence,
            factors=factors,
            similar_funded=similar_funded,
            recommendations=recommendations[:5],
            historical_rate=base_rate,
        )


# Singleton instance
_analytics_service: Optional[WinnersAnalyticsService] = None


def get_winners_analytics_service() -> WinnersAnalyticsService:
    """Get or create the analytics service singleton."""
    global _analytics_service
    if _analytics_service is None:
        _analytics_service = WinnersAnalyticsService()
    return _analytics_service
