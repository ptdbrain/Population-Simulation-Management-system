from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import os
from dotenv import load_dotenv
from bson import ObjectId

load_dotenv()

app = FastAPI(title="Hệ thống quản lý hộ khẩu", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MongoDB connection
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
client = AsyncIOMotorClient(MONGODB_URL)
db = client.household_management

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Pydantic models
class Person(BaseModel):
    id: Optional[str] = None
    name: str
    birth_date: str
    gender: str  # "nam" or "nu"
    id_number: str
    relationship: str  # "chủ hộ", "vợ", "chồng", "con", etc.
    occupation: str
    address: str
    phone: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class Household(BaseModel):
    id: Optional[str] = None
    household_number: str
    address: str
    members: List[Person] = []
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class TemporaryAbsence(BaseModel):
    id: Optional[str] = None
    person_id: str
    person_name: str
    household_id: str
    household_number: str
    start_date: str
    end_date: str
    reason: str
    status: str = "active"  # "active", "expired"
    created_at: Optional[datetime] = None

class TemporaryResidence(BaseModel):
    id: Optional[str] = None
    person_id: str
    person_name: str
    household_id: str
    household_number: str
    start_date: str
    end_date: str
    reason: str
    status: str = "active"  # "active", "expired"
    created_at: Optional[datetime] = None

class Feedback(BaseModel):
    id: Optional[str] = None
    person_name: str
    content: str
    date: str
    category: str
    status: str = "new"  # "new", "processing", "resolved"
    response: Optional[str] = None
    response_date: Optional[str] = None
    created_at: Optional[datetime] = None

# Database collections
households_collection = db.households
persons_collection = db.persons
temporary_absences_collection = db.temporary_absences
temporary_residences_collection = db.temporary_residences
feedbacks_collection = db.feedbacks

# Helper function to convert ObjectId to string
def convert_objectid_to_str(doc):
    if doc and "_id" in doc:
        doc["id"] = str(doc["_id"])
        del doc["_id"]
    return doc

@app.get("/", response_class=HTMLResponse)
async def read_root():
    with open("static/index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

# Household endpoints
@app.post("/api/households/")
async def create_household(household: Household):
    household_dict = household.dict()
    household_dict["created_at"] = datetime.now()
    household_dict["updated_at"] = datetime.now()
    
    result = await households_collection.insert_one(household_dict)
    household_dict["id"] = str(result.inserted_id)
    
    return convert_objectid_to_str(household_dict)

@app.get("/api/households/")
async def get_households():
    households = []
    async for household in households_collection.find():
        households.append(convert_objectid_to_str(household))
    return households

@app.get("/api/households/{household_id}")
async def get_household(household_id: str):
    household = await households_collection.find_one({"_id": ObjectId(household_id)})
    if household:
        return convert_objectid_to_str(household)
    raise HTTPException(status_code=404, detail="Household not found")

@app.put("/api/households/{household_id}")
async def update_household(household_id: str, household: Household):
    household_dict = household.dict()
    household_dict["updated_at"] = datetime.now()
    
    result = await households_collection.update_one(
        {"_id": ObjectId(household_id)},
        {"$set": household_dict}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Household not found")
    
    return {"message": "Household updated successfully"}

@app.delete("/api/households/{household_id}")
async def delete_household(household_id: str):
    result = await households_collection.delete_one({"_id": ObjectId(household_id)})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Household not found")
    
    return {"message": "Household deleted successfully"}

# Person endpoints
@app.post("/api/persons/")
async def create_person(person: Person):
    person_dict = person.dict()
    person_dict["created_at"] = datetime.now()
    person_dict["updated_at"] = datetime.now()
    
    result = await persons_collection.insert_one(person_dict)
    person_dict["id"] = str(result.inserted_id)
    
    return convert_objectid_to_str(person_dict)

@app.get("/api/persons/")
async def get_persons():
    persons = []
    async for person in persons_collection.find():
        persons.append(convert_objectid_to_str(person))
    return persons

@app.get("/api/persons/{person_id}")
async def get_person(person_id: str):
    person = await persons_collection.find_one({"_id": ObjectId(person_id)})
    if person:
        return convert_objectid_to_str(person)
    raise HTTPException(status_code=404, detail="Person not found")

@app.put("/api/persons/{person_id}")
async def update_person(person_id: str, person: Person):
    person_dict = person.dict()
    person_dict["updated_at"] = datetime.now()
    
    result = await persons_collection.update_one(
        {"_id": ObjectId(person_id)},
        {"$set": person_dict}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Person not found")
    
    return {"message": "Person updated successfully"}

@app.delete("/api/persons/{person_id}")
async def delete_person(person_id: str):
    result = await persons_collection.delete_one({"_id": ObjectId(person_id)})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Person not found")
    
    return {"message": "Person deleted successfully"}

# Temporary absence endpoints
@app.post("/api/temporary-absences/")
async def create_temporary_absence(absence: TemporaryAbsence):
    absence_dict = absence.dict()
    absence_dict["created_at"] = datetime.now()
    
    result = await temporary_absences_collection.insert_one(absence_dict)
    absence_dict["id"] = str(result.inserted_id)
    
    return convert_objectid_to_str(absence_dict)

@app.get("/api/temporary-absences/")
async def get_temporary_absences():
    absences = []
    async for absence in temporary_absences_collection.find():
        absences.append(convert_objectid_to_str(absence))
    return absences

# Temporary residence endpoints
@app.post("/api/temporary-residences/")
async def create_temporary_residence(residence: TemporaryResidence):
    residence_dict = residence.dict()
    residence_dict["created_at"] = datetime.now()
    
    result = await temporary_residences_collection.insert_one(residence_dict)
    residence_dict["id"] = str(result.inserted_id)
    
    return convert_objectid_to_str(residence_dict)

@app.get("/api/temporary-residences/")
async def get_temporary_residences():
    residences = []
    async for residence in temporary_residences_collection.find():
        residences.append(convert_objectid_to_str(residence))
    return residences

# Feedback endpoints
@app.post("/api/feedbacks/")
async def create_feedback(feedback: Feedback):
    feedback_dict = feedback.dict()
    feedback_dict["created_at"] = datetime.now()
    
    result = await feedbacks_collection.insert_one(feedback_dict)
    feedback_dict["id"] = str(result.inserted_id)
    
    return convert_objectid_to_str(feedback_dict)

@app.get("/api/feedbacks/")
async def get_feedbacks():
    feedbacks = []
    async for feedback in feedbacks_collection.find():
        feedbacks.append(convert_objectid_to_str(feedback))
    return feedbacks

@app.put("/api/feedbacks/{feedback_id}")
async def update_feedback(feedback_id: str, feedback: Feedback):
    feedback_dict = feedback.dict()
    
    result = await feedbacks_collection.update_one(
        {"_id": ObjectId(feedback_id)},
        {"$set": feedback_dict}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Feedback not found")
    
    return {"message": "Feedback updated successfully"}

@app.delete("/api/temporary-absences/{absence_id}")
async def delete_temporary_absence(absence_id: str):
    result = await temporary_absences_collection.delete_one({"_id": ObjectId(absence_id)})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Temporary absence not found")
    
    return {"message": "Temporary absence deleted successfully"}

@app.delete("/api/temporary-residences/{residence_id}")
async def delete_temporary_residence(residence_id: str):
    result = await temporary_residences_collection.delete_one({"_id": ObjectId(residence_id)})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Temporary residence not found")
    
    return {"message": "Temporary residence deleted successfully"}

@app.delete("/api/feedbacks/{feedback_id}")
async def delete_feedback(feedback_id: str):
    result = await feedbacks_collection.delete_one({"_id": ObjectId(feedback_id)})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Feedback not found")
    
    return {"message": "Feedback deleted successfully"}

# Statistics endpoints
@app.get("/api/statistics/population-by-gender")
async def get_population_by_gender():
    pipeline = [
        {"$group": {"_id": "$gender", "count": {"$sum": 1}}}
    ]
    result = []
    async for doc in persons_collection.aggregate(pipeline):
        result.append({"gender": doc["_id"], "count": doc["count"]})
    return result

@app.get("/api/statistics/population-by-age")
async def get_population_by_age():
    # This is a simplified version - in real implementation, you'd calculate age from birth_date
    pipeline = [
        {"$group": {"_id": "$age_group", "count": {"$sum": 1}}}
    ]
    result = []
    async for doc in persons_collection.aggregate(pipeline):
        result.append({"age_group": doc["_id"], "count": doc["count"]})
    return result

@app.get("/api/statistics/feedbacks-by-status")
async def get_feedbacks_by_status():
    pipeline = [
        {"$group": {"_id": "$status", "count": {"$sum": 1}}}
    ]
    result = []
    async for doc in feedbacks_collection.aggregate(pipeline):
        result.append({"status": doc["_id"], "count": doc["count"]})
    return result

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

