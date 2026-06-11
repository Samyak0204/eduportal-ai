import os
from pymongo import MongoClient
from dotenv import load_dotenv
import bcrypt
from datetime import datetime,timezone

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB = os.getenv("MONGO_DB", "portal_db")

_client = None

def get_db():
    global _client
    if _client is None:
        _client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    return _client[MONGO_DB]


# ── Users ──────────────────────────────────────────────────────────────────

def seed_default_users():
    db = get_db()
    if db.users.count_documents({}) == 0:
        db.users.insert_many([
            {
                "username": "admin",
                "password": bcrypt.hashpw(b"admin123", bcrypt.gensalt()),
                "role": "admin",
                "name": "Administrator",
                "created_at": datetime.now(timezone.utc),
            },
            {
                "username": "student1",
                "password": bcrypt.hashpw(b"student123", bcrypt.gensalt()),
                "role": "student",
                "name": "Student One",
                "created_at": datetime.now(timezone.utc),
            },
        ])


def verify_user(username: str, password: str):
    db = get_db()
    user = db.users.find_one({"username": username})
    if user and bcrypt.checkpw(password.encode(), user["password"]):
        return {"username": user["username"], "role": user["role"], "name": user["name"]}
    return None


def create_user(username: str, password: str, role: str, name: str):
    db = get_db()
    if db.users.find_one({"username": username}):
        return False, "Username already exists"
    db.users.insert_one({
        "username": username,
        "password": bcrypt.hashpw(password.encode(), bcrypt.gensalt()),
        "role": role,
        "name": name,
        "created_at": datetime.now(timezone.utc),
    })
    return True, "User created"


def get_all_students():
    db = get_db()
    return list(db.users.find({"role": "student"}, {"password": 0}))


# ── Questions ──────────────────────────────────────────────────────────────

def insert_question(question_doc: dict):
    db = get_db()
    result = db.questions.insert_one(question_doc)
    return str(result.inserted_id)


def get_all_questions():
    db = get_db()
    return list(db.questions.find().sort("created_at", -1))


def get_question_by_id(qid: str):
    from bson import ObjectId
    db = get_db()
    return db.questions.find_one({"_id": ObjectId(qid)})


def delete_question(qid: str):
    from bson import ObjectId
    db = get_db()
    db.questions.delete_one({"_id": ObjectId(qid)})


def update_question(qid: str, question_doc: dict):
    from bson import ObjectId
    db = get_db()
    db.questions.update_one({"_id": ObjectId(qid)}, {"$set": question_doc})


# ── Submissions ────────────────────────────────────────────────────────────

def insert_submission(submission_doc: dict):
    db = get_db()
    result = db.submissions.insert_one(submission_doc)
    return str(result.inserted_id)


def get_submissions_by_student(username: str):
    db = get_db()
    return list(db.submissions.find({"student_username": username}).sort("submitted_at", -1))


def get_all_submissions():
    db = get_db()
    return list(db.submissions.find().sort("submitted_at", -1))


def submission_exists(student_username: str, question_id: str):
    db = get_db()
    return db.submissions.find_one({
        "student_username": student_username,
        "question_id": question_id
    }) is not None


# ── Active Exam State Persistence ──────────────────────────────────────────

def save_active_exam_state(username: str, state_doc: dict):
    db = get_db()
    db.active_exams.update_one(
        {"username": username},
        {"$set": state_doc},
        upsert=True
    )

def get_active_exam_state(username: str):
    db = get_db()
    return db.active_exams.find_one({"username": username})

def delete_active_exam_state(username: str):
    db = get_db()
    db.active_exams.delete_one({"username": username})
