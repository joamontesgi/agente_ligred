import bcrypt
import os
import shutil

from config import Config
from database import get_session
from models import Document, Enrollment, Subject, SubjectTeacher, User, UserRole


def hash_password(password: str) -> str:
    return bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt(),
    ).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(
        password.encode("utf-8"),
        password_hash.encode("utf-8"),
    )


def normalize_security_answer(answer: str) -> str:
    return " ".join((answer or "").strip().lower().split())


def hash_security_answer(answer: str) -> str:
    return hash_password(normalize_security_answer(answer))


def verify_security_answer(answer: str, answer_hash: str) -> bool:
    if not answer_hash:
        return False
    return verify_password(normalize_security_answer(answer), answer_hash)


def register_user(
    email: str,
    password: str,
    nombre: str,
    role: str,
    security_question: str = "",
    security_answer: str = "",
):
    session = get_session()
    try:
        existing = session.query(User).filter(User.email == email).first()
        if existing:
            return None, "Ya existe una cuenta con ese correo."

        if role not in (UserRole.TEACHER.value, UserRole.STUDENT.value):
            return None, "Rol no válido."

        from security_questions import SECURITY_QUESTIONS

        question = (security_question or "").strip()
        answer = (security_answer or "").strip()
        if not question or not answer:
            return None, "La pregunta y respuesta de seguridad son obligatorias."
        if question not in SECURITY_QUESTIONS:
            return None, "Pregunta de seguridad no válida."
        if len(answer) < 2:
            return None, "La respuesta de seguridad es demasiado corta."

        user = User(
            email=email.strip().lower(),
            password_hash=hash_password(password),
            nombre=nombre.strip(),
            role=role,
            security_question=question,
            security_answer_hash=hash_security_answer(answer),
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        return user_to_dict(user), None
    finally:
        session.close()


def login_user(email: str, password: str):
    session = get_session()
    try:
        user = (
            session.query(User)
            .filter(User.email == email.strip().lower())
            .first()
        )
        if not user or not verify_password(password, user.password_hash):
            return None, "Correo o contraseña incorrectos."
        return user_to_dict(user), None
    finally:
        session.close()


def user_to_dict(user: User) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "nombre": user.nombre,
        "role": user.role,
    }


def get_user_by_email(email: str):
    session = get_session()
    try:
        return (
            session.query(User)
            .filter(User.email == email.strip().lower())
            .first()
        )
    finally:
        session.close()


def get_security_question_for_email(email: str):
    user = get_user_by_email(email)
    if not user:
        return None, "No encontramos una cuenta con ese correo."
    if not user.security_question:
        return None, (
            "Esta cuenta no tiene pregunta de seguridad. "
            "Regístrate de nuevo o contacta al administrador."
        )
    return user.security_question, None


def reset_password_with_security_answer(
    email: str,
    security_answer: str,
    new_password: str,
):
    if len(new_password) < 6:
        return False, "La nueva contraseña debe tener al menos 6 caracteres."

    answer = (security_answer or "").strip()
    if not answer:
        return False, "Debes responder la pregunta de seguridad."

    session = get_session()
    try:
        user = (
            session.query(User)
            .filter(User.email == email.strip().lower())
            .first()
        )
        if not user:
            return False, "No encontramos una cuenta con ese correo."
        if not user.security_answer_hash:
            return False, "Esta cuenta no tiene pregunta de seguridad configurada."
        if not verify_security_answer(answer, user.security_answer_hash):
            return False, "La respuesta de seguridad es incorrecta."

        user.password_hash = hash_password(new_password)
        session.commit()
        return True, None
    finally:
        session.close()


def create_subject(
    teacher_id: int,
    name: str,
    description: str = "",
    llm_model: str | None = None,
):
    session = get_session()
    try:
        subject = Subject(
            name=name.strip(),
            description=description.strip(),
            teacher_id=teacher_id,
            llm_model=(llm_model or "").strip() or None,
        )
        session.add(subject)
        session.flush()
        session.add(
            SubjectTeacher(
                subject_id=subject.id,
                teacher_id=teacher_id,
                is_primary=1,
            )
        )
        session.commit()
        session.refresh(subject)
        return subject
    finally:
        session.close()


def teacher_can_manage_subject(subject_id: int, teacher_id: int) -> bool:
    session = get_session()
    try:
        return (
            session.query(SubjectTeacher)
            .filter(
                SubjectTeacher.subject_id == subject_id,
                SubjectTeacher.teacher_id == teacher_id,
            )
            .first()
            is not None
        )
    finally:
        session.close()


def get_subject_teachers(subject_id: int) -> list[dict]:
    session = get_session()
    try:
        rows = (
            session.query(SubjectTeacher, User)
            .join(User, SubjectTeacher.teacher_id == User.id)
            .filter(SubjectTeacher.subject_id == subject_id)
            .order_by(SubjectTeacher.is_primary.desc(), User.nombre)
            .all()
        )
        return [
            {
                "id": user.id,
                "nombre": user.nombre,
                "email": user.email,
                "is_primary": bool(link.is_primary),
            }
            for link, user in rows
        ]
    finally:
        session.close()


def add_subject_teacher(
    subject_id: int,
    requester_id: int,
    teacher_email: str,
):
    email = (teacher_email or "").strip().lower()
    if not email:
        return None, "Ingresa el correo del docente."

    session = get_session()
    try:
        if not teacher_can_manage_subject(subject_id, requester_id):
            return None, "No autorizado para gestionar docentes de esta asignatura."

        teacher = session.query(User).filter(User.email == email).first()
        if not teacher:
            return None, "No existe un usuario con ese correo."
        if teacher.role != UserRole.TEACHER.value:
            return None, "El usuario indicado no es docente."

        existing = (
            session.query(SubjectTeacher)
            .filter(
                SubjectTeacher.subject_id == subject_id,
                SubjectTeacher.teacher_id == teacher.id,
            )
            .first()
        )
        if existing:
            return None, "Ese docente ya está asignado a la asignatura."

        link = SubjectTeacher(
            subject_id=subject_id,
            teacher_id=teacher.id,
            is_primary=0,
        )
        session.add(link)
        session.commit()
        return get_subject_teachers(subject_id), None
    finally:
        session.close()


def remove_subject_teacher(
    subject_id: int,
    requester_id: int,
    teacher_id: int,
):
    session = get_session()
    try:
        if not teacher_can_manage_subject(subject_id, requester_id):
            return None, "No autorizado para gestionar docentes de esta asignatura."

        link = (
            session.query(SubjectTeacher)
            .filter(
                SubjectTeacher.subject_id == subject_id,
                SubjectTeacher.teacher_id == teacher_id,
            )
            .first()
        )
        if not link:
            return None, "Ese docente no está asignado a la asignatura."
        if link.is_primary:
            return None, "No se puede quitar al docente principal."

        session.delete(link)
        session.commit()
        return get_subject_teachers(subject_id), None
    finally:
        session.close()


def update_subject(subject_id: int, teacher_id: int, **fields):
    session = get_session()
    try:
        subject = session.query(Subject).filter(Subject.id == subject_id).first()
        if not subject or not teacher_can_manage_subject(subject_id, teacher_id):
            return None, "Asignatura no encontrada o no autorizada."

        if "name" in fields:
            name = (fields["name"] or "").strip()
            if not name:
                return None, "El nombre no puede estar vacío."
            subject.name = name
        if "description" in fields:
            subject.description = (fields["description"] or "").strip()
        if "llm_model" in fields:
            subject.llm_model = (fields["llm_model"] or "").strip() or None

        session.commit()
        session.refresh(subject)
        return subject, None
    finally:
        session.close()


def get_teacher_subjects(teacher_id: int):
    session = get_session()
    try:
        return (
            session.query(Subject)
            .join(SubjectTeacher, SubjectTeacher.subject_id == Subject.id)
            .filter(SubjectTeacher.teacher_id == teacher_id)
            .order_by(Subject.name)
            .distinct()
            .all()
        )
    finally:
        session.close()


def get_all_subjects():
    session = get_session()
    try:
        return session.query(Subject).order_by(Subject.name).all()
    finally:
        session.close()


def get_student_enrollments(student_id: int):
    session = get_session()
    try:
        rows = (
            session.query(Enrollment, Subject)
            .join(Subject)
            .filter(Enrollment.student_id == student_id)
            .order_by(Subject.name)
            .all()
        )
        return [
            {"subject_id": subject.id, "subject_name": subject.name}
            for _, subject in rows
        ]
    finally:
        session.close()


def is_student_enrolled(student_id: int, subject_id: int) -> bool:
    enrollments = get_student_enrollments(student_id)
    return any(e["subject_id"] == subject_id for e in enrollments)


def enroll_student(student_id: int, subject_id: int):
    session = get_session()
    try:
        existing = (
            session.query(Enrollment)
            .filter(
                Enrollment.student_id == student_id,
                Enrollment.subject_id == subject_id,
            )
            .first()
        )
        if existing:
            return False, "Ya estás inscrito en esta asignatura."

        subject = session.query(Subject).filter(Subject.id == subject_id).first()
        if not subject:
            return False, "Asignatura no encontrada."

        enrollment = Enrollment(
            student_id=student_id,
            subject_id=subject_id,
        )
        session.add(enrollment)
        session.commit()
        return True, "Inscripción exitosa."
    finally:
        session.close()


def get_subject_documents(subject_id: int):
    session = get_session()
    try:
        return (
            session.query(Document)
            .filter(Document.subject_id == subject_id)
            .order_by(Document.uploaded_at.desc())
            .all()
        )
    finally:
        session.close()


def count_ingested_subject_documents(subject_id: int) -> int:
    session = get_session()
    try:
        docs = session.query(Document).filter(Document.subject_id == subject_id).all()
        return sum(1 for doc in docs if doc.ingested)
    finally:
        session.close()


def get_subject_document_stats(subject_id: int) -> dict:
    session = get_session()
    try:
        docs = session.query(Document).filter(Document.subject_id == subject_id).all()
        ingested = sum(1 for doc in docs if doc.ingested)
        return {
            "document_count": len(docs),
            "ingested_count": ingested,
        }
    finally:
        session.close()


def subject_has_ingested_documents(subject_id: int) -> bool:
    stats = get_subject_document_stats(subject_id)
    if stats["ingested_count"] > 0:
        return True

    if stats["document_count"] > 0:
        from rag import ProfesorRAG

        return ProfesorRAG.for_subject(subject_id).subject_has_course_documents(
            subject_id
        )

    return False


def add_document_record(subject_id: int, filename: str, storage_path: str):
    session = get_session()
    try:
        doc = Document(
            subject_id=subject_id,
            filename=filename,
            storage_path=storage_path,
        )
        session.add(doc)
        session.commit()
        session.refresh(doc)
        return doc
    finally:
        session.close()


def mark_document_ingested(document_id: int):
    session = get_session()
    try:
        doc = session.query(Document).filter(Document.id == document_id).first()
        if doc:
            doc.ingested = 1
            session.commit()
    finally:
        session.close()


def get_document_by_id(document_id: int):
    session = get_session()
    try:
        return session.query(Document).filter(Document.id == document_id).first()
    finally:
        session.close()


def delete_subject_document(document_id: int) -> tuple[bool, str | None, int]:
    from ingest import delete_subject_document_from_chroma

    session = get_session()
    try:
        doc = session.query(Document).filter(Document.id == document_id).first()
        if not doc:
            return False, "Documento no encontrado.", 0

        chunks_removed = delete_subject_document_from_chroma(doc.id, doc.subject_id)

        if os.path.isfile(doc.storage_path):
            os.remove(doc.storage_path)

        session.delete(doc)
        session.commit()
        return True, None, chunks_removed
    finally:
        session.close()


def get_subject_by_id(subject_id: int):
    session = get_session()
    try:
        return session.query(Subject).filter(Subject.id == subject_id).first()
    finally:
        session.close()


def get_teacher_name(teacher_id: int) -> str:
    session = get_session()
    try:
        user = session.query(User).filter(User.id == teacher_id).first()
        return user.nombre if user else "Desconocido"
    finally:
        session.close()


def is_subject_creator(subject_id: int, teacher_id: int) -> bool:
    session = get_session()
    try:
        subject = session.query(Subject).filter(Subject.id == subject_id).first()
        return bool(subject and subject.teacher_id == teacher_id)
    finally:
        session.close()


def delete_subject(subject_id: int, teacher_id: int):
    from ingest import delete_all_subject_chunks_from_chroma

    session = get_session()
    try:
        subject = session.query(Subject).filter(Subject.id == subject_id).first()
        if not subject:
            return False, "Asignatura no encontrada.", 0
        if subject.teacher_id != teacher_id:
            return False, "Solo el docente que creó la asignatura puede eliminarla.", 0

        chunks_removed = delete_all_subject_chunks_from_chroma(subject_id)

        subject_folder = Config.DOCUMENTOS_DIR / str(subject_id)
        if subject_folder.exists():
            shutil.rmtree(subject_folder)

        session.delete(subject)
        session.commit()
        return True, None, chunks_removed
    finally:
        session.close()
