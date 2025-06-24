import logging
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


logger = logging.getLogger()
logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter()
logHandler.setFormatter(formatter)
logger.handlers = [logHandler]
logger.setLevel(logging.INFO)

app = FastAPI(lifespan=lifespan)


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


@app.get("/health")
def health():
    return {"status": "ok"}


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