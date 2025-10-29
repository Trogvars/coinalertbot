from aiogram import Router
from . import start, settings, monitoring


def setup_routers() -> Router:
    """Настройка роутеров"""
    router = Router()
    
    # Подключаем роутеры в нужном порядке
    router.include_router(start.router)
    router.include_router(settings.router)
    router.include_router(monitoring.router)
    
    return router
