import sys
import os

print("Starting debug script...", flush=True)
print(f"Python executable: {sys.executable}", flush=True)
print(f"CWD: {os.getcwd()}", flush=True)

try:
    print("Importing sqlmodel...", flush=True)
    from sqlmodel import SQLModel, create_engine, Session, select
    print("sqlmodel imported.", flush=True)
except Exception as e:
    print(f"Failed to import sqlmodel: {e}", flush=True)
    sys.exit(1)

try:
    print("Importing app modules...", flush=True)
    from app.modules.finance.models import Transaction
    print("app modules imported.", flush=True)
except Exception as e:
    print(f"Failed to import app modules: {e}", flush=True)
    sys.exit(1)

print("Creating engine...", flush=True)
try:
    engine = create_engine("sqlite:///:memory:", echo=True)
    print("Engine created.", flush=True)
    
    print("Creating tables...", flush=True)
    SQLModel.metadata.create_all(engine)
    print("Tables created.", flush=True)
except Exception as e:
    print(f"Database error: {e}", flush=True)
    sys.exit(1)

print("Debug script finished successfully.", flush=True)
