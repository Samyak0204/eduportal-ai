import os
from pymongo import MongoClient
from dotenv import load_dotenv
import bcrypt
from datetime import datetime, timezone, timedelta
import uuid
import random

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB = os.getenv("MONGO_DB", "portal_db")

_client = None
_indexes_created = False

def get_db():
    global _client, _indexes_created
    if _client is None:
        _client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        
    db = _client[MONGO_DB]
    
    # Connection ping check
    try:
        db.command("ping")
    except Exception:
        # Retry once by recreating client
        _client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        db = _client[MONGO_DB]
        db.command("ping") # If this fails, let the exception propagate
        
    if not _indexes_created:
        try:
            # Ensure indexes for fast lookups and security token validation
            db.exam_sessions.create_index("token", unique=True)
            db.upload_tokens.create_index("token", unique=True)
            # TTL Index to auto-expire upload tokens after their expires_at time
            db.upload_tokens.create_index("expires_at", expireAfterSeconds=0)
            db.otp_codes.create_index("expires_at", expireAfterSeconds=0)
            _indexes_created = True
        except Exception:
            pass # Index creation failure shouldn't crash the entire app if DB is otherwise fine
            
    return db


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


# ── Lockdown Browser Helpers ────────────────────────────────────────────────

def create_exam_session(username: str, question_ids: list, duration_minutes: int = 60) -> str:
    db = get_db()
    token = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=duration_minutes)
    
    db.exam_sessions.insert_one({
        "token": token,
        "student_username": username,
        "question_ids": question_ids,
        "started_at": now,
        "expires_at": expires_at,
        "status": "active",
        "violations": [],
        "last_heartbeat": now
    })
    return token

def verify_exam_token(token: str):
    db = get_db()
    session = db.exam_sessions.find_one({"token": token, "status": "active"})
    if not session:
        return None
    
    # Check if expired
    now = datetime.now(timezone.utc)
    expires_at = session["expires_at"]
    # Handle both offset-aware and offset-naive from pymongo
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
        
    if expires_at < now:
        db.exam_sessions.update_one({"token": token}, {"$set": {"status": "expired"}})
        return None
        
    return session

def heartbeat_session(token: str) -> bool:
    db = get_db()
    now = datetime.now(timezone.utc)
    result = db.exam_sessions.update_one(
        {"token": token, "status": "active"},
        {"$set": {"last_heartbeat": now}}
    )
    return result.modified_count > 0

def log_violation(token: str, violation_type: str, detail: str) -> bool:
    db = get_db()
    now = datetime.now(timezone.utc)
    violation = {
        "type": violation_type,
        "detail": detail,
        "timestamp": now
    }
    result = db.exam_sessions.update_one(
        {"token": token},
        {"$push": {"violations": violation}}
    )
    return result.modified_count > 0

def create_upload_token(student_username: str, question_id: str) -> str:
    db = get_db()
    token = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=5)
    
    db.upload_tokens.insert_one({
        "token": token,
        "student_username": student_username,
        "question_id": question_id,
        "expires_at": expires_at,
        "used": False,
        "image_bytes": None
    })
    return token

def verify_upload_token(token: str):
    db = get_db()
    token_doc = db.upload_tokens.find_one({"token": token, "used": False})
    if not token_doc:
        return None
        
    now = datetime.now(timezone.utc)
    expires_at = token_doc["expires_at"]
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
        
    if expires_at < now:
        return None
        
    return token_doc

def save_token_image(token: str, image_bytes: bytes) -> bool:
    db = get_db()
    result = db.upload_tokens.update_one(
        {"token": token, "used": False},
        {"$set": {"image_bytes": image_bytes, "used": True}}
    )
    return result.modified_count > 0

def check_token_status(token: str) -> dict:
    db = get_db()
    token_doc = db.upload_tokens.find_one({"token": token})
    if not token_doc:
        return {"uploaded": False, "image_bytes": None}
    return {
        "uploaded": token_doc.get("used", False),
        "image_bytes": token_doc.get("image_bytes")
    }

def generate_login_otp(username: str)->str:
    db = get_db()
    code = f"{random.randint(100000,999999)}"

    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=5)

    db.otp_codes.insert_one({
        "username": username,
        "code": code,
        "created_at": now,
        "expires_at": expires_at,
        "used": False
    })

    print(f"[Simulated OTP] Code for @{username}: {code}")

    return code

def verify_login_otp(username: str, code: str) -> bool:
    db=get_db()
    now = datetime.now(timezone.utc)

    otp_doc = db.otp_codes.find_one({
        "username": username,
        "code": code.strip(),
        "used": False
    })

    if not otp_doc:
        return False
    
    expires_at = otp_doc["expires_at"]
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if expires_at < now:
        return False

    db.otp_codes.update_one({"_id": otp_doc["_id"]}, {"$set": {"used": True}})
    return True