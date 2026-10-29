"""Central configuration. Values come from environment variables / the .env file."""
import os
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))



def _flag(name, default=False):
    return os.environ.get(name, str(default)).strip().lower() in ("1", "true", "yes", "on")


class Config:
    # Sessions: must be fixed (and secret) or everyone is logged out on every restart.
    SECRET_KEY = os.environ.get("SECRET_KEY") or "dev-only-change-me"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    # Set SESSION_COOKIE_SECURE=true once the site is served over https (Cloudflare tunnel).
    SESSION_COOKIE_SECURE = _flag("SESSION_COOKIE_SECURE", False)

    # Firebase
    FIREBASE_CREDENTIALS = os.environ.get(
        "FIREBASE_CREDENTIALS", os.path.join(BASE_DIR, "firebase-adminsdk.json")
    )
    FIREBASE_DATABASE_URL = os.environ.get(
        "FIREBASE_DATABASE_URL", "https://cbwci-892de-default-rtdb.firebaseio.com/"
    )

    CHURCH_TIMEZONE = os.environ.get("CHURCH_TIMEZONE", "Africa/Johannesburg")
    PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL", "").strip().rstrip("/")
    MEETING_DOMAIN = os.environ.get("MEETING_DOMAIN", "meet.jit.si")

    # Server
    DEBUG = _flag("FLASK_DEBUG", False)
    HOST = os.environ.get("HOST", "127.0.0.1")
    PORT = int(os.environ.get("PORT", "5000"))

    if SECRET_KEY == "dev-only-change-me" and not DEBUG:
        print("⚠️  SECRET_KEY is not set in .env - using an insecure default. Set it before going live.")


# Realtime Database server-side timestamp placeholder (works in every firebase-admin version)
SERVER_TIMESTAMP = {".sv": "timestamp"}