from flask import Blueprint, jsonify

from config import Config
from jwt_utils import role_required
from ollama_client import filter_llama_models, list_ollama_models

models_bp = Blueprint("models", __name__)


@models_bp.get("/")
@role_required("teacher")
def get_models():
    models, error = list_ollama_models()
    llama_models = filter_llama_models(models)

    return jsonify({
        "default_model": Config.DEFAULT_LLM_MODEL,
        "models": models,
        "llama_models": llama_models,
        "ollama_url": Config.OLLAMA_BASE_URL,
        "warning": error,
    })
