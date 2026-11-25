from typing import Any

from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException

app = Flask(__name__)

users: dict[int, dict[str, Any]] = {}
next_user_id = 1


@app.errorhandler(HTTPException)
def handle_http_exception(error):
    return jsonify(error=error.description), error.code or 500


@app.errorhandler(500)
def handle_internal_server_error(error):
    return jsonify(error="Internal server error"), 500


def get_user_data():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return None, (jsonify(error="Request body must be a JSON object"), 400)
    return {key: value for key, value in data.items() if key != "id"}, None


@app.route("/users", methods=["POST"])
def create_user():
    global next_user_id
    data, error = get_user_data()
    if error:
        return error

    user_id = next_user_id
    next_user_id += 1
    user = {"id": user_id, **data}
    users[user_id] = user
    return jsonify(user), 201


@app.route("/users", methods=["GET"])
def list_users():
    return jsonify(users=list(users.values()))


@app.route("/users/<int:user_id>", methods=["GET"])
def get_user(user_id: int):
    user = users.get(user_id)
    if user is None:
        return jsonify(error="User not found"), 404
    return jsonify(user)


@app.route("/users/<int:user_id>", methods=["PUT"])
def replace_user(user_id: int):
    if user_id not in users:
        return jsonify(error="User not found"), 404

    data, error = get_user_data()
    if error:
        return error

    user = {"id": user_id, **data}
    users[user_id] = user
    return jsonify(user)


@app.route("/users/<int:user_id>", methods=["PATCH"])
def update_user(user_id: int):
    if user_id not in users:
        return jsonify(error="User not found"), 404

    data, error = get_user_data()
    if error:
        return error

    users[user_id].update(data)
    return jsonify(users[user_id])


@app.route("/users/<int:user_id>", methods=["DELETE"])
def delete_user(user_id: int):
    user = users.pop(user_id, None)
    if user is None:
        return jsonify(error="User not found"), 404
    return jsonify(message="User deleted", id=user_id)


if __name__ == "__main__":
    app.run(port=5002)
