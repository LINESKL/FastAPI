from datetime import datetime, UTC
from dotenv import load_dotenv
import os
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from typing import Optional, Annotated
from sqlalchemy.orm import DeclarativeBase
from fastapi import Depends
from sqlmodel import SQLModel
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession
from config.redis_cache import redis_cache
from config.settings import settings
load_dotenv()

CURRENT_DATETIME = datetime.now(UTC)  

SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

DATABASE_URL = str(settings.DATABASE_URL)
engine = create_async_engine(DATABASE_URL, echo=True)
session_factory = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

async def get_db():
    async with session_factory() as session:
        yield session

SessionDep = Annotated[AsyncSession, Depends(get_db)]

class Base(DeclarativeBase):
    pass

@asynccontextmanager
async def lifespan(app):
    await redis_cache.init_redis(str(settings.REDIS_URL))
    
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    
    yield
    
    await redis_cache.close()
    await engine.dispose()