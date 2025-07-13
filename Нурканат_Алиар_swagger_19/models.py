from sqlalchemy import select
from sqlmodel import SQLModel, Field, Relationship
from pydantic import BaseModel, Field as PydanticField
from typing import Optional, List
from metadata import (
    CURRENT_DATETIME,
    SECRET_KEY,
    ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    pwd_context,
    get_db,
    SessionDep
)
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from datetime import timedelta, datetime
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# Database Models
class User(SQLModel, table=True):
    """Модель пользователя в базе данных"""
    id: Optional[int] = Field(
        primary_key=True, 
        default=None,
        description="Уникальный идентификатор пользователя"
    )
    username: str = Field(
        index=True, 
        unique=True, 
        min_length=3, 
        max_length=50,
        description="Уникальное имя пользователя"
    )
    password: str = Field(
        min_length=8,
        description="Хэшированный пароль пользователя"
    )
    role: str = Field(
        default="user",
        description="Роль пользователя в системе"
    )
    notes: List["Note"] = Relationship(back_populates="owner")

class Note(SQLModel, table=True):
    """Модель заметки в базе данных"""
    id: Optional[int] = Field(
        primary_key=True, 
        default=None,
        description="Уникальный идентификатор заметки"
    )
    title: str = Field(
        max_length=100,
        description="Заголовок заметки"
    )
    content: str = Field(
        max_length=1000,
        description="Содержимое заметки"
    )
    owner_id: int = Field(
        foreign_key="user.id",
        description="ID владельца заметки"
    )
    owner: Optional[User] = Relationship(back_populates="notes")

# Pydantic Models для API
class UserCreate(BaseModel):
    """Модель для создания нового пользователя"""
    username: str = PydanticField(
        min_length=3,
        max_length=50,
        description="Уникальное имя пользователя",
        example="john_doe"
    )
    password: str = PydanticField(
        min_length=8,
        description="Пароль пользователя (минимум 8 символов)",
        example="strongpassword123"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "username": "john_doe",
                "password": "strongpassword123"
            }
        }

class UserLogin(BaseModel):
    """Модель для входа пользователя в систему"""
    username: str = PydanticField(
        description="Имя пользователя",
        example="john_doe"
    )
    password: str = PydanticField(
        description="Пароль пользователя",
        example="strongpassword123"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "username": "john_doe",
                "password": "strongpassword123"
            }
        }

class UserOut(BaseModel):
    """Модель пользователя для ответа API"""
    id: int = PydanticField(
        description="Уникальный идентификатор пользователя",
        example=1
    )
    username: str = PydanticField(
        description="Имя пользователя",
        example="john_doe"
    )
    role: str = PydanticField(
        description="Роль пользователя",
        example="user"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "username": "john_doe", 
                "role": "user"
            }
        }
        
class NoteCreate(BaseModel):
    """Модель для создания новой заметки"""
    title: str = PydanticField(
        min_length=1,
        max_length=100,
        description="Заголовок заметки",
        example="Моя первая заметка"
    )
    content: str = PydanticField(
        min_length=1,
        max_length=1000,
        description="Содержимое заметки",
        example="Это содержимое моей первой заметки в системе"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "title": "Моя первая заметка",
                "content": "Это содержимое моей первой заметки в системе"
            }
        }

class NoteUpdate(BaseModel):
    """Модель для обновления заметки"""
    title: Optional[str] = PydanticField(
        None,
        min_length=1,
        max_length=100,
        description="Новый заголовок заметки (необязательно)",
        example="Обновленный заголовок"
    )
    content: Optional[str] = PydanticField(
        None,
        min_length=1,
        max_length=1000,
        description="Новое содержимое заметки (необязательно)",
        example="Обновленное содержимое заметки"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "title": "Обновленный заголовок",
                "content": "Обновленное содержимое заметки"
            }
        }

class NoteOut(BaseModel):
    """Модель заметки для ответа API"""
    id: int = PydanticField(
        description="Уникальный идентификатор заметки",
        example=1
    )
    title: str = PydanticField(
        description="Заголовок заметки",
        example="Моя заметка"
    )
    content: str = PydanticField(
        description="Содержимое заметки",
        example="Содержимое заметки"
    )
    owner_id: int = PydanticField(
        description="ID владельца заметки",
        example=1
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "title": "Моя заметка",
                "content": "Содержимое заметки",
                "owner_id": 1
            }
        }

class Token(BaseModel):
    """Модель токена доступа"""
    access_token: str = PydanticField(
        description="JWT токен для аутентификации",
        example="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    )
    token_type: str = PydanticField(
        description="Тип токена",
        example="bearer"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer"
            }
        }


# Helper functions
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

def require_owner(current_user: User = Depends(get_current_user)):
    async def check_owner(note: Note):
        if note.owner_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. You can only manage your own notes."
            )
        return note
    return check_owner

