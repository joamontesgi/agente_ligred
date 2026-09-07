from datetime import datetime, timedelta, timezone
from functools import wraps

import jwt
from flask import current_app, jsonify, request

from auth import user_to_dict
from database import get_session
from models import User


def create_token(user: dict) -> str:
    payload = {
        "sub": str(user["id"]),
        "email": user["email"],
        "nombre": user["nombre"],
        "role": user["role"],
        "exp": datetime.now(timezone.utc)
        + timedelta(hours=current_app.config["JWT_EXPIRY_HOURS"]),
    }
    token = jwt.encode(
        payload,
        current_app.config["JWT_SECRET"],
        algorithm="HS256",
    )
    return token if isinstance(token, str) else token.decode("utf-8")


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return jsonify({"error": "Token requerido"}), 401

        token = auth_header.split(" ", 1)[1]
        try:
            payload = jwt.decode(
                token,
                current_app.config["JWT_SECRET"],
                algorithms=["HS256"],
            )
            payload["sub"] = int(payload["sub"])
            request.current_user = payload
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expirado"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Token inválido"}), 401

        return f(*args, **kwargs)

    return decorated


def role_required(role):
    def decorator(f):
        @wraps(f)
        @token_required
        def decorated(*args, **kwargs):
            if request.current_user.get("role") != role:
                return jsonify({"error": "No autorizado"}), 403
            return f(*args, **kwargs)

        return decorated

    return decorator


def get_current_user_dict():
    session = get_session()
    try:
        user = session.query(User).filter(User.id == request.current_user["sub"]).first()
        if not user:
            return None
        return user_to_dict(user)
    finally:
        session.close()
