# BMSIT Assignment Management System

Full-stack Flask prototype based on the provided SRS and software design document.

## Setup

```powershell
cd <project-folder>
.\myenv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:SECRET_KEY="replace-with-a-random-secret"
flask --app app seed
python app.py
```

Open http://127.0.0.1:5000

## Demo accounts

| Role | Email | Password |
|---|---|---|
| Administrator | admin@bmsit.edu | Admin@123 |
| Professor | professor@bmsit.edu | Professor@123 |
| Student | student@bmsit.edu | Student@123 |

These accounts are synthetic seed data for local development only.
