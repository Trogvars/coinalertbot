"""
Модуль безопасности и валидации
"""
import re
import logging
from typing import Any, Optional
from functools import wraps
import time

logger = logging.getLogger(__name__)


class InputValidator:
    """Валидация пользовательского ввода"""
    
    @staticmethod
    def validate_number(value: Any, min_val: Optional[float] = None, max_val: Optional[float] = None) -> Optional[float]:
        """
        Валидация числового значения
        
        Args:
            value: Значение для валидации
            min_val: Минимальное допустимое значение
            max_val: Максимальное допустимое значение
        
        Returns:
            Валидное число или None
        """
        try:
            # Очистка строки от пробелов и запятых
            if isinstance(value, str):
                value = value.replace(',', '').replace(' ', '').strip()
            
            num = float(value)
            
            # Проверка на NaN и Infinity
            if not (num == num) or num == float('inf') or num == float('-inf'):
                return None
            
            # Проверка диапазона
            if min_val is not None and num < min_val:
                return None
            if max_val is not None and num > max_val:
                return None
            
            return num
        except (ValueError, TypeError):
            return None
    
    @staticmethod
    def validate_integer(value: Any, min_val: Optional[int] = None, max_val: Optional[int] = None) -> Optional[int]:
        """
        Валидация целочисленного значения
        
        Args:
            value: Значение для валидации
            min_val: Минимальное допустимое значение
            max_val: Максимальное допустимое значение
        
        Returns:
            Валидное целое число или None
        """
        try:
            if isinstance(value, str):
                value = value.replace(',', '').replace(' ', '').strip()
            
            num = int(value)
            
            if min_val is not None and num < min_val:
                return None
            if max_val is not None and num > max_val:
                return None
            
            return num
        except (ValueError, TypeError):
            return None
    
    @staticmethod
    def sanitize_symbol(symbol: str, max_length: int = 20) -> Optional[str]:
        """
        Санитизация символа криптовалюты
        
        Args:
            symbol: Символ для санитизации
            max_length: Максимальная длина
        
        Returns:
            Очищенный символ или None
        """
        if not isinstance(symbol, str):
            return None
        
        # Только буквы и цифры
        sanitized = ''.join(c for c in symbol.upper() if c.isalnum())
        
        if not sanitized or len(sanitized) > max_length:
            return None
        
        return sanitized
    
    @staticmethod
    def validate_user_id(user_id: Any) -> Optional[int]:
        """
        Валидация Telegram User ID
        
        Args:
            user_id: ID пользователя
        
        Returns:
            Валидный user_id или None
        """
        try:
            uid = int(user_id)
            # Telegram user IDs - положительные числа
            if uid > 0 and uid < 10**15:  # Разумный лимит
                return uid
        except (ValueError, TypeError):
            pass
        return None
    
    @staticmethod
    def sanitize_html(text: str) -> str:
        """
        Санитизация HTML для предотвращения XSS
        
        Args:
            text: Текст для санитизации
        
        Returns:
            Очищенный текст
        """
        if not isinstance(text, str):
            return ""
        
        # Заменяем опасные символы
        replacements = {
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#x27;',
            '/': '&#x2F;'
        }
        
        for old, new in replacements.items():
            text = text.replace(old, new)
        
        return text


class RateLimiter:
    """Ограничение частоты запросов"""
    
    def __init__(self, max_calls: int, period: float):
        """
        Args:
            max_calls: Максимальное количество вызовов
            period: Период в секундах
        """
        self.max_calls = max_calls
        self.period = period
        self.calls = {}
    
    def is_allowed(self, key: str) -> bool:
        """
        Проверка разрешен ли вызов
        
        Args:
            key: Ключ (например, user_id)
        
        Returns:
            True если вызов разрешен
        """
        now = time.time()
        
        if key not in self.calls:
            self.calls[key] = []
        
        # Удаляем старые вызовы
        self.calls[key] = [t for t in self.calls[key] if now - t < self.period]
        
        # Проверяем лимит
        if len(self.calls[key]) < self.max_calls:
            self.calls[key].append(now)
            return True
        
        return False
    
    def reset(self, key: str):
        """Сброс счетчика для ключа"""
        if key in self.calls:
            del self.calls[key]


def rate_limit(max_calls: int, period: float):
    """
    Декоратор для ограничения частоты вызовов
    
    Args:
        max_calls: Максимальное количество вызовов
        period: Период в секундах
    """
    limiter = RateLimiter(max_calls, period)
    
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Получаем user_id из аргументов
            user_id = None
            if args and hasattr(args[0], 'from_user'):
                user_id = str(args[0].from_user.id)
            
            if user_id and not limiter.is_allowed(user_id):
                logger.warning(f"Rate limit exceeded for user {user_id}")
                return None
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


class SecureConfig:
    """Валидация конфигурации с безопасными значениями"""
    
    @staticmethod
    def validate_api_key(key: str, min_length: int = 32) -> bool:
        """
        Валидация API ключа
        
        Args:
            key: API ключ
            min_length: Минимальная длина
        
        Returns:
            True если ключ валиден
        """
        if not isinstance(key, str):
            return False
        
        # Проверка длины
        if len(key) < min_length:
            return False
        
        # Проверка что не содержит только пробелы
        if not key.strip():
            return False
        
        return True
    
    @staticmethod
    def validate_url(url: str) -> bool:
        """
        Валидация URL
        
        Args:
            url: URL для проверки
        
        Returns:
            True если URL валиден
        """
        if not isinstance(url, str):
            return False
        
        # Простая валидация URL
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain
            r'localhost|'  # localhost
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        
        return bool(url_pattern.match(url))
