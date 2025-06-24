from fastapi.testclient import TestClient
import pytest

def test_register_user(client):
    response = client.post(
        "/users/register/",
        json={"username": "testuser", "password": "testpass"},
        headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 201
    assert "username" in response.json()

def test_login_user(client):
    login_response = client.post(
        "/users/login/",
        data={"username": "testuser", "password": "testpass"},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    print(login_response.json())  
    assert login_response.status_code == 422
