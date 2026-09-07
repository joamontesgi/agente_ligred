from flask import Blueprint, Response, jsonify, request

from auth import (
    get_subject_by_id,
    get_subject_document_stats,
    is_student_enrolled,
    subject_has_ingested_documents,
    teacher_can_manage_subject,
)
from evaluations import (
    add_answer,
    answer_to_dict,
    attempt_to_dict,
    complete_attempt,
    count_evaluation_attempts,
    create_attempt,
    create_evaluation,
    delete_evaluation,
    evaluation_to_dict,
    get_attempt_by_id,
    get_attempt_full,
    get_available_evaluations_for_student,
    get_answers_for_attempt,
    get_evaluation_by_id,
    get_evaluations_by_subject,
    get_in_progress_attempt,
    update_answer_result,
    update_evaluation,
)
from jwt_utils import role_required
from pdf_export import generate_results_pdf
from rag import ProfesorRAG
from routes.llm_errors import llm_error_response

evaluations_bp = Blueprint("evaluations", __name__)


def get_rag(subject_id: int):
    return ProfesorRAG.for_subject(subject_id)


def _verify_teacher_owns_subject(subject, user_id):
    return subject and teacher_can_manage_subject(subject.id, user_id)


def _get_teacher_evaluation(evaluation_id, user_id):
    evaluation = get_evaluation_by_id(evaluation_id)
    if not evaluation:
        return None, "Evaluación no encontrada.", 404

    subject = get_subject_by_id(evaluation.subject_id)
    if not _verify_teacher_owns_subject(subject, user_id):
        return None, "No autorizado.", 403

    return evaluation, None, None


@evaluations_bp.post("/")
@role_required("teacher")
def create_evaluation_route():
    data = request.get_json(silent=True) or {}

    subject_id = data.get("subject_id")
    title = (data.get("title") or "").strip()
    topic = (data.get("topic") or "").strip()
    num_questions = data.get("num_questions", 5)

    if not subject_id or not topic:
        return jsonify({"error": "subject_id y topic son obligatorios."}), 400

    try:
        num_questions = int(num_questions)
    except (TypeError, ValueError):
        return jsonify({"error": "num_questions debe ser un número."}), 400

    if num_questions < 1 or num_questions > 20:
        return jsonify({"error": "El número de preguntas debe estar entre 1 y 20."}), 400

    subject = get_subject_by_id(subject_id)
    if not _verify_teacher_owns_subject(subject, request.current_user["sub"]):
        return jsonify({"error": "Asignatura no encontrada o no autorizada."}), 403

    if not subject_has_ingested_documents(subject_id):
        return jsonify({
            "error": (
                "La asignatura no tiene documentos procesados. Sube y procesa PDFs "
                "antes de crear evaluaciones; las preguntas se generan solo con ese material."
            ),
        }), 400

    if not title:
        title = f"Evaluación: {topic}"

    evaluation = create_evaluation(subject_id, title, topic, num_questions)
    return jsonify({"evaluation": evaluation_to_dict(evaluation)}), 201


@evaluations_bp.get("/")
@role_required("teacher")
def list_evaluations():
    subject_id = request.args.get("subject_id", type=int)
    if not subject_id:
        return jsonify({"error": "subject_id es obligatorio."}), 400

    subject = get_subject_by_id(subject_id)
    if not _verify_teacher_owns_subject(subject, request.current_user["sub"]):
        return jsonify({"error": "No autorizado."}), 403

    evaluations = get_evaluations_by_subject(subject_id)
    has_documents = subject_has_ingested_documents(subject_id)
    return jsonify({
        "evaluations": [
            evaluation_to_dict(
                evaluation,
                attempt_count=count_evaluation_attempts(evaluation.id),
            )
            for evaluation in evaluations
        ],
        "has_documents": has_documents,
    })


@evaluations_bp.patch("/<int:evaluation_id>")
@role_required("teacher")
def update_evaluation_route(evaluation_id):
    evaluation, error, status = _get_teacher_evaluation(
        evaluation_id,
        request.current_user["sub"],
    )
    if error:
        return jsonify({"error": error}), status

    data = request.get_json(silent=True) or {}
    updates = {}
    if "title" in data:
        updates["title"] = data.get("title")
    if "topic" in data:
        updates["topic"] = data.get("topic")
    if "num_questions" in data:
        updates["num_questions"] = data.get("num_questions")

    if not updates:
        return jsonify({"error": "No hay campos para actualizar."}), 400

    updated, error = update_evaluation(evaluation_id, **updates)
    if error:
        return jsonify({"error": error}), 400

    return jsonify({
        "evaluation": evaluation_to_dict(
            updated,
            attempt_count=count_evaluation_attempts(updated.id),
        ),
    })


@evaluations_bp.delete("/<int:evaluation_id>")
@role_required("teacher")
def delete_evaluation_route(evaluation_id):
    evaluation, error, status = _get_teacher_evaluation(
        evaluation_id,
        request.current_user["sub"],
    )
    if error:
        return jsonify({"error": error}), status

    attempt_count = count_evaluation_attempts(evaluation_id)
    ok, error = delete_evaluation(evaluation_id)
    if not ok:
        return jsonify({"error": error}), 404

    return jsonify({
        "ok": True,
        "message": "Evaluación eliminada.",
        "attempts_removed": attempt_count,
    })


@evaluations_bp.get("/available")
@role_required("student")
def list_available():
    rows = get_available_evaluations_for_student(request.current_user["sub"])
    result = []
    for evaluation, subject in rows:
        item = evaluation_to_dict(evaluation, subject_name=subject.name)
        doc_stats = get_subject_document_stats(subject.id)
        item["document_count"] = doc_stats["document_count"]
        item["ingested_document_count"] = doc_stats["ingested_count"]
        item["has_documents"] = subject_has_ingested_documents(subject.id)
        in_progress = get_in_progress_attempt(evaluation.id, request.current_user["sub"])
        item["in_progress"] = in_progress is not None
        if in_progress:
            item["attempt_id"] = in_progress.id
        result.append(item)
    return jsonify({"evaluations": result})


@evaluations_bp.post("/<int:evaluation_id>/start")
@role_required("student")
def start_evaluation(evaluation_id):
    student_id = request.current_user["sub"]
    evaluation = get_evaluation_by_id(evaluation_id)

    if not evaluation:
        return jsonify({"error": "Evaluación no encontrada."}), 404

    if not is_student_enrolled(student_id, evaluation.subject_id):
        return jsonify({"error": "No estás inscrito en esta asignatura."}), 403

    if not subject_has_ingested_documents(evaluation.subject_id):
        return jsonify({
            "error": (
                "Esta evaluación requiere documentos procesados en la asignatura. "
                "El docente debe subir y procesar PDFs primero."
            ),
        }), 400

    existing = get_in_progress_attempt(evaluation_id, student_id)
    if existing:
        answers = get_answers_for_attempt(existing.id)
        return jsonify({
            "attempt_id": existing.id,
            "evaluation": evaluation_to_dict(evaluation),
            "questions": [
                answer_to_dict(a) for a in answers
            ],
        })

    try:
        result = get_rag(evaluation.subject_id).generar_preguntas(
            evaluation.subject_id,
            evaluation.topic,
            evaluation.num_questions,
        )
    except RuntimeError as exc:
        return llm_error_response(exc)

    if result.get("error"):
        return jsonify({"error": result["error"]}), 400

    attempt = create_attempt(evaluation_id, student_id)

    for q in result["preguntas"]:
        add_answer(
            attempt.id,
            q["question_number"],
            q["pregunta"],
            q["contexto"],
            q["fuente"],
        )

    answers = get_answers_for_attempt(attempt.id)

    return jsonify({
        "attempt_id": attempt.id,
        "evaluation": evaluation_to_dict(evaluation),
        "questions": [answer_to_dict(a) for a in answers],
    })


@evaluations_bp.post("/attempts/<int:attempt_id>/submit")
@role_required("student")
def submit_evaluation(attempt_id):
    student_id = request.current_user["sub"]
    attempt = get_attempt_by_id(attempt_id)

    if not attempt:
        return jsonify({"error": "Intento no encontrado."}), 404

    if attempt.student_id != student_id:
        return jsonify({"error": "No autorizado."}), 403

    if attempt.status == "completed":
        return jsonify({"error": "Esta evaluación ya fue enviada."}), 400

    data = request.get_json(silent=True) or {}
    submitted = data.get("answers") or []

    if not submitted:
        return jsonify({"error": "Debes enviar al menos una respuesta."}), 400

    stored_answers = get_answers_for_attempt(attempt_id)
    answers_by_num = {a.question_number: a for a in stored_answers}
    submitted_by_num = {
        item.get("question_number"): (item.get("respuesta") or "").strip()
        for item in submitted
    }

    if len(submitted_by_num) != len(stored_answers):
        return jsonify({"error": "Debes responder todas las preguntas."}), 400

    evaluation = get_evaluation_by_id(attempt.evaluation_id)
    subject_id = evaluation.subject_id if evaluation else None
    rag = get_rag(subject_id) if subject_id else ProfesorRAG()
    correct_count = 0

    for num, answer in answers_by_num.items():
        respuesta = submitted_by_num.get(num, "")
        if not respuesta:
            return jsonify({"error": f"Falta la respuesta de la pregunta {num}."}), 400

        try:
            evaluacion = rag.evaluar(answer.contexto, answer.pregunta, respuesta)
        except RuntimeError as exc:
            return llm_error_response(exc)
        correcta = "Correcta" in evaluacion

        update_answer_result(answer.id, respuesta, evaluacion, correcta)
        if correcta:
            correct_count += 1

    complete_attempt(attempt_id, correct_count, len(stored_answers))
    updated = get_attempt_by_id(attempt_id)
    answers = get_answers_for_attempt(attempt_id)

    return jsonify({
        "attempt": attempt_to_dict(updated),
        "answers": [answer_to_dict(a, include_evaluation=True) for a in answers],
    })


@evaluations_bp.get("/attempts/<int:attempt_id>")
@role_required("student")
def get_attempt_results(attempt_id):
    student_id = request.current_user["sub"]
    attempt = get_attempt_by_id(attempt_id)

    if not attempt:
        return jsonify({"error": "Intento no encontrado."}), 404

    if attempt.student_id != student_id:
        return jsonify({"error": "No autorizado."}), 403

    evaluation = get_evaluation_by_id(attempt.evaluation_id)
    answers = get_answers_for_attempt(attempt_id)

    return jsonify({
        "attempt": attempt_to_dict(attempt),
        "evaluation": evaluation_to_dict(evaluation) if evaluation else None,
        "answers": [answer_to_dict(a, include_evaluation=True) for a in answers],
    })


@evaluations_bp.get("/attempts/<int:attempt_id>/pdf")
@role_required("student")
def export_pdf(attempt_id):
    student_id = request.current_user["sub"]
    data = get_attempt_full(attempt_id)

    if not data:
        return jsonify({"error": "Intento no encontrado."}), 404

    if data["attempt"].student_id != student_id:
        return jsonify({"error": "No autorizado."}), 403

    if data["attempt"].status != "completed":
        return jsonify({"error": "La evaluación aún no está completada."}), 400

    pdf_bytes = generate_results_pdf(data)
    filename = f"evaluacion_{attempt_id}_resultados.pdf"

    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
