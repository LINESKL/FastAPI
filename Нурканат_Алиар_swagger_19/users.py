from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import select
from metadata import SessionDep
from models import User, UserCreate, UserOut, UserLogin, get_current_user, hash_password, verify_password, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES, timedelta, Token
from tests.tasks import send_email_task

router = APIRouter(
    prefix="/users",
    tags=["users"]
)

@router.post(
    "/register/", 
    response_model=UserOut, 
    status_code=status.HTTP_201_CREATED,
    summary="Регистрация нового пользователя",
    description="""
    Создает нового пользователя в системе.
    
    Требования:
    - Уникальное имя пользователя (3-50 символов)
    - Пароль минимум 8 символов
    
    Возвращает:
    - Информацию о созданном пользователе
    - Автоматически отправляет приветственное email
    """,
    responses={
        201: {
            "description": "Пользователь успешно создан",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "username": "john_doe",
                        "role": "user"
                    }
                }
            }
        },
        400: {
            "description": "Пользователь с таким именем уже существует",
            "content": {
                "application/json": {
                    "example": {"detail": "Username already registered"}
                }
            }
        },
        422: {
            "description": "Ошибка валидации данных",
            "content": {
                "application/json": {
                    "example": {
                        "detail": [
                            {
                                "loc": ["body", "username"],
                                "msg": "ensure this value has at least 3 characters",
                                "type": "value_error.any_str.min_length"
                            }
                        ]
                    }
                }
            }
        }
    }
)
async def register(user: UserCreate, session: SessionDep):
    """Регистрация нового пользователя"""
    db_user = await session.execute(select(User).where(User.username == user.username))
    if db_user.scalars().first():
        raise HTTPException(status_code=400, detail="Username already registered")
    new_user = User(username=user.username, password=hash_password(user.password))
    session.add(new_user)
    await session.commit()
    await session.refresh(new_user)
    # send_email_task.delay(
    #     recipient=new_user.username,
    #     subject="Welcome to Notes App",
    #     body="Thank you for registering!"
    # )
    return new_user

@router.post(
    "/login/", 
    response_model=Token,
    summary="Вход в систему",
    description="""
    Аутентификация пользователя и получение JWT токена.
    
    Процесс:
    1. Проверка существования пользователя
    2. Верификация пароля
    3. Создание JWT токена
    
    Использование токена:
    Добавьте полученный токен в заголовок: `Authorization: Bearer <token>`
    """,
    responses={
        200: {
            "description": "Успешная аутентификация",
            "content": {
                "application/json": {
                    "example": {
                        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                        "token_type": "bearer"
                    }
                }
            }
        },
        401: {
            "description": "Неверные учетные данные",
            "content": {
                "application/json": {
                    "example": {"detail": "Invalid credentials"}
                }
            }
        }
    }
)
async def login(credentials: UserLogin, session: SessionDep):
    user = await session.execute(select(User).where(User.username == credentials.username))
    user = user.scalars().first()
    if not user or not verify_password(credentials.password, user.password):
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": user.username}, expires_delta=access_token_expires)
    return {"access_token": access_token, "token_type": "bearer"}

@router.get(
    "/me", 
    response_model=UserOut,
    summary="Получение информации о текущем пользователе",
    description="""
    Возвращает информацию о текущем аутентифицированном пользователе.
    
    Требования:
    - Пользователь должен быть аутентифицирован
    - Необходимо передать валидный JWT токен в заголовке Authorization
    
    Возвращает:
    - ID пользователя
    - Имя пользователя
    - Роль в системе
    """,
    responses={
        200: {
            "description": "Информация о пользователе",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "username": "john_doe",
                        "role": "user"
                    }
                }
            }
        },
        401: {
            "description": "Пользователь не аутентифицирован",
            "content": {
                "application/json": {
                    "example": {"detail": "Not authenticated"}
                }
            }
        }
    }
)
async def read_users_me(current_user: User = Depends(get_current_user)):
    """Получение информации о текущем пользователе"""
    return current_user