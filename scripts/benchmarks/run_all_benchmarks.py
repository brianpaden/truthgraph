#!/usr/bin/env python3
"""Run all benchmarks and generate baseline results.

This script runs all component benchmarks (embeddings, NLI, vector search, pipeline)
and saves the results with timestamps.

Usage:
    python run_all_benchmarks.py
    python run_all_benchmarks.py --quick  # Quick run with fewer iterations
    python run_all_benchmarks.py --baseline  # Generate baseline results
"""

import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def run_benchmark(script_name: str, args: list[str] = None) -> int:
    """Run a benchmark script.

    Args:
        script_name: Name of benchmark script
        args: Additional arguments for the script

    Returns:
        Exit code
    """
    script_path = Path(__file__).parent / script_name
    cmd = [sys.executable, str(script_path)]

    if args:
        cmd.extend(args)

    print(f"\n{'=' * 80}")
    print(f"Running: {script_name}")
    print(f"{'=' * 80}")

    result = subprocess.run(cmd)
    return result.returncode


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Run all benchmarks")
    parser.add_argument("--quick", action="store_true", help="Quick run with fewer iterations")
    parser.add_argument(
        "--baseline",
        action="store_true",
        help="Generate baseline results (saves to baseline_DATE.json)",
    )
    parser.add_argument("--skip-embeddings", action="store_true", help="Skip embeddings benchmark")
    parser.add_argument("--skip-nli", action="store_true", help="Skip NLI benchmark")
    parser.add_argument(
        "--skip-vector-search", action="store_true", help="Skip vector search benchmark"
    )
    parser.add_argument("--skip-pipeline", action="store_true", help="Skip pipeline benchmark")

    args = parser.parse_args()

    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    date_only = datetime.now().strftime("%Y-%m-%d")

    print("=" * 80)
    print("RUNNING ALL BENCHMARKS")
    print("=" * 80)
    print(f"\nTimestamp: {timestamp}")
    print(f"Quick mode: {args.quick}")
    print(f"Baseline mode: {args.baseline}")

    results_dir = Path(__file__).parent / "results"
    results_dir.mkdir(exist_ok=True)

    all_passed = True

    # Embeddings benchmark
    if not args.skip_embeddings:
        embed_args = []
        if args.quick:
            embed_args.extend(["--num-texts", "500", "--iterations", "50"])

        if args.baseline:
            output = f"baseline_embeddings_{date_only}.json"
        else:
            output = f"embeddings_{timestamp}.json"

        embed_args.extend(["--output", str(results_dir / output)])

        exit_code = run_benchmark("benchmark_embeddings.py", embed_args)
        if exit_code != 0:
            all_passed = False
            print(f"\n⚠ Embeddings benchmark failed with exit code {exit_code}")

    # NLI benchmark
    if not args.skip_nli:
        nli_args = []
        if args.quick:
            nli_args.extend(["--num-pairs", "50", "--iterations", "30"])

        if args.baseline:
            output = f"baseline_nli_{date_only}.json"
        else:
            output = f"nli_{timestamp}.json"

        nli_args.extend(["--output", str(results_dir / output)])

        exit_code = run_benchmark("benchmark_nli.py", nli_args)
        if exit_code != 0:
            all_passed = False
            print(f"\n⚠ NLI benchmark failed with exit code {exit_code}")

    # Vector search benchmark
    if not args.skip_vector_search:
        vs_args = []
        if args.quick:
            vs_args.extend(["--corpus-sizes", "1000,5000"])
        else:
            vs_args.extend(["--corpus-sizes", "1000,5000,10000"])

        if args.baseline:
            output = f"baseline_vector_search_{date_only}.json"
        else:
            output = f"vector_search_{timestamp}.json"

        vs_args.extend(["--output", str(results_dir / output)])

        exit_code = run_benchmark("benchmark_vector_search.py", vs_args)
        if exit_code != 0:
            all_passed = False
            print(f"\n⚠ Vector search benchmark failed with exit code {exit_code}")

    # Pipeline benchmark
    if not args.skip_pipeline:
        pipe_args = []
        if args.quick:
            pipe_args.extend(["--num-evidence", "500", "--iterations", "1"])
        else:
            pipe_args.extend(["--num-evidence", "1000", "--iterations", "2"])

        if args.baseline:
            output = f"baseline_pipeline_{date_only}.json"
        else:
            output = f"pipeline_{timestamp}.json"

        pipe_args.extend(["--output", str(results_dir / output)])

        exit_code = run_benchmark("benchmark_pipeline.py", pipe_args)
        if exit_code != 0:
            all_passed = False
            print(f"\n⚠ Pipeline benchmark failed with exit code {exit_code}")

    # Final summary
    print("\n" + "=" * 80)
    print("BENCHMARK SUITE COMPLETE")
    print("=" * 80)

    if all_passed:
        print("\n✓ All benchmarks completed successfully")
        print(f"\nResults saved to: {results_dir}")
        return 0
    else:
        print("\n⚠ Some benchmarks failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
