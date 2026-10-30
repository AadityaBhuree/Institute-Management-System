#!/usr/bin/env python3
"""Institute Management System (IMS Enterprise) - Production Load Testing & Benchmark Script.

Simulates concurrent user sessions against the running FastAPI application or TestClient.
Measures request latencies, throughput (req/s), error rates, and connection stability.
"""

import argparse
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

# Ensure stdout handles unicode on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from fastapi.testclient import TestClient  # noqa: E402

from src.app import app  # noqa: E402


def run_benchmark(concurrency: int = 15, requests_per_worker: int = 10):
    """Run concurrent load test suite and print detailed telemetry statistics."""
    total_requests = concurrency * requests_per_worker
    print("=" * 70)
    print("IMS ENTERPRISE - PRODUCTION CONCURRENT LOAD BENCHMARK")
    print("=" * 70)
    print(f"Workers (Concurrency) : {concurrency}")
    print(f"Requests per worker   : {requests_per_worker}")
    print(f"Total operations      : {total_requests}")
    print("=" * 70)

    client = TestClient(app)

    endpoints = [
        "/api/dashboard/stats",
        "/api/departments",
        "/api/students?page=1&limit=10",
        "/api/courses",
        "/api/reports/analytics-summary",
        "/api/system/telemetry",
    ]

    latencies = []
    statuses = {}
    start_time = time.perf_counter()

    def worker_task(worker_id: int):
        worker_latencies = []
        for i in range(requests_per_worker):
            path = endpoints[(worker_id + i) % len(endpoints)]
            t0 = time.perf_counter()
            resp = client.get(path)
            duration = time.perf_counter() - t0
            worker_latencies.append((resp.status_code, duration))
        return worker_latencies

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(worker_task, i) for i in range(concurrency)]
        for fut in as_completed(futures):
            res_list = fut.result()
            for status, duration in res_list:
                statuses[status] = statuses.get(status, 0) + 1
                latencies.append(duration)

    total_wall_time = time.perf_counter() - start_time
    rps = total_requests / total_wall_time if total_wall_time > 0 else 0

    latencies.sort()
    avg_latency = sum(latencies) / len(latencies) if latencies else 0
    p50 = latencies[int(len(latencies) * 0.50)]
    p90 = latencies[int(len(latencies) * 0.90)]
    p95 = latencies[int(len(latencies) * 0.95)]
    p99 = latencies[int(len(latencies) * 0.99)]
    min_lat = min(latencies) if latencies else 0
    max_lat = max(latencies) if latencies else 0

    print("\nBENCHMARK RESULTS:")
    print(f"  Total Duration       : {total_wall_time:.3f} s")
    print(f"  Throughput           : {rps:.1f} req/s")
    print(f"  Min Latency          : {min_lat * 1000:.2f} ms")
    print(f"  Avg Latency          : {avg_latency * 1000:.2f} ms")
    print(f"  p50 (Median)         : {p50 * 1000:.2f} ms")
    print(f"  p90 Latency          : {p90 * 1000:.2f} ms")
    print(f"  p95 Latency          : {p95 * 1000:.2f} ms")
    print(f"  p99 Latency          : {p99 * 1000:.2f} ms")
    print(f"  Max Latency          : {max_lat * 1000:.2f} ms")
    print("\nHTTP STATUS DISTRIBUTION:")
    for status, count in sorted(statuses.items()):
        pct = (count / total_requests) * 100
        print(f"  HTTP {status}           : {count}/{total_requests} ({pct:.1f}%)")

    success_count = statuses.get(200, 0)
    success_rate = (success_count / total_requests) * 100
    print(f"\nOverall Success Rate: {success_rate:.1f}%")
    if success_rate == 100.0 and p95 < 1.0:
        print("[PASS] Production load criteria passed successfully.")
        return 0
    else:
        print("[FAIL] Production load criteria failed.")
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="IMS Enterprise Load Tester")
    parser.add_argument(
        "-c", "--concurrency", type=int, default=15, help="Number of worker threads"
    )
    parser.add_argument("-n", "--requests", type=int, default=10, help="Requests per worker thread")
    args = parser.parse_args()
    sys.exit(run_benchmark(concurrency=args.concurrency, requests_per_worker=args.requests))
