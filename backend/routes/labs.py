from flask import Blueprint, Response, jsonify, request

from auth import get_subject_by_id, is_student_enrolled, teacher_can_manage_subject
from jwt_utils import role_required, token_required
from ingest import ingest_lab_pdf, save_uploaded_lab_pdf
from labs import (
    add_chat_message,
    add_evidence_record,
    add_lab_document_record,
    complete_lab_session,
    create_lab,
    create_lab_session,
    delete_lab_document,
    evidence_to_dict,
    get_available_labs_for_student,
    get_evidence_by_id,
    get_lab_by_id,
    get_lab_document_by_id,
    get_lab_documents,
    get_lab_sessions_for_teacher,
    get_labs_by_subject,
    get_session_by_id,
    get_session_evidence,
    get_session_full,
    get_session_messages,
    get_student_session,
    is_allowed_evidence,
    lab_document_to_dict,
    lab_to_dict,
    mark_lab_document_ingested,
    message_to_dict,
    save_lab_evidence_file,
    session_to_dict,
)
from pdf_export import generate_lab_chat_pdf
from rag import ProfesorRAG
from routes.llm_errors import llm_error_response

labs_bp = Blueprint("labs", __name__)


def get_rag(subject_id: int):
    return ProfesorRAG.for_subject(subject_id)


def _teacher_owns_lab(lab, teacher_id):
    return lab and teacher_can_manage_subject(lab.subject_id, teacher_id)


def _can_access_session(lab_session, user):
    lab = get_lab_by_id(lab_session.lab_id)
    if user["role"] == "student":
        return lab_session.student_id == user["sub"]
    if user["role"] == "teacher":
        return lab and _teacher_owns_lab(lab, user["sub"])
    return False


@labs_bp.post("/")
@role_required("teacher")
def create_lab_route():
    data = request.get_json(silent=True) or {}

    subject_id = data.get("subject_id")
    title = (data.get("title") or "").strip()
    instructions = (data.get("instructions") or "").strip()
    topic = (data.get("topic") or "").strip()

    if not all([subject_id, title, instructions, topic]):
        return jsonify({"error": "Completa título, instrucciones, tema y asignatura."}), 400

    subject = get_subject_by_id(subject_id)
    if not subject or not teacher_can_manage_subject(subject_id, request.current_user["sub"]):
        return jsonify({"error": "Asignatura no encontrada o no autorizada."}), 403

    lab = create_lab(subject_id, title, instructions, topic)
    return jsonify({"lab": lab_to_dict(lab)}), 201


@labs_bp.get("/")
@role_required("teacher")
def list_labs():
    subject_id = request.args.get("subject_id", type=int)
    if not subject_id:
        return jsonify({"error": "subject_id es obligatorio."}), 400

    subject = get_subject_by_id(subject_id)
    if not subject or not teacher_can_manage_subject(subject_id, request.current_user["sub"]):
        return jsonify({"error": "No autorizado."}), 403

    labs = get_labs_by_subject(subject_id)
    return jsonify({
        "labs": [lab_to_dict(lab, include_doc_counts=True) for lab in labs],
    })


@labs_bp.get("/available")
@role_required("student")
def list_available_labs():
    student_id = request.current_user["sub"]
    rows = get_available_labs_for_student(student_id)

    result = []
    for lab, subject in rows:
        item = lab_to_dict(lab, subject_name=subject.name)
        active = get_student_session(lab.id, student_id, status="in_progress")
        completed = get_student_session(lab.id, student_id, status="completed")
        item["in_progress"] = active is not None
        item["completed"] = completed is not None
        if active:
            item["session_id"] = active.id
        elif completed:
            item["session_id"] = completed.id
        result.append(item)

    return jsonify({"labs": result})


@labs_bp.get("/<int:lab_id>/sessions")
@role_required("teacher")
def list_lab_sessions(lab_id):
    lab = get_lab_by_id(lab_id)
    if not lab:
        return jsonify({"error": "Laboratorio no encontrado."}), 404

    if not _teacher_owns_lab(lab, request.current_user["sub"]):
        return jsonify({"error": "No autorizado."}), 403

    sessions = get_lab_sessions_for_teacher(lab_id)
    result = []
    for item in sessions:
        lab_session = item["session"]
        student = item["student"]
        result.append({
            "session_id": lab_session.id,
            "student_id": student.id,
            "student_name": student.nombre,
            "status": lab_session.status,
            "message_count": item["message_count"],
            "evidence_count": item["evidence_count"],
            "started_at": lab_session.started_at.isoformat() if lab_session.started_at else None,
            "completed_at": lab_session.completed_at.isoformat() if lab_session.completed_at else None,
        })

    return jsonify({"lab": lab_to_dict(lab), "sessions": result})


@labs_bp.get("/<int:lab_id>/documents")
@role_required("teacher")
def list_lab_documents(lab_id):
    lab = get_lab_by_id(lab_id)
    if not lab:
        return jsonify({"error": "Laboratorio no encontrado."}), 404

    if not _teacher_owns_lab(lab, request.current_user["sub"]):
        return jsonify({"error": "No autorizado."}), 403

    documents = get_lab_documents(lab_id)
    return jsonify({"documents": [lab_document_to_dict(d) for d in documents]})


@labs_bp.post("/<int:lab_id>/documents")
@role_required("teacher")
def upload_lab_documents(lab_id):
    lab = get_lab_by_id(lab_id)
    if not lab:
        return jsonify({"error": "Laboratorio no encontrado."}), 404

    if not _teacher_owns_lab(lab, request.current_user["sub"]):
        return jsonify({"error": "No autorizado."}), 403

    files = request.files.getlist("files")
    if not files:
        return jsonify({"error": "No se enviaron archivos."}), 400

    results = []
    for file in files:
        if not file.filename or not file.filename.lower().endswith(".pdf"):
            results.append({
                "filename": file.filename or "desconocido",
                "ok": False,
                "message": "Solo se permiten archivos PDF.",
            })
            continue

        file_bytes = file.read()
        storage_path = save_uploaded_lab_pdf(
            lab.subject_id,
            lab_id,
            file.filename,
            file_bytes,
        )
        doc_record = add_lab_document_record(lab_id, file.filename, storage_path)

        chunks = ingest_lab_pdf(
            storage_path,
            lab.subject_id,
            lab_id,
            doc_record.id,
            file.filename,
        )

        if chunks > 0:
            mark_lab_document_ingested(doc_record.id)
            results.append({
                "filename": file.filename,
                "ok": True,
                "chunks": chunks,
                "message": f"{chunks} fragmentos indexados.",
            })
        else:
            results.append({
                "filename": file.filename,
                "ok": False,
                "message": "No se extrajo contenido del PDF.",
            })

    return jsonify({"results": results})


@labs_bp.delete("/documents/<int:document_id>")
@role_required("teacher")
def delete_lab_document_route(document_id):
    doc = get_lab_document_by_id(document_id)
    if not doc:
        return jsonify({"error": "Documento no encontrado."}), 404

    lab = get_lab_by_id(doc.lab_id)
    if not lab or not _teacher_owns_lab(lab, request.current_user["sub"]):
        return jsonify({"error": "No autorizado."}), 403

    ok, error, chunks_removed = delete_lab_document(document_id)
    if not ok:
        return jsonify({"error": error}), 404

    return jsonify({
        "ok": True,
        "message": "Documento del laboratorio eliminado de la base de conocimiento.",
        "chunks_removed": chunks_removed,
    })


@labs_bp.post("/<int:lab_id>/start")
@role_required("student")
def start_lab(lab_id):
    student_id = request.current_user["sub"]
    lab = get_lab_by_id(lab_id)

    if not lab:
        return jsonify({"error": "Laboratorio no encontrado."}), 404

    if not is_student_enrolled(student_id, lab.subject_id):
        return jsonify({"error": "No estás inscrito en esta asignatura."}), 403

    existing = get_student_session(lab_id, student_id, status="in_progress")
    if existing:
        messages = get_session_messages(existing.id)
        return jsonify({
            "session": session_to_dict(existing, include_lab=True, lab=lab),
            "messages": [message_to_dict(m) for m in messages],
            "read_only": False,
        })

    completed = get_student_session(lab_id, student_id, status="completed")
    if completed:
        messages = get_session_messages(completed.id)
        return jsonify({
            "session": session_to_dict(completed, include_lab=True, lab=lab),
            "messages": [message_to_dict(m) for m in messages],
            "read_only": True,
        })

    lab_session = create_lab_session(lab_id, student_id)

    welcome = (
        f"¡Bienvenido al laboratorio «{lab.title}»!\n\n"
        "Sigue las instrucciones del panel izquierdo. "
        "Si tienes dudas sobre algún paso, escríbeme aquí."
    )
    add_chat_message(lab_session.id, "assistant", welcome)

    messages = get_session_messages(lab_session.id)

    return jsonify({
        "session": session_to_dict(lab_session, include_lab=True, lab=lab),
        "messages": [message_to_dict(m) for m in messages],
        "read_only": False,
    })


@labs_bp.get("/sessions/<int:session_id>")
@token_required
def get_session_detail(session_id):
    lab_session = get_session_by_id(session_id)
    if not lab_session:
        return jsonify({"error": "Sesión no encontrada."}), 404

    lab = get_lab_by_id(lab_session.lab_id)
    user = request.current_user

    if user["role"] == "student":
        if lab_session.student_id != user["sub"]:
            return jsonify({"error": "No autorizado."}), 403
    elif user["role"] == "teacher":
        if not lab or not _teacher_owns_lab(lab, user["sub"]):
            return jsonify({"error": "No autorizado."}), 403
    else:
        return jsonify({"error": "No autorizado."}), 403

    messages = get_session_messages(session_id)

    from database import get_session
    from models import User

    db = get_session()
    try:
        student = db.query(User).filter(User.id == lab_session.student_id).first()
        student_name = student.nombre if student else "Desconocido"
    finally:
        db.close()

    return jsonify({
        "session": session_to_dict(lab_session, include_lab=True, lab=lab),
        "student_name": student_name,
        "messages": [message_to_dict(m) for m in messages],
        "evidence": [evidence_to_dict(e) for e in get_session_evidence(session_id)],
    })


@labs_bp.post("/sessions/<int:session_id>/chat")
@role_required("student")
def chat_in_lab(session_id):
    student_id = request.current_user["sub"]
    lab_session = get_session_by_id(session_id)

    if not lab_session:
        return jsonify({"error": "Sesión no encontrada."}), 404

    if lab_session.student_id != student_id:
        return jsonify({"error": "No autorizado."}), 403

    if lab_session.status != "in_progress":
        return jsonify({"error": "Este laboratorio ya fue finalizado."}), 400

    data = request.get_json(silent=True) or {}
    user_message = (data.get("message") or "").strip()

    if not user_message:
        return jsonify({"error": "El mensaje no puede estar vacío."}), 400

    lab = get_lab_by_id(lab_session.lab_id)
    if not lab:
        return jsonify({"error": "Laboratorio no encontrado."}), 404

    history = [
        message_to_dict(m)
        for m in get_session_messages(session_id)
        if m.role in ("user", "assistant")
    ]

    add_chat_message(session_id, "user", user_message)

    try:
        result = get_rag(lab.subject_id).responder_laboratorio(
            lab.subject_id,
            lab.instructions,
            lab.topic,
            history,
            user_message,
            lab_id=lab.id,
        )
    except RuntimeError as exc:
        return llm_error_response(exc)
    except Exception as exc:
        return jsonify({
            "error": (
                "No se pudo obtener respuesta del asistente. "
                "Verifica que Ollama esté en ejecución."
            ),
            "detail": str(exc),
        }), 503

    add_chat_message(session_id, "assistant", result["respuesta"])

    return jsonify({
        "message": message_to_dict(
            get_session_messages(session_id)[-1]
        ),
        "fuentes": result.get("fuentes", []),
    })


@labs_bp.post("/sessions/<int:session_id>/complete")
@role_required("student")
def complete_lab(session_id):
    student_id = request.current_user["sub"]
    lab_session = get_session_by_id(session_id)

    if not lab_session:
        return jsonify({"error": "Sesión no encontrada."}), 404

    if lab_session.student_id != student_id:
        return jsonify({"error": "No autorizado."}), 403

    if lab_session.status == "completed":
        return jsonify({"error": "Este laboratorio ya fue finalizado."}), 400

    updated = complete_lab_session(session_id)
    farewell = (
        "Has marcado el laboratorio como completado. "
        "¡Buen trabajo! Si necesitas revisar algo, tu docente podrá ver este chat."
    )
    add_chat_message(session_id, "assistant", farewell)

    return jsonify({"session": session_to_dict(updated)})


@labs_bp.get("/sessions/<int:session_id>/pdf")
@token_required
def export_lab_chat_pdf(session_id):
    lab_session = get_session_by_id(session_id)
    if not lab_session:
        return jsonify({"error": "Sesión no encontrada."}), 404

    lab = get_lab_by_id(lab_session.lab_id)
    user = request.current_user

    if user["role"] == "student":
        if lab_session.student_id != user["sub"]:
            return jsonify({"error": "No autorizado."}), 403
    elif user["role"] == "teacher":
        if not lab or not _teacher_owns_lab(lab, user["sub"]):
            return jsonify({"error": "No autorizado."}), 403
    else:
        return jsonify({"error": "No autorizado."}), 403

    data = get_session_full(session_id)
    if not data:
        return jsonify({"error": "Sesión no encontrada."}), 404

    pdf_bytes = generate_lab_chat_pdf(data)
    lab_title = data["lab"].title if data["lab"] else "laboratorio"
    safe_title = "".join(c if c.isalnum() or c in " -_" else "" for c in lab_title)[:40]
    filename = f"lab_{session_id}_{safe_title.strip()}.pdf"

    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@labs_bp.get("/sessions/<int:session_id>/evidence")
@token_required
def list_session_evidence(session_id):
    lab_session = get_session_by_id(session_id)
    if not lab_session:
        return jsonify({"error": "Sesión no encontrada."}), 404

    if not _can_access_session(lab_session, request.current_user):
        return jsonify({"error": "No autorizado."}), 403

    evidence = get_session_evidence(session_id)
    return jsonify({"evidence": [evidence_to_dict(e) for e in evidence]})


@labs_bp.post("/sessions/<int:session_id>/evidence")
@role_required("student")
def upload_session_evidence(session_id):
    lab_session = get_session_by_id(session_id)
    if not lab_session:
        return jsonify({"error": "Sesión no encontrada."}), 404

    if lab_session.student_id != request.current_user["sub"]:
        return jsonify({"error": "No autorizado."}), 403

    lab = get_lab_by_id(lab_session.lab_id)
    if not lab:
        return jsonify({"error": "Laboratorio no encontrado."}), 404

    files = request.files.getlist("files")
    if not files:
        return jsonify({"error": "No se enviaron archivos."}), 400

    note = (request.form.get("note") or "").strip()
    results = []

    for file in files:
        if not file.filename:
            continue

        if not is_allowed_evidence(file.filename):
            results.append({
                "filename": file.filename,
                "ok": False,
                "message": "Tipo de archivo no permitido.",
            })
            continue

        file_bytes = file.read()
        storage_path = save_lab_evidence_file(
            lab.subject_id,
            lab.id,
            session_id,
            file.filename,
            file_bytes,
        )
        record = add_evidence_record(
            session_id,
            file.filename,
            storage_path,
            note if len(results) == 0 else "",
        )
        results.append({
            "filename": file.filename,
            "ok": True,
            "evidence": evidence_to_dict(record),
        })

    if not results:
        return jsonify({"error": "No se enviaron archivos válidos."}), 400

    return jsonify({"results": results})


@labs_bp.get("/sessions/<int:session_id>/evidence/<int:evidence_id>/download")
@token_required
def download_session_evidence(session_id, evidence_id):
    lab_session = get_session_by_id(session_id)
    if not lab_session:
        return jsonify({"error": "Sesión no encontrada."}), 404

    if not _can_access_session(lab_session, request.current_user):
        return jsonify({"error": "No autorizado."}), 403

    evidence = get_evidence_by_id(evidence_id)
    if not evidence or evidence.session_id != session_id:
        return jsonify({"error": "Evidencia no encontrada."}), 404

    from pathlib import Path
    import mimetypes

    file_path = Path(evidence.storage_path)
    if not file_path.exists():
        return jsonify({"error": "Archivo no encontrado en el servidor."}), 404

    mime_type = mimetypes.guess_type(evidence.filename)[0] or "application/octet-stream"

    return Response(
        file_path.read_bytes(),
        mimetype=mime_type,
        headers={"Content-Disposition": f'attachment; filename="{evidence.filename}"'},
    )
