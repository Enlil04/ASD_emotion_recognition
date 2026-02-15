from fastapi import APIRouter, HTTPException
import sqlite3
import time
import string
import random
from pydantic import BaseModel
from setup_db import DB_PATH  # ✅ Corrected import

# ✅ Result URLs will start with /api/guardian/...
router = APIRouter(tags=["guardian"])

# --- Models ---
class RegenerateCodeRequest(BaseModel):
    user_id: str

class ConnectRequest(BaseModel):
    patient_id: str
    code: str

# --- Helpers ---
def _generate_guardian_code() -> str:
    chars = string.ascii_uppercase + string.digits
    return "G-" + "".join(random.choice(chars) for _ in range(6))

def _connect_db_row() -> sqlite3.Connection:
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con

# Check logic for dashboard access
def _guardian_can_access_patient(cur: sqlite3.Cursor, guardian_id: str, patient_id: str) -> bool:
    row = cur.execute(
        "SELECT 1 FROM therapist_patient WHERE therapist_id = ? AND patient_id = ? LIMIT 1",
        (guardian_id, patient_id),
    ).fetchone()
    return row is not None


# ==============================
# ENDPOINTS
# ==============================

# 1. Get Code
@router.get("/code")  # ✅ URL: /api/guardian/code
async def therapist_my_code(user_id: str):
    """Retrieve existing link code or generate a new one."""
    con = _connect_db_row()
    try:
        cur = con.cursor()
        u = cur.execute("SELECT user_id, role, therapist_code FROM users WHERE user_id = ?", (user_id,)).fetchone()
        
        if not u:
            raise HTTPException(status_code=404, detail="user not found")
        
        role = (u["role"] or "").lower()
        if role not in ("therapist", "parent"):
            raise HTTPException(status_code=403, detail="Only therapist/parent can have a code")

        if u["therapist_code"]:
            return {"user_id": user_id, "code": u["therapist_code"]}

        # Generate new if none exists
        for _ in range(10):
            new_code = _generate_guardian_code()
            try:
                cur.execute("UPDATE users SET therapist_code = ? WHERE user_id = ?", (new_code, user_id))
                con.commit()
                return {"user_id": user_id, "code": new_code}
            except Exception:
                continue
        raise HTTPException(status_code=500, detail="Could not generate unique code")
    finally:
        con.close()


# 2. Regenerate Code
@router.post("/code/regenerate")  # ✅ URL: /api/guardian/code/regenerate
async def therapist_regenerate_code(req: RegenerateCodeRequest):
    """Force a new code generation (invalidates old code)."""
    con = _connect_db_row()
    try:
        cur = con.cursor()
        u = cur.execute("SELECT role FROM users WHERE user_id = ?", (req.user_id,)).fetchone()
        
        if not u or (u["role"] or "").lower() not in ("therapist", "parent"):
            raise HTTPException(status_code=403, detail="Not allowed")

        for _ in range(10):
            new_code = _generate_guardian_code()
            try:
                cur.execute("UPDATE users SET therapist_code = ? WHERE user_id = ?", (new_code, req.user_id))
                con.commit()
                return {"user_id": req.user_id, "code": new_code}
            except Exception:
                continue
        raise HTTPException(status_code=500, detail="Could not generate unique code")
    finally:
        con.close()


# 3. Connect Patient
@router.post("/connect")  # ✅ URL: /api/guardian/connect
async def connect_patient(req: ConnectRequest):
    """Patient enters the Guardian's code to link accounts."""
    con = _connect_db_row()
    now = time.time()
    try:
        cur = con.cursor()

        # Validate Patient
        p = cur.execute("SELECT role FROM users WHERE user_id = ?", (req.patient_id,)).fetchone()
        if not p or (p["role"] or "").lower() != "user":
            raise HTTPException(status_code=400, detail="Invalid patient user")

        # Validate Code
        code = (req.code or "").strip().upper()
        g = cur.execute("SELECT user_id, role FROM users WHERE therapist_code = ?", (code,)).fetchone()
        if not g:
            raise HTTPException(status_code=404, detail="Invalid code")

        # Insert Link
        cur.execute(
            "INSERT OR IGNORE INTO therapist_patient(therapist_id, patient_id, date_assigned) VALUES (?, ?, ?)",
            (g["user_id"], req.patient_id, now),
        )
        con.commit()
        return {"ok": True, "therapist_id": g["user_id"], "patient_id": req.patient_id}
    finally:
        con.close()


# 4. List Patients
@router.get("/{guardian_id}/patients")  # ✅ URL: /api/guardian/{id}/patients
async def get_guardian_patients(guardian_id: str):
    """List all patients linked to this guardian."""
    con = _connect_db_row()
    try:
        cur = con.cursor()
        
        g = cur.execute("SELECT role FROM users WHERE user_id = ?", (guardian_id,)).fetchone()
        if not g or (g["role"] or "").lower() not in ("therapist", "parent"):
            raise HTTPException(status_code=403, detail="Not allowed")

        rows = cur.execute(
            """
            SELECT u.user_id, u.name, u.username, u.age, u.photo
            FROM therapist_patient tp
            JOIN users u ON u.user_id = tp.patient_id
            WHERE tp.therapist_id = ?
            ORDER BY tp.date_assigned DESC
            """,
            (guardian_id,),
        ).fetchall()

        return {"items": [dict(r) for r in rows]}
    finally:
        con.close()



# from fastapi import APIRouter, HTTPException
# import sqlite3
# import time
# import string
# import random
# from back.agent.koog_orchestrator import DB_PATH
# from pydantic import BaseModel


# router = APIRouter(prefix="/guardian", tags=["guardian"])

# # --- model for regenerate code request ---

# class RegenerateCodeRequest(BaseModel):
#     user_id: str

# class ConnectRequest(BaseModel):
#     patient_id: str
#     code: str

# # ----------------- generate therapist code ---------------------------
# def _generate_guardian_code() -> str:
#     # Example: G-7K3F9A (short, readable)
#     chars = string.ascii_uppercase + string.digits
#     return "G-" + "".join(random.choice(chars) for _ in range(6))



# def _connect_db_row() -> sqlite3.Connection:
#     con = sqlite3.connect(DB_PATH)
#     con.row_factory = sqlite3.Row
#     return con

# # guardian (therapist or parent) can only view linked patients 
# def _guardian_can_access_patient(cur: sqlite3.Cursor, guardian_id: str, patient_id: str) -> bool:
#     row = cur.execute(
#         """
#         SELECT 1
#         FROM therapist_patient
#         WHERE therapist_id = ? AND patient_id = ?
#         LIMIT 1
#         """,
#         (guardian_id, patient_id),
#     ).fetchone()
#     return row is not None


# #======================================================
# #connect therapist and users endpoints
# #======================================================

# #1. get therapist code 
# @router.get("/api/therapist/my_code")
# async def therapist_my_code(user_id: str):
#     con = _connect_db_row()
#     try:
#         cur = con.cursor()

#         u = cur.execute(
#             "SELECT user_id, role, therapist_code FROM users WHERE user_id = ?",
#             (user_id,),
#         ).fetchone()

#         if not u:
#             raise HTTPException(status_code=404, detail="user not found")

#         role = (u["role"] or "").lower()
#         if role not in ("therapist", "parent"):
#             raise HTTPException(status_code=403, detail="only therapist/parent can have a code")

#         code = u["therapist_code"]
#         if code:
#             return {"user_id": user_id, "code": code}

#         # generate unique code + save
#         for _ in range(10):
#             new_code = _generate_guardian_code()
#             try:
#                 cur.execute(
#                     "UPDATE users SET therapist_code = ? WHERE user_id = ?",
#                     (new_code, user_id),
#                 )
#                 con.commit()
#                 return {"user_id": user_id, "code": new_code}
#             except Exception:
#                 # possible rare collision, retry
#                 continue

#         raise HTTPException(status_code=500, detail="could not generate unique code")

#     finally:
#         con.close()


# # 2. regenerate code 
# @router.post("/api/therapist/regenerate_code")
# async def therapist_regenerate_code(req: RegenerateCodeRequest):
#     con = _connect_db_row()
#     try:
#         cur = con.cursor()

#         u = cur.execute(
#             "SELECT user_id, role FROM users WHERE user_id = ?",
#             (req.user_id,),
#         ).fetchone()

#         if not u:
#             raise HTTPException(status_code=404, detail="user not found")

#         role = (u["role"] or "").lower()
#         if role not in ("therapist", "parent"):
#             raise HTTPException(status_code=403, detail="only therapist/parent can regenerate code")

#         for _ in range(10):
#             new_code = _generate_guardian_code()
#             try:
#                 cur.execute(
#                     "UPDATE users SET therapist_code = ? WHERE user_id = ?",
#                     (new_code, req.user_id),
#                 )
#                 con.commit()
#                 return {"user_id": req.user_id, "code": new_code}
#             except Exception:
#                 continue

#         raise HTTPException(status_code=500, detail="could not generate unique code")

#     finally:
#         con.close()


# #3. patients connect using that code 
# @router.post("/api/therapist/connect")
# async def connect_patient(req: ConnectRequest):
#     con = _connect_db_row()
#     now = time.time()
#     try:
#         cur = con.cursor()

#         # validate patient exists and is role=user
#         p = cur.execute(
#             "SELECT user_id, role FROM users WHERE user_id = ?",
#             (req.patient_id,),
#         ).fetchone()

#         if not p or (p["role"] or "").lower() != "user":
#             raise HTTPException(status_code=400, detail="invalid patient")

#         # normalize code (support lowercase input)
#         code = (req.code or "").strip().upper()

#         # find guardian by code
#         g = cur.execute(
#             "SELECT user_id, role FROM users WHERE therapist_code = ?",
#             (code,),
#         ).fetchone()

#         if not g:
#             raise HTTPException(status_code=404, detail="invalid code")

#         g_role = (g["role"] or "").lower()
#         if g_role not in ("therapist", "parent"):
#             raise HTTPException(status_code=400, detail="code does not belong to guardian")

#         guardian_id = g["user_id"]

#         # insert relation (idempotent)
#         cur.execute(
#             """
#             INSERT OR IGNORE INTO therapist_patient(therapist_id, patient_id, date_assigned)
#             VALUES (?, ?, ?)
#             """,
#             (guardian_id, req.patient_id, now),
#         )
#         con.commit()

#         return {"ok": True, "therapist_id": guardian_id, "patient_id": req.patient_id}

#     finally:
#         con.close()

# # 4. therapist (or parent) list their patients (or childern)
# @router.get("/api/therapist/{therapist_id}/patients")
# async def get_guardian_patients(therapist_id: str):
#     con = _connect_db_row()
#     try:
#         cur = con.cursor()

#         # validate guardian role
#         g = cur.execute(
#             "SELECT role FROM users WHERE user_id = ?",
#             (therapist_id,),
#         ).fetchone()

#         if not g or (g["role"] or "").lower() not in ("therapist", "parent"):
#             raise HTTPException(status_code=403, detail="not allowed")

#         rows = cur.execute(
#             """
#             SELECT u.user_id, u.name, u.username, u.age, u.photo
#             FROM therapist_patient tp
#             JOIN users u ON u.user_id = tp.patient_id
#             WHERE tp.therapist_id = ?
#             ORDER BY tp.date_assigned DESC
#             """,
#             (therapist_id,),
#         ).fetchall()

#         return {
#             "items": [
#                 {
#                     "user_id": r["user_id"],
#                     "name": r["name"],
#                     "username": r["username"],
#                     "age": r["age"],
#                     "photo": r["photo"],
#                 }
#                 for r in rows
#             ]
#         }

#     finally:
#         con.close()

