### 🧠 GitHub Instructions — Baby Health Monitoring Backend (FastAPI + Python)

=======================================================================

🚀 **Project Overview**
------------------

This is the backend server for the Baby Health Monitoring App, rebuilt entirely in Python with FastAPI. It receives real-time health data (temperature, humidity, and baby crying audio), **natively analyzes crying events using a Python AI model**, and detects potential illness based on body temperature.

🧱 **Tech Stack**
------------

| Layer | Technology |
| :--- | :--- |
| Runtime | Python (v3.10+) |
| Framework | FastAPI |
| Language | Python |
| Package Manager | Pip / Poetry |
| Database | PostgreSQL + TimescaleDB |
| ORM | SQLModel / SQLAlchemy 2.0 |
| Validation | Pydantic |
| Auth | JWT (python-jose) |
| Realtime | FastAPI WebSockets |
| File Uploads | FastAPI `UploadFile` |
| **AI Cry Detection** | **Integrated Python Model (e.g., PyTorch, TensorFlow/Keras)** |

📁 **Project Structure**
-------------------

```backend/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app instance
│   ├── config.py               # Environment settings
│   ├── dependencies.py         # Common dependencies (e.g., get_db_session)
│   │
│   ├── db/
│   │   ├── __init__.py
│   │   ├── database.py         # Database engine and session setup
│   │   └── models.py           # SQLModel table definitions
│   │
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── auth.py             # /auth endpoints
│   │   └── health.py           # /health endpoints
│   │
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── health.py           # Pydantic models for health data
│   │   └── user.py             # Pydantic models for users
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── auth_service.py     # User registration, login, password hashing
│   │   ├── health_service.py   # Core logic for health data processing
│   │   └── cry_detection.py    # AI model loading and inference logic
│   │
│   └── websocket/
│       ├── __init__.py
│       └── connection_manager.py # WebSocket connection manager
│
├── alembic/                    # Database migrations
├── models/                     # Saved AI model files (e.g., model.pth)
├── uploads/                    # Directory for storing audio files locally
├── .env
├── requirements.txt
└── README.md
```

⚙️ **Environment Variables (.env)**
--------------------------------

```env
DATABASE_URL=postgresql://user:password@localhost:5432/babycare
JWT_SECRET=supersecretkey
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

🧩 **Database Schema (app/db/models.py)**
--------------------------------------

```python
# Using SQLModel for combined ORM and Pydantic features
from typing import List, Optional
from sqlmodel import Field, Relationship, SQLModel
import datetime as dt

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(sa_column_kwargs={"unique": True}, index=True)
    password_hash: str
    name: Optional[str] = None
    created_at: dt.datetime = Field(default_factory=dt.datetime.utcnow)
    
    health_data: List["HealthData"] = Relationship(back_populates="user")

class HealthData(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    temperature: float
    humidity: float
    audio_url: Optional[str] = None
    cry_detected: bool = Field(default=False)
    sick_detected: bool = Field(default=False)
    created_at: dt.datetime = Field(default_factory=dt.datetime.utcnow)
    
    user: User = Relationship(back_populates="health_data")
```

📡 **API Endpoints**
---------------

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/auth/register` | Register new user |
| `POST` | `/auth/token` | Authenticate user (login) |
| `POST` | `/health/upload` | Upload health data + optional audio file |
| `GET` | `/health/history`| Retrieve health history of current user |
| `WS` | `/ws/{user_id}` | Realtime crying alerts (WebSockets) |

🔁 **Core Logic Flow**
-------------------

1.  Mobile app sends a `POST /health/upload` request with health data and an optional audio file.
2.  The server validates the incoming data using a Pydantic schema.
3.  If an audio file is present, it's saved locally.
4.  The server calls the internal **`cry_detection_service`** to analyze the audio file with the pre-loaded AI model.
5.  The analysis result (`cry_detected`) and health data are saved to the database via SQLModel.
6.  If `cry_detected` is true and `temperature > 38°C`, `sickDetected` is set to `True`.
7.  A WebSocket message is broadcast to the specific user to trigger a real-time alert on their device.

⚙️ **Example Code**
----------------

**File: `app/routers/health.py`**
```python
from fastapi import APIRouter, Depends, UploadFile, File, Form
from sqlalchemy.orm import Session
from .. import dependencies, schemas, services

router = APIRouter(prefix="/health", tags=["Health"])

@router.post("/upload", response_model=schemas.HealthDataRead)
async def upload_health_data(
    temperature: float = Form(...),
    humidity: float = Form(...),
    audio: UploadFile = File(None),
    db: Session = Depends(dependencies.get_db_session),
    current_user: schemas.UserRead = Depends(services.get_current_user)
):
    """
    Handles health data upload, including an optional audio file.
    """
    health_data_in = schemas.HealthDataCreate(temperature=temperature, humidity=humidity)
    
    return await services.health_service.handle_health_upload(
        db=db, user_id=current_user.id, data=health_data_in, file=audio
    )
```

**File: `app/services/health_service.py`**
```python
from sqlalchemy.orm import Session
from fastapi import UploadFile
from . import cry_detection_service
from ..db import models
from ..schemas import health as health_schemas
from ..websocket import connection_manager
import shutil

async def handle_health_upload(db: Session, user_id: int, data: health_schemas.HealthDataCreate, file: UploadFile | None):
    cry_detected = False
    sick_detected = False
    audio_url = None

    if file:
        # Save file locally
        file_path = f"uploads/{file.filename}"
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        audio_url = file_path
        
        # Analyze using the integrated AI model
        cry_detected = cry_detection_service.analyze(file_path)

    if cry_detected and data.temperature > 38.0:
        sick_detected = True

    db_record = models.HealthData(
        user_id=user_id,
        temperature=data.temperature,
        humidity=data.humidity,
        audio_url=audio_url,
        cry_detected=cry_detected,
        sick_detected=sick_detected,
    )
    db.add(db_record)
    db.commit()
    db.refresh(db_record)

    if cry_detected:
        await connection_manager.broadcast_to_user(
            user_id,
            {"event": "CRY_DETECTED", "sick_detected": sick_detected}
        )

    return db_record
```

🧰 **Commands**
------------

```bash
# Install dependencies
pip install -r requirements.txt

# Initialize Alembic for migrations
alembic init alembic

# Create a new migration after changing models.py
alembic revision --autogenerate -m "Initial models"

# Apply migrations to the database
alembic upgrade head

# Start development server with live reload
uvicorn app.main:app --reload

# Start production server (example with Gunicorn)
# gunicorn -w 4 -k uvicorn.workers.UvicornWorker app.main:app
```