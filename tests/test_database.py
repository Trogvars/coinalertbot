"""
Тесты для модуля базы данных
"""
import pytest
import asyncio
from datetime import datetime
import tempfile
import os

from database import Database, User, Alert, OpenInterestHistory
from database.models import DEFAULT_USER_SETTINGS


@pytest.fixture
async def db():
    """Фикстура для временной БД"""
    # Создаем временный файл БД
    temp_file = tempfile.NamedTemporaryFile(delete=False)
    temp_file.close()
    
    database = Database(temp_file.name)
    await database.init_db()
    
    yield database
    
    await database.close()
    # Удаляем временный файл
    os.unlink(temp_file.name)


class TestDatabase:
    """Тесты базы данных"""
    
    @pytest.mark.asyncio
    async def test_create_user(self, db):
        """Тест создания пользователя"""
        user = await db.create_user(user_id=123, chat_id=123)
        
        assert user.user_id == 123
        assert user.chat_id == 123
        assert user.settings == DEFAULT_USER_SETTINGS
        assert user.is_monitoring is False
    
    @pytest.mark.asyncio
    async def test_get_user(self, db):
        """Тест получения пользователя"""
        await db.create_user(user_id=123, chat_id=123)
        user = await db.get_user(123)
        
        assert user is not None
        assert user.user_id == 123
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_user(self, db):
        """Тест получения несуществующего пользователя"""
        user = await db.get_user(999)
        assert user is None
    
    @pytest.mark.asyncio
    async def test_update_user_settings(self, db):
        """Тест обновления настроек пользователя"""
        await db.create_user(user_id=123, chat_id=123)
        
        new_settings = {'min_market_cap': 500000000}
        await db.update_user_settings(123, new_settings)
        
        user = await db.get_user(123)
        assert user.settings == new_settings
    
    @pytest.mark.asyncio
    async def test_set_monitoring_status(self, db):
        """Тест установки статуса мониторинга"""
        await db.create_user(user_id=123, chat_id=123)
        
        await db.set_monitoring_status(123, True)
        user = await db.get_user(123)
        assert user.is_monitoring is True
        
        await db.set_monitoring_status(123, False)
        user = await db.get_user(123)
        assert user.is_monitoring is False
    
    @pytest.mark.asyncio
    async def test_get_monitoring_users(self, db):
        """Тест получения пользователей с активным мониторингом"""
        await db.create_user(user_id=1, chat_id=1)
        await db.create_user(user_id=2, chat_id=2)
        await db.create_user(user_id=3, chat_id=3)
        
        await db.set_monitoring_status(1, True)
        await db.set_monitoring_status(2, True)
        
        monitoring_users = await db.get_monitoring_users()
        assert len(monitoring_users) == 2
        assert all(u.is_monitoring for u in monitoring_users)
    
    @pytest.mark.asyncio
    async def test_create_alert(self, db):
        """Тест создания алерта"""
        await db.create_user(user_id=123, chat_id=123)
        
        alert = Alert(
            user_id=123,
            alert_type='open_interest',
            symbol='BTC',
            message='Test alert',
            value=15.5,
            created_at=datetime.now()
        )
        
        await db.create_alert(alert)
        
        alerts = await db.get_user_alerts(123)
        assert len(alerts) == 1
        assert alerts[0].symbol == 'BTC'
    
    @pytest.mark.asyncio
    async def test_get_user_alerts_limit(self, db):
        """Тест получения алертов с лимитом"""
        await db.create_user(user_id=123, chat_id=123)
        
        # Создаем несколько алертов
        for i in range(10):
            alert = Alert(
                user_id=123,
                alert_type='test',
                symbol=f'COIN{i}',
                message='Test',
                value=i,
                created_at=datetime.now()
            )
            await db.create_alert(alert)
        
        alerts = await db.get_user_alerts(123, limit=5)
        assert len(alerts) == 5
    
    @pytest.mark.asyncio
    async def test_save_oi_history(self, db):
        """Тест сохранения истории OI"""
        oi = OpenInterestHistory(
            symbol='BTCUSDT',
            open_interest=50000.0,
            timestamp=datetime.now(),
            exchange='binance'
        )
        
        await db.save_oi_history(oi)
        
        latest = await db.get_latest_oi('BTCUSDT', 'binance')
        assert latest is not None
        assert latest.symbol == 'BTCUSDT'
        assert latest.open_interest == 50000.0
    
    @pytest.mark.asyncio
    async def test_get_latest_oi_nonexistent(self, db):
        """Тест получения несуществующего OI"""
        latest = await db.get_latest_oi('NONEXISTENT', 'binance')
        assert latest is None
    
    @pytest.mark.asyncio
    async def test_cache_freshness(self, db):
        """Тест проверки свежести кэша"""
        # Кэш пустой - не свежий
        assert await db.is_cache_fresh() is False
        
        # Добавляем данные в кэш
        await db.update_cmc_cache({'test': 'data'})
        
        # Теперь свежий
        assert await db.is_cache_fresh(ttl=3600) is True


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
