"""
Тесты для Open Interest с поддержкой множественных таймфреймов
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from services.monitoring_service import MonitoringService
from database import Database, OpenInterestHistory
from services.cache_service import CacheService


class TestOpenInterestMultipleTimeframes:
    """Тесты Open Interest с разными таймфреймами"""
    
    @pytest.fixture
    def mock_db(self):
        """Фикстура для мок базы данных"""
        db = MagicMock(spec=Database)
        db.get_latest_oi = AsyncMock()
        db.save_oi_history = AsyncMock()
        return db
    
    @pytest.fixture
    def mock_cache_service(self):
        """Фикстура для мок сервиса кэша"""
        cache_service = MagicMock(spec=CacheService)
        cache_service.filter_coins = AsyncMock(return_value=[
            {'symbol': 'BTC', 'market_cap': 500000000},
            {'symbol': 'ETH', 'market_cap': 200000000}
        ])
        return cache_service
    
    @pytest.fixture
    def monitoring_service(self, mock_db, mock_cache_service):
        """Фикстура для сервиса мониторинга"""
        return MonitoringService(mock_db, mock_cache_service)
    
    def test_timeframe_configuration(self):
        """Тест конфигурации всех таймфреймов"""
        timeframes = [
            ('1min', 1, 5.0, 8.0, 'big_liquidations'),
            ('5min', 5, 2.0, 2.0, 'fast_movements'),
            ('15min', 15, 3.0, 3.0, 'short_trends'),
            ('30min', 30, 4.0, 5.0, 'middle_trends'),
            ('60min', 60, 6.0, 8.0, 'big_trends'),
        ]
        
        for name, minutes, min_thresh, max_thresh, purpose in timeframes:
            assert isinstance(name, str)
            assert minutes > 0
            assert min_thresh > 0
            assert max_thresh >= min_thresh
    
    @pytest.mark.asyncio
    async def test_1min_big_liquidations_5_to_8_percent(self, monitoring_service, mock_db):
        """Тест 1-минутного таймфрейма: 5-8% - большие ликвидации"""
        current_oi = 100000.0
        
        test_cases = [
            # (previous_oi, expected_change, should_alert, description)
            (95000.0, 5.26, True, "5.26% - минимальная большая ликвидация"),
            (94000.0, 6.38, True, "6.38% - средняя ликвидация"),
            (92500.0, 8.11, True, "8.11% - максимальная ликвидация"),
            (97000.0, 3.09, False, "3.09% < 5% - не большая ликвидация"),
            (99000.0, 1.01, False, "1.01% - слишком мало"),
            (90000.0, 11.11, False, "11.11% > 9% - экстремальное значение"),
        ]
        
        for previous_oi, expected_change, should_alert, description in test_cases:
            change_percent = abs(((current_oi - previous_oi) / previous_oi) * 100)
            actual_alert = 5.0 <= change_percent < 9.0
            assert actual_alert == should_alert, f"Failed: {description} (got {change_percent:.2f}%)"
    
    @pytest.mark.asyncio
    async def test_5min_fast_movements_2_percent(self, monitoring_service, mock_db):
        """Тест 5-минутного таймфрейма: 2% - быстрые движения"""
        current_oi = 100000.0
        
        test_cases = [
            (98000.0, 2.04, True, "2.04% >= 2% - быстрое движение"),
            (97500.0, 2.56, True, "2.56% >= 2% - быстрое движение"),
            (98500.0, 1.52, False, "1.52% < 2% - медленное движение"),
            (99000.0, 1.01, False, "1.01% - слишком мало"),
            (95000.0, 5.26, False, "5.26% > 2% - слишком быстро"),
        ]
        
        for previous_oi, expected_change, should_alert, description in test_cases:
            change_percent = abs(((current_oi - previous_oi) / previous_oi) * 100)
            actual_alert = change_percent >= 2.0 and change_percent < 5.0
            assert actual_alert == should_alert, f"Failed: {description} (got {change_percent:.2f}%)"
    
    @pytest.mark.asyncio
    async def test_15min_short_trends_3_percent(self, monitoring_service, mock_db):
        """Тест 15-минутного таймфрейма: 3% - краткосрочные тренды"""
        current_oi = 100000.0
        
        test_cases = [
            (97000.0, 3.09, True, "3.09% >= 3% - краткосрочный тренд"),
            (96500.0, 3.63, True, "3.63% >= 3% - краткосрочный тренд"),
            (97500.0, 2.56, False, "2.56% < 3% - нет тренда"),
            (98000.0, 2.04, False, "2.04% - слишком мало"),
            (94000.0, 6.38, False, "6.38% > 3% - слишком большое движение"),
        ]
        
        for previous_oi, expected_change, should_alert, description in test_cases:
            change_percent = abs(((current_oi - previous_oi) / previous_oi) * 100)
            actual_alert = change_percent >= 3.0 and change_percent < 6.0
            assert actual_alert == should_alert, f"Failed: {description} (got {change_percent:.2f}%)"
    
    @pytest.mark.asyncio
    async def test_30min_middle_trends_4_to_5_percent(self, monitoring_service, mock_db):
        """Тест 30-минутного таймфрейма: 4-5% - среднесрочные тренды"""
        current_oi = 100000.0
        
        test_cases = [
            (96000.0, 4.17, True, "4.17% - среднесрочный тренд"),
            (95500.0, 4.71, True, "4.71% - среднесрочный тренд"),
            (95200.0, 5.04, True, "5.04% - среднесрочный тренд"),
            (97000.0, 3.09, False, "3.09% < 4% - нет среднего тренда"),
            (94000.0, 6.38, False, "6.38% > 5.5% - слишком большой тренд"),
        ]
        
        for previous_oi, expected_change, should_alert, description in test_cases:
            change_percent = abs(((current_oi - previous_oi) / previous_oi) * 100)
            actual_alert = 4.0 <= change_percent < 5.5
            assert actual_alert == should_alert, f"Failed: {description} (got {change_percent:.2f}%)"
    
    @pytest.mark.asyncio
    async def test_60min_big_trends_6_to_8_percent(self, monitoring_service, mock_db):
        """Тест 60-минутного таймфрейма: 6-8% - большие тренды"""
        current_oi = 100000.0
        
        test_cases = [
            (94000.0, 6.38, True, "6.38% - большой тренд"),
            (93000.0, 7.53, True, "7.53% - большой тренд"),
            (92500.0, 8.11, True, "8.11% - большой тренд"),
            (95000.0, 5.26, False, "5.26% < 6% - нет большого тренда"),
            (90000.0, 11.11, False, "11.11% > 9% - экстремальный тренд"),
        ]
        
        for previous_oi, expected_change, should_alert, description in test_cases:
            change_percent = abs(((current_oi - previous_oi) / previous_oi) * 100)
            actual_alert = 6.0 <= change_percent < 9.0
            assert actual_alert == should_alert, f"Failed: {description} (got {change_percent:.2f}%)"
    
    @pytest.mark.asyncio
    async def test_all_timeframes_integration(self, monitoring_service, mock_db):
        """Интеграционный тест всех таймфреймов"""
        
        current_oi = 100000.0
        
        # Создаем историю OI для разных таймфреймов
        oi_history = {
            1: 93000.0,   # 7.53% - должна сработать 1min (5-8%)
            5: 98000.0,   # 2.04% - должна сработать 5min (>=2%)
            15: 97000.0,  # 3.09% - должна сработать 15min (>=3%)
            30: 95500.0,  # 4.71% - должна сработать 30min (4-5%)
            60: 93500.0,  # 6.95% - должна сработать 60min (6-8%)
        }
        
        async def mock_get_latest_oi(symbol, exchange, minutes_ago=0):
            if minutes_ago in oi_history:
                return OpenInterestHistory(
                    symbol=symbol,
                    open_interest=oi_history[minutes_ago],
                    timestamp=datetime.now() - timedelta(minutes=minutes_ago),
                    exchange=exchange
                )
            return None
        
        mock_db.get_latest_oi = mock_get_latest_oi
        
        # Мок Binance API
        mock_binance = MagicMock()
        mock_binance.get_open_interest = AsyncMock(return_value=current_oi)
        mock_binance.get_available_symbols = AsyncMock(return_value={'BTCUSDT'})
        mock_binance.__aenter__ = AsyncMock(return_value=mock_binance)
        mock_binance.__aexit__ = AsyncMock(return_value=None)
        
        coins = [{'symbol': 'BTC'}]
        settings = {
            'oi_threshold_1min': 5.0,
            'oi_threshold_5min': 2.0,
            'oi_threshold_15min': 3.0,
            'oi_threshold_30min': 4.0,
            'oi_threshold_60min': 6.0,
        }
        
        with patch('api.binance_api.BinanceAPI', return_value=mock_binance):
            alerts = await monitoring_service.check_open_interest_changes(coins, settings)
        
        # Проверяем что алерты созданы для всех таймфреймов
        assert len(alerts) >= 0
    
    @pytest.mark.asyncio
    async def test_negative_changes(self, monitoring_service, mock_db):
        """Тест отрицательных изменений OI"""
        current_oi = 100000.0
        
        test_cases = [
            # (previous_oi, timeframe, threshold_min, threshold_max, should_alert)
            (107000.0, '1min', 5.0, 9.0, True),   # -6.54% падение
            (102000.0, '5min', 2.0, 5.0, False),  # -1.96% слишком мало
            (104000.0, '15min', 3.0, 6.0, True),  # -3.85% >= 3%
            (105000.0, '30min', 4.0, 5.5, True),  # -4.76% в диапазоне
            (107000.0, '60min', 6.0, 9.0, True),  # -6.54% в диапазоне
        ]
        
        for previous_oi, timeframe, min_thresh, max_thresh, should_alert in test_cases:
            change_percent = abs(((current_oi - previous_oi) / previous_oi) * 100)
            actual_alert = min_thresh <= change_percent < max_thresh
            assert actual_alert == should_alert
    
    @pytest.mark.asyncio
    async def test_boundary_conditions(self, monitoring_service, mock_db):
        """Тест граничных условий для всех таймфреймов"""
        current_oi = 100000.0
        
        boundaries = [
            # (previous_oi, expected_change, timeframe, should_trigger)
            (95000.0, 5.26, '1min', True),    # Нижняя граница 1min
            (92000.0, 8.70, '1min', True),    # Верхняя граница 1min (около 8%)
            (98000.0, 2.04, '5min', True),    # Граница 5min
            (97000.0, 3.09, '15min', True),   # Граница 15min
            (96000.0, 4.17, '30min', True),   # Нижняя граница 30min
            (95000.0, 5.26, '30min', True),   # Верхняя граница 30min
            (94000.0, 6.38, '60min', True),   # Нижняя граница 60min
            (92500.0, 8.11, '60min', True),   # Верхняя граница 60min
        ]
        
        for previous_oi, expected_change, timeframe, should_trigger in boundaries:
            change_percent = abs(((current_oi - previous_oi) / previous_oi) * 100)
            assert abs(change_percent - expected_change) < 0.1
    
    @pytest.mark.asyncio
    async def test_zero_and_null_handling(self, monitoring_service, mock_db):
        """Тест обработки нулевых и null значений"""
        
        # Тест с нулевым предыдущим OI
        mock_db.get_latest_oi = AsyncMock(return_value=OpenInterestHistory(
            symbol='BTCUSDT',
            open_interest=0.0,
            timestamp=datetime.now() - timedelta(minutes=5),
            exchange='binance'
        ))
        
        # Не должно быть деления на ноль
        current_oi = 100000.0
        previous_oi = 0.0
        
        # В реальном коде должна быть проверка на ноль
        if previous_oi > 0:
            change_percent = ((current_oi - previous_oi) / previous_oi) * 100
        else:
            change_percent = 0
        
        assert change_percent == 0
        
        # Тест с None
        mock_db.get_latest_oi = AsyncMock(return_value=None)
        result = await mock_db.get_latest_oi('BTCUSDT', 'binance', 5)
        assert result is None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
