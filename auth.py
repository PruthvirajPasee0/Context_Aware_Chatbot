"""
Authentication module for user management
Handles user registration, login, and password hashing
"""

import sqlite3
import bcrypt
from pathlib import Path
from datetime import datetime

# Database file path
USER_DB_PATH = Path("users.db")

def init_user_db():
    """Initialize SQLite database for user management"""
    conn = sqlite3.connect(USER_DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()

def hash_password(password: str) -> str:
    """Hash password using bcrypt"""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    """Verify password against hash"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def register_user(username: str, password: str) -> tuple[bool, str]:
    """
    Register a new user
    Returns: (success: bool, message: str)
    """
    if not username or not password:
        return False, "Username and password are required"
    
    if len(username) < 3:
        return False, "Username must be at least 3 characters"
    
    if len(password) < 6:
        return False, "Password must be at least 6 characters"
    
    try:
        conn = sqlite3.connect(USER_DB_PATH)
        cursor = conn.cursor()
        
        # Check if username already exists
        cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
        if cursor.fetchone():
            conn.close()
            return False, "Username already exists"
        
        # Insert new user
        password_hash = hash_password(password)
        cursor.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (username, password_hash)
        )
        
        conn.commit()
        conn.close()
        return True, "Registration successful"
        
    except Exception as e:
        return False, f"Registration failed: {str(e)}"

def authenticate_user(username: str, password: str) -> tuple[bool, int, str]:
    """
    Authenticate user credentials
    Returns: (success: bool, user_id: int, message: str)
    """
    if not username or not password:
        return False, 0, "Username and password are required"
    
    try:
        conn = sqlite3.connect(USER_DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT id, password_hash FROM users WHERE username = ?",
            (username,)
        )
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return False, 0, "Invalid username or password"
        
        user_id, password_hash = result
        
        if verify_password(password, password_hash):
            return True, user_id, "Login successful"
        else:
            return False, 0, "Invalid username or password"
            
    except Exception as e:
        return False, 0, f"Authentication failed: {str(e)}"

def get_user_id(username: str) -> int:
    """Get user ID from username"""
    try:
        conn = sqlite3.connect(USER_DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
        result = cursor.fetchone()
        conn.close()
        
        return result[0] if result else 0
        
    except Exception as e:
        return 0

def get_username(user_id: int) -> str:
    """Get username from user ID"""
    try:
        conn = sqlite3.connect(USER_DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("SELECT username FROM users WHERE id = ?", (user_id,))
        result = cursor.fetchone()
        conn.close()
        
        return result[0] if result else ""
        
    except Exception as e:
        return ""

# Initialize database on module import
init_user_db()
