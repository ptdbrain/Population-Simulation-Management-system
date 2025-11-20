# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .db import engine, Base
from app.core.config import settings
from app.Routers import auth, users, households, persons, temp, complaints, report

# Auto-create schema in development (disable via settings.AUTO_CREATE_SCHEMA)
if settings.AUTO_CREATE_SCHEMA:
    Base.metadata.create_all(bind=engine)

app = FastAPI(title="PSMS - Hộ khẩu & Phản ánh") # Tạo một ứng dụng FastAPI với tiêu đề cụ thể

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router) # bao gồm các router từ các module khác nhau để tổ chức các endpoint của ứng dụng
app.include_router(users.router)    # bao gồm router cho người dùng
app.include_router(households.router) # bao gồm router cho hộ gia đình
app.include_router(persons.router)   # bao gồm router cho cá nhân
app.include_router(temp.router)      # bao gồm router cho tạm trú
app.include_router(complaints.router) # bao gồm router cho khiếu nại
app.include_router(report.router)    # bao gồm router cho báo cáo

@app.get("/api/health")
def health_check():
    return {"status": "ok"}


if settings.FRONTEND_DIST_PATH and settings.FRONTEND_DIST_PATH.exists():
    app.mount(
        "/",
        StaticFiles(directory=settings.FRONTEND_DIST_PATH, html=True),
        name="frontend",
    )
