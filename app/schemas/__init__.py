from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, computed_field
from app.models import (
    UserRole, DepartmentType, ResolutionMode, AppealStatus, AppointmentStatus
)


# User Schemas
class UserLogin(BaseModel):
    username: str
    password: str


class HemisStudentLogin(BaseModel):
    hemis_login: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: UserRole
    user_id: int
    full_name: str
    expires_in_minutes: int
    must_change_password: bool = False
    hemis_token: Optional[str] = None
    hemis_refresh_token: Optional[str] = None


# Department & Service Schemas (Pre-defined for UserOut)
class DepartmentOut(BaseModel):
    id: int
    name: str
    code: str
    dept_type: DepartmentType
    window_number: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ServiceOut(BaseModel):
    id: int
    code: str
    title: str
    description: Optional[str] = None
    department_id: int
    kpi_points: int
    sla_hours: int
    resolution_mode: ResolutionMode
    required_docs: Optional[str] = None
    is_active: bool = True
    department: Optional[DepartmentOut] = None

    model_config = ConfigDict(from_attributes=True)


class UserOut(BaseModel):
    id: int
    username: str
    full_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    role: UserRole
    department_id: Optional[int] = None
    department: Optional[DepartmentOut] = None
    assigned_services: List[ServiceOut] = []
    is_active: bool = True
    must_change_password: bool = False
    assigned_duties: Optional[str] = None
    hemis_student_id: Optional[str] = None
    faculty: Optional[str] = None
    group_name: Optional[str] = None
    course: Optional[int] = None
    education_type: Optional[str] = None
    education_form: Optional[str] = None
    specialty: Optional[str] = None
    telegram_chat_id: Optional[int] = None
    telegram_username: Optional[str] = None
    telegram_connected_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class TelegramConnectInfo(BaseModel):
    bot_username: str
    is_connected: bool
    telegram_chat_id: Optional[int] = None
    telegram_username: Optional[str] = None
    deep_link: str


class UserRoleUpdate(BaseModel):
    role: UserRole


class StaffCreate(BaseModel):
    username: str
    full_name: str
    role: UserRole
    department_id: Optional[int] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    assigned_duties: Optional[str] = None
    custom_password: Optional[str] = None  # If not provided, 8-character OTP is generated
    service_ids: Optional[List[int]] = None


class StaffCreateResponse(BaseModel):
    user: UserOut
    temporary_password: str
    must_change_password: bool = True


class StaffUpdate(BaseModel):
    full_name: Optional[str] = None
    username: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    department_id: Optional[int] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
    assigned_duties: Optional[str] = None
    reset_password: Optional[bool] = False  # If True, generates new 8-char OTP
    new_password: Optional[str] = None  # If provided, sets custom password directly
    service_ids: Optional[List[int]] = None


class StaffServiceAssignRequest(BaseModel):
    service_ids: List[int]


class UpdateCredentialsRequest(BaseModel):
    current_password: str
    new_username: Optional[str] = None
    new_password: Optional[str] = None


class KPIAwardRequest(BaseModel):
    employee_id: int
    duty_title: str
    points: int
    reason: str


# Department & Service Schemas
class DepartmentCreate(BaseModel):
    name: str
    code: str
    dept_type: DepartmentType
    window_number: Optional[str] = None


class DepartmentUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    dept_type: Optional[DepartmentType] = None
    window_number: Optional[str] = None


class MyServicesResponse(BaseModel):
    department: Optional[DepartmentOut] = None
    services: List[ServiceOut]


class ServiceCreate(BaseModel):
    code: str
    title: str
    description: Optional[str] = None
    department_id: int
    kpi_points: int = 1
    sla_hours: int = 24
    resolution_mode: ResolutionMode = ResolutionMode.BOTH
    required_docs: Optional[str] = None


class ServiceUpdate(BaseModel):
    code: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    department_id: Optional[int] = None
    kpi_points: Optional[int] = None
    sla_hours: Optional[int] = None
    resolution_mode: Optional[ResolutionMode] = None
    required_docs: Optional[str] = None
    is_active: Optional[bool] = None


# Appeal Schemas
class AppealCreate(BaseModel):
    service_id: int
    subject: str
    message: str
    attachment_urls: Optional[str] = None


class AppealAssign(BaseModel):
    staff_id: int


class AppealReassign(BaseModel):
    new_staff_id: int
    reason: str


class AppealClarify(BaseModel):
    clarification_message: str


class AppealProvideClarify(BaseModel):
    additional_info: str


class AppealResolve(BaseModel):
    resolution_text: str
    result_file_url: Optional[str] = None


class AppealConfirm(BaseModel):
    rating: int  # 1 to 5
    rating_comment: Optional[str] = None


class AppealDispute(BaseModel):
    dispute_reason: str


class AppealEscalateProrektor(BaseModel):
    head_note: str


class ProrektorFinalDecision(BaseModel):
    final_decision: str


class AppealOut(BaseModel):
    id: int
    ticket_number: str
    student_id: int
    service_id: int
    assigned_staff_id: Optional[int] = None
    status: AppealStatus
    subject: str
    message: str
    attachment_urls: Optional[str] = None
    resolution_text: Optional[str] = None
    result_file_url: Optional[str] = None
    qr_hash: Optional[str] = None
    clarification_message: Optional[str] = None
    created_at: datetime
    assigned_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    sla_deadline_at: Optional[datetime] = None
    confirmation_deadline_at: Optional[datetime] = None
    rating: Optional[int] = None
    rating_comment: Optional[str] = None
    dispute_reason: Optional[str] = None
    earned_kpi_points: int
    service: Optional[ServiceOut] = None
    student: Optional[UserOut] = None
    assigned_staff: Optional[UserOut] = None

    model_config = ConfigDict(from_attributes=True)


# Appointment Schemas (Kelib hal etish)
class AppointmentBook(BaseModel):
    service_id: int
    appointment_date: str  # "YYYY-MM-DD"
    time_slot: str         # "10:15 - 10:30"


class AppointmentComplete(BaseModel):
    notes: Optional[str] = None


class AppointmentOut(BaseModel):
    id: int
    ticket_code: str
    student_id: int
    service_id: int
    staff_id: Optional[int] = None
    window_number: str
    appointment_date: str
    time_slot: str
    status: AppointmentStatus
    created_at: datetime
    called_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    notes: Optional[str] = None
    earned_kpi_points: int
    service: Optional[ServiceOut] = None
    student: Optional[UserOut] = None

    model_config = ConfigDict(from_attributes=True)


class SlotDetail(BaseModel):
    time_slot: str
    is_available: bool
    status: str  # "available", "past", "booked", "holiday"
    reason: Optional[str] = None


class AvailableSlotsResponse(BaseModel):
    date: str
    is_working_day: bool
    message: Optional[str] = None
    slots: List[SlotDetail]


# KPI Schemas
class EmployeeKPIOut(BaseModel):
    id: int
    employee_id: int
    period: str
    target_points: int
    completed_points: int
    penalty_points: int
    total_appeals_completed: int
    total_appointments_completed: int
    average_rating: float
    kpi_percentage: float
    employee: Optional[UserOut] = None

    model_config = ConfigDict(from_attributes=True)


# Holiday & Calendar Schemas
class HolidayCreate(BaseModel):
    holiday_date: str  # "YYYY-MM-DD"
    title: str
    is_working_day: bool = False


class HolidayOut(BaseModel):
    id: int
    holiday_date: str
    title: str
    is_working_day: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# HEMIS Extended Schemas
class HemisTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: UserRole
    user_id: int
    full_name: str
    expires_in_minutes: int
    hemis_token: Optional[str] = None
    hemis_refresh_token: Optional[str] = None


class HemisRefreshRequest(BaseModel):
    refresh_token: str


# Education Form Policy Schemas (Ta'lim shakllari onlayn murojaat cheklovlari)
class EducationFormItem(BaseModel):
    code: str
    title: str
    allowed: bool
    description: str


class EducationFormPolicyOut(BaseModel):
    allowed_forms: List[str]
    items: List[EducationFormItem]


class EducationFormPolicyUpdate(BaseModel):
    allowed_forms: List[str]


# Audit Log Schemas (Tizim audit jurnali)
class AuditLogOut(BaseModel):
    id: int
    user_id: Optional[int] = None
    entity_type: str
    entity_id: int
    action: str
    details: Optional[str] = None
    created_at: datetime
    user: Optional[UserOut] = None

    model_config = ConfigDict(from_attributes=True)

    @computed_field
    @property
    def user_full_name(self) -> Optional[str]:
        return self.user.full_name if self.user else None

    @computed_field
    @property
    def user_role(self) -> Optional[str]:
        return self.user.role.value if (self.user and self.user.role) else None


# E'lonlar va Bildirishnomalar Sxemalari
from app.models import AnnouncementPriority


class AnnouncementCreate(BaseModel):
    title: str
    content: str
    priority: AnnouncementPriority = AnnouncementPriority.NORMAL
    target_education_form: Optional[str] = None # None yoki "ALL" bo'lsa barchaga
    target_faculty: Optional[str] = None
    target_course: Optional[int] = None
    requires_ack: bool = False
    send_telegram: bool = False
    expires_at: Optional[datetime] = None


class AnnouncementOut(BaseModel):
    id: int
    title: str
    content: str
    priority: AnnouncementPriority
    target_education_form: Optional[str] = None
    target_faculty: Optional[str] = None
    target_course: Optional[int] = None
    author_id: int
    is_active: bool
    requires_ack: bool
    send_telegram: bool
    created_at: datetime
    expires_at: Optional[datetime] = None
    author: Optional[UserOut] = None

    model_config = ConfigDict(from_attributes=True)


class AnnouncementStudentView(BaseModel):
    id: int
    title: str
    content: str
    priority: AnnouncementPriority
    requires_ack: bool
    created_at: datetime
    is_read: bool = False
    read_at: Optional[datetime] = None
    is_acknowledged: bool = False

    model_config = ConfigDict(from_attributes=True)


class UnreadStudentInfo(BaseModel):
    id: int
    full_name: str
    hemis_student_id: Optional[str] = None
    group_name: Optional[str] = None
    faculty: Optional[str] = None
    course: Optional[int] = None
    education_form: Optional[str] = None
    phone: Optional[str] = None


class AnnouncementAnalyticsOut(BaseModel):
    announcement: AnnouncementOut
    total_target_students: int
    read_count: int
    read_percentage: float
    acknowledged_count: int
    acknowledged_percentage: float
    unread_students: List[UnreadStudentInfo]



