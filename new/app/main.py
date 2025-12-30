from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import auth, household, complaint, person, stats, temp_residence, request, my_data, admin_stats, admin_users, questions, reminders
from app.database import engine
from app.models.base import Base
# Import all models to register them with Base.metadata
from app.models import auth_models, residence_models, temp_models, complaint_models, request_models, notification_models, question_models, reminder_models
from app.worker import start_scheduler
from fastapi.staticfiles import StaticFiles
import os

app = FastAPI(title="Residence Management System")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers with /api prefix
app.include_router(auth.router, prefix="/api")
app.include_router(household.router, prefix="/api")
app.include_router(complaint.router, prefix="/api")
app.include_router(person.router, prefix="/api")
app.include_router(stats.router, prefix="/api")
app.include_router(temp_residence.router, prefix="/api")
app.include_router(request.router, prefix="/api")
app.include_router(my_data.router, prefix="/api")
app.include_router(admin_stats.router, prefix="/api")
app.include_router(admin_users.router, prefix="/api")
app.include_router(questions.router, prefix="/api")
app.include_router(reminders.router, prefix="/api")

# Mount Frontend
# We mount it AFTER the routers so that API routes take priority
frontend_path = os.path.join(os.getcwd(), "frontend", "public")
if os.path.exists(frontend_path):
    app.mount("/", StaticFiles(directory=frontend_path, html=True), name="static")

@app.on_event("startup")
async def startup():
    start_scheduler()
    async with engine.begin() as conn:
        # await conn.run_sync(Base.metadata.drop_all) # For dev/testing only
        await conn.run_sync(Base.metadata.create_all)
