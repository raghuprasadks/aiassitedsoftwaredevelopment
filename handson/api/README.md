# Signup API

A small Flask API that stores signup details in SQLite and hashes passwords before
they are saved.

## Run locally

From the `api` directory:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
```

The API listens at `http://127.0.0.1:5000`. The SQLite database is created at
`api/instance/users.sqlite3` by default. Set `SIGNUP_DATABASE` to change its path.

## Create an account

Send a JSON `POST` request to `/api/signup`:

```json
{
  "name": "Alex",
  "email": "alex@example.com",
  "password": "a-strong-password"
}
```

`name` is optional. Email and password are required; passwords must be 8–128
characters. A successful response has status `201` and returns the new user's
ID, name, and email. It never returns the password or its hash. Invalid input
returns `400`, an existing email returns `409`, and an oversized body returns
`413`.

This example runs Flask's development server and is intended for local development.
