# admin_init.py
# Run this script once to set up predefined admin users and fix existing users

import firebase_admin
from firebase_admin import credentials, auth, db
import json
import os
import getpass

from config import Config, SERVER_TIMESTAMP

# ========================================
# FIREBASE ADMIN INITIALIZATION
# ========================================

# Path to your service account key
# Download from: Firebase Console → Project Settings → Service Accounts → Generate New Private Key
SERVICE_ACCOUNT_PATH = Config.FIREBASE_CREDENTIALS

def initialize_firebase():
    """Initialize Firebase Admin SDK"""
    try:
        if not os.path.exists(SERVICE_ACCOUNT_PATH):
            print(f"❌ Service account file not found: {SERVICE_ACCOUNT_PATH}")
            print("Please download the service account key from Firebase Console")
            return None, None
        
        cred = credentials.Certificate(SERVICE_ACCOUNT_PATH)
        firebase_admin.initialize_app(cred, {
            'databaseURL': Config.FIREBASE_DATABASE_URL
        })
        print("✅ Firebase Admin SDK initialized")
        return auth, db
    except Exception as e:
        print(f"❌ Error initializing Firebase: {e}")
        return None, None

# ========================================
# PREDEFINED ADMIN USERS
# ========================================

PREDEFINED_ADMINS = [
    {
        "email": "siyanda_SuperAdmin@cbwci.org",
        "password_env": "SUPERADMIN_PASSWORD",
        "fullName": "Siyanda SuperAdmin",
        "phone": "+27 82 111 2222",
        "role": "super_admin",
        "status": "active"
    },
    {
        "email": "ReverendSekgobela@cbwci.org",
        "password_env": "ADMIN_PASSWORD",
        "fullName": "Reverend Sekgobela",
        "phone": "+27 82 222 3333",
        "role": "admin",
        "status": "active"
    }
]

# ========================================
# FIX EXISTING USERS (AUTH BUT NOT IN DB)
# ========================================

def fix_existing_users(auth, db):
    """Fix existing users who are in Auth but not in Database"""
    try:
        print("\n" + "=" * 60)
        print("🔧 FIXING EXISTING USERS (Auth → Database)")
        print("=" * 60)
        
        # Get all users from Auth
        users_list = auth.list_users().users
        
        if not users_list:
            print("ℹ️ No users found in Auth")
            return 0
        
        print(f"📊 Found {len(users_list)} users in Auth")
        
        fixed_count = 0
        for user in users_list:
            email = user.email
            uid = user.uid
            predefined_admin = next(
                (
                    admin_data for admin_data in PREDEFINED_ADMINS
                    if admin_data['email'].strip().lower() == email.strip().lower()
                ),
                None
            )
            role = predefined_admin.get('role', 'admin') if predefined_admin else 'member'
            status = predefined_admin.get('status', 'active') if predefined_admin else 'active'
            
            # Check if user exists in database
            user_ref = db.reference(f'cbwci/users/{uid}')
            user_data = user_ref.get()

            if user_data and predefined_admin:
                user_ref.update({
                    'role': role,
                    'status': status,
                    'isPredefined': True,
                    'updatedAt': SERVER_TIMESTAMP
                })
                db.reference(f'cbwci/members/{uid}').update({
                    'role': role,
                    'status': status,
                    'isPredefined': True
                })
                print(f"   ✅ Updated predefined admin role for {email}: {role}")
                continue
            
            if not user_data:
                print(f"📝 Fixing user: {email} (UID: {uid})")
                
                # Create user data
                user_data = {
                    "uid": uid,
                    "fullName": user.display_name or email.split('@')[0],
                    "email": email,
                    "phone": "",
                    "role": role,
                    "status": status,
                    "isPredefined": predefined_admin is not None,
                    "createdAt": SERVER_TIMESTAMP,
                    "updatedAt": SERVER_TIMESTAMP,
                    "preferences": {
                        "notifications": True,
                        "taxi": True,
                        "language": "English"
                    },
                    "groups": []
                }
                
                # Save to users collection
                user_ref.set(user_data)
                print(f"   ✅ User data saved to cbwci/users/{uid}")
                
                # Save to members collection
                member_data = {
                    "uid": uid,
                    "fullName": user.display_name or email.split('@')[0],
                    "email": email,
                    "phone": "",
                    "role": role,
                    "status": status,
                    "isPredefined": predefined_admin is not None,
                    "dateJoined": SERVER_TIMESTAMP
                }
                member_ref = db.reference(f'cbwci/members/{uid}')
                member_ref.set(member_data)
                print(f"   ✅ Member data saved to cbwci/members/{uid}")
                
                fixed_count += 1
                print(f"   ✅ Fixed user: {email}\n")
        
        print(f"\n✅ Fixed {fixed_count} users")
        return fixed_count
        
    except Exception as e:
        print(f"❌ Error fixing users: {e}")
        return 0

# ========================================
# FIX A SINGLE USER BY EMAIL
# ========================================

def fix_user_by_email(auth, db, email):
    """Fix a single user by email"""
    try:
        print(f"\n🔧 Fixing user: {email}")
        
        # Get user by email
        try:
            user = auth.get_user_by_email(email)
            uid = user.uid
            print(f"   ✅ User found in Auth: {uid}")
        except firebase_admin.auth.UserNotFoundError:
            print(f"   ❌ User not found in Auth: {email}")
            return False
        
        # Check if user exists in database
        user_ref = db.reference(f'cbwci/users/{uid}')
        user_data = user_ref.get()
        
        if user_data:
            print(f"   ℹ️ User already exists in database")
            return True
        
        # Create user data
        user_data = {
            "uid": uid,
            "fullName": user.display_name or email.split('@')[0],
            "email": email,
            "phone": "",
            "role": "member",
            "status": "active",
            "isPredefined": False,
            "createdAt": SERVER_TIMESTAMP,
            "updatedAt": SERVER_TIMESTAMP,
            "preferences": {
                "notifications": True,
                "taxi": True,
                "language": "English"
            },
            "groups": []
        }
        
        # Save to users collection
        user_ref.set(user_data)
        print(f"   ✅ User data saved to cbwci/users/{uid}")
        
        # Save to members collection
        member_data = {
            "uid": uid,
            "fullName": user.display_name or email.split('@')[0],
            "email": email,
            "phone": "",
            "role": "member",
            "status": "active",
            "dateJoined": SERVER_TIMESTAMP
        }
        member_ref = db.reference(f'cbwci/members/{uid}')
        member_ref.set(member_data)
        print(f"   ✅ Member data saved to cbwci/members/{uid}")
        
        print(f"   ✅ User fixed: {email}")
        return True
        
    except Exception as e:
        print(f"   ❌ Error fixing user: {e}")
        return False

# ========================================
# CREATE PREDEFINED ADMIN USERS
# ========================================

def get_admin_password(admin_data):
    """Passwords are never stored in the code: read from the environment or ask."""
    password = os.environ.get(admin_data.get('password_env', ''), '')
    if not password:
        password = getpass.getpass(f"Password for {admin_data['email']} (min 6 chars): ")
    return password


def create_admin_user(auth, db, admin_data):
    """Create a predefined admin user"""
    try:
        email = admin_data.get('email')
        full_name = admin_data.get('fullName')
        phone = admin_data.get('phone')
        role = admin_data.get('role', 'admin')
        status = admin_data.get('status', 'active')

        print(f"🔄 Creating admin: {email}")

        # Step 1: Check if user already exists in Auth
        try:
            user = auth.get_user_by_email(email)
            print(f"   ℹ️ User already exists in Auth: {user.uid}")
            uid = user.uid
        except firebase_admin.auth.UserNotFoundError:
            # Step 2: Create user in Firebase Auth
            user = auth.create_user(
                email=email,
                password=get_admin_password(admin_data),
                display_name=full_name,
                email_verified=True  # Auto-verify admin emails
            )
            uid = user.uid
            print(f"   ✅ User created in Auth: {uid}")

        # Step 3: Save/Update user data in Realtime Database
        user_data = {
            "uid": uid,
            "fullName": full_name,
            "email": email,
            "phone": phone,
            "role": role,
            "status": status,
            "isPredefined": True,  # Flag to identify predefined users
            "createdAt": SERVER_TIMESTAMP,
            "updatedAt": SERVER_TIMESTAMP,
            "preferences": {
                "notifications": True,
                "taxi": True,
                "language": "English"
            },
            "groups": []
        }

        # Save to users collection
        user_ref = db.reference(f'cbwci/users/{uid}')
        user_ref.update(user_data)

        # Save to members collection (for quick access)
        member_data = {
            "uid": uid,
            "fullName": full_name,
            "email": email,
            "phone": phone,
            "role": role,
            "status": status,
            "dateJoined": SERVER_TIMESTAMP,
            "isPredefined": True
        }
        member_ref = db.reference(f'cbwci/members/{uid}')
        member_ref.set(member_data)

        # Step 4: Log admin creation
        log_data = {
            "uid": uid,
            "email": email,
            "action": "Admin Account Created",
            "details": f"Predefined admin account created for {full_name} with role: {role}",
            "timestamp": SERVER_TIMESTAMP,
            "type": "system"
        }
        log_ref = db.reference(f'cbwci/admin/logs/system')
        log_ref.push(log_data)

        print(f"   ✅ Admin user saved to database: {email}")
        print(f"   👑 Role: {role}")
        print(f"   🔑 UID: {uid}")
        print("   " + "-" * 40)
        
        return True, uid

    except Exception as e:
        print(f"   ❌ Error creating admin {email}: {e}")
        return False, None

# ========================================
# UPDATE STATISTICS
# ========================================

def update_statistics(db):
    """Update statistics after adding admins"""
    try:
        # Get all users
        users_ref = db.reference('cbwci/users')
        users_snapshot = users_ref.get()
        
        if not users_snapshot:
            return
        
        members_count = 0
        admin_count = 0
        driver_count = 0
        
        for uid, data in users_snapshot.items():
            role = data.get('role', 'member')
            status = data.get('status', 'active')
            
            if status == 'active':
                if role in ['admin', 'super_admin']:
                    admin_count += 1
                elif role == 'driver':
                    driver_count += 1
                else:
                    members_count += 1
        
        # Update statistics
        stats = {
            "members": {
                "total": members_count,
                "active": members_count,
                "admins": admin_count,
                "drivers": driver_count,
                "updatedAt": SERVER_TIMESTAMP
            }
        }
        
        stats_ref = db.reference('cbwci/reports/statistics')
        stats_ref.update(stats)
        print(f"   ✅ Statistics updated: {members_count} members, {admin_count} admins, {driver_count} drivers")
        
    except Exception as e:
        print(f"   ❌ Error updating statistics: {e}")

# ========================================
# LIST ALL ADMIN USERS
# ========================================

def list_admins(db):
    """List all predefined admin users"""
    try:
        users_ref = db.reference('cbwci/users')
        users_snapshot = users_ref.get()
        
        if not users_snapshot:
            print("❌ No users found")
            return
        
        print("\n" + "=" * 60)
        print("📋 PREDEFINED ADMIN USERS")
        print("=" * 60)
        
        for uid, data in users_snapshot.items():
            if data.get('isPredefined') and data.get('role') in ['admin', 'super_admin']:
                print(f"\n👑 {data.get('fullName')}")
                print(f"   📧 {data.get('email')}")
                print(f"   🔑 Role: {data.get('role')}")
                print(f"   📱 Phone: {data.get('phone', 'N/A')}")
                print(f"   🆔 UID: {uid}")
                print("   " + "-" * 40)
    
    except Exception as e:
        print(f"❌ Error listing admins: {e}")

# ========================================
# DELETE ADMIN USER
# ========================================

def delete_admin(auth, db, email):
    """Delete an admin user"""
    try:
        print(f"🔄 Deleting admin: {email}")
        
        # Find user by email
        try:
            user = auth.get_user_by_email(email)
            uid = user.uid
            
            # Delete from Auth
            auth.delete_user(uid)
            print(f"   ✅ User deleted from Auth")
            
            # Delete from Database
            user_ref = db.reference(f'cbwci/users/{uid}')
            user_ref.delete()
            
            member_ref = db.reference(f'cbwci/members/{uid}')
            member_ref.delete()
            
            print(f"   ✅ User deleted from Database")
            print(f"   ✅ Admin {email} deleted successfully")
            
        except firebase_admin.auth.UserNotFoundError:
            print(f"   ❌ User not found in Auth")
            
    except Exception as e:
        print(f"   ❌ Error deleting admin: {e}")

# ========================================
# RESET A PASSWORD
# ========================================

def reset_password(auth, email):
    """Set a new password for an existing account (typed hidden, never stored)."""
    try:
        user = auth.get_user_by_email(email)
    except firebase_admin.auth.UserNotFoundError:
        print(f"   ❌ No account found for {email}")
        return
    new_password = getpass.getpass("New password (min 6 chars): ")
    confirm = getpass.getpass("Repeat new password: ")
    if new_password != confirm:
        print("   ❌ Passwords do not match")
        return
    try:
        auth.update_user(user.uid, password=new_password)
        print(f"   ✅ Password updated for {email}")
    except Exception as e:
        print(f"   ❌ Could not update password: {e}")

# ========================================
# MENU
# ========================================

def show_menu():
    print("\n" + "=" * 60)
    print("👑 CBWCI - Admin Management")
    print("=" * 60)
    print("\nSelect an option:")
    print("1. Fix all users (Auth → Database)")
    print("2. Create predefined admins")
    print("3. Fix a specific user by email")
    print("4. List all admin users")
    print("5. Delete an admin user")
    print("6. Run full setup (Fix users + Create admins)")
    print("7. Reset a user's password")
    print("8. Exit")
    print("-" * 60)

# ========================================
# MAIN EXECUTION
# ========================================

def main():
    # Initialize Firebase
    auth, db = initialize_firebase()
    if not auth or not db:
        return
    
    while True:
        show_menu()
        choice = input("\nEnter your choice (1-8): ").strip()
        
        if choice == '1':
            # Fix all users
            fix_existing_users(auth, db)
            
        elif choice == '2':
            # Create predefined admins
            print(f"\n📋 Creating {len(PREDEFINED_ADMINS)} predefined admin users...\n")
            success_count = 0
            for admin_data in PREDEFINED_ADMINS:
                success, uid = create_admin_user(auth, db, admin_data)
                if success:
                    success_count += 1
            
            if success_count > 0:
                update_statistics(db)
            print(f"\n✅ Created {success_count} admin users")
            
        elif choice == '3':
            # Fix a specific user
            email = input("Enter the user's email: ").strip()
            fix_user_by_email(auth, db, email)
            
        elif choice == '4':
            # List all admins
            list_admins(db)
            
        elif choice == '5':
            # Delete an admin
            email = input("Enter the admin's email to delete: ").strip()
            confirm = input(f"Are you sure you want to delete {email}? (yes/no): ").strip()
            if confirm.lower() == 'yes':
                delete_admin(auth, db, email)
            else:
                print("❌ Deletion cancelled")
                
        elif choice == '6':
            # Full setup
            print("\n🚀 Running full setup...")
            
            # Step 1: Fix all users
            fixed = fix_existing_users(auth, db)
            print(f"\n✅ Fixed {fixed} users\n")
            
            # Step 2: Create admins
            print(f"📋 Creating {len(PREDEFINED_ADMINS)} predefined admin users...\n")
            success_count = 0
            for admin_data in PREDEFINED_ADMINS:
                success, uid = create_admin_user(auth, db, admin_data)
                if success:
                    success_count += 1
            
            if success_count > 0:
                update_statistics(db)
            
            print(f"\n✅ Created {success_count} admin users")
            list_admins(db)
            print("\n" + "=" * 60)
            print("✅ Full setup completed!")
            print("=" * 60)
            print("\n🔐 Admin Login Credentials:")
            for admin in PREDEFINED_ADMINS:
                print(f"   📧 {admin['email']} | 👑 Role: {admin['role']}")
                print("   🔑 Password: the one you entered / set in .env")
                print()
            
        elif choice == '7':
            email = input("Enter the account's email: ").strip()
            reset_password(auth, email)

        elif choice == '8':
            print("👋 Exiting...")
            break
            
        else:
            print("❌ Invalid choice. Please try again.")
        
        input("\nPress Enter to continue...")

# ========================================
# RUN
# ========================================

if __name__ == "__main__":
    main()