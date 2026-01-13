from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential


DEFAULT_UA = "rss-br/0.1 (+https://github.com/)"


@dataclass(slots=True)
class HttpConfig:
    timeout_s: float = 15.0
    user_agent: str = DEFAULT_UA
    follow_redirects: bool = True
    accept: str = "text/html,application/xml,application/rss+xml,application/atom+xml,text/xml,*/*;q=0.1"


def _headers(cfg: HttpConfig) -> dict[str, str]:
    return {"User-Agent": cfg.user_agent, "Accept": cfg.accept}


def make_client(cfg: HttpConfig) -> httpx.Client:
    return httpx.Client(
        timeout=httpx.Timeout(cfg.timeout_s),
        follow_redirects=cfg.follow_redirects,
        headers=_headers(cfg),
    )


def _should_retry_status(status_code: int) -> bool:
    return status_code in (408, 425, 429, 500, 502, 503, 504)


@retry(
    retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError, httpx.RemoteProtocolError)),
    wait=wait_exponential(multiplier=0.5, min=0.5, max=8),
    stop=stop_after_attempt(4),
    reraise=True,
)
def get(client: httpx.Client, url: str) -> httpx.Response:
    resp = client.get(url)
    if _should_retry_status(resp.status_code):
        # force retry by raising for 4xx/5xx, but only on selected codes
        raise httpx.HTTPStatusError(f"retryable status {resp.status_code}", request=resp.request, response=resp)
    return resp


def first_working_url(
    client: httpx.Client, urls: Iterable[str]
) -> tuple[str | None, httpx.Response | None, str | None]:
    """
    Tenta URLs em ordem e retorna a primeira que responde sem erro de rede.
    Não garante sucesso (pode retornar 404 etc), só evita falhas de conexão.
    """
    last_err: str | None = None
    for u in urls:
        try:
            r = client.get(u)
            return u, r, None
        except Exception as e:  # noqa: BLE001 - CLI tool: keep reason
            last_err = f"{type(e).__name__}: {e}"
            continue
    return None, None, last_err

