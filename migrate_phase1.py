from app.db.schema_guard import ensure_schema


if __name__ == "__main__":
    ensure_schema()
    print("Schema migration check complete. Existing financial records were preserved.")
