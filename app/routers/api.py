"""
JSON API endpoints consumed by JavaScript (webcam attendance + face capture).
"""
from fastapi import APIRouter, Request, UploadFile, File, Form, Depends
from sqlalchemy.orm import Session
from datetime import date
import numpy as np
import cv2

from ..database import get_db
from ..auth import get_current_user
from .. import models, face_engine

router = APIRouter(prefix="/api")


@router.post("/recognize")
async def recognize(
    request: Request,
    file: UploadFile = File(...),
    course_id: int = Form(...),
    db: Session = Depends(get_db),
):
    """
    Receive a webcam frame, run face recognition, mark attendance if matched.
    Returns JSON with recognized student info.
    """
    user = get_current_user(request, db)
    if not user or user.role not in ("admin", "teacher"):
        return {"error": "Unauthorized"}

    data = await file.read()
    arr = np.frombuffer(data, np.uint8)
    image = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if image is None:
        return {"error": "Invalid image"}

    label, confidence = face_engine.recognize_face(image)
    if label is None:
        return {"recognized": False, "confidence": confidence}

    student = db.query(models.Student).filter(models.Student.face_label == label).first()
    if not student:
        return {"recognized": False, "confidence": confidence}

    # check student is enrolled in this course
    enrollment = db.query(models.Enrollment).filter(
        models.Enrollment.student_id == student.id,
        models.Enrollment.course_id == course_id,
    ).first()
    if not enrollment:
        return {
            "recognized": True,
            "name": student.user.name,
            "roll_no": student.roll_no,
            "enrolled": False,
            "message": "Student not enrolled in this course",
        }

    # check if already marked today
    existing = db.query(models.Attendance).filter(
        models.Attendance.student_id == student.id,
        models.Attendance.course_id == course_id,
        models.Attendance.date == date.today(),
    ).first()

    if existing:
        return {
            "recognized": True,
            "name": student.user.name,
            "roll_no": student.roll_no,
            "enrolled": True,
            "already_marked": True,
            "status": existing.status,
        }

    # mark attendance
    attendance = models.Attendance(
        student_id=student.id,
        course_id=course_id,
        date=date.today(),
        status="present",
    )
    db.add(attendance)
    db.commit()

    return {
        "recognized": True,
        "name": student.user.name,
        "roll_no": student.roll_no,
        "enrolled": True,
        "already_marked": False,
        "marked": True,
        "confidence": confidence,
    }


@router.post("/capture-face")
async def capture_face(
    request: Request,
    student_id: int = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Receive a webcam frame and save it as a face sample for a student."""
    user = get_current_user(request, db)
    if not user or user.role != "admin":
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
        return {"success": False, "error": "No face detected"}

    count = face_engine.count_samples(student.face_label)
    return {"success": True, "sample_count": count}


@router.get("/attendance/today/{course_id}")
def today_attendance(course_id: int, request: Request, db: Session = Depends(get_db)):
    """Return list of students marked present today for a course."""
    user = get_current_user(request, db)
    if not user:
        return {"error": "Unauthorized"}

    records = db.query(models.Attendance).filter(
        models.Attendance.course_id == course_id,
        models.Attendance.date == date.today(),
        models.Attendance.status == "present",
    ).all()

    return {
        "marked": [
            {"name": r.student.user.name, "roll_no": r.student.roll_no, "marked_at": str(r.marked_at)}
            for r in records
        ]
    }
