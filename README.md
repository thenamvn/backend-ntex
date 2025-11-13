# 👶 Baby Health Monitoring Backend API

A FastAPI-based backend server for monitoring baby health with real-time AI-powered crying detection. Built with Python, FastAPI, PostgreSQL/TimescaleDB, and integrated PyTorch models.

## 🚀 Features

- **👤 User Authentication**: JWT-based authentication with secure password hashing
- **📊 Health Data Monitoring**: Track temperature, humidity, and environmental conditions
- **🤖 AI Cry Detection**: Native Python-based audio analysis using machine learning models
- **🔥 Illness Detection**: Automatic detection of potential illness (crying + high temperature)
- **⚡ Real-time Alerts**: WebSocket connections for instant notifications
- **📈 Statistics Dashboard**: Historical data analysis and trend visualization
- **⏰ Time-Series Data**: TimescaleDB-optimized queries for time-based analytics
- **🔒 Secure API**: OAuth2 with password flow, encrypted tokens

## 🛠️ Tech Stack

| Component | Technology |
|-----------|------------|
| Framework | FastAPI |
| Language | Python 3.10+ |
| Database | PostgreSQL + TimescaleDB |
| ORM | SQLModel / SQLAlchemy 2.0 |
| Validation | Pydantic |
| Auth | JWT (python-jose) |
| AI/ML | PyTorch, TorchAudio, Librosa |
| Real-time | FastAPI WebSockets |

## 📁 Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app instance & WebSocket endpoint
│   ├── config.py               # Application settings
│   ├── dependencies.py         # Dependency injection
│   │
│   ├── db/
│   │   ├── database.py         # Database connection & session
│   │   └── models.py           # SQLModel table definitions
│   │
│   ├── routers/
│   │   ├── auth.py             # Authentication endpoints
│   │   └── health.py           # Health data endpoints
│   │
│   ├── schemas/
│   │   ├── user.py             # User Pydantic models
│   │   └── health.py           # Health data Pydantic models
│   │
│   ├── services/
│   │   ├── auth_service.py     # Authentication logic
│   │   ├── health_service.py   # Health data processing
│   │   └── cry_detection.py    # AI cry detection model
│   │
│   └── websocket/
│       └── connection_manager.py # WebSocket management
│
├── alembic/                    # Database migrations
├── models/                     # AI model files (.pth)
├── uploads/                    # Audio file storage
├── .env                        # Environment variables
├── requirements.txt            # Python dependencies
└── README.md                   # This file
```

## 🔧 Installation & Setup

### Prerequisites

- Python 3.10 or higher
- PostgreSQL with TimescaleDB extension
- pip or Poetry package manager

### 1. Clone the Repository

```bash
git clone <repository-url>
cd backend
```

### 2. Create Virtual Environment

```bash
# Windows
python -m venv venv
.\venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the backend directory:

```env
DATABASE_URL=postgresql://postgres:2182004nam@localhost:5433/babycare
JWT_SECRET=your-super-secret-key-change-this-in-production
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
DEBUG=True
```

### 5. Setup Database with Docker

```bash
# Start TimescaleDB container
docker-compose up -d

# Check if running
docker ps
```

### 6. Run the Server

```bash
# Development mode with auto-reload
uvicorn app.main:app --reload

# Production mode
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

The API will be available at:
- **API**: http://localhost:8000
- **Interactive Docs**: http://localhost:8000/docs
- **Alternative Docs**: http://localhost:8000/redoc

---

## 📡 Complete API Documentation

### Base URL
```
http://localhost:8000
```

---

## 🔐 Authentication Endpoints

### 1. Register New User

**Endpoint**: `POST /auth/register`

**Description**: Create a new user account.

**Request Body** (JSON):
```json
{
  "email": "user@example.com",
  "password": "securePassword123",
  "name": "John Doe"
}
```

**Response** (201 Created):
```json
{
  "id": 1,
  "email": "user@example.com",
  "name": "John Doe",
  "created_at": "2025-11-13T12:00:00.000Z"
}
```

**Error Responses**:
- `400 Bad Request`: Email already registered
- `422 Unprocessable Entity`: Invalid input data

**cURL Example**:
```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "securePassword123",
    "name": "John Doe"
  }'
```

---

### 2. Login (OAuth2 Token)

**Endpoint**: `POST /auth/token`

**Description**: Authenticate and get access token (OAuth2 password flow).

**Request Body** (Form Data):
```
username=user@example.com
password=securePassword123
```

**Response** (200 OK):
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Error Responses**:
- `401 Unauthorized`: Invalid credentials

**cURL Example**:
```bash
curl -X POST http://localhost:8000/auth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=user@example.com&password=securePassword123"
```

---

### 3. Login (JSON)

**Endpoint**: `POST /auth/login`

**Description**: Alternative login endpoint accepting JSON payload.

**Request Body** (JSON):
```json
{
  "email": "user@example.com",
  "password": "securePassword123"
}
```

**Response** (200 OK):
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "name": "John Doe"
  }
}
```

**cURL Example**:
```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "securePassword123"
  }'
```

---

### 4. Get Current User

**Endpoint**: `GET /auth/me`

**Description**: Get information about the currently authenticated user.

**Headers**:
```
Authorization: Bearer <access_token>
```

**Response** (200 OK):
```json
{
  "id": 1,
  "email": "user@example.com",
  "name": "John Doe",
  "created_at": "2025-11-13T12:00:00.000Z"
}
```

**Error Responses**:
- `401 Unauthorized`: Invalid or expired token

**cURL Example**:
```bash
curl -X GET http://localhost:8000/auth/me \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

## 🏥 Health Data Endpoints

### 5. Upload Health Data

**Endpoint**: `POST /health/upload`

**Description**: Upload health monitoring data with optional audio file for cry detection.

**Headers**:
```
Authorization: Bearer <access_token>
Content-Type: multipart/form-data
```

**Request Body** (Form Data):
```
temperature: 37.5          (required, float)
humidity: 65.0            (required, float)
notes: "Baby seems restless" (optional, string)
audio: <file>             (optional, audio file)
```

**Supported Audio Formats**: WAV, MP3, M4A, OGG, FLAC

**Response** (201 Created):
```json
{
  "id": 1,
  "user_id": 1,
  "temperature": 37.5,
  "humidity": 65.0,
  "audio_url": "uploads/audio_1_20251113_120000.wav",
  "cry_detected": true,
  "sick_detected": false,
  "created_at": "2025-11-13T12:00:00.000Z",
  "notes": "Baby seems restless"
}
```

**Error Responses**:
- `400 Bad Request`: Invalid temperature/humidity range or file format
- `401 Unauthorized`: Missing or invalid token
- `500 Internal Server Error`: Processing error

**cURL Example**:
```bash
curl -X POST http://localhost:8000/health/upload \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -F "temperature=37.5" \
  -F "humidity=65.0" \
  -F "notes=Baby seems restless" \
  -F "audio=@baby_cry.wav"
```

**Python Example**:
```python
import requests

url = "http://localhost:8000/health/upload"
headers = {"Authorization": "Bearer YOUR_ACCESS_TOKEN"}
data = {
    "temperature": 37.5,
    "humidity": 65.0,
    "notes": "Baby seems restless"
}
files = {"audio": open("baby_cry.wav", "rb")}

response = requests.post(url, headers=headers, data=data, files=files)
print(response.json())
```

---

### 6. Get Health History

**Endpoint**: `GET /health/history`

**Description**: Retrieve health monitoring history with optional filters.

**Headers**:
```
Authorization: Bearer <access_token>
```

**Query Parameters**:
- `limit` (optional, int, default=100): Maximum records to return (1-1000)
- `offset` (optional, int, default=0): Number of records to skip
- `cry_detected` (optional, bool): Filter by cry detection status
- `sick_detected` (optional, bool): Filter by sick detection status
- `start_date` (optional, ISO datetime): Filter records after this date
- `end_date` (optional, ISO datetime): Filter records before this date

**Response** (200 OK):
```json
[
  {
    "id": 3,
    "user_id": 1,
    "temperature": 38.2,
    "humidity": 70.0,
    "audio_url": "uploads/audio_1_20251113_150000.wav",
    "cry_detected": true,
    "sick_detected": true,
    "created_at": "2025-11-13T15:00:00.000Z",
    "notes": "High temperature detected"
  },
  {
    "id": 2,
    "user_id": 1,
    "temperature": 37.5,
    "humidity": 65.0,
    "audio_url": null,
    "cry_detected": false,
    "sick_detected": false,
    "created_at": "2025-11-13T12:00:00.000Z",
    "notes": null
  }
]
```

**cURL Example**:
```bash
# Get last 10 records where crying was detected
curl -X GET "http://localhost:8000/health/history?limit=10&cry_detected=true" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

### 7. Get Health Statistics

**Endpoint**: `GET /health/stats`

**Description**: Get aggregated statistics for user's health data.

**Headers**:
```
Authorization: Bearer <access_token>
```

**Response** (200 OK):
```json
{
  "total_records": 150,
  "cry_detected_count": 25,
  "sick_detected_count": 5,
  "avg_temperature": 37.2,
  "avg_humidity": 62.5,
  "latest_record": {
    "id": 150,
    "user_id": 1,
    "temperature": 37.8,
    "humidity": 68.0,
    "audio_url": "uploads/audio_1_20251113_180000.wav",
    "cry_detected": false,
    "sick_detected": false,
    "created_at": "2025-11-13T18:00:00.000Z",
    "notes": null
  }
}
```

**cURL Example**:
```bash
curl -X GET http://localhost:8000/health/stats \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

### 8. Get Specific Health Record

**Endpoint**: `GET /health/{record_id}`

**Description**: Retrieve a specific health data record by ID.

**Headers**:
```
Authorization: Bearer <access_token>
```

**Path Parameters**:
- `record_id` (required, int): ID of the health record

**Response** (200 OK):
```json
{
  "id": 1,
  "user_id": 1,
  "temperature": 37.5,
  "humidity": 65.0,
  "audio_url": "uploads/audio_1_20251113_120000.wav",
  "cry_detected": true,
  "sick_detected": false,
  "created_at": "2025-11-13T12:00:00.000Z",
  "notes": "Baby seems restless"
}
```

**Error Responses**:
- `404 Not Found`: Record doesn't exist or doesn't belong to user

**cURL Example**:
```bash
curl -X GET http://localhost:8000/health/1 \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

### 9. Get Time-Series Data

**Endpoint**: `GET /health/timeseries`

**Description**: Get aggregated time-series data using TimescaleDB for charts and dashboards.

**Headers**:
```
Authorization: Bearer <access_token>
```

**Query Parameters**:
- `interval` (optional, string, default="1 hour"): Time bucket interval
  - Examples: "1 hour", "6 hours", "1 day", "1 week"
- `start_date` (optional, ISO datetime): Start date (default: 7 days ago)
- `end_date` (optional, ISO datetime): End date (default: now)

**Response** (200 OK):
```json
{
  "data": [
    {
      "time": "2025-11-13T18:00:00.000Z",
      "avg_temperature": 37.3,
      "avg_humidity": 64.5,
      "record_count": 12,
      "cry_count": 2,
      "sick_count": 0
    },
    {
      "time": "2025-11-13T17:00:00.000Z",
      "avg_temperature": 37.5,
      "avg_humidity": 65.8,
      "record_count": 15,
      "cry_count": 3,
      "sick_count": 1
    }
  ]
}
```

**cURL Example**:
```bash
# Get hourly statistics for the last 24 hours
curl -X GET "http://localhost:8000/health/timeseries?interval=1 hour" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"

# Get daily statistics for the last month
curl -X GET "http://localhost:8000/health/timeseries?interval=1 day&start_date=2025-10-13T00:00:00Z" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

### 10. Test Health Endpoint

**Endpoint**: `GET /health/test/endpoint`

**Description**: Test endpoint to verify health router is working.

**Response** (200 OK):
```json
{
  "message": "Health router is working!",
  "cry_detection": "AI model ready"
}
```

**cURL Example**:
```bash
curl -X GET http://localhost:8000/health/test/endpoint
```

---

## 🔌 WebSocket Connection

### Real-time Notifications

**Endpoint**: `WS /ws/{user_id}`

**Description**: Establish WebSocket connection for real-time crying alerts.

**Query Parameters**:
- `token` (required): JWT access token

**Connection URL**:
```
ws://localhost:8000/ws/1?token=YOUR_ACCESS_TOKEN
```

**Messages Received**:
```json
{
  "event": "CRY_DETECTED",
  "sick_detected": true,
  "timestamp": "2025-11-13T12:00:00.000Z",
  "data": {
    "temperature": 38.5,
    "humidity": 70.0
  }
}
```

**JavaScript Example**:
```javascript
const userId = 1;
const token = "YOUR_ACCESS_TOKEN";
const ws = new WebSocket(`ws://localhost:8000/ws/${userId}?token=${token}`);

ws.onopen = () => {
    console.log('Connected to WebSocket');
};

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    
    if (data.event === 'CRY_DETECTED') {
        console.log('Baby is crying!');
        if (data.sick_detected) {
            alert('⚠️ Baby may be sick! Check temperature!');
        }
    }
};

ws.onerror = (error) => {
    console.error('WebSocket error:', error);
};

ws.onclose = () => {
    console.log('WebSocket connection closed');
};
```

**Python Example**:
```python
import asyncio
import websockets
import json

async def listen_to_alerts():
    user_id = 1
    token = "YOUR_ACCESS_TOKEN"
    uri = f"ws://localhost:8000/ws/{user_id}?token={token}"
    
    async with websockets.connect(uri) as websocket:
        print("Connected to WebSocket")
        
        while True:
            message = await websocket.recv()
            data = json.loads(message)
            
            if data['event'] == 'CRY_DETECTED':
                print(f"🚨 Baby crying detected!")
                if data['sick_detected']:
                    print(f"⚠️ Baby may be sick!")

asyncio.run(listen_to_alerts())
```

---

## 🧪 Complete Testing Examples

### Full Workflow Test (Python)

```python
import requests
import time

BASE_URL = "http://localhost:8000"

# 1. Register
print("1. Registering user...")
register_response = requests.post(f"{BASE_URL}/auth/register", json={
    "email": f"test_{int(time.time())}@example.com",
    "password": "testPassword123",
    "name": "Test User"
})
print(f"✅ User registered: {register_response.json()}")

# 2. Login
print("\n2. Logging in...")
login_response = requests.post(f"{BASE_URL}/auth/login", json={
    "email": register_response.json()['email'],
    "password": "testPassword123"
})
token = login_response.json()['access_token']
print(f"✅ Token received: {token[:20]}...")

# 3. Get user info
print("\n3. Getting user info...")
headers = {"Authorization": f"Bearer {token}"}
me_response = requests.get(f"{BASE_URL}/auth/me", headers=headers)
print(f"✅ User info: {me_response.json()}")

# 4. Upload health data
print("\n4. Uploading health data...")
data = {"temperature": 37.5, "humidity": 65.0, "notes": "Test upload"}
upload_response = requests.post(
    f"{BASE_URL}/health/upload",
    headers=headers,
    data=data
)
print(f"✅ Health data uploaded: {upload_response.json()}")

# 5. Get history
print("\n5. Getting health history...")
history_response = requests.get(f"{BASE_URL}/health/history", headers=headers)
print(f"✅ History: {len(history_response.json())} records")

# 6. Get statistics
print("\n6. Getting statistics...")
stats_response = requests.get(f"{BASE_URL}/health/stats", headers=headers)
print(f"✅ Stats: {stats_response.json()}")

# 7. Get time-series data
print("\n7. Getting time-series data...")
timeseries_response = requests.get(
    f"{BASE_URL}/health/timeseries?interval=1 hour",
    headers=headers
)
print(f"✅ Time-series data: {len(timeseries_response.json()['data'])} buckets")
```

---

## 📊 Response Status Codes

| Code | Meaning | Description |
|------|---------|-------------|
| 200 | OK | Request successful |
| 201 | Created | Resource created successfully |
| 400 | Bad Request | Invalid input data |
| 401 | Unauthorized | Missing or invalid authentication |
| 404 | Not Found | Resource not found |
| 422 | Unprocessable Entity | Validation error |
| 500 | Internal Server Error | Server error |

---

## 🔐 Security Best Practices

- Store JWT tokens securely (not in localStorage for web apps)
- Use HTTPS in production
- Rotate JWT_SECRET regularly
- Implement rate limiting
- Validate all user inputs
- Use strong passwords (min 8 characters)

---

## 📚 Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLModel Documentation](https://sqlmodel.tiangolo.com/)
- [TimescaleDB Documentation](https://docs.timescale.com/)
- [PyTorch Documentation](https://pytorch.org/docs/)

---

## 📄 License

This project is licensed under the MIT License.

---

**Built with ❤️ using FastAPI, Python, and TimescaleDB**