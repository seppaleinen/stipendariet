import os

from sqlalchemy import create_engine, inspect

database_url = os.getenv("DATABASE_URL")
if not database_url:
    # Try to find it in settings or other places if needed, but usually it's in env
    print("DATABASE_URL not found")
    exit(1)

engine = create_engine(database_url)
inspector = inspect(engine)

print("Columns in 'profiles' table:")
columns = inspector.get_columns('profiles')
for column in columns:
    print(f"- {column['name']} ({column['type']})")

print("\nAlembic versions:")
try:
    with engine.connect() as conn:
        from sqlalchemy import text
        result = conn.execute(text("SELECT version_num FROM alembic_version"))
        for row in result:
            print(f"- {row[0]}")
except Exception as e:
    print(f"Error fetching alembic version: {e}")
