from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import date

from ..database import get_db
from ..auth import require_role
from .. import models

router = APIRouter(prefix="/teacher")
templates = Jinja2Templates(directory="templates")


def get_teacher(request: Request, db: Session):
    user = require_role(request, db, "teacher")
    if not user:
        return None, None
    teacher = db.query(models.Teacher).filter(models.Teacher.user_id == user.id).first()
    return user, teacher


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    user, teacher = get_teacher(request, db)
    if not user:
        return RedirectResponse("/login", 302)

    assignments = db.query(models.TeacherCourse).filter(
        models.TeacherCourse.teacher_id == teacher.id
    ).all()

    return templates.TemplateResponse("teacher/dashboard.html", {
        "request": request, "user": user, "assignments": assignments, "today": date.today()
    })


@router.get("/attendance/{assignment_id}", response_class=HTMLResponse)
def attendance_page(assignment_id: int, request: Request, db: Session = Depends(get_db)):
    user, teacher = get_teacher(request, db)
    if not user:
        return RedirectResponse("/login", 302)

    assignment = db.query(models.TeacherCourse).filter(
        models.TeacherCourse.id == assignment_id,
        models.TeacherCourse.teacher_id == teacher.id,
    ).first()
    if not assignment:
        return RedirectResponse("/teacher/dashboard", 302)

    # students enrolled in this course
    enrollments = db.query(models.Enrollment).filter(
        models.Enrollment.course_id == assignment.course_id
    ).all()

    # today's attendance for this course
    today_records = db.query(models.Attendance).filter(
        models.Attendance.course_id == assignment.course_id,
        models.Attendance.date == date.today(),
    ).all()
    marked_ids = {r.student_id for r in today_records}

    return templates.TemplateResponse("teacher/attendance.html", {
        "request": request,
        "user": user,
        "assignment": assignment,
        "enrollments": enrollments,
        "marked_ids": marked_ids,
        "today": date.today(),
    })


@router.get("/attendance/{assignment_id}/report", response_class=HTMLResponse)
def attendance_report(assignment_id: int, request: Request, db: Session = Depends(get_db)):
    user, teacher = get_teacher(request, db)
    if not user:
        return RedirectResponse("/login", 302)

    assignment = db.query(models.TeacherCourse).filter(
        models.TeacherCourse.id == assignment_id,
        models.TeacherCourse.teacher_id == teacher.id,
    ).first()
    if not assignment:
        return RedirectResponse("/teacher/dashboard", 302)

    enrollments = db.query(models.Enrollment).filter(
        models.Enrollment.course_id == assignment.course_id
    ).all()

    report = []
    for enr in enrollments:
        total = db.query(models.Attendance).filter(
            models.Attendance.student_id == enr.student_id,
            models.Attendance.course_id == assignment.course_id,
        ).count()
        present = db.query(models.Attendance).filter(
            models.Attendance.student_id == enr.student_id,
            models.Attendance.course_id == assignment.course_id,
            models.Attendance.status == "present",
        ).count()
        pct = round((present / total * 100) if total > 0 else 0, 1)
        report.append({
            "student": enr.student,
            "total": total,
            "present": present,
            "absent": total - present,
            "percentage": pct,
        })

    return templates.TemplateResponse("teacher/report.html", {
        "request": request, "user": user, "assignment": assignment, "report": report
    })
