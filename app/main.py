from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .database import engine
from . import models
from .routers import auth_router, admin, teacher, student, api
from .auth import hash_password
from .database import SessionLocal

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Face Attendance System")

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

app.include_router(auth_router.router)
app.include_router(admin.router)
app.include_router(teacher.router)
app.include_router(student.router)
app.include_router(api.router)


@app.get("/")
def root():
    return RedirectResponse("/login", 302)


def create_default_admin():
    """Create default admin account on first run."""
    db = SessionLocal()
    try:
        if not db.query(models.User).filter(models.User.role == "admin").first():
            admin_user = models.User(
                name="Admin",
                email="admin@attendance.com",
                password_hash=hash_password("admin123"),
                role="admin",
            )
            db.add(admin_user)
            db.commit()
            print("Default admin created -- email: admin@attendance.com  password: admin123")
    finally:
        db.close()


create_default_admin()
