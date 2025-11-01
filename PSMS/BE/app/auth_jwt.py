import os
from datetime import datetime ,timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from dotenv import load_dotenv

load_dotenv() # khởi tạo biến môi trường từ file .env
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60)) # thời gian hết hạn token

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto") # cấu hình thuật toán băm mật khẩu

def hash_password(password: str) -> str:
    """Băm mật khẩu người dùng."""
    return pwd_context.hash(password) # hàm băm mật khẩu

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Xác thực mật khẩu người dùng."""
    return pwd_context.verify(plain_password, hashed_password) # hàm xác thực mật khẩu

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Tạo JWT access token."""
    to_encode = data.copy() # sao chép dữ liệu để mã hóa
    if expires_delta:
        expire = datetime.datetime.utcnow() + expires_delta
    else:
        expire = datetime.datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)    # thời gian hết hạn mặc định
    to_encode.update({"exp": expire})  # thêm thời gian hết hạn vào payload
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM) # mã hóa JWT
    return encoded_jwt # trả về token

def decode_token(token: str) -> dict | None:
    """Giải mã JWT token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM]) # giải mã token
        return payload # trả về payload nếu thành công
    except JWTError:
        return None # trả về None nếu giải mã thất bại  