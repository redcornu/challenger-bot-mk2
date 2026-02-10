#!/usr/bin/env python3
"""
백업 DB를 새 스키마로 변환하는 스크립트

백업 DB (구 스키마) → 임시 DB (신 스키마)
"""

import sqlite3
import json
from datetime import datetime
import sys

BACKUP_DB = "/Users/mac/Documents/자료/요진편/Challenger/백업/challenge.db"
NEW_DB = "data/bot_new.db"

def create_new_schema():
    """새 스키마로 빈 DB 생성"""
    conn = sqlite3.connect(NEW_DB)
    c = conn.cursor()

    # duck_challenge 테이블
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

    # users 테이블
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

    # system_config 테이블
    c.execute('''
        CREATE TABLE IF NOT EXISTS system_config (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')

    # 인덱스 생성
    c.execute('CREATE INDEX IF NOT EXISTS idx_user_id ON duck_challenge(user_id)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_state ON duck_challenge(state)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_ranking ON users(ducks_raised DESC, gold DESC)')

    conn.commit()
    conn.close()
    print("✅ 새 스키마 생성 완료")

def migrate_users():
    """유저 데이터 마이그레이션"""
    backup_conn = sqlite3.connect(BACKUP_DB)
    backup_conn.row_factory = sqlite3.Row
    bc = backup_conn.cursor()

    new_conn = sqlite3.connect(NEW_DB)
    nc = new_conn.cursor()

    bc.execute("SELECT * FROM users")
    users = bc.fetchall()

    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    migrated = 0

    for user in users:
        try:
            nc.execute('''
                INSERT INTO users (user_id, username, ducks_raised, gold, inventory, created_at, updated_at)
                VALUES (?, NULL, ?, ?, ?, ?, ?)
            ''', (
                user['user_id'],
                user['ducks_raised'],
                user['gold'],
                user['inventory'],
                now,
                now
            ))
            migrated += 1
        except sqlite3.IntegrityError as e:
            print(f"⚠️  유저 {user['user_id']} 중복: {e}")

    new_conn.commit()
    backup_conn.close()
    new_conn.close()

    print(f"✅ {migrated}명 유저 마이그레이션 완료")
    return migrated

def handle_orphaned_challenges():
    """Orphaned challenges 처리"""
    backup_conn = sqlite3.connect(BACKUP_DB)
    backup_conn.row_factory = sqlite3.Row
    bc = backup_conn.cursor()

    # Orphaned challenges 찾기
    bc.execute('''
        SELECT dc.thread_id, dc.user_id, dc.goal_text
        FROM duck_challenge dc
        LEFT JOIN users u ON dc.user_id = u.user_id
        WHERE u.user_id IS NULL
    ''')
    orphaned = bc.fetchall()

    if not orphaned:
        print("✅ Orphaned challenges 없음")
        backup_conn.close()
        return []

    print(f"\n⚠️  {len(orphaned)}개의 orphaned challenges 발견:")
    for row in orphaned:
        print(f"  - thread_id={row['thread_id']}, user_id={row['user_id']}, goal={row['goal_text']}")

    print("\n처리 방법을 선택하세요:")
    print("  1. 유저 생성 (Unknown User로)")
    print("  2. 챌린지 삭제 (권장)")
    print("  3. 건너뛰기 (마이그레이션하지 않음)")

    choice = input("\n선택 (1/2/3): ").strip()

    if choice == '1':
        # 유저 생성
        new_conn = sqlite3.connect(NEW_DB)
        nc = new_conn.cursor()
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        for row in orphaned:
            try:
                nc.execute('''
                    INSERT INTO users (user_id, username, ducks_raised, gold, inventory, created_at, updated_at)
                    VALUES (?, '[Unknown User]', 0, 0, '{}', ?, ?)
                ''', (row['user_id'], now, now))
                print(f"  ✅ user_id={row['user_id']} 생성")
            except sqlite3.IntegrityError:
                print(f"  ℹ️  user_id={row['user_id']} 이미 존재")

        new_conn.commit()
        new_conn.close()
        skip_threads = []

    elif choice == '2':
        # 챌린지 삭제 (마이그레이션하지 않음)
        skip_threads = [row['thread_id'] for row in orphaned]
        print(f"  ✅ {len(skip_threads)}개 챌린지 건너뛰기")

    else:
        # 건너뛰기
        skip_threads = [row['thread_id'] for row in orphaned]
        print(f"  ⚠️  {len(skip_threads)}개 챌린지 마이그레이션하지 않음")

    backup_conn.close()
    return skip_threads

def migrate_challenges(skip_threads=None):
    """챌린지 데이터 마이그레이션"""
    if skip_threads is None:
        skip_threads = []

    backup_conn = sqlite3.connect(BACKUP_DB)
    backup_conn.row_factory = sqlite3.Row
    bc = backup_conn.cursor()

    new_conn = sqlite3.connect(NEW_DB)
    nc = new_conn.cursor()

    bc.execute("SELECT * FROM duck_challenge")
    challenges = bc.fetchall()

    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    migrated = 0
    skipped = 0

    for ch in challenges:
        if ch['thread_id'] in skip_threads:
            skipped += 1
            continue

        try:
            # sulky_days → growth_days 변환
            growth_days = ch.get('sulky_days', 0)

            nc.execute('''
                INSERT INTO duck_challenge (
                    thread_id, user_id, goal_text, state,
                    streak, growth_days, total_days,
                    last_auth_date, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                ch['thread_id'],
                ch['user_id'],
                ch['goal_text'],
                ch['state'],
                ch['streak'],
                growth_days,
                ch['total_days'],
                ch['last_auth_date'],
                now
            ))
            migrated += 1
        except sqlite3.IntegrityError as e:
            print(f"⚠️  챌린지 {ch['thread_id']} 중복: {e}")

    new_conn.commit()
    backup_conn.close()
    new_conn.close()

    print(f"✅ {migrated}개 챌린지 마이그레이션 완료 ({skipped}개 건너뜀)")
    return migrated

def verify_new_db():
    """새 DB 검증"""
    conn = sqlite3.connect(NEW_DB)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    print("\n=== 새 DB 검증 ===")

    # 통계
    c.execute("SELECT COUNT(*) as cnt FROM users")
    user_count = c.fetchone()['cnt']

    c.execute("SELECT COUNT(*) as cnt FROM duck_challenge")
    challenge_count = c.fetchone()['cnt']

    c.execute("SELECT SUM(gold) as total FROM users")
    total_gold = c.fetchone()['total'] or 0

    print(f"유저 수: {user_count}명")
    print(f"챌린지 수: {challenge_count}개")
    print(f"총 골드: {total_gold}G")

    # Orphaned 확인
    c.execute('''
        SELECT COUNT(*) as cnt
        FROM duck_challenge dc
        LEFT JOIN users u ON dc.user_id = u.user_id
        WHERE u.user_id IS NULL
    ''')
    orphaned_count = c.fetchone()['cnt']

    if orphaned_count > 0:
        print(f"⚠️  Orphaned challenges: {orphaned_count}개")
        return False
    else:
        print("✅ Orphaned challenges 없음")

    # NULL 확인
    c.execute('''
        SELECT COUNT(*) as cnt
        FROM duck_challenge
        WHERE user_id IS NULL OR goal_text IS NULL OR state IS NULL
    ''')
    null_count = c.fetchone()['cnt']

    if null_count > 0:
        print(f"⚠️  NULL 값: {null_count}개")
        return False
    else:
        print("✅ 필수 필드 모두 채워짐")

    conn.close()
    return True

def main():
    """메인 실행 함수"""
    print("="*60)
    print("백업 DB → 새 스키마 변환")
    print("="*60)
    print(f"\n백업 DB: {BACKUP_DB}")
    print(f"새 DB: {NEW_DB}\n")

    try:
        # 1. 새 스키마 생성
        print("[1/5] 새 스키마 생성 중...")
        create_new_schema()

        # 2. 유저 마이그레이션
        print("\n[2/5] 유저 마이그레이션 중...")
        user_count = migrate_users()

        # 3. Orphaned challenges 처리
        print("\n[3/5] Orphaned challenges 처리 중...")
        skip_threads = handle_orphaned_challenges()

        # 4. 챌린지 마이그레이션
        print("\n[4/5] 챌린지 마이그레이션 중...")
        challenge_count = migrate_challenges(skip_threads)

        # 5. 검증
        print("\n[5/5] 새 DB 검증 중...")
        if verify_new_db():
            print("\n" + "="*60)
            print("✅ 변환 완료!")
            print("="*60)
            print(f"\n새 DB 위치: {NEW_DB}")
            print(f"유저: {user_count}명")
            print(f"챌린지: {challenge_count}개")
            print("\n다음 단계: ./scripts/replace_database.sh 실행")
            return 0
        else:
            print("\n❌ 검증 실패")
            return 1

    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
