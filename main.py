from fastapi import FastAPI, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from jose import jwt, JWTError
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import os
from dotenv import load_dotenv
from bson import ObjectId
from fastapi.security import OAuth2PasswordBearer

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

class User(BaseModel):
    id: Optional[str] = None
    user_name: str
    password: str

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
user_collection = db.users
temporary_absences_collection = db.temporary_absences
temporary_residences_collection = db.temporary_residences
feedbacks_collection = db.feedbacks

# Helper function to convert ObjectId to string
def convert_objectid_to_str(doc):
    if doc and "_id" in doc:
        doc["id"] = str(doc["_id"])
        del doc["_id"]
    return doc


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")
ALGORITHM = "HS256"
async def verify_token(Authorization: str = Header(None)):
    if Authorization is None or not Authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token không hợp lệ")

    token = Authorization.split(" ")[1]

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Token hết hạn hoặc không hợp lệ")

@app.get("/", response_class=HTMLResponse)
async def read_root():
    with open("static/index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

# Household endpoints
@app.post("/api/households/")
async def create_household(household: Household, current_user: dict = Depends(verify_token)):
    household_dict = household.dict()
    household_dict["created_at"] = datetime.now()
    household_dict["updated_at"] = datetime.now()
    
    result = await households_collection.insert_one(household_dict)
    household_dict["id"] = str(result.inserted_id)
    
    return convert_objectid_to_str(household_dict)

@app.get("/api/households/")
async def get_households(current_user: dict = Depends(verify_token)):
    households = []
    async for household in households_collection.find():
        households.append(convert_objectid_to_str(household))
    return households

@app.get("/api/households/{household_id}")
async def get_household(household_id: str, current_user: dict = Depends(verify_token)):
    household = await households_collection.find_one({"_id": ObjectId(household_id)})
    if household:
        return convert_objectid_to_str(household)
    raise HTTPException(status_code=404, detail="Household not found")

@app.put("/api/households/{household_id}")
async def update_household(household_id: str, household: Household, current_user: dict = Depends(verify_token)):
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
async def delete_household(household_id: str, current_user: dict = Depends(verify_token)):
    result = await households_collection.delete_one({"_id": ObjectId(household_id)})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Household not found")
    
    return {"message": "Household deleted successfully"}

# Person endpoints
@app.post("/api/persons/")
async def create_person(person: Person, current_user: dict = Depends(verify_token)):
    person_dict = person.dict()
    person_dict["created_at"] = datetime.now()
    person_dict["updated_at"] = datetime.now()
    
    result = await persons_collection.insert_one(person_dict)
    person_dict["id"] = str(result.inserted_id)
    
    return convert_objectid_to_str(person_dict)

@app.get("/api/persons/")
async def get_persons(current_user: dict = Depends(verify_token)):
    persons = []
    async for person in persons_collection.find():
        persons.append(convert_objectid_to_str(person))
    return persons

@app.get("/api/persons/{person_id}")
async def get_person(person_id: str,current_user: dict = Depends(verify_token)):
    person = await persons_collection.find_one({"_id": ObjectId(person_id)})
    if person:
        return convert_objectid_to_str(person)
    raise HTTPException(status_code=404, detail="Person not found")

@app.put("/api/persons/{person_id}")
async def update_person(person_id: str, person: Person, current_user: dict = Depends(verify_token)):
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
async def delete_person(person_id: str, current_user: dict = Depends(verify_token)):
    result = await persons_collection.delete_one({"_id": ObjectId(person_id)})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Person not found")
    
    return {"message": "Person deleted successfully"}

# Temporary absence endpoints
@app.post("/api/temporary-absences/")
async def create_temporary_absence(absence: TemporaryAbsence, current_user: dict = Depends(verify_token)):
    absence_dict = absence.dict()
    absence_dict["created_at"] = datetime.now()
    
    result = await temporary_absences_collection.insert_one(absence_dict)
    absence_dict["id"] = str(result.inserted_id)
    
    return convert_objectid_to_str(absence_dict)

@app.get("/api/temporary-absences/")
async def get_temporary_absences(current_user: dict = Depends(verify_token)):
    absences = []
    async for absence in temporary_absences_collection.find():
        absences.append(convert_objectid_to_str(absence))
    return absences

# Temporary residence endpoints
@app.post("/api/temporary-residences/")
async def create_temporary_residence(residence: TemporaryResidence, current_user: dict = Depends(verify_token)):
    residence_dict = residence.dict()
    residence_dict["created_at"] = datetime.now()
    
    result = await temporary_residences_collection.insert_one(residence_dict)
    residence_dict["id"] = str(result.inserted_id)
    
    return convert_objectid_to_str(residence_dict)

@app.get("/api/temporary-residences/")
async def get_temporary_residences(current_user: dict = Depends(verify_token)):
    residences = []
    async for residence in temporary_residences_collection.find():
        residences.append(convert_objectid_to_str(residence))
    return residences

# Feedback endpoints
@app.post("/api/feedbacks/")
async def create_feedback(feedback: Feedback, current_user: dict = Depends(verify_token)):
    feedback_dict = feedback.dict()
    feedback_dict["created_at"] = datetime.now()
    
    result = await feedbacks_collection.insert_one(feedback_dict)
    feedback_dict["id"] = str(result.inserted_id)
    
    return convert_objectid_to_str(feedback_dict)

@app.get("/api/feedbacks/")
async def get_feedbacks(current_user: dict = Depends(verify_token)):
    feedbacks = []
    async for feedback in feedbacks_collection.find():
        feedbacks.append(convert_objectid_to_str(feedback))
    return feedbacks

@app.put("/api/feedbacks/{feedback_id}")
async def update_feedback(feedback_id: str, feedback: Feedback, current_user: dict = Depends(verify_token)):
    feedback_dict = feedback.dict()
    
    result = await feedbacks_collection.update_one(
        {"_id": ObjectId(feedback_id)},
        {"$set": feedback_dict}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Feedback not found")
    
    return {"message": "Feedback updated successfully"}

@app.delete("/api/temporary-absences/{absence_id}")
async def delete_temporary_absence(absence_id: str, current_user: dict = Depends(verify_token)):
    result = await temporary_absences_collection.delete_one({"_id": ObjectId(absence_id)})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Temporary absence not found")
    
    return {"message": "Temporary absence deleted successfully"}

@app.delete("/api/temporary-residences/{residence_id}")
async def delete_temporary_residence(residence_id: str, current_user: dict = Depends(verify_token)):
    result = await temporary_residences_collection.delete_one({"_id": ObjectId(residence_id)})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Temporary residence not found")
    
    return {"message": "Temporary residence deleted successfully"}

@app.delete("/api/feedbacks/{feedback_id}")
async def delete_feedback(feedback_id: str, current_user: dict = Depends(verify_token)):
    result = await feedbacks_collection.delete_one({"_id": ObjectId(feedback_id)})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Feedback not found")
    
    return {"message": "Feedback deleted successfully"}

# Statistics endpoints
@app.get("/api/statistics/population-by-gender")
async def get_population_by_gender(current_user: dict = Depends(verify_token)):
    pipeline = [
        {"$group": {"_id": "$gender", "count": {"$sum": 1}}}
    ]
    result = []
    async for doc in persons_collection.aggregate(pipeline):
        result.append({"gender": doc["_id"], "count": doc["count"]})
    return result

@app.get("/api/statistics/population-by-age")
async def get_population_by_age(current_user: dict = Depends(verify_token)):
    # This is a simplified version - in real implementation, you'd calculate age from birth_date
    pipeline = [
        {"$group": {"_id": "$age_group", "count": {"$sum": 1}}}
    ]
    result = []
    async for doc in persons_collection.aggregate(pipeline):
        result.append({"age_group": doc["_id"], "count": doc["count"]})
    return result

@app.get("/api/statistics/feedbacks-by-status")
async def get_feedbacks_by_status(current_user: dict = Depends(verify_token)):
    pipeline = [
        {"$group": {"_id": "$status", "count": {"$sum": 1}}}
    ]
    result = []
    async for doc in feedbacks_collection.aggregate(pipeline):
        result.append({"status": doc["_id"], "count": doc["count"]})
    return result

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import bcrypt
from datetime import datetime, timedelta

def hash_password(password: str):
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

SECRET_KEY = "SECRET_KEY"

def verify_password(plain_password, hashed_password):
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def create_token(data: dict):
    payload = data.copy()
    payload.update({"exp": datetime.utcnow() + timedelta(hours=12)})  # token hết hạn sau 12h
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")


class LoginRequest(BaseModel):
    user_name: str
    password: str

@app.post("/login")
async def login(request: LoginRequest):
    # 1️⃣ Tìm user trong MongoDB theo user_name
    user = await user_collection.find_one({"user_name": request.user_name})

    if not user:
        raise HTTPException(status_code=401, detail="Tên đăng nhập hoặc mật khẩu không đúng")

    # 2️⃣ Kiểm tra mật khẩu (đã hash bằng bcrypt)
    if not verify_password(request.password, user["password"]):
        raise HTTPException(status_code=401, detail="Tên đăng nhập hoặc mật khẩu không đúng")

    # 3️⃣ Tạo JWT token
    token = create_token({
        "user_id": str(user["_id"]),
        "user_name": user["user_name"]
    })

    # ✅ Trả về JSON
    return JSONResponse({
        "message": "Đăng nhập thành công",
        "token": token,
        "user": {
            "id": str(user["_id"]),
            "user_name": user["user_name"]
        }
    })

@app.post("/register")
async def register(user: LoginRequest):
    # Kiểm tra user_name đã tồn tại chưa
    existing_user = await db.users.find_one({"user_name": user.user_name})
    if existing_user:
        raise HTTPException(status_code=400, detail="Tên đăng nhập đã tồn tại")

    hashed_pw = hash_password(user.password)

    new_user = {
        "user_name": user.user_name,
        "password": hashed_pw,
    }

    await db.users.insert_one(new_user)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

