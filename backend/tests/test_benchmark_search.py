import time
import statistics
import pytest

def test_search_latency_p95_below_500ms(client):
    latencies = []
    
    # Run 50 search requests simulating typical search queries
    queries = [
        "/api/v1/jobs?keyword=Engineer",
        "/api/v1/jobs?remote_type=REMOTE",
        "/api/v1/jobs?company=Stripe",
        "/api/v1/jobs?min_salary=100000",
        "/api/v1/jobs?country=United%20States",
        "/api/v1/jobs?page=1&page_size=10",
        "/api/v1/jobs?sort_by=newest",
        "/api/v1/jobs?sort_by=salary_high",
        "/api/v1/jobs?keyword=Python&remote_type=REMOTE",
        "/api/v1/jobs"
    ]

    for i in range(50):
        url = queries[i % len(queries)]
        start = time.perf_counter()
        res = client.get(url)
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        assert res.status_code == 200
        latencies.append(elapsed_ms)

    latencies.sort()
    # Compute p95 index (48th element out of 50)
    p95_index = int(0.95 * len(latencies))
    p95_latency = latencies[p95_index]
    mean_latency = statistics.mean(latencies)

    print(f"\n[BENCHMARK] Total Requests: {len(latencies)}, Mean: {mean_latency:.2f}ms, p95: {p95_latency:.2f}ms")
    # PRD Requirement: p95 below 500 ms
    assert p95_latency < 500.0, f"p95 search latency ({p95_latency:.2f}ms) exceeded 500ms target"
