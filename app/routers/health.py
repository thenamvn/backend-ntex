from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status, Query
from sqlmodel import Session

from ..dependencies import get_db_session
from ..schemas.health import HealthDataCreate, HealthDataRead, HealthDataStats
from ..schemas.user import UserRead
from ..services import get_current_user, health_service

router = APIRouter(prefix="/health", tags=["Health Data"])

@router.get("/timeseries")
async def get_timeseries_data(
    interval: str = Query(default="1 hour", description="Time bucket interval (e.g., '1 hour', '1 day')"),
    start_date: Optional[datetime] = Query(None, description="Start date for time series"),
    end_date: Optional[datetime] = Query(None, description="End date for time series"),
    db: Session = Depends(get_db_session),
    current_user: UserRead = Depends(get_current_user)
):
    """
    Get aggregated time-series data using TimescaleDB.
    
    **Query Parameters:**
    - **interval**: Time bucket interval ('1 hour', '1 day', '1 week')
    - **start_date**: Start date (ISO format, defaults to 7 days ago)
    - **end_date**: End date (ISO format, defaults to now)
    
    **Returns:**
    Aggregated statistics for each time bucket:
    - Average temperature and humidity
    - Count of records, crying events, and sick detections
    
    Useful for creating charts and dashboards.
    """
    try:
        data = health_service.get_time_series_data(
            db=db,
            user_id=current_user.id,
            interval=interval,
            start_date=start_date,
            end_date=end_date
        )
        return {"data": data}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving time-series data: {str(e)}"
        )
    
@router.post("/upload", response_model=HealthDataRead, status_code=status.HTTP_201_CREATED)
async def upload_health_data(
    temperature: float = Form(..., description="Body temperature in Celsius"),
    humidity: float = Form(..., description="Environmental humidity percentage"),
    notes: Optional[str] = Form(None, description="Optional notes"),
    audio: Optional[UploadFile] = File(None, description="Optional audio file for cry detection"),
    db: Session = Depends(get_db_session),
    current_user: UserRead = Depends(get_current_user)
):
    """
    Upload health monitoring data with optional audio file.
    
    **Required Fields:**
    - **temperature**: Baby's body temperature (°C)
    - **humidity**: Environmental humidity (%)
    
    **Optional Fields:**
    - **audio**: Audio file for cry detection analysis
    - **notes**: Additional notes or observations
    
    **Process:**
    1. Validates health data
    2. Saves audio file if provided
    3. Analyzes audio for baby crying using AI model
    4. Detects potential illness (crying + high temperature)
    5. Stores data in database
    6. Sends real-time alert via WebSocket if crying detected
    
    Returns the created health data record with analysis results.
    """
    # Create health data object
    health_data = HealthDataCreate(
        temperature=temperature,
        humidity=humidity,
        notes=notes
    )
    
    # Validate temperature range
    if not -10 <= temperature <= 50:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Temperature must be between -10°C and 50°C"
        )
    
    # Validate humidity range
    if not 0 <= humidity <= 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Humidity must be between 0% and 100%"
        )
    
    # Validate audio file if provided
    if audio:
        # Check file extension
        allowed_extensions = {".wav", ".mp3", ".m4a", ".ogg", ".flac"}
        file_ext = audio.filename.split(".")[-1].lower()
        
        if f".{file_ext}" not in allowed_extensions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid audio format. Allowed: {', '.join(allowed_extensions)}"
            )
    
    # Process and save health data
    try:
        result = await health_service.handle_health_upload(
            db=db,
            user_id=current_user.id,
            data=health_data,
            file=audio
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing health data: {str(e)}"
        )


@router.get("/history", response_model=List[HealthDataRead])
async def get_health_history(
    limit: int = Query(default=100, ge=1, le=1000, description="Maximum number of records"),
    offset: int = Query(default=0, ge=0, description="Number of records to skip"),
    cry_detected: Optional[bool] = Query(None, description="Filter by cry detection"),
    sick_detected: Optional[bool] = Query(None, description="Filter by sick detection"),
    db: Session = Depends(get_db_session),
    current_user: UserRead = Depends(get_current_user)
):
    """
    Get health monitoring history for the current user.
    
    **Query Parameters:**
    - **limit**: Maximum number of records to return (1-1000, default: 100)
    - **offset**: Number of records to skip for pagination (default: 0)
    - **cry_detected**: Filter by cry detection status (true/false)
    - **sick_detected**: Filter by sick detection status (true/false)
    
    Returns a list of health data records ordered by most recent first.
    """
    try:
        history = health_service.get_user_health_history(
            db=db,
            user_id=current_user.id,
            limit=limit,
            offset=offset,
            cry_detected=cry_detected,
            sick_detected=sick_detected
        )
        return history
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving health history: {str(e)}"
        )


@router.get("/stats", response_model=HealthDataStats)
async def get_health_statistics(
    db: Session = Depends(get_db_session),
    current_user: UserRead = Depends(get_current_user)
):
    """
    Get statistics for the current user's health data.
    
    **Returns:**
    - Total number of records
    - Count of cry detection events
    - Count of sick detection events
    - Average temperature
    - Average humidity
    - Latest health record
    
    Useful for dashboard analytics and monitoring trends.
    """
    try:
        stats = health_service.get_health_stats(db=db, user_id=current_user.id)
        return stats
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error calculating statistics: {str(e)}"
        )


@router.get("/{record_id}", response_model=HealthDataRead)
async def get_health_record(
    record_id: int,
    db: Session = Depends(get_db_session),
    current_user: UserRead = Depends(get_current_user)
):
    """
    Get a specific health data record by ID.
    
    **Parameters:**
    - **record_id**: ID of the health data record
    
    Only returns records belonging to the current user.
    """
    record = health_service.get_health_record(
        db=db,
        record_id=record_id,
        user_id=current_user.id
    )
    
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Health record not found"
        )
    
    return record


@router.get("/test/endpoint")
async def test_health():
    """Test endpoint to verify health router is working."""
    return {"message": "Health router is working!", "cry_detection": "AI model ready"}
