from fastapi import FastAPI, Depends, HTTPException, status
from sqlmodel import Field, SQLModel, create_engine, Session, select
from typing import Optional, Annotated
from pydantic import BaseModel
import os
from dotenv import load_dotenv
from contextlib import asynccontextmanager
from passlib.context import CryptContext

load_dotenv()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)

def get_db():
    db = Session(engine)
    try:
        yield db
    finally:
        db.close()

@asynccontextmanager
async def lifespan(app: FastAPI):
    SQLModel.metadata.create_all(engine)
    yield

def hash(password: str) -> str:
    return pwd_context.hash(password)

def verify(password: str, hashed_password: str) -> bool:
    return pwd_context.verify(password, hashed_password)


def get_user(username: str, db: Session):
    return db.exec(select(User).where(User.username == username)).first()


class User(SQLModel, table=True):
    id: Optional[int] = Field(primary_key=True, default=None)
    username: str = Field(index=True, unique=True, min_length=3, max_length=50)
    password: str = Field(min_length=8)

class UserCreate(BaseModel):
    username: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class UserOut(BaseModel):
    id: int
    username: str

app = FastAPI(lifespan=lifespan)

@app.post("/register/", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(user: UserCreate, db: Session = Depends(get_db)):
    db_user = get_user(user.username, db)
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    new_user = User(username=user.username, password=hash(user.password))
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.post("/login/", response_model=UserOut)
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    user = db.exec(select(User).where(User.username == credentials.username)).first()
    if not user or not verify(credentials.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"}
        )
    return user