from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any
import json


@dataclass
class User:
    """Модель пользователя"""
    user_id: int
    chat_id: int
    settings: Dict[str, Any]
    created_at: datetime
    is_monitoring: bool = False
    
    def to_dict(self) -> dict:
        return {
            'user_id': self.user_id,
            'chat_id': self.chat_id,
            'settings': json.dumps(self.settings),
            'created_at': self.created_at.isoformat(),
            'is_monitoring': int(self.is_monitoring)
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'User':
        return cls(
            user_id=data['user_id'],
            chat_id=data['chat_id'],
            settings=json.loads(data['settings']) if isinstance(data['settings'], str) else data['settings'],
            created_at=datetime.fromisoformat(data['created_at']) if isinstance(data['created_at'], str) else data['created_at'],
            is_monitoring=bool(data.get('is_monitoring', 0))
        )


@dataclass
class Alert:
    """Модель алерта"""
    user_id: int
    alert_type: str
    symbol: str
    message: str
    value: float
    created_at: datetime
    id: Optional[int] = None
    
    def to_dict(self) -> dict:
        return {
            'user_id': self.user_id,
            'alert_type': self.alert_type,
            'symbol': self.symbol,
            'message': self.message,
            'value': self.value,
            'created_at': self.created_at.isoformat()
        }


@dataclass
class OpenInterestHistory:
    """История Open Interest"""
    symbol: str
    open_interest: float
    timestamp: datetime
    exchange: str = 'binance'
    id: Optional[int] = None
    
    def to_dict(self) -> dict:
        return {
            'symbol': self.symbol,
            'open_interest': self.open_interest,
            'timestamp': self.timestamp.isoformat(),
            'exchange': self.exchange
        }


@dataclass
class CMCCache:
    """Кэш данных CoinMarketCap"""
    data: Dict[str, Any]
    last_updated: datetime
    id: Optional[int] = None
    
    def to_dict(self) -> dict:
        return {
            'data_json': json.dumps(self.data),
            'last_updated': self.last_updated.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'CMCCache':
        return cls(
            data=json.loads(data['data_json']) if isinstance(data['data_json'], str) else data['data_json'],
            last_updated=datetime.fromisoformat(data['last_updated']) if isinstance(data['last_updated'], str) else data['last_updated'],
            id=data.get('id')
        )


# Настройки по умолчанию для нового пользователя
DEFAULT_USER_SETTINGS = {
    # Фильтры монет
    'min_market_cap': 100000000,        # $100M
    'min_volume_24h': 10000000,         # $10M
    'exclude_top_n': 10,                # Исключить топ-10
    
    # OI пороги для разных таймфреймов
    'oi_threshold_15min': 2.0,          # 2% за 15 минут
    'oi_threshold_30min': 3.0,          # 3% за 30 минут
    'oi_threshold_1hour': 5.0,          # 5% за 1 час
    
    # Ликвидации
    'liquidation_oi_threshold': 8.0,    # 8% падение = вероятные ликвидации
    
    # Мониторинг
    'update_interval': 300,             # 5 минут
    'max_coins_to_check': 30,           # Макс монет для проверки
    'monitoring_mode': 'api',           # 'api' или 'websocket'
    
    # Включение/отключение алертов
    'enable_oi_alerts': True,
    'enable_liquidation_detection': True,
    'long_alerts': True,
    'short_alerts': True,
    
    # Дополнительно
    'custom_exclusions': []
}
