"""Production-style server (works on Windows). Run:  python serve.py
Point your Cloudflare tunnel at http://127.0.0.1:5000"""
from waitress import serve
from app import app
from config import Config

if __name__ == "__main__":
    print(f"Serving CBWCI on http://{Config.HOST}:{Config.PORT}")
    serve(app, host=Config.HOST, port=Config.PORT, threads=8)
