# CBWCI Website

Flask + Firebase (Auth + Realtime Database).

## First-time setup
1. Copy `.env.example` to `.env`; set `SECRET_KEY` (command is in the file).
2. Firebase console -> Project settings -> Service accounts -> **Generate new private key**.
   Save it as `firebase-adminsdk.json` in this folder (it is git-ignored). Revoke the old key.
3. Double-click `run.bat` (creates `venv`, installs requirements, starts the server).
   Use `run.bat dev` for debug mode on your own PC only.
4. Create the admin accounts once: `python admin_init.py` -> option 6.

## Live site
`python serve.py` (waitress) listens on 127.0.0.1:5000; point the Cloudflare tunnel there.
Set `SESSION_COOKIE_SECURE=true` in `.env` once it is on https.

## Status
Step 1 (foundation) done. Pages still showing "coming soon": about, contact,
taxi history, taxi tracking, member details, driver trips.
