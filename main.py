import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import config
from database import Database
from bot.handlers import setup_routers
from services import CacheService, MonitoringService, AlertService
from utils import setup_logger


async def on_startup(bot: Bot, db: Database):
    """Действия при запуске бота"""
    logger = logging.getLogger(__name__)
    logger.info("Starting crypto monitoring bot...")
    
    # Инициализация базы данных
    await db.init_db()
    logger.info("Database initialized")
    
    # Предзагрузка кэша
    cache_service = CacheService(db)
    coins = await cache_service.get_coins_data(force_refresh=True)
    logger.info(f"Preloaded {len(coins)} coins into cache")
    
    # Информация о боте
    bot_info = await bot.get_me()
    logger.info(f"Bot started: @{bot_info.username}")


async def on_shutdown(bot: Bot, db: Database, alert_service: AlertService):
    """Действия при остановке"""
    logger = logging.getLogger(__name__)
    logger.info("Shutting down bot...")
    
    # Останавливаем мониторинг
    alert_service.stop()
    
    # Закрываем соединение с БД
    await db.close()
    
    logger.info("Bot stopped")


async def main():
    """Главная функция"""
    # Настройка логирования
    logger = setup_logger(config.LOG_LEVEL)
    
    # Валидация конфигурации
    try:
        config.validate()
        logger.info("Configuration validated successfully")
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        return
    
    # Инициализация бота и диспетчера
    bot = Bot(token=config.BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    # Инициализация базы данных
    db = Database(config.DB_PATH)
    await db.connect()  # ← Подключаемся один раз здесь
    await db.init_db()  # ← Инициализируем таблицы
    
    # Инициализация сервисов
    cache_service = CacheService(db)
    monitoring_service = MonitoringService(db, cache_service)
    alert_service = AlertService(bot, db, monitoring_service)
    
    # Регистрация middleware для передачи зависимостей
    @dp.update.outer_middleware()
    async def database_middleware(handler, event, data):
        data['db'] = db
        data['cache_service'] = cache_service
        data['monitoring_service'] = monitoring_service
        data['alert_service'] = alert_service
        return await handler(event, data)
    
    # Подключение роутеров
    dp.include_router(setup_routers())
    
    
    # Запуск
    try:
        await on_startup(bot, db)
        
        # Запускаем цикл мониторинга в фоне
        monitoring_task = asyncio.create_task(
            alert_service.monitoring_loop(config.UPDATE_INTERVAL)
        )
        
        # Запускаем polling
        logger.info("Starting polling...")
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
        
    except KeyboardInterrupt:
        logger.info("Received KeyboardInterrupt")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
    finally:
        await on_shutdown(bot, db, alert_service)
        
        # Останавливаем фоновую задачу
        if 'monitoring_task' in locals():
            monitoring_task.cancel()
            try:
                await monitoring_task
            except asyncio.CancelledError:
                pass
        
        await bot.session.close()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot stopped by user")
