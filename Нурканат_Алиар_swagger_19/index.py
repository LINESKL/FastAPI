import logging
import json
from pythonjsonlogger import jsonlogger
from fastapi import FastAPI, Request
from prometheus_fastapi_instrumentator import Instrumentator
from metadata import lifespan
from users import router as users_router
from notes import router as notes_router
from websocket.webs import router as ws_router
import uvicorn
from fastapi.middleware.cors import CORSMiddleware
from config.settings import settings
from config.middleware import RateLimiterMiddleware


logger = logging.getLogger()
logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter()
logHandler.setFormatter(formatter)
logger.handlers = [logHandler]
logger.setLevel(logging.INFO)

# Создаем FastAPI приложение с детальной информацией для OpenAPI
app = FastAPI(
    title="Notes Management API",
    description="""
    🚀 Современный API для управления заметками
    
    Этот API предоставляет полный функционал для:
    
    * 👤 Управление пользователями - регистрация, аутентификация, профили
    * 📝 Работа с заметками - создание, редактирование, удаление, поиск
    * 🔒 Безопасность - JWT токены, ограничение скорости запросов
    * ⚡ Real-time - WebSocket соединения для мгновенных обновлений
    * 📊 Мониторинг - метрики Prometheus для отслеживания производительности
    
    ## Аутентификация
    
    API использует JWT токены для аутентификации. Получите токен через эндпоинт `/login`,
    затем добавляйте его в заголовок `Authorization: Bearer <token>`.
    
    ## Rate Limiting
    
    API имеет ограничения на количество запросов для предотвращения злоупотреблений.
    """,
    version="2.0.0",
    terms_of_service="https://example.com/terms/",
    contact={
        "name": "API Support Team",
        "url": "https://example.com/contact/",
        "email": "support@example.com",
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    },
    openapi_tags=[
        {
            "name": "users",
            "description": "Операции с пользователями: регистрация, аутентификация, управление профилями",
        },
        {
            "name": "notes", 
            "description": "Управление заметками: создание, чтение, обновление, удаление",
        },
        {
            "name": "websocket",
            "description": "Real-time соединения для мгновенных обновлений",
        },
        {
            "name": "health",
            "description": "Проверка состояния сервиса и мониторинг",
        },
    ],
    lifespan=lifespan
)

# Add the rate limiter middleware
app.add_middleware(RateLimiterMiddleware)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info({
        "event": "request",
        "method": request.method,
        "url": str(request.url)
    })
    response = await call_next(request)
    logger.info({
        "event": "response",
        "status_code": response.status_code
    })
    return response


@app.get(
    "/health",
    tags=["health"],
    summary="Проверка состояния сервиса",
    description="""
    Эндпоинт для проверки работоспособности API.
    
    Возвращает статус сервиса и может использоваться для:
    - Health checks в Docker/Kubernetes
    - Мониторинга доступности сервиса
    - Проверки перед deployment
    """,
    responses={
        200: {
            "description": "Сервис работает нормально",
            "content": {
                "application/json": {
                    "example": {"status": "ok", "timestamp": "2025-07-13T23:30:00Z"}
                }
            }
        }
    }
)
def health():
    """Проверка работоспособности API"""
    from datetime import datetime, UTC
    return {
        "status": "ok",
        "timestamp": datetime.now(UTC).isoformat(),
        "service": "Notes Management API",
        "version": "2.0.0"
    }


Instrumentator().instrument(app).expose(app)

app.include_router(users_router)
app.include_router(notes_router)
app.include_router(ws_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=settings.CORS_METHODS,
    allow_headers=settings.CORS_HEADERS,
)

if __name__ == "__main__":
    uvicorn.run("index:app", reload=True)