import os
from pathlib import Path

from auth import teacher_can_manage_subject
from config import Config
from database import get_session
from models import ConversationPdf


def _conversation_dir(subject_id: int) -> Path:
    folder = Config.DOCUMENTOS_DIR / str(subject_id) / "conversations"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def save_conversation_pdf(subject_id: int, filename: str, file_bytes: bytes) -> ConversationPdf:
    folder = _conversation_dir(subject_id)
    safe_name = Path(filename).name
    dest = folder / safe_name

    with open(dest, "wb") as handle:
        handle.write(file_bytes)

    session = get_session()
    try:
        record = ConversationPdf(
            subject_id=subject_id,
            filename=safe_name,
            storage_path=str(dest),
        )
        session.add(record)
        session.commit()
        session.refresh(record)
        return record
    finally:
        session.close()


def list_conversation_pdfs(subject_id: int) -> list[ConversationPdf]:
    session = get_session()
    try:
        return (
            session.query(ConversationPdf)
            .filter(ConversationPdf.subject_id == subject_id)
            .order_by(ConversationPdf.uploaded_at.desc())
            .all()
        )
    finally:
        session.close()


def get_conversation_pdf(pdf_id: int) -> ConversationPdf | None:
    session = get_session()
    try:
        return session.query(ConversationPdf).filter(ConversationPdf.id == pdf_id).first()
    finally:
        session.close()


def delete_conversation_pdf(pdf_id: int) -> bool:
    session = get_session()
    try:
        record = session.query(ConversationPdf).filter(ConversationPdf.id == pdf_id).first()
        if not record:
            return False

        if os.path.isfile(record.storage_path):
            os.remove(record.storage_path)

        session.delete(record)
        session.commit()
        return True
    finally:
        session.close()


def pdf_to_dict(record: ConversationPdf) -> dict:
    return {
        "id": record.id,
        "subject_id": record.subject_id,
        "filename": record.filename,
        "uploaded_at": record.uploaded_at.isoformat() if record.uploaded_at else None,
    }


def teacher_owns_subject(subject_id: int, teacher_id: int) -> bool:
    return teacher_can_manage_subject(subject_id, teacher_id)


def get_pdf_paths_for_subject(subject_id: int, pdf_ids: list[int] | None = None) -> list[str]:
    records = list_conversation_pdfs(subject_id)
    if pdf_ids:
        allowed = {pdf_id for pdf_id in pdf_ids}
        records = [record for record in records if record.id in allowed]
    return [record.storage_path for record in records if os.path.isfile(record.storage_path)]
