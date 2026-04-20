"""
Create all database tables. Run once after setting DATABASE_URL in .env.

    python scripts/init_db.py
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend.app import create_app
from backend.db import db


def main() -> None:
    app = create_app()
    with app.app_context():
        db.create_all()
        from sqlalchemy import inspect
        tables = inspect(db.engine).get_table_names()
        print(f"Tables created: {tables}")


if __name__ == "__main__":
    main()
