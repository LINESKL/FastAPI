from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy import select
from sqlmodel import SQLModel, Field
from pydantic import BaseModel
from jose import JWTError, jwt
import uvicorn
from typing import Optional, Annotated
from sqlalchemy.orm import DeclarativeBase
from fastapi import Depends
from sqlmodel import SQLModel
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import timedelta
from metadata import (
    CURRENT_DATETIME,
    SECRET_KEY,
    ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    pwd_context,
    DATABASE_URL,
    engine,
    session_factory,
    oauth2_scheme,
    get_db,
    SessionDep,
    Base,
    lifespan
)

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(password: str, hashed_password: str) -> bool:
    return pwd_context.verify(password, hashed_password)

async def get_user(username: str, session: AsyncSession):
    stmt = select(User).where(User.username == username)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = CURRENT_DATETIME + expires_delta
    else:
        expire = CURRENT_DATETIME + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = await get_user(username, db)
    if user is None:
        raise credentials_exception
    return user

def require_role(required_role: str):
    async def role_checker(current_user: User = Depends(get_current_user)):
        if current_user.role != required_role: 
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role: {required_role}"
            )
        return current_user
    return role_checker

class User(SQLModel, table=True):
    id: Optional[int] = Field(primary_key=True, default=None)
    username: str = Field(index=True, unique=True, min_length=3, max_length=50)
    password: str = Field(min_length=8)
    role: str = Field(default="user")

class UserCreate(BaseModel):
    username: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class UserOut(BaseModel):
    id: int
    username: str
    role: str  

class Token(BaseModel):
    access_token: str
    token_type: str

app = FastAPI(lifespan=lifespan)

@app.post("/register/", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(user: UserCreate, session: SessionDep) -> UserOut:
    db_user = await get_user(user.username, session=session)
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    new_user = User(username=user.username, password=hash_password(user.password), role="user")  
    session.add(new_user)
    await session.commit()
    await session.refresh(new_user)
    return new_user

@app.post("/login/", response_model=Token)
async def login(credentials: UserLogin, db: AsyncSession = Depends(get_db)):
    user = await get_user(credentials.username, db)
    if not user or not verify_password(credentials.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"}
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": user.username}, expires_delta=access_token_expires)
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/users/me", response_model=UserOut)
async def read_users_me(current_user: User = Depends(get_current_user)):
    if current_user.role != "user":
        return {
            "message": "You are admin",
            "id": current_user.id,
            "username": current_user.username,
            "role": current_user.role,
        }
    return current_user

@app.get("/admin/users", response_model=list[UserOut], dependencies=[Depends(require_role("admin"))])
async def get_users(session: SessionDep):
    stmt = select(User)
    result = await session.execute(stmt)
    users = result.scalars().all()
    return [UserOut(id=user.id, username=user.username, role=user.role) for user in users]

if __name__ == "__main__":
    uvicorn.run("index:app", reload=True)