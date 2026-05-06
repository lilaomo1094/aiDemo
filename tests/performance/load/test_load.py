import pytest
import time
from unittest.mock import Mock


class MockLoadTest:
    def __init__(self):
        self.response_times = []

    def simulate_request(self, request_id):
        start = time.time()
        time.sleep(0.01)
        end = time.time()
        self.response_times.append(end - start)
        return {"request_id": request_id, "status": "success"}


@pytest.mark.performance
class TestLoadPerformance:
    def test_response_time_single_request(self):
        tester = MockLoadTest()
        result = tester.simulate_request(1)
        assert result["status"] == "success"
        assert len(tester.response_times) == 1

    def test_response_time_multiple_requests(self):
        tester = MockLoadTest()
        for i in range(10):
            tester.simulate_request(i)
        
        assert len(tester.response_times) == 10
        avg_time = sum(tester.response_times) / len(tester.response_times)
        assert avg_time < 0.1

    def test_concurrent_requests_simulation(self):
        tester = MockLoadTest()
        results = [tester.simulate_request(i) for i in range(5)]
        
        assert len(results) == 5
        assert all(r["status"] == "success" for r in results)


@pytest.mark.performance
class TestStressSimulation:
    def test_high_volume_requests(self):
        tester = MockLoadTest()
        for i in range(100):
            tester.simulate_request(i)
        
        assert len(tester.response_times) == 100
        
    def test_response_time_distribution(self):
        tester = MockLoadTest()
        for i in range(20):
            tester.simulate_request(i)
        
        min_time = min(tester.response_times)
        max_time = max(tester.response_times)
        
        assert min_time >= 0
        assert max_time < 1
