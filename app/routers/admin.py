from fastapi import APIRouter, Request, Form, Depends, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import numpy as np
import cv2

from ..database import get_db
from ..auth import require_role, hash_password  # hash_password now uses bcrypt directly
from .. import models, face_engine

router = APIRouter(prefix="/admin")
templates = Jinja2Templates(directory="templates")


def get_admin(request: Request, db: Session = Depends(get_db)):
    user = require_role(request, db, "admin")
    if not user:
        return None
    return user


# ── Dashboard ─────────────────────────────────────────────────────────────────

@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    admin = get_admin(request, db)
    if not admin:
        return RedirectResponse("/login", 302)

    stats = {
        "students": db.query(models.Student).count(),
        "teachers": db.query(models.Teacher).count(),
        "courses": db.query(models.Course).count(),
        "attendance_today": db.query(models.Attendance).filter(
            models.Attendance.date == __import__("datetime").date.today()
        ).count(),
    }
    return templates.TemplateResponse("admin/dashboard.html", {"request": request, "user": admin, "stats": stats})


# ── Students ──────────────────────────────────────────────────────────────────

@router.get("/students", response_class=HTMLResponse)
def students_list(request: Request, db: Session = Depends(get_db)):
    admin = get_admin(request, db)
    if not admin:
        return RedirectResponse("/login", 302)
    students = db.query(models.Student).join(models.User).all()
    courses = db.query(models.Course).all()
    return templates.TemplateResponse("admin/students.html", {
        "request": request, "user": admin, "students": students, "courses": courses
    })


@router.get("/students/add", response_class=HTMLResponse)
def add_student_page(request: Request, db: Session = Depends(get_db)):
    admin = get_admin(request, db)
    if not admin:
        return RedirectResponse("/login", 302)
    courses = db.query(models.Course).all()
    return templates.TemplateResponse("admin/add_student.html", {
        "request": request, "user": admin, "courses": courses, "error": None, "success": None
    })


@router.post("/students/add")
async def add_student(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    roll_no: str = Form(...),
    batch: str = Form(...),
    section: str = Form(...),
    course_ids: list[int] = Form(default=[]),
    db: Session = Depends(get_db),
):
    admin = get_admin(request, db)
    if not admin:
        return RedirectResponse("/login", 302)

    courses = db.query(models.Course).all()

    if db.query(models.User).filter(models.User.email == email).first():
        return templates.TemplateResponse("admin/add_student.html", {
            "request": request, "user": admin, "courses": courses,
            "error": "Email already exists", "success": None
        })
    if db.query(models.Student).filter(models.Student.roll_no == roll_no).first():
        return templates.TemplateResponse("admin/add_student.html", {
            "request": request, "user": admin, "courses": courses,
            "error": "Roll number already exists", "success": None
        })

    # assign next available face_label
    max_label = db.query(models.Student).count()
    face_label = max_label + 1

    user = models.User(name=name, email=email, password_hash=hash_password(password), role="student")
    db.add(user)
    db.flush()

    student = models.Student(
        user_id=user.id, roll_no=roll_no, batch=batch, section=section, face_label=face_label
    )
    db.add(student)
    db.flush()

    for cid in course_ids:
        db.add(models.Enrollment(student_id=student.id, course_id=cid))

    db.commit()
    return templates.TemplateResponse("admin/add_student.html", {
        "request": request, "user": admin, "courses": courses,
        "error": None, "success": f"Student '{name}' added. Now register their face."
    })


@router.post("/students/{student_id}/delete")
def delete_student(student_id: int, request: Request, db: Session = Depends(get_db)):
    admin = get_admin(request, db)
    if not admin:
        return RedirectResponse("/login", 302)
    student = db.query(models.Student).filter(models.Student.id == student_id).first()
    if student:
        db.query(models.Enrollment).filter(models.Enrollment.student_id == student_id).delete()
        db.query(models.Attendance).filter(models.Attendance.student_id == student_id).delete()
        db.delete(student.user)
        db.delete(student)
        db.commit()
    return RedirectResponse("/admin/students", 302)


# ── Face Registration ─────────────────────────────────────────────────────────

@router.get("/students/{student_id}/face", response_class=HTMLResponse)
def face_register_page(student_id: int, request: Request, db: Session = Depends(get_db)):
    admin = get_admin(request, db)
    if not admin:
        return RedirectResponse("/login", 302)
    student = db.query(models.Student).filter(models.Student.id == student_id).first()
    if not student:
        return RedirectResponse("/admin/students", 302)
    sample_count = face_engine.count_samples(student.face_label)
    return templates.TemplateResponse("admin/face_register.html", {
        "request": request, "user": admin, "student": student, "sample_count": sample_count
    })


@router.post("/students/{student_id}/face/upload")
async def upload_face(
    student_id: int,
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    admin = get_admin(request, db)
    if not admin:
        return {"error": "Unauthorized"}
    student = db.query(models.Student).filter(models.Student.id == student_id).first()
    if not student:
        return {"error": "Student not found"}

    data = await file.read()
    arr = np.frombuffer(data, np.uint8)
    image = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if image is None:
        return {"error": "Invalid image"}

    sample_id = face_engine.count_samples(student.face_label) + 1
    success = face_engine.save_face_sample(image, student.face_label, sample_id)
    if not success:
        return {"error": "No face detected in image"}

    count = face_engine.count_samples(student.face_label)
    return {"success": True, "sample_count": count}


@router.post("/train-model")
def train_model(request: Request, db: Session = Depends(get_db)):
    admin = get_admin(request, db)
    if not admin:
        return RedirectResponse("/login", 302)
    success = face_engine.train_model()
    msg = "trained" if success else "no_data"
    return RedirectResponse(f"/admin/students?trained={msg}", 302)


# ── Courses ───────────────────────────────────────────────────────────────────

@router.get("/courses", response_class=HTMLResponse)
def courses_list(request: Request, db: Session = Depends(get_db)):
    admin = get_admin(request, db)
    if not admin:
        return RedirectResponse("/login", 302)
    courses = db.query(models.Course).all()
    teachers = db.query(models.Teacher).join(models.User).all()
    assignments = db.query(models.TeacherCourse).all()
    return templates.TemplateResponse("admin/courses.html", {
        "request": request, "user": admin, "courses": courses,
        "teachers": teachers, "assignments": assignments
    })


@router.post("/courses/add")
def add_course(
    request: Request,
    code: str = Form(...),
    name: str = Form(...),
    db: Session = Depends(get_db),
):
    admin = get_admin(request, db)
    if not admin:
        return RedirectResponse("/login", 302)
    if not db.query(models.Course).filter(models.Course.code == code).first():
        db.add(models.Course(code=code, name=name))
        db.commit()
    return RedirectResponse("/admin/courses", 302)


@router.post("/courses/assign")
def assign_teacher(
    request: Request,
    teacher_id: int = Form(...),
    course_id: int = Form(...),
    section: str = Form(...),
    db: Session = Depends(get_db),
):
    admin = get_admin(request, db)
    if not admin:
        return RedirectResponse("/login", 302)
    exists = db.query(models.TeacherCourse).filter(
        models.TeacherCourse.teacher_id == teacher_id,
        models.TeacherCourse.course_id == course_id,
        models.TeacherCourse.section == section,
    ).first()
    if not exists:
        db.add(models.TeacherCourse(teacher_id=teacher_id, course_id=course_id, section=section))
        db.commit()
    return RedirectResponse("/admin/courses", 302)


# ── Teachers ──────────────────────────────────────────────────────────────────

@router.get("/teachers", response_class=HTMLResponse)
def teachers_list(request: Request, db: Session = Depends(get_db)):
    admin = get_admin(request, db)
    if not admin:
        return RedirectResponse("/login", 302)
    teachers = db.query(models.Teacher).join(models.User).all()
    return templates.TemplateResponse("admin/teachers.html", {
        "request": request, "user": admin, "teachers": teachers
    })


@router.post("/teachers/add")
def add_teacher(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    admin = get_admin(request, db)
    if not admin:
        return RedirectResponse("/login", 302)
    if not db.query(models.User).filter(models.User.email == email).first():
        user = models.User(name=name, email=email, password_hash=hash_password(password), role="teacher")
        db.add(user)
        db.flush()
        db.add(models.Teacher(user_id=user.id))
        db.commit()
    return RedirectResponse("/admin/teachers", 302)


@router.post("/teachers/{teacher_id}/delete")
def delete_teacher(teacher_id: int, request: Request, db: Session = Depends(get_db)):
    admin = get_admin(request, db)
    if not admin:
        return RedirectResponse("/login", 302)
    teacher = db.query(models.Teacher).filter(models.Teacher.id == teacher_id).first()
    if teacher:
        db.query(models.TeacherCourse).filter(models.TeacherCourse.teacher_id == teacher_id).delete()
        db.delete(teacher.user)
        db.delete(teacher)
        db.commit()
    return RedirectResponse("/admin/teachers", 302)


# ── Enrollment ────────────────────────────────────────────────────────────────

@router.post("/students/{student_id}/enroll")
def enroll_student(
    student_id: int,
    request: Request,
    course_id: int = Form(...),
    db: Session = Depends(get_db),
):
    admin = get_admin(request, db)
    if not admin:
        return RedirectResponse("/login", 302)
    exists = db.query(models.Enrollment).filter(
        models.Enrollment.student_id == student_id,
        models.Enrollment.course_id == course_id,
    ).first()
    if not exists:
        db.add(models.Enrollment(student_id=student_id, course_id=course_id))
        db.commit()
    return RedirectResponse("/admin/students", 302)
