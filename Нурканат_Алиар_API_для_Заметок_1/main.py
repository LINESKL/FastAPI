from fastapi import FastAPI, HTTPException
from sqlmodel import SQLModel, Session, create_engine, select, Field
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel
import os
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

# Настройка подключения к базе данных
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)

# Модель заметки
class Note(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    text: str
    created_at: datetime = Field(default_factory=datetime.now)

# Создание таблиц
def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

app = FastAPI(title="Notes API")

@app.on_event("startup")
def on_startup():
    create_db_and_tables()

# Схемы Pydantic
class NoteCreate(BaseModel):
    text: str

class NoteOut(BaseModel):
    id: int
    text: str
    created_at: datetime

# Эндпоинты
@app.post("/notes", response_model=NoteOut)
def create_note(note: NoteCreate):
    with Session(engine) as session:
        db_note = Note(text=note.text)
        session.add(db_note)
        session.commit()
        session.refresh(db_note)
        return db_note

@app.get("/notes", response_model=List[NoteOut])
def read_notes():
    with Session(engine) as session:
        notes = session.exec(select(Note)).all()
        return notes
