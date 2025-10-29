"""
Тесты для модуля безопасности
"""
import pytest
from utils.security import InputValidator, RateLimiter, SecureConfig


class TestInputValidator:
    """Тесты валидатора ввода"""
    
    def test_validate_number_valid(self):
        """Тест валидации корректных чисел"""
        assert InputValidator.validate_number("100") == 100.0
        assert InputValidator.validate_number(100) == 100.0
        assert InputValidator.validate_number("1,000.50") == 1000.5
        assert InputValidator.validate_number("  123.45  ") == 123.45
    
    def test_validate_number_with_range(self):
        """Тест валидации чисел с диапазоном"""
        assert InputValidator.validate_number(50, min_val=0, max_val=100) == 50.0
        assert InputValidator.validate_number(-10, min_val=0) is None
        assert InputValidator.validate_number(200, max_val=100) is None
        assert InputValidator.validate_number(0, min_val=0, max_val=100) == 0.0
    
    def test_validate_number_invalid(self):
        """Тест валидации некорректных чисел"""
        assert InputValidator.validate_number("abc") is None
        assert InputValidator.validate_number("") is None
        assert InputValidator.validate_number(None) is None
        assert InputValidator.validate_number(float('inf')) is None
        assert InputValidator.validate_number(float('nan')) is None
    
    def test_validate_integer_valid(self):
        """Тест валидации корректных целых чисел"""
        assert InputValidator.validate_integer("100") == 100
        assert InputValidator.validate_integer(100) == 100
        assert InputValidator.validate_integer("  50  ") == 50
    
    def test_validate_integer_with_range(self):
        """Тест валидации целых чисел с диапазоном"""
        assert InputValidator.validate_integer(50, min_val=0, max_val=100) == 50
        assert InputValidator.validate_integer(-10, min_val=0) is None
        assert InputValidator.validate_integer(200, max_val=100) is None
    
    def test_validate_integer_invalid(self):
        """Тест валидации некорректных целых чисел"""
        assert InputValidator.validate_integer("abc") is None
        assert InputValidator.validate_integer("12.5") is None
        assert InputValidator.validate_integer(None) is None
    
    def test_sanitize_symbol_valid(self):
        """Тест санитизации корректных символов"""
        assert InputValidator.sanitize_symbol("BTC") == "BTC"
        assert InputValidator.sanitize_symbol("btc") == "BTC"
        assert InputValidator.sanitize_symbol("BTC123") == "BTC123"
        assert InputValidator.sanitize_symbol("eth-usdt") == "ETHUSDT"
    
    def test_sanitize_symbol_invalid(self):
        """Тест санитизации некорректных символов"""
        assert InputValidator.sanitize_symbol("") is None
        assert InputValidator.sanitize_symbol("BTC" * 10) is None  # Слишком длинный
        assert InputValidator.sanitize_symbol(123) is None
        assert InputValidator.sanitize_symbol(None) is None
        assert InputValidator.sanitize_symbol("!@#$%") is None
    
    def test_validate_user_id_valid(self):
        """Тест валидации корректных user ID"""
        assert InputValidator.validate_user_id(123456789) == 123456789
        assert InputValidator.validate_user_id("123456789") == 123456789
    
    def test_validate_user_id_invalid(self):
        """Тест валидации некорректных user ID"""
        assert InputValidator.validate_user_id(-123) is None
        assert InputValidator.validate_user_id(0) is None
        assert InputValidator.validate_user_id("abc") is None
        assert InputValidator.validate_user_id(10**20) is None  # Слишком большой
    
    def test_sanitize_html(self):
        """Тест санитизации HTML"""
        assert InputValidator.sanitize_html("<script>alert('xss')</script>") == "&lt;script&gt;alert(&#x27;xss&#x27;)&lt;&#x2F;script&gt;"
        assert InputValidator.sanitize_html("Normal text") == "Normal text"
        assert InputValidator.sanitize_html("<b>Bold</b>") == "&lt;b&gt;Bold&lt;&#x2F;b&gt;"
        assert InputValidator.sanitize_html(123) == ""


class TestRateLimiter:
    """Тесты ограничителя частоты"""
    
    def test_rate_limiter_allows_initial_calls(self):
        """Тест что начальные вызовы разрешены"""
        limiter = RateLimiter(max_calls=3, period=1.0)
        
        assert limiter.is_allowed("user1") is True
        assert limiter.is_allowed("user1") is True
        assert limiter.is_allowed("user1") is True
    
    def test_rate_limiter_blocks_excess_calls(self):
        """Тест что превышающие вызовы блокируются"""
        limiter = RateLimiter(max_calls=2, period=1.0)
        
        assert limiter.is_allowed("user1") is True
        assert limiter.is_allowed("user1") is True
        assert limiter.is_allowed("user1") is False  # Превышен лимит
    
    def test_rate_limiter_different_users(self):
        """Тест что лимиты независимы для разных пользователей"""
        limiter = RateLimiter(max_calls=2, period=1.0)
        
        assert limiter.is_allowed("user1") is True
        assert limiter.is_allowed("user1") is True
        assert limiter.is_allowed("user2") is True
        assert limiter.is_allowed("user2") is True
    
    def test_rate_limiter_reset(self):
        """Тест сброса лимита"""
        limiter = RateLimiter(max_calls=2, period=1.0)
        
        limiter.is_allowed("user1")
        limiter.is_allowed("user1")
        limiter.reset("user1")
        
        assert limiter.is_allowed("user1") is True


class TestSecureConfig:
    """Тесты валидации конфигурации"""
    
    def test_validate_api_key_valid(self):
        """Тест валидации корректных API ключей"""
        valid_key = "a" * 32
        assert SecureConfig.validate_api_key(valid_key) is True
        
        long_key = "a" * 64
        assert SecureConfig.validate_api_key(long_key) is True
    
    def test_validate_api_key_invalid(self):
        """Тест валидации некорректных API ключей"""
        short_key = "short"
        assert SecureConfig.validate_api_key(short_key) is False
        
        assert SecureConfig.validate_api_key("") is False
        assert SecureConfig.validate_api_key("   ") is False
        assert SecureConfig.validate_api_key(None) is False
        assert SecureConfig.validate_api_key(123) is False
    
    def test_validate_url_valid(self):
        """Тест валидации корректных URL"""
        assert SecureConfig.validate_url("https://api.binance.com") is True
        assert SecureConfig.validate_url("http://localhost:8000") is True
        assert SecureConfig.validate_url("https://example.com/path") is True
    
    def test_validate_url_invalid(self):
        """Тест валидации некорректных URL"""
        assert SecureConfig.validate_url("not a url") is False
        assert SecureConfig.validate_url("ftp://example.com") is False
        assert SecureConfig.validate_url("") is False
        assert SecureConfig.validate_url(None) is False


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
