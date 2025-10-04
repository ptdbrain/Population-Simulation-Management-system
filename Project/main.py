from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
from bson import ObjectId
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext

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

# Security config
SECRET_KEY = os.getenv("SECRET_KEY", "change_me_dev_only_secret")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

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
    user_id: Optional[str] = None
    person_name: str
    content: str
    date: str
    category: str
    status: str = "new"  # "new", "processing", "resolved"
    response: Optional[str] = None
    response_date: Optional[str] = None
    created_at: Optional[datetime] = None

class UserCreate(BaseModel):
    username: str
    password: str
    full_name: Optional[str] = None
    role: Optional[str] = None  # optional on register, defaults to "user"
    person_id: Optional[str] = None  # link to Person if applicable
    household_id: Optional[str] = None  # link to Household if applicable

class UserOut(BaseModel):
    id: Optional[str] = None
    username: str
    full_name: Optional[str] = None
    role: str
    person_id: Optional[str] = None
    household_id: Optional[str] = None

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

# Database collections
households_collection = db.households
persons_collection = db.persons
temporary_absences_collection = db.temporary_absences
temporary_residences_collection = db.temporary_residences
feedbacks_collection = db.feedbacks
users_collection = db.users

# Helper function to convert ObjectId to string
def convert_objectid_to_str(doc):
    if doc and "_id" in doc:
        doc["id"] = str(doc["_id"])
        del doc["_id"]
    return doc

# Security helpers
def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:
        return False

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_user_by_username(username: str) -> Optional[dict]:
    user = await users_collection.find_one({"username": username})
    if not user:
        return None
    user_doc = {**user, "id": str(user["_id"])}
    user_doc.pop("_id", None)
    return user_doc

async def authenticate_user(username: str, password: str) -> Optional[dict]:
    user = await users_collection.find_one({"username": username})
    if not user:
        return None
    if not verify_password(password, user.get("password_hash", "")):
        return None
    user_doc = {**user, "id": str(user["_id"])}
    user_doc.pop("_id", None)
    user_doc.pop("password_hash", None)
    return user_doc

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(status_code=401, detail="Không thể xác thực", headers={"WWW-Authenticate": "Bearer"})
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: Optional[str] = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = await get_user_by_username(username)
    if user is None:
        raise credentials_exception
    return user

def require_admin(current_user: dict = Depends(get_current_user)):
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Chỉ dành cho admin")
    return current_user

@app.get("/", response_class=HTMLResponse)
async def read_root():
    with open("static/index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

# Auth routes
@app.post("/api/auth/register", response_model=UserOut)
async def register_user(user: UserCreate, current_user: Optional[dict] = Depends(lambda: None)):
    # Only admin can set role other than default. If no current_user, role forced to user.
    existing = await users_collection.find_one({"username": user.username})
    if existing:
        raise HTTPException(status_code=400, detail="Username đã tồn tại")
    # Bootstrap: first user becomes admin automatically
    first_user = await users_collection.count_documents({}) == 0
    role = "admin" if first_user else (
        user.role if (current_user and current_user.get("role") == "admin" and user.role in ["admin", "user"]) else "user"
    )
    doc = {
        "username": user.username,
        "password_hash": get_password_hash(user.password),
        "full_name": user.full_name,
        "role": role,
        "person_id": user.person_id,
        "household_id": user.household_id,
        "created_at": datetime.utcnow(),
    }
    result = await users_collection.insert_one(doc)
    return {
        "id": str(result.inserted_id),
        "username": user.username,
        "full_name": user.full_name,
        "role": role,
        "person_id": user.person_id,
        "household_id": user.household_id,
    }

@app.post("/api/auth/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = await authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Sai tài khoản hoặc mật khẩu", headers={"WWW-Authenticate": "Bearer"})
    access_token = create_access_token(data={"sub": user["username"]})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/api/me", response_model=UserOut)
async def read_me(current_user: dict = Depends(get_current_user)):
    return {
        "id": current_user["id"],
        "username": current_user["username"],
        "full_name": current_user.get("full_name"),
        "role": current_user.get("role", "user"),
        "person_id": current_user.get("person_id"),
        "household_id": current_user.get("household_id"),
    }

# Household endpoints
@app.post("/api/households/")
async def create_household(household: Household, _: dict = Depends(require_admin)):
    household_dict = household.dict()
    household_dict["created_at"] = datetime.now()
    household_dict["updated_at"] = datetime.now()
    
    result = await households_collection.insert_one(household_dict)
    household_dict["id"] = str(result.inserted_id)
    
    return convert_objectid_to_str(household_dict)

@app.get("/api/households/")
async def get_households(_: dict = Depends(require_admin)):
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
async def update_household(household_id: str, household: Household, _: dict = Depends(require_admin)):
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
async def delete_household(household_id: str, _: dict = Depends(require_admin)):
    result = await households_collection.delete_one({"_id": ObjectId(household_id)})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Household not found")
    
    return {"message": "Household deleted successfully"}

# Person endpoints
@app.post("/api/persons/")
async def create_person(person: Person, _: dict = Depends(require_admin)):
    person_dict = person.dict()
    person_dict["created_at"] = datetime.now()
    person_dict["updated_at"] = datetime.now()
    
    result = await persons_collection.insert_one(person_dict)
    person_dict["id"] = str(result.inserted_id)
    
    return convert_objectid_to_str(person_dict)

@app.get("/api/persons/")
async def get_persons(_: dict = Depends(require_admin)):
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
async def update_person(person_id: str, person: Person, _: dict = Depends(require_admin)):
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
async def delete_person(person_id: str, _: dict = Depends(require_admin)):
    result = await persons_collection.delete_one({"_id": ObjectId(person_id)})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Person not found")
    
    return {"message": "Person deleted successfully"}

# Temporary absence endpoints
@app.post("/api/temporary-absences/")
async def create_temporary_absence(absence: TemporaryAbsence, _: dict = Depends(require_admin)):
    absence_dict = absence.dict()
    absence_dict["created_at"] = datetime.now()
    
    result = await temporary_absences_collection.insert_one(absence_dict)
    absence_dict["id"] = str(result.inserted_id)
    
    return convert_objectid_to_str(absence_dict)

@app.get("/api/temporary-absences/")
async def get_temporary_absences(_: dict = Depends(require_admin)):
    absences = []
    async for absence in temporary_absences_collection.find():
        absences.append(convert_objectid_to_str(absence))
    return absences

# Temporary residence endpoints
@app.post("/api/temporary-residences/")
async def create_temporary_residence(residence: TemporaryResidence, _: dict = Depends(require_admin)):
    residence_dict = residence.dict()
    residence_dict["created_at"] = datetime.now()
    
    result = await temporary_residences_collection.insert_one(residence_dict)
    residence_dict["id"] = str(result.inserted_id)
    
    return convert_objectid_to_str(residence_dict)

@app.get("/api/temporary-residences/")
async def get_temporary_residences(_: dict = Depends(require_admin)):
    residences = []
    async for residence in temporary_residences_collection.find():
        residences.append(convert_objectid_to_str(residence))
    return residences

# Feedback endpoints
@app.post("/api/feedbacks/")
async def create_feedback(feedback: Feedback, current_user: dict = Depends(get_current_user)):
    feedback_dict = feedback.dict()
    feedback_dict["created_at"] = datetime.now()
    feedback_dict["user_id"] = current_user["id"]
    
    result = await feedbacks_collection.insert_one(feedback_dict)
    feedback_dict["id"] = str(result.inserted_id)
    
    return convert_objectid_to_str(feedback_dict)

@app.get("/api/feedbacks/")
async def get_feedbacks(_: dict = Depends(require_admin)):
    feedbacks = []
    async for feedback in feedbacks_collection.find():
        feedbacks.append(convert_objectid_to_str(feedback))
    return feedbacks

@app.put("/api/feedbacks/{feedback_id}")
async def update_feedback(feedback_id: str, feedback: Feedback, _: dict = Depends(require_admin)):
    feedback_dict = feedback.dict()
    
    result = await feedbacks_collection.update_one(
        {"_id": ObjectId(feedback_id)},
        {"$set": feedback_dict}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Feedback not found")
    
    return {"message": "Feedback updated successfully"}

@app.delete("/api/temporary-absences/{absence_id}")
async def delete_temporary_absence(absence_id: str, _: dict = Depends(require_admin)):
    result = await temporary_absences_collection.delete_one({"_id": ObjectId(absence_id)})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Temporary absence not found")
    
    return {"message": "Temporary absence deleted successfully"}

@app.delete("/api/temporary-residences/{residence_id}")
async def delete_temporary_residence(residence_id: str, _: dict = Depends(require_admin)):
    result = await temporary_residences_collection.delete_one({"_id": ObjectId(residence_id)})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Temporary residence not found")
    
    return {"message": "Temporary residence deleted successfully"}

@app.delete("/api/feedbacks/{feedback_id}")
async def delete_feedback(feedback_id: str, _: dict = Depends(require_admin)):
    result = await feedbacks_collection.delete_one({"_id": ObjectId(feedback_id)})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Feedback not found")
    
    return {"message": "Feedback deleted successfully"}

# Statistics endpoints
@app.get("/api/statistics/population-by-gender")
async def get_population_by_gender(_: dict = Depends(require_admin)):
    pipeline = [
        {"$group": {"_id": "$gender", "count": {"$sum": 1}}}
    ]
    result = []
    async for doc in persons_collection.aggregate(pipeline):
        result.append({"gender": doc["_id"], "count": doc["count"]})
    return result

@app.get("/api/statistics/population-by-age")
async def get_population_by_age(_: dict = Depends(require_admin)):
    # This is a simplified version - in real implementation, you'd calculate age from birth_date
    pipeline = [
        {"$group": {"_id": "$age_group", "count": {"$sum": 1}}}
    ]
    result = []
    async for doc in persons_collection.aggregate(pipeline):
        result.append({"age_group": doc["_id"], "count": doc["count"]})
    return result

@app.get("/api/statistics/feedbacks-by-status")
async def get_feedbacks_by_status(_: dict = Depends(require_admin)):
    pipeline = [
        {"$group": {"_id": "$status", "count": {"$sum": 1}}}
    ]
    result = []
    async for doc in feedbacks_collection.aggregate(pipeline):
        result.append({"status": doc["_id"], "count": doc["count"]})
    return result

# Self-service endpoints for normal users
@app.get("/api/my/household")
async def get_my_household(current_user: dict = Depends(get_current_user)):
    household_id = current_user.get("household_id")
    if not household_id:
        raise HTTPException(status_code=404, detail="Chưa liên kết hộ khẩu với tài khoản")
    household = await households_collection.find_one({"_id": ObjectId(household_id)})
    if not household:
        raise HTTPException(status_code=404, detail="Không tìm thấy hộ khẩu")
    return convert_objectid_to_str(household)

@app.get("/api/my/person")
async def get_my_person(current_user: dict = Depends(get_current_user)):
    person_id = current_user.get("person_id")
    if not person_id:
        raise HTTPException(status_code=404, detail="Chưa liên kết nhân khẩu với tài khoản")
    person = await persons_collection.find_one({"_id": ObjectId(person_id)})
    if not person:
        raise HTTPException(status_code=404, detail="Không tìm thấy nhân khẩu")
    return convert_objectid_to_str(person)

@app.get("/api/my/feedbacks")
async def get_my_feedbacks(current_user: dict = Depends(get_current_user)):
    items = []
    async for fb in feedbacks_collection.find({"user_id": current_user["id"]}):
        items.append(convert_objectid_to_str(fb))
    return items

# Feedback moderation endpoints (admin)
@app.put("/api/feedbacks/{feedback_id}/accept")
async def accept_feedback(feedback_id: str, _: dict = Depends(require_admin)):
    result = await feedbacks_collection.update_one({"_id": ObjectId(feedback_id)}, {"$set": {"status": "processing"}})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Feedback not found")
    return {"message": "Feedback accepted"}

@app.put("/api/feedbacks/{feedback_id}/reject")
async def reject_feedback(feedback_id: str, _: dict = Depends(require_admin)):
    result = await feedbacks_collection.update_one({"_id": ObjectId(feedback_id)}, {"$set": {"status": "rejected"}})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Feedback not found")
    return {"message": "Feedback rejected"}

class FeedbackReply(BaseModel):
    message: str

@app.post("/api/feedbacks/{feedback_id}/reply")
async def reply_feedback(feedback_id: str, body: FeedbackReply, _: dict = Depends(require_admin)):
    update = {"response": body.message, "response_date": datetime.utcnow().isoformat(), "status": "resolved"}
    result = await feedbacks_collection.update_one({"_id": ObjectId(feedback_id)}, {"$set": update})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Feedback not found")
    return {"message": "Reply sent"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

