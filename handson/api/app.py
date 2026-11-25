import os
import re
import sqlite3
from pathlib import Path
from typing import Any, Dict, Optional

from flask import Flask, current_app, g, jsonify, request
from werkzeug.security import generate_password_hash


EMAIL_PATTERN = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")
MAX_REQUEST_SIZE = 16 * 1024


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        connection = sqlite3.connect(current_app.config["DATABASE"])
        connection.row_factory = sqlite3.Row
        g.db = connection
    return g.db


def close_db(_error: Optional[BaseException] = None) -> None:
    connection = g.pop("db", None)
    if connection is not None:
        connection.close()


def initialize_database() -> None:
    database_path = Path(current_app.config["DATABASE"])
    database_path.parent.mkdir(parents=True, exist_ok=True)

    connection = get_db()
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    connection.commit()


def create_app(test_config: Optional[Dict[str, Any]] = None) -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        DATABASE=os.environ.get(
            "SIGNUP_DATABASE",
            str(Path(app.instance_path) / "users.sqlite3"),
        ),
        MAX_CONTENT_LENGTH=MAX_REQUEST_SIZE,
    )
    if test_config is not None:
        app.config.update(test_config)

    app.teardown_appcontext(close_db)

    with app.app_context():
        initialize_database()

    @app.post("/api/signup")
    def signup():
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return jsonify(error="Request body must be a JSON object."), 400

        email = data.get("email")
        password = data.get("password")
        name = data.get("name")

        if not isinstance(email, str) or not isinstance(password, str):
            return jsonify(error="Email and password are required."), 400

        email = email.strip().lower()
        if len(email) > 254 or not EMAIL_PATTERN.fullmatch(email):
            return jsonify(error="Enter a valid email address."), 400

        if not 8 <= len(password) <= 128:
            return jsonify(error="Password must be between 8 and 128 characters."), 400

        if name is not None and not isinstance(name, str):
            return jsonify(error="Name must be a string."), 400

        name = name.strip() if isinstance(name, str) else None
        if name == "":
            name = None
        if name is not None and len(name) > 100:
            return jsonify(error="Name must be 100 characters or fewer."), 400

        password_hash = generate_password_hash(password)
        connection = get_db()
        try:
            cursor = connection.execute(
                "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
                (name, email, password_hash),
            )
            connection.commit()
        except sqlite3.IntegrityError:
            connection.rollback()
            return jsonify(error="An account with this email already exists."), 409

        return jsonify(
            message="Account created successfully.",
            user={"id": cursor.lastrowid, "name": name, "email": email},
        ), 201

    @app.errorhandler(413)
    def request_too_large(_error):
        return jsonify(error="Request body is too large."), 413

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
