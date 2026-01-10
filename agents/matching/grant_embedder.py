"""
Grant Embedding Generator
Generates vector embeddings for grants to enable similarity matching.
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

logger = structlog.get_logger().bind(agent="grant_embedder")


class GrantEmbedder:
    """
    Generates embeddings for grant opportunities.

    Uses OpenAI text-embedding-3-small (1536 dimensions) to create
    vector representations of grants for similarity matching.
    """

    EMBEDDING_MODEL = "text-embedding-3-small"
    EMBEDDING_DIMENSIONS = 1536
    BATCH_SIZE = 100  # Process grants in batches

    def __init__(self, db_engine: Engine):
        """
        Initialize grant embedder.

        Args:
            db_engine: SQLAlchemy engine for database operations.
        """
        self.db_engine = db_engine
        self.openai_client = openai.OpenAI(api_key=settings.openai_api_key)

    def _grant_to_text(self, grant: dict[str, Any]) -> str:
        """
        Convert grant data to text for embedding.

        Args:
            grant: Grant data dictionary.

        Returns:
            Formatted text representation.
        """
        parts = []

        # Title is most important
        if grant.get("title"):
            parts.append(f"Title: {grant['title']}")

        # Agency/funder
        if grant.get("agency"):
            parts.append(f"Agency: {grant['agency']}")

        # Description/abstract
        if grant.get("description"):
            desc = grant["description"]
            # Truncate if too long
            if len(desc) > 4000:
                desc = desc[:4000] + "..."
            parts.append(f"Description: {desc}")

        # Categories/research areas
        if grant.get("categories"):
            cats = grant["categories"]
            if isinstance(cats, list):
                parts.append(f"Categories: {', '.join(cats)}")

        # Eligibility
        if grant.get("eligibility"):
            elig = grant["eligibility"]
            if isinstance(elig, dict):
                if elig.get("applicant_types"):
                    parts.append(f"Eligible Applicants: {', '.join(elig['applicant_types'])}")
            elif isinstance(elig, str):
                parts.append(f"Eligibility: {elig}")

        # Funding amount
        if grant.get("amount_min") or grant.get("amount_max"):
            amount_parts = []
            if grant.get("amount_min"):
                amount_parts.append(f"${grant['amount_min']:,}")
            if grant.get("amount_max") and grant.get("amount_max") != grant.get("amount_min"):
                amount_parts.append(f"${grant['amount_max']:,}")
            if amount_parts:
                parts.append(f"Funding: {' - '.join(amount_parts)}")

        return "\n".join(parts)

    def _compute_text_hash(self, text: str) -> str:
        """
        Compute SHA-256 hash of text for cache invalidation.

        Args:
            text: Text to hash.

        Returns:
            Hex digest of hash.
        """
        return hashlib.sha256(text.encode()).hexdigest()

    def _generate_embedding(self, text: str) -> list[float]:
        """
        Generate embedding using OpenAI API.

        Args:
            text: Text to embed.

        Returns:
            Embedding vector (1536 dimensions).
        """
        response = self.openai_client.embeddings.create(
            model=self.EMBEDDING_MODEL,
            input=text,
        )
        return response.data[0].embedding

    def _generate_embeddings_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for multiple texts in one API call.

        Args:
            texts: List of texts to embed.

        Returns:
            List of embedding vectors.
        """
        response = self.openai_client.embeddings.create(
            model=self.EMBEDDING_MODEL,
            input=texts,
        )
        return [item.embedding for item in response.data]

    def needs_embedding(self, grant_id: UUID, session: Session) -> bool:
        """
        Check if a grant needs embedding generation.

        Args:
            grant_id: Grant identifier.
            session: Database session.

        Returns:
            True if embedding should be generated.
        """
        query = text("""
            SELECT embedding IS NULL as needs_embedding
            FROM grants
            WHERE id = :grant_id
        """)
        result = session.execute(query, {"grant_id": str(grant_id)}).fetchone()

        if not result:
            return False

        return result.needs_embedding

    def build_embedding(self, grant_id: UUID, force: bool = False) -> Optional[dict[str, Any]]:
        """
        Generate and store embedding for a single grant.

        Args:
            grant_id: Grant identifier.
            force: Force regeneration even if embedding exists.

        Returns:
            Embedding metadata if successful, None otherwise.
        """
        with Session(self.db_engine) as session:
            # Fetch grant data
            query = text("""
                SELECT id, title, description, agency,
                       amount_min, amount_max, categories, eligibility,
                       embedding IS NOT NULL as has_embedding
                FROM grants
                WHERE id = :grant_id
            """)
            result = session.execute(query, {"grant_id": str(grant_id)}).fetchone()

            if not result:
                logger.warning("grant_not_found", grant_id=str(grant_id))
                return None

            # Check if we need to generate
            if result.has_embedding and not force:
                logger.debug(
                    "embedding_exists",
                    grant_id=str(grant_id),
                )
                return None

            # Convert to dict for text generation
            grant_data = {
                "title": result.title,
                "description": result.description,
                "agency": result.agency,
                "amount_min": result.amount_min,
                "amount_max": result.amount_max,
                "categories": result.categories,
                "eligibility": result.eligibility,
            }

            # Generate embedding text
            embedding_text = self._grant_to_text(grant_data)

            if not embedding_text.strip():
                logger.warning(
                    "empty_grant_text",
                    grant_id=str(grant_id),
                )
                return None

            # Generate embedding
            embedding = self._generate_embedding(embedding_text)

            # Store embedding
            embedding_str = "[" + ",".join(map(str, embedding)) + "]"
            update_query = text("""
                UPDATE grants
                SET embedding = CAST(:embedding AS vector)
                WHERE id = :grant_id
            """)
            session.execute(update_query, {"grant_id": str(grant_id), "embedding": embedding_str})
            session.commit()

            logger.info(
                "embedding_generated",
                grant_id=str(grant_id),
                dimensions=len(embedding),
            )

            return {
                "grant_id": str(grant_id),
                "dimensions": len(embedding),
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }

    def build_embeddings_batch(
        self,
        grant_ids: list[UUID],
        force: bool = False,
    ) -> dict[str, Any]:
        """
        Generate embeddings for multiple grants.

        Args:
            grant_ids: List of grant identifiers.
            force: Force regeneration even if embeddings exist.

        Returns:
            Statistics about the batch operation.
        """
        stats = {
            "requested": len(grant_ids),
            "processed": 0,
            "generated": 0,
            "skipped": 0,
            "errors": 0,
        }

        with Session(self.db_engine) as session:
            # Fetch grants that need embeddings
            query = text("""
                SELECT id, title, description, agency,
                       amount_min, amount_max, categories, eligibility,
                       embedding IS NOT NULL as has_embedding
                FROM grants
                WHERE id = ANY(CAST(:grant_ids AS uuid[]))
            """)
            results = session.execute(query, {"grant_ids": [str(gid) for gid in grant_ids]}).fetchall()

            # Filter to those needing embeddings
            grants_to_process = []
            for row in results:
                if row.has_embedding and not force:
                    stats["skipped"] += 1
                    continue

                grant_data = {
                    "id": row.id,
                    "title": row.title,
                    "description": row.description,
                    "agency": row.agency,
                    "amount_min": row.amount_min,
                    "amount_max": row.amount_max,
                    "categories": row.categories,
                    "eligibility": row.eligibility,
                }
                grants_to_process.append(grant_data)

            # Process in batches
            for i in range(0, len(grants_to_process), self.BATCH_SIZE):
                batch = grants_to_process[i : i + self.BATCH_SIZE]

                try:
                    # Generate texts
                    texts = [self._grant_to_text(g) for g in batch]

                    # Generate embeddings
                    embeddings = self._generate_embeddings_batch(texts)

                    # Store embeddings
                    for grant, embedding in zip(batch, embeddings):
                        embedding_str = "[" + ",".join(map(str, embedding)) + "]"
                        update_query = text("""
                            UPDATE grants
                            SET embedding = CAST(:embedding AS vector)
                            WHERE id = :grant_id
                        """)
                        session.execute(
                            update_query,
                            {
                                "grant_id": str(grant["id"]),
                                "embedding": embedding_str,
                            },
                        )
                        stats["generated"] += 1

                    session.commit()
                    stats["processed"] += len(batch)

                except Exception as e:
                    logger.error(
                        "batch_embedding_failed",
                        batch_start=i,
                        error=str(e),
                    )
                    stats["errors"] += len(batch)

        logger.info("batch_embedding_complete", **stats)
        return stats

    def rebuild_missing_embeddings(self) -> dict[str, Any]:
        """
        Generate embeddings for all grants that don't have them.

        Returns:
            Statistics about the rebuild operation.
        """
        with Session(self.db_engine) as session:
            # Get grants without embeddings
            query = text("""
                SELECT id FROM grants
                WHERE embedding IS NULL
                ORDER BY created_at DESC
            """)
            results = session.execute(query).fetchall()
            grant_ids = [UUID(str(row.id)) for row in results]

        if not grant_ids:
            logger.info("no_grants_need_embeddings")
            return {
                "total_grants": 0,
                "embeddings_generated": 0,
                "errors": 0,
            }

        logger.info(
            "rebuilding_embeddings",
            grants_count=len(grant_ids),
        )

        return self.build_embeddings_batch(grant_ids, force=True)

    def rebuild_all_embeddings(self) -> dict[str, Any]:
        """
        Regenerate embeddings for all grants.

        Use with caution - this will regenerate all embeddings.

        Returns:
            Statistics about the rebuild operation.
        """
        with Session(self.db_engine) as session:
            query = text("SELECT id FROM grants ORDER BY created_at DESC")
            results = session.execute(query).fetchall()
            grant_ids = [UUID(str(row.id)) for row in results]

        if not grant_ids:
            logger.info("no_grants_found")
            return {
                "total_grants": 0,
                "embeddings_generated": 0,
                "errors": 0,
            }

        logger.info(
            "rebuilding_all_embeddings",
            grants_count=len(grant_ids),
        )

        return self.build_embeddings_batch(grant_ids, force=True)
