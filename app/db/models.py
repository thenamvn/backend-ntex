from typing import List, Optional
from sqlmodel import Field, Relationship, SQLModel, Column, Integer, TIMESTAMP
from sqlalchemy import func
from datetime import datetime


class User(SQLModel, table=True):
    """User model for authentication and data ownership."""
    
    __tablename__ = "users"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(sa_column_kwargs={"unique": True}, index=True)
    password_hash: str
    name: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    health_data: List["HealthData"] = Relationship(back_populates="user")


class HealthData(SQLModel, table=True):
    """
    Health data model storing baby monitoring information.
    Optimized for time-series data with TimescaleDB.
    
    Note: Uses composite primary key (id, created_at) as required by TimescaleDB.
    """
    
    __tablename__ = "health_data"
    
    # Composite primary key: id + created_at (required for TimescaleDB hypertable)
    id: int = Field(
        sa_column=Column(
            Integer,
            primary_key=True,
            autoincrement=True
        )
    )
    
    created_at: datetime = Field(
        sa_column=Column(
            TIMESTAMP,
            primary_key=True,
            server_default=func.now()
        ),
        description="Timestamp for time-series data"
    )
    
    # User relationship
    user_id: int = Field(foreign_key="users.id", index=True)
    
    # Sensor data
    temperature: float = Field(description="Body temperature in Celsius")
    humidity: float = Field(description="Environmental humidity percentage")
    
    # Audio analysis
    audio_url: Optional[str] = Field(default=None, description="Path to saved audio file")
    cry_detected: bool = Field(default=False, description="Whether crying was detected by AI")
    
    # Health status
    sick_detected: bool = Field(default=False, description="Whether potential illness was detected")
    
    # Metadata
    notes: Optional[str] = Field(default=None, description="Optional notes from user")
    
    # Relationships
    user: User = Relationship(back_populates="health_data")