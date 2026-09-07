from datetime import datetime
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def _escape(text: str) -> str:
    if not text:
        return ""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("\n", "<br/>")
    )


def generate_results_pdf(data: dict) -> bytes:
    attempt = data["attempt"]
    evaluation = data["evaluation"]
    subject = data["subject"]
    student = data["student"]
    answers = data["answers"]

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "Title",
        parent=styles["Heading1"],
        fontSize=18,
        spaceAfter=12,
    )
    heading_style = ParagraphStyle(
        "Heading",
        parent=styles["Heading2"],
        fontSize=13,
        spaceBefore=14,
        spaceAfter=8,
    )
    body_style = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontSize=10,
        leading=14,
        spaceAfter=6,
    )
    small_style = ParagraphStyle(
        "Small",
        parent=styles["Normal"],
        fontSize=9,
        textColor=colors.grey,
    )

    story = []

    story.append(Paragraph("Resultados de Evaluación", title_style))
    story.append(Spacer(1, 0.3 * cm))

    info = [
        ["Estudiante:", student.nombre if student else "—"],
        ["Asignatura:", subject.name if subject else "—"],
        ["Evaluación:", evaluation.title if evaluation else "—"],
        ["Tema:", evaluation.topic if evaluation else "—"],
        [
            "Fecha:",
            attempt.completed_at.strftime("%d/%m/%Y %H:%M")
            if attempt.completed_at
            else datetime.utcnow().strftime("%d/%m/%Y %H:%M"),
        ],
        ["Puntuación:", f"{attempt.score}% ({attempt.correct_count}/{attempt.total_questions})"],
    ]

    info_table = Table(info, colWidths=[4 * cm, 12 * cm])
    info_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 0.5 * cm))

    for answer in answers:
        resultado = "Correcta" if answer.correcta else "Incorrecta"
        resultado_color = "#059669" if answer.correcta else "#dc2626"

        story.append(Paragraph(
            f"Pregunta {answer.question_number}",
            heading_style,
        ))
        story.append(Paragraph(_escape(answer.pregunta), body_style))
        story.append(Paragraph(
            f"<b>Resultado:</b> <font color='{resultado_color}'>{resultado}</font>",
            body_style,
        ))
        story.append(Paragraph(
            f"<b>Respuesta del estudiante:</b><br/>{_escape(answer.respuesta_estudiante)}",
            body_style,
        ))
        if answer.evaluacion:
            story.append(Paragraph(
                f"<b>Evaluación:</b><br/>{_escape(answer.evaluacion)}",
                body_style,
            ))
        if answer.fuente:
            story.append(Paragraph(f"Fuente: {_escape(answer.fuente)}", small_style))
        story.append(Spacer(1, 0.2 * cm))

    doc.build(story)
    buffer.seek(0)
    return buffer.read()


def generate_lab_chat_pdf(data: dict) -> bytes:
    lab_session = data["session"]
    lab = data["lab"]
    subject = data["subject"]
    student = data["student"]
    messages = data["messages"]

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "Title",
        parent=styles["Heading1"],
        fontSize=18,
        spaceAfter=12,
    )
    heading_style = ParagraphStyle(
        "Heading",
        parent=styles["Heading2"],
        fontSize=13,
        spaceBefore=14,
        spaceAfter=8,
    )
    body_style = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontSize=10,
        leading=14,
        spaceAfter=6,
    )
    small_style = ParagraphStyle(
        "Small",
        parent=styles["Normal"],
        fontSize=9,
        textColor=colors.grey,
    )

    story = []
    story.append(Paragraph("Chat del Laboratorio", title_style))
    story.append(Spacer(1, 0.3 * cm))

    status_label = "Completado" if lab_session.status == "completed" else "En progreso"
    info = [
        ["Estudiante:", student.nombre if student else "—"],
        ["Asignatura:", subject.name if subject else "—"],
        ["Laboratorio:", lab.title if lab else "—"],
        ["Tema:", lab.topic if lab else "—"],
        ["Estado:", status_label],
        [
            "Inicio:",
            lab_session.started_at.strftime("%d/%m/%Y %H:%M")
            if lab_session.started_at
            else "—",
        ],
        [
            "Finalización:",
            lab_session.completed_at.strftime("%d/%m/%Y %H:%M")
            if lab_session.completed_at
            else "—",
        ],
    ]

    info_table = Table(info, colWidths=[4 * cm, 12 * cm])
    info_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 0.4 * cm))

    if lab and lab.instructions:
        story.append(Paragraph("Instrucciones del laboratorio", heading_style))
        story.append(Paragraph(_escape(lab.instructions), body_style))
        story.append(Spacer(1, 0.3 * cm))

    story.append(Paragraph("Historial del chat", heading_style))

    student_name = student.nombre if student else "Estudiante"
    for msg in messages:
        if msg.role == "user":
            label = student_name
            color = "#4338ca"
        else:
            label = "Asistente"
            color = "#374151"

        timestamp = (
            msg.created_at.strftime("%d/%m/%Y %H:%M")
            if msg.created_at
            else ""
        )
        story.append(Paragraph(
            f"<b><font color='{color}'>{label}</font></b>"
            + (f" <font size='8' color='#6b7280'>{timestamp}</font>" if timestamp else ""),
            body_style,
        ))
        story.append(Paragraph(_escape(msg.content), body_style))
        story.append(Spacer(1, 0.15 * cm))

    doc.build(story)
    buffer.seek(0)
    return buffer.read()
