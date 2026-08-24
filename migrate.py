from sqlalchemy import text
from ssp.core.database import engine

with engine.connect() as conn:
    try:
        conn.execute(text('ALTER TABLE candidate ADD COLUMN timestamp_confidence VARCHAR;'))
        conn.commit()
        print("Migration successful")
    except Exception as e:
        print(e)
