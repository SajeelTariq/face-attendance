from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, default="student")  # admin / teacher / student

    student = relationship("Student", back_populates="user", uselist=False)
    teacher = relationship("Teacher", back_populates="user", uselist=False)


class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    roll_no = Column(String, unique=True)
    batch = Column(String)
    section = Column(String)
    face_label = Column(Integer, unique=True, nullable=True)  # LBPH numeric label

    user = relationship("User", back_populates="student")
    enrollments = relationship("Enrollment", back_populates="student")
    attendances = relationship("Attendance", back_populates="student")


class Teacher(Base):
    __tablename__ = "teachers"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)

    user = relationship("User", back_populates="teacher")
    assignments = relationship("TeacherCourse", back_populates="teacher")


class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True)
    code = Column(String, unique=True)
    name = Column(String)

    enrollments = relationship("Enrollment", back_populates="course")
    assignments = relationship("TeacherCourse", back_populates="course")
    attendances = relationship("Attendance", back_populates="course")


class Enrollment(Base):
    __tablename__ = "enrollments"

    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey("students.id"))
    course_id = Column(Integer, ForeignKey("courses.id"))

    student = relationship("Student", back_populates="enrollments")
    course = relationship("Course", back_populates="enrollments")


class TeacherCourse(Base):
    __tablename__ = "teacher_courses"

    id = Column(Integer, primary_key=True)
    teacher_id = Column(Integer, ForeignKey("teachers.id"))
    course_id = Column(Integer, ForeignKey("courses.id"))
    section = Column(String)

    teacher = relationship("Teacher", back_populates="assignments")
    course = relationship("Course", back_populates="assignments")


class Attendance(Base):
    __tablename__ = "attendances"

    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey("students.id"))
    course_id = Column(Integer, ForeignKey("courses.id"))
    date = Column(Date, nullable=False)
    status = Column(String, default="present")  # present / absent
    marked_at = Column(DateTime, default=datetime.utcnow)

    student = relationship("Student", back_populates="attendances")
    course = relationship("Course", back_populates="attendances")
