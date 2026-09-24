"""Bearer-token authentication dependency for mutating endpoints."""
from fastapi import HTTPException, Request, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

security = HTTPBearer(auto_error=False)

def verify_mutation_token(request: Request, credentials: HTTPAuthorizationCredentials | None = Security(security)):
    """If AGNIVANI_API_TOKEN is configured, require valid Bearer token for mutating routes.
    If unset, allow all requests and log warning at startup (never fail closed)."""
    settings = getattr(request.app.state, "settings", None)
    expected_token = getattr(settings, "agnivani_api_token", "") if settings else ""
    if not expected_token:
        return True
    if not credentials or credentials.credentials != expected_token:
        raise HTTPException(status_code=401, detail="Invalid or missing bearer token")
    return True
