from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from ..database import get_db
from ..auth import require_role
from .. import models

router = APIRouter(prefix="/student")
templates = Jinja2Templates(directory="templates")


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    user = require_role(request, db, "student")
    if not user:
        return RedirectResponse("/login", 302)

    student = db.query(models.Student).filter(models.Student.user_id == user.id).first()
    if not student:
        return RedirectResponse("/login", 302)

    enrollments = db.query(models.Enrollment).filter(
        models.Enrollment.student_id == student.id
    ).all()

    attendance_summary = []
    for enr in enrollments:
        total = db.query(models.Attendance).filter(
            models.Attendance.student_id == student.id,
            models.Attendance.course_id == enr.course_id,
        ).count()
        present = db.query(models.Attendance).filter(
            models.Attendance.student_id == student.id,
            models.Attendance.course_id == enr.course_id,
            models.Attendance.status == "present",
        ).count()
        pct = round((present / total * 100) if total > 0 else 0, 1)
        records = db.query(models.Attendance).filter(
            models.Attendance.student_id == student.id,
            models.Attendance.course_id == enr.course_id,
        ).order_by(models.Attendance.date.desc()).limit(10).all()

        attendance_summary.append({
            "course": enr.course,
            "total": total,
            "present": present,
            "absent": total - present,
            "percentage": pct,
            "records": records,
        })

    return templates.TemplateResponse("student/dashboard.html", {
        "request": request,
        "user": user,
        "student": student,
        "attendance_summary": attendance_summary,
    })
