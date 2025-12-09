import json
import asyncio
import ssl
from typing import Optional
import paho.mqtt.client as mqtt
from sqlmodel import Session

from ..config import settings
from ..db.database import engine
from ..schemas.health import HealthDataCreate
from .health_service import health_service


class MQTTService:
    """
    MQTT service để nhận data từ ESP32/sensors.
    
    Message format từ MQTT:
    {
        "FinalResult": "SNORING" hoặc "InfantCry",
        "InfantCry": 5.52,
        "Snoring": 94.48,
        "Temperature": 25.8,
        "Humidity": 72
    }
    """
    
    def __init__(self):
        self.client: Optional[mqtt.Client] = None
        self.loop: Optional[asyncio.AbstractEventLoop] = None
    
    def _on_connect(self, client, userdata, flags, rc, properties=None):
        """Callback khi kết nối MQTT thành công."""
        if rc == 0:
            print(f"✅ Connected to MQTT Broker at {settings.mqtt_broker}:{settings.mqtt_port}")
            # Subscribe topic
            client.subscribe(settings.mqtt_topic)
            print(f"📡 Subscribed to topic: {settings.mqtt_topic}")
        else:
            print(f"❌ Failed to connect to MQTT. Return code: {rc}")
            print(f"   Error codes: 0=Success, 1=Wrong protocol, 2=Invalid client ID")
            print(f"   3=Server unavailable, 4=Bad username/password, 5=Not authorized")
    
    def _on_disconnect(self, client, userdata, rc):
        """Callback khi mất kết nối MQTT."""
        if rc != 0:
            print(f"⚠️ Unexpected MQTT disconnection. Return code: {rc}")
            print("🔄 Attempting to reconnect...")
    
    def _on_message(self, client, userdata, msg):
        """
        Callback khi nhận được message từ MQTT.
        
        Args:
            client: MQTT client
            userdata: User data
            msg: MQTT message object
        """
        try:
            # Parse JSON payload
            payload = json.loads(msg.payload.decode())
            print(f"📥 MQTT message received: {payload}")
            
            # Validate required fields
            if not all(k in payload for k in ["Temperature", "Humidity"]):
                print("❌ Missing required fields (Temperature, Humidity)")
                return
            
            # ✅ Handle error values from sensor
            try:
                temperature = float(payload["Temperature"]) if payload["Temperature"] != "Err" else None
                humidity = float(payload["Humidity"]) if payload["Humidity"] != "Err" else None
            except (ValueError, TypeError):
                print("❌ Invalid temperature/humidity values")
                return
            
            # Skip if both sensors failed
            if temperature is None and humidity is None:
                print("⚠️ Sensor error, skipping this reading")
                return
            
            # Use default values if one sensor fails
            if temperature is None:
                temperature = 25.0  # Default safe temperature
            if humidity is None:
                humidity = 50.0  # Default safe humidity
            
            # ✅ Parse crying detection
            cry_detected = payload.get("FinalResult", "").upper() == "INFANTCRY"
            infant_cry_confidence = payload.get("InfantCry", 0.0)
            
            # Get user_id from payload (default to 1)
            user_id = payload.get("user_id", 1)
            
            print(f"🔍 Cry detected: {cry_detected} (confidence: {infant_cry_confidence:.2f}%)")
            print(f"🌡️ Temperature: {temperature}°C, Humidity: {humidity}%")
            
            # Schedule async save to database
            if self.loop:
                asyncio.run_coroutine_threadsafe(
                    self._save_to_database(user_id, temperature, humidity, cry_detected),
                    self.loop
                )
            
        except json.JSONDecodeError:
            print(f"❌ Invalid JSON payload: {msg.payload}")
        except Exception as e:
            print(f"❌ Error processing MQTT message: {e}")
            import traceback
            traceback.print_exc()
    
    async def _save_to_database(
        self,
        user_id: int,
        temperature: float,
        humidity: float,
        cry_detected: bool
    ):
        """
        Lưu health data vào database (giống như /health/upload).
        
        Args:
            user_id: User ID
            temperature: Nhiệt độ
            humidity: Độ ẩm
            cry_detected: Có khóc hay không
        """
        try:
            with Session(engine) as db:
                health_data = HealthDataCreate(
                    temperature=temperature,
                    humidity=humidity,
                    notes="Auto-uploaded from MQTT sensor"
                )
                
                from sqlalchemy import text
                
                # Determine sick_detected based on temperature only
                sick_detected = temperature >= 38.0
                
                # Insert into database
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
                        "temperature": temperature,
                        "humidity": humidity,
                        "audio_url": None,
                        "cry_detected": cry_detected,
                        "sick_detected": sick_detected,
                        "notes": health_data.notes
                    }
                )
                
                row = result.fetchone()
                db.commit()
                
                from sqlmodel import select
                from ..db.models import HealthData
                
                db_record = db.exec(
                    select(HealthData).where(
                        HealthData.id == row[0],
                        HealthData.created_at == row[1]
                    )
                ).first()
                
                print(f"✅ Saved MQTT data to DB: ID={db_record.id}, sick_detected={db_record.sick_detected}")
                
                # 🚀 Send WebSocket notification
                await health_service._send_health_update(user_id, db_record)
                
        except Exception as e:
            print(f"❌ Error saving MQTT data to database: {e}")
            import traceback
            traceback.print_exc()
    
    def start(self, loop: asyncio.AbstractEventLoop):
        """
        Khởi động MQTT client.
        
        Args:
            loop: Event loop để chạy async tasks
        """
        self.loop = loop
        
        # ✅ FIX: Use CallbackAPIVersion.VERSION2 for Paho MQTT 2.0+
        try:
            self.client = mqtt.Client(
                mqtt.CallbackAPIVersion.VERSION2,
                client_id=settings.mqtt_client_id
            )
        except AttributeError:
            # Fallback for older paho-mqtt versions
            self.client = mqtt.Client(client_id=settings.mqtt_client_id)
        
        # Set callbacks
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message
        
        # ✅ FIX: Enable TLS/SSL for HiveMQ Cloud (port 8883)
        if settings.mqtt_port == 8883:
            print("🔒 Enabling TLS/SSL for MQTT connection...")
            self.client.tls_set(tls_version=ssl.PROTOCOL_TLS)
        
        # Set credentials
        if settings.mqtt_username and settings.mqtt_password:
            self.client.username_pw_set(settings.mqtt_username, settings.mqtt_password)
            print(f"🔑 MQTT Credentials: {settings.mqtt_username} / {'*' * len(settings.mqtt_password)}")
        
        try:
            # Connect to broker
            print(f"🔌 Connecting to MQTT Broker: {settings.mqtt_broker}:{settings.mqtt_port}")
            print(f"📡 Topic: {settings.mqtt_topic}")
            
            self.client.connect(settings.mqtt_broker, settings.mqtt_port, keepalive=60)
            
            # Start loop in background thread
            self.client.loop_start()
            
            print("✅ MQTT Service started successfully")
            
        except Exception as e:
            print(f"❌ Failed to start MQTT service: {e}")
            import traceback
            traceback.print_exc()
    
    def stop(self):
        """Dừng MQTT client."""
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
            print("👋 MQTT Service stopped")


# Singleton instance
mqtt_service = MQTTService()