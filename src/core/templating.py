from pathlib import Path

from fastapi.templating import Jinja2Templates

BASE_DIR = Path(__file__).resolve().parent.parent  # папка src
templates = Jinja2Templates(directory=BASE_DIR / "templates")
templates.env.globals["WEEKDAYS"] = [
    "Понеділок",
    "Вівторок",
    "Середа",
    "Четвер",
    "П'ятниця",
]
