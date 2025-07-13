from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import select
from metadata import SessionDep
from models import Note, NoteCreate, NoteOut, NoteUpdate, User, get_current_user
from config.redis_cache import redis_cache

router = APIRouter(
    prefix="/notes",
    tags=["notes"]
)

@router.post(
    "/", 
    response_model=NoteOut,
    status_code=201,
    summary="Создание новой заметки",
    description="""
    Создает новую заметку для текущего пользователя.
    
    Требования:
    - Пользователь должен быть аутентифицирован
    - Заголовок: 1-100 символов
    - Содержимое: 1-1000 символов
    
    Возвращает:
    - Созданную заметку с ID и информацией о владельце
    """,
    responses={
        201: {
            "description": "Заметка успешно создана",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "title": "Моя первая заметка",
                        "content": "Это содержимое моей первой заметки",
                        "owner_id": 1
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
        },
        422: {
            "description": "Ошибка валидации данных",
            "content": {
                "application/json": {
                    "example": {
                        "detail": [
                            {
                                "loc": ["body", "title"],
                                "msg": "ensure this value has at least 1 characters",
                                "type": "value_error.any_str.min_length"
                            }
                        ]
                    }
                }
            }
        }
    }
)
async def create_note(note: NoteCreate, session: SessionDep, current_user: User = Depends(get_current_user)):
    """Создание новой заметки"""
    new_note = Note(title=note.title, content=note.content, owner_id=current_user.id)
    session.add(new_note)
    await session.commit()
    await session.refresh(new_note)
    return new_note

@router.get(
    "/", 
    response_model=list[NoteOut],
    summary="Получение списка заметок",
    description="""
    Возвращает список заметок текущего пользователя с поддержкой:
    
    Фильтрация:
    - Поиск по заголовку и содержимому заметок
    
    Пагинация:
    - skip: количество записей для пропуска (по умолчанию 0)
    - limit: максимальное количество записей (по умолчанию 10, максимум 100)
    
    Кеширование:
    - Результаты кешируются на 60 секунд для улучшения производительности
    """,
    responses={
        200: {
            "description": "Список заметок пользователя",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "id": 1,
                            "title": "Первая заметка",
                            "content": "Содержимое первой заметки",
                            "owner_id": 1
                        },
                        {
                            "id": 2,
                            "title": "Вторая заметка", 
                            "content": "Содержимое второй заметки",
                            "owner_id": 1
                        }
                    ]
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
@redis_cache.cache(key_prefix="notes", ttl=60)
async def list_notes(
    session: SessionDep, 
    current_user: User = Depends(get_current_user), 
    skip: int = Query(0, ge=0, description="Количество записей для пропуска"),
    limit: int = Query(10, le=100, description="Максимальное количество записей"),
    search: str = Query(None, description="Поиск по заголовку и содержимому")
    ):
    """Получение списка заметок с поиском и пагинацией"""

    stmt = select(Note).where(Note.owner_id == current_user.id)
    if search:
        search_term = f"%{search}%"
        stmt = stmt.where(
            (Note.title.ilike(search_term)) | (Note.content.ilike(search_term))
        )
    stmt = stmt.offset(skip).limit(limit)
    result = await session.execute(stmt)
    notes = result.scalars().all()
    return notes

@router.get(
    "/{note_id}", 
    response_model=NoteOut,
    summary="Получение заметки по ID",
    description="""
    Возвращает конкретную заметку по её идентификатору.
    
    Безопасность:
    - Пользователь может получить только свои заметки
    - Автоматическая проверка владельца
    
    Параметры:
    - note_id: уникальный идентификатор заметки
    """,
    responses={
        200: {
            "description": "Заметка найдена",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "title": "Моя заметка",
                        "content": "Содержимое заметки",
                        "owner_id": 1
                    }
                }
            }
        },
        404: {
            "description": "Заметка не найдена или доступ запрещен",
            "content": {
                "application/json": {
                    "example": {"detail": "Note not found or access denied"}
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
async def get_note(note_id: int, session: SessionDep, current_user: User = Depends(get_current_user)):
    """Получение заметки по ID с проверкой владельца"""
    stmt = select(Note).where(Note.id == note_id, Note.owner_id == current_user.id)
    result = await session.execute(stmt)
    note = result.scalars().first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found or access denied")
    return note

@router.put(
    "/{note_id}", 
    response_model=NoteOut,
    summary="Обновление заметки",
    description="""
    Обновляет существующую заметку.
    
    Особенности:
    - Частичное обновление (можно обновить только заголовок или только содержимое)
    - Пользователь может обновлять только свои заметки
    - Валидация размеров полей (заголовок: 1-100 символов, содержимое: 1-1000 символов)
    
    Параметры:
    - note_id: ID заметки для обновления
    - Тело запроса: поля для обновления (все поля необязательные)
    """,
    responses={
        200: {
            "description": "Заметка успешно обновлена",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "title": "Обновленный заголовок",
                        "content": "Обновленное содержимое",
                        "owner_id": 1
                    }
                }
            }
        },
        404: {
            "description": "Заметка не найдена или доступ запрещен",
            "content": {
                "application/json": {
                    "example": {"detail": "Note not found or access denied"}
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
        },
        422: {
            "description": "Ошибка валидации данных",
            "content": {
                "application/json": {
                    "example": {
                        "detail": [
                            {
                                "loc": ["body", "title"],
                                "msg": "ensure this value has at most 100 characters",
                                "type": "value_error.any_str.max_length"
                            }
                        ]
                    }
                }
            }
        }
    }
)
async def update_note(note_id: int, note: NoteUpdate, session: SessionDep, current_user: User = Depends(get_current_user)):
    """Обновление заметки с проверкой владельца"""
    stmt = select(Note).where(Note.id == note_id, Note.owner_id == current_user.id)
    result = await session.execute(stmt)
    db_note = result.scalars().first()
    if not db_note:
        raise HTTPException(status_code=404, detail="Note not found or access denied")
    if note.title is not None:
        db_note.title = note.title
    if note.content is not None:
        db_note.content = note.content
    session.add(db_note)
    await session.commit()
    await session.refresh(db_note)
    return db_note

@router.delete(
    "/{note_id}",
    status_code=200,
    summary="Удаление заметки",
    description="""
    Удаляет заметку по её идентификатору.
    
    Безопасность:
    - Пользователь может удалить только свои заметки
    - Автоматическая проверка владельца
    - Безвозвратное удаление
    
    Параметры:
    - note_id: уникальный идентификатор заметки для удаления
    """,
    responses={
        200: {
            "description": "Заметка успешно удалена",
            "content": {
                "application/json": {
                    "example": {"detail": "Note deleted"}
                }
            }
        },
        404: {
            "description": "Заметка не найдена или доступ запрещен",
            "content": {
                "application/json": {
                    "example": {"detail": "Note not found or access denied"}
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
async def delete_note(note_id: int, session: SessionDep, current_user: User = Depends(get_current_user)):
    """Удаление заметки с проверкой владельца"""
    stmt = select(Note).where(Note.id == note_id, Note.owner_id == current_user.id)
    result = await session.execute(stmt)
    note = result.scalars().first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found or access denied")
    session.delete(note)
    await session.commit()
    return {"detail": "Note deleted"}