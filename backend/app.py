from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv
import os

from backend.db import db
from backend.routes.crawl import crawl_bp
from backend.routes.graph import graph_bp
from backend.routes.health import health_bp
from backend.routes.papers import papers_bp
from backend.routes.rankings import rankings_bp

load_dotenv()


def create_app() -> Flask:
    app = Flask(__name__)

    _project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    _default_db = f"sqlite:///{os.path.join(_project_root, 'papertrail.db')}"
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", _default_db)
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)

    # Import models so SQLAlchemy registers their metadata before create_all()
    import backend.models  # noqa: F401

    with app.app_context():
        db.create_all()

    CORS(app)

    app.register_blueprint(health_bp, url_prefix="/api/v1")
    app.register_blueprint(papers_bp, url_prefix="/api/v1")
    app.register_blueprint(crawl_bp, url_prefix="/api/v1")
    app.register_blueprint(graph_bp, url_prefix="/api/v1")
    app.register_blueprint(rankings_bp, url_prefix="/api/v1")

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(port=5001, debug=os.getenv("FLASK_DEBUG", "false").lower() == "true")
