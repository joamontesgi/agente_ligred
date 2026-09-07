from datetime import datetime
import os
from pathlib import Path

from config import Config
from models import Enrollment, Lab, LabChatMessage, LabDocument, LabEvidence, LabSession, Subject, User
from database import get_session

ALLOWED_EVIDENCE_EXTENSIONS = {
    ".pdf", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".txt", ".zip", ".doc", ".docx",
}


def create_lab(subject_id: int, title: str, instructions: str, topic: str):
    session = get_session()
    try:
        lab = Lab(
            subject_id=subject_id,
            title=title.strip(),
            instructions=instructions.strip(),
            topic=topic.strip(),
        )
        session.add(lab)
        session.commit()
        session.refresh(lab)
        return lab
    finally:
        session.close()


def get_labs_by_subject(subject_id: int):
    session = get_session()
    try:
        return (
            session.query(Lab)
            .filter(Lab.subject_id == subject_id)
            .order_by(Lab.created_at.desc())
            .all()
        )
    finally:
        session.close()


def get_lab_by_id(lab_id: int):
    session = get_session()
    try:
        return session.query(Lab).filter(Lab.id == lab_id).first()
    finally:
        session.close()


def get_lab_documents(lab_id: int):
    session = get_session()
    try:
        return (
            session.query(LabDocument)
            .filter(LabDocument.lab_id == lab_id)
            .order_by(LabDocument.uploaded_at.desc())
            .all()
        )
    finally:
        session.close()


def add_lab_document_record(lab_id: int, filename: str, storage_path: str):
    session = get_session()
    try:
        doc = LabDocument(
            lab_id=lab_id,
            filename=filename,
            storage_path=storage_path,
        )
        session.add(doc)
        session.commit()
        session.refresh(doc)
        return doc
    finally:
        session.close()


def mark_lab_document_ingested(document_id: int):
    session = get_session()
    try:
        doc = session.query(LabDocument).filter(LabDocument.id == document_id).first()
        if doc:
            doc.ingested = 1
            session.commit()
    finally:
        session.close()


def get_lab_document_by_id(document_id: int):
    session = get_session()
    try:
        return session.query(LabDocument).filter(LabDocument.id == document_id).first()
    finally:
        session.close()


def delete_lab_document(document_id: int) -> tuple[bool, str | None, int]:
    from ingest import delete_lab_document_from_chroma

    session = get_session()
    try:
        doc = session.query(LabDocument).filter(LabDocument.id == document_id).first()
        if not doc:
            return False, "Documento no encontrado.", 0

        lab = session.query(Lab).filter(Lab.id == doc.lab_id).first()
        if not lab:
            return False, "Laboratorio no encontrado.", 0

        chunks_removed = delete_lab_document_from_chroma(
            doc.id,
            lab.subject_id,
            doc.lab_id,
        )

        if os.path.isfile(doc.storage_path):
            os.remove(doc.storage_path)

        session.delete(doc)
        session.commit()
        return True, None, chunks_removed
    finally:
        session.close()


def lab_document_to_dict(doc):
    return {
        "id": doc.id,
        "filename": doc.filename,
        "ingested": bool(doc.ingested),
        "uploaded_at": doc.uploaded_at.isoformat() if doc.uploaded_at else None,
    }


def get_available_labs_for_student(student_id: int):
    session = get_session()
    try:
        return (
            session.query(Lab, Subject)
            .join(Subject, Lab.subject_id == Subject.id)
            .join(Enrollment, Enrollment.subject_id == Subject.id)
            .filter(Enrollment.student_id == student_id)
            .order_by(Lab.created_at.desc())
            .all()
        )
    finally:
        session.close()


def get_student_session(lab_id: int, student_id: int, status: str | None = None):
    session = get_session()
    try:
        query = session.query(LabSession).filter(
            LabSession.lab_id == lab_id,
            LabSession.student_id == student_id,
        )
        if status:
            query = query.filter(LabSession.status == status)
        return query.order_by(LabSession.started_at.desc()).first()
    finally:
        session.close()


def create_lab_session(lab_id: int, student_id: int):
    session = get_session()
    try:
        lab_session = LabSession(
            lab_id=lab_id,
            student_id=student_id,
            status="in_progress",
        )
        session.add(lab_session)
        session.commit()
        session.refresh(lab_session)
        return lab_session
    finally:
        session.close()


def get_session_by_id(session_id: int):
    session = get_session()
    try:
        return session.query(LabSession).filter(LabSession.id == session_id).first()
    finally:
        session.close()


def complete_lab_session(session_id: int):
    session = get_session()
    try:
        lab_session = session.query(LabSession).filter(LabSession.id == session_id).first()
        if lab_session:
            lab_session.status = "completed"
            lab_session.completed_at = datetime.utcnow()
            session.commit()
            session.refresh(lab_session)
        return lab_session
    finally:
        session.close()


def add_chat_message(session_id: int, role: str, content: str):
    session = get_session()
    try:
        message = LabChatMessage(
            session_id=session_id,
            role=role,
            content=content,
        )
        session.add(message)
        session.commit()
        session.refresh(message)
        return message
    finally:
        session.close()


def get_session_messages(session_id: int):
    session = get_session()
    try:
        return (
            session.query(LabChatMessage)
            .filter(LabChatMessage.session_id == session_id)
            .order_by(LabChatMessage.created_at)
            .all()
        )
    finally:
        session.close()


def get_lab_sessions_for_teacher(lab_id: int):
    session = get_session()
    try:
        rows = (
            session.query(LabSession, User)
            .join(User, LabSession.student_id == User.id)
            .filter(LabSession.lab_id == lab_id)
            .order_by(LabSession.started_at.desc())
            .all()
        )
        result = []
        for lab_session, student in rows:
            msg_count = (
                session.query(LabChatMessage)
                .filter(LabChatMessage.session_id == lab_session.id)
                .count()
            )
            evidence_count = (
                session.query(LabEvidence)
                .filter(LabEvidence.session_id == lab_session.id)
                .count()
            )
            result.append({
                "session": lab_session,
                "student": student,
                "message_count": msg_count,
                "evidence_count": evidence_count,
            })
        return result
    finally:
        session.close()


def lab_to_dict(lab, subject_name=None, include_doc_counts=False):
    data = {
        "id": lab.id,
        "subject_id": lab.subject_id,
        "title": lab.title,
        "instructions": lab.instructions,
        "topic": lab.topic,
        "created_at": lab.created_at.isoformat() if lab.created_at else None,
    }
    if subject_name:
        data["subject_name"] = subject_name
    if include_doc_counts:
        docs = get_lab_documents(lab.id)
        ingested = sum(1 for d in docs if d.ingested)
        data["document_count"] = len(docs)
        data["ingested_count"] = ingested
    return data


def session_to_dict(lab_session, include_lab=False, lab=None):
    data = {
        "id": lab_session.id,
        "lab_id": lab_session.lab_id,
        "student_id": lab_session.student_id,
        "status": lab_session.status,
        "started_at": lab_session.started_at.isoformat() if lab_session.started_at else None,
        "completed_at": lab_session.completed_at.isoformat() if lab_session.completed_at else None,
    }
    if include_lab and lab:
        data["lab"] = lab_to_dict(lab)
    return data


def message_to_dict(message):
    return {
        "id": message.id,
        "role": message.role,
        "content": message.content,
        "created_at": message.created_at.isoformat() if message.created_at else None,
    }


def get_session_full(session_id: int):
    session = get_session()
    try:
        lab_session = session.query(LabSession).filter(
            LabSession.id == session_id
        ).first()
        if not lab_session:
            return None

        lab = session.query(Lab).filter(Lab.id == lab_session.lab_id).first()
        subject = (
            session.query(Subject).filter(Subject.id == lab.subject_id).first()
            if lab
            else None
        )
        student = session.query(User).filter(User.id == lab_session.student_id).first()
        messages = (
            session.query(LabChatMessage)
            .filter(LabChatMessage.session_id == session_id)
            .order_by(LabChatMessage.created_at)
            .all()
        )

        return {
            "session": lab_session,
            "lab": lab,
            "subject": subject,
            "student": student,
            "messages": messages,
        }
    finally:
        session.close()


def save_lab_evidence_file(
    subject_id: int,
    lab_id: int,
    session_id: int,
    filename: str,
    file_bytes: bytes,
) -> str:
    folder = (
        Config.DOCUMENTOS_DIR
        / str(subject_id)
        / "labs"
        / str(lab_id)
        / "evidence"
        / str(session_id)
    )
    folder.mkdir(parents=True, exist_ok=True)

    safe_name = Path(filename).name
    dest = folder / safe_name

    with open(dest, "wb") as f:
        f.write(file_bytes)

    return str(dest)


def add_evidence_record(session_id: int, filename: str, storage_path: str, note: str = ""):
    session = get_session()
    try:
        evidence = LabEvidence(
            session_id=session_id,
            filename=filename,
            storage_path=storage_path,
            note=note.strip(),
        )
        session.add(evidence)
        session.commit()
        session.refresh(evidence)
        return evidence
    finally:
        session.close()


def get_session_evidence(session_id: int):
    session = get_session()
    try:
        return (
            session.query(LabEvidence)
            .filter(LabEvidence.session_id == session_id)
            .order_by(LabEvidence.uploaded_at.desc())
            .all()
        )
    finally:
        session.close()


def get_evidence_by_id(evidence_id: int):
    session = get_session()
    try:
        return session.query(LabEvidence).filter(LabEvidence.id == evidence_id).first()
    finally:
        session.close()


def evidence_to_dict(evidence):
    return {
        "id": evidence.id,
        "filename": evidence.filename,
        "note": evidence.note or "",
        "uploaded_at": evidence.uploaded_at.isoformat() if evidence.uploaded_at else None,
    }


def is_allowed_evidence(filename: str) -> bool:
    return Path(filename).suffix.lower() in ALLOWED_EVIDENCE_EXTENSIONS
