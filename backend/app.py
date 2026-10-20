from flask import Flask, jsonify
from flask_cors import CORS

from config import Config
from database import check_db_connection, init_db
from routes.auth import auth_bp
from routes.evaluations import evaluations_bp
from routes.labs import labs_bp
from routes.metrics import metrics_bp
from routes.models import models_bp
from routes.practice import practice_bp
from routes.subjects import subjects_bp
from routes.wordclouds import wordclouds_bp


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    cors_origins = app.config["CORS_ORIGINS"]
    if cors_origins == "*":
        CORS(app, resources={r"/api/*": {"origins": "*"}})
    else:
        CORS(app, origins=cors_origins, supports_credentials=True)

    init_db()

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(subjects_bp, url_prefix="/api/subjects")
    app.register_blueprint(practice_bp, url_prefix="/api/practice")
    app.register_blueprint(evaluations_bp, url_prefix="/api/evaluations")
    app.register_blueprint(labs_bp, url_prefix="/api/labs")
    app.register_blueprint(metrics_bp, url_prefix="/api/metrics")
    app.register_blueprint(models_bp, url_prefix="/api/models")
    app.register_blueprint(wordclouds_bp, url_prefix="/api/wordclouds")

    @app.get("/api/health")
    def health():
        db_ok, db_info = check_db_connection()
        payload = {
            "status": "ok" if db_ok else "degraded",
            "database": {
                "engine": Config.DB_ENGINE,
                "connected": db_ok,
            },
        }
        if not db_ok:
            payload["database"]["error"] = db_info
        return jsonify(payload)

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
