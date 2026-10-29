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

        const close = document.createElement('button');
        close.type = 'button';
        close.setAttribute('aria-label', 'Close announcement');
        close.textContent = 'x';
        close.style.cssText = 'position:absolute;right:12px;top:10px;border:0;background:transparent;color:#4a1942;font-size:22px;cursor:pointer;';
        close.addEventListener('click', function () { alert.remove(); });

        alert.append(title, message, close);
        document.body.appendChild(alert);
    }

    async function start() {
        try {
            const announcementApp = await ensureFirebase();
            announcementApp.auth().onAuthStateChanged(async function (user) {
                const apiBase = window.location.port === '5500' ? 'http://127.0.0.1:5000' : '';
                const headers = {};
                if (user) headers.Authorization = `Bearer ${await user.getIdToken()}`;
                const response = await fetch(`${apiBase}/api/announcements`, {
                    headers
                });
                if (!response.ok) throw new Error(`Announcements request failed (${response.status})`);
                const payload = await response.json();
                const announcements = payload.announcements || [];
                updateUnreadBadges(announcements);
                if (announcements.length) showAnnouncementAlert(announcements[0]);
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
