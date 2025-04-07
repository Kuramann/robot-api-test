import pytest
import requests

@pytest.fixture(scope="session")
def base_url(request):
    return request.config.getoption("--base-url")

@pytest.fixture(scope="session")
def token(base_url):
    response = requests.post(f"{base_url}/auth/login", json={
        "username": "octavian",
        "password": "password123"
    })
    print("TOKEN RESPONSE:", response.text)  # Ajută la debugging
    return response.json().get("token")

@pytest.fixture(autouse=True)
def reset_robot(base_url, token):
    headers = {"Authorization": f"Bearer {token}"}
    requests.post(f"{base_url}/robot/reset", headers=headers)

def pytest_addoption(parser):
    parser.addoption("--base-url", action="store", default="http://localhost:5000")

