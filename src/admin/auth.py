from functools import wraps
from flask import session, redirect, url_for, flash
from werkzeug.security import check_password_hash, generate_password_hash
import os

admin_password = os.getenv('ADMIN_PASSWORD')
if not admin_password or admin_password in {'admin1234', 'your_secure_password_here'}:
    raise RuntimeError("ADMIN_PASSWORD가 안전한 값으로 설정되어야 합니다.")

ADMIN_PASSWORD_HASH = generate_password_hash(admin_password)

def login_required(f):
    """로그인 필수 데코레이터"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            flash('로그인이 필요합니다.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def verify_password(password: str) -> bool:
    """비밀번호 검증"""
    return check_password_hash(ADMIN_PASSWORD_HASH, password)
