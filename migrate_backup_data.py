"""
백업 데이터베이스를 현재 봇 스키마로 마이그레이션하는 스크립트

변환 내역:
- duck_challenge.sulky_days -> growth_days
- duck_challenge.created_at 추가
- users.username 추가 (NULL, 나중에 Discord에서 업데이트)
- users.created_at, updated_at 추가
"""

import sqlite3
from datetime import datetime
import json
import os

# 경로 설정
BACKUP_DB = "/Users/mac/Documents/자료/요진편/Challenger/백업/challenge.db"
CURRENT_DB = "data/bot.db"
BACKUP_CURRENT_DB = f"data/bot_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"

def backup_current_db():
    """현재 DB 백업"""
    if os.path.exists(CURRENT_DB):
        import shutil
        shutil.copy2(CURRENT_DB, BACKUP_CURRENT_DB)
        print(f"✅ 현재 DB를 백업했습니다: {BACKUP_CURRENT_DB}")
    else:
        print("⚠️  현재 DB가 존재하지 않습니다.")

def analyze_data():
    """데이터 분석 및 통계 출력"""
    print("\n" + "="*60)
    print("📊 데이터 분석")
    print("="*60)

    # 백업 DB 분석
    with sqlite3.connect(BACKUP_DB) as backup_conn:
        backup_conn.row_factory = sqlite3.Row
        c = backup_conn.cursor()

        # 도전 통계
        c.execute("SELECT COUNT(*) as cnt FROM duck_challenge")
        backup_challenges = c.fetchone()['cnt']

        c.execute("SELECT state, COUNT(*) as cnt FROM duck_challenge GROUP BY state")
        state_stats = c.fetchall()

        # 유저 통계
        c.execute("SELECT COUNT(*) as cnt FROM users")
        backup_users = c.fetchone()['cnt']

        c.execute("SELECT SUM(ducks_raised) as total FROM users")
        total_ducks = c.fetchone()['total'] or 0

        c.execute("SELECT SUM(gold) as total FROM users")
        total_gold = c.fetchone()['total'] or 0

    print(f"\n📦 백업 DB:")
    print(f"  - 도전: {backup_challenges}개")
    for stat in state_stats:
        print(f"    • {stat['state']}: {stat['cnt']}개")
    print(f"  - 유저: {backup_users}명")
    print(f"  - 총 졸업 오리: {total_ducks}마리")
    print(f"  - 총 골드: {total_gold}개")

    # 현재 DB 분석
    if os.path.exists(CURRENT_DB):
        with sqlite3.connect(CURRENT_DB) as current_conn:
            current_conn.row_factory = sqlite3.Row
            c = current_conn.cursor()

            c.execute("SELECT COUNT(*) as cnt FROM duck_challenge")
            current_challenges = c.fetchone()['cnt']

            c.execute("SELECT COUNT(*) as cnt FROM users")
            current_users = c.fetchone()['cnt']

        print(f"\n💾 현재 DB:")
        print(f"  - 도전: {current_challenges}개")
        print(f"  - 유저: {current_users}명")

    print("\n" + "="*60)
    return backup_challenges, backup_users

def migrate_data(skip_duplicates=True):
    """데이터 마이그레이션 실행"""
    print("\n🔄 데이터 마이그레이션 시작...")

    # 현재 시간 (created_at, updated_at용)
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # 백업 DB 연결
    backup_conn = sqlite3.connect(BACKUP_DB)
    backup_conn.row_factory = sqlite3.Row
    backup_cursor = backup_conn.cursor()

    # 현재 DB 연결
    current_conn = sqlite3.connect(CURRENT_DB)
    current_cursor = current_conn.cursor()

    try:
        # 1. users 테이블 마이그레이션
        print("\n👥 유저 데이터 마이그레이션 중...")
        backup_cursor.execute("SELECT * FROM users")
        users = backup_cursor.fetchall()

        migrated_users = 0
        skipped_users = 0

        for user in users:
            try:
                current_cursor.execute('''
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
                migrated_users += 1
            except sqlite3.IntegrityError:
                if skip_duplicates:
                    skipped_users += 1
                else:
                    raise

        print(f"  ✅ {migrated_users}명 마이그레이션 완료")
        if skipped_users > 0:
            print(f"  ⚠️  {skipped_users}명 중복으로 건너뜀")

        # 2. duck_challenge 테이블 마이그레이션
        print("\n🦆 도전 데이터 마이그레이션 중...")
        backup_cursor.execute("SELECT * FROM duck_challenge")
        challenges = backup_cursor.fetchall()

        migrated_challenges = 0
        skipped_challenges = 0

        for challenge in challenges:
            try:
                # sulky_days -> growth_days로 변환
                growth_days = challenge['sulky_days'] if 'sulky_days' in challenge.keys() else 0
                state = 'DUCKLING' if challenge['state'] == 'DUCK' else challenge['state']

                current_cursor.execute('''
                    INSERT INTO duck_challenge
                    (thread_id, user_id, goal_text, state, streak, growth_days, total_days, last_auth_date, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    challenge['thread_id'],
                    challenge['user_id'],
                    challenge['goal_text'],
                    state,
                    challenge['streak'],
                    growth_days,
                    challenge['total_days'],
                    challenge['last_auth_date'] if challenge['last_auth_date'] else None,
                    now
                ))
                migrated_challenges += 1
            except sqlite3.IntegrityError:
                if skip_duplicates:
                    skipped_challenges += 1
                else:
                    raise

        print(f"  ✅ {migrated_challenges}개 마이그레이션 완료")
        if skipped_challenges > 0:
            print(f"  ⚠️  {skipped_challenges}개 중복으로 건너뜀")

        # 커밋
        current_conn.commit()
        print("\n✅ 마이그레이션이 성공적으로 완료되었습니다!")

        # 마이그레이션 후 통계
        print("\n" + "="*60)
        print("📈 마이그레이션 후 통계")
        print("="*60)

        current_cursor.execute("SELECT COUNT(*) as cnt FROM users")
        total_users = current_cursor.fetchone()[0]

        current_cursor.execute("SELECT COUNT(*) as cnt FROM duck_challenge")
        total_challenges = current_cursor.fetchone()[0]

        current_cursor.execute("SELECT state, COUNT(*) as cnt FROM duck_challenge GROUP BY state")
        state_stats = current_cursor.fetchall()

        print(f"\n💾 현재 DB:")
        print(f"  - 유저: {total_users}명")
        print(f"  - 도전: {total_challenges}개")
        for state, cnt in state_stats:
            print(f"    • {state}: {cnt}개")

    except Exception as e:
        current_conn.rollback()
        print(f"\n❌ 마이그레이션 실패: {e}")
        raise
    finally:
        backup_conn.close()
        current_conn.close()

def main():
    print("="*60)
    print("🦆 챌린저 봇 데이터 마이그레이션 도구")
    print("="*60)

    # 1. 백업 DB 존재 확인
    if not os.path.exists(BACKUP_DB):
        print(f"❌ 백업 DB를 찾을 수 없습니다: {BACKUP_DB}")
        return

    # 2. 현재 DB 백업
    backup_current_db()

    # 3. 데이터 분석
    backup_challenges, backup_users = analyze_data()

    # 4. 사용자 확인
    print("\n⚠️  주의사항:")
    print("  - 중복된 데이터는 자동으로 건너뜁니다")
    print("  - sulky_days는 growth_days로 변환됩니다")
    print("  - username은 NULL로 설정됩니다 (나중에 Discord에서 업데이트)")
    print(f"  - 현재 DB는 {BACKUP_CURRENT_DB}에 백업되었습니다")

    response = input("\n마이그레이션을 진행하시겠습니까? (y/n): ").strip().lower()

    if response == 'y':
        # 5. 마이그레이션 실행
        migrate_data(skip_duplicates=True)
    else:
        print("\n❌ 마이그레이션이 취소되었습니다.")

if __name__ == "__main__":
    main()
