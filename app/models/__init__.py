from datetime import datetime, timezone
from enum import Enum
from typing import Optional, List
from sqlalchemy import (
    Column, Integer, BigInteger, String, Boolean, DateTime, ForeignKey, 
    Text, Float, Enum as SQLEnum, JSON, Index, Table
)
from sqlalchemy.orm import relationship, Mapped, mapped_column
from app.core.database import Base


# Many-to-Many: Xodimlarga aniq xizmatlarni biriktirish jadvali
user_services = Table(
    "user_services",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("service_id", Integer, ForeignKey("services.id", ondelete="CASCADE"), primary_key=True)
)


class UserRole(str, Enum):
    STUDENT = "student"
    FRONT_STAFF = "front_staff"
    BACK_STAFF = "back_staff"
    OFFICE_HEAD = "office_head"
    VICE_RECTOR = "vice_rector"
    ADMIN = "admin"


class DepartmentType(str, Enum):
    FRONT_OFFICE = "front_office"
    BACK_OFFICE = "back_office"


class ResolutionMode(str, Enum):
    ONLINE_ONLY = "online_only"
    IN_PERSON_ONLY = "in_person_only"
    BOTH = "both"


class AppealStatus(str, Enum):
    NEW = "new"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    CLARIFICATION_NEEDED = "clarification_needed"
    PENDING_EXTERNAL = "pending_external"
    RESOLVED = "resolved"
    AUTO_CLOSED = "auto_closed"
    COMPLETED = "completed"
    DISPUTED = "disputed"
    ESCALATED_HEAD = "escalated_head"
    ESCALATED_PROREKTOR = "escalated_prorektor"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class AppointmentStatus(str, Enum):
    BOOKED = "booked"
    CHECKED_IN = "checked_in"
    IN_SERVICE = "in_service"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"


# 1. Department / Sector Model
class Department(Base):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    dept_type: Mapped[DepartmentType] = mapped_column(SQLEnum(DepartmentType), nullable=False)
    window_number: Mapped[Optional[str]] = mapped_column(String(20), nullable=True) # e.g. "1-darcha"
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    users = relationship("User", back_populates="department")
    services = relationship("Service", back_populates="department")


# 1.5 CustomRole Model (Dinamik Rollar va Huquqlar Matritsasi)
class CustomRole(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False) # e.g. "office_head", "yurist"
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    permissions: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False) # ["appeals:view_all", ...]
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)
    is_immutable: Mapped[bool] = mapped_column(Boolean, default=False) # True only for admin
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


# 2. User Model
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    role: Mapped[str] = mapped_column(String(50), default="student", nullable=False)
    custom_permissions: Mapped[Optional[List[str]]] = mapped_column(JSON, default=list, nullable=True)
    
    # Department / Staff assignment
    department_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("departments.id"), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=False)
    assigned_duties: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Student specific fields (HEMIS integration - strictly academic, NO PII/passport)
    hemis_student_id: Mapped[Optional[str]] = mapped_column(String(50), unique=True, index=True, nullable=True)
    faculty: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    group_name: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    course: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    education_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True) # "Bakalavr", "Magistr"
    education_form: Mapped[Optional[str]] = mapped_column(String(50), nullable=True) # "Kunduzgi", "Sirtqi", "Kechki"
    specialty: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    hemis_refresh_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Telegram Bot Integratsiyasi
    telegram_chat_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, index=True)
    telegram_username: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    telegram_connected_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    department = relationship("Department", back_populates="users", lazy="selectin")
    appeals_created = relationship("Appeal", foreign_keys="Appeal.student_id", back_populates="student")
    appeals_assigned = relationship("Appeal", foreign_keys="Appeal.assigned_staff_id", back_populates="assigned_staff")
    kpi_records = relationship("EmployeeKPITarget", back_populates="employee")
    appointments = relationship("Appointment", foreign_keys="Appointment.student_id", back_populates="student")
    assigned_services = relationship("Service", secondary=user_services, back_populates="assigned_users", lazy="selectin")

    @property
    def role_value(self) -> str:
        return self.role.value if hasattr(self.role, "value") else str(self.role)


# 3. Service Model
class Service(Base):
    __tablename__ = "services"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    department_id: Mapped[int] = mapped_column(Integer, ForeignKey("departments.id"), nullable=False)
    kpi_points: Mapped[int] = mapped_column(Integer, default=1, nullable=False) # 1 to 10 points
    sla_hours: Mapped[int] = mapped_column(Integer, default=24, nullable=False) # 24, 72, 120
    resolution_mode: Mapped[ResolutionMode] = mapped_column(SQLEnum(ResolutionMode), default=ResolutionMode.BOTH, nullable=False)
    required_docs: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    department = relationship("Department", back_populates="services", lazy="selectin")
    appeals = relationship("Appeal", back_populates="service")
    appointments = relationship("Appointment", back_populates="service")
    assigned_users = relationship("User", secondary=user_services, back_populates="assigned_services", lazy="selectin")


# 4. Employee KPI Target Model
class EmployeeKPITarget(Base):
    __tablename__ = "employee_kpi_targets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    employee_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    period: Mapped[str] = mapped_column(String(7), nullable=False) # "YYYY-MM", e.g. "2026-09"
    target_points: Mapped[int] = mapped_column(Integer, default=150, nullable=False) # Standard monthly target
    completed_points: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    penalty_points: Mapped[int] = mapped_column(Integer, default=0, nullable=False) # e.g. -5 per overdue
    total_appeals_completed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_appointments_completed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    average_rating: Mapped[float] = mapped_column(Float, default=5.0, nullable=False)
    kpi_percentage: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    employee = relationship("User", back_populates="kpi_records", lazy="selectin")


# 5. Appeal Model
class Appeal(Base):
    __tablename__ = "appeals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    ticket_number: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    student_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    service_id: Mapped[int] = mapped_column(Integer, ForeignKey("services.id"), nullable=False)
    assigned_staff_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)

    status: Mapped[AppealStatus] = mapped_column(SQLEnum(AppealStatus), default=AppealStatus.NEW, nullable=False)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    attachment_urls: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Resolution & Output
    resolution_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    result_file_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    qr_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    clarification_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Dates & Timers
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    assigned_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    sla_deadline_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    confirmation_deadline_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Rating & Anti-Corruption Feedback
    rating: Mapped[Optional[int]] = mapped_column(Integer, nullable=True) # 1 to 5
    rating_comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    dispute_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reassign_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    earned_kpi_points: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    student = relationship("User", foreign_keys=[student_id], back_populates="appeals_created", lazy="selectin")
    assigned_staff = relationship("User", foreign_keys=[assigned_staff_id], back_populates="appeals_assigned")
    service = relationship("Service", back_populates="appeals", lazy="selectin")

    __table_args__ = (
        Index("ix_appeals_student_status", "student_id", "status"),
        Index("ix_appeals_staff_status", "assigned_staff_id", "status"),
        Index("ix_appeals_status_created", "status", "created_at"),
        Index("ix_appeals_service_id", "service_id"),
    )


# 6. Appointment Model (Kelib hal etish / Navbat)
class Appointment(Base):
    __tablename__ = "appointments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    ticket_code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False) # e.g. "TALON-A-102"
    student_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    service_id: Mapped[int] = mapped_column(Integer, ForeignKey("services.id"), nullable=False)
    staff_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)

    window_number: Mapped[str] = mapped_column(String(50), nullable=False) # e.g. "1-qavat, 104-xona, 2-darcha"
    appointment_date: Mapped[str] = mapped_column(String(10), nullable=False) # "YYYY-MM-DD"
    time_slot: Mapped[str] = mapped_column(String(20), nullable=False) # "10:15 - 10:30"
    scheduled_start: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    scheduled_end: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[AppointmentStatus] = mapped_column(SQLEnum(AppointmentStatus), default=AppointmentStatus.BOOKED, nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    called_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    earned_kpi_points: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    student = relationship("User", foreign_keys=[student_id], back_populates="appointments", lazy="selectin")
    service = relationship("Service", back_populates="appointments", lazy="selectin")

    __table_args__ = (
        Index("ix_appointments_date_service_slot", "appointment_date", "service_id", "time_slot"),
        Index("ix_appointments_student_date", "student_id", "appointment_date", "service_id"),
        Index("ix_appointments_date_status", "appointment_date", "status"),
    )


# 7. Audit Log Model
class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False) # "appeal", "appointment", "service", "auth", "staff"
    entity_id: Mapped[int] = mapped_column(Integer, nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False) # "created", "status_changed", "assigned", "login", etc.
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    user: Mapped[Optional["User"]] = relationship("User", foreign_keys=[user_id])


# 8. Holiday & Calendar Model (Bayramlar va dam olish kunlari kalendari)
class Holiday(Base):
    __tablename__ = "holidays"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    holiday_date: Mapped[str] = mapped_column(String(10), unique=True, index=True, nullable=False) # "YYYY-MM-DD"
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    is_working_day: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


# 9. System Setting Model (Tizim konfiguratsiyalari va cheklov siyosatlari)
class SystemSetting(Base):
    __tablename__ = "system_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    key: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


# 10. Announcement Models (Ommaviy va Segmentatsiyalangan E'lonlar)
class AnnouncementPriority(str, Enum):
    NORMAL = "normal"          # Oddiy axborot
    IMPORTANT = "important"    # Muhim ogohlantirish
    URGENT = "urgent"          # Shoshilinch (Qat'iy tanishish shart)


class Announcement(Base):
    __tablename__ = "announcements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[AnnouncementPriority] = mapped_column(SQLEnum(AnnouncementPriority), default=AnnouncementPriority.NORMAL, nullable=False)
    
    # Segmentatsiya filtrlari (None yoki "ALL" bo'lsa barcha talabalarga tegishli)
    target_education_form: Mapped[Optional[str]] = mapped_column(String(50), nullable=True) # "Kunduzgi", "Sirtqi", "Kechki", "Masofaviy"
    target_faculty: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    target_course: Mapped[Optional[int]] = mapped_column(Integer, nullable=True) # 1, 2, 3, 4
    
    author_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    requires_ack: Mapped[bool] = mapped_column(Boolean, default=False) # "Tanishdim" tugmasi talab etilishi
    send_telegram: Mapped[bool] = mapped_column(Boolean, default=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    author = relationship("User", foreign_keys=[author_id], lazy="selectin")
    reads = relationship("AnnouncementRead", back_populates="announcement", cascade="all, delete-orphan", lazy="selectin")


class AnnouncementRead(Base):
    __tablename__ = "announcement_reads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    announcement_id: Mapped[int] = mapped_column(Integer, ForeignKey("announcements.id", ondelete="CASCADE"), nullable=False)
    student_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    read_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    ip_address: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_acknowledged: Mapped[bool] = mapped_column(Boolean, default=False) # "Tanishdim" tugmasi bosilganligi

    announcement = relationship("Announcement", back_populates="reads")
    student = relationship("User", foreign_keys=[student_id], lazy="selectin")

    __table_args__ = (
        Index("ix_announcement_reads_ann_student", "announcement_id", "student_id", unique=True),
        Index("ix_announcement_reads_student", "student_id"),
    )


# 11. Captcha Challenge Model (Brute-Force & Bot Himoyasi)
class CaptchaChallenge(Base):
    __tablename__ = "captcha_challenges"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)  # UUID
    hashed_code: Mapped[str] = mapped_column(String(128), nullable=False)  # SHA-256 kichik harflarda
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    __table_args__ = (
        Index("ix_captcha_expires_at", "expires_at"),
    )
