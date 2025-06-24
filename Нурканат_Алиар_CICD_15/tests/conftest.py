import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, create_engine, Session
from sqlmodel.pool import StaticPool
from index import app
from metadata import SessionDep, get_db

@pytest.fixture(name="client")
def client_fixture():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    
    def get_db_override():
        with Session(engine) as session:
            yield session
    
    app.dependency_overrides[get_db] = get_db_override
    
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()

@pytest.fixture
def test_user(client):
    user_data = {
        "username": "testuser",
        "password": "testpass"
    }
    response = client.post(
        "/users/register/",
        json=user_data,
        headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 201
    return response.json()

@pytest.fixture
def auth_headers(client, test_user):
    login_data = {
        "username": "testuser",
        "password": "testpass"
    }
    response = client.post(
        "/users/login/",
        data=login_data,
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    print(response.json())  # Для отладки
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}