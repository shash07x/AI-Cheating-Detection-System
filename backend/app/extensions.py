import threading
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO
from flask_cors import CORS

db = SQLAlchemy()
socketio = SocketIO(cors_allowed_origins="*")
global_pytorch_lock = threading.Lock()

def init_extensions(app):
    db.init_app(app)
    socketio.init_app(app)
    CORS(app)