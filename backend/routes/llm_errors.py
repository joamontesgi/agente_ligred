from flask import jsonify


def llm_error_response(exc: Exception, status: int = 503):
    return jsonify({"error": str(exc)}), status
