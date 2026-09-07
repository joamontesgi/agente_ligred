from datetime import datetime

from models import Enrollment, Evaluation, EvaluationAnswer, EvaluationAttempt, Subject
from database import get_session


def create_evaluation(subject_id: int, title: str, topic: str, num_questions: int):
    session = get_session()
    try:
        evaluation = Evaluation(
            subject_id=subject_id,
            title=title.strip(),
            topic=topic.strip(),
            num_questions=num_questions,
        )
        session.add(evaluation)
        session.commit()
        session.refresh(evaluation)
        return evaluation
    finally:
        session.close()


def get_evaluations_by_subject(subject_id: int):
    session = get_session()
    try:
        return (
            session.query(Evaluation)
            .filter(Evaluation.subject_id == subject_id)
            .order_by(Evaluation.created_at.desc())
            .all()
        )
    finally:
        session.close()


def get_evaluation_by_id(evaluation_id: int):
    session = get_session()
    try:
        return session.query(Evaluation).filter(Evaluation.id == evaluation_id).first()
    finally:
        session.close()


def count_evaluation_attempts(evaluation_id: int) -> int:
    session = get_session()
    try:
        return (
            session.query(EvaluationAttempt)
            .filter(EvaluationAttempt.evaluation_id == evaluation_id)
            .count()
        )
    finally:
        session.close()


def update_evaluation(evaluation_id: int, **fields):
    session = get_session()
    try:
        evaluation = session.query(Evaluation).filter(
            Evaluation.id == evaluation_id
        ).first()
        if not evaluation:
            return None, "Evaluación no encontrada."

        if "title" in fields:
            title = (fields["title"] or "").strip()
            if not title:
                return None, "El título no puede estar vacío."
            evaluation.title = title

        if "topic" in fields:
            topic = (fields["topic"] or "").strip()
            if not topic:
                return None, "El tema no puede estar vacío."
            evaluation.topic = topic

        if "num_questions" in fields:
            try:
                num_questions = int(fields["num_questions"])
            except (TypeError, ValueError):
                return None, "num_questions debe ser un número."
            if num_questions < 1 or num_questions > 20:
                return None, "El número de preguntas debe estar entre 1 y 20."
            evaluation.num_questions = num_questions

        session.commit()
        session.refresh(evaluation)
        return evaluation, None
    finally:
        session.close()


def delete_evaluation(evaluation_id: int):
    session = get_session()
    try:
        evaluation = session.query(Evaluation).filter(
            Evaluation.id == evaluation_id
        ).first()
        if not evaluation:
            return False, "Evaluación no encontrada."

        session.delete(evaluation)
        session.commit()
        return True, None
    finally:
        session.close()


def get_available_evaluations_for_student(student_id: int):
    session = get_session()
    try:
        return (
            session.query(Evaluation, Subject)
            .join(Subject, Evaluation.subject_id == Subject.id)
            .join(Enrollment, Enrollment.subject_id == Subject.id)
            .filter(Enrollment.student_id == student_id)
            .order_by(Evaluation.created_at.desc())
            .all()
        )
    finally:
        session.close()


def create_attempt(evaluation_id: int, student_id: int):
    session = get_session()
    try:
        attempt = EvaluationAttempt(
            evaluation_id=evaluation_id,
            student_id=student_id,
            status="in_progress",
        )
        session.add(attempt)
        session.commit()
        session.refresh(attempt)
        return attempt
    finally:
        session.close()


def get_attempt_by_id(attempt_id: int):
    session = get_session()
    try:
        return (
            session.query(EvaluationAttempt)
            .filter(EvaluationAttempt.id == attempt_id)
            .first()
        )
    finally:
        session.close()


def get_in_progress_attempt(evaluation_id: int, student_id: int):
    session = get_session()
    try:
        return (
            session.query(EvaluationAttempt)
            .filter(
                EvaluationAttempt.evaluation_id == evaluation_id,
                EvaluationAttempt.student_id == student_id,
                EvaluationAttempt.status == "in_progress",
            )
            .first()
        )
    finally:
        session.close()


def add_answer(
    attempt_id: int,
    question_number: int,
    pregunta: str,
    contexto: str,
    fuente: str,
):
    session = get_session()
    try:
        answer = EvaluationAnswer(
            attempt_id=attempt_id,
            question_number=question_number,
            pregunta=pregunta,
            contexto=contexto,
            fuente=fuente,
        )
        session.add(answer)
        session.commit()
        session.refresh(answer)
        return answer
    finally:
        session.close()


def get_answers_for_attempt(attempt_id: int):
    session = get_session()
    try:
        return (
            session.query(EvaluationAnswer)
            .filter(EvaluationAnswer.attempt_id == attempt_id)
            .order_by(EvaluationAnswer.question_number)
            .all()
        )
    finally:
        session.close()


def complete_attempt(attempt_id: int, correct_count: int, total: int):
    session = get_session()
    try:
        attempt = session.query(EvaluationAttempt).filter(
            EvaluationAttempt.id == attempt_id
        ).first()
        if attempt:
            attempt.status = "completed"
            attempt.correct_count = correct_count
            attempt.total_questions = total
            attempt.score = round((correct_count / total) * 100, 1) if total else 0
            attempt.completed_at = datetime.utcnow()
            session.commit()
            session.refresh(attempt)
        return attempt
    finally:
        session.close()


def update_answer_result(
    answer_id: int,
    respuesta_estudiante: str,
    evaluacion: str,
    correcta: bool,
):
    session = get_session()
    try:
        answer = session.query(EvaluationAnswer).filter(
            EvaluationAnswer.id == answer_id
        ).first()
        if answer:
            answer.respuesta_estudiante = respuesta_estudiante
            answer.evaluacion = evaluacion
            answer.correcta = 1 if correcta else 0
            session.commit()
            session.refresh(answer)
        return answer
    finally:
        session.close()


def evaluation_to_dict(evaluation, subject_name=None, attempt_count=None):
    data = {
        "id": evaluation.id,
        "subject_id": evaluation.subject_id,
        "title": evaluation.title,
        "topic": evaluation.topic,
        "num_questions": evaluation.num_questions,
        "created_at": evaluation.created_at.isoformat() if evaluation.created_at else None,
    }
    if subject_name:
        data["subject_name"] = subject_name
    if attempt_count is not None:
        data["attempt_count"] = attempt_count
    return data


def attempt_to_dict(attempt, include_answers=False):
    data = {
        "id": attempt.id,
        "evaluation_id": attempt.evaluation_id,
        "student_id": attempt.student_id,
        "status": attempt.status,
        "score": attempt.score,
        "correct_count": attempt.correct_count,
        "total_questions": attempt.total_questions,
        "completed_at": attempt.completed_at.isoformat() if attempt.completed_at else None,
    }
    if include_answers:
        answers = get_answers_for_attempt(attempt.id)
        data["answers"] = [answer_to_dict(a) for a in answers]
    return data


def answer_to_dict(answer, include_evaluation=False):
    data = {
        "id": answer.id,
        "question_number": answer.question_number,
        "pregunta": answer.pregunta,
        "respuesta_estudiante": answer.respuesta_estudiante or "",
        "correcta": bool(answer.correcta),
        "fuente": answer.fuente,
    }
    if include_evaluation:
        data["evaluacion"] = answer.evaluacion or ""
    return data


def get_attempt_full(attempt_id: int):
    session = get_session()
    try:
        attempt = session.query(EvaluationAttempt).filter(
            EvaluationAttempt.id == attempt_id
        ).first()
        if not attempt:
            return None

        evaluation = session.query(Evaluation).filter(
            Evaluation.id == attempt.evaluation_id
        ).first()
        subject = session.query(Subject).filter(
            Subject.id == evaluation.subject_id
        ).first() if evaluation else None

        from models import User
        student = session.query(User).filter(User.id == attempt.student_id).first()

        answers = (
            session.query(EvaluationAnswer)
            .filter(EvaluationAnswer.attempt_id == attempt_id)
            .order_by(EvaluationAnswer.question_number)
            .all()
        )

        return {
            "attempt": attempt,
            "evaluation": evaluation,
            "subject": subject,
            "student": student,
            "answers": answers,
        }
    finally:
        session.close()
