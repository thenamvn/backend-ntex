from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class HealthDataBase(BaseModel):
    """Base health data schema."""
    temperature: float = Field(..., ge=-10, le=50, description="Body temperature in Celsius")
    humidity: float = Field(..., ge=0, le=100, description="Environmental humidity percentage")
    notes: Optional[str] = Field(None, max_length=500, description="Optional notes")


class HealthDataCreate(HealthDataBase):
    """Schema for creating health data (incoming from mobile app)."""
    pass


class HealthDataRead(HealthDataBase):
    """Schema for reading health data (response)."""
    id: int
    user_id: int
    audio_url: Optional[str]
    cry_detected: bool
    sick_detected: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class HealthDataWithUser(HealthDataRead):
    """Schema for health data with user information."""
    user: "UserRead"
    
    class Config:
        from_attributes = True


class HealthDataStats(BaseModel):
    """Statistics for health data."""
    total_records: int
    cry_detected_count: int
    sick_detected_count: int
    avg_temperature: float
    avg_humidity: float
    latest_record: Optional[HealthDataRead]


class HealthDataFilter(BaseModel):
    """Filter parameters for health data queries."""
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    cry_detected: Optional[bool] = None
    sick_detected: Optional[bool] = None
    limit: int = Field(default=100, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)


# Avoid circular imports
from .user import UserRead
HealthDataWithUser.model_rebuild()
