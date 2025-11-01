from fastapi import Depends, HTTPException, status, Security
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordBearer, SecurityScopes
from jose import JWTError, jwt
from .db import get_db
from .auth_jwt import decode_token
from . import models

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token/login")

def get_current_user(
    security_scopes: SecurityScopes, # danh sách phạm vi bảo mật yêu cầu 
    token: str = Depends(oauth2_scheme), # token được truyền từ header Authorization
    db: Session = Depends(get_db)   # phiên làm việc với cơ sở dữ liệu
                        ) -> models.User:
    """Lấy thông tin người dùng hiện tại từ token."""
    credentials_exception = HTTPException( # ngoại lệ khi xác thực thất bại
        status_code=status.HTTP_401_UNAUTHORIZED, # mã lỗi 401
        detail="Could not validate credentials",    # chi tiết lỗi
        headers={"WWW-Authenticate": "Bearer"},     # header xác thực
    )
    payload = decode_token(token) # giải mã token để lấy payload
    if payload is None:
        raise credentials_exception # ném ngoại lệ nếu giải mã thất bại
    username: str = payload.get("sub") # lấy tên người dùng từ payload
    if username is None:
        raise credentials_exception # ném ngoại lệ nếu không có tên người dùng
    token_scopes = payload.get("scopes", [])    # lấy phạm vi bảo mật từ payload
    user = db.query(models.User).filter(models.User.username == username).first()   # truy vấn người dùng từ cơ sở dữ liệu
    if user is None:
        raise credentials_exception # ném ngoại lệ nếu không tìm thấy người dùng
    for scope in security_scopes.scopes: # kiểm tra từng phạm vi bảo mật yêu cầu
        if scope not in token_scopes: # nếu phạm vi không có trong token
            raise HTTPException(    # ném ngoại lệ nếu không đủ quyền
                status_code=status.HTTP_401_UNAUTHORIZED,   # mã lỗi 401
                detail="Not enough permissions",    # chi tiết lỗi
                headers={"WWW-Authenticate": f'Bearer scope="{security_scopes.scope_str}"'},    # header xác thực với phạm vi yêu cầu
            )
    return user


def require_permission(permission_code : str):
    def _checker(user = Depends(get_current_user), db: Session = Depends(get_db)): # phụ thuộc vào người dùng hiện tại và phiên làm việc với cơ sở dữ liệu
        rows = db.execute(    # truy vấn để kiểm tra quyền
            """
            SELECT 1
            FROM user_roles ur
            JOIN role_permissions rp ON ur.role_id = rp.role_id
            JOIN permissions p ON rp.permission_id = p.id
            WHERE ur.user_id = :user_id AND p.name = :permission_name
            """,
            {"user_id": user.id, "permission_name": permission_code}
        ).fetchall()

        perm_set = {r[0] for r in rows} # tập hợp các quyền từ kết quả truy vấn
        if permission_code not in perm_set: # nếu quyền yêu cầu không có trong tập hợp
            raise HTTPException(    # ném ngoại lệ nếu không đủ quyền
                status_code=status.HTTP_403_FORBIDDEN,   # mã lỗi 403
                detail="You do not have permission to perform this action."  # chi tiết lỗi
            )
        return True # trả về True nếu có quyền
    return _checker         # trả về hàm kiểm tra quyền

