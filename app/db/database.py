from sqlmodel import create_engine, SQLModel, Session, text
from ..config import settings

# Create database engine
engine = create_engine(
    settings.database_url,
    echo=settings.debug,  # Log SQL queries in debug mode
    pool_pre_ping=True,   # Verify connections before using them
    pool_size=10,         # Connection pool size
    max_overflow=20       # Max connections beyond pool_size
)


def create_db_and_tables():
    """
    Create all database tables and setup TimescaleDB hypertables.
    This should be called when the application starts.
    """
    # Create tables
    SQLModel.metadata.create_all(engine)
    
    # Setup TimescaleDB hypertable for health_data
    with Session(engine) as session:
        try:
            # Check if TimescaleDB extension is available
            result = session.exec(
                text("SELECT extname FROM pg_extension WHERE extname = 'timescaledb'")
            ).first()
            
            if result:
                print("✅ TimescaleDB extension detected")
                
                # Convert health_data table to hypertable (if not already)
                try:
                    session.exec(
                        text("""
                            SELECT create_hypertable(
                                'health_data',
                                'created_at',
                                if_not_exists => TRUE,
                                migrate_data => TRUE
                            );
                        """)
                    )
                    session.commit()
                    print("✅ Created TimescaleDB hypertable for health_data")
                except Exception as e:
                    if "already a hypertable" not in str(e):
                        print(f"⚠️ Warning creating hypertable: {e}")
                    else:
                        print("✅ Hypertable already exists")
                    session.rollback()
                        
            else:
                print("⚠️ TimescaleDB extension not found. Using standard PostgreSQL.")
                
        except Exception as e:
            print(f"⚠️ Error setting up TimescaleDB: {e}")
            session.rollback()
    
    # Create continuous aggregate and retention policy outside transaction
    # These operations require AUTOCOMMIT mode
    try:
        connection = engine.raw_connection()
        connection.set_isolation_level(0)  # AUTOCOMMIT mode
        cursor = connection.cursor()
        
        # Create continuous aggregate for hourly statistics
        try:
            cursor.execute("""
                CREATE MATERIALIZED VIEW IF NOT EXISTS health_data_hourly
                WITH (timescaledb.continuous) AS
                SELECT
                    user_id,
                    time_bucket('1 hour', created_at) AS hour,
                    AVG(temperature) as avg_temperature,
                    AVG(humidity) as avg_humidity,
                    COUNT(*) as record_count,
                    SUM(CASE WHEN cry_detected THEN 1 ELSE 0 END) as cry_count,
                    SUM(CASE WHEN sick_detected THEN 1 ELSE 0 END) as sick_count
                FROM health_data
                GROUP BY user_id, hour
                WITH NO DATA;
            """)
            print("✅ Created continuous aggregate for hourly statistics")
        except Exception as e:
            if "already exists" in str(e):
                print("✅ Continuous aggregate already exists")
            else:
                print(f"⚠️ Warning creating continuous aggregate: {e}")
        
        # Add retention policy (keeps data for 90 days)
        try:
            cursor.execute("""
                SELECT add_retention_policy(
                    'health_data',
                    INTERVAL '90 days',
                    if_not_exists => TRUE
                );
            """)
            print("✅ Added retention policy (90 days)")
        except Exception as e:
            if "already exists" in str(e) or "policy already exists" in str(e):
                print("✅ Retention policy already exists")
            else:
                print(f"⚠️ Warning adding retention policy: {e}")
        
        cursor.close()
        connection.close()
        
    except Exception as e:
        print(f"⚠️ Error setting up TimescaleDB features: {e}")


def get_session():
    """Get a database session."""
    with Session(engine) as session:
        yield session