import hashlib
import secrets
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from src.models.user import User

# In-memory session store for lightweight local session verification
# maps session_token -> {"user_id": user_id, "expires_at": datetime}
SESSION_STORE = {}

def hash_password(password: str) -> str:
    # Use PBKDF2 with SHA-256 for secure hashing out-of-the-box
    salt = b"running_coach_salt_secure_123"
    iterations = 100000
    hashed = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return hashed.hex()

def verify_password(password: str, hashed_password: str) -> bool:
    return hash_password(password) == hashed_password

def create_user_session(user_id: str) -> str:
    token = secrets.token_urlsafe(32)
    # Session valid for 7 days
    expiry = datetime.utcnow() + timedelta(days=7)
    SESSION_STORE[token] = {"user_id": user_id, "expires_at": expiry}
    return token

def get_user_from_session(token: str, db: Session) -> User:
    session = SESSION_STORE.get(token)
    if not session:
        return None
    if session["expires_at"] < datetime.utcnow():
        # Session expired, cleanup
        SESSION_STORE.pop(token, None)
        return None
    return db.query(User).filter(User.id == session["user_id"]).first()
