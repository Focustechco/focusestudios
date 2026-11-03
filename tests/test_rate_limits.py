import time
from unittest.mock import MagicMock
import httpx
from app.adapters.tiktok.direct_post import TikTokDirectPostAdapter


def test_rate_limit_retry_after_handling(monkeypatch):
    adapter = TikTokDirectPostAdapter()
    
    # Mock time.sleep para não pausar os testes reais
    sleep_called_with = []
    monkeypatch.setattr(time, "sleep", lambda secs: sleep_called_with.append(secs))

    response_429 = httpx.Response(
        status_code=429,
        headers={"Retry-After": "5"},
        request=httpx.Request("POST", "https://open.tiktokapis.com/test")
    )

    adapter._handle_backoff(attempt=1, response=response_429)

    assert len(sleep_called_with) == 1
    assert sleep_called_with[0] == 5.0
