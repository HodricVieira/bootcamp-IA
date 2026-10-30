from functools import lru_cache

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings

bearer_scheme = HTTPBearer(auto_error=False)
UNAUTHORIZED_DETAIL = {"code": "UNAUTHORIZED", "message": "Faça login para continuar."}


def _unauthorized() -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=UNAUTHORIZED_DETAIL)


@lru_cache
def _get_supabase_auth_client():
    from supabase import create_client

    return create_client(settings.supabase_url, settings.supabase_service_role_key)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> str:
    if (
        credentials is None
        or credentials.scheme.lower() != "bearer"
        or not credentials.credentials.strip()
    ):
        raise _unauthorized()
    try:
        response = _get_supabase_auth_client().auth.get_user(credentials.credentials.strip())
    except Exception as exc:
        raise _unauthorized() from exc
    user = getattr(response, "user", None)
    user_id = getattr(user, "id", None)
    if not user_id:
        raise _unauthorized()
    return str(user_id)
