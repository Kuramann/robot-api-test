import pytest
import requests


# ---------------------- #
#      BASIC TESTS       #
# ---------------------- #

def test_status_code(base_url):
    """Test GET /status returns 200 OK."""
    response = requests.get(f"{base_url}/status")
    assert response.status_code == 200


# ---------------------- #
#     AUTHENTICATION     #
# ---------------------- #

@pytest.mark.auth
def test_valid_login(base_url):
    """Test login with valid credentials returns 200 OK."""
    response = requests.post(f"{base_url}/auth/login", json={
        "username": "octavian",
        "password": "password123"
    })
    assert response.status_code == 200


@pytest.mark.auth
def test_invalid_login(base_url):
    """Test login with invalid credentials returns 401 Unauthorized."""
    response = requests.post(f"{base_url}/auth/login", json={
        "username": "octavian",
        "password": "123password"
    })
    assert response.status_code == 401


@pytest.mark.auth
def test_notoken_endpoint(base_url):
    """Test accessing /robot/status without token returns 401."""
    response = requests.get(f"{base_url}/robot/status")
    assert response.status_code == 401


@pytest.mark.auth
def test_token_endpoint(base_url, token):
    """Test /robot/status with valid token returns 200 OK."""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{base_url}/robot/status", headers=headers)
    assert response.status_code == 200


@pytest.mark.auth
def test_token_expiration(base_url, token=1):
    """Test expired/invalid token returns 401 Unauthorized."""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{base_url}/robot/status", headers=headers)
    assert response.status_code == 401


# ---------------------- #
#     ROBOT STATUS       #
# ---------------------- #

@pytest.mark.robot
def test_robot_status_data(base_url, token):
    """Test /robot/status returns expected keys and value types."""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{base_url}/robot/status", headers=headers)
    assert response.status_code == 200
    data = response.json()

    for key in ["status", "battery", "position"]:
        assert key in data
    assert isinstance(data["status"], str)
    assert isinstance(data["battery"], int)
    assert isinstance(data["position"], dict)
    assert data["status"] in ["idle"]
    assert 0 <= data["battery"] <= 100


# ---------------------- #
#     ROBOT ACTIONS      #
# ---------------------- #

@pytest.mark.robot
def test_start_status(base_url, token):
    """Test robot can start and is_on becomes True."""
    headers = {"Authorization": f"Bearer {token}"}
    requests.post(f"{base_url}/robot/start", headers=headers)
    response = requests.get(f"{base_url}/robot/status", headers=headers)
    assert response.json()["is_on"] is True


@pytest.mark.robot
@pytest.mark.parametrize("direction, axis, delta", [
    ("forward", "y", 1),
    ("backward", "y", -1),
    ("left", "x", -1),
    ("right", "x", 1),
])
def test_robot_movement(base_url, token, reset_robot, direction, axis, delta):
    """Test robot movement updates position correctly."""
    headers = {"Authorization": f"Bearer {token}"}
    requests.post(f"{base_url}/robot/start", headers=headers)
    before = requests.get(f"{base_url}/robot/status", headers=headers).json()["position"]
    requests.post(f"{base_url}/robot/move", headers=headers, json={"direction": direction})
    after = requests.get(f"{base_url}/robot/status", headers=headers).json()["position"]
    assert after[axis] == before[axis] + delta


@pytest.mark.robot
def test_robot_logs(base_url, token):
    """Test robot logs include actions like start and move."""
    headers = {"Authorization": f"Bearer {token}"}
    requests.post(f"{base_url}/robot/start", headers=headers)
    requests.post(f"{base_url}/robot/move", headers=headers, json={"direction": "forward"})
    logs = requests.get(f"{base_url}/robot/logs", headers=headers).json()
    assert any("start" in entry["action"].lower() for entry in logs)
    assert any("move" in entry["action"].lower() for entry in logs)


@pytest.mark.robot
def test_robot_move_invalid(base_url, token):
    """Test invalid movement direction returns 400."""
    headers = {"Authorization": f"Bearer {token}"}
    requests.post(f"{base_url}/robot/start", headers=headers)
    response = requests.post(f"{base_url}/robot/move", headers=headers, json={"direction": "sideways"})
    assert response.status_code == 400


@pytest.mark.robot
def test_robot_start_invalid(base_url, token):
    """Test robot cannot be started twice (409 Conflict)."""
    headers = {"Authorization": f"Bearer {token}"}
    requests.post(f"{base_url}/robot/start", headers=headers)
    response = requests.post(f"{base_url}/robot/start", headers=headers)
    assert response.status_code == 409


# ---------------------- #
#     LIFT FUNCTIONS     #
# ---------------------- #

@pytest.mark.lift
def test_robot_go_to_floor(base_url, token):
    """Test robot can request a floor via lift."""
    headers = {"Authorization": f"Bearer {token}"}
    floor = 5
    requests.post(f"{base_url}/robot/start", headers=headers)
    response = requests.post(f"{base_url}/robot/go_to_floor", headers=headers, json={"floor": floor})
    assert response.status_code == 200
    assert f"Robot requested lift to floor {floor}" in response.json()["message"]
    lift_status = requests.get(f"{base_url}/robot/lift_status", headers=headers).json()
    assert lift_status["current_floor"] == floor


@pytest.mark.lift
def test_get_lift_status(base_url, token):
    """Test getting current lift floor status."""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{base_url}/robot/lift_status", headers=headers)
    assert response.status_code == 200


@pytest.mark.lift
def test_get_lift_notvalid(base_url, token):
    """Test calling lift when not near lift returns 400."""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.post(f"{base_url}/robot/go_to_floor", headers=headers, json={"floor": 3})
    assert response.status_code == 400


@pytest.mark.lift
def test_go_to_floor_and_check_logs(base_url, token):
    """Test robot floor request is logged."""
    headers = {"Authorization": f"Bearer {token}"}
    requests.post(f"{base_url}/robot/start", headers=headers)
    floor = 3
    requests.post(f"{base_url}/robot/go_to_floor", headers=headers, json={"floor": floor})
    status = requests.get(f"{base_url}/robot/status", headers=headers)
    assert status.json()["floor"] == floor
    logs = requests.get(f"{base_url}/robot/logs", headers=headers).json()
    assert any(f"requested lift to floor {floor}" in entry["action"].lower() for entry in logs)


@pytest.mark.lift
def test_take_lift_and_position_unchanged(base_url, token):
    """Test robot position is unchanged after taking lift."""
    headers = {"Authorization": f"Bearer {token}"}
    requests.post(f"{base_url}/robot/start", headers=headers)
    requests.post(f"{base_url}/robot/move", headers=headers, json={"direction": "forward"})
    requests.post(f"{base_url}/robot/move", headers=headers, json={"direction": "right"})
    position_before = requests.get(f"{base_url}/robot/status", headers=headers).json()["position"]
    requests.post(f"{base_url}/robot/go_to_floor", headers=headers, json={"floor": 10})
    status_after = requests.get(f"{base_url}/robot/status", headers=headers).json()
    assert status_after["floor"] == 10
    assert status_after["position"] == position_before


@pytest.mark.lift_stress
def test_stress_lift(base_url, token):
    """Test lift reaction when requested to move to more floors"""
    headers = {"Authorization": f"Bearer {token}"}
    requests.post(f"{base_url}/robot/start", headers=headers)
    for floor in range(1,101):
        floor_status = requests.post(f"{base_url}/robot/go_to_floor", headers=headers, json={"floor": floor})
        print("Lift at floor no", floor)
        assert floor_status.status_code == 200
