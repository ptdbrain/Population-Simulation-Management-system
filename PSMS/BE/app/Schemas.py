from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    refresh_token: Optional[str] = None


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class LoginIn(BaseModel):
    username: str
    password: str


class UserBase(BaseModel):
    username: str
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None


class UserCreate(UserBase):
    password: str
    role: str = "citizen"
    role_secret: Optional[str] = None


class UserOut(UserBase):
    id: int
    is_active: bool

    class Config:
        orm_mode = True


class RoleOut(BaseModel):
    id: int
    name: str
    description: Optional[str]

    class Config:
        orm_mode = True


class RolePermissionUpdate(BaseModel):
    permission_ids: List[int]


class PermissionOut(BaseModel):
    id: int
    code: str
    description: Optional[str]

    class Config:
        orm_mode = True


class HouseholdCreate(BaseModel):
    household_number: str
    address: Optional[str] = None
    head_person_id: Optional[int] = None


class HouseholdOut(BaseModel):
    id: int
    household_number: str
    address: Optional[str] = None
    head_person_id: Optional[int] = None
    created_at: datetime

    class Config:
        orm_mode = True


class PersonCreate(BaseModel):
    full_name: str
    birthdate: date
    gender: str
    id_number: Optional[str]
    current_household_id: int
    relation_to_head: str


class PersonOut(BaseModel):
    id: int
    full_name: str
    birthdate: date
    gender: str
    id_number: Optional[str]
    current_household_id: int
    relation_to_head: str
    created_at: datetime

    class Config:
        orm_mode = True


class HouseholdDetail(HouseholdOut):
    members: List[PersonOut] = []


class PersonHistoryOut(BaseModel):
    id: int
    person_id: int
    action: str
    from_household_id: Optional[int]
    to_household_id: Optional[int]
    note: Optional[str]
    performed_by: int
    performed_at: datetime

    class Config:
        orm_mode = True


class HouseholdSplit(BaseModel):
    new_household_number: str = Field(..., description="Số hộ khẩu của hộ mới thành lập")
    address: Optional[str] = Field(None, description="Địa chỉ của hộ mới thành lập")
    member_ids: List[int] = Field(..., description="Danh sách ID của các thành viên chuyển sang hộ mới")
    head_person_id: Optional[int] = Field(None, description="ID chủ hộ mới (phải nằm trong danh sách member_ids)")


class TempAbsenceCreate(BaseModel):
    person_id: int
    from_date: date
    to_date: date
    reason: Optional[str] = None


class TempAbsenceOut(BaseModel):
    id: int
    person_id: int
    from_date: date
    to_date: date
    reason: Optional[str]
    status: str
    registered_by: int
    approved_by: Optional[int]
    approved_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class TempResidenceCreate(BaseModel):
    person_id: int
    from_date: date
    to_date: date
    reason: Optional[str] = None
    host_household_id: int


class TempResidenceOut(BaseModel):
    id: int
    person_id: int
    from_date: date
    to_date: date
    reason: Optional[str]
    status: str
    host_household_id: int
    registered_by: int
    approved_by: Optional[int]
    approved_at: Optional[datetime]
    registered_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class TempRecordStatusUpdate(BaseModel):
    status: str = Field(..., description="new/pending/resolved")
    note: Optional[str] = None


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
    duplicate_count: int
    response_note: Optional[str]
    response_by: Optional[int]
    response_at: Optional[datetime]
    reported_at: datetime
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class ComplaintStatusUpdate(BaseModel):
    status: str
    response_note: Optional[str] = None


class ComplaintResponse(BaseModel):
    status: Optional[str] = None
    response_note: Optional[str] = None


class ComplaintFilter(BaseModel):
    status: Optional[str] = None
    category: Optional[str] = None
    keyword: Optional[str] = None


class DateRangeFilter(BaseModel):
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class ComplaintStatsOut(BaseModel):
    status: str
    count: int


class QuarterlyComplaintStats(BaseModel):
    year: int
    quarter: int
    status: str
    count: int


class ComplaintReportOut(BaseModel):
    id: int
    complaint_id: int
    reporter_person_id: int
    report_at: datetime

    class Config:
        orm_mode = True


class PopulationSummary(BaseModel):
    total_households: int
    total_persons: int
    by_gender: List[dict]
    temp_absence_pending: int
    temp_residence_pending: int
    complaints_pending: int


class AgeDistributionItem(BaseModel):
    age_group: str
    count: int


class TempRecordStatsOut(BaseModel):
    record_type: str
    status: str
    count: int
