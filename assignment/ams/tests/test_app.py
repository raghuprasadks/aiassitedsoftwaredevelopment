import io
import os
import tempfile

import pytest
from werkzeug.security import generate_password_hash

from app import create_app
from extensions import db
import models as m
from datetime import datetime, timezone


@pytest.fixture()
def app():
    directory = tempfile.TemporaryDirectory()
    app = create_app({
        "TESTING": True,
        "WTF_CSRF_ENABLED": False,
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{directory.name}/test.db",
        "UPLOAD_FOLDER": directory.name,
    })
    with app.app_context():
        db.create_all()
        admin = m.User(full_name="Admin", email="admin@test.edu",
                       password_hash=generate_password_hash("password"), role="ADMIN")
        professor = m.User(full_name="Professor", email="prof@test.edu",
                           password_hash=generate_password_hash("password"), role="PROFESSOR")
        student = m.User(full_name="Student", email="student@test.edu",
                         password_hash=generate_password_hash("password"), role="STUDENT")
        db.session.add_all([admin, professor, student])
        db.session.flush()
        prof = m.Professor(user_id=professor.user_id, employee_id="EMP1")
        year = m.AcademicYear(label="2026-2027", start_date=datetime(2026, 7, 1).date(),
                              end_date=datetime(2027, 6, 30).date())
        semester = m.Semester(number=3)
        db.session.add_all([prof, year, semester])
        db.session.flush()
        section = m.Section(academic_year_id=year.academic_year_id,
                            semester_id=semester.semester_id, name="A")
        subject = m.Subject(code="CS101", name="Test Subject", semester_id=semester.semester_id)
        db.session.add_all([section, subject])
        db.session.flush()
        student_profile = m.Student(user_id=student.user_id, usn="USN1",
                                    section_id=section.section_id, admission_year=2026)
        db.session.add(student_profile)
        db.session.flush()
        offering = m.CourseOffering(subject_id=subject.subject_id, section_id=section.section_id,
                                    professor_id=prof.professor_id)
        db.session.add(offering)
        db.session.flush()
        db.session.add(m.Enrollment(student_id=student_profile.student_id,
                                    course_offering_id=offering.course_offering_id))
        db.session.commit()
    yield app
    with app.app_context():
        db.session.remove()
        db.engine.dispose()
    directory.cleanup()


@pytest.fixture()
def client(app):
    return app.test_client()


def login(client, email):
    return client.post("/api/auth/login", json={"email": email, "password": "password"})


def test_login_and_role_profile(client):
    response = login(client, "student@test.edu")
    assert response.status_code == 200
    profile = client.get("/api/auth/profile")
    assert profile.get_json()["data"]["role"] == "STUDENT"


def test_student_cannot_create_assignment(client):
    login(client, "student@test.edu")
    response = client.post("/api/assignments", json={"title": "Test"})
    assert response.status_code == 403


def test_assignment_publish_and_student_submission(client):
    login(client, "prof@test.edu")
    due = datetime.now(timezone.utc).replace(hour=23, minute=59).isoformat()
    response = client.post("/api/assignments", json={
        "course_offering_id": 1,
        "title": "Linked Lists",
        "description": "Implementation",
        "instructions": "Submit source",
        "max_marks": 25,
        "due_date": due,
        "allow_late": False,
        "allow_resubmission": True,
    })
    assert response.status_code == 201
    assignment_id = response.get_json()["data"]["assignment_id"]
    assert client.patch(f"/api/assignments/{assignment_id}/publish").status_code == 200

    client.post("/api/auth/logout")
    login(client, "student@test.edu")
    response = client.post(
        f"/api/assignments/{assignment_id}/submissions",
        data={"comments": "My submission", "files": (io.BytesIO(b"print('hello')"), "solution.py")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 201
    assert response.get_json()["data"]["version"] == 1


def test_unsupported_upload_is_rejected(client):
    login(client, "prof@test.edu")
    due = (datetime.now(timezone.utc).replace(hour=23, minute=59)).isoformat()
    create = client.post("/api/assignments", json={
        "course_offering_id": 1, "title": "File test", "max_marks": 10, "due_date": due,
    })
    assignment_id = create.get_json()["data"]["assignment_id"]
    client.patch(f"/api/assignments/{assignment_id}/publish")
    client.post("/api/auth/logout")
    login(client, "student@test.edu")
    response = client.post(
        f"/api/assignments/{assignment_id}/submissions",
        data={"files": (io.BytesIO(b"MZ"), "malware.exe")},
        content_type="multipart/form-data",
    )
    assert response.status_code in (400, 415)
