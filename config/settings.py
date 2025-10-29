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
        """Валидация конфигурации с проверками безопасности"""
        # Проверка обязательных полей
        if not self.BOT_TOKEN:
            raise ValueError("BOT_TOKEN is required")
        if not self.COINMARKETCAP_API_KEY:
            raise ValueError("COINMARKETCAP_API_KEY is required")
        
        # Проверка длины токенов (минимальная безопасность)
        if len(self.BOT_TOKEN.strip()) < 20:
            raise ValueError("BOT_TOKEN appears to be invalid (too short)")
        if len(self.COINMARKETCAP_API_KEY.strip()) < 20:
            raise ValueError("COINMARKETCAP_API_KEY appears to be invalid (too short)")
        
        # Проверка числовых значений
        if self.UPDATE_INTERVAL < 60:
            raise ValueError("UPDATE_INTERVAL must be at least 60 seconds")
        if self.UPDATE_INTERVAL > 3600:
            raise ValueError("UPDATE_INTERVAL should not exceed 3600 seconds (1 hour)")
        
        if self.MAX_ALERTS_PER_USER < 1 or self.MAX_ALERTS_PER_USER > 1000:
            raise ValueError("MAX_ALERTS_PER_USER must be between 1 and 1000")
        
        if self.CACHE_TTL < 60 or self.CACHE_TTL > 86400:
            raise ValueError("CACHE_TTL must be between 60 and 86400 seconds")
        
        # Проверка URL
        if not self.BINANCE_BASE_URL.startswith('https://'):
            raise ValueError("BINANCE_BASE_URL must use HTTPS")
        if not self.BYBIT_BASE_URL.startswith('https://'):
            raise ValueError("BYBIT_BASE_URL must use HTTPS")
        if not self.COINMARKETCAP_BASE_URL.startswith('https://'):
            raise ValueError("COINMARKETCAP_BASE_URL must use HTTPS")
        
        return True


config = Config()
