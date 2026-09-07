from flask import Blueprint, jsonify, request

from auth import (
    get_security_question_for_email,
    login_user,
    register_user,
    reset_password_with_security_answer,
)
from jwt_utils import create_token, get_current_user_dict, token_required
from security_questions import SECURITY_QUESTIONS

auth_bp = Blueprint("auth", __name__)


@auth_bp.get("/security-questions")
def list_security_questions():
    return jsonify({"questions": SECURITY_QUESTIONS})


@auth_bp.post("/register")
def register():
    data = request.get_json(silent=True) or {}

    nombre = (data.get("nombre") or "").strip()
    email = (data.get("email") or "").strip()
    password = data.get("password") or ""
    role = data.get("role") or "student"
    security_question = data.get("security_question") or ""
    security_answer = data.get("security_answer") or ""

    if not all([nombre, email, password]):
        return jsonify({"error": "Completa todos los campos."}), 400

    if len(password) < 6:
        return jsonify({"error": "La contraseña debe tener al menos 6 caracteres."}), 400

    user, error = register_user(
        email,
        password,
        nombre,
        role,
        security_question=security_question,
        security_answer=security_answer,
    )
    if error:
        return jsonify({"error": error}), 400

    token = create_token(user)
    return jsonify({"token": token, "user": user}), 201


@auth_bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}

    email = (data.get("email") or "").strip()
    password = data.get("password") or ""

    if not email or not password:
        return jsonify({"error": "Completa todos los campos."}), 400

    user, error = login_user(email, password)
    if error:
        return jsonify({"error": error}), 401

    token = create_token(user)
    return jsonify({"token": token, "user": user})


@auth_bp.post("/forgot-password/lookup")
def forgot_password_lookup():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip()

    if not email:
        return jsonify({"error": "Ingresa tu correo electrónico."}), 400

    question, error = get_security_question_for_email(email)
    if error:
        return jsonify({"error": error}), 404

    return jsonify({"email": email, "security_question": question})


@auth_bp.post("/forgot-password/reset")
def forgot_password_reset():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip()
    security_answer = data.get("security_answer") or ""
    new_password = data.get("new_password") or ""
    confirm_password = data.get("confirm_password") or new_password

    if not email:
        return jsonify({"error": "Ingresa tu correo electrónico."}), 400

    if new_password != confirm_password:
        return jsonify({"error": "Las contraseñas no coinciden."}), 400

    ok, error = reset_password_with_security_answer(
        email,
        security_answer,
        new_password,
    )
    if not ok:
        return jsonify({"error": error}), 400

    return jsonify({
        "ok": True,
        "message": "Contraseña actualizada. Ya puedes iniciar sesión.",
    })


@auth_bp.get("/me")
@token_required
def me():
    user = get_current_user_dict()
    if not user:
        return jsonify({"error": "Usuario no encontrado"}), 404
    return jsonify({"user": user})
