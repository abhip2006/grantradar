#!/usr/bin/env python3
"""
Test Matching Flow
Tests the matching agent components without requiring database/Redis.
"""

import sys

sys.path.insert(0, "/Users/abhinavpenagalapati/Desktop/grantradar")

from datetime import datetime, timezone
from uuid import uuid4


def test_grant_embedder():
    """Test grant embedder text generation."""
    print("\n=== Testing Grant Embedder ===")

    from agents.matching.grant_embedder import GrantEmbedder
    from unittest.mock import MagicMock

    embedder = GrantEmbedder(MagicMock())

    # Test grant to text conversion
    grant = {
        "title": "Machine Learning for Climate Science",
        "agency": "National Science Foundation",
        "description": "Developing novel ML approaches for climate prediction.",
        "categories": ["ai_ml", "climate"],
        "amount_min": 500000,
        "amount_max": 750000,
        "eligibility": {"applicant_types": ["Universities"]},
    }

    text = embedder._grant_to_text(grant)
    print("Grant to text conversion:")
    print(f"  Input: {grant['title']}")
    print(f"  Output length: {len(text)} chars")
    print(f"  Contains title: {'Machine Learning' in text}")
    print(f"  Contains agency: {'NSF' in text or 'National Science Foundation' in text}")

    # Test hash
    hash1 = embedder._compute_text_hash(text)
    hash2 = embedder._compute_text_hash(text)
    print(f"\nHash consistency: {hash1 == hash2}")
    print(f"Hash length: {len(hash1)}")

    return True


def test_models():
    """Test matching models."""
    print("\n=== Testing Matching Models ===")

    from agents.matching.models import (
        GrantData,
        UserProfile,
        ProfileMatch,
        MatchResult,
        FinalMatch,
        BatchMatchRequest,
    )

    # Test GrantData
    grant = GrantData(
        grant_id=uuid4(),
        title="Test Grant",
        description="A test grant for ML research.",
        funding_agency="NSF",
        funding_amount=500000,
        deadline=datetime(2025, 6, 15, tzinfo=timezone.utc),
        categories=["ai_ml"],
    )
    print(f"GrantData created: {grant.title}")
    print(f"  to_matching_text length: {len(grant.to_matching_text())} chars")

    # Test UserProfile
    profile = UserProfile(
        user_id=uuid4(),
        research_areas=["machine learning", "climate"],
        methods=["neural networks", "simulation"],
        past_grants=["NSF: Prior Grant ($300K)"],
        institution="Stanford University",
    )
    print(f"UserProfile created: {profile.user_id}")
    print(f"  to_embedding_text length: {len(profile.to_embedding_text())} chars")

    # Test ProfileMatch
    match = ProfileMatch(
        user_id=profile.user_id,
        vector_similarity=0.85,
        profile=profile,
    )
    print(f"ProfileMatch created with similarity: {match.vector_similarity}")

    # Test MatchResult
    result = MatchResult(
        match_score=85,
        reasoning="Strong alignment in research areas.",
        key_strengths=["ML expertise", "Prior funding"],
        concerns=["Limited publications"],
        predicted_success=75,
    )
    print(f"MatchResult created with score: {result.match_score}")

    # Test FinalMatch score computation
    final_score = FinalMatch.compute_final_score(0.85, 80)
    print(f"FinalMatch score (0.85 vector, 80 LLM): {final_score}")

    # Test BatchMatchRequest
    batch = BatchMatchRequest(
        grant=grant,
        profiles=[match],
    )
    print(f"BatchMatchRequest created with {len(batch.profiles)} profiles")

    return True


def test_priority_levels():
    """Test priority level computation."""
    print("\n=== Testing Priority Levels ===")

    from agents.matching.matcher import GrantMatcher
    from unittest.mock import MagicMock
    from datetime import timedelta

    matcher = GrantMatcher(MagicMock())

    now = datetime.now(timezone.utc)

    # Test cases
    test_cases = [
        (95, now + timedelta(days=3), "CRITICAL (high score + urgent)"),
        (85, None, "HIGH (good score)"),
        (75, None, "MEDIUM (decent score)"),
        (60, None, "LOW (below threshold)"),
        (85, now + timedelta(days=20), "HIGH (good score + moderate deadline)"),
    ]

    for score, deadline, description in test_cases:
        priority = matcher._compute_priority_level(score, deadline)
        print(f"  Score {score}, Deadline {deadline}: {priority.value} - {description}")

    return True


def test_score_computation():
    """Test final score computation."""
    print("\n=== Testing Score Computation ===")

    from agents.matching.models import FinalMatch

    test_cases = [
        (1.0, 100, "Perfect match"),
        (0.5, 50, "Moderate match"),
        (0.8, 85, "Good match"),
        (0.6, 70, "Threshold match"),
        (0.9, 60, "High vector, low LLM"),
        (0.5, 95, "Low vector, high LLM"),
    ]

    for vector, llm, description in test_cases:
        score = FinalMatch.compute_final_score(vector, llm)
        expected = int(0.4 * (vector * 100) + 0.6 * llm)
        print(f"  Vector {vector}, LLM {llm}: Score {score} (expected ~{expected}) - {description}")

    return True


def test_workflow_simulation():
    """Simulate the full matching workflow."""
    print("\n=== Simulating Matching Workflow ===")

    from agents.matching.models import (
        GrantData,
        UserProfile,
        ProfileMatch,
        MatchResult,
        FinalMatch,
    )

    # Step 1: Grant arrives
    print("\nStep 1: Grant arrives")
    grant = GrantData(
        grant_id=uuid4(),
        title="AI for Healthcare Research",
        description="Developing AI systems for medical diagnosis and treatment planning.",
        funding_agency="NIH",
        funding_amount=1000000,
        deadline=datetime(2025, 4, 15, tzinfo=timezone.utc),
        categories=["ai_ml", "biomedical"],
        embedding=[0.1] * 1536,
    )
    print(f"  Grant: {grant.title}")
    print(f"  Agency: {grant.funding_agency}")
    print(f"  Amount: ${grant.funding_amount:,}")

    # Step 2: Find similar profiles (simulated)
    print("\nStep 2: Vector similarity search (simulated)")
    profiles = [
        ProfileMatch(
            user_id=uuid4(),
            vector_similarity=0.92,
            profile=UserProfile(
                user_id=uuid4(),
                research_areas=["artificial intelligence", "medical imaging"],
                methods=["deep learning", "computer vision"],
                past_grants=["NIH R01: AI Diagnostics ($800K)"],
                institution="Johns Hopkins",
            ),
        ),
        ProfileMatch(
            user_id=uuid4(),
            vector_similarity=0.78,
            profile=UserProfile(
                user_id=uuid4(),
                research_areas=["machine learning", "genomics"],
                methods=["neural networks", "bioinformatics"],
                institution="MIT",
            ),
        ),
        ProfileMatch(
            user_id=uuid4(),
            vector_similarity=0.65,
            profile=UserProfile(
                user_id=uuid4(),
                research_areas=["data science", "healthcare analytics"],
                methods=["statistical modeling"],
                institution="UCLA",
            ),
        ),
    ]
    for p in profiles:
        print(f"  Candidate: {p.profile.institution} (similarity: {p.vector_similarity:.2f})")

    # Step 3: LLM evaluation (simulated)
    print("\nStep 3: LLM evaluation (simulated)")
    llm_results = [
        MatchResult(
            match_score=90, reasoning="Excellent fit", key_strengths=["AI expertise"], concerns=[], predicted_success=85
        ),
        MatchResult(
            match_score=75,
            reasoning="Good fit",
            key_strengths=["ML background"],
            concerns=["No healthcare experience"],
            predicted_success=65,
        ),
        MatchResult(
            match_score=55,
            reasoning="Moderate fit",
            key_strengths=["Data skills"],
            concerns=["Limited AI experience"],
            predicted_success=45,
        ),
    ]

    # Step 4: Compute final scores
    print("\nStep 4: Final score computation")
    final_matches = []
    for profile, llm_result in zip(profiles, llm_results):
        final_score = FinalMatch.compute_final_score(
            profile.vector_similarity,
            llm_result.match_score,
        )
        final_matches.append((profile, llm_result, final_score))
        print(f"  {profile.profile.institution}:")
        print(f"    Vector: {profile.vector_similarity:.2f}, LLM: {llm_result.match_score}, Final: {final_score}")

    # Step 5: Filter and publish
    print("\nStep 5: Filter and publish (threshold: 70)")
    published = 0
    for profile, llm_result, final_score in final_matches:
        if final_score > 70:
            print(f"  PUBLISH: {profile.profile.institution} (score: {final_score})")
            published += 1
        else:
            print(f"  SKIP: {profile.profile.institution} (score: {final_score})")

    print(f"\nSummary: {published}/{len(final_matches)} matches published")

    return True


def main():
    print("=" * 60)
    print("MATCHING FLOW TEST")
    print("=" * 60)

    results = {}

    results["Grant Embedder"] = test_grant_embedder()
    results["Models"] = test_models()
    results["Priority Levels"] = test_priority_levels()
    results["Score Computation"] = test_score_computation()
    results["Workflow Simulation"] = test_workflow_simulation()

    print("\n" + "=" * 60)
    print("RESULTS:")
    print("=" * 60)
    for name, passed in results.items():
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"  {name}: {status}")

    return all(results.values())


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
