import os
import logging
from flask import Flask, send_from_directory
from flask_cors import CORS
from app.extensions import db, socketio

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_app():
    app = Flask(__name__)
    CORS(app,
         supports_credentials=True,
         resources={r"/*": {"origins": "*"}},
         allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
         methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    )

    # Fix CORB: Ensure all responses have correct Content-Type and CORS headers
    @app.after_request
    def add_cors_headers(response):
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    # ---------------- CONFIG ----------------
    app.config.from_object("app.config.Config")
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///cheating.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # ---------------- INIT EXTENSIONS ----------------
    db.init_app(app)

    socketio.init_app(
        app,
        cors_allowed_origins="*",
        async_mode='threading',  # FIX: Explicitly set to threading
        ping_timeout=60,
        ping_interval=25,
        max_http_buffer_size=100000000,
        logger=False,
        engineio_logger=False
    )

    # ---------------- SERVE EVIDENCE IMAGES ----------------
    @app.route("/evidence/<session>/<filename>")
    def serve_evidence(session, filename):
        return send_from_directory(
            f"backend/evidence/{session}",
            filename
        )

    # ---------------- REGISTER BLUEPRINTS ----------------
    from app.routes.health_routes import health_bp
    from app.routes.video_routes import video_bp
    from app.routes.audio_routes import audio_bp
    from app.routes.fusion_routes import fusion_bp
    from app.routes.ai_detection_routes import ai_bp
    from app.routes.dashboard_routes import dashboard_bp
    from app.routes.timeline_routes import timeline_bp
    from app.routes.session_routes import session_bp

    app.register_blueprint(health_bp)
    app.register_blueprint(video_bp)
    app.register_blueprint(audio_bp)
    app.register_blueprint(fusion_bp)
    app.register_blueprint(ai_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(timeline_bp)
    app.register_blueprint(session_bp)

    # ---------------- SOCKET HANDLERS ----------------
    # MUST be imported AFTER socketio init
    from app.socket_handlers import session_socket, audio_socket
    logger.info("✅ App initialized successfully")
    # ---------------- ROOT ----------------
    @app.route("/")
    def index():
        return {
            "status": "Backend is running",
            "message": "AI Proctoring API"
        }

    # ---------------- CREATE DB ----------------
    with app.app_context():
        db.create_all()

    return app