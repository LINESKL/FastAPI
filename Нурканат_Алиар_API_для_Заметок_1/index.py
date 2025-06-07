from fastapi import FastAPI
from pydantic import BaseModel
from datetime import datetime
import os
from dotenv import load_dotenv
from sqlmodel import Session, select, Field, create_engine, SQLModel
from typing import List, Optional

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)

def create_db():
    SQLModel.metadata.create_all(engine)

class Note(SQLModel, table=True):
    id: Optional[int] = Field(primary_key=True, default=None)
    text: str
    created_time: datetime = Field(default_factory=datetime.now)

class NoteCreate(BaseModel):
    text: str

class NoteOut(BaseModel):
    id: int
    text: str
    created_time: datetime

app = FastAPI()

@app.on_event("startup")
def on_start():
    create_db()

@app.post("/notes", response_model=NoteOut)
def create_note(note: NoteCreate):
    with Session(engine) as session:
        db_note = Note(text=note.text)
        session.add(db_note)
        session.commit()
        session.refresh(db_note)
        return db_note

@app.get("/notes", response_model=NoteOut)
def get_notes():
    with Session(engine) as session:
        return session.exec(select(Note)).all()
        