from flask import Blueprint, jsonify, request

from auth import (
    add_document_record,
    add_subject_teacher,
    create_subject,
    delete_subject,
    delete_subject_document,
    enroll_student,
    get_all_subjects,
    get_document_by_id,
    get_student_enrollments,
    get_subject_by_id,
    get_subject_documents,
    get_subject_teachers,
    get_teacher_name,
    get_teacher_subjects,
    is_subject_creator,
    mark_document_ingested,
    remove_subject_teacher,
    teacher_can_manage_subject,
    update_subject,
)
from config import Config
from ingest import ingest_pdf, save_uploaded_pdf
from jwt_utils import role_required, token_required
from ollama_client import is_model_available, list_ollama_models, validate_llm_model

subjects_bp = Blueprint("subjects", __name__)


def subject_to_dict(
    subject,
    include_teacher=False,
    current_teacher_id=None,
    available_models=None,
):
    model = subject.llm_model or Config.DEFAULT_LLM_MODEL
    teachers = get_subject_teachers(subject.id) if include_teacher else []
    primary_teacher = next((teacher for teacher in teachers if teacher["is_primary"]), None)

    data = {
        "id": subject.id,
        "name": subject.name,
        "description": subject.description or "",
        "teacher_id": subject.teacher_id,
        "llm_model": model,
    }
    if available_models is not None:
        data["llm_model_available"] = is_model_available(model, available_models)
    if include_teacher:
        data["teacher_name"] = (
            primary_teacher["nombre"]
            if primary_teacher
            else get_teacher_name(subject.teacher_id)
        )
        data["teacher_names"] = [teacher["nombre"] for teacher in teachers]
        data["teachers"] = teachers
    if current_teacher_id is not None:
        data["is_primary_teacher"] = subject.teacher_id == current_teacher_id
        data["can_delete"] = subject.teacher_id == current_teacher_id
    return data


def document_to_dict(doc):
    return {
        "id": doc.id,
        "filename": doc.filename,
        "ingested": bool(doc.ingested),
        "uploaded_at": doc.uploaded_at.isoformat() if doc.uploaded_at else None,
    }


@subjects_bp.get("/mine")
@role_required("teacher")
def my_subjects():
    teacher_id = request.current_user["sub"]
    subjects = get_teacher_subjects(teacher_id)
    available_models, _ = list_ollama_models()

    result = []
    for subject in subjects:
        docs = get_subject_documents(subject.id)
        ingested = sum(1 for d in docs if d.ingested)
        item = subject_to_dict(
            subject,
            include_teacher=True,
            current_teacher_id=teacher_id,
            available_models=available_models,
        )
        item["document_count"] = len(docs)
        item["ingested_count"] = ingested
        result.append(item)

    return jsonify({"subjects": result})


@subjects_bp.post("/")
@role_required("teacher")
def create_subject_route():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    description = (data.get("description") or "").strip()
    llm_model = (data.get("llm_model") or "").strip() or None

    if not name:
        return jsonify({"error": "El nombre es obligatorio."}), 400

    if llm_model:
        ok, model_error, resolved_model = validate_llm_model(llm_model)
        if not ok:
            return jsonify({"error": model_error}), 400
        llm_model = resolved_model

    subject = create_subject(
        request.current_user["sub"],
        name,
        description,
        llm_model=llm_model,
    )
    return jsonify({
        "subject": subject_to_dict(
            subject,
            include_teacher=True,
            current_teacher_id=request.current_user["sub"],
        ),
    }), 201


@subjects_bp.patch("/<int:subject_id>")
@role_required("teacher")
def update_subject_route(subject_id):
    if not teacher_can_manage_subject(subject_id, request.current_user["sub"]):
        return jsonify({"error": "Asignatura no encontrada o no autorizada."}), 403

    data = request.get_json(silent=True) or {}
    updates = {}
    if "name" in data:
        updates["name"] = data.get("name")
    if "description" in data:
        updates["description"] = data.get("description")
    if "llm_model" in data:
        updates["llm_model"] = data.get("llm_model")

    if not updates:
        return jsonify({"error": "No hay campos para actualizar."}), 400

    if "llm_model" in updates:
        model_value = (updates["llm_model"] or "").strip() or None
        if model_value:
            ok, model_error, resolved_model = validate_llm_model(model_value)
            if not ok:
                return jsonify({"error": model_error}), 400
            updates["llm_model"] = resolved_model
        else:
            updates["llm_model"] = None

    updated, error = update_subject(
        subject_id,
        request.current_user["sub"],
        **updates,
    )

    if error:
        return jsonify({"error": error}), 404

    return jsonify({
        "subject": subject_to_dict(
            updated,
            include_teacher=True,
            current_teacher_id=request.current_user["sub"],
            available_models=list_ollama_models()[0],
        ),
    })


@subjects_bp.delete("/<int:subject_id>")
@role_required("teacher")
def delete_subject_route(subject_id):
    teacher_id = request.current_user["sub"]
    if not is_subject_creator(subject_id, teacher_id):
        return jsonify({
            "error": "Solo el docente que creó la asignatura puede eliminarla.",
        }), 403

    ok, error, chunks_removed = delete_subject(subject_id, teacher_id)
    if not ok:
        status = 404 if error == "Asignatura no encontrada." else 403
        return jsonify({"error": error}), status

    return jsonify({
        "ok": True,
        "message": "Asignatura eliminada.",
        "chunks_removed": chunks_removed,
    })


@subjects_bp.get("/<int:subject_id>/teachers")
@role_required("teacher")
def list_subject_teachers(subject_id):
    if not teacher_can_manage_subject(subject_id, request.current_user["sub"]):
        return jsonify({"error": "No autorizado."}), 403

    return jsonify({"teachers": get_subject_teachers(subject_id)})


@subjects_bp.post("/<int:subject_id>/teachers")
@role_required("teacher")
def add_subject_teacher_route(subject_id):
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip()

    teachers, error = add_subject_teacher(
        subject_id,
        request.current_user["sub"],
        email,
    )
    if error:
        status = 403 if "autorizado" in error.lower() else 400
        return jsonify({"error": error}), status

    return jsonify({"teachers": teachers}), 201


@subjects_bp.delete("/<int:subject_id>/teachers/<int:teacher_id>")
@role_required("teacher")
def remove_subject_teacher_route(subject_id, teacher_id):
    teachers, error = remove_subject_teacher(
        subject_id,
        request.current_user["sub"],
        teacher_id,
    )
    if error:
        status = 403 if "autorizado" in error.lower() else 400
        return jsonify({"error": error}), status

    return jsonify({"teachers": teachers})


@subjects_bp.get("/")
@token_required
def list_subjects():
    user = request.current_user
    subjects = get_all_subjects()

    if user["role"] == "student":
        enrolled_ids = {
            e["subject_id"] for e in get_student_enrollments(user["sub"])
        }
        result = []
        for subject in subjects:
            item = subject_to_dict(subject, include_teacher=True)
            item["enrolled"] = subject.id in enrolled_ids
            result.append(item)
        return jsonify({"subjects": result})

    return jsonify({
        "subjects": [subject_to_dict(s, include_teacher=True) for s in subjects]
    })


@subjects_bp.get("/enrollments")
@role_required("student")
def my_enrollments():
    enrollments = get_student_enrollments(request.current_user["sub"])
    return jsonify({"enrollments": enrollments})


@subjects_bp.post("/<int:subject_id>/enroll")
@role_required("student")
def enroll(subject_id):
    ok, message = enroll_student(request.current_user["sub"], subject_id)
    status = 200 if ok else 400
    return jsonify({"ok": ok, "message": message}), status


@subjects_bp.get("/<int:subject_id>/documents")
@role_required("teacher")
def list_documents(subject_id):
    if not teacher_can_manage_subject(subject_id, request.current_user["sub"]):
        return jsonify({"error": "No autorizado."}), 403

    documents = get_subject_documents(subject_id)
    return jsonify({"documents": [document_to_dict(d) for d in documents]})


@subjects_bp.post("/<int:subject_id>/documents")
@role_required("teacher")
def upload_documents(subject_id):
    if not teacher_can_manage_subject(subject_id, request.current_user["sub"]):
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
        storage_path = save_uploaded_pdf(subject_id, file.filename, file_bytes)
        doc_record = add_document_record(subject_id, file.filename, storage_path)

        chunks = ingest_pdf(
            storage_path,
            subject_id,
            doc_record.id,
            file.filename,
        )

        if chunks > 0:
            mark_document_ingested(doc_record.id)
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


@subjects_bp.delete("/documents/<int:document_id>")
@role_required("teacher")
def delete_document_route(document_id):
    doc = get_document_by_id(document_id)
    if not doc:
        return jsonify({"error": "Documento no encontrado."}), 404

    if not teacher_can_manage_subject(doc.subject_id, request.current_user["sub"]):
        return jsonify({"error": "No autorizado."}), 403

    ok, error, chunks_removed = delete_subject_document(document_id)
    if not ok:
        return jsonify({"error": error}), 404

    return jsonify({
        "ok": True,
        "message": "Documento eliminado del sistema y de la base de conocimiento.",
        "chunks_removed": chunks_removed,
    })
