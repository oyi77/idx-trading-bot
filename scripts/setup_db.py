"""Database setup — creates all tables."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.models import create_tables


def main():
    print("📦 Setting up database...")
    create_tables()
    print("✅ Database tables created successfully!")


if __name__ == "__main__":
    main()
