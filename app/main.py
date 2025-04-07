from flask import Flask, request, jsonify
import jwt as pyjwt, datetime
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = 'supersecretkey'

robot_state = {
    "status": "idle",
    "is_on": False,
    "position": {"x": 0, "y": 0},
    "battery": 87,
    "holding_object": False,
    "logs": [],
    "floor": 1
}

users = {"octavian": "password123"}


@app.route("/status", methods=["GET"])
def status():
    return jsonify({"message": "API is up"}), 200



def token_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace("Bearer ", "")
        if not token:
            return jsonify({"message": "Missing token"}), 401
        try:
            pyjwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
        except pyjwt.ExpiredSignatureError:
            return jsonify({"message": "Token expired"}), 401
        except pyjwt.InvalidTokenError:
            return jsonify({"message": "Invalid token"}), 401
        return f(*args, **kwargs)
    return wrapper


@app.route("/auth/login", methods=["POST"])
def login():
    data = request.json or {}
    username = data.get("username")
    password = data.get("password")
    if users.get(username) == password:
        token = pyjwt.encode({
            'user': username,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=30)
        }, app.config['SECRET_KEY'], algorithm="HS256")
        return jsonify({"token": token})
    return jsonify({"message": "Invalid credentials"}), 401


@app.route("/robot/start", methods=["POST"])
@token_required
def start_robot():
    if robot_state["status"] == "started":
        return jsonify({"error": "Robot already started"}), 409
    robot_state["is_on"] = True
    robot_state["status"] = "started"
    robot_state["logs"].append({"action": "start", "timestamp": datetime.datetime.now().isoformat()})
    return jsonify({"message": "Robot started"}), 200


@app.route("/robot/reset", methods=["POST"])
@token_required
def reset_robot():
    robot_state.update({
        "is_on": False,
        "status": "idle",
        "position": {"x": 0, "y": 0},
        "floor": 1,
        "holding_object": False,
        "logs": []
    })
    return jsonify({"message": "Robot reset"}), 200


@app.route("/robot/stop", methods=["POST"])
@token_required
def stop_robot():
    robot_state["is_on"] = False
    robot_state["status"] = "stopped"
    robot_state["logs"].append({"action": "stop", "timestamp": datetime.datetime.now().isoformat()})
    return jsonify({"message": "Robot stopped"}), 200


@app.route("/robot/status", methods=["GET"])
@token_required
def get_status():
    return jsonify({
        "status": robot_state["status"],
        "is_on": robot_state["is_on"],
        "position": robot_state["position"],
        "battery": robot_state["battery"],
        "holding_object": robot_state["holding_object"],
        "floor": robot_state["floor"]
    }), 200


@app.route("/robot/move", methods=["POST"])
@token_required
def move_robot():
    if not robot_state["is_on"]:
        return jsonify({"message": "Robot is off"}), 400

    direction = request.json.get("direction")
    if direction not in ["forward", "backward", "left", "right"]:
        return jsonify({"message": "Invalid direction"}), 400

    if direction == "forward":
        robot_state["position"]["y"] += 1
    elif direction == "backward":
        robot_state["position"]["y"] -= 1
    elif direction == "left":
        robot_state["position"]["x"] -= 1
    elif direction == "right":
        robot_state["position"]["x"] += 1

    robot_state["logs"].append({"action": f"move_{direction}", "timestamp": datetime.datetime.now().isoformat()})
    return jsonify({"message": f"Moved {direction}"}), 200


@app.route("/robot/go_to_floor", methods=["POST"])
@token_required
def go_to_floor():
    try:
        requested_floor = int(request.json.get("floor"))
    except (TypeError, ValueError):
        return jsonify({"message": "Floor must be an integer"}), 400

    if not (1 <= requested_floor <= 100):
        return jsonify({"message": "Invalid floor"}), 400

    if not robot_state.get("status", ["idle", "stooped"]):
        return jsonify({"message": "Robot must be started before requesting the lift"}), 400

    robot_state["floor"] = requested_floor
    robot_state["logs"].append({
        "action": f"requested lift to floor {requested_floor}",
        "timestamp": datetime.datetime.now().isoformat()
    })

    return jsonify({"message": f"Robot requested lift to floor {requested_floor}"}), 200


@app.route("/robot/lift_status", methods=["GET"])
@token_required
def lift_status():
    return jsonify({"current_floor": robot_state["floor"], "message": "Lift is functioning normally"}), 200


@app.route("/robot/logs", methods=["GET"])
@token_required
def get_logs():
    return jsonify(robot_state["logs"]), 200


if __name__ == "__main__":
    app.run(debug=True)
