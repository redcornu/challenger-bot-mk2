"""
Flask 서버 생명주기 관리 Hook

Discord 봇 시작 시 Flask 서버를 자동으로 시작하고,
봇 종료 시 Flask 서버도 안전하게 종료합니다.
"""

import subprocess
import os
import sys
import time
import signal
import logging
import requests
from pathlib import Path

logger = logging.getLogger(__name__)

# Flask 서버 프로세스 저장
flask_process = None
flask_pid_file = Path('.flask.pid')


def check_dependencies():
    """필수 의존성 확인"""
    try:
        import flask
        import werkzeug
        return True
    except ImportError as e:
        logger.error(f"Flask 의존성 누락: {e}")
        return False


def validate_env():
    """환경 변수 검증"""
    admin_password = os.getenv('ADMIN_PASSWORD')
    flask_secret = os.getenv('FLASK_SECRET_KEY')
    
    if not admin_password or admin_password == 'your_secure_password_here':
        logger.warning("⚠️  ADMIN_PASSWORD가 설정되지 않았습니다.")
        return False
    
    if not flask_secret or flask_secret == 'your-random-secret-key-here':
        logger.warning("⚠️  FLASK_SECRET_KEY가 설정되지 않았습니다.")
        return False
    
    return True


def health_check(url=None, retries=5, delay=1):
    """
    Flask 서버 헬스 체크

    Args:
        url: 확인할 URL (None이면 환경 변수에서 포트 읽기)
        retries: 재시도 횟수
        delay: 재시도 간 대기 시간 (초)

    Returns:
        bool: 서버 응답 여부
    """
    if url is None:
        port = os.getenv('FLASK_PORT', '5001')
        url = f'http://localhost:{port}'

    for i in range(retries):
        try:
            response = requests.get(url, timeout=5)
            if response.status_code in [200, 302]:  # 200 OK 또는 302 Redirect
                return True
        except requests.RequestException:
            if i < retries - 1:
                time.sleep(delay)
    return False


def start_flask_server():
    """Flask 서버를 백그라운드로 시작"""
    global flask_process
    
    logger.info("🔧 Flask 서버 시작 중...")
    
    # 1. 의존성 확인
    if not check_dependencies():
        logger.error("❌ Flask 의존성이 설치되지 않았습니다. 'pip install -r requirements.txt' 실행 필요.")
        return False
    
    # 2. 환경 변수 검증
    if not validate_env():
        logger.error("❌ 환경 변수가 올바르게 설정되지 않았습니다. .env 파일 확인 필요.")
        return False
    
    # 3. PID 파일 기준 실행 중인지 확인
    if flask_pid_file.exists():
        try:
            with open(flask_pid_file, 'r') as f:
                pid = int(f.read().strip())
            # 프로세스가 실행 중인지 확인
            os.kill(pid, 0)  # 시그널 0: 프로세스 존재 확인
            logger.warning(f"⚠️  Flask 서버가 이미 실행 중입니다 (PID: {pid}).")
            return True
        except (OSError, ValueError):
            # 프로세스가 존재하지 않으면 PID 파일 삭제
            flask_pid_file.unlink()

    # 4. 외부(systemd 등)에서 이미 실행 중인 경우 중복 실행 방지
    if health_check(retries=1, delay=0):
        logger.info("ℹ️ Flask 서버가 이미 응답 중입니다. (외부 프로세스 관리로 판단, 시작 건너뜀)")
        return True
    
    # 5. 로그 디렉토리 생성
    os.makedirs('logs', exist_ok=True)
    
    # 6. Flask 서버 시작
    try:
        flask_app_path = os.path.join(os.path.dirname(__file__), '..', 'admin', 'app.py')
        flask_app_path = os.path.abspath(flask_app_path)
        
        with open('logs/flask.log', 'a') as log_file:
            flask_process = subprocess.Popen(
                [sys.executable, flask_app_path],
                stdout=log_file,
                stderr=subprocess.STDOUT,
                start_new_session=True  # 독립 프로세스 그룹 생성
            )
        
        # PID 저장
        with open(flask_pid_file, 'w') as f:
            f.write(str(flask_process.pid))
        
        logger.info(f"🚀 Flask 서버 시작됨 (PID: {flask_process.pid})")
        
        # 7. 헬스 체크
        time.sleep(2)  # 초기 시작 대기
        port = os.getenv('FLASK_PORT', '5001')
        if health_check():
            logger.info(f"✅ Flask 대시보드가 시작되었습니다: http://localhost:{port}")
            return True
        else:
            logger.warning("⚠️  Flask 서버가 아직 준비되지 않았습니다. 잠시 후 다시 확인하세요.")
            return True  # 프로세스는 시작되었으므로 True 반환
        
    except Exception as e:
        logger.error(f"❌ Flask 서버 시작 실패: {e}", exc_info=True)
        return False


def stop_flask_server():
    """Flask 서버를 안전하게 종료"""
    global flask_process
    
    logger.info("🛑 Flask 서버 종료 중...")
    
    # PID 파일에서 프로세스 ID 읽기
    if flask_pid_file.exists():
        try:
            with open(flask_pid_file, 'r') as f:
                pid = int(f.read().strip())
            
            # SIGTERM으로 안전하게 종료
            os.kill(pid, signal.SIGTERM)
            
            # 종료 대기 (최대 10초)
            for _ in range(10):
                try:
                    os.kill(pid, 0)  # 프로세스 존재 확인
                    time.sleep(1)
                except OSError:
                    # 프로세스가 종료됨
                    logger.info("✅ Flask 서버가 종료되었습니다.")
                    flask_pid_file.unlink()
                    flask_process = None
                    return True
            
            # 강제 종료
            logger.warning("⚠️  정상 종료 실패. 강제 종료 중...")
            os.kill(pid, signal.SIGKILL)
            flask_pid_file.unlink()
            flask_process = None
            logger.info("✅ Flask 서버가 강제 종료되었습니다.")
            return True
            
        except Exception as e:
            logger.error(f"❌ Flask 서버 종료 실패: {e}")
            return False
    else:
        # PID 파일이 없으면 외부 프로세스일 수 있으므로 종료를 시도하지 않음
        if health_check(retries=1, delay=0):
            logger.info("ℹ️ Flask 서버는 응답 중이지만 PID 파일이 없습니다. (외부 관리로 판단, 종료 건너뜀)")
            return True
        logger.warning("⚠️  Flask 서버 PID 파일이 없습니다.")
        return False


def on_bot_start():
    """봇 시작 시 호출되는 Hook"""
    return start_flask_server()


def on_bot_stop():
    """봇 종료 시 호출되는 Hook"""
    return stop_flask_server()
