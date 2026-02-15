"""
Firebase authentication dependency for FastAPI.

Verifies the Firebase ID token passed as a Bearer token in the Authorization header.
Use `require_admin` as a FastAPI dependency on any route that must be admin-only.

Initialization:
  - Set the GOOGLE_APPLICATION_CREDENTIALS env var to the path of a Firebase
    service-account JSON key file, OR
  - Place `firebase-service-account.json` next to the `api/` directory
    (i.e. `backend/firebase-service-account.json`).
"""

import os
from pathlib import Path

import firebase_admin
from firebase_admin import auth as firebase_auth, credentials
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

# ---------------------------------------------------------------------------
# Firebase Admin SDK – initialise once
# ---------------------------------------------------------------------------

_DEFAULT_SA_PATH = Path(__file__).resolve().parents[2] / "firebase-service-account.json"

if not firebase_admin._apps:
    cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", str(_DEFAULT_SA_PATH))
    if os.path.isfile(cred_path):
        _cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(_cred)
    else:
        # When running on GCP (Cloud Run / GKE) the default credentials are
        # available automatically — no key file needed.
        firebase_admin.initialize_app()

# ---------------------------------------------------------------------------
# Bearer-token extraction scheme
# ---------------------------------------------------------------------------

_bearer_scheme = HTTPBearer(auto_error=False)


# ---------------------------------------------------------------------------
# Dependency
# ---------------------------------------------------------------------------

async def require_admin(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> dict:
    """
    FastAPI dependency that:
    1. Extracts the Bearer token from the `Authorization` header.
    2. Verifies it with Firebase Admin SDK.
    3. Returns the decoded token dict (contains `uid`, `email`, etc.).

    Raises 401 if the token is missing or invalid.
    """
    if creds is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = creds.credentials
    try:
        decoded = firebase_auth.verify_id_token(token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired Firebase token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return decoded

