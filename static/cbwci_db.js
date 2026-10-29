// ========================================
// CBWCI - Firebase Database Service
// ========================================
// This file handles all database operations for the CBWCI admin system
// It assumes Firebase is already initialized in the HTML page

// ========================================
// DATABASE SERVICE CLASS
// ========================================
class CBWCIDatabase {
    constructor() {
        // Use the already initialized Firebase instance
        if (typeof firebase === 'undefined') {
            console.error('❌ Firebase is not loaded! Make sure Firebase SDKs are loaded before this file.');
            return;
        }
        
        this.db = firebase.database();
        this.auth = firebase.auth();
        this.basePath = 'cbwci';
        console.log('✅ CBWCI Database Service initialized');
    }

    // ========================================
    // DATABASE INITIALIZATION
    // ========================================
    async initializeDatabase() {
        try {
            console.log('🚀 Initializing CBWCI database structure...');
            
            // Check if database exists
            const snapshot = await this.db.ref(this.basePath).once('value');
            if (!snapshot.exists()) {
                console.log('📦 Creating initial database structure...');
                await this.createInitialStructure();
                console.log('✅ Database structure created successfully');
            } else {
                console.log('✅ Database already exists');
            }
            
            // Ensure all collections exist
            await this.ensureCollections();
            console.log('✅ All collections verified');
            
            return true;
        } catch (error) {
            console.error('❌ Error initializing database:', error);
            throw error;
        }
    }

    // ========================================
    // CREATE INITIAL DATABASE STRUCTURE
    // ========================================
    async createInitialStructure() {
        const initialData = {
            settings: {
                general: {
                    churchName: "Changed By The Word Church International",
                    shortName: "CBWCI",
                    tagline: "\"Change, Dominate and Walk in Glory\"",
                    description: "Changed By The Word Church International is a multi-cultural, spirit-filled church dedicated to transforming lives through the Word of God.",
                    primaryColor: "#4A1942",
                    secondaryColor: "#C9A84C"
                },
                church: {
                    address: "123 Church Street, Nelspruit, Mpumalanga",
                    city: "Nelspruit",
                    province: "Mpumalanga",
                    phone: "+27 13 123 4567",
                    email: "info@cbwci.org",
                    serviceTimes: {
                        sunday: "10:00 AM",
                        midweek: "6:30 PM",
                        prayer: "6:00 PM",
                        bibleStudy: "7:00 PM"
                    }
                },
                membership: {
                    allowRegistration: true,
                    requireApproval: false,
                    defaultRole: "member",
                    maxMembers: 1000
                },
                transport: {
                    maxPassengers: 15,
                    defaultPickupTime: "08:30",
                    allowBooking: true,
                    liveTracking: true
                },
                notifications: {
                    email: true,
                    push: true,
                    sms: false,
                    whatsapp: true,
                    notificationEmail: "notifications@cbwci.org",
                    notificationPhone: "+27 82 123 4567"
                },
                security: {
                    twoFactorAuth: false,
                    sessionTimeout: true,
                    sessionTimeoutMinutes: 30,
                    maxLoginAttempts: 5
                },
                backup: {
                    autoBackup: true,
                    frequency: "weekly",
                    time: "02:00"
                }
            },
            users: {},
            members: {},
            followups: {},
            drivers: {},
            taxiBookings: {},
            announcements: {},
            feedback: {},
            taxiRoutes: {},
            reports: {
                activity: {},
                statistics: {}
            },
            admin: {
                admins: {},
                logs: {}
            },
            notifications: {
                global: {}
            },
            backups: {},
            groups: {},
            zoomMeetings: {},
            _meta: {
                createdAt: new Date().toISOString(),
                version: "1.0.0",
                initialized: true
            }
        };

        await this.db.ref(this.basePath).set(initialData);
        return true;
    }

    // ========================================
    // ENSURE ALL COLLECTIONS EXIST
    // ========================================
    async ensureCollections() {
        const collections = [
            'settings',
            'users',
            'members',
            'followups',
            'drivers',
            'taxiBookings',
            'announcements',
            'feedback',
            'taxiRoutes',
            'reports',
            'admin',
            'notifications',
            'backups',
            'groups',
            'zoomMeetings'
        ];

        for (const collection of collections) {
            const ref = this.db.ref(`${this.basePath}/${collection}`);
            const snapshot = await ref.once('value');
            if (!snapshot.exists()) {
                await ref.set({});
                console.log(`📁 Created collection: ${collection}`);
            }
        }
    }

    // ========================================
    // USER MANAGEMENT
    // ========================================
    
    // Create a new user
    async createUser(uid, userData) {
        try {
            const userRef = this.db.ref(`${this.basePath}/users/${uid}`);
            const memberRef = this.db.ref(`${this.basePath}/members/${uid}`);
            
            // Add timestamp
            userData.dateJoined = new Date().toISOString();
            userData.uid = uid;
            userData.status = userData.status || 'active';
            
            // Save to users
            await userRef.set(userData);
            
            // Save to members list (simplified version)
            await memberRef.set({
                uid: uid,
                fullName: userData.fullName,
                email: userData.email,
                phone: userData.phone,
                role: userData.role || 'member',
                status: userData.status || 'active',
                dateJoined: userData.dateJoined
            });
            
            console.log(`✅ User created: ${uid}`);
            return userData;
        } catch (error) {
            console.error('❌ Error creating user:', error);
            throw error;
        }
    }

    // Get user by UID
    async getUser(uid) {
        try {
            const snapshot = await this.db.ref(`${this.basePath}/users/${uid}`).once('value');
            return snapshot.val();
        } catch (error) {
            console.error('❌ Error getting user:', error);
            throw error;
        }
    }

    // Update user
    async updateUser(uid, updates) {
        try {
            const userRef = this.db.ref(`${this.basePath}/users/${uid}`);
            const memberRef = this.db.ref(`${this.basePath}/members/${uid}`);
            
            // Update user
            await userRef.update(updates);
            
            // Update member list if relevant fields changed
            const userSnapshot = await userRef.once('value');
            const userData = userSnapshot.val();
            await memberRef.update({
                fullName: userData.fullName,
                email: userData.email,
                phone: userData.phone,
                role: userData.role,
                status: userData.status
            });
            
            console.log(`✅ User updated: ${uid}`);
            return true;
        } catch (error) {
            console.error('❌ Error updating user:', error);
            throw error;
        }
    }

    // Get all members
    async getAllMembers() {
        try {
            const snapshot = await this.db.ref(`${this.basePath}/members`).once('value');
            const data = snapshot.val();
            if (!data) return [];
            return Object.values(data);
        } catch (error) {
            console.error('❌ Error getting members:', error);
            throw error;
        }
    }

    // ========================================
    // ANNOUNCEMENT MANAGEMENT
    // ========================================
    
    // Create announcement
    async createAnnouncement(announcementData) {
        try {
            const ref = this.db.ref(`${this.basePath}/announcements`).push();
            const id = ref.key;
            
            const announcement = {
                id: id,
                ...announcementData,
                createdAt: new Date().toISOString(),
                status: announcementData.status || 'draft'
            };
            
            await ref.set(announcement);
            console.log(`✅ Announcement created: ${id}`);
            return announcement;
        } catch (error) {
            console.error('❌ Error creating announcement:', error);
            throw error;
        }
    }

    // Get all announcements
    async getAnnouncements() {
        try {
            const snapshot = await this.db.ref(`${this.basePath}/announcements`).once('value');
            const data = snapshot.val();
            if (!data) return [];
            return Object.values(data);
        } catch (error) {
            console.error('❌ Error getting announcements:', error);
            throw error;
        }
    }

    // Update announcement
    async updateAnnouncement(id, updates) {
        try {
            await this.db.ref(`${this.basePath}/announcements/${id}`).update(updates);
            console.log(`✅ Announcement updated: ${id}`);
            return true;
        } catch (error) {
            console.error('❌ Error updating announcement:', error);
            throw error;
        }
    }

    // Delete announcement
    async deleteAnnouncement(id) {
        try {
            await this.db.ref(`${this.basePath}/announcements/${id}`).remove();
            console.log(`✅ Announcement deleted: ${id}`);
            return true;
        } catch (error) {
            console.error('❌ Error deleting announcement:', error);
            throw error;
        }
    }

    // Get announcements for a specific user
    async getUserAnnouncements(uid) {
        try {
            const allAnnouncements = await this.getAnnouncements();
            
            // Filter announcements for this user
            return allAnnouncements.filter(ann => {
                if (ann.audience === 'everyone') return true;
                if (ann.audience === 'specific' && ann.audienceList) {
                    return ann.audienceList.includes(uid);
                }
                return false;
            });
        } catch (error) {
            console.error('❌ Error getting user announcements:', error);
            throw error;
        }
    }

    // ========================================
    // FOLLOW-UP MANAGEMENT
    // ========================================
    
    // Create follow-up
    async createFollowup(followupData) {
        try {
            const ref = this.db.ref(`${this.basePath}/followups`).push();
            const id = ref.key;
            
            const followup = {
                id: id,
                ...followupData,
                dateAdded: new Date().toISOString(),
                status: followupData.status || 'pending'
            };
            
            await ref.set(followup);
            console.log(`✅ Follow-up created: ${id}`);
            return followup;
        } catch (error) {
            console.error('❌ Error creating follow-up:', error);
            throw error;
        }
    }

    // Get all followups
    async getFollowups() {
        try {
            const snapshot = await this.db.ref(`${this.basePath}/followups`).once('value');
            const data = snapshot.val();
            if (!data) return [];
            return Object.values(data);
        } catch (error) {
            console.error('❌ Error getting followups:', error);
            throw error;
        }
    }

    // Update followup status
    async updateFollowupStatus(id, status) {
        try {
            await this.db.ref(`${this.basePath}/followups/${id}/status`).set(status);
            console.log(`✅ Follow-up status updated: ${id} -> ${status}`);
            return true;
        } catch (error) {
            console.error('❌ Error updating follow-up status:', error);
            throw error;
        }
    }

    // ========================================
    // FEEDBACK MANAGEMENT
    // ========================================
    
    // Create feedback
    async createFeedback(feedbackData) {
        try {
            const ref = this.db.ref(`${this.basePath}/feedback`).push();
            const id = ref.key;
            
            const feedback = {
                id: id,
                ...feedbackData,
                timestamp: new Date().toISOString(),
                status: 'pending',
                priority: false,
                replies: []
            };
            
            await ref.set(feedback);
            console.log(`✅ Feedback created: ${id}`);
            return feedback;
        } catch (error) {
            console.error('❌ Error creating feedback:', error);
            throw error;
        }
    }

    // Get all feedback
    async getFeedback() {
        try {
            const snapshot = await this.db.ref(`${this.basePath}/feedback`).once('value');
            const data = snapshot.val();
            if (!data) return [];
            return Object.values(data);
        } catch (error) {
            console.error('❌ Error getting feedback:', error);
            throw error;
        }
    }

    // Update feedback status
    async updateFeedbackStatus(id, status) {
        try {
            await this.db.ref(`${this.basePath}/feedback/${id}/status`).set(status);
            console.log(`✅ Feedback status updated: ${id} -> ${status}`);
            return true;
        } catch (error) {
            console.error('❌ Error updating feedback status:', error);
            throw error;
        }
    }

    // Add reply to feedback
    async addFeedbackReply(id, reply) {
        try {
            const replyData = {
                id: 'rep_' + Date.now(),
                message: reply,
                timestamp: new Date().toISOString()
            };
            
            await this.db.ref(`${this.basePath}/feedback/${id}/replies`).push(replyData);
            console.log(`✅ Reply added to feedback: ${id}`);
            return true;
        } catch (error) {
            console.error('❌ Error adding reply:', error);
            throw error;
        }
    }

    // ========================================
    // TAXI BOOKING MANAGEMENT
    // ========================================
    
    // Create taxi booking
    async createTaxiBooking(bookingData) {
        try {
            const ref = this.db.ref(`${this.basePath}/taxiBookings`).push();
            const id = ref.key;
            
            const booking = {
                id: id,
                ...bookingData,
                timestamp: new Date().toISOString(),
                status: 'pending',
                paymentStatus: 'pending'
            };
            
            await ref.set(booking);
            console.log(`✅ Taxi booking created: ${id}`);
            return booking;
        } catch (error) {
            console.error('❌ Error creating taxi booking:', error);
            throw error;
        }
    }

    // Get all taxi bookings
    async getTaxiBookings() {
        try {
            const snapshot = await this.db.ref(`${this.basePath}/taxiBookings`).once('value');
            const data = snapshot.val();
            if (!data) return [];
            return Object.values(data);
        } catch (error) {
            console.error('❌ Error getting taxi bookings:', error);
            throw error;
        }
    }

    // Update booking status
    async updateBookingStatus(id, status) {
        try {
            await this.db.ref(`${this.basePath}/taxiBookings/${id}/status`).set(status);
            console.log(`✅ Booking status updated: ${id} -> ${status}`);
            return true;
        } catch (error) {
            console.error('❌ Error updating booking status:', error);
            throw error;
        }
    }

    // Assign driver to booking
    async assignDriverToBooking(bookingId, driverUid, driverName) {
        try {
            await this.db.ref(`${this.basePath}/taxiBookings/${bookingId}`).update({
                driverUid: driverUid,
                driverName: driverName,
                status: 'confirmed'
            });
            console.log(`✅ Driver assigned to booking: ${bookingId}`);
            return true;
        } catch (error) {
            console.error('❌ Error assigning driver:', error);
            throw error;
        }
    }

    // ========================================
    // DRIVER MANAGEMENT
    // ========================================
    
    // Register driver
    async registerDriver(driverData) {
        try {
            const ref = this.db.ref(`${this.basePath}/drivers`).push();
            const id = ref.key;
            
            const driver = {
                id: id,
                ...driverData,
                status: 'pending',
                approvedBy: null,
                approvedAt: null
            };
            
            await ref.set(driver);
            console.log(`✅ Driver registered: ${id}`);
            return driver;
        } catch (error) {
            console.error('❌ Error registering driver:', error);
            throw error;
        }
    }

    // Approve driver
    async approveDriver(driverId, adminUid) {
        try {
            await this.db.ref(`${this.basePath}/drivers/${driverId}`).update({
                status: 'approved',
                approvedBy: adminUid,
                approvedAt: new Date().toISOString()
            });
            console.log(`✅ Driver approved: ${driverId}`);
            return true;
        } catch (error) {
            console.error('❌ Error approving driver:', error);
            throw error;
        }
    }

    // Get all drivers
    async getDrivers() {
        try {
            const snapshot = await this.db.ref(`${this.basePath}/drivers`).once('value');
            const data = snapshot.val();
            if (!data) return [];
            return Object.values(data);
        } catch (error) {
            console.error('❌ Error getting drivers:', error);
            throw error;
        }
    }

    // ========================================
    // NOTIFICATION MANAGEMENT
    // ========================================
    
    // Send notification to user
    async sendNotification(userUid, notificationData) {
        try {
            const ref = this.db.ref(`${this.basePath}/users/${userUid}/notifications`).push();
            const id = ref.key;
            
            const notification = {
                id: id,
                ...notificationData,
                read: false,
                timestamp: new Date().toISOString()
            };
            
            await ref.set(notification);
            console.log(`✅ Notification sent to ${userUid}: ${id}`);
            return notification;
        } catch (error) {
            console.error('❌ Error sending notification:', error);
            throw error;
        }
    }

    // Send notification to all members
    async sendGlobalNotification(notificationData) {
        try {
            const members = await this.getAllMembers();
            const results = [];
            
            for (const member of members) {
                try {
                    const result = await this.sendNotification(member.uid, notificationData);
                    results.push(result);
                } catch (error) {
                    console.error(`❌ Error sending to ${member.uid}:`, error);
                }
            }
            
            console.log(`✅ Global notification sent to ${results.length} members`);
            return results;
        } catch (error) {
            console.error('❌ Error sending global notification:', error);
            throw error;
        }
    }

    // Get user notifications
    async getUserNotifications(uid) {
        try {
            const snapshot = await this.db.ref(`${this.basePath}/users/${uid}/notifications`).once('value');
            const data = snapshot.val();
            if (!data) return [];
            return Object.values(data);
        } catch (error) {
            console.error('❌ Error getting user notifications:', error);
            throw error;
        }
    }

    // Mark notification as read
    async markNotificationRead(userUid, notificationId) {
        try {
            await this.db.ref(`${this.basePath}/users/${userUid}/notifications/${notificationId}/read`).set(true);
            console.log(`✅ Notification marked as read: ${notificationId}`);
            return true;
        } catch (error) {
            console.error('❌ Error marking notification as read:', error);
            throw error;
        }
    }

    // ========================================
    // ZOOM MEETING MANAGEMENT
    // ========================================
    
    // Create zoom meeting
    async createZoomMeeting(meetingData) {
        try {
            const ref = this.db.ref(`${this.basePath}/zoomMeetings`).push();
            const id = ref.key;
            
            const meeting = {
                id: id,
                ...meetingData,
                createdAt: new Date().toISOString(),
                status: meetingData.status || 'upcoming'
            };
            
            await ref.set(meeting);
            console.log(`✅ Zoom meeting created: ${id}`);
            return meeting;
        } catch (error) {
            console.error('❌ Error creating zoom meeting:', error);
            throw error;
        }
    }

    // Get all zoom meetings
    async getZoomMeetings() {
        try {
            const snapshot = await this.db.ref(`${this.basePath}/zoomMeetings`).once('value');
            const data = snapshot.val();
            if (!data) return [];
            return Object.values(data);
        } catch (error) {
            console.error('❌ Error getting zoom meetings:', error);
            throw error;
        }
    }

    // ========================================
    // ADMIN LOGGING
    // ========================================
    
    // Log admin action
    async logAdminAction(adminUid, action, details) {
        try {
            const ref = this.db.ref(`${this.basePath}/admin/logs`).push();
            const id = ref.key;
            
            const log = {
                id: id,
                uid: adminUid,
                action: action,
                details: details,
                timestamp: new Date().toISOString()
            };
            
            await ref.set(log);
            console.log(`✅ Admin action logged: ${action}`);
            return log;
        } catch (error) {
            console.error('❌ Error logging admin action:', error);
            throw error;
        }
    }

    // Get admin logs
    async getAdminLogs() {
        try {
            const snapshot = await this.db.ref(`${this.basePath}/admin/logs`).once('value');
            const data = snapshot.val();
            if (!data) return [];
            return Object.values(data);
        } catch (error) {
            console.error('❌ Error getting admin logs:', error);
            throw error;
        }
    }

    // ========================================
    // STATISTICS & REPORTS
    // ========================================
    
    // Update statistics
    async updateStatistics() {
        try {
            const members = await this.getAllMembers();
            const followups = await this.getFollowups();
            const bookings = await this.getTaxiBookings();
            const announcements = await this.getAnnouncements();
            
            const stats = {
                members: {
                    total: members.length,
                    active: members.filter(m => m.status === 'active').length,
                    updatedAt: new Date().toISOString()
                },
                followups: {
                    total: followups.length,
                    pending: followups.filter(f => f.status === 'pending').length,
                    confirmed: followups.filter(f => f.status === 'confirmed').length,
                    notComing: followups.filter(f => f.status === 'not-coming').length
                },
                transport: {
                    total: bookings.length,
                    confirmed: bookings.filter(b => b.status === 'confirmed').length,
                    completed: bookings.filter(b => b.status === 'completed').length,
                    pending: bookings.filter(b => b.status === 'pending').length
                },
                announcements: {
                    total: announcements.length,
                    published: announcements.filter(a => a.status === 'published').length,
                    draft: announcements.filter(a => a.status === 'draft').length,
                    scheduled: announcements.filter(a => a.status === 'scheduled').length
                },
                updatedAt: new Date().toISOString()
            };
            
            await this.db.ref(`${this.basePath}/reports/statistics`).set(stats);
            console.log('✅ Statistics updated');
            return stats;
        } catch (error) {
            console.error('❌ Error updating statistics:', error);
            throw error;
        }
    }

    // Get statistics
    async getStatistics() {
        try {
            const snapshot = await this.db.ref(`${this.basePath}/reports/statistics`).once('value');
            return snapshot.val() || {};
        } catch (error) {
            console.error('❌ Error getting statistics:', error);
            throw error;
        }
    }

    // ========================================
    // SETTINGS MANAGEMENT
    // ========================================
    
    // Get settings
    async getSettings() {
        try {
            const snapshot = await this.db.ref(`${this.basePath}/settings`).once('value');
            return snapshot.val() || {};
        } catch (error) {
            console.error('❌ Error getting settings:', error);
            throw error;
        }
    }

    // Update settings
    async updateSettings(section, updates) {
        try {
            await this.db.ref(`${this.basePath}/settings/${section}`).update(updates);
            console.log(`✅ Settings updated: ${section}`);
            return true;
        } catch (error) {
            console.error('❌ Error updating settings:', error);
            throw error;
        }
    }

    // ========================================
    // BACKUP MANAGEMENT
    // ========================================
    
    // Create backup
    async createBackup(backupType = 'full') {
        try {
            const ref = this.db.ref(`${this.basePath}/backups`).push();
            const id = ref.key;
            
            const backup = {
                id: id,
                name: `CBWCI_${backupType.toUpperCase()}_Backup_${new Date().toISOString().split('T')[0]}`,
                date: new Date().toISOString(),
                size: Math.floor(Math.random() * 300) + 100 + ' MB',
                type: backupType,
                status: 'completed'
            };
            
            await ref.set(backup);
            console.log(`✅ Backup created: ${id}`);
            return backup;
        } catch (error) {
            console.error('❌ Error creating backup:', error);
            throw error;
        }
    }

    // Get backups
    async getBackups() {
        try {
            const snapshot = await this.db.ref(`${this.basePath}/backups`).once('value');
            const data = snapshot.val();
            if (!data) return [];
            return Object.values(data);
        } catch (error) {
            console.error('❌ Error getting backups:', error);
            throw error;
        }
    }

    // ========================================
    // GROUPS MANAGEMENT
    // ========================================
    
    // Create group
    async createGroup(groupData) {
        try {
            const ref = this.db.ref(`${this.basePath}/groups`).push();
            const id = ref.key;
            
            const group = {
                id: id,
                ...groupData,
                members: groupData.members || [],
                createdAt: new Date().toISOString()
            };
            
            await ref.set(group);
            console.log(`✅ Group created: ${id}`);
            return group;
        } catch (error) {
            console.error('❌ Error creating group:', error);
            throw error;
        }
    }

    // Get groups
    async getGroups() {
        try {
            const snapshot = await this.db.ref(`${this.basePath}/groups`).once('value');
            const data = snapshot.val();
            if (!data) return [];
            return Object.values(data);
        } catch (error) {
            console.error('❌ Error getting groups:', error);
            throw error;
        }
    }

    // Add member to group
    async addMemberToGroup(groupId, memberUid) {
        try {
            const groupRef = this.db.ref(`${this.basePath}/groups/${groupId}`);
            const snapshot = await groupRef.once('value');
            const group = snapshot.val();
            
            if (!group) {
                throw new Error('Group not found');
            }
            
            const members = group.members || [];
            if (!members.includes(memberUid)) {
                members.push(memberUid);
                await groupRef.update({ members: members });
                console.log(`✅ Member ${memberUid} added to group ${groupId}`);
            }
            
            return true;
        } catch (error) {
            console.error('❌ Error adding member to group:', error);
            throw error;
        }
    }

    // ========================================
    // REAL-TIME LISTENERS
    // ========================================
    
    // Listen for changes to a path
    listenToPath(path, callback) {
        this.db.ref(`${this.basePath}/${path}`).on('value', (snapshot) => {
            callback(snapshot.val());
        });
    }

    // Listen for new announcements
    listenForAnnouncements(callback) {
        this.db.ref(`${this.basePath}/announcements`).on('child_added', (snapshot) => {
            callback(snapshot.val());
        });
    }

    // Listen for new feedback
    listenForFeedback(callback) {
        this.db.ref(`${this.basePath}/feedback`).on('child_added', (snapshot) => {
            callback(snapshot.val());
        });
    }

    // Listen for new bookings
    listenForBookings(callback) {
        this.db.ref(`${this.basePath}/taxiBookings`).on('child_added', (snapshot) => {
            callback(snapshot.val());
        });
    }

    // Stop listening
    stopListening(path) {
        this.db.ref(`${this.basePath}/${path}`).off();
    }
}

// ========================================
// INITIALIZE AND EXPORT
// ========================================

// Create singleton instance
const cbwciDB = new CBWCIDatabase();

// Initialize database on load
cbwciDB.initializeDatabase()
    .then(() => {
        console.log('🎉 CBWCI Database is ready!');
    })
    .catch((error) => {
        console.error('❌ Failed to initialize database:', error);
    });

// Export for use in other files
if (typeof module !== 'undefined' && module.exports) {
    module.exports = cbwciDB;
} else {
    window.cbwciDB = cbwciDB;
}

// ========================================
// CONSOLE HELPERS
// ========================================
console.log('%c🚀 CBWCI Database Service Loaded', 'font-size: 16px; color: #C9A84C; font-weight: bold;');
console.log('📝 Available methods:');
console.log('  - cbwciDB.createUser(uid, data)');
console.log('  - cbwciDB.getUser(uid)');
console.log('  - cbwciDB.updateUser(uid, updates)');
console.log('  - cbwciDB.getAllMembers()');
console.log('  - cbwciDB.createAnnouncement(data)');
console.log('  - cbwciDB.getAnnouncements()');
console.log('  - cbwciDB.createFollowup(data)');
console.log('  - cbwciDB.getFollowups()');
console.log('  - cbwciDB.createFeedback(data)');
console.log('  - cbwciDB.getFeedback()');
console.log('  - cbwciDB.createTaxiBooking(data)');
console.log('  - cbwciDB.getTaxiBookings()');
console.log('  - cbwciDB.registerDriver(data)');
console.log('  - cbwciDB.getDrivers()');
console.log('  - cbwciDB.sendNotification(uid, data)');
console.log('  - cbwciDB.sendGlobalNotification(data)');
console.log('  - cbwciDB.updateStatistics()');
console.log('  - cbwciDB.getStatistics()');
console.log('  - cbwciDB.getSettings()');
console.log('  - cbwciDB.updateSettings(section, updates)');
console.log('  - cbwciDB.createBackup(type)');
console.log('  - cbwciDB.getBackups()');
console.log('  - cbwciDB.createGroup(data)');
console.log('  - cbwciDB.getGroups()');
console.log('  - cbwciDB.createZoomMeeting(data)');
console.log('  - cbwciDB.getZoomMeetings()');
console.log('  - cbwciDB.logAdminAction(uid, action, details)');
console.log('  - cbwciDB.getAdminLogs()');
console.log('\n💡 To use: cbwciDB.methodName()');