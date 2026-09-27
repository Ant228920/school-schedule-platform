from fastapi import FastAPI
from sqlalchemy import text
from src.core.database import SessionLocal

app = FastAPI()


@app.get("/health")
def health_check():
    try:
        db = SessionLocal()
        result = db.execute(text("SELECT 1")).scalar()
        db.close()
        print("\n" + "=" * 30)
        print(f"База успішно відповіла! Результат: {result}")
        print("=" * 30 + "\n")

        return {"status": "ok", "db_result": result}

    except Exception as e:
        # Виводимо текст помилки в термінал
        print("\n" + "!" * 30)
        print(f"ПОМИЛКА ПІДКЛЮЧЕННЯ ДО БД: {e}")
        print("!" * 30 + "\n")

        return {"status": "database_error", "details": str(e)}


@app.get("/ping")
def ping():
    return {"status": "alive"}
