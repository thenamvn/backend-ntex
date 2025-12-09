import os
import shutil
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from fastapi import UploadFile, HTTPException, status
from sqlmodel import Session, select, func, text

from ..config import settings
from ..db.models import HealthData, User
from ..schemas.health import HealthDataCreate, HealthDataRead, HealthDataStats
from .cry_detection import CryDetectionService
from ..websocket import connection_manager


class HealthService:
    """Service for handling health data operations with TimescaleDB optimization."""
    
    def __init__(self):
        self.cry_detector = CryDetectionService()
    
    async def handle_health_upload(
        self,
        db: Session,
        user_id: int,
        data: HealthDataCreate,
        file: Optional[UploadFile] = None
    ) -> HealthData:
        """
        Handle health data upload with optional audio file.
        
        Args:
            db: Database session
            user_id: User ID
            data: Health data to save
            file: Optional audio file
        
        Returns:
            Created health data record
        """
        cry_detected = False
        audio_url = None
        
        # Process audio file if present
        if file:
            # Ensure upload directory exists
            os.makedirs(settings.upload_dir, exist_ok=True)
            
            # Generate unique filename
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            file_extension = os.path.splitext(file.filename)[1]
            filename = f"audio_{user_id}_{timestamp}{file_extension}"
            file_path = os.path.join(settings.upload_dir, filename)
            
            # Save file
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            audio_url = file_path
            
            # Analyze audio for crying
            try:
                cry_detected = self.cry_detector.analyze(file_path)
            except Exception as e:
                print(f"Error analyzing audio: {e}")
        
        # ✅ LOGIC: Xác định sick_detected dựa trên nhiệt độ
        # Nhiệt độ >= 38.0°C → sốt → sick_detected = True
        sick_detected = data.temperature >= 38.0
        
        # 🔍 Debug log
        print(f"🌡️ Temperature: {data.temperature}°C → sick_detected: {sick_detected}")
        
        # ✅ FIX: Dùng raw SQL INSERT để bypass SQLModel composite key issue
        insert_query = text("""
            INSERT INTO health_data (
                user_id, temperature, humidity, audio_url, 
                cry_detected, sick_detected, notes, created_at
            ) VALUES (
                :user_id, :temperature, :humidity, :audio_url,
                :cry_detected, :sick_detected, :notes, NOW()
            )
            RETURNING id, created_at
        """)
        
        result = db.execute(
            insert_query,
            {
                "user_id": user_id,
                "temperature": data.temperature,
                "humidity": data.humidity,
                "audio_url": audio_url,
                "cry_detected": cry_detected,
                "sick_detected": sick_detected,
                "notes": data.notes
            }
        )
        
        row = result.fetchone()
        db.commit()
        
        # Fetch the complete record
        db_record = HealthData(
            id=row[0],
            user_id=row[1],
            temperature=row[2],
            humidity=row[3],
            audio_url=row[4],
            cry_detected=row[5],
            sick_detected=row[6],
            notes=row[7],
            created_at=row[8]
        )
        
        # ✅ Verify saved value
        print(f"💾 Saved to DB → sick_detected: {db_record.sick_detected}")
        
        # 🚀 Send WebSocket update
        await self._send_health_update(user_id, db_record)
        
        return db_record
    
    async def _send_health_update(self, user_id: int, health_data: HealthData):
        """
        Send health data update via WebSocket.
        
        Args:
            user_id: User ID to send to
            health_data: Health data record
        """
        message = {
            "event": "HEALTH_UPDATE",
            "data": {
                "id": health_data.id,
                "temperature": health_data.temperature,
                "humidity": health_data.humidity,
                "cry_detected": health_data.cry_detected,
                "sick_detected": health_data.sick_detected,
                "created_at": health_data.created_at.isoformat(),
                "notes": health_data.notes
            }
        }
        
        # ✅ Phân loại cảnh báo theo mức độ nghiêm trọng
        needs_diaper_change = health_data.humidity > 80.0
        
        if health_data.sick_detected and health_data.cry_detected:
            # 🚨 Cảnh báo mức CAO: Khóc + Sốt
            message["event"] = "CRITICAL_ALERT"
            message["alert"] = "🚨 BÉ ĐANG SỐT VÀ KHÓC! Kiểm tra ngay!"
            message["severity"] = "critical"
        
        elif needs_diaper_change and health_data.cry_detected:
            # 💩 Cảnh báo: Độ ẩm cao + Khóc → Đi vệ sinh
            message["event"] = "DIAPER_ALERT"
            message["alert"] = "💩 Bé có thể đã đi vệ sinh! Độ ẩm cao và đang khóc."
            message["severity"] = "warning"
        
        elif needs_diaper_change:
            # 💧 Cảnh báo: Chỉ độ ẩm cao → Có thể đi vệ sinh
            message["event"] = "HUMIDITY_ALERT"
            message["alert"] = "💧 Độ ẩm cao! Bé có thể đã đi vệ sinh."
            message["severity"] = "info"
        
        elif health_data.sick_detected:
            # ⚠️ Cảnh báo mức TRUNG BÌNH: Chỉ sốt
            message["event"] = "FEVER_ALERT"
            message["alert"] = "⚠️ Bé đang sốt! Nhiệt độ cao hơn 38°C"
            message["severity"] = "warning"
        
        elif health_data.cry_detected:
            # ℹ️ Thông báo: Chỉ khóc (không sốt, độ ẩm bình thường)
            message["event"] = "CRY_DETECTED"
            message["alert"] = "ℹ️ Bé đang khóc"
            message["severity"] = "info"
        
        try:
            await connection_manager.broadcast_to_user(user_id, message)
            print(f"📤 Sent health update to user {user_id}: {message['event']}")
        except Exception as e:
            print(f"❌ Error sending WebSocket message: {e}")
    
    def get_user_health_history(
        self,
        db: Session,
        user_id: int,
        limit: int = 100,
        offset: int = 0,
        cry_detected: Optional[bool] = None,
        sick_detected: Optional[bool] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[HealthData]:
        """
        Get health history for a user with optional filters.
        Optimized for TimescaleDB time-series queries.
        """
        statement = select(HealthData).where(HealthData.user_id == user_id)
        
        if cry_detected is not None:
            statement = statement.where(HealthData.cry_detected == cry_detected)
        
        if sick_detected is not None:
            statement = statement.where(HealthData.sick_detected == sick_detected)
        
        if start_date:
            statement = statement.where(HealthData.created_at >= start_date)
        
        if end_date:
            statement = statement.where(HealthData.created_at <= end_date)
        
        statement = statement.order_by(HealthData.created_at.desc())
        statement = statement.offset(offset).limit(limit)
        
        results = db.exec(statement).all()
        return results
    
    def get_health_stats(self, db: Session, user_id: int) -> HealthDataStats:
        """
        Get SUMMARY statistics for user's health data.
        
        ⚠️ This is for OVERVIEW only, NOT for charts!
        For charts, use get_chart_data_* methods.
        
        Returns:
            HealthDataStats: Summary counts and averages
        """
        # Total records
        total_statement = select(func.count(HealthData.id)).where(HealthData.user_id == user_id)
        total_records = db.exec(total_statement).one()
        
        # Cry detected count
        cry_statement = select(func.count(HealthData.id)).where(
            HealthData.user_id == user_id,
            HealthData.cry_detected == True
        )
        cry_detected_count = db.exec(cry_statement).one()
        
        # Sick detected count
        sick_statement = select(func.count(HealthData.id)).where(
            HealthData.user_id == user_id,
            HealthData.sick_detected == True
        )
        sick_detected_count = db.exec(sick_statement).one()
        
        # Average temperature and humidity
        avg_statement = select(
            func.avg(HealthData.temperature),
            func.avg(HealthData.humidity)
        ).where(HealthData.user_id == user_id)
        avg_result = db.exec(avg_statement).one()
        avg_temperature = avg_result[0] or 0.0
        avg_humidity = avg_result[1] or 0.0
        
        # Latest record
        latest_statement = select(HealthData).where(
            HealthData.user_id == user_id
        ).order_by(HealthData.created_at.desc()).limit(1)
        latest_record = db.exec(latest_statement).first()
        
        return HealthDataStats(
            total_records=total_records,
            cry_detected_count=cry_detected_count,
            sick_detected_count=sick_detected_count,
            avg_temperature=round(avg_temperature, 2),
            avg_humidity=round(avg_humidity, 2),
            latest_record=latest_record
        )
    
    # ========================================
    # 🆕 NEW CHART DATA METHODS
    # ========================================
    
    def get_chart_data_temperature_humidity(
        self,
        db: Session,
        user_id: int,
        interval: str = "1 hour",
        days: int = 1
    ) -> Dict[str, Any]:
        """
        📈 LINE CHART: Nhiệt độ & Độ ẩm theo thời gian
        
        Args:
            db: Database session
            user_id: User ID
            interval: Time bucket ('1 hour', '6 hours', '1 day')
            days: Number of days to look back (1, 7, 30)
        
        Returns:
            {
                "labels": ["2025-11-13 08:00", "2025-11-13 09:00", ...],
                "temperature": [37.2, 37.5, 38.1, ...],
                "humidity": [65.0, 68.5, 72.0, ...]
            }
        
        Usage in Flutter:
            - Use fl_chart LineChart
            - X-axis: time labels
            - Y-axis: temperature (line 1), humidity (line 2)
        """
        start_date = datetime.utcnow() - timedelta(days=days)
        end_date = datetime.utcnow()
        
        query = text("""
            SELECT
                time_bucket(:interval, created_at) AS time_bucket,
                AVG(temperature) as avg_temperature,
                AVG(humidity) as avg_humidity
            FROM health_data
            WHERE user_id = :user_id
                AND created_at >= :start_date
                AND created_at <= :end_date
            GROUP BY time_bucket
            ORDER BY time_bucket ASC
        """)
        
        result = db.execute(
            query,
            {
                "interval": interval,
                "user_id": user_id,
                "start_date": start_date,
                "end_date": end_date
            }
        ).fetchall()
        
        return {
            "labels": [row[0].strftime("%m/%d %H:%M") for row in result],
            "temperature": [round(float(row[1]), 1) if row[1] else None for row in result],
            "humidity": [round(float(row[2]), 1) if row[2] else None for row in result]
        }
    
    def get_chart_data_cry_frequency(
        self,
        db: Session,
        user_id: int,
        interval: str = "1 hour",
        days: int = 7
    ) -> Dict[str, Any]:
        """
        📊 BAR CHART: Số lần khóc theo thời gian
        
        Args:
            db: Database session
            user_id: User ID
            interval: Time bucket ('1 hour', '1 day')
            days: Number of days to look back
        
        Returns:
            {
                "labels": ["Mon", "Tue", "Wed", ...],
                "cry_count": [5, 3, 8, 2, 1, 4, 6],
                "sick_count": [1, 0, 2, 0, 0, 1, 1]
            }
        
        Usage in Flutter:
            - Use fl_chart BarChart
            - X-axis: day labels
            - Y-axis: count
            - Two bar groups: cry_count (blue), sick_count (red)
        """
        start_date = datetime.utcnow() - timedelta(days=days)
        end_date = datetime.utcnow()
        
        query = text("""
            SELECT
                time_bucket(:interval, created_at) AS time_bucket,
                SUM(CASE WHEN cry_detected THEN 1 ELSE 0 END) as cry_count,
                SUM(CASE WHEN sick_detected THEN 1 ELSE 0 END) as sick_count
            FROM health_data
            WHERE user_id = :user_id
                AND created_at >= :start_date
                AND created_at <= :end_date
            GROUP BY time_bucket
            ORDER BY time_bucket ASC
        """)
        
        result = db.execute(
            query,
            {
                "interval": interval,
                "user_id": user_id,
                "start_date": start_date,
                "end_date": end_date
            }
        ).fetchall()
        
        return {
            "labels": [row[0].strftime("%a %d") for row in result],
            "cry_count": [int(row[1]) for row in result],
            "sick_count": [int(row[2]) for row in result]
        }
    
    def get_chart_data_health_distribution(
        self,
        db: Session,
        user_id: int,
        days: int = 7
    ) -> Dict[str, Any]:
        """
        🥧 PIE CHART: Phân bố trạng thái sức khỏe
        
        Args:
            db: Database session
            user_id: User ID
            days: Number of days to look back
        
        Returns:
            {
                "labels": ["Bình thường", "Khóc", "Sốt", "Nguy hiểm"],
                "values": [120, 15, 8, 3],
                "percentages": [82.2, 10.3, 5.5, 2.1]
            }
        
        Usage in Flutter:
            - Use fl_chart PieChart
            - Each segment: label + percentage
            - Colors: green, yellow, orange, red
        """
        start_date = datetime.utcnow() - timedelta(days=days)
        
        query = text("""
            SELECT
                COUNT(*) FILTER (WHERE NOT cry_detected AND NOT sick_detected) as normal,
                COUNT(*) FILTER (WHERE cry_detected AND NOT sick_detected) as crying,
                COUNT(*) FILTER (WHERE NOT cry_detected AND sick_detected) as fever,
                COUNT(*) FILTER (WHERE cry_detected AND sick_detected) as critical
            FROM health_data
            WHERE user_id = :user_id
                AND created_at >= :start_date
        """)
        
        result = db.execute(query, {"user_id": user_id, "start_date": start_date}).fetchone()
        
        total = sum(result) if result else 0
        
        if total == 0:
            return {
                "labels": ["Bình thường", "Khóc", "Sốt", "Nguy hiểm"],
                "values": [0, 0, 0, 0],
                "percentages": [0, 0, 0, 0],
                "colors": ["#4CAF50", "#FFC107", "#FF9800", "#F44336"]
            }
        
        return {
            "labels": ["Bình thường", "Khóc", "Sốt", "Nguy hiểm"],
            "values": [result[0], result[1], result[2], result[3]],
            "percentages": [
                round(result[0] / total * 100, 1),
                round(result[1] / total * 100, 1),
                round(result[2] / total * 100, 1),
                round(result[3] / total * 100, 1)
            ],
            "colors": ["#4CAF50", "#FFC107", "#FF9800", "#F44336"]
        }
    
    def get_chart_data_hourly_heatmap(
        self,
        db: Session,
        user_id: int,
        days: int = 7
    ) -> Dict[str, Any]:
        """
        🔥 HEATMAP: Giờ nào bé hay khóc (theo giờ và ngày trong tuần)
        
        Args:
            db: Database session
            user_id: User ID
            days: Number of days to look back
        
        Returns:
            {
                "hours": [0, 1, 2, ..., 23],
                "days": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
                "data": [
                    [0, 0, 1, 2, ...],  # Monday
                    [1, 0, 0, 3, ...],  # Tuesday
                    ...
                ]
            }
        
        Usage in Flutter:
            - Use custom heatmap widget or fl_chart
            - X-axis: hours (0-23)
            - Y-axis: days of week
            - Color intensity: number of cries
        """
        start_date = datetime.utcnow() - timedelta(days=days)
        
        query = text("""
            SELECT
                EXTRACT(DOW FROM created_at) as day_of_week,
                EXTRACT(HOUR FROM created_at) as hour,
                COUNT(*) FILTER (WHERE cry_detected) as cry_count
            FROM health_data
            WHERE user_id = :user_id
                AND created_at >= :start_date
            GROUP BY day_of_week, hour
            ORDER BY day_of_week, hour
        """)
        
        result = db.execute(query, {"user_id": user_id, "start_date": start_date}).fetchall()
        
        # Initialize 7x24 matrix (7 days, 24 hours)
        heatmap = [[0 for _ in range(24)] for _ in range(7)]
        
        for row in result:
            day = int(row[0])  # 0=Sunday, 6=Saturday
            hour = int(row[1])
            count = int(row[2])
            heatmap[day][hour] = count
        
        return {
            "hours": list(range(24)),
            "days": ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
            "data": heatmap
        }
    
    def get_health_record(self, db: Session, record_id: int, user_id: int) -> Optional[HealthData]:
        """Get a specific health record."""
        statement = select(HealthData).where(
            HealthData.id == record_id,
            HealthData.user_id == user_id
        )
        return db.exec(statement).first()
    
    def get_time_series_data(
        self,
        db: Session,
        user_id: int,
        interval: str = "1 hour",
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Get aggregated time-series data using TimescaleDB time_bucket."""
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=7)
        if not end_date:
            end_date = datetime.utcnow()
        
        query = text(f"""
            SELECT
                time_bucket(:interval, created_at) AS time_bucket,
                AVG(temperature) as avg_temperature,
                AVG(humidity) as avg_humidity,
                COUNT(*) as record_count,
                SUM(CASE WHEN cry_detected THEN 1 ELSE 0 END) as cry_count,
                SUM(CASE WHEN sick_detected THEN 1 ELSE 0 END) as sick_count
            FROM health_data
            WHERE user_id = :user_id
                AND created_at >= :start_date
                AND created_at <= :end_date
            GROUP BY time_bucket
            ORDER BY time_bucket DESC;
        """)
        
        result = db.exec(
            query,
            {
                "interval": interval,
                "user_id": user_id,
                "start_date": start_date,
                "end_date": end_date
            }
        ).all()
        
        return [
            {
                "time": row[0],
                "avg_temperature": float(row[1]) if row[1] else None,
                "avg_humidity": float(row[2]) if row[2] else None,
                "record_count": row[3],
                "cry_count": row[4],
                "sick_count": row[5]
            }
            for row in result
        ]


# Singleton instance
health_service = HealthService()