from flask import Blueprint, jsonify, request

from auth import get_teacher_subjects
from jwt_utils import role_required
from metrics import get_subject_metrics

metrics_bp = Blueprint("metrics", __name__)


@metrics_bp.get("/subjects")
@role_required("teacher")
def list_teacher_subjects_for_metrics():
    teacher_id = request.current_user["sub"]
    subjects = get_teacher_subjects(teacher_id)
    return jsonify({
        "subjects": [
            {"id": s.id, "name": s.name, "description": s.description or ""}
            for s in subjects
        ],
    })


@metrics_bp.get("/subjects/<int:subject_id>")
@role_required("teacher")
def subject_metrics(subject_id):
    teacher_id = request.current_user["sub"]
    data = get_subject_metrics(subject_id, teacher_id)

    if not data:
        return jsonify({"error": "Asignatura no encontrada o no autorizada."}), 404

    return jsonify(data)
