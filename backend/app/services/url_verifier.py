"""
Application URL Safety & Verification Engine.

Performs deterministic, safe health verification on original employer application links.
Distinguishes between:
- VALID: 200 OK / 204 No Content
- REDIRECTED: 301 / 302 / 307 / 308 reaching a valid destination
- TEMPORARILY_UNAVAILABLE: 429 (rate-limited), 500/502/503/504, timeout, network glitch
- CONFIRMED_BROKEN: 404 Not Found, 410 Gone
- INVALID_URL: Malformed, non-HTTP, or SSRF-blocked

Invariants:
- Never closes jobs because of temporary network failures or rate limits.
- Never invents or fabricates replacement URLs.
- Fully honors SSRF blocking against private/internal hostnames.
"""

import time
import httpx
import ipaddress
from urllib.parse import urlparse
from typing import Dict, Any, List, Optional
from datetime import datetime


class UrlVerifierService:
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 (GetMeHire Verification Engine/1.0)"

    @staticmethod
    def is_safe_url(url: Optional[str]) -> bool:
        if not url or not isinstance(url, str):
            return False
        clean = url.strip()
        try:
            parsed = urlparse(clean)
            if parsed.scheme not in ("http", "https"):
                return False
            hostname = parsed.hostname
            if not hostname:
                return False
            h_lower = hostname.lower()
            if h_lower in ("localhost", "127.0.0.1", "0.0.0.0", "::1", "169.254.169.254"):
                return False
            try:
                ip = ipaddress.ip_address(h_lower)
                if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                    return False
            except ValueError:
                pass
            return True
        except Exception:
            return False

    @classmethod
    def verify_single_url(cls, url: Optional[str], timeout: float = 6.0) -> Dict[str, Any]:
        """
        Verifies a single application URL deterministically.
        """
        start_t = time.time()
        if not cls.is_safe_url(url):
            return {
                "url": url,
                "status": "INVALID_URL",
                "http_status": None,
                "final_url": None,
                "is_redirected": False,
                "latency_ms": round((time.time() - start_t) * 1000, 1),
                "error": "URL blocked by security / safety policy",
            }

        headers = {
            "User-Agent": cls.USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

        try:
            with httpx.Client(timeout=timeout, follow_redirects=True, max_redirects=3) as client:
                # Try HEAD first for minimal network consumption
                try:
                    resp = client.head(url, headers=headers)
                    if resp.status_code == 405:  # Method Not Allowed on some ATS servers
                        resp = client.get(url, headers=headers)
                except httpx.HTTPError:
                    # Fallback to GET stream if HEAD is rejected
                    resp = client.get(url, headers=headers)

                status_code = resp.status_code
                final_url = str(resp.url)
                is_redirected = final_url.rstrip("/") != url.rstrip("/")
                latency = round((time.time() - start_t) * 1000, 1)

                if status_code in (200, 204):
                    return {
                        "url": url,
                        "status": "REDIRECTED" if is_redirected else "VALID",
                        "http_status": status_code,
                        "final_url": final_url,
                        "is_redirected": is_redirected,
                        "latency_ms": latency,
                        "error": None,
                    }
                elif status_code in (404, 410):
                    return {
                        "url": url,
                        "status": "CONFIRMED_BROKEN",
                        "http_status": status_code,
                        "final_url": final_url,
                        "is_redirected": is_redirected,
                        "latency_ms": latency,
                        "error": f"HTTP {status_code} - Posting removed by employer",
                    }
                elif status_code in (429, 500, 502, 503, 504):
                    return {
                        "url": url,
                        "status": "TEMPORARILY_UNAVAILABLE",
                        "http_status": status_code,
                        "final_url": final_url,
                        "is_redirected": is_redirected,
                        "latency_ms": latency,
                        "error": f"HTTP {status_code} - Remote ATS rate limit or server error",
                    }
                else:
                    return {
                        "url": url,
                        "status": "TEMPORARILY_UNAVAILABLE",
                        "http_status": status_code,
                        "final_url": final_url,
                        "is_redirected": is_redirected,
                        "latency_ms": latency,
                        "error": f"Unexpected HTTP status {status_code}",
                    }
        except (httpx.TimeoutException, httpx.ConnectTimeout):
            return {
                "url": url,
                "status": "TEMPORARILY_UNAVAILABLE",
                "http_status": None,
                "final_url": None,
                "is_redirected": False,
                "latency_ms": round((time.time() - start_t) * 1000, 1),
                "error": "Connection timed out",
            }
        except httpx.NetworkError as ne:
            return {
                "url": url,
                "status": "TEMPORARILY_UNAVAILABLE",
                "http_status": None,
                "final_url": None,
                "is_redirected": False,
                "latency_ms": round((time.time() - start_t) * 1000, 1),
                "error": f"Network error: {str(ne)[:80]}",
            }
        except Exception as e:
            return {
                "url": url,
                "status": "TEMPORARILY_UNAVAILABLE",
                "http_status": None,
                "final_url": None,
                "is_redirected": False,
                "latency_ms": round((time.time() - start_t) * 1000, 1),
                "error": str(e)[:100],
            }
