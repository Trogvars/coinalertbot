import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    """Конфигурация приложения"""
    
    # Telegram
    BOT_TOKEN: str = os.getenv('BOT_TOKEN', '')
    
    # CoinMarketCap
    COINMARKETCAP_API_KEY: str = os.getenv('COINMARKETCAP_API_KEY', '')
    COINMARKETCAP_BASE_URL: str = 'https://pro-api.coinmarketcap.com/v1'
    
    # Binance
    BINANCE_API_KEY: str = os.getenv('BINANCE_API_KEY', '')
    BINANCE_SECRET_KEY: str = os.getenv('BINANCE_SECRET_KEY', '')
    BINANCE_BASE_URL: str = 'https://fapi.binance.com'
    
    # Bybit
    BYBIT_API_KEY: str = os.getenv('BYBIT_API_KEY', '')
    BYBIT_SECRET_KEY: str = os.getenv('BYBIT_SECRET_KEY', '')
    BYBIT_BASE_URL: str = 'https://api.bybit.com'
    
    # Database
    DB_PATH: str = os.getenv('DB_PATH', 'crypto_bot.db')
    
    # Monitoring
    CACHE_TTL: int = int(os.getenv('CACHE_TTL', 3600))  # 60 минут
    UPDATE_INTERVAL: int = int(os.getenv('UPDATE_INTERVAL', 300))  # 5 минут
    MAX_ALERTS_PER_USER: int = int(os.getenv('MAX_ALERTS_PER_USER', 50))
    
    # Logging
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
    
    # Rate Limits
    CMC_REQUESTS_PER_DAY: int = 333
    BINANCE_REQUESTS_PER_MINUTE: int = 1200
    BYBIT_REQUESTS_PER_MINUTE: int = 100
    
    def validate(self) -> bool:
        """Валидация конфигурации"""
        if not self.BOT_TOKEN:
            raise ValueError("BOT_TOKEN is required")
        if not self.COINMARKETCAP_API_KEY:
            raise ValueError("COINMARKETCAP_API_KEY is required")
        return True


config = Config()
