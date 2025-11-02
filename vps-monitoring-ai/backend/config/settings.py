"""
Configuration management using Pydantic Settings
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """Application settings"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )
    
    # LLM Configuration
    openai_api_key: str
    openai_model: str = "gpt-4-turbo-preview"
    
    # Master Server
    master_host: str = "0.0.0.0"
    master_port: int = 8000
    grpc_port: int = 50051
    ws_port: int = 8001
    
    # MySQL Database
    mysql_host: str = "localhost"
    mysql_port: int = 3306
    mysql_database: str = "vps_monitoring"
    mysql_user: str
    mysql_password: str
    
    # InfluxDB
    influx_url: str = "http://localhost:8086"
    influx_token: str
    influx_org: str = "vps-monitoring"
    influx_bucket: str = "metrics"
    
    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: Optional[str] = None
    
    # RabbitMQ
    rabbitmq_host: str = "localhost"
    rabbitmq_port: int = 5672
    rabbitmq_user: str = "guest"
    rabbitmq_password: str = "guest"
    
    # Authentication
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # Email Alerting
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str
    smtp_password: str
    alert_from_email: str
    
    # Telegram Alerting
    telegram_bot_token: str
    telegram_chat_id: str
    
    # ML Configuration
    ml_model_path: str = "./ml_models"
    anomaly_threshold: float = 0.7
    retrain_interval_hours: int = 24
    min_training_samples: int = 1000
    
    # Monitoring Thresholds
    cpu_warning_threshold: int = 70
    cpu_critical_threshold: int = 85
    memory_warning_threshold: int = 75
    memory_critical_threshold: int = 90
    disk_warning_threshold: int = 80
    disk_critical_threshold: int = 95
    
    # Action Safety
    max_actions_per_hour: int = 10
    enable_auto_restart: bool = True
    enable_cache_clear: bool = True
    enable_disk_cleanup: bool = True
    
    # Data Retention
    metrics_retention_days: int = 7
    logs_retention_days: int = 7
    audit_retention_days: int = 90
    
    # Development
    debug: bool = False
    log_level: str = "INFO"
    environment: str = "production"
    
    @property
    def mysql_url(self) -> str:
        """Build MySQL connection URL"""
        return f"mysql+mysqlconnector://{self.mysql_user}:{self.mysql_password}@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}"
    
    @property
    def rabbitmq_url(self) -> str:
        """Build RabbitMQ connection URL"""
        return f"amqp://{self.rabbitmq_user}:{self.rabbitmq_password}@{self.rabbitmq_host}:{self.rabbitmq_port}/"


# Global settings instance
settings = Settings()
