import os
from dotenv import load_dotenv
from typing import Optional

load_dotenv()

class Settings:
    """Configuración centralizada del bot de trading"""
    
    # Telegram
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "")
    
    # Binance
    BINANCE_API_KEY: str = os.getenv("BINANCE_API_KEY", "")
    BINANCE_SECRET_KEY: str = os.getenv("BINANCE_SECRET_KEY", "")
    BINANCE_TESTNET: bool = os.getenv("BINANCE_TESTNET", "True").lower() == "true"
    
    # LLM Configuration
    GROQ_API_KEY: Optional[str] = os.getenv("GROQ_API_KEY")
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama2")
    
    # Trading Parameters
    TARGET_WEEKLY_RETURN: float = float(os.getenv("TARGET_WEEKLY_RETURN", "0.30"))
    MAX_RISK_PER_TRADE: float = float(os.getenv("MAX_RISK_PER_TRADE", "0.02"))
    STOP_LOSS_PERCENTAGE: float = float(os.getenv("STOP_LOSS_PERCENTAGE", "0.05"))
    TAKE_PROFIT_PERCENTAGE: float = float(os.getenv("TAKE_PROFIT_PERCENTAGE", "0.10"))
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///trading_bot.db")
    
    # Trading pairs principales
    TRADING_PAIRS = [
        "BTCUSDT", "ETHUSDT", "BNBUSDT", "ADAUSDT", "SOLUSDT",
        "XRPUSDT", "DOTUSDT", "LINKUSDT", "LTCUSDT", "BCHUSDT"
    ]
    
    # Timeframes para análisis
    TIMEFRAMES = ["1m", "5m", "15m", "1h", "4h", "1d"]
    
    @classmethod
    def validate(cls) -> bool:
        """Valida que las configuraciones esenciales estén presentes"""
        required_fields = [
            cls.TELEGRAM_BOT_TOKEN,
            cls.BINANCE_API_KEY,
            cls.BINANCE_SECRET_KEY
        ]
        return all(field for field in required_fields)

settings = Settings()