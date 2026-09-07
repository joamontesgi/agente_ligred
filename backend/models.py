from datetime import datetime
from enum import Enum

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class UserRole(str, Enum):
    TEACHER = "teacher"
    STUDENT = "student"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    nombre = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False)
    security_question = Column(String(255), nullable=True)
    security_answer_hash = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    subjects_taught = relationship(
        "Subject",
        back_populates="teacher",
        foreign_keys="Subject.teacher_id",
    )
    subject_assignments = relationship("SubjectTeacher", back_populates="teacher")
    enrollments = relationship("Enrollment", back_populates="student")


class Subject(Base):
    __tablename__ = "subjects"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, default="")
    teacher_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    llm_model = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    teacher = relationship(
        "User",
        back_populates="subjects_taught",
        foreign_keys=[teacher_id],
    )
    documents = relationship(
        "Document",
        back_populates="subject",
        cascade="all, delete-orphan",
    )
    enrollments = relationship(
        "Enrollment",
        back_populates="subject",
        cascade="all, delete-orphan",
    )
    evaluations = relationship(
        "Evaluation",
        back_populates="subject",
        cascade="all, delete-orphan",
    )
    labs = relationship(
        "Lab",
        back_populates="subject",
        cascade="all, delete-orphan",
    )
    conversation_pdfs = relationship(
        "ConversationPdf",
        back_populates="subject",
        cascade="all, delete-orphan",
    )
    teacher_links = relationship(
        "SubjectTeacher",
        back_populates="subject",
        cascade="all, delete-orphan",
    )


class SubjectTeacher(Base):
    __tablename__ = "subject_teachers"
    __table_args__ = (
        UniqueConstraint("subject_id", "teacher_id", name="uq_subject_teacher"),
    )

    id = Column(Integer, primary_key=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    teacher_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_primary = Column(Integer, default=0)
    assigned_at = Column(DateTime, default=datetime.utcnow)

    subject = relationship("Subject", back_populates="teacher_links")
    teacher = relationship("User", back_populates="subject_assignments")


class Enrollment(Base):
    __tablename__ = "enrollments"
    __table_args__ = (
        UniqueConstraint("student_id", "subject_id", name="uq_enrollment"),
    )

    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    enrolled_at = Column(DateTime, default=datetime.utcnow)

    student = relationship("User", back_populates="enrollments")
    subject = relationship("Subject", back_populates="enrollments")


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    filename = Column(String(255), nullable=False)
    storage_path = Column(String(512), nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    ingested = Column(Integer, default=0)

    subject = relationship("Subject", back_populates="documents")


class Evaluation(Base):
    __tablename__ = "evaluations"

    id = Column(Integer, primary_key=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    title = Column(String(255), nullable=False)
    topic = Column(String(255), nullable=False)
    num_questions = Column(Integer, nullable=False, default=5)
    created_at = Column(DateTime, default=datetime.utcnow)

    subject = relationship("Subject", back_populates="evaluations")
    attempts = relationship(
        "EvaluationAttempt",
        back_populates="evaluation",
        cascade="all, delete-orphan",
    )


class EvaluationAttempt(Base):
    __tablename__ = "evaluation_attempts"

    id = Column(Integer, primary_key=True)
    evaluation_id = Column(Integer, ForeignKey("evaluations.id"), nullable=False)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(String(20), nullable=False, default="in_progress")
    score = Column(Float, nullable=True)
    correct_count = Column(Integer, nullable=True)
    total_questions = Column(Integer, nullable=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    evaluation = relationship("Evaluation", back_populates="attempts")
    answers = relationship(
        "EvaluationAnswer",
        back_populates="attempt",
        cascade="all, delete-orphan",
    )


class EvaluationAnswer(Base):
    __tablename__ = "evaluation_answers"

    id = Column(Integer, primary_key=True)
    attempt_id = Column(Integer, ForeignKey("evaluation_attempts.id"), nullable=False)
    question_number = Column(Integer, nullable=False)
    pregunta = Column(Text, nullable=False)
    contexto = Column(Text, nullable=False)
    respuesta_estudiante = Column(Text, default="")
    evaluacion = Column(Text, default="")
    correcta = Column(Integer, default=0)
    fuente = Column(String(255), default="")

    attempt = relationship("EvaluationAttempt", back_populates="answers")


class Lab(Base):
    __tablename__ = "labs"

    id = Column(Integer, primary_key=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    title = Column(String(255), nullable=False)
    instructions = Column(Text, nullable=False)
    topic = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    subject = relationship("Subject", back_populates="labs")
    documents = relationship(
        "LabDocument",
        back_populates="lab",
        cascade="all, delete-orphan",
    )
    sessions = relationship(
        "LabSession",
        back_populates="lab",
        cascade="all, delete-orphan",
    )


class LabSession(Base):
    __tablename__ = "lab_sessions"

    id = Column(Integer, primary_key=True)
    lab_id = Column(Integer, ForeignKey("labs.id"), nullable=False)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(String(20), nullable=False, default="in_progress")
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    lab = relationship("Lab", back_populates="sessions")
    messages = relationship(
        "LabChatMessage",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="LabChatMessage.created_at",
    )
    evidence = relationship(
        "LabEvidence",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="LabEvidence.uploaded_at",
    )


class LabChatMessage(Base):
    __tablename__ = "lab_chat_messages"

    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey("lab_sessions.id"), nullable=False)
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("LabSession", back_populates="messages")


class LabDocument(Base):
    __tablename__ = "lab_documents"

    id = Column(Integer, primary_key=True)
    lab_id = Column(Integer, ForeignKey("labs.id"), nullable=False)
    filename = Column(String(255), nullable=False)
    storage_path = Column(String(512), nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    ingested = Column(Integer, default=0)

    lab = relationship("Lab", back_populates="documents")


class LabEvidence(Base):
    __tablename__ = "lab_evidence"

    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey("lab_sessions.id"), nullable=False)
    filename = Column(String(255), nullable=False)
    storage_path = Column(String(512), nullable=False)
    note = Column(Text, default="")
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("LabSession", back_populates="evidence")


class ConversationPdf(Base):
    __tablename__ = "conversation_pdfs"

    id = Column(Integer, primary_key=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    filename = Column(String(255), nullable=False)
    storage_path = Column(String(512), nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    subject = relationship("Subject", back_populates="conversation_pdfs")
