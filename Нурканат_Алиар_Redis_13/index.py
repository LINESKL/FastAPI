from fastapi import FastAPI
from metadata import lifespan
from users import router as users_router
from notes import router as notes_router
from webs import router as ws_router
import uvicorn
from fastapi.middleware.cors import CORSMiddleware



app = FastAPI(lifespan=lifespan)

app.include_router(users_router)
app.include_router(notes_router)
app.include_router(ws_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Разрешаем все origins (для разработки)
    allow_credentials=True,
    allow_methods=["*"],  # Разрешаем все методы
    allow_headers=["*"],  # Разрешаем все заголовки
)
if __name__ == "__main__":
    uvicorn.run("index:app", reload=True)