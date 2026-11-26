import os
from datetime import datetime, timezone
from flask import Flask, jsonify, render_template, request, send_file
from flask_login import login_required, login_user, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_wtf.csrf import generate_csrf

from config import Config
from extensions import db, login_manager, migrate, csrf
import models as m


def utcnow():
    return datetime.now(timezone.utc)


def create_app(config_object=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(Config)
    if config_object:
        app.config.update(config_object)
    os.makedirs(app.instance_path, exist_ok=True)
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(m.User, int(user_id))

    @app.context_processor
    def inject_globals():
        return {"csrf_token": generate_csrf}

    @app.errorhandler(404)
    def not_found(error):
        if request.path.startswith("/api/"):
            return jsonify(success=False, error={"code": "NOT_FOUND", "message": "Resource not found"}), 404
        return render_template("404.html"), 404

    @app.errorhandler(413)
    def too_large(error):
        return jsonify(success=False, error={"code": "PAYLOAD_TOO_LARGE", "message": "Upload exceeds the size limit"}), 413

    @app.errorhandler(400)
    def bad_request(error):
        if request.path.startswith("/api/"):
            return jsonify(success=False, error={"code": "BAD_REQUEST", "message": "Invalid request"}), 400
        return render_template("404.html"), 400

    @app.route("/")
    def index():
        if current_user.is_authenticated:
            return dashboard()
        return render_template("login.html")

    @app.get("/login")
    def login_page():
        if current_user.is_authenticated:
            return dashboard()
        return render_template("login.html")

    @app.post("/api/auth/login")
    def login():
        data = request.get_json(silent=True) or request.form
        email = str(data.get("email", "")).strip().lower()
        password = str(data.get("password", ""))
        user = m.User.query.filter_by(email=email, is_active=True).first()
        if not user or not check_password_hash(user.password_hash, password):
            return jsonify(success=False, error={"code": "UNAUTHORIZED", "message": "Invalid email or password"}), 401
        login_user(user)
        return jsonify(success=True, data=user.to_profile())

    @app.post("/api/auth/logout")
    @login_required
    def logout():
        logout_user()
        return jsonify(success=True, data={"logged_out": True})

    @app.get("/api/auth/profile")
    @login_required
    def profile():
        return jsonify(success=True, data=current_user.to_profile())

    @app.put("/api/auth/password")
    @login_required
    def change_password():
        data = request.get_json(silent=True) or {}
        old_password = str(data.get("old_password", ""))
        new_password = str(data.get("new_password", ""))
        if not check_password_hash(current_user.password_hash, old_password):
            return jsonify(success=False, error={"code": "VALIDATION_ERROR", "message": "Current password is incorrect"}), 400
        if len(new_password) < 8:
            return jsonify(success=False, error={"code": "VALIDATION_ERROR", "message": "Password must contain at least 8 characters"}), 400
        current_user.password_hash = generate_password_hash(new_password)
        db.session.commit()
        return jsonify(success=True, data={"changed": True})

    def require_role(*roles):
        if current_user.role not in roles:
            return jsonify(success=False, error={"code": "FORBIDDEN", "message": "You are not authorized"}), 403
        return None

    @app.get("/dashboard")
    @login_required
    def dashboard():
        if current_user.role == "ADMIN":
            return render_template("dashboard_admin.html")
        if current_user.role == "PROFESSOR":
            return render_template("dashboard_professor.html")
        return render_template("dashboard_student.html")

    @app.get("/api/dashboard")
    @login_required
    def dashboard_api():
        if current_user.role == "STUDENT":
            student = current_user.student
            enrollments = m.Enrollment.query.filter_by(student_id=student.student_id, active=True).all()
            offering_ids = [e.course_offering_id for e in enrollments]
            assignments = m.Assignment.query.filter(
                m.Assignment.course_offering_id.in_(offering_ids),
                m.Assignment.status == "PUBLISHED",
            ).all() if offering_ids else []
            submitted = m.Submission.query.filter_by(student_id=student.student_id).all()
            submitted_ids = {s.assignment_id for s in submitted}
            pending = [a for a in assignments if a.assignment_id not in submitted_ids]
            return jsonify(success=True, data={
                "total": len(assignments),
                "pending": len(pending),
                "submitted": len(submitted),
                "assignments": [a.to_dict() for a in assignments],
            })
        if current_user.role == "PROFESSOR":
            professor = current_user.professor
            assignments = m.Assignment.query.filter_by(professor_id=professor.professor_id).all()
            return jsonify(success=True, data={
                "assignments": [a.to_dict() for a in assignments],
                "total_assignments": len(assignments),
            })
        return jsonify(success=True, data={"students": m.Student.query.count(),
                                            "professors": m.Professor.query.count(),
                                            "subjects": m.Subject.query.count(),
                                            "assignments": m.Assignment.query.count()})

    @app.get("/api/assignments")
    @login_required
    def list_assignments():
        if current_user.role == "STUDENT":
            student = current_user.student
            offering_ids = [e.course_offering_id for e in m.Enrollment.query.filter_by(
                student_id=student.student_id, active=True).all()]
            items = m.Assignment.query.filter(
                m.Assignment.course_offering_id.in_(offering_ids),
                m.Assignment.status.in_(["PUBLISHED", "CLOSED"]),
            ).all() if offering_ids else []
        elif current_user.role == "PROFESSOR":
            items = m.Assignment.query.filter_by(professor_id=current_user.professor.professor_id).all()
        else:
            items = m.Assignment.query.all()
        return jsonify(success=True, data=[a.to_dict() for a in items])

    @app.post("/api/assignments")
    @login_required
    def create_assignment():
        denied = require_role("PROFESSOR")
        if denied:
            return denied
        data = request.get_json(silent=True) or {}
        required = ("course_offering_id", "title", "max_marks", "due_date")
        missing = [field for field in required if data.get(field) in (None, "")]
        if missing:
            return jsonify(success=False, error={"code": "VALIDATION_ERROR", "message": "Invalid assignment",
                                                 "field_errors": {field: "Required" for field in missing}}), 400
        offering = db.session.get(m.CourseOffering, int(data["course_offering_id"]))
        if not offering or offering.professor_id != current_user.professor.professor_id:
            return jsonify(success=False, error={"code": "FORBIDDEN", "message": "Course offering is not allocated to you"}), 403
        try:
            due = datetime.fromisoformat(str(data["due_date"]).replace("Z", "+00:00"))
            max_marks = float(data["max_marks"])
        except (TypeError, ValueError):
            return jsonify(success=False, error={"code": "VALIDATION_ERROR", "message": "Invalid deadline or maximum marks"}), 400
        if max_marks <= 0:
            return jsonify(success=False, error={"code": "VALIDATION_ERROR", "message": "Maximum marks must be positive"}), 400
        assignment = m.Assignment(
            course_offering_id=offering.course_offering_id,
            professor_id=current_user.professor.professor_id,
            title=str(data["title"]).strip(),
            description=str(data.get("description", "")),
            instructions=str(data.get("instructions", "")),
            max_marks=max_marks,
            due_date=due,
            allow_late=bool(data.get("allow_late", False)),
            allow_resubmission=bool(data.get("allow_resubmission", True)),
        )
        db.session.add(assignment)
        db.session.commit()
        return jsonify(success=True, data={"assignment_id": assignment.assignment_id, "status": assignment.status}), 201

    @app.get("/api/assignments/<int:assignment_id>")
    @login_required
    def get_assignment(assignment_id):
        assignment = db.session.get(m.Assignment, assignment_id)
        if not assignment:
            return jsonify(success=False, error={"code": "NOT_FOUND", "message": "Assignment not found"}), 404
        if current_user.role == "PROFESSOR" and assignment.professor_id != current_user.professor.professor_id:
            return jsonify(success=False, error={"code": "FORBIDDEN", "message": "Forbidden"}), 403
        if current_user.role == "STUDENT":
            enrolled = m.Enrollment.query.filter_by(
                student_id=current_user.student.student_id,
                course_offering_id=assignment.course_offering_id,
                active=True,
            ).first()
            if not enrolled or assignment.status not in ("PUBLISHED", "CLOSED"):
                return jsonify(success=False, error={"code": "FORBIDDEN", "message": "Forbidden"}), 403
        return jsonify(success=True, data=assignment.to_dict())

    @app.patch("/api/assignments/<int:assignment_id>/<string:action>")
    @login_required
    def assignment_action(assignment_id, action):
        denied = require_role("PROFESSOR")
        if denied:
            return denied
        assignment = db.session.get(m.Assignment, assignment_id)
        if not assignment or assignment.professor_id != current_user.professor.professor_id:
            return jsonify(success=False, error={"code": "FORBIDDEN", "message": "Forbidden"}), 403
        transitions = {"publish": ("DRAFT", "PUBLISHED"), "close": ("PUBLISHED", "CLOSED"), "archive": ("CLOSED", "ARCHIVED")}
        if action not in transitions:
            return jsonify(success=False, error={"code": "NOT_FOUND", "message": "Action not found"}), 404
        required, target = transitions[action]
        if assignment.status != required:
            return jsonify(success=False, error={"code": "CONFLICT", "message": f"Assignment must be {required}"}), 409
        if action == "publish" and (not assignment.due_date or not assignment.max_marks):
            return jsonify(success=False, error={"code": "VALIDATION_ERROR", "message": "Deadline and maximum marks are required"}), 400
        assignment.status = target
        db.session.commit()
        return jsonify(success=True, data=assignment.to_dict())

    def allowed_upload(filename):
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        return ext in {"pdf", "docx", "txt", "jpg", "png", "py", "java", "c", "cpp", "js", "html", "zip"}

    @app.post("/api/assignments/<int:assignment_id>/submissions")
    @login_required
    def submit_assignment(assignment_id):
        denied = require_role("STUDENT")
        if denied:
            return denied
        assignment = db.session.get(m.Assignment, assignment_id)
        student = current_user.student
        if not assignment or assignment.status != "PUBLISHED":
            return jsonify(success=False, error={"code": "CONFLICT", "message": "Assignment is not accepting submissions"}), 409
        enrolled = m.Enrollment.query.filter_by(student_id=student.student_id,
                                                 course_offering_id=assignment.course_offering_id,
                                                 active=True).first()
        if not enrolled:
            return jsonify(success=False, error={"code": "FORBIDDEN", "message": "You are not enrolled"}), 403
        existing = m.Submission.query.filter_by(assignment_id=assignment_id, student_id=student.student_id).first()
        if existing:
            return jsonify(success=False, error={"code": "CONFLICT", "message": "Use the resubmission endpoint"}), 409
        now = utcnow()
        due = assignment.due_date
        if due.tzinfo is None:
            due = due.replace(tzinfo=timezone.utc)
        if now > due and not assignment.allow_late:
            return jsonify(success=False, error={"code": "CONFLICT", "message": "Deadline has passed"}), 409
        files = request.files.getlist("files")
        if not files:
            return jsonify(success=False, error={"code": "VALIDATION_ERROR", "message": "At least one file is required"}), 400
        if len(files) > 5:
            return jsonify(success=False, error={"code": "VALIDATION_ERROR", "message": "Maximum 5 files are allowed"}), 400
        staged = []
        try:
            total = 0
            for upload in files:
                filename = secure_filename(upload.filename)
                if not filename or not allowed_upload(filename):
                    raise ValueError("Unsupported file type")
                upload.stream.seek(0, 2)
                size = upload.stream.tell()
                upload.stream.seek(0)
                if size > 20 * 1024 * 1024:
                    raise ValueError("Individual file exceeds 20 MB")
                total += size
                if total > 50 * 1024 * 1024:
                    raise ValueError("Submission exceeds 50 MB")
                storage_name = f"{os.urandom(16).hex()}-{filename}"
                path = os.path.join(app.config["UPLOAD_FOLDER"], storage_name)
                upload.save(path)
                staged.append((path, filename, size))
            submission = m.Submission(assignment_id=assignment_id, student_id=student.student_id,
                                      comments=request.form.get("comments", ""),
                                      current_version=1, is_late=now > due)
            db.session.add(submission)
            db.session.flush()
            for index, (path, filename, size) in enumerate(staged):
                file_record = m.SubmissionFile(submission_id=submission.submission_id,
                                               version_no=1, storage_key=os.path.basename(path),
                                               original_name=filename, mime=files[index].mimetype or "application/octet-stream",
                                               size=size)
                db.session.add(file_record)
            db.session.commit()
            return jsonify(success=True, data={"submission_id": submission.submission_id,
                                               "version": 1, "is_late": submission.is_late}), 201
        except ValueError as exc:
            for path, _, _ in staged:
                if os.path.exists(path):
                    os.remove(path)
            return jsonify(success=False, error={"code": "VALIDATION_ERROR", "message": str(exc)}), 400
        except Exception:
            db.session.rollback()
            for path, _, _ in staged:
                if os.path.exists(path):
                    os.remove(path)
            raise

    @app.get("/api/my-submissions")
    @login_required
    def my_submissions():
        denied = require_role("STUDENT")
        if denied:
            return denied
        items = m.Submission.query.filter_by(student_id=current_user.student.student_id).all()
        return jsonify(success=True, data=[s.to_dict() for s in items])

    @app.get("/api/submissions/<int:submission_id>")
    @login_required
    def get_submission(submission_id):
        submission = db.session.get(m.Submission, submission_id)
        if not submission:
            return jsonify(success=False, error={"code": "NOT_FOUND", "message": "Submission not found"}), 404
        if current_user.role == "STUDENT" and submission.student_id != current_user.student.student_id:
            return jsonify(success=False, error={"code": "FORBIDDEN", "message": "Forbidden"}), 403
        if current_user.role == "PROFESSOR" and submission.assignment.professor_id != current_user.professor.professor_id:
            return jsonify(success=False, error={"code": "FORBIDDEN", "message": "Forbidden"}), 403
        return jsonify(success=True, data=submission.to_dict())

    @app.get("/api/files/<int:file_id>/download")
    @login_required
    def download_file(file_id):
        file_record = db.session.get(m.SubmissionFile, file_id)
        if not file_record:
            return jsonify(success=False, error={"code": "NOT_FOUND", "message": "File not found"}), 404
        submission = file_record.submission
        if current_user.role == "STUDENT" and submission.student_id != current_user.student.student_id:
            return jsonify(success=False, error={"code": "FORBIDDEN", "message": "Forbidden"}), 403
        if current_user.role == "PROFESSOR" and submission.assignment.professor_id != current_user.professor.professor_id:
            return jsonify(success=False, error={"code": "FORBIDDEN", "message": "Forbidden"}), 403
        path = os.path.join(app.config["UPLOAD_FOLDER"], file_record.storage_key)
        if not os.path.exists(path):
            return jsonify(success=False, error={"code": "NOT_FOUND", "message": "File not found"}), 404
        return send_file(path, as_attachment=True, download_name=file_record.original_name)

    @app.post("/api/submissions/<int:submission_id>/evaluation")
    @login_required
    def save_evaluation(submission_id):
        denied = require_role("PROFESSOR")
        if denied:
            return denied
        submission = db.session.get(m.Submission, submission_id)
        if not submission or submission.assignment.professor_id != current_user.professor.professor_id:
            return jsonify(success=False, error={"code": "FORBIDDEN", "message": "Forbidden"}), 403
        data = request.get_json(silent=True) or {}
        try:
            marks = float(data["marks"])
        except (KeyError, TypeError, ValueError):
            return jsonify(success=False, error={"code": "VALIDATION_ERROR", "message": "Marks are required"}), 400
        if marks < 0 or marks > float(submission.assignment.max_marks):
            return jsonify(success=False, error={"code": "VALIDATION_ERROR", "message": "Marks are outside the allowed range"}), 400
        evaluation = submission.evaluation
        if not evaluation:
            evaluation = m.Evaluation(submission_id=submission.submission_id,
                                      professor_id=current_user.professor.professor_id,
                                      version_no=submission.current_version)
            db.session.add(evaluation)
        evaluation.marks_obtained = marks
        evaluation.feedback = str(data.get("feedback", ""))
        evaluation.evaluated_at = utcnow()
        db.session.commit()
        return jsonify(success=True, data=evaluation.to_dict()), 201

    @app.patch("/api/evaluations/<int:evaluation_id>/publish")
    @login_required
    def publish_evaluation(evaluation_id):
        denied = require_role("PROFESSOR")
        if denied:
            return denied
        evaluation = db.session.get(m.Evaluation, evaluation_id)
        if not evaluation or evaluation.submission.assignment.professor_id != current_user.professor.professor_id:
            return jsonify(success=False, error={"code": "FORBIDDEN", "message": "Forbidden"}), 403
        evaluation.is_published = True
        evaluation.published_at = utcnow()
        notification = m.Notification(user_id=evaluation.submission.student.user_id,
                                      type="MARKS_PUBLISHED",
                                      message=f"Marks published for {evaluation.submission.assignment.title}",
                                      resource_id=evaluation.evaluation_id,
                                      dedupe_key=f"marks-{evaluation.evaluation_id}")
        db.session.add(notification)
        db.session.commit()
        return jsonify(success=True, data=evaluation.to_dict())

    @app.get("/api/my-results")
    @login_required
    def my_results():
        denied = require_role("STUDENT")
        if denied:
            return denied
        items = m.Submission.query.filter_by(student_id=current_user.student.student_id).all()
        return jsonify(success=True, data=[s.evaluation.to_dict() for s in items
                                           if s.evaluation and s.evaluation.is_published])

    @app.get("/api/notifications")
    @login_required
    def notifications():
        items = m.Notification.query.filter_by(user_id=current_user.user_id).order_by(m.Notification.created_at.desc()).all()
        return jsonify(success=True, data=[n.to_dict() for n in items])

    @app.patch("/api/notifications/<int:notification_id>/read")
    @login_required
    def read_notification(notification_id):
        notification = db.session.get(m.Notification, notification_id)
        if not notification or notification.user_id != current_user.user_id:
            return jsonify(success=False, error={"code": "FORBIDDEN", "message": "Forbidden"}), 403
        notification.read_at = utcnow()
        db.session.commit()
        return jsonify(success=True, data=notification.to_dict())

    @app.get("/api/reports/submissions")
    @login_required
    def submission_report():
        denied = require_role("PROFESSOR", "ADMIN")
        if denied:
            return denied
        items = []
        if current_user.role == "PROFESSOR":
            assignments = m.Assignment.query.filter_by(professor_id=current_user.professor.professor_id).all()
        else:
            assignments = m.Assignment.query.all()
        for assignment in assignments:
            enrollments = m.Enrollment.query.filter_by(course_offering_id=assignment.course_offering_id, active=True).all()
            submitted = m.Submission.query.filter_by(assignment_id=assignment.assignment_id).count()
            items.append({"assignment_id": assignment.assignment_id, "title": assignment.title,
                          "total_students": len(enrollments), "submitted": submitted,
                          "pending": max(0, len(enrollments) - submitted)})
        return jsonify(success=True, data=items)

    @app.cli.command("seed")
    def seed_command():
        db.create_all()
        if m.User.query.count():
            print("Database already seeded.")
            return
        admin = m.User(full_name="System Administrator", email="admin@bmsit.edu",
                       password_hash=generate_password_hash("Admin@123"), role="ADMIN")
        professor = m.User(full_name="Dr. Anita Rao", email="professor@bmsit.edu",
                           password_hash=generate_password_hash("Professor@123"), role="PROFESSOR")
        student = m.User(full_name="Arjun Kumar", email="student@bmsit.edu",
                         password_hash=generate_password_hash("Student@123"), role="STUDENT")
        db.session.add_all([admin, professor, student])
        db.session.flush()
        professor_profile = m.Professor(user_id=professor.user_id, employee_id="EMP001",
                                        designation="Associate Professor", department="CSE")
        year = m.AcademicYear(label="2026-2027", start_date=datetime(2026, 7, 1).date(),
                              end_date=datetime(2027, 6, 30).date(), active=True)
        semester = m.Semester(number=3)
        db.session.add_all([professor_profile, year, semester])
        db.session.flush()
        section = m.Section(academic_year_id=year.academic_year_id, semester_id=semester.semester_id, name="A")
        subject = m.Subject(code="CS233", name="Data Structures", semester_id=semester.semester_id)
        db.session.add_all([section, subject])
        db.session.flush()
        student_profile = m.Student(user_id=student.user_id, usn="1BM23CS001",
                                    section_id=section.section_id, admission_year=2023)
        db.session.add(student_profile)
        db.session.flush()
        offering = m.CourseOffering(subject_id=subject.subject_id, section_id=section.section_id,
                                    professor_id=professor_profile.professor_id)
        db.session.add(offering)
        db.session.flush()
        enrollment = m.Enrollment(student_id=student_profile.student_id,
                                  course_offering_id=offering.course_offering_id)
        db.session.add(enrollment)
        db.session.commit()
        print("Seeded admin@bmsit.edu / Admin@123")
        print("Seeded professor@bmsit.edu / Professor@123")
        print("Seeded student@bmsit.edu / Student@123")

    with app.app_context():
        db.create_all()

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
