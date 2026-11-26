from datetime import datetime, timezone
from flask_login import UserMixin
from extensions import db


def utcnow():
    return datetime.now(timezone.utc)


class User(db.Model, UserMixin):
    __tablename__ = "users"
    user_id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    student = db.relationship("Student", back_populates="user", uselist=False)
    professor = db.relationship("Professor", back_populates="user", uselist=False)

    def get_id(self):
        return str(self.user_id)

    def to_profile(self):
        return {"user_id": self.user_id, "name": self.full_name,
                "email": self.email, "role": self.role}


class AcademicYear(db.Model):
    __tablename__ = "academic_years"
    academic_year_id = db.Column(db.Integer, primary_key=True)
    label = db.Column(db.String(20), unique=True, nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    active = db.Column(db.Boolean, default=True, nullable=False)


class Semester(db.Model):
    __tablename__ = "semesters"
    semester_id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.Integer, unique=True, nullable=False)


class Section(db.Model):
    __tablename__ = "sections"
    section_id = db.Column(db.Integer, primary_key=True)
    academic_year_id = db.Column(db.Integer, db.ForeignKey("academic_years.academic_year_id"), nullable=False)
    semester_id = db.Column(db.Integer, db.ForeignKey("semesters.semester_id"), nullable=False)
    name = db.Column(db.String(20), nullable=False)
    __table_args__ = (db.UniqueConstraint("academic_year_id", "semester_id", "name", name="uq_section"),)


class Subject(db.Model):
    __tablename__ = "subjects"
    subject_id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(30), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    semester_id = db.Column(db.Integer, db.ForeignKey("semesters.semester_id"), nullable=False)


class Student(db.Model):
    __tablename__ = "students"
    student_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.user_id"), unique=True, nullable=False)
    usn = db.Column(db.String(30), unique=True, nullable=False)
    section_id = db.Column(db.Integer, db.ForeignKey("sections.section_id"), nullable=False)
    admission_year = db.Column(db.Integer, nullable=False)
    user = db.relationship("User", back_populates="student")
    enrollments = db.relationship("Enrollment", back_populates="student")


class Professor(db.Model):
    __tablename__ = "professors"
    professor_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.user_id"), unique=True, nullable=False)
    employee_id = db.Column(db.String(30), unique=True, nullable=False)
    designation = db.Column(db.String(100))
    department = db.Column(db.String(100))
    user = db.relationship("User", back_populates="professor")


class CourseOffering(db.Model):
    __tablename__ = "course_offerings"
    course_offering_id = db.Column(db.Integer, primary_key=True)
    subject_id = db.Column(db.Integer, db.ForeignKey("subjects.subject_id"), nullable=False)
    section_id = db.Column(db.Integer, db.ForeignKey("sections.section_id"), nullable=False)
    professor_id = db.Column(db.Integer, db.ForeignKey("professors.professor_id"), nullable=False)
    __table_args__ = (db.UniqueConstraint("subject_id", "section_id", "professor_id", name="uq_offering"),)
    subject = db.relationship("Subject")
    section = db.relationship("Section")
    professor = db.relationship("Professor")


class Enrollment(db.Model):
    __tablename__ = "enrollments"
    enrollment_id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.student_id"), nullable=False)
    course_offering_id = db.Column(db.Integer, db.ForeignKey("course_offerings.course_offering_id"), nullable=False)
    active = db.Column(db.Boolean, default=True, nullable=False)
    __table_args__ = (db.UniqueConstraint("student_id", "course_offering_id", name="uq_enrollment"),)
    student = db.relationship("Student", back_populates="enrollments")
    offering = db.relationship("CourseOffering")


class Assignment(db.Model):
    __tablename__ = "assignments"
    assignment_id = db.Column(db.Integer, primary_key=True)
    course_offering_id = db.Column(db.Integer, db.ForeignKey("course_offerings.course_offering_id"), nullable=False)
    professor_id = db.Column(db.Integer, db.ForeignKey("professors.professor_id"), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    instructions = db.Column(db.Text)
    max_marks = db.Column(db.Numeric(7, 2), nullable=False)
    due_date = db.Column(db.DateTime, nullable=False)
    allow_late = db.Column(db.Boolean, default=False, nullable=False)
    allow_resubmission = db.Column(db.Boolean, default=True, nullable=False)
    status = db.Column(db.String(20), default="DRAFT", nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow, nullable=False)
    offering = db.relationship("CourseOffering")
    submissions = db.relationship("Submission", back_populates="assignment")

    def to_dict(self):
        due = self.due_date.isoformat() if self.due_date else None
        return {"assignment_id": self.assignment_id,
                "title": self.title,
                "description": self.description or "",
                "instructions": self.instructions or "",
                "max_marks": float(self.max_marks),
                "due_date": due,
                "allow_late": self.allow_late,
                "allow_resubmission": self.allow_resubmission,
                "status": self.status,
                "course_offering_id": self.course_offering_id,
                "subject": self.offering.subject.name if self.offering and self.offering.subject else None}


class Submission(db.Model):
    __tablename__ = "submissions"
    submission_id = db.Column(db.Integer, primary_key=True)
    assignment_id = db.Column(db.Integer, db.ForeignKey("assignments.assignment_id"), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey("students.student_id"), nullable=False)
    current_version = db.Column(db.Integer, default=1, nullable=False)
    submitted_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    is_late = db.Column(db.Boolean, default=False, nullable=False)
    status = db.Column(db.String(20), default="SUBMITTED", nullable=False)
    comments = db.Column(db.Text)
    __table_args__ = (db.UniqueConstraint("assignment_id", "student_id", name="uq_submission"),)
    assignment = db.relationship("Assignment", back_populates="submissions")
    student = db.relationship("Student")
    files = db.relationship("SubmissionFile", back_populates="submission", cascade="all, delete-orphan")
    evaluation = db.relationship("Evaluation", back_populates="submission", uselist=False)

    def to_dict(self):
        return {"submission_id": self.submission_id,
                "assignment_id": self.assignment_id,
                "assignment_title": self.assignment.title,
                "student_name": self.student.user.full_name,
                "current_version": self.current_version,
                "submitted_at": self.submitted_at.isoformat(),
                "is_late": self.is_late,
                "status": self.status,
                "comments": self.comments or "",
                "files": [{"file_id": f.file_id, "original_name": f.original_name,
                           "version_no": f.version_no} for f in self.files],
                "evaluation": self.evaluation.to_dict() if self.evaluation else None}


class SubmissionFile(db.Model):
    __tablename__ = "submission_files"
    file_id = db.Column(db.Integer, primary_key=True)
    submission_id = db.Column(db.Integer, db.ForeignKey("submissions.submission_id"), nullable=False)
    version_no = db.Column(db.Integer, nullable=False)
    storage_key = db.Column(db.String(255), unique=True, nullable=False)
    original_name = db.Column(db.String(255), nullable=False)
    mime = db.Column(db.String(100), nullable=False)
    size = db.Column(db.Integer, nullable=False)
    sha256 = db.Column(db.String(64))
    uploaded_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    submission = db.relationship("Submission", back_populates="files")


class Evaluation(db.Model):
    __tablename__ = "evaluations"
    evaluation_id = db.Column(db.Integer, primary_key=True)
    submission_id = db.Column(db.Integer, db.ForeignKey("submissions.submission_id"), unique=True, nullable=False)
    professor_id = db.Column(db.Integer, db.ForeignKey("professors.professor_id"), nullable=False)
    version_no = db.Column(db.Integer, nullable=False)
    marks_obtained = db.Column(db.Numeric(7, 2))
    feedback = db.Column(db.Text)
    evaluated_at = db.Column(db.DateTime)
    is_published = db.Column(db.Boolean, default=False, nullable=False)
    published_at = db.Column(db.DateTime)
    submission = db.relationship("Submission", back_populates="evaluation")
    professor = db.relationship("Professor")

    def to_dict(self):
        return {"evaluation_id": self.evaluation_id,
                "submission_id": self.submission_id,
                "marks": float(self.marks_obtained) if self.marks_obtained is not None else None,
                "feedback": self.feedback or "",
                "is_published": self.is_published,
                "published_at": self.published_at.isoformat() if self.published_at else None}


class Notification(db.Model):
    __tablename__ = "notifications"
    notification_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=False)
    type = db.Column(db.String(50), nullable=False)
    message = db.Column(db.String(500), nullable=False)
    resource_id = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    read_at = db.Column(db.DateTime)
    dedupe_key = db.Column(db.String(100), unique=True)

    def to_dict(self):
        return {"notification_id": self.notification_id, "type": self.type,
                "message": self.message, "resource_id": self.resource_id,
                "created_at": self.created_at.isoformat(), "read_at": self.read_at.isoformat() if self.read_at else None}
