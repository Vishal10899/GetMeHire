import time
from typing import Dict, List
from collections import defaultdict
from fastapi import Request, status
from fastapi.responses import JSONResponse

class InMemoryRateLimiter:
    """
    Sliding-window rate limiter for sensitive endpoints (PRD 4.1 & 9.1).
    Tracks requests per IP address within a configurable time window.
    """
    def __init__(self, requests_limit: int = 15, window_seconds: int = 60):
        self.requests_limit = requests_limit
        self.window_seconds = window_seconds
        self.requests: Dict[str, List[float]] = defaultdict(list)

    def is_allowed(self, client_ip: str) -> bool:
        now = time.time()
        window_start = now - self.window_seconds
        
        # Clean older entries
        self.requests[client_ip] = [t for t in self.requests[client_ip] if t > window_start]
        
        if len(self.requests[client_ip]) >= self.requests_limit:
            return False
            
        self.requests[client_ip].append(now)
        return True

auth_rate_limiter = InMemoryRateLimiter(requests_limit=15, window_seconds=60)
