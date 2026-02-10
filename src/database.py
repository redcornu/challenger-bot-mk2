import sqlite3
import json
import logging
from contextlib import contextmanager
from typing import Optional, Dict, List, Any
from config import DB_PATH

logger = logging.getLogger(__name__)

@contextmanager
def get_db_connection():
    """데이터베이스 연결 컨텍스트 매니저 - 자동 commit/close"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def init_db():
    """테이블 초기화"""
    with get_db_connection() as conn:
        c = conn.cursor()

        # 도전 테이블
        c.execute('''
            CREATE TABLE IF NOT EXISTS duck_challenge (
                thread_id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                goal_text TEXT NOT NULL,
                state TEXT NOT NULL,
                streak INTEGER DEFAULT 0,
                growth_days INTEGER DEFAULT 0,
                total_days INTEGER DEFAULT 0,
                last_auth_date TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 유저 테이블
        c.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                ducks_raised INTEGER DEFAULT 0,
                gold INTEGER DEFAULT 0,
                inventory TEXT DEFAULT '{}',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 시스템 설정 테이블
        c.execute('''
            CREATE TABLE IF NOT EXISTS system_config (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')

        # 인덱스 생성 (성능 최적화)
        c.execute('CREATE INDEX IF NOT EXISTS idx_user_id ON duck_challenge(user_id)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_state ON duck_challenge(state)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_ranking ON users(ducks_raised DESC, gold DESC)')

def get_challenge(thread_id: int) -> Optional[Dict]:
    """도전 정보 조회"""
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM duck_challenge WHERE thread_id = ?", (thread_id,))
        row = c.fetchone()
        return dict(row) if row else None

def create_challenge(thread_id: int, user_id: int, goal_text: str) -> bool:
    """새로운 도전 생성"""
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute('''
                INSERT INTO duck_challenge (thread_id, user_id, goal_text, state, streak, growth_days, total_days)
                VALUES (?, ?, ?, 'EGG', 0, 0, 0)
            ''', (thread_id, user_id, goal_text))
            return True
    except sqlite3.IntegrityError:
        return False  # 이미 존재하는 도전

def update_challenge(thread_id: int, state: str = None, streak: int = None,
                     growth_days: int = None, total_days: int = None,
                     last_auth_date: str = None) -> bool:
    """도전 정보 업데이트"""
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            updates = []
            params = []

            if state is not None:
                updates.append("state = ?")
                params.append(state)
            if streak is not None:
                updates.append("streak = ?")
                params.append(streak)
            if growth_days is not None:
                updates.append("growth_days = ?")
                params.append(growth_days)
            if total_days is not None:
                updates.append("total_days = ?")
                params.append(total_days)
            if last_auth_date is not None:
                updates.append("last_auth_date = ?")
                params.append(last_auth_date)

            if not updates:
                return False

            params.append(thread_id)
            query = f"UPDATE duck_challenge SET {', '.join(updates)} WHERE thread_id = ?"
            c.execute(query, params)
            if c.rowcount == 0:
                logger.warning(f"Update affected 0 rows for challenge {thread_id}")
            return True
    except Exception as e:
        logger.error(f"Failed to update challenge {thread_id}: {type(e).__name__}: {e}")
        return False

def get_user(user_id: int) -> Optional[Dict]:
    """유저 정보 조회"""
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = c.fetchone()
        return dict(row) if row else None

def create_user(user_id: int, username: str) -> bool:
    """새로운 유저 생성"""
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute('''
                INSERT INTO users (user_id, username, ducks_raised, gold, inventory)
                VALUES (?, ?, 0, 0, '{}')
            ''', (user_id, username))
            return True
    except sqlite3.IntegrityError as e:
        logger.debug(f"User {user_id} already exists (expected): {e}")
        return False  # 이미 존재하는 유저 (정상)
    except Exception as e:
        logger.error(f"Failed to create user {user_id}: {type(e).__name__}: {e}")
        return False

def update_user_inventory(user_id: int, gold: int, inventory: str) -> bool:
    """유저 골드 및 인벤토리 업데이트"""
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute('''
                UPDATE users SET gold = ?, inventory = ?, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
            ''', (gold, inventory, user_id))
            if c.rowcount == 0:
                logger.warning(f"Update affected 0 rows for user {user_id}")
            return True
    except Exception as e:
        logger.error(f"Failed to update user {user_id} inventory: {type(e).__name__}: {e}")
        return False

def get_user_total_auth_days(user_id: int) -> int:
    """사용자의 모든 도전 total_days 합산"""
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('''
            SELECT COALESCE(SUM(total_days), 0) as total
            FROM duck_challenge
            WHERE user_id = ?
        ''', (user_id,))
        result = c.fetchone()
        return result['total'] if result else 0

def get_top_users(limit: int = 10) -> List[Dict]:
    """상위 유저 조회 - 졸업 오리 > 총 인증일 > 골드 순"""
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('''
            SELECT
                u.user_id,
                u.username,
                u.ducks_raised,
                u.gold,
                COALESCE(SUM(dc.total_days), 0) as total_auth_days
            FROM users u
            LEFT JOIN duck_challenge dc ON u.user_id = dc.user_id
            GROUP BY u.user_id
            ORDER BY u.ducks_raised DESC, total_auth_days DESC, u.gold DESC
            LIMIT ?
        ''', (limit,))
        return [dict(row) for row in c.fetchall()]

def get_user_challenges(user_id: int) -> List[Dict]:
    """특정 유저의 모든 도전 조회"""
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('''
            SELECT * FROM duck_challenge 
            WHERE user_id = ? 
            ORDER BY created_at DESC
        ''', (user_id,))
        return [dict(row) for row in c.fetchall()]

def update_challenge_admin(thread_id: int, state: str = None, 
                           streak: int = None, total_days: int = None) -> bool:
    """관리자용 도전 정보 업데이트 (검증 없이)"""
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            updates = []
            params = []

            if state is not None:
                updates.append("state = ?")
                params.append(state)
            if streak is not None:
                updates.append("streak = ?")
                params.append(streak)
            if total_days is not None:
                updates.append("total_days = ?")
                params.append(total_days)

            if not updates:
                return False

            params.append(thread_id)
            query = f"UPDATE duck_challenge SET {', '.join(updates)} WHERE thread_id = ?"
            c.execute(query, params)
            if c.rowcount == 0:
                logger.warning(f"Admin update affected 0 rows for challenge {thread_id}")
            return c.rowcount > 0
    except Exception as e:
        logger.error(f"Failed to admin update challenge {thread_id}: {type(e).__name__}: {e}")
        return False


def verify_database_integrity() -> Dict[str, Any]:
    """데이터베이스 무결성 검증

    Returns:
        dict: {
            'orphaned_count': int,
            'orphaned_challenges': List[Dict],
            'null_count': int,
            'is_valid': bool
        }
    """
    with get_db_connection() as conn:
        c = conn.cursor()

        # Orphaned challenges 확인
        c.execute('''
            SELECT COUNT(*) as cnt
            FROM duck_challenge dc
            LEFT JOIN users u ON dc.user_id = u.user_id
            WHERE u.user_id IS NULL
        ''')
        orphaned_count = c.fetchone()['cnt']

        # Orphaned challenges 상세 정보
        c.execute('''
            SELECT dc.thread_id, dc.user_id, dc.goal_text
            FROM duck_challenge dc
            LEFT JOIN users u ON dc.user_id = u.user_id
            WHERE u.user_id IS NULL
        ''')
        orphaned_challenges = [dict(row) for row in c.fetchall()]

        # NULL 값 확인
        c.execute('''
            SELECT COUNT(*) as cnt
            FROM duck_challenge
            WHERE user_id IS NULL OR goal_text IS NULL OR state IS NULL
        ''')
        null_count = c.fetchone()['cnt']

        return {
            'orphaned_count': orphaned_count,
            'orphaned_challenges': orphaned_challenges,
            'null_count': null_count,
            'is_valid': orphaned_count == 0 and null_count == 0
        }
