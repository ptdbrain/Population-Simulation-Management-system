from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, SecurityScopes
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from .db import get_db
from . import models

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

def get_current_user(
    security_scopes: SecurityScopes,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> models.User:
    """Lấy thông tin người dùng hiện tại từ token."""
    credentials_exception = HTTPException( # ngoại lệ khi xác thực thất bại
        status_code=status.HTTP_401_UNAUTHORIZED, # mã lỗi 401
        detail="Could not validate credentials",    # chi tiết lỗi
        headers={"WWW-Authenticate": "Bearer"},     # header xác thực
    )
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception

    subject = payload.get("sub")
    if subject is None:
        raise credentials_exception
    try:
        user_id = int(subject)
    except (TypeError, ValueError):
        raise credentials_exception

    token_scopes = payload.get("perms", [])
    user = db.query(models.User).get(user_id)
    if user is None:
        raise credentials_exception

    for scope in security_scopes.scopes:
        if scope not in token_scopes:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not enough permissions",
                headers={"WWW-Authenticate": f'Bearer scope=\"{security_scopes.scope_str}\"'},
            )
    return user


def require_permission(permission_code : str):
    def _checker(user = Depends(get_current_user), db: Session = Depends(get_db)):
        row = db.execute(
            """
            SELECT 1
            FROM user_roles ur
            JOIN role_permissions rp ON ur.role_id = rp.role_id
            JOIN permissions p ON rp.permission_id = p.id
            WHERE ur.user_id = :user_id AND p.code = :permission_code
            """,
            {"user_id": user.id, "permission_code": permission_code},
        ).fetchone()

        if not row:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action."
            )
        return True

    return _checker

