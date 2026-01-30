from setup_db import engine, Base

# IMPORTANT: import models so Base knows about them
from services import models  # noqa: F401

def main():
    print("🔄 Creating tables from SQLAlchemy models...")
    Base.metadata.create_all(bind=engine)
    print("✅ Tables ready.")

if __name__ == "__main__":
    main()
