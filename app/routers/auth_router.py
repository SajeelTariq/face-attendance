from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from ..database import get_db
from ..auth import verify_password, create_access_token
from .. import models

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "error": None})


@router.post("/login")
def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user or not verify_password(password, user.password_hash):
        return templates.TemplateResponse(
            "login.html", {"request": request, "error": "Invalid email or password"}
        )

    token = create_access_token(user.id, user.role)
    redirect_map = {"admin": "/admin/dashboard", "teacher": "/teacher/dashboard", "student": "/student/dashboard"}
    response = RedirectResponse(url=redirect_map.get(user.role, "/login"), status_code=302)
    response.set_cookie("access_token", token, httponly=True, max_age=28800)
    return response


@router.get("/logout")
def logout():
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie("access_token")
    return response
