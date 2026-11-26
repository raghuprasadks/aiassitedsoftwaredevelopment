import os
import sqlite3
from pathlib import Path
from typing import Any

from flask import Flask, g, jsonify, request
from werkzeug.exceptions import HTTPException


DATABASE_PATH = Path(__file__).with_name("todos.db")
TODO_FIELDS = {"title", "completed", "userId"}


def create_app(database_path: str | os.PathLike[str] = DATABASE_PATH) -> Flask:
    ui_directory = Path(__file__).resolve().parent.parent / "ui"
    app = Flask(
        __name__,
        static_folder=str(ui_directory),
        static_url_path="/ui",
    )
    app.config["DATABASE"] = str(database_path)

    @app.get("/")
    def serve_ui():
        return app.send_static_file("index.html")

    @app.get("/app.js")
    def serve_app_js():
        return app.send_static_file("app.js")

    @app.get("/styles.css")
    def serve_stylesheet():
        return app.send_static_file("styles.css")

    @app.errorhandler(HTTPException)
    def handle_http_exception(error: HTTPException):
        return jsonify(error=error.description), error.code or 500

    @app.errorhandler(500)
    def handle_internal_server_error(error: HTTPException):
        return jsonify(error="Internal server error"), 500

    @app.teardown_appcontext
    def close_database(_error: BaseException | None = None) -> None:
        connection = g.pop("database", None)
        if connection is not None:
            connection.close()

    def get_database() -> sqlite3.Connection:
        if "database" not in g:
            connection = sqlite3.connect(app.config["DATABASE"])
            connection.row_factory = sqlite3.Row
            g.database = connection
        return g.database

    def initialize_database() -> None:
        database_path = app.config["DATABASE"]
        if database_path != ":memory:":
            Path(database_path).parent.mkdir(parents=True, exist_ok=True)

        with sqlite3.connect(database_path) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS todos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL CHECK (user_id > 0),
                    title TEXT NOT NULL CHECK (length(trim(title)) > 0),
                    completed INTEGER NOT NULL DEFAULT 0 CHECK (completed IN (0, 1))
                )
                """
            )

    def serialize_todo(todo: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": todo["id"],
            "userId": todo["user_id"],
            "title": todo["title"],
            "completed": bool(todo["completed"]),
        }

    def validate_todo_data(
        data: Any,
        *,
        partial: bool = False,
    ) -> tuple[dict[str, Any] | None, tuple[Any, int] | None]:
        if not isinstance(data, dict):
            return None, (jsonify(error="Request body must be a JSON object"), 400)

        unknown_fields = set(data) - TODO_FIELDS
        if unknown_fields:
            return None, (
                jsonify(error=f"Unsupported field: {sorted(unknown_fields)[0]}"),
                400,
            )

        if not partial and "title" not in data:
            return None, (jsonify(error="title is required"), 400)

        validated: dict[str, Any] = {}
        if "title" in data:
            title = data["title"]
            if not isinstance(title, str) or not title.strip():
                return None, (jsonify(error="title must be a non-empty string"), 400)
            validated["title"] = title.strip()

        if "completed" in data:
            completed = data["completed"]
            if not isinstance(completed, bool):
                return None, (jsonify(error="completed must be a boolean"), 400)
            validated["completed"] = int(completed)
        elif not partial:
            validated["completed"] = 0

        if "userId" in data:
            user_id = data["userId"]
            if isinstance(user_id, bool) or not isinstance(user_id, int) or user_id < 1:
                return None, (jsonify(error="userId must be a positive integer"), 400)
            validated["user_id"] = user_id
        elif not partial:
            validated["user_id"] = 1

        if partial and not validated:
            return None, (jsonify(error="At least one todo field is required"), 400)

        return validated, None

    def find_todo(todo_id: int) -> sqlite3.Row | None:
        return get_database().execute(
            "SELECT id, user_id, title, completed FROM todos WHERE id = ?",
            (todo_id,),
        ).fetchone()

    @app.get("/todos")
    def list_todos():
        rows = get_database().execute(
            "SELECT id, user_id, title, completed FROM todos ORDER BY id"
        ).fetchall()
        return jsonify(todos=[serialize_todo(row) for row in rows])

    @app.post("/todos")
    def create_todo():
        data, error = validate_todo_data(request.get_json(silent=True))
        if error:
            return error

        database = get_database()
        cursor = database.execute(
            """
            INSERT INTO todos (user_id, title, completed)
            VALUES (?, ?, ?)
            """,
            (data["user_id"], data["title"], data["completed"]),
        )
        database.commit()
        if cursor.lastrowid is None:
            raise RuntimeError("The created todo could not be loaded from the database.")
        todo = find_todo(cursor.lastrowid)
        if todo is None:
            raise RuntimeError("The created todo could not be loaded from the database.")
        return jsonify(serialize_todo(todo)), 201

    @app.get("/todos/<int:todo_id>")
    def get_todo(todo_id: int):
        todo = find_todo(todo_id)
        if todo is None:
            return jsonify(error="Todo not found"), 404
        return jsonify(serialize_todo(todo))

    @app.put("/todos/<int:todo_id>")
    def replace_todo(todo_id: int):
        if find_todo(todo_id) is None:
            return jsonify(error="Todo not found"), 404

        data, error = validate_todo_data(request.get_json(silent=True))
        if error:
            return error

        database = get_database()
        database.execute(
            """
            UPDATE todos
            SET user_id = ?, title = ?, completed = ?
            WHERE id = ?
            """,
            (data["user_id"], data["title"], data["completed"], todo_id),
        )
        database.commit()
        todo = find_todo(todo_id)
        if todo is None:
            raise RuntimeError("The updated todo could not be loaded from the database.")
        return jsonify(serialize_todo(todo))

    @app.patch("/todos/<int:todo_id>")
    def update_todo(todo_id: int):
        if find_todo(todo_id) is None:
            return jsonify(error="Todo not found"), 404

        data, error = validate_todo_data(request.get_json(silent=True), partial=True)
        if error:
            return error

        assignments = ", ".join(f"{field} = ?" for field in data)
        database = get_database()
        database.execute(
            f"UPDATE todos SET {assignments} WHERE id = ?",
            (*data.values(), todo_id),
        )
        database.commit()
        todo = find_todo(todo_id)
        if todo is None:
            raise RuntimeError("The updated todo could not be loaded from the database.")
        return jsonify(serialize_todo(todo))

    @app.delete("/todos/<int:todo_id>")
    def delete_todo(todo_id: int):
        database = get_database()
        cursor = database.execute("DELETE FROM todos WHERE id = ?", (todo_id,))
        if cursor.rowcount == 0:
            return jsonify(error="Todo not found"), 404
        database.commit()
        return jsonify(message="Todo deleted", id=todo_id)

    initialize_database()
    return app


app = create_app()


if __name__ == "__main__":
    app.run(port=5003, debug=True)
