from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from functools import wraps
from admin_init import PREDEFINED_ADMINS
import firebase_admin
from firebase_admin import credentials, auth, db
import os
import json
import time
import secrets
from datetime import datetime, timezone


from urllib.parse import urlparse

from config import Config, SERVER_TIMESTAMP

app = Flask(__name__)
app.config.from_object(Config)
PREDEFINED_ADMIN_EMAILS = {
    admin_data['email'].strip().lower()
    for admin_data in PREDEFINED_ADMINS
}

# ========================================
# FIREBASE INITIALIZATION
# ========================================

# Initialize Firebase Admin SDK
# You need to download your service account key from Firebase Console
# and save it as 'firebase-adminsdk.json' in the project root

try:
    # Try to initialize with service account
    if os.path.exists(Config.FIREBASE_CREDENTIALS):
        cred = credentials.Certificate(Config.FIREBASE_CREDENTIALS)
        firebase_admin.initialize_app(cred, {
            'databaseURL': Config.FIREBASE_DATABASE_URL
        })
        print('✅ Firebase Admin SDK initialized with service account')
    else:
        print(f'⚠️ Service account file not found at {Config.FIREBASE_CREDENTIALS}. '
              'Login, admin pages and the API will not work until it is added.')
except Exception as e:
    print(f'❌ Firebase initialization error: {e}')

# ========================================
# DECORATORS FOR ROLE-BASED ACCESS
# ========================================

def login_required(f):
    """Decorator to require user to be logged in"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Decorator to require admin role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login', next=request.url))
        if session.get('role') != 'admin':
            return 'Access Denied. Admin privileges required.', 403
        return f(*args, **kwargs)
    return decorated_function

def member_required(f):
    """Decorator to require member role or higher"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login', next=request.url))
        if session.get('role') not in ['admin', 'member', 'followup', 'driver']:
            return 'Access Denied. Member privileges required.', 403
        return f(*args, **kwargs)
    return decorated_function

def driver_required(f):
    """Decorator to require driver role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login', next=request.url))
        if session.get('role') != 'driver' and session.get('role') != 'admin':
            return 'Access Denied. Driver privileges required.', 403
        return f(*args, **kwargs)
    return decorated_function

# ========================================
# HELPER FUNCTIONS
# ========================================

def get_user_data(uid):
    """Fetch user data from Firebase Realtime Database"""
    try:
        ref = db.reference(f'cbwci/users/{uid}')
        user_data = ref.get()
        return user_data
    except Exception as e:
        print(f'Error fetching user data: {e}')
        return None

def get_user_role(uid):
    """Get user role from Firebase"""
    user_data = get_user_data(uid)
    if user_data:
        return user_data.get('role', 'member')
    return 'member'

def save_user_session(uid, user_data):
    """Save user session data"""
    session['user_id'] = uid
    session['email'] = user_data.get('email', '')
    session['name'] = user_data.get('fullName', user_data.get('name', 'User'))
    session['role'] = user_data.get('role', 'member')
    session['phone'] = user_data.get('phone', '')
    session['logged_in'] = True

def get_login_profile(uid, email):
    """Resolve an authenticated account, prioritizing admin-created drivers."""
    is_predefined_admin = bool(email and email.strip().lower() in PREDEFINED_ADMIN_EMAILS)

    driver_paths = (f'drivers/{uid}', f'cbwci/drivers/{uid}')
    for path in driver_paths:
        profile = db.reference(path).get()
        if profile:
            profile['role'] = 'driver'
            return profile

    drivers = db.reference('drivers').get()
    if isinstance(drivers, dict) and email:
        normalized_email = email.strip().lower()
        for profile in drivers.values():
            driver_email = profile.get('email', '')
            if isinstance(driver_email, str) and driver_email.strip().lower() == normalized_email:
                profile['role'] = 'driver'
                return profile

    profile = db.reference(f'cbwci/users/{uid}').get()
    if profile:
        profile['role'] = 'admin' if profile.get('isPredefined') or is_predefined_admin else profile.get('role') or 'member'
        return profile

    users = db.reference('cbwci/users').get()
    if isinstance(users, dict) and email:
        normalized_email = email.strip().lower()
        for profile in users.values():
            profile_email = profile.get('email', '')
            if isinstance(profile_email, str) and profile_email.strip().lower() == normalized_email:
                profile['role'] = 'admin' if profile.get('isPredefined') or is_predefined_admin else profile.get('role') or 'member'
                return profile

    for path in (f'users/{uid}', f'cbwci/members/{uid}'):
        profile = db.reference(path).get()
        if profile:
            profile['role'] = 'admin' if is_predefined_admin else profile.get('role') or 'member'
            return profile

    if is_predefined_admin:
        return {'email': email, 'role': 'admin', 'status': 'active', 'isPredefined': True}

    return None

# ========================================
# AUTH ROUTES
# ========================================

@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # This is handled by Firebase Auth on the frontend
        # The frontend will send the user data after successful login
        return redirect(url_for('dashboard'))
    
    # Check if user is already logged in
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    
    return render_template("login.html")

@app.route("/register", methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # This is handled by Firebase Auth on the frontend
        return redirect(url_for('login'))
    return render_template("register.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('home'))

@app.route("/auth/status", methods=['POST'])
def auth_status():
    """Create a Flask session from a verified Firebase login."""
    data = request.get_json(silent=True) or {}
    nxt = urlparse(str(data.get('next') or ''))
    id_token = data.get('idToken')
    if not id_token:
        return jsonify({'success': False, 'message': 'Missing Firebase ID token.'}), 400

    try:
        decoded_token = auth.verify_id_token(id_token)
    except Exception:
        return jsonify({'success': False, 'message': 'Invalid or expired Firebase login.'}), 401

    uid = decoded_token['uid']
    email = decoded_token.get('email', '')
    try:
        user_data = get_login_profile(uid, email)
    except Exception as error:
        app.logger.exception('Unable to resolve authenticated user profile')
        return jsonify({'success': False, 'message': 'Unable to load your account profile.'}), 500

    if not user_data:
        return jsonify({'success': False, 'message': 'No profile is registered for this account.'}), 404

    role = str(user_data.get('role', 'member')).strip().lower()
    status = str(user_data.get('status', 'active')).strip().lower()
    if role == 'driver' and (status in ('pending', 'suspended', 'inactive') or user_data.get('credentialsActive') is False):
        return jsonify({'success': False, 'message': 'This driver account is not active.'}), 403

    user_data['role'] = 'admin' if role == 'super_admin' else role
    user_data['email'] = user_data.get('email') or email

    session.clear()
    save_user_session(uid, user_data)

    if role in ('admin', 'super_admin'):
        redirect_url = url_for('admin_dashboard')
    elif role == 'driver':
        redirect_url = url_for('driver_dashboard')
    elif role in ('followup', 'follow_up'):
        redirect_url = url_for('followup')
    else:
        redirect_url = url_for('profile')

    return jsonify({'success': True, 'role': role, 'redirect': redirect_url})

# ========================================
# MAIN PAGES (Public)
# ========================================

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/index")
def index():
    return render_template("index.html")

@app.route("/about")
def about():
    return render_template("coming_soon.html", page_title="About Us", user=session)

@app.route("/contact")
def contact():
    return render_template("coming_soon.html", page_title="Contact Us", user=session)

# ========================================
# MEMBER PAGES (Requires Login)
# ========================================

@app.route("/dashboard")
@login_required
def dashboard():
    # Redirect to appropriate dashboard based on role
    role = session.get('role', 'member')
    if role == 'admin':
        return redirect(url_for('admin_dashboard'))
    elif role == 'driver':
        return redirect(url_for('driver_dashboard'))
    elif role in ['followup', 'follow_up']:
        return redirect(url_for('followup'))
    else:
        return redirect(url_for('profile'))

@app.route("/profile")
@member_required
def profile():
    user_data = get_user_data(session['user_id'])
    return render_template("profile.html", user=user_data, session=session)

@app.route("/edit_profile")
@member_required
def edit_profile():
    user_data = get_user_data(session['user_id'])
    return render_template("edit_profile.html", user=user_data, session=session)

@app.route("/notifications")
@app.route("/notification.html")
@member_required
def notifications():
    return render_template("notification.html", user=session)

@app.route("/notification")
@member_required
def notification():
    return render_template("notification.html", user=session)

@app.route("/taxi")
@app.route("/taxi.html")
@member_required
def taxi():
    return render_template("taxi.html", user=session)

@app.route("/taxi-history")
@member_required
def taxi_history():
    return render_template("coming_soon.html", page_title="Taxi History", user=session)

@app.route("/taxi_tracking")
@member_required
def taxi_tracking():
    return render_template("coming_soon.html", page_title="Taxi Tracking", user=session)

@app.route("/sermons")
@member_required
def sermons():
    return render_template("sermons.html", user=session)

@app.route("/security")
@member_required
def security():
    return render_template("security.html", user=session)

@app.route("/followup")
@member_required
def followup():
    return render_template("followup.html", user=session)

@app.route("/followups")
@member_required
def followups():
    return render_template("followup.html", user=session)

# ========================================
# ADMIN PAGES (Requires Admin Role)
# ========================================

@app.route("/admin")
@admin_required
def admin():
    return redirect(url_for('admin_dashboard'))

@app.route("/admin/dashboard")
@admin_required
def admin_dashboard():
    # Fetch admin statistics
    stats = {
        'total_members': 0,
        'total_drivers': 0,
        'total_followups': 0,
        'total_bookings': 0,
        'pending_drivers': 0,
        'pending_followups': 0
    }
    
    # Fetch counts from Firebase
    try:
        users_ref = db.reference('cbwci/users')
        users = users_ref.get()
        if users:
            for uid, data in users.items():
                role = data.get('role', 'member')
                if role == 'member':
                    stats['total_members'] += 1
                elif role == 'driver':
                    if data.get('status') == 'pending':
                        stats['pending_drivers'] += 1
                    stats['total_drivers'] += 1
    except Exception as e:
        print(f'Error fetching stats: {e}')
    
    # Fetch followups
    try:
        followups_ref = db.reference('cbwci/followups')
        followups = followups_ref.get()
        if followups:
            stats['total_followups'] = len(followups)
            for fid, data in followups.items():
                if data.get('status') == 'pending':
                    stats['pending_followups'] += 1
    except Exception as e:
        print(f'Error fetching followups: {e}')
    
    return render_template("admin/dashboard.html", stats=stats, user=session)

@app.route("/admin/members")
@admin_required
def admin_members():
    members = []
    try:
        users_ref = db.reference('cbwci/users')
        users = users_ref.get()
        if users:
            for uid, data in users.items():
                if data.get('role', 'member') != 'admin':
                    data['uid'] = uid
                    members.append(data)
    except Exception as e:
        print(f'Error fetching members: {e}')
    
    return render_template("admin/members.html", members=members, user=session)

@app.route("/admin/members/<uid>")
@admin_required
def admin_member_detail(uid):
    user_data = get_user_data(uid)
    return render_template("coming_soon.html", page_title="Member Details", user=session)

@app.route("/admin/members/<uid>/edit", methods=['POST'])
@admin_required
def admin_member_edit(uid):
    data = request.json
    try:
        user_ref = db.reference(f'cbwci/users/{uid}')
        user_ref.update({
            'fullName': data.get('name'),
            'phone': data.get('phone'),
            'role': data.get('role'),
            'status': data.get('status')
        })
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route("/admin/followup")
@admin_required
def admin_followup():
    followups = []
    try:
        followups_ref = db.reference('cbwci/followups')
        data = followups_ref.get()
        if data:
            for fid, item in data.items():
                item['id'] = fid
                followups.append(item)
    except Exception as e:
        print(f'Error fetching followups: {e}')
    
    return render_template("admin/followup.html", followups=followups, user=session)

@app.route("/admin/followup/add", methods=['POST'])
@admin_required
def admin_followup_add():
    data = request.json
    try:
        followups_ref = db.reference('cbwci/followups')
        new_ref = followups_ref.push({
            'visitorName': data.get('visitorName'),
            'phone': data.get('phone'),
            'invitedBy': session.get('name'),
            'invitedByUid': session.get('user_id'),
            'serviceDate': data.get('serviceDate'),
            'status': 'pending',
            'dateAdded': SERVER_TIMESTAMP
        })
        return jsonify({'success': True, 'id': new_ref.key})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route("/admin/followup/<followup_id>/status", methods=['POST'])
@admin_required
def admin_followup_status(followup_id):
    data = request.json
    try:
        followup_ref = db.reference(f'cbwci/followups/{followup_id}')
        followup_ref.update({'status': data.get('status')})
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route("/admin/drivers")
@admin_required
def admin_drivers():
    drivers = []
    try:
        users_ref = db.reference('cbwci/users')
        users = users_ref.get()
        if users:
            for uid, data in users.items():
                if data.get('role') == 'driver':
                    data['uid'] = uid
                    drivers.append(data)
    except Exception as e:
        print(f'Error fetching drivers: {e}')
    
    return render_template("admin/drivers.html", drivers=drivers, user=session)

@app.route("/admin/drivers/approve/<uid>", methods=['POST'])
@admin_required
def admin_driver_approve(uid):
    try:
        user_ref = db.reference(f'cbwci/users/{uid}')
        user_ref.update({
            'status': 'approved',
            'approvedBy': session.get('user_id'),
            'approvedAt': SERVER_TIMESTAMP
        })
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route("/admin/transport")
@admin_required
def admin_transport():
    bookings = []
    try:
        bookings_ref = db.reference('cbwci/taxiBookings')
        data = bookings_ref.get()
        if data:
            for bid, item in data.items():
                item['id'] = bid
                bookings.append(item)
    except Exception as e:
        print(f'Error fetching bookings: {e}')
    
    return render_template("admin/transport.html", bookings=bookings, user=session)

@app.route("/admin/announcements")
@app.route("/admin/announcement.html")
@admin_required
def admin_announcements():
    announcements = []
    try:
        announcements_ref = db.reference('cbwci/announcements')
        data = announcements_ref.get()
        if data:
            for aid, item in data.items():
                item['id'] = aid
                announcements.append(item)
    except Exception as e:
        print(f'Error fetching announcements: {e}')
    
    return render_template("admin/announcement.html", announcements=announcements, user=session)

@app.route("/admin/announcements/add", methods=['POST'])
@admin_required
def admin_announcement_add():
    data = request.json
    try:
        announcements_ref = db.reference('cbwci/announcements')
        new_ref = announcements_ref.push({
            'title': data.get('title'),
            'message': data.get('message', data.get('description', '')),
            'audience': data.get('audience', 'everyone'),
            'audienceLabel': data.get('audienceLabel', 'Everyone'),
            'audienceList': data.get('audienceList', []),
            'status': data.get('status', 'published'),
            'date': data.get('date'),
            'time': data.get('time'),
            'createdBy': session.get('name'),
            'createdByUid': session.get('user_id'),
            'createdAt': SERVER_TIMESTAMP
        })
        return jsonify({'success': True, 'id': new_ref.key})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route("/admin/announcements/<announcement_id>", methods=['DELETE'])
@admin_required
def admin_announcement_delete(announcement_id):
    try:
        announcement_ref = db.reference(f'cbwci/announcements/{announcement_id}')
        announcement_ref.delete()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route("/admin/reports")
@app.route("/admin/reports.html")
@admin_required
def admin_reports():
    return render_template("admin/reports.html", user=session)

@app.route("/admin/settings")
@admin_required
def admin_settings():
    return render_template("admin/settings.html", user=session)

# ========================================
# DRIVER PAGES
# ========================================

@app.route("/driver/dashboard")
@app.route("/Drivers_Dashboard.html")
@app.route("/driver-dashboard.html")
@driver_required
def driver_dashboard():
    return render_template("Drivers_Dashboard.html", user=session)

@app.route("/driver/trips")
@driver_required
def driver_trips():
    return render_template("coming_soon.html", page_title="My Trips", user=session)

# ========================================
# API ENDPOINTS
# ========================================

@app.route("/api/user")
@login_required
def api_user():
    """Get current user data"""
    user_data = get_user_data(session['user_id'])
    return jsonify(user_data)

@app.route("/api/announcements")
def api_announcements():
    """Return published public announcements and targeted announcements for a user."""
    uid = session.get('user_id')
    token = request.headers.get('Authorization', '')
    if not uid and token.startswith('Bearer '):
        try:
            decoded_token = auth.verify_id_token(token[7:])
            uid = decoded_token.get('uid')
        except Exception:
            return jsonify({'success': False, 'message': 'Authentication required'}), 401
    try:
        records = db.reference('cbwci/announcements').get() or {}
        now = __import__('time').time() * 1000
        announcements = []
        for announcement_id, raw in records.items():
            raw = raw or {}
            audience = raw.get('audience', 'everyone')
            audience_list = raw.get('audienceList') or []
            scheduled_date = raw.get('scheduledDate')
            scheduled_time = None
            if scheduled_date:
                try:
                    scheduled_time = __import__('datetime').datetime.fromisoformat(
                        scheduled_date.replace('Z', '+00:00')
                    ).timestamp() * 1000
                except (TypeError, ValueError):
                    scheduled_time = None
            if raw.get('status') != 'published' or (scheduled_time and scheduled_time > now):
                continue
            if audience == 'specific' and (not uid or (audience_list and uid not in audience_list)):
                continue
            announcements.append({'id': announcement_id, **raw})
        announcements.sort(key=lambda item: item.get('createdAt', 0), reverse=True)
        return jsonify({'success': True, 'announcements': announcements})
    except Exception as error:
        print(f'Error fetching announcements API: {error}')
        return jsonify({'success': False, 'message': 'Announcements unavailable'}), 500

@app.route("/api/bookings", methods=['POST'])
def api_create_booking():
    """Create a ride request in the shared driver booking feed."""
    token = request.headers.get('Authorization', '')
    if not token.startswith('Bearer '):
        return jsonify({'success': False, 'message': 'Authentication required'}), 401
    try:
        decoded_token = auth.verify_id_token(token[7:])
        booking = request.get_json(silent=True) or {}
        booking['userId'] = decoded_token.get('uid')
        booking['createdAt'] = SERVER_TIMESTAMP
        new_ref = db.reference('bookings').push(booking)
        return jsonify({'success': True, 'id': new_ref.key})
    except Exception as error:
        print(f'Error creating booking API request: {error}')
        return jsonify({'success': False, 'message': 'Booking could not be created'}), 400

@app.route("/api/stats")
@admin_required
def api_stats():
    """Get admin statistics"""
    stats = {
        'total_members': 0,
        'total_drivers': 0,
        'total_followups': 0,
        'total_bookings': 0
    }
    
    try:
        users_ref = db.reference('cbwci/users')
        users = users_ref.get()
        if users:
            for uid, data in users.items():
                role = data.get('role', 'member')
                if role == 'member':
                    stats['total_members'] += 1
                elif role == 'driver':
                    stats['total_drivers'] += 1
    except Exception as e:
        print(f'Error fetching stats: {e}')
    
    return jsonify(stats)

# ========================================
# CBWCI VIRTUAL MEETINGS
# ========================================

MEETINGS_PATH = 'cbwci/meetings'
MEMBER_ROLES = ('admin', 'member', 'followup', 'follow_up', 'driver')

try:
    from zoneinfo import ZoneInfo
    CHURCH_TZ = ZoneInfo(Config.CHURCH_TIMEZONE)
except Exception:
    CHURCH_TZ = timezone.utc


def now_ms():
    return int(time.time() * 1000)


def api_role_required(*roles):
    """Same idea as admin_required, but answers JSON (for fetch calls)."""
    def wrapper(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if 'user_id' not in session:
                return jsonify({'success': False, 'message': 'Please log in.'}), 401
            if session.get('role') not in roles:
                return jsonify({'success': False, 'message': 'Not allowed.'}), 403
            return f(*args, **kwargs)
        return decorated
    return wrapper


def meeting_status(m):
    """upcoming / live / ended (an unstarted meeting expires 3h after it should have finished)."""
    end = int(m.get('startsAt') or 0) + int(m.get('durationMins') or 60) * 60000
    if m.get('status') == 'ended':
        return 'ended'
    if m.get('status') == 'live':
        return 'ended' if now_ms() > end + 6 * 3600000 else 'live'
    return 'ended' if now_ms() > end + 3 * 3600000 else 'upcoming'


def meeting_link(meeting_id):
    base = Config.PUBLIC_BASE_URL or request.host_url.rstrip('/')
    return base + url_for('meeting_room', meeting_id=meeting_id)


def public_meeting(meeting_id, m):
    """What people may see. The room name is never included."""
    return {'id': meeting_id, 'title': m.get('title', 'Meeting'),
            'description': m.get('description', ''), 'hostName': m.get('hostName', ''),
            'startsAt': int(m.get('startsAt') or 0), 'durationMins': int(m.get('durationMins') or 60),
            'status': meeting_status(m)}


# ----- pages -----

@app.route("/admin/meetings")
@admin_required
def admin_meetings():
    return render_template("admin/meetings.html", user=session)


@app.route("/meeting/<meeting_id>")
@member_required
def meeting_room(meeting_id):
    m = db.reference(f'{MEETINGS_PATH}/{meeting_id}').get()
    if not m:
        return 'Meeting not found.', 404
    is_host = session.get('role') == 'admin'
    status = meeting_status(m)
    state = 'ended' if status == 'ended' else ('waiting' if (not is_host and status != 'live') else 'ready')
    room = {'domain': Config.MEETING_DOMAIN, 'roomName': m.get('roomName'),
            'scriptUrl': f'https://{Config.MEETING_DOMAIN}/external_api.js'} if state == 'ready' else None
    return render_template("meeting_room.html", meeting=public_meeting(meeting_id, m),
                           state=state, is_host=is_host, jitsi=room, user=session)


# ----- API used by members -----

@app.route("/api/meetings")
@api_role_required(*MEMBER_ROLES)
def api_meetings():
    records = db.reference(MEETINGS_PATH).get() or {}
    items = [public_meeting(k, v) for k, v in records.items() if v]
    upcoming = sorted([i for i in items if i['status'] != 'ended'], key=lambda i: i['startsAt'])
    past = sorted([i for i in items if i['status'] == 'ended'], key=lambda i: -i['startsAt'])[:20]
    return jsonify({'success': True, 'meetings': upcoming + past})


@app.route("/api/meetings/<meeting_id>/status")
@api_role_required(*MEMBER_ROLES)
def api_meeting_status(meeting_id):
    m = db.reference(f'{MEETINGS_PATH}/{meeting_id}').get()
    if not m:
        return jsonify({'success': False, 'message': 'Meeting not found'}), 404
    return jsonify({'success': True, 'status': meeting_status(m)})


# ----- API used by the host (admin) -----

@app.route("/api/admin/meetings", methods=['GET'])
@api_role_required('admin')
def api_admin_meetings():
    records = db.reference(MEETINGS_PATH).get() or {}
    items = []
    for k, v in records.items():
        if v:
            item = public_meeting(k, v)
            item['link'] = meeting_link(k)
            item['shared'] = bool(v.get('announcementId'))
            items.append(item)
    items.sort(key=lambda i: -i['startsAt'])
    return jsonify({'success': True, 'meetings': items})


@app.route("/api/admin/meetings", methods=['POST'])
@api_role_required('admin')
def api_admin_meeting_create():
    d = request.get_json(silent=True) or {}
    title = str(d.get('title', '')).strip()
    try:
        starts_at, duration = int(d.get('startsAt')), int(d.get('durationMins', 60))
    except (TypeError, ValueError):
        return jsonify({'success': False, 'message': 'Please choose a valid date and time.'}), 400
    if not title or len(title) > 120:
        return jsonify({'success': False, 'message': 'Please enter a title (max 120 characters).'}), 400
    if not 15 <= duration <= 480:
        return jsonify({'success': False, 'message': 'Duration must be 15 to 480 minutes.'}), 400
    if starts_at < now_ms() - 3600000:
        return jsonify({'success': False, 'message': 'The start time is in the past.'}), 400
    ref = db.reference(MEETINGS_PATH).push({
        'title': title, 'description': str(d.get('description', '')).strip()[:1000],
        'startsAt': starts_at, 'durationMins': duration, 'status': 'upcoming',
        'roomName': 'cbwci-' + secrets.token_hex(8),
        'hostName': session.get('name', 'Admin'), 'hostUid': session.get('user_id'),
        'createdAt': now_ms()})
    return jsonify({'success': True, 'id': ref.key})


@app.route("/api/admin/meetings/<meeting_id>", methods=['DELETE'])
@api_role_required('admin')
def api_admin_meeting_delete(meeting_id):
    db.reference(f'{MEETINGS_PATH}/{meeting_id}').delete()
    return jsonify({'success': True})


@app.route("/api/admin/meetings/<meeting_id>/start", methods=['POST'])
@api_role_required('admin')
def api_admin_meeting_start(meeting_id):
    ref = db.reference(f'{MEETINGS_PATH}/{meeting_id}')
    m = ref.get()
    if not m or meeting_status(m) == 'ended':
        return jsonify({'success': False, 'message': 'This meeting has ended.'}), 400
    if m.get('status') != 'live':
        ref.update({'status': 'live', 'startedAt': now_ms(), 'hostName': session.get('name', 'Admin')})
    return jsonify({'success': True})


@app.route("/api/admin/meetings/<meeting_id>/end", methods=['POST'])
@api_role_required('admin')
def api_admin_meeting_end(meeting_id):
    ref = db.reference(f'{MEETINGS_PATH}/{meeting_id}')
    if not ref.get():
        return jsonify({'success': False, 'message': 'Meeting not found'}), 404
    ref.update({'status': 'ended', 'endedAt': now_ms()})
    return jsonify({'success': True})


@app.route("/api/admin/meetings/<meeting_id>/share", methods=['POST'])
@api_role_required('admin')
def api_admin_meeting_share(meeting_id):
    """Post the join link to the Announcements tab, for everyone."""
    ref = db.reference(f'{MEETINGS_PATH}/{meeting_id}')
    m = ref.get()
    if not m or meeting_status(m) == 'ended':
        return jsonify({'success': False, 'message': 'This meeting has ended or does not exist.'}), 400
    link = meeting_link(meeting_id)
    when = datetime.fromtimestamp(int(m['startsAt']) / 1000, tz=CHURCH_TZ).strftime('%a, %d %b %Y at %H:%M')
    lines = [m.get('description', ''), f"When: {when}", f"Duration: {m.get('durationMins', 60)} minutes",
             f"Host: {m.get('hostName', 'CBWCI')}", f"Join: {link}"]
    now = datetime.now(tz=CHURCH_TZ)
    new = db.reference('cbwci/announcements').push({
        'title': f"Virtual Meeting: {m.get('title', 'Meeting')}",
        'message': "\n".join(x for x in lines if x),
        'audience': 'everyone', 'audienceLabel': 'Everyone', 'audienceList': [],
        'status': 'published', 'date': now.strftime('%d/%m/%Y'), 'time': now.strftime('%H:%M'),
        'createdAt': now_ms(), 'scheduledDate': None, 'type': 'meeting',
        'meetingId': meeting_id, 'link': link})
    ref.update({'announcementId': new.key, 'sharedAt': now_ms()})
    return jsonify({'success': True, 'link': link})

# ========================================
# ERROR HANDLERS
# ========================================

@app.errorhandler(404)
def page_not_found(e):
    return "Page not found", 404

@app.errorhandler(500)
def internal_server_error(e):
    return "Internal server error", 500

# ========================================
# CONTEXT PROCESSOR (Make user available in all templates)
# ========================================

@app.context_processor
def inject_user():
    """Make user session available in all templates"""
    return {
        'current_user': session.get('name', 'Guest'),
        'current_role': session.get('role', 'guest'),
        'is_logged_in': 'user_id' in session,
        'is_admin': session.get('role') == 'admin',
        'is_driver': session.get('role') == 'driver',
        'is_member': session.get('role') in ['member', 'admin', 'followup', 'driver']
    }

@app.after_request
def inject_announcement_listener(response):
    """Load the live announcement alert on every rendered HTML page."""
    if request.path in ['/api/announcements', '/api/bookings']:
        response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
        response.headers['Access-Control-Allow-Headers'] = 'Authorization, Content-Type'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    if response.content_type and response.content_type.startswith('text/html'):
        html = response.get_data(as_text=True)
        if '/static/announcement-alert.js' not in html and '</body>' in html:
            html = html.replace(
                '</body>',
                '<script src="/static/announcement-alert.js"></script></body>'
            )
            response.set_data(html)
    return response

# ========================================
# RUN THE APP
# ========================================

if __name__ == "__main__":
    # Local development only. For the live site use serve.py (waitress).
    app.run(debug=Config.DEBUG, host=Config.HOST, port=Config.PORT)