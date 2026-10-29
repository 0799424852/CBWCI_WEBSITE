(function () {
    'use strict';

    const firebaseConfig = {
        apiKey: 'AIzaSyBhXS5EOZjEAahTjk8XPd-9PkG3HeKV8bg',
        authDomain: 'cbwci-892de.firebaseapp.com',
        projectId: 'cbwci-892de',
        storageBucket: 'cbwci-892de.firebasestorage.app',
        messagingSenderId: '187272132769',
        appId: '1:187272132769:web:63a9fcba465e54867d98e0',
        databaseURL: 'https://cbwci-892de-default-rtdb.firebaseio.com'
    };

    // Announcements older than this are never popped up (they still show in Notifications)
    const MAX_ALERT_AGE_MS = 7 * 24 * 60 * 60 * 1000;

    // Never pop an alert over a live video meeting
    if (window.location.pathname.indexOf('/meeting/') === 0) return;

    let checkedThisPage = false;

    function loadScript(src) {
        return new Promise(function (resolve, reject) {
            const script = document.createElement('script');
            script.src = src;
            script.onload = resolve;
            script.onerror = reject;
            document.head.appendChild(script);
        });
    }

    async function ensureFirebase() {
        if (!window.firebase) {
            await loadScript('https://www.gstatic.com/firebasejs/9.23.0/firebase-app-compat.js');
        }
        if (!window.firebase.auth) {
            await loadScript('https://www.gstatic.com/firebasejs/9.23.0/firebase-auth-compat.js');
        }
        if (!firebase.apps.length) {
            firebase.initializeApp(firebaseConfig);
        }
        return firebase.app();
    }

    // ---- "already alerted" memory, kept per user in this browser ----
    function alertedKey(uid) {
        return 'cbwci_alerted_announcements_' + uid;
    }

    function loadAlerted(uid) {
        try { return JSON.parse(localStorage.getItem(alertedKey(uid)) || '{}'); } catch (error) { return {}; }
    }

    function saveAlerted(uid, alerted) {
        try {
            // keep the newest 200 entries so the list never grows forever
            const ids = Object.keys(alerted).sort(function (a, b) { return alerted[b] - alerted[a]; }).slice(0, 200);
            const trimmed = {};
            ids.forEach(function (id) { trimmed[id] = alerted[id]; });
            localStorage.setItem(alertedKey(uid), JSON.stringify(trimmed));
        } catch (error) {}
    }

    function updateUnreadBadges(announcements) {
        let read = {};
        try { read = JSON.parse(localStorage.getItem('cbwci_read_announcements') || '{}'); } catch (error) {}
        const unreadCount = announcements.filter(function (item) { return !read[item.id]; }).length;
        document.querySelectorAll('#notificationBadge, #unreadCount').forEach(function (badge) {
            badge.textContent = unreadCount;
            badge.style.display = unreadCount ? '' : 'none';
        });
    }

    function showAnnouncementAlert(announcement) {
        if (document.getElementById('cbwciAnnouncementAlert')) return;

        const alert = document.createElement('div');
        alert.id = 'cbwciAnnouncementAlert';
        alert.setAttribute('role', 'alert');
        alert.style.cssText = [
            'position:fixed', 'top:18px', 'left:50%', 'transform:translateX(-50%)',
            'z-index:2050', 'width:min(720px, calc(100% - 32px))', 'padding:16px 48px 16px 18px',
            'background:#fffdf7', 'border:2px solid #c9a84c', 'border-radius:12px',
            'box-shadow:0 12px 35px rgba(0,0,0,.25)', 'color:#2c1a24',
            'font:14px/1.5 Inter, Arial, sans-serif'
        ].join(';');

        const title = document.createElement('strong');
        title.textContent = 'Announcement: ' + (announcement.title || 'New update');
        title.style.display = 'block';
        title.style.color = '#4a1942';

        const message = document.createElement('span');
        message.textContent = announcement.message || '';
        message.style.whiteSpace = 'pre-line';

        const close = document.createElement('button');
        close.type = 'button';
        close.setAttribute('aria-label', 'Close announcement');
        close.textContent = 'x';
        close.style.cssText = 'position:absolute;right:12px;top:10px;border:0;background:transparent;color:#4a1942;font-size:22px;cursor:pointer;';
        close.addEventListener('click', function () { alert.remove(); });

        alert.append(title, message);
        if (/^(https?:\/\/|\/)/.test(announcement.link || '')) {
            const join = document.createElement('a');
            join.href = announcement.link;
            join.target = '_blank';
            join.rel = 'noopener';
            join.textContent = 'Join meeting';
            join.style.cssText = 'display:inline-block;margin-top:10px;padding:8px 16px;border-radius:8px;background:#4a1942;color:#fff;text-decoration:none;font-weight:600;';
            alert.append(document.createElement('br'), join);
        }
        alert.append(close);
        document.body.appendChild(alert);
    }

    async function checkAnnouncements(user) {
        // Visitors who are not logged in never get an alert
        if (!user) return;
        // Only once per page load, however many times Firebase reports the login state
        if (checkedThisPage) return;
        checkedThisPage = true;

        const apiBase = window.location.port === '5500' ? 'http://127.0.0.1:5000' : '';
        const response = await fetch(`${apiBase}/api/announcements`, {
            headers: { Authorization: `Bearer ${await user.getIdToken()}` }
        });
        if (!response.ok) throw new Error(`Announcements request failed (${response.status})`);
        const payload = await response.json();
        const announcements = payload.announcements || [];   // newest first
        updateUnreadBadges(announcements);

        const alerted = loadAlerted(user.uid);
        const fresh = announcements.filter(function (item) { return !alerted[item.id]; });
        if (!fresh.length) return;

        // Remember everything as alerted BEFORE showing, so it can never pop up twice
        const now = Date.now();
        announcements.forEach(function (item) { alerted[item.id] = alerted[item.id] || now; });
        saveAlerted(user.uid, alerted);

        // Show only the newest new announcement, and only if it is recent
        const newest = fresh[0];
        const createdAt = Number(newest.createdAt);
        const isRecent = !createdAt || (now - createdAt) <= MAX_ALERT_AGE_MS;
        if (isRecent) showAnnouncementAlert(newest);
    }

    async function start() {
        try {
            const announcementApp = await ensureFirebase();
            announcementApp.auth().onAuthStateChanged(function (user) {
                checkAnnouncements(user).catch(function (error) {
                    console.error('CBWCI announcements could not load:', error);
                });
            });
        } catch (error) {
            console.error('CBWCI announcements could not load:', error);
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', start);
    } else {
        start();
    }
})();