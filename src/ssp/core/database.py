import os
from sqlmodel import SQLModel, create_engine
from ssp.core.config import settings

# Parse the connection string
db_url = settings.DATABASE_URL
if db_url.startswith("sqlite:///"):
    db_path = db_url.replace("sqlite:///", "")
    # Ensure directory exists
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

engine = create_engine(db_url, echo=False)

def init_db():
    from ssp.core import models # Ensure models are loaded
    SQLModel.metadata.create_all(engine)
