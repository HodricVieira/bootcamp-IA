import logging
import time
from collections.abc import Callable
from typing import TypeVar

import httpx
from google.genai import errors

try:
    import httpx2
except ImportError:
    httpx2 = None

logger = logging.getLogger(__name__)

RETRY_DELAYS = (1.0, 2.0)

_NETWORK_ERRORS = tuple(
    cls
    for cls in (
        TimeoutError,
        httpx.TimeoutException,
        httpx.ConnectError,
        getattr(httpx2, "TimeoutException", None),
        getattr(httpx2, "ConnectError", None),
    )
    if cls is not None
)

T = TypeVar("T")


class RateLimitedError(RuntimeError):
    """Indica que o Gemini continuou devolvendo 429 depois das novas tentativas."""


def is_rate_limited(exc: Exception) -> bool:
    return isinstance(exc, errors.APIError) and exc.code == 429


def is_transient(exc: Exception) -> bool:
    if isinstance(exc, errors.APIError):
        return exc.code == 429 or 500 <= exc.code < 600
    return isinstance(exc, _NETWORK_ERRORS)


def call_with_retry(call: Callable[[], T], sleep: Callable[[float], None] = time.sleep) -> T:
    """Executa a chamada com até len(RETRY_DELAYS) novas tentativas para erros temporários."""
    for delay in RETRY_DELAYS:
        try:
            return call()
        except Exception as exc:
            if not is_transient(exc):
                raise
            logger.warning("Erro temporário no Gemini (%s); nova tentativa em %ss.", type(exc).__name__, delay)
        sleep(delay)
    return call()
