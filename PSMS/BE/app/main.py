# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .db import engine, Base
from app.Routers import auth, users, households, persons, temp, complaints, report

# create tables if not using Alembic for dev quick start
# Base.metadata.create_all(bind=engine)

app = FastAPI(title="PSMS - Hộ khẩu & Phản ánh") # Tạo một ứng dụng FastAPI với tiêu đề cụ thể

app.add_middleware(
    CORSMiddleware, # Cấu hình CORS để cho phép các yêu cầu từ các nguồn khác nhau, middleware này rất quan trọng cho các ứng dụng web hiện đại
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"], # Thay thế bằng danh sách các nguồn được phép truy cập
    allow_credentials=True, # cho phép gửi cookie và thông tin xác thực
    allow_methods=["*"], # cho phép tất cả các phương thức HTTP
    allow_headers=["*"],    # cho phép tất cả các tiêu đề HTTP
)

app.include_router(auth.router) # bao gồm các router từ các module khác nhau để tổ chức các endpoint của ứng dụng
app.include_router(users.router)    # bao gồm router cho người dùng
app.include_router(households.router) # bao gồm router cho hộ gia đình
app.include_router(persons.router)   # bao gồm router cho cá nhân
app.include_router(temp.router)      # bao gồm router cho tạm trú
app.include_router(complaints.router) # bao gồm router cho khiếu nại
app.include_router(report.router)    # bao gồm router cho báo cáo

@app.get("/")   # Định nghĩa một route gốc trả về trạng thái "ok"
def root():
    return {"status":"ok"} # Định nghĩa một route gốc trả về trạng thái "ok"
