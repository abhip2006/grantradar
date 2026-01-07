"""
Profile Builder
Generates and manages user profile embeddings for grant matching.
"""
import hashlib
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

import openai
import structlog
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from backend.core.config import settings

from .models import ProfileEmbedding, UserProfile

logger = structlog.get_logger().bind(agent="profile_builder")


class ProfileBuilder:
    """
    Builds and manages user profile embeddings.

    Handles:
    - Profile text generation from user onboarding data
    - Embedding generation via OpenAI text-embedding-3-small
    - Storage in lab_profiles.profile_embedding column
    - Cache invalidation based on profile changes
    """

    def __init__(self, db_engine: Engine):
        """
        Initialize profile builder.

        Args:
            db_engine: SQLAlchemy engine for database operations.
        """
        self.db_engine = db_engine
        self.openai_client = openai.OpenAI(api_key=settings.openai_api_key)
        self.embedding_model = settings.embedding_model
        self.embedding_dimensions = settings.embedding_dimensions

    def _compute_text_hash(self, text: str) -> str:
        """
        Compute hash of profile text for cache invalidation.

        Args:
            text: Profile text to hash.

        Returns:
            SHA-256 hash of the text.
        """
        return hashlib.sha256(text.encode()).hexdigest()

    def _generate_embedding(self, text: str) -> list[float]:
        """
        Generate embedding vector using OpenAI.

        Args:
            text: Text to embed.

        Returns:
            Embedding vector (1536 dimensions).

        Raises:
            openai.OpenAIError: If API call fails.
        """
        response = self.openai_client.embeddings.create(
            model=self.embedding_model,
            input=text,
            dimensions=self.embedding_dimensions,
        )
        return response.data[0].embedding

    def _generate_embeddings_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for multiple texts in a single API call.

        Args:
            texts: List of texts to embed.

        Returns:
            List of embedding vectors.

        Raises:
            openai.OpenAIError: If API call fails.
        """
        if not texts:
            return []

        response = self.openai_client.embeddings.create(
            model=self.embedding_model,
            input=texts,
            dimensions=self.embedding_dimensions,
        )

        # Sort by index to ensure correct ordering
        sorted_data = sorted(response.data, key=lambda x: x.index)
        return [item.embedding for item in sorted_data]

    def fetch_user_profile(self, user_id: UUID, session: Session) -> Optional[UserProfile]:
        """
        Fetch user profile data from database.

        Args:
            user_id: User identifier.
            session: Database session.

        Returns:
            UserProfile if found, None otherwise.
        """
        query = text("""
            SELECT
                user_id,
                research_areas,
                methods,
                past_grants,
                institution,
                department,
                keywords
            FROM lab_profiles
            WHERE user_id = :user_id
        """)

        result = session.execute(query, {"user_id": str(user_id)}).fetchone()

        if not result:
            logger.warning("user_profile_not_found", user_id=str(user_id))
            return None

        return UserProfile(
            user_id=user_id,
            research_areas=result.research_areas or [],
            methods=result.methods or [],
            past_grants=result.past_grants or [],
            institution=result.institution,
            department=result.department,
            keywords=result.keywords or [],
        )

    def get_current_embedding_hash(
        self, user_id: UUID, session: Session
    ) -> Optional[str]:
        """
        Get the current embedding source text hash.

        Args:
            user_id: User identifier.
            session: Database session.

        Returns:
            Current hash if exists, None otherwise.
        """
        query = text("""
            SELECT source_text_hash
            FROM lab_profiles
            WHERE user_id = :user_id
        """)

        result = session.execute(query, {"user_id": str(user_id)}).fetchone()

        if result:
            return result.source_text_hash
        return None

    def needs_update(
        self, profile: UserProfile, session: Session
    ) -> bool:
        """
        Check if profile embedding needs regeneration.

        Args:
            profile: User profile data.
            session: Database session.

        Returns:
            True if embedding should be regenerated.
        """
        profile_text = profile.to_embedding_text()
        new_hash = self._compute_text_hash(profile_text)
        current_hash = self.get_current_embedding_hash(profile.user_id, session)

        return new_hash != current_hash

    def build_embedding(
        self, user_id: UUID, force: bool = False
    ) -> Optional[ProfileEmbedding]:
        """
        Build embedding for a user profile.

        Args:
            user_id: User identifier.
            force: Force regeneration even if unchanged.

        Returns:
            ProfileEmbedding if successful, None otherwise.
        """
        with Session(self.db_engine) as session:
            # Fetch profile data
            profile = self.fetch_user_profile(user_id, session)
            if not profile:
                return None

            # Check if update needed
            if not force and not self.needs_update(profile, session):
                logger.info(
                    "embedding_up_to_date",
                    user_id=str(user_id),
                )
                return None

            # Generate embedding text
            profile_text = profile.to_embedding_text()
            if not profile_text.strip():
                logger.warning(
                    "empty_profile_text",
                    user_id=str(user_id),
                )
                return None

            # Generate embedding
            try:
                embedding = self._generate_embedding(profile_text)
            except openai.OpenAIError as e:
                logger.error(
                    "embedding_generation_failed",
                    user_id=str(user_id),
                    error=str(e),
                )
                raise

            # Create embedding object
            text_hash = self._compute_text_hash(profile_text)
            profile_embedding = ProfileEmbedding(
                user_id=user_id,
                embedding=embedding,
                created_at=datetime.now(timezone.utc),
                source_text_hash=text_hash,
            )

            # Store in database
            self._store_embedding(profile_embedding, session)
            session.commit()

            logger.info(
                "embedding_generated",
                user_id=str(user_id),
                text_length=len(profile_text),
                embedding_dims=len(embedding),
            )

            return profile_embedding

    def build_embeddings_batch(
        self, user_ids: list[UUID], force: bool = False
    ) -> list[ProfileEmbedding]:
        """
        Build embeddings for multiple users in batch.

        More efficient than individual calls when processing many users.

        Args:
            user_ids: List of user identifiers.
            force: Force regeneration even if unchanged.

        Returns:
            List of successfully generated ProfileEmbeddings.
        """
        results = []

        with Session(self.db_engine) as session:
            # Fetch all profiles
            profiles_to_process: list[tuple[UserProfile, str]] = []

            for user_id in user_ids:
                profile = self.fetch_user_profile(user_id, session)
                if not profile:
                    continue

                if not force and not self.needs_update(profile, session):
                    continue

                profile_text = profile.to_embedding_text()
                if profile_text.strip():
                    profiles_to_process.append((profile, profile_text))

            if not profiles_to_process:
                return results

            # Generate embeddings in batch
            texts = [text for _, text in profiles_to_process]
            try:
                embeddings = self._generate_embeddings_batch(texts)
            except openai.OpenAIError as e:
                logger.error(
                    "batch_embedding_generation_failed",
                    count=len(texts),
                    error=str(e),
                )
                raise

            # Process results
            for (profile, profile_text), embedding in zip(
                profiles_to_process, embeddings
            ):
                text_hash = self._compute_text_hash(profile_text)
                profile_embedding = ProfileEmbedding(
                    user_id=profile.user_id,
                    embedding=embedding,
                    created_at=datetime.now(timezone.utc),
                    source_text_hash=text_hash,
                )

                self._store_embedding(profile_embedding, session)
                results.append(profile_embedding)

            session.commit()

            logger.info(
                "batch_embeddings_generated",
                count=len(results),
            )

        return results

    def _store_embedding(
        self, profile_embedding: ProfileEmbedding, session: Session
    ) -> None:
        """
        Store embedding in database.

        Args:
            profile_embedding: Embedding to store.
            session: Database session.
        """
        # Convert embedding to pgvector format
        embedding_str = "[" + ",".join(map(str, profile_embedding.embedding)) + "]"

        query = text("""
            UPDATE lab_profiles
            SET
                profile_embedding = :embedding::vector,
                source_text_hash = :source_text_hash,
                embedding_updated_at = :updated_at
            WHERE user_id = :user_id
        """)

        session.execute(
            query,
            {
                "user_id": str(profile_embedding.user_id),
                "embedding": embedding_str,
                "source_text_hash": profile_embedding.source_text_hash,
                "updated_at": profile_embedding.created_at,
            },
        )

    def rebuild_all_embeddings(self) -> dict[str, Any]:
        """
        Rebuild embeddings for all users.

        Use for initial setup or full reindexing.

        Returns:
            Statistics about the rebuild operation.
        """
        stats = {
            "total_users": 0,
            "embeddings_generated": 0,
            "errors": 0,
            "skipped": 0,
        }

        with Session(self.db_engine) as session:
            # Get all user IDs
            query = text("SELECT user_id FROM lab_profiles")
            results = session.execute(query).fetchall()
            user_ids = [UUID(row.user_id) for row in results]
            stats["total_users"] = len(user_ids)

        # Process in batches of 100
        batch_size = 100
        for i in range(0, len(user_ids), batch_size):
            batch = user_ids[i : i + batch_size]
            try:
                embeddings = self.build_embeddings_batch(batch, force=True)
                stats["embeddings_generated"] += len(embeddings)
                stats["skipped"] += len(batch) - len(embeddings)
            except Exception as e:
                logger.error(
                    "batch_rebuild_failed",
                    batch_start=i,
                    error=str(e),
                )
                stats["errors"] += len(batch)

        logger.info("rebuild_complete", stats=stats)
        return stats


# Celery task for profile embedding generation
def create_profile_builder_task(db_engine: Engine):
    """
    Factory function to create profile builder Celery task.

    Args:
        db_engine: SQLAlchemy engine.

    Returns:
        Configured ProfileBuilder instance.
    """
    return ProfileBuilder(db_engine)
