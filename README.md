# Face Recognition Attendance System

A web-based attendance management system that uses classical computer vision (Haar Cascade + LBPH) to automatically mark student attendance via face recognition through a live webcam feed.

**Course:** Image Processing and Computer Vision (CT-467) — NED University of Engineering and Technology  
**Student:** Sajeel Tariq (CTAI-22029) — Batch 2022

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI (Python) |
| Face Detection | Haar Cascade Classifier (OpenCV) |
| Face Recognition | LBPH Face Recognizer (OpenCV) |
| Database | SQLite + SQLAlchemy |
| Frontend | Jinja2 Templates + Bootstrap 5 |
| Auth | JWT tokens + bcrypt |

---

## Setup & Run

**Requirements:** Python 3.10+ (tested on 3.14), Windows/Linux/Mac

```bash
# 1. Create virtual environment
python -m venv myenv

# 2. Activate it
# Windows:
myenv\Scripts\activate
# Linux/Mac:
source myenv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the server
python run.py
```

Open your browser at: **http://127.0.0.1:8000**

Default admin credentials: `admin@attendance.com` / `admin123`

---

## Workflow

### Step 1 — Admin Setup
1. Log in as admin
2. Go to **Courses** → Add courses (e.g., CT-467, Image Processing)
3. Go to **Teachers** → Add teacher accounts
4. Go to **Courses** → Assign teachers to courses with section
5. Go to **Students** → Add student accounts (enroll them in courses)

### Step 2 — Face Registration
1. Go to **Students** → Click the **Face** button next to a student
2. Capture 10+ webcam samples OR upload photos
3. After registering all students, click **Train Face Model**

### Step 3 — Take Attendance (Teacher)
1. Teacher logs in → sees assigned courses
2. Click **Take Attendance** for a course
3. Click **Start** → webcam scans faces every 2 seconds
4. Recognized students are automatically marked present
5. Click **Stop** when done

### Step 4 — View Attendance (Student)
1. Student logs in → sees attendance % per course
2. Progress bars show present/absent/total with color coding

---

## IPCV Pipeline

```
Input Frame
    │
    ▼
Face Detection (Haar Cascade)
    │  scaleFactor=1.1, minNeighbors=5
    ▼
Grayscale + Resize (100×100)
    │
    ▼
LBP Feature Extraction
    │  8-bit binary encoding per pixel
    ▼
LBPH Histogram (8×8 grid → concatenated)
    │
    ▼
Chi-squared Distance Matching
    │  threshold = 85.0
    ▼
Identity Output
```

---

## Project Structure

```
face-attendance/
├── app/
│   ├── main.py            # FastAPI app entry point
│   ├── database.py        # SQLAlchemy engine + session
│   ├── models.py          # DB models (User, Student, Course, Attendance...)
│   ├── auth.py            # JWT auth + bcrypt password hashing
│   ├── face_engine.py     # IPCV pipeline (detection + LBPH recognition)
│   └── routers/
│       ├── admin.py       # Admin CRUD routes
│       ├── teacher.py     # Teacher dashboard + attendance
│       ├── student.py     # Student portal
│       └── api.py         # JSON API for webcam recognition
├── templates/             # Jinja2 HTML templates
├── static/                # CSS + JS
├── face_data/
│   ├── images/            # Stored face samples per student
│   └── lbph_model.yml     # Trained LBPH model
├── requirements.txt
└── run.py
```
