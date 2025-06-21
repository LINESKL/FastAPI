import os
import pytest
import pytest_asyncio
import asyncio
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlmodel import SQLModel
from asgi_lifespan import LifespanManager

from index import app
from models import User, hash_password as get_password_hash, create_access_token, get_db
from metadata import Base

# Загрузка переменных окружения
load_dotenv()

# Настройка тестовой базы данных
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", "postgresql+asyncpg://lineskin:altel8708@localhost/Test")
test_async_engine = create_async_engine(TEST_DATABASE_URL, echo=True)
TestingSessionLocal = async_sessionmaker(autocommit=False, autoflush=False, bind=test_async_engine)

# Переопределение зависимости get_db для тестов
async def override_get_db():
    async with TestingSessionLocal() as session:
        yield session

app.dependency_overrides[get_db] = override_get_db

@pytest_asyncio.fixture(scope="session")
async def setup_database():
    """
    Фикстура для создания таблиц в тестовой базе данных.
    """
    try:
        print("Настройка тестовой базы данных...")
        async with test_async_engine.begin() as conn:
            print("Удаление существующих таблиц...")
            await conn.run_sync(Base.metadata.drop_all)
            print("Создание таблиц...")
            await conn.run_sync(Base.metadata.create_all)
            print("Таблицы успешно созданы")
    except Exception as e:
        print(f"Ошибка настройки базы данных: {e}")
        raise

@pytest_asyncio.fixture(scope="session", autouse=True)
async def cleanup_database():
    """
    Фикстура для очистки тестовой базы данных после всех тестов.
    """
    yield
    try:
        print("Очистка тестовой базы данных...")
        async with test_async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            print("Тестовая база данных очищена")
    except Exception as e:
        print(f"Ошибка очистки базы данных: {e}")
        raise

@pytest_asyncio.fixture(scope="function")
async def client(setup_database):
    """
    Фикстура для предоставления AsyncClient с тестовым пользователем.
    """
    print("Создание тестового пользователя...")
    async with TestingSessionLocal() as session:
        hashed_password = get_password_hash("testpass")
        test_user = User(username="testuser", password=hashed_password, role="user")
        session.add(test_user)
        await session.commit()
        print("Тестовый пользователь создан")

    print("Настройка AsyncClient...")
    async with LifespanManager(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(base_url="http://test", transport=transport) as c:
            yield c
    print("AsyncClient завершён")

@pytest.mark.asyncio
async def test_register(client: AsyncClient):
    """
    Тест регистрации нового пользователя и обработки дубликата.
    """
    print("Запуск теста test_register...")
    res = await client.post("/users/register/", json={"username": "newuser", "password": "newpass"})
    assert res.status_code == 201
    data = res.json()
    assert data["username"] == "newuser"
    assert data["role"] == "user"

    res_dup = await client.post("/users/register/", json={"username": "newuser", "password": "newpass"})
    assert res_dup.status_code == 400
    assert res_dup.json()["detail"] == "Username already registered"
    print("Тест test_register завершён")

@pytest.mark.asyncio
async def test_login(client: AsyncClient):
    """
    Тест входа с правильными и неправильными учетными данными.
    """
    print("Запуск теста test_login...")
    res = await client.post("/users/login/", json={"username": "testuser", "password": "testpass"})
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

    res_fail = await client.post("/users/login/", json={"username": "testuser", "password": "wrongpass"})
    assert res_fail.status_code == 401
    assert res_fail.json()["detail"] == "Incorrect username or password"
    print("Тест test_login завершён")

@pytest.mark.asyncio
async def test_users_me_authenticated(client: AsyncClient):
    """
    Тест доступа к защищённому эндпоинту /users/me.
    """
    print("Запуск теста test_users_me_authenticated...")
    token = create_access_token({"sub": "testuser"})
    headers = {"Authorization": f"Bearer {token}"}

    res = await client.get("/users/me", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["username"] == "testuser"
    assert data["role"] == "user"

    res_no_token = await client.get("/users/me")
    assert res_no_token.status_code == 401
    assert res_no_token.json()["detail"] == "Could not validate credentials"
    print("Тест test_users_me_authenticated завершён")

@pytest.mark.asyncio
async def test_notes_crud(client: AsyncClient):
    """
    Тест CRUD операций с заметками.
    """
    print("Запуск теста test_notes_crud...")
    token = create_access_token({"sub": "testuser"})
    headers = {"Authorization": f"Bearer {token}"}

    # Создание заметки
    res_create = await client.post("/notes/", json={"title": "Test Note", "content": "Test Content"}, headers=headers)
    assert res_create.status_code == 200
    note = res_create.json()
    assert note["title"] == "Test Note"
    assert note["content"] == "Test Content"
    note_id = note["id"]

    # Получение списка заметок
    res_all = await client.get("/notes/", headers=headers)
    assert res_all.status_code == 200
    notes = res_all.json()
    assert any(n["id"] == note_id for n in notes)

    # Получение конкретной заметки
    res_get = await client.get(f"/notes/{note_id}", headers=headers)
    assert res_get.status_code == 200
    assert res_get.json()["id"] == note_id

    # Обновление заметки
    res_update = await client.put(f"/notes/{note_id}", json={"title": "Updated Note", "content": "Updated Content"}, headers=headers)
    assert res_update.status_code == 200
    updated_note = res_update.json()
    assert updated_note["title"] == "Updated Note"
    assert updated_note["content"] == "Updated Content"

    # Удаление заметки
    res_del = await client.delete(f"/notes/{note_id}", headers=headers)
    assert res_del.status_code == 200
    assert res_del.json()["detail"] == "Note deleted"

    # Повторное удаление
    res_del_fail = await client.delete(f"/notes/{note_id}", headers=headers)
    assert res_del_fail.status_code == 404
    assert res_del_fail.json()["detail"] == "Note not found or access denied"

    # Тест доступа к чужой заметке
    async with TestingSessionLocal() as session:
        hashed_password = get_password_hash("otherpass")
        other_user = User(username="otheruser", password=hashed_password, role="user")
        session.add(other_user)
        await session.commit()
        await session.refresh(other_user)
        other_user_id = other_user.id

    other_token = create_access_token({"sub": "otheruser"})
    other_headers = {"Authorization": f"Bearer {other_token}"}
    res_other_note = await client.post("/notes/", json={"title": "Other Note", "content": "Other Content"}, headers=other_headers)
    assert res_other_note.status_code == 200
    other_note_id = res_other_note.json()["id"]

    res_access_denied = await client.get(f"/notes/{other_note_id}", headers=headers)
    assert res_access_denied.status_code == 404
    assert res_access_denied.json()["detail"] == "Note not found or access denied"
    print("Тест test_notes_crud завершён")