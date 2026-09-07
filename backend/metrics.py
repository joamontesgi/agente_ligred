from sqlalchemy import func

from auth import teacher_can_manage_subject
from database import get_session
from models import (
    Enrollment,
    Evaluation,
    EvaluationAttempt,
    Lab,
    LabChatMessage,
    LabEvidence,
    LabSession,
    Subject,
    User,
)


def _verify_teacher_subject(subject_id: int, teacher_id: int):
    session = get_session()
    try:
        if not teacher_can_manage_subject(subject_id, teacher_id):
            return None
        return session.query(Subject).filter(Subject.id == subject_id).first()
    finally:
        session.close()


def get_subject_metrics(subject_id: int, teacher_id: int):
    session = get_session()
    try:
        if not teacher_can_manage_subject(subject_id, teacher_id):
            return None

        subject = session.query(Subject).filter(Subject.id == subject_id).first()
        if not subject:
            return None

        students_count = session.query(Enrollment).filter(
            Enrollment.subject_id == subject_id
        ).count()

        labs = session.query(Lab).filter(Lab.subject_id == subject_id).all()
        evaluations = session.query(Evaluation).filter(
            Evaluation.subject_id == subject_id
        ).all()

        lab_sessions = (
            session.query(LabSession, Lab, User)
            .join(Lab, LabSession.lab_id == Lab.id)
            .join(User, LabSession.student_id == User.id)
            .filter(Lab.subject_id == subject_id)
            .order_by(LabSession.started_at.desc())
            .all()
        )

        lab_rows = []
        for lab_session, lab, student in lab_sessions:
            msg_count = session.query(LabChatMessage).filter(
                LabChatMessage.session_id == lab_session.id
            ).count()
            user_msg_count = session.query(LabChatMessage).filter(
                LabChatMessage.session_id == lab_session.id,
                LabChatMessage.role == "user",
            ).count()
            evidence_count = session.query(LabEvidence).filter(
                LabEvidence.session_id == lab_session.id
            ).count()

            duration_min = None
            if lab_session.started_at and lab_session.completed_at:
                delta = lab_session.completed_at - lab_session.started_at
                duration_min = round(delta.total_seconds() / 60, 1)

            lab_rows.append({
                "session_id": lab_session.id,
                "lab_id": lab.id,
                "lab_title": lab.title,
                "student_id": student.id,
                "student_name": student.nombre,
                "student_email": student.email,
                "status": lab_session.status,
                "message_count": msg_count,
                "student_message_count": user_msg_count,
                "evidence_count": evidence_count,
                "started_at": lab_session.started_at.isoformat() if lab_session.started_at else None,
                "completed_at": lab_session.completed_at.isoformat() if lab_session.completed_at else None,
                "duration_minutes": duration_min,
            })

        eval_attempts = (
            session.query(EvaluationAttempt, Evaluation, User)
            .join(Evaluation, EvaluationAttempt.evaluation_id == Evaluation.id)
            .join(User, EvaluationAttempt.student_id == User.id)
            .filter(Evaluation.subject_id == subject_id)
            .order_by(EvaluationAttempt.started_at.desc())
            .all()
        )

        eval_rows = []
        for attempt, evaluation, student in eval_attempts:
            eval_rows.append({
                "attempt_id": attempt.id,
                "evaluation_id": evaluation.id,
                "evaluation_title": evaluation.title,
                "topic": evaluation.topic,
                "student_id": student.id,
                "student_name": student.nombre,
                "status": attempt.status,
                "score": attempt.score,
                "correct_count": attempt.correct_count,
                "total_questions": attempt.total_questions,
                "started_at": attempt.started_at.isoformat() if attempt.started_at else None,
                "completed_at": attempt.completed_at.isoformat() if attempt.completed_at else None,
            })

        completed_labs = sum(1 for r in lab_rows if r["status"] == "completed")
        completed_evals = sum(1 for r in eval_rows if r["status"] == "completed")
        avg_eval_score = session.query(func.avg(EvaluationAttempt.score)).join(
            Evaluation
        ).filter(
            Evaluation.subject_id == subject_id,
            EvaluationAttempt.status == "completed",
        ).scalar()

        return {
            "subject": {
                "id": subject.id,
                "name": subject.name,
            },
            "summary": {
                "students_enrolled": students_count,
                "labs_count": len(labs),
                "evaluations_count": len(evaluations),
                "lab_sessions_total": len(lab_rows),
                "lab_sessions_completed": completed_labs,
                "evaluation_attempts_total": len(eval_rows),
                "evaluation_attempts_completed": completed_evals,
                "avg_evaluation_score": round(float(avg_eval_score), 1) if avg_eval_score else None,
            },
            "lab_sessions": lab_rows,
            "evaluation_attempts": eval_rows,
        }
    finally:
        session.close()
