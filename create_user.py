"""
Run this on the server to create a login for a staff member or admin.
There's no public sign-up page on purpose - accounts are created by
whoever runs the server.

Usage:
    python create_user.py
"""
import getpass
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.database import init_db, get_connection
from app.security import hash_password


def main():
    init_db()
    username = input("Username: ").strip()
    if not username:
        print("Username can't be empty.")
        return
    password = getpass.getpass("Password: ")
    if len(password) < 6:
        print("Use at least 6 characters.")
        return
    role = input("Role [staff/admin] (default staff): ").strip().lower() or "staff"
    if role not in ("staff", "admin"):
        print("Role must be 'staff' or 'admin'.")
        return

    pw_hash, salt = hash_password(password)
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO users (username, password_hash, salt, role) VALUES (?, ?, ?, ?)",
            (username, pw_hash, salt, role),
        )
        conn.commit()
        print(f"Created {role} user '{username}'.")
    except sqlite3.IntegrityError:
        print(f"Username '{username}' already exists.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
