from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.future import select
from datetime import date
from app.database import AsyncSessionLocal
from app.models.temp_models import AbsentRequest, RequestStatus
from app.models.residence_models import Resident, ResidentStatus

scheduler = AsyncIOScheduler()

async def sync_resident_status():
    """
    Logic 3: Auto-Sync Residency Status
    Run daily at 00:01
    """
    async with AsyncSessionLocal() as db:
        today = date.today()
        
        # 1. Query APPROVED absent requests
        result = await db.execute(select(AbsentRequest).where(AbsentRequest.status == RequestStatus.APPROVED))
        requests = result.scalars().all()
        
        for req in requests:
            res_result = await db.execute(select(Resident).where(Resident.id == req.resident_id))
            resident = res_result.scalars().first()
            if not resident:
                continue
            
            # If today >= start and today <= end -> TEMP ABSENT
            if req.start_date <= today <= req.end_date:
                if resident.status != ResidentStatus.TEMPORARY_ABSENT:
                    resident.status = ResidentStatus.TEMPORARY_ABSENT
                    db.add(resident)
            
            # If today > end -> PERMANENT (Auto-return)
            elif today > req.end_date:
                if resident.status != ResidentStatus.PERMANENT: # Assuming they return to permanent
                    # Check if they are actually back or moved out? 
                    # Logic says "Auto-return to PERMANENT"
                    resident.status = ResidentStatus.PERMANENT
                    db.add(resident)
        
        await db.commit()

def start_scheduler():
    scheduler.add_job(sync_resident_status, 'cron', hour=0, minute=1)
    scheduler.start()
