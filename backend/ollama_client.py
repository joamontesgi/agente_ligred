import json
import urllib.error
import urllib.request

from config import Config


def list_ollama_models() -> tuple[list[dict], str | None]:
    url = f"{Config.OLLAMA_BASE_URL.rstrip('/')}/api/tags"

    try:
        with urllib.request.urlopen(url, timeout=8) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        return [], f"No se pudo conectar con Ollama en {Config.OLLAMA_BASE_URL}: {exc}"
    except json.JSONDecodeError:
        return [], "Respuesta inválida del servidor Ollama."

    models = []
    for item in payload.get("models", []):
        name = item.get("name")
        if not name:
            continue
        models.append({
            "name": name,
            "size": item.get("size"),
            "modified_at": item.get("modified_at"),
        })

    models.sort(key=lambda model: model["name"].lower())
    return models, None


def filter_llama_models(models: list[dict]) -> list[dict]:
    return [
        model for model in models
        if "llama" in model["name"].lower()
    ]


def resolve_model_name(requested: str, models: list[dict]) -> str | None:
    if not requested:
        return None

    requested = requested.strip()
    names = [model["name"] for model in models]

    if requested in names:
        return requested

    requested_base = requested.split(":")[0]
    matches = [name for name in names if name.split(":")[0] == requested_base]
    if len(matches) == 1:
        return matches[0]

    latest = f"{requested_base}:latest"
    if latest in names:
        return latest

    return None


def is_model_available(model_name: str, models: list[dict] | None = None) -> bool:
    if not model_name:
        return True

    if models is None:
        models, _ = list_ollama_models()

    return resolve_model_name(model_name, models) is not None


def validate_llm_model(model_name: str) -> tuple[bool, str | None, str | None]:
    model_name = (model_name or "").strip()
    if not model_name:
        return True, None, None

    models, connection_error = list_ollama_models()
    if connection_error:
        return False, connection_error, None

    resolved = resolve_model_name(model_name, models)
    if resolved:
        return True, None, resolved

    base = model_name.split(":")[0]
    return False, (
        f"El modelo «{model_name}» no está descargado en Ollama. "
        f"Descárgalo con: ollama pull {base}"
    ), None


def format_llm_runtime_error(exc: Exception, model_name: str) -> str:
    message = str(exc).lower()

    if any(token in message for token in ("not found", "404", "does not exist", "model '" )):
        base = model_name.split(":")[0]
        return (
            f"El modelo «{model_name}» no está disponible en Ollama. "
            f"Descárgalo con: ollama pull {base}"
        )

    if any(token in message for token in ("connection refused", "failed to establish", "connect")):
        return (
            "No se pudo conectar con Ollama. "
            f"Verifica que esté en ejecución en {Config.OLLAMA_BASE_URL}."
        )

    return f"Error al usar el modelo «{model_name}»: {exc}"
