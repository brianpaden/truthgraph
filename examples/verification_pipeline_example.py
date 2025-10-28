"""Example usage of the Verification Pipeline Service.

This script demonstrates how to use the VerificationPipelineService
for end-to-end claim verification.
"""

import asyncio
import sys
from pathlib import Path
from uuid import uuid4

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from truthgraph.db import Base
from truthgraph.schemas import Claim, Evidence
from truthgraph.services.verification_pipeline_service import (
    VerificationPipelineService,
)


def setup_demo_database(db_url: str):
    """Set up demo database with sample evidence.

    Args:
        db_url: Database connection URL

    Returns:
        Tuple of (engine, SessionLocal)
    """
    engine = create_engine(db_url, echo=False)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)

    session = SessionLocal()

    # Create sample evidence
    sample_evidence = [
        Evidence(
            id=uuid4(),
            content=(
                "The Earth orbits the Sun in an elliptical path, completing "
                "one full revolution approximately every 365.25 days. This "
                "heliocentric model was confirmed by observations from "
                "astronomers like Copernicus and Galileo."
            ),
            source_url="https://science.nasa.gov/solar-system/earth",
            source_type="nasa_article",
        ),
        Evidence(
            id=uuid4(),
            content=(
                "Water is composed of two hydrogen atoms covalently bonded "
                "to one oxygen atom, giving it the chemical formula H₂O. "
                "This molecular structure gives water its unique properties."
            ),
            source_url="https://chemistry.example.com/water",
            source_type="chemistry_textbook",
        ),
        Evidence(
            id=uuid4(),
            content=(
                "The speed of light in a vacuum is exactly 299,792,458 meters "
                "per second (approximately 300,000 km/s). This is a fundamental "
                "constant in physics and serves as the basis for the definition "
                "of the meter."
            ),
            source_url="https://physics.example.com/constants",
            source_type="physics_reference",
        ),
        Evidence(
            id=uuid4(),
            content=(
                "Python is a high-level, interpreted programming language known "
                "for its clear syntax and readability. Created by Guido van Rossum "
                "and first released in 1991, it has become one of the most popular "
                "programming languages."
            ),
            source_url="https://www.python.org/about/",
            source_type="official_documentation",
        ),
        Evidence(
            id=uuid4(),
            content=(
                "The Great Wall of China is not visible from space with the naked eye, "
                "contrary to popular belief. While it is an impressive structure, "
                "it is too narrow to be distinguished from orbit without aid."
            ),
            source_url="https://space.example.com/myths",
            source_type="space_fact_check",
        ),
    ]

    for evidence in sample_evidence:
        session.add(evidence)

    session.commit()
    print(f"Added {len(sample_evidence)} evidence items to database")

    session.close()

    return engine, SessionLocal


async def verify_claim_example(
    service: VerificationPipelineService,
    session,
    claim_text: str,
    use_cache: bool = True,
):
    """Verify a single claim and print results.

    Args:
        service: Verification pipeline service
        session: Database session
        claim_text: Claim text to verify
        use_cache: Whether to use caching
    """
    print("\n" + "=" * 80)
    print(f"CLAIM: {claim_text}")
    print("=" * 80)

    # Create claim record
    claim = Claim(id=uuid4(), text=claim_text)
    session.add(claim)
    session.commit()

    # Verify claim
    result = await service.verify_claim(
        db=session,
        claim_id=claim.id,
        claim_text=claim_text,
        top_k_evidence=5,
        min_similarity=0.3,
        use_cache=use_cache,
        store_result=False,  # Don't store for demo
    )

    # Print results
    print(f"\nVERDICT: {result.verdict.value}")
    print(f"Confidence: {result.confidence:.2%}")
    print(f"Pipeline Duration: {result.pipeline_duration_ms:.0f}ms")
    print()
    print("Scores:")
    print(f"  Support:  {result.support_score:.2%}")
    print(f"  Refute:   {result.refute_score:.2%}")
    print(f"  Neutral:  {result.neutral_score:.2%}")
    print()
    print(f"Evidence Analyzed: {len(result.evidence_items)}")

    if result.evidence_items:
        print("\nTop Evidence:")
        for i, item in enumerate(result.evidence_items[:3], 1):
            print(
                f"\n  [{i}] Similarity: {item.similarity:.2%} | NLI: {item.nli_label.value} ({item.nli_confidence:.2%})"
            )
            print(f"      {item.content[:100]}...")

    print()
    print("Reasoning:")
    print(f"  {result.reasoning}")
    print()


async def main():
    """Main entry point for example."""
    print("=" * 80)
    print("Verification Pipeline Service - Example Usage")
    print("=" * 80)

    # Database setup
    db_url = "postgresql+psycopg://truthgraph:changeme@localhost:5432/truthgraph_demo"
    print(f"\nDatabase: {db_url}")
    print("\nSetting up demo database...")

    try:
        engine, SessionLocal = setup_demo_database(db_url)
    except Exception as e:
        print(f"\nError setting up database: {e}")
        print("\nNote: This example requires a PostgreSQL database with pgvector.")
        print("Update the db_url in the script to match your setup.")
        return

    # Initialize service
    print("\nInitializing verification pipeline service...")
    service = VerificationPipelineService(embedding_dimension=384)
    print("Service initialized!")

    # Example claims to verify
    claims = [
        "The Earth orbits around the Sun",
        "Water is made of hydrogen and oxygen",
        "The speed of light is about 300,000 kilometers per second",
        "Python is a programming language",
        "The Great Wall of China is visible from space",
        "The moon is made of cheese",  # False claim
    ]

    # Verify each claim
    for claim_text in claims:
        session = SessionLocal()
        try:
            await verify_claim_example(
                service=service,
                session=session,
                claim_text=claim_text,
                use_cache=True,
            )
        except Exception as e:
            print(f"\nError verifying claim: {e}")
        finally:
            session.close()

    # Demonstrate caching
    print("\n" + "=" * 80)
    print("DEMONSTRATING CACHE")
    print("=" * 80)
    print("\nRe-verifying first claim to show cache hit...")

    session = SessionLocal()
    try:
        await verify_claim_example(
            service=service,
            session=session,
            claim_text=claims[0],
            use_cache=True,
        )
    finally:
        session.close()

    # Cleanup
    print("\nCleaning up...")
    Base.metadata.drop_all(engine)
    engine.dispose()
    print("Done!")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nExample interrupted by user")
    except Exception as e:
        print(f"\n\nExample failed with error: {e}")
        import traceback

        traceback.print_exc()
