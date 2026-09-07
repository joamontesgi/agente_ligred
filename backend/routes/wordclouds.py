from flask import Blueprint, jsonify, request

from conversation_pdfs import (
    delete_conversation_pdf,
    get_conversation_pdf,
    get_pdf_paths_for_subject,
    list_conversation_pdfs,
    pdf_to_dict,
    save_conversation_pdf,
    teacher_owns_subject,
)
from jwt_utils import role_required
from wordcloud_service import build_wordcloud_analysis

wordclouds_bp = Blueprint("wordclouds", __name__)


@wordclouds_bp.get("/subjects/<int:subject_id>/pdfs")
@role_required("teacher")
def list_pdfs(subject_id):
    teacher_id = request.current_user["sub"]
    if not teacher_owns_subject(subject_id, teacher_id):
        return jsonify({"error": "No autorizado."}), 403

    records = list_conversation_pdfs(subject_id)
    return jsonify({"pdfs": [pdf_to_dict(record) for record in records]})


@wordclouds_bp.post("/subjects/<int:subject_id>/pdfs")
@role_required("teacher")
def upload_pdfs(subject_id):
    teacher_id = request.current_user["sub"]
    if not teacher_owns_subject(subject_id, teacher_id):
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

        record = save_conversation_pdf(subject_id, file.filename, file.read())
        results.append({
            "filename": record.filename,
            "ok": True,
            "id": record.id,
            "message": "PDF cargado.",
        })

    return jsonify({"results": results})


@wordclouds_bp.delete("/pdfs/<int:pdf_id>")
@role_required("teacher")
def remove_pdf(pdf_id):
    teacher_id = request.current_user["sub"]
    record = get_conversation_pdf(pdf_id)
    if not record:
        return jsonify({"error": "PDF no encontrado."}), 404

    if not teacher_owns_subject(record.subject_id, teacher_id):
        return jsonify({"error": "No autorizado."}), 403

    delete_conversation_pdf(pdf_id)
    return jsonify({"ok": True})


@wordclouds_bp.post("/subjects/<int:subject_id>/generate")
@role_required("teacher")
def generate_wordcloud(subject_id):
    teacher_id = request.current_user["sub"]
    if not teacher_owns_subject(subject_id, teacher_id):
        return jsonify({"error": "No autorizado."}), 403

    payload = request.get_json(silent=True) or {}
    pdf_ids = payload.get("pdf_ids")
    if pdf_ids is not None and not isinstance(pdf_ids, list):
        return jsonify({"error": "pdf_ids debe ser una lista."}), 400

    pdf_paths = get_pdf_paths_for_subject(subject_id, pdf_ids)
    if not pdf_paths:
        return jsonify({"error": "No hay PDFs seleccionados para analizar."}), 400

    try:
        analysis = build_wordcloud_analysis(pdf_paths)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    analysis["documents_used"] = len(pdf_paths)
    return jsonify(analysis)
