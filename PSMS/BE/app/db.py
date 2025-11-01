import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session, declarative_base
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL, future = True) # có nghĩa là sử dụng các tính năng mới của SQLAlchemy
SessionLocal = sessionmaker(bind = engine, autocommit = False, autoflush = False) # cấu hình session , không tự động commit và flush
Base = declarative_base() # cơ sở để định nghĩa các mô hình (models)

def get_db():
    db = SessionLocal() # tạo một phiên làm việc với cơ sở dữ liệu
    try:
        yield db # trả về phiên làm việc
    finally:
        db.close()  # đóng phiên làm việc sau khi sử dụng xong

