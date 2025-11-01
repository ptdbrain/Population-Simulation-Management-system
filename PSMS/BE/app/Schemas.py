from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, date
from enum import Enum

class Token(BaseModel): # BaseModel để định nghĩa cấu trúc của token
    access_token: str
    token_type: str = "bearer"

class LoginIn(BaseModel):
    username: str
    password: str

class UserBase(BaseModel):
    username : str
    full_name : Optional[str] = None
    email : Optional[str] = None
    phone : Optional[str] = None

class UserCreate(UserBase):
    password : str 
class UserOut(UserBase):
    id : int
    is_active : bool
    class Config:
        orm_mode = True

class RoleOut(BaseModel):
    id: int
    name: str
    description: Optional[str]
    class Config:
        orm_mode = True
class PermissionOut(BaseModel):
    id: int
    code: str
    description: Optional[str]
    class Config:
        orm_mode = True
class HouseholdCreate(BaseModel):
    household_number: str
    address: Optional[str] = None
    
class HouseholdOut(BaseModel):
    id: int
    household_number: str
    address: Optional[str] = None
    created_at: datetime
    class Config:
        orm_mode = True

class PersonCreate(BaseModel):
    full_name: str
    birthdate: date
    gender : str
    id_number: Optional[str] 
    current_household_id: int
    relation_to_head: str


class PersonOut(BaseModel):
    id : int
    full_name: str
    birthdate: date     
    gender : str
    id_number: Optional[str]        
    current_household_id: int
    relation_to_head: str
    created_at: datetime
    class Config:
        orm_mode = True


class HouseholdSplit(BaseModel):
    new_household_number: str = Field(..., description="Số hộ khẩu của hộ mới thành lập")
    address: Optional[str] = Field(None, description="Địa chỉ của hộ mới thành lập")
    member_ids: list[int] = Field(..., description="Danh sách ID của các thành viên chuyển sang hộ mới")
    head_person_id: int


class TempAbsenceCreate(BaseModel):
    person_id: int
    from_date: date
    to_date: date
    reason: Optional[str] = None

class TempResidenceCreate(BaseModel):
    id: int
    person_id: int
    from_date: date
    to_date: date
    reason: Optional[str] = None
    host_household_id: int

class ComplaintCreate(BaseModel):
    reporter_person_id: Optional[int]
    content: str
    category: Optional[str]

class ComplaintOut(BaseModel):
    id: int
    reporter_person_id: Optional[int]
    content: str
    category: Optional[str]
    status: str
    duplicates_count: int
    created_at: datetime
    class Config:
        orm_mode = True


