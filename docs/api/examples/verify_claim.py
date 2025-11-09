"""TruthGraph API - Python Examples

This module demonstrates how to use the TruthGraph verification API
with httpx for async HTTP requests.

Requirements:
    pip install httpx

Usage:
    python verify_claim.py
"""

import asyncio
import time
from typing import Optional

import httpx


BASE_URL = "http://localhost:8000"


async def health_check():
    """Check API health status."""
    print("=" * 60)
    print("1. Health Check")
    print("=" * 60)

    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/health")
        health = response.json()

        print(f"Status: {health['status']}")
        print(f"Version: {health['version']}")
        print("\nServices:")
        for service, status in health["services"].items():
            print(f"  - {service}: {status['status']}")

    print()


async def simple_verify():
    """Simple synchronous verification."""
    print("=" * 60)
    print("2. Simple Synchronous Verification")
    print("=" * 60)

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/api/v1/verify",
            json={
                "claim": "The Earth orbits the Sun",
                "max_evidence": 5,
                "confidence_threshold": 0.7,
            },
        )

        if response.status_code == 200:
            result = response.json()
            print(f"Verdict: {result['verdict']}")
            print(f"Confidence: {result['confidence']:.2%}")
            print(f"Evidence count: {len(result['evidence'])}")
            print(f"Explanation: {result['explanation']}")
            print(f"Processing time: {result['processing_time_ms']:.2f}ms")
        else:
            print(f"Error: {response.status_code}")
            print(response.json())

    print()


async def async_verify_with_polling(claim_id: str, claim_text: str):
    """Async verification with smart polling."""
    print("=" * 60)
    print("3. Async Verification with Polling")
    print("=" * 60)

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Trigger verification
        print(f"Triggering verification for: {claim_id}")
        response = await client.post(
            f"{BASE_URL}/api/v1/claims/{claim_id}/verify",
            json={
                "claim_id": claim_id,
                "claim_text": claim_text,
                "options": {
                    "max_evidence_items": 5,
                    "confidence_threshold": 0.7,
                    "return_reasoning": True,
                },
            },
        )

        task_data = response.json()
        task_id = task_data["task_id"]
        print(f"Task created: {task_id}")
        print(f"Status: {task_data['status']}")
        print()

        # Poll for result with exponential backoff
        print("Polling for result...")
        delay = 1
        max_attempts = 30

        for attempt in range(1, max_attempts + 1):
            # Check verdict endpoint
            verdict_response = await client.get(
                f"{BASE_URL}/api/v1/verdicts/{claim_id}"
            )

            if verdict_response.status_code == 200:
                # Verification complete
                result = verdict_response.json()
                print(f"\n✓ Verification complete (attempt {attempt})")
                print(f"  Claim: {result['claim_text']}")
                print(f"  Verdict: {result['verdict']}")
                print(f"  Confidence: {result['confidence']:.2%}")
                print(f"  Evidence count: {len(result['evidence'])}")
                print(f"  Processing time: {result['processing_time_ms']}ms")

                if result.get("reasoning"):
                    print(f"  Reasoning: {result['reasoning']}")

                return result

            elif verdict_response.status_code == 202:
                # Still processing
                print(f"  Attempt {attempt}: Still processing... (waiting {delay}s)")
                await asyncio.sleep(delay)
                delay = min(delay * 1.5, 10)  # Exponential backoff, cap at 10s

            else:
                # Error
                print(f"  Error: {verdict_response.status_code}")
                print(f"  {verdict_response.json()}")
                return None

        print(f"\n✗ Timeout after {max_attempts} attempts")
        return None

    print()


async def task_status_polling(task_id: str):
    """Poll task status endpoint."""
    print("=" * 60)
    print("4. Task Status Polling")
    print("=" * 60)

    async with httpx.AsyncClient() as client:
        max_attempts = 10

        for attempt in range(1, max_attempts + 1):
            response = await client.get(f"{BASE_URL}/api/v1/tasks/{task_id}")

            if response.status_code == 200:
                task = response.json()
                print(f"Attempt {attempt}:")
                print(f"  Status: {task['status']}")
                print(f"  Progress: {task.get('progress_percentage', 0)}%")

                if task["status"] == "completed":
                    print(f"  ✓ Task completed!")
                    print(f"  Verdict: {task['result']['verdict']}")
                    break
                elif task["status"] == "failed":
                    print(f"  ✗ Task failed: {task['error']}")
                    break

                await asyncio.sleep(2)
            else:
                print(f"Error: {response.status_code}")
                break

    print()


async def generate_embeddings():
    """Generate text embeddings."""
    print("=" * 60)
    print("5. Generate Embeddings")
    print("=" * 60)

    async with httpx.AsyncClient() as client:
        texts = [
            "The Earth orbits the Sun",
            "Water freezes at 0 degrees Celsius",
            "Python is a programming language",
        ]

        response = await client.post(
            f"{BASE_URL}/api/v1/embed",
            json={"texts": texts, "batch_size": 32},
        )

        data = response.json()
        print(f"Generated {data['count']} embeddings")
        print(f"Dimension: {data['dimension']}")
        print(f"Processing time: {data['processing_time_ms']:.2f}ms")

        # Compute cosine similarity between first two
        import numpy as np

        embeddings = np.array(data["embeddings"])
        emb1, emb2 = embeddings[0], embeddings[1]

        cos_sim = np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))
        print(f"\nSimilarity between texts 1 and 2: {cos_sim:.3f}")

    print()


async def search_evidence():
    """Search for evidence."""
    print("=" * 60)
    print("6. Search for Evidence")
    print("=" * 60)

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/api/v1/search",
            json={
                "query": "climate change effects on polar ice caps",
                "limit": 5,
                "mode": "hybrid",
                "min_similarity": 0.5,
            },
        )

        data = response.json()
        print(f"Found {data['count']} results in {data['query_time_ms']:.2f}ms")
        print(f"Mode: {data['mode']}\n")

        for result in data["results"]:
            print(f"Rank {result['rank']}: Similarity {result['similarity']:.2f}")
            print(f"  Source: {result.get('source_url', 'N/A')}")
            print(f"  Content: {result['content'][:100]}...")
            print()

    print()


async def nli_inference():
    """Run NLI inference."""
    print("=" * 60)
    print("7. NLI Inference (Single)")
    print("=" * 60)

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/api/v1/nli",
            json={
                "premise": "The Earth revolves around the Sun in an elliptical orbit",
                "hypothesis": "The Earth orbits the Sun",
            },
        )

        data = response.json()
        print(f"Label: {data['label']}")
        print(f"Confidence: {data['confidence']:.2%}")
        print(f"Processing time: {data['processing_time_ms']:.2f}ms")
        print("\nAll scores:")
        for label, score in data["scores"].items():
            print(f"  {label}: {score:.2%}")

    print()


async def nli_batch():
    """Run batch NLI inference."""
    print("=" * 60)
    print("8. NLI Batch Inference")
    print("=" * 60)

    async with httpx.AsyncClient() as client:
        pairs = [
            ("The Earth orbits the Sun", "Earth revolves around Sun"),
            ("Water boils at 100°C", "Water freezes at 100°C"),
            ("Cats are mammals", "Cats are animals"),
        ]

        response = await client.post(
            f"{BASE_URL}/api/v1/nli/batch",
            json={"pairs": pairs, "batch_size": 8},
        )

        data = response.json()
        print(f"Processed {data['count']} pairs")
        print(f"Total time: {data['total_processing_time_ms']:.2f}ms\n")

        for i, result in enumerate(data["results"]):
            premise, hypothesis = pairs[i]
            print(f"{i+1}. Hypothesis: {hypothesis}")
            print(f"   Premise: {premise}")
            print(f"   Label: {result['label']} ({result['confidence']:.2%})")
            print()

    print()


async def rate_limit_stats():
    """Get rate limit statistics."""
    print("=" * 60)
    print("9. Rate Limit Statistics")
    print("=" * 60)

    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/rate-limit-stats")
        data = response.json()

        stats = data.get("rate_limit_statistics", {})
        print(f"Total violations: {stats.get('total_violations', 0)}")
        print(f"Total requests: {stats.get('total_requests', 0)}")

        print("\nEndpoint violations:")
        violations = stats.get("endpoint_violations", {})
        for endpoint, count in violations.items():
            if count > 0:
                print(f"  {endpoint}: {count}")

    print()


async def main():
    """Run all examples."""
    print("\n" + "=" * 60)
    print("TruthGraph API - Python Examples")
    print("=" * 60 + "\n")

    try:
        # 1. Health check
        await health_check()

        # 2. Simple synchronous verification
        await simple_verify()

        # 3. Async verification with polling
        claim_id = f"claim_{int(time.time())}"
        await async_verify_with_polling(
            claim_id, "The Earth is approximately 4.54 billion years old"
        )

        # 4. Generate embeddings
        await generate_embeddings()

        # 5. Search evidence
        await search_evidence()

        # 6. NLI inference
        await nli_inference()

        # 7. NLI batch
        await nli_batch()

        # 8. Rate limit stats
        await rate_limit_stats()

        print("=" * 60)
        print("All examples completed successfully!")
        print("=" * 60)

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
