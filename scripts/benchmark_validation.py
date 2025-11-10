"""Performance benchmark for validation layer.

Measures validation performance to ensure <10ms target is met.
"""

import time
from statistics import mean, median, stdev

from truthgraph.validation import ClaimValidator


def benchmark_validation():
    """Benchmark validation performance."""
    validator = ClaimValidator()

    # Test cases
    test_cases = [
        ("Simple valid", "The Earth orbits the Sun"),
        ("Medium length", "The Earth is the third planet from the Sun and the only astronomical object known to harbor life"),
        ("With emoji", "The Earth 🌍 is round and orbits the Sun ☀️"),
        ("Greek text", "Η Γη είναι στρογγυλή και περιστρέφεται γύρω από τον Ήλιο"),
        ("Arabic text", "الأرض كروية وتدور حول الشمس"),
        ("Math symbols", "Einstein's equation E = mc² shows mass-energy equivalence"),
        ("Mixed languages", "The Earth (地球 in Chinese, Γη in Greek) is round"),
        ("Long claim", "word " * 100),
    ]

    print("=" * 80)
    print("VALIDATION PERFORMANCE BENCHMARK")
    print("=" * 80)
    print(f"Target: <10ms per validation\n")

    # Warm-up
    for _, claim in test_cases:
        validator.validate(claim)

    # Benchmark each test case
    results = []
    for name, claim in test_cases:
        times = []
        iterations = 100

        for _ in range(iterations):
            start = time.perf_counter()
            validator.validate(claim)
            end = time.perf_counter()
            times.append((end - start) * 1000)  # Convert to ms

        avg_time = mean(times)
        med_time = median(times)
        std_time = stdev(times) if len(times) > 1 else 0
        min_time = min(times)
        max_time = max(times)

        results.append({
            "name": name,
            "avg": avg_time,
            "med": med_time,
            "std": std_time,
            "min": min_time,
            "max": max_time,
            "passes": avg_time < 10.0,
        })

        status = "PASS" if avg_time < 10.0 else "FAIL"
        print(f"{name:20} | Avg: {avg_time:6.3f}ms | Med: {med_time:6.3f}ms | Std: {std_time:6.3f}ms | {status}")

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    all_avg_times = [r["avg"] for r in results]
    overall_avg = mean(all_avg_times)
    overall_max = max(all_avg_times)
    all_pass = all(r["passes"] for r in results)

    print(f"Overall average: {overall_avg:.3f}ms")
    print(f"Overall max:     {overall_max:.3f}ms")
    print(f"Target:          <10.0ms")
    print(f"\nAll tests passed: {'YES' if all_pass else 'NO'}")

    if all_pass:
        print("\nAll validation operations meet the <10ms performance target!")
    else:
        print("\nSome validation operations exceed the 10ms target")

    # Batch performance
    print("\n" + "=" * 80)
    print("BATCH VALIDATION PERFORMANCE")
    print("=" * 80)

    batch_claims = [claim for _, claim in test_cases] * 10  # 80 claims
    batch_times = []
    batch_iterations = 50

    for _ in range(batch_iterations):
        start = time.perf_counter()
        validator.validate_batch(batch_claims)
        end = time.perf_counter()
        batch_times.append((end - start) * 1000)

    batch_avg = mean(batch_times)
    per_claim_avg = batch_avg / len(batch_claims)

    print(f"Batch size:           {len(batch_claims)} claims")
    print(f"Batch avg time:       {batch_avg:.2f}ms")
    print(f"Per claim avg:        {per_claim_avg:.3f}ms")
    print(f"Target per claim:     <10.0ms")
    print(f"Batch passes:         {'YES' if per_claim_avg < 10.0 else 'NO'}")

    return all_pass and per_claim_avg < 10.0


if __name__ == "__main__":
    success = benchmark_validation()
    exit(0 if success else 1)
