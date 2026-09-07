from flask import Blueprint, jsonify, request

from auth import is_student_enrolled
from jwt_utils import role_required
from rag import ProfesorRAG
from routes.llm_errors import llm_error_response

practice_bp = Blueprint("practice", __name__)


def get_rag(subject_id: int):
    return ProfesorRAG.for_subject(subject_id)


@practice_bp.post("/question")
@role_required("student")
def generate_question():
    data = request.get_json(silent=True) or {}
    subject_id = data.get("subject_id")

    if not subject_id:
        return jsonify({"error": "subject_id es obligatorio."}), 400

    student_id = request.current_user["sub"]
    if not is_student_enrolled(student_id, subject_id):
        return jsonify({"error": "No estás inscrito en esta asignatura."}), 403

    try:
        result = get_rag(subject_id).generar_pregunta(subject_id)
    except RuntimeError as exc:
        return llm_error_response(exc)

    if result.get("error"):
        return jsonify({"error": result["error"]}), 400

    return jsonify({
        "pregunta": result["pregunta"],
        "contexto": result["contexto"],
        "fuente": result["fuente"],
    })


@practice_bp.post("/evaluate")
@role_required("student")
def evaluate_answer():
    data = request.get_json(silent=True) or {}

    contexto = (data.get("contexto") or "").strip()
    pregunta = (data.get("pregunta") or "").strip()
    respuesta = (data.get("respuesta") or "").strip()

    subject_id = data.get("subject_id")

    if not all([contexto, pregunta, respuesta]):
        return jsonify({"error": "Faltan campos obligatorios."}), 400

    if subject_id:
        student_id = request.current_user["sub"]
        if not is_student_enrolled(student_id, subject_id):
            return jsonify({"error": "No estás inscrito en esta asignatura."}), 403
        rag = get_rag(subject_id)
    else:
        rag = ProfesorRAG()

    try:
        evaluacion = rag.evaluar(contexto, pregunta, respuesta)
    except RuntimeError as exc:
        return llm_error_response(exc)
    correcta = "Correcta" in evaluacion

    return jsonify({
        "evaluacion": evaluacion,
        "correcta": correcta,
    })
