from fastapi import FastAPI
from metadata import lifespan
from users import router as users_router
from notes import router as notes_router
import uvicorn

app = FastAPI(lifespan=lifespan)

app.include_router(users_router)
app.include_router(notes_router)

if __name__ == "__main__":
    uvicorn.run("index:app", reload=True)