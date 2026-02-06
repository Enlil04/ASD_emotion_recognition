import time
import json
import uuid
import sqlite3
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from passlib.context import CryptContext

from datetime import datetime, timedelta
from jose import jwt



from setup_db import DB_PATH

router = APIRouter(prefix="/auth", tags=["auth"])

pwd_context = CryptContext(schemes=["bcrypt_sha256"], deprecated="auto")
SECRET_KEY = "CHANGE_THIS_TO_A_LONG_RANDOM_SECRET"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 7



class RegisterRequest(BaseModel):
    email: str
    password: str
    role: str                 # therapist | parent | user
    username: str | None = None
    name: str | None = None
    dob: str | None = None
    extra: dict | None = None

class LoginRequest(BaseModel):
    email: str
    password: str
    
def create_access_token(user_id: str, role: str) -> str:
    expire = datetime.utcnow() + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    payload = {"sub": user_id, "role": role, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

@router.post("/register")
def register(req: RegisterRequest):
    role = req.role.strip().lower()
    if role not in ("therapist", "parent", "user"):
        raise HTTPException(status_code=400, detail="Invalid role")

    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    # Check email uniqueness
    existing = cur.execute(
        "SELECT user_id FROM users WHERE email = ?",
        (req.email.strip(),)
    ).fetchone()
    if existing:
        con.close()
        raise HTTPException(status_code=409, detail="Email already registered")

    user_id = f"user_{uuid.uuid4().hex[:8]}"
    password_hash = pwd_context.hash(req.password)

    preferences = {
        "dob": req.dob,
        **(req.extra or {}),
    }

    now = time.time()
    cur.execute(
        """
        INSERT INTO users (
            user_id, username, name, role,
            preferences_json, created_at, updated_at,
            email, password_hash, is_active
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
        """,
        (
            user_id,
            req.username,
            req.name,
            role,
            json.dumps(preferences),
            now,
            now,
            req.email,
            password_hash,
        ),
    )

    con.commit()
    con.close()

    return {"ok": True, "user_id": user_id, "role": role}

@router.post("/login")
def login(req: LoginRequest):
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    user = cur.execute(
        "SELECT user_id, role, password_hash, is_active FROM users WHERE email = ?",
        (req.email.strip(),),
    ).fetchone()

    con.close()

    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if int(user["is_active"] or 1) != 1:
        raise HTTPException(status_code=403, detail="Account disabled")

    if not user["password_hash"]:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # verify password
    ok = pwd_context.verify(req.password, user["password_hash"])
    if not ok:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token(user["user_id"], (user["role"] or "user"))
    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": user["user_id"],
        "role": user["role"],
    }

