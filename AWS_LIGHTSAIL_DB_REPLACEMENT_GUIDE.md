# AWS Lightsail 데이터베이스 교체 가이드

> **백업 DB를 AWS Lightsail 서버의 현재 운영 DB로 교체하는 완전한 가이드**

이 가이드는 로컬에 있는 백업 DB를 AWS Lightsail 서버에 업로드하고, 현재 운영 중인 DB를 안전하게 교체하는 전체 프로세스를 단계별로 설명합니다.

---

## 📋 목차

1. [사전 준비](#1-사전-준비)
2. [스크립트 서버용으로 수정](#2-스크립트-서버용으로-수정)
3. [백업 DB 및 스크립트 서버로 업로드](#3-백업-db-및-스크립트-서버로-업로드)
4. [서버에서 DB 교체 실행](#4-서버에서-db-교체-실행)
5. [교체 후 검증](#5-교체-후-검증)
6. [롤백 방법](#6-롤백-방법)
7. [문제 해결](#7-문제-해결)

---

## ⚠️ 중요 경고

### 데이터 손실 주의

백업 DB로 교체하면:
- **2명의 신규 유저 삭제**
- **4개의 신규 챌린지 삭제**
- **모든 진행 상황이 백업 시점(2025-02-02)으로 롤백** (gold, streak, total_days 감소)

### 안전 조치

✅ 다음 안전 장치가 마련되어 있습니다:
1. 현재 DB를 2번 백업 (Step 1, Step 3에서)
2. 단계별 검증으로 문제 발생 시 즉시 중단
3. 롤백 방법 제공 (언제든 원복 가능)

---

## 1. 사전 준비

### 1.1 필요한 정보 확인

다음 정보를 준비하세요:

```bash
# AWS Lightsail 정보
서버 IP: 3.39.110.88
SSH 키: ~/Downloads/challenger-duck.pem
유저: ubuntu
프로젝트 경로: /home/ubuntu/challenger-bot-mk2
```

### 1.2 로컬 파일 확인

**백업 DB 위치:**
```bash
/Users/mac/Documents/자료/요진편/Challenger/백업/challenge.db
```

**백업 DB 존재 확인:**
```bash
ls -lh "/Users/mac/Documents/자료/요진편/Challenger/백업/challenge.db"
```

**출력 예시:**
```
-rw-r--r--@ 1 mac  staff    12K  2  2 18:39 /Users/mac/Documents/.../challenge.db
```

### 1.3 SSH 연결 테스트

**방법 1: 로컬 터미널 (macOS/Linux)**
```bash
ssh -i ~/Downloads/challenger-duck.pem ubuntu@3.39.110.88
```

**방법 2: Lightsail 브라우저 SSH (더 간단)**
1. [AWS Lightsail 콘솔](https://lightsail.aws.amazon.com/) 접속
2. 인스턴스(`challenger-bot`) 선택
3. 우측 상단 **터미널 아이콘** 클릭

---

## 2. 스크립트 서버용으로 수정

로컬에서 스크립트를 서버 환경에 맞게 수정합니다.

### 2.1 서버용 스크립트 생성

**로컬 터미널에서 실행:**

```bash
cd /users/mac/Documents/자료/요진편/challenger-bot-mk2
```

#### 2.1.1 `prepare_db_replacement_server.sh` 생성

```bash
cat > scripts/prepare_db_replacement_server.sh << 'EOF'
#!/bin/bash

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# 서버 경로
BACKUP_DB="/tmp/challenge.db"
CURRENT_DB="data/bot.db"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo -e "${GREEN}=== DB 교체 준비 (서버) ===${NC}"
echo ""

# 1. 백업 DB 존재 확인
if [ ! -f "$BACKUP_DB" ]; then
    echo -e "${RED}❌ 백업 DB를 찾을 수 없습니다: $BACKUP_DB${NC}"
    echo ""
    echo "먼저 로컬에서 백업 DB를 업로드하세요:"
    echo "  scp -i ~/Downloads/challenger-duck.pem \\"
    echo "      /Users/mac/Documents/자료/요진편/Challenger/백업/challenge.db \\"
    echo "      ubuntu@3.39.110.88:/tmp/challenge.db"
    exit 1
fi
echo -e "${GREEN}✅ 백업 DB 확인: $BACKUP_DB${NC}"

# 2. 현재 DB 백업
if [ -f "$CURRENT_DB" ]; then
    BACKUP_FILE="data/bot_before_replacement_${TIMESTAMP}.db"
    cp "$CURRENT_DB" "$BACKUP_FILE"
    echo -e "${GREEN}✅ 현재 DB 백업: $BACKUP_FILE${NC}"
else
    echo -e "${YELLOW}⚠️  현재 DB 없음 (새로 생성됨)${NC}"
fi

# 3. 백업 DB 통계
echo ""
echo -e "${YELLOW}백업 DB 통계:${NC}"
sqlite3 "$BACKUP_DB" << SQL
.mode column
.headers on
SELECT '유저 수' as 항목, COUNT(*) as 값 FROM users
UNION ALL
SELECT '챌린지 수', COUNT(*) FROM duck_challenge
UNION ALL
SELECT '총 골드', SUM(gold) FROM users
UNION ALL
SELECT 'EGG 상태', COUNT(*) FROM duck_challenge WHERE state = 'EGG'
UNION ALL
SELECT 'DUCK 상태', COUNT(*) FROM duck_challenge WHERE state = 'DUCK';
SQL

# 4. Orphaned challenges 확인
echo ""
echo -e "${YELLOW}Orphaned Challenges 확인:${NC}"
ORPHANED=$(sqlite3 "$BACKUP_DB" "SELECT COUNT(*) FROM duck_challenge dc LEFT JOIN users u ON dc.user_id = u.user_id WHERE u.user_id IS NULL;")
if [ "$ORPHANED" -gt 0 ]; then
    echo -e "${RED}⚠️  $ORPHANED 개의 orphaned challenges 발견${NC}"
    sqlite3 "$BACKUP_DB" << SQL
.mode column
.headers on
SELECT dc.thread_id, dc.user_id, dc.goal_text
FROM duck_challenge dc
LEFT JOIN users u ON dc.user_id = u.user_id
WHERE u.user_id IS NULL;
SQL
else
    echo -e "${GREEN}✅ Orphaned challenges 없음${NC}"
fi

echo ""
echo -e "${GREEN}=== 준비 완료 ===${NC}"
echo ""
echo -e "${YELLOW}다음 단계:${NC}"
echo "  1. python3 scripts/convert_backup_to_new_schema_server.py"
echo "  2. ./scripts/replace_database_server.sh"
EOF
```

#### 2.1.2 `convert_backup_to_new_schema_server.py` 생성

```bash
cat > scripts/convert_backup_to_new_schema_server.py << 'EOF'
#!/usr/bin/env python3
"""
백업 DB를 새 스키마로 변환하는 스크립트 (서버용)

백업 DB (구 스키마) → 임시 DB (신 스키마)
"""

import sqlite3
import json
from datetime import datetime
import sys

BACKUP_DB = "/tmp/challenge.db"
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
    print("백업 DB → 새 스키마 변환 (서버)")
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
            print("\n다음 단계: ./scripts/replace_database_server.sh 실행")
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
EOF
```

#### 2.1.3 `replace_database_server.sh` 생성

```bash
cat > scripts/replace_database_server.sh << 'EOF'
#!/bin/bash

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

NEW_DB="data/bot_new.db"
CURRENT_DB="data/bot.db"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo -e "${GREEN}=== DB 교체 시작 (서버) ===${NC}"
echo ""

# 1. 새 DB 존재 확인
if [ ! -f "$NEW_DB" ]; then
    echo -e "${RED}❌ 새 DB를 찾을 수 없습니다: $NEW_DB${NC}"
    echo "먼저 python3 scripts/convert_backup_to_new_schema_server.py를 실행하세요."
    exit 1
fi
echo -e "${GREEN}✅ 새 DB 확인: $NEW_DB${NC}"

# 2. 서비스 중지
echo ""
echo -e "${YELLOW}서비스 중지 중...${NC}"
sudo systemctl stop challenger-bot
sudo systemctl stop challenger-flask
echo -e "${GREEN}✅ 서비스 중지 완료${NC}"

# 3. 현재 DB 최종 백업
if [ -f "$CURRENT_DB" ]; then
    BACKUP_FILE="data/bot_replaced_${TIMESTAMP}.db"
    mv "$CURRENT_DB" "$BACKUP_FILE"
    echo -e "${GREEN}✅ 현재 DB 백업: $BACKUP_FILE${NC}"
fi

# 4. 새 DB를 현재 DB로 복사
cp "$NEW_DB" "$CURRENT_DB"
echo -e "${GREEN}✅ DB 교체 완료${NC}"

# 5. 권한 설정
chmod 644 "$CURRENT_DB"
chown ubuntu:ubuntu "$CURRENT_DB"
echo -e "${GREEN}✅ 권한 설정 완료${NC}"

# 6. 서비스 재시작
echo ""
echo -e "${YELLOW}서비스 재시작 중...${NC}"
sudo systemctl start challenger-bot
sudo systemctl start challenger-flask
sleep 3
echo -e "${GREEN}✅ 서비스 재시작 완료${NC}"

# 7. 상태 확인
echo ""
echo -e "${YELLOW}서비스 상태 확인 중...${NC}"
if sudo systemctl is-active --quiet challenger-bot; then
    echo -e "${GREEN}✅ Discord 봇 실행 중${NC}"
else
    echo -e "${RED}❌ Discord 봇이 실행되지 않았습니다.${NC}"
    echo "   로그 확인: sudo journalctl -u challenger-bot -n 50"
fi

if sudo systemctl is-active --quiet challenger-flask; then
    echo -e "${GREEN}✅ Flask 서버 실행 중${NC}"
else
    echo -e "${RED}❌ Flask 서버가 실행되지 않았습니다.${NC}"
    echo "   로그 확인: sudo journalctl -u challenger-flask -n 50"
fi

echo ""
echo -e "${GREEN}=== DB 교체 완료! ===${NC}"
echo ""
echo -e "${YELLOW}다음 단계:${NC}"
echo "  1. Discord에서 !상태 명령어 테스트"
echo "  2. 대시보드 접속: http://3.39.110.88:5001"
echo "  3. !인증 명령어 테스트"
echo ""
echo -e "${YELLOW}롤백 방법 (문제 발생 시):${NC}"
echo "  cp data/bot_replaced_${TIMESTAMP}.db data/bot.db"
echo "  sudo systemctl restart challenger-bot challenger-flask"
EOF
```

### 2.2 스크립트 실행 권한 부여

```bash
chmod +x scripts/prepare_db_replacement_server.sh
chmod +x scripts/convert_backup_to_new_schema_server.py
chmod +x scripts/replace_database_server.sh
```

---

## 3. 백업 DB 및 스크립트 서버로 업로드

### 3.1 백업 DB 업로드

**로컬 터미널에서 실행:**

```bash
# 백업 DB를 서버의 /tmp 디렉토리로 업로드
scp -i ~/Downloads/challenger-duck.pem \
    "/Users/mac/Documents/자료/요진편/Challenger/백업/challenge.db" \
    ubuntu@3.39.110.88:/tmp/challenge.db
```

**예상 출력:**
```
challenge.db                          100%   12KB  12.0KB/s   00:01
```

### 3.2 서버용 스크립트 업로드

**로컬 터미널에서 실행:**

```bash
cd /Users/mac/Documents/자료/요진편/challenger-bot-mk2

# 3개의 스크립트 업로드
scp -i ~/Downloads/challenger-duck.pem \
    scripts/prepare_db_replacement_server.sh \
    scripts/convert_backup_to_new_schema_server.py \
    scripts/replace_database_server.sh \
    ubuntu@3.39.110.88:/home/ubuntu/challenger-bot-mk2/scripts/
```

**예상 출력:**
```
prepare_db_replacement_server.sh      100%  2.1KB   2.1KB/s   00:01
convert_backup_to_new_schema_server.py 100%  8.5KB   8.5KB/s   00:01
replace_database_server.sh            100%  2.3KB   2.3KB/s   00:01
```

### 3.3 업로드 확인

**서버에서 확인:**

```bash
# 서버로 SSH 접속
ssh -i ~/Downloads/challenger-duck.pem ubuntu@3.39.110.88

# 파일 확인
ls -lh /tmp/challenge.db
ls -lh /home/ubuntu/challenger-bot-mk2/scripts/*_server*
```

---

## 4. 서버에서 DB 교체 실행

**⚠️ 주의: 이제부터는 서버에서 작업합니다!**

### 4.1 SSH 접속

```bash
ssh -i ~/Downloads/challenger-duck.pem ubuntu@3.39.110.88
```

또는 Lightsail 브라우저 SSH 사용

### 4.2 프로젝트 디렉토리로 이동

```bash
cd /home/ubuntu/challenger-bot-mk2
```

### 4.3 Step 1: 준비 및 검증

```bash
chmod +x scripts/prepare_db_replacement_server.sh
./scripts/prepare_db_replacement_server.sh
```

**예상 출력:**
```
=== DB 교체 준비 (서버) ===

✅ 백업 DB 확인: /tmp/challenge.db
✅ 현재 DB 백업: data/bot_before_replacement_20260210_143022.db

백업 DB 통계:
항목        값
---------  ---
유저 수      46
챌린지 수    52
총 골드    2340
EGG 상태    15
DUCK 상태   37

Orphaned Challenges 확인:
⚠️  2 개의 orphaned challenges 발견
thread_id   user_id     goal_text
----------  ----------  ----------
1234567890  999999999   테스트 목표
1234567891  999999998   테스트 목표 2

=== 준비 완료 ===

다음 단계:
  1. python3 scripts/convert_backup_to_new_schema_server.py
  2. ./scripts/replace_database_server.sh
```

### 4.4 Step 2: 스키마 변환 및 마이그레이션

```bash
python3 scripts/convert_backup_to_new_schema_server.py
```

**대화형 프롬프트:**
```
============================================================
백업 DB → 새 스키마 변환 (서버)
============================================================

백업 DB: /tmp/challenge.db
새 DB: data/bot_new.db

[1/5] 새 스키마 생성 중...
✅ 새 스키마 생성 완료

[2/5] 유저 마이그레이션 중...
✅ 46명 유저 마이그레이션 완료

[3/5] Orphaned challenges 처리 중...

⚠️  2개의 orphaned challenges 발견:
  - thread_id=1234567890, user_id=999999999, goal=테스트 목표
  - thread_id=1234567891, user_id=999999998, goal=테스트 목표 2

처리 방법을 선택하세요:
  1. 유저 생성 (Unknown User로)
  2. 챌린지 삭제 (권장)
  3. 건너뛰기 (마이그레이션하지 않음)

선택 (1/2/3): 2
```

**👉 권장: `2` (챌린지 삭제) 선택**

**예상 출력 (계속):**
```
  ✅ 2개 챌린지 건너뛰기

[4/5] 챌린지 마이그레이션 중...
✅ 50개 챌린지 마이그레이션 완료 (2개 건너뜀)

[5/5] 새 DB 검증 중...

=== 새 DB 검증 ===
유저 수: 46명
챌린지 수: 50개
총 골드: 2340G
✅ Orphaned challenges 없음
✅ 필수 필드 모두 채워짐

============================================================
✅ 변환 완료!
============================================================

새 DB 위치: data/bot_new.db
유저: 46명
챌린지: 50개

다음 단계: ./scripts/replace_database_server.sh 실행
```

### 4.5 Step 3: DB 교체 및 서비스 재시작

```bash
chmod +x scripts/replace_database_server.sh
./scripts/replace_database_server.sh
```

**예상 출력:**
```
=== DB 교체 시작 (서버) ===

✅ 새 DB 확인: data/bot_new.db

서비스 중지 중...
✅ 서비스 중지 완료
✅ 현재 DB 백업: data/bot_replaced_20260210_143525.db
✅ DB 교체 완료
✅ 권한 설정 완료

서비스 재시작 중...
✅ 서비스 재시작 완료

서비스 상태 확인 중...
✅ Discord 봇 실행 중
✅ Flask 서버 실행 중

=== DB 교체 완료! ===

다음 단계:
  1. Discord에서 !상태 명령어 테스트
  2. 대시보드 접속: http://3.39.110.88:5001
  3. !인증 명령어 테스트

롤백 방법 (문제 발생 시):
  cp data/bot_replaced_20260210_143525.db data/bot.db
  sudo systemctl restart challenger-bot challenger-flask
```

---

## 5. 교체 후 검증

### 5.1 DB 통계 확인

**서버에서 실행:**

```bash
sqlite3 data/bot.db << EOF
.mode column
.headers on
SELECT
    (SELECT COUNT(*) FROM users) as 유저수,
    (SELECT COUNT(*) FROM duck_challenge) as 챌린지수,
    (SELECT SUM(gold) FROM users) as 총골드;
EOF
```

**예상 출력:**
```
유저수  챌린지수  총골드
----  ------  ----
46    50      2340
```

### 5.2 무결성 검증

```bash
sqlite3 data/bot.db << EOF
-- Orphaned challenges 확인
SELECT COUNT(*) as orphaned_count
FROM duck_challenge dc
LEFT JOIN users u ON dc.user_id = u.user_id
WHERE u.user_id IS NULL;

-- NULL 값 확인
SELECT COUNT(*) as null_count
FROM duck_challenge
WHERE user_id IS NULL OR goal_text IS NULL OR state IS NULL;
EOF
```

**예상 출력:**
```
orphaned_count
--------------
0

null_count
----------
0
```

### 5.3 로그 확인

**실시간 로그 모니터링:**

```bash
# Discord 봇 로그
sudo journalctl -u challenger-bot -f
```

**Ctrl+C로 종료 후 Flask 로그:**

```bash
# Flask 서버 로그
sudo journalctl -u challenger-flask -f
```

**최근 에러 확인:**

```bash
sudo journalctl -u challenger-bot -n 100 | grep -E "ERROR|Critical"
```

### 5.4 서비스 상태 확인

```bash
sudo systemctl status challenger-bot
sudo systemctl status challenger-flask
```

**정상 출력:**
```
● challenger-bot.service - Challenger Discord Bot (오리와 66일의 약속)
   Loaded: loaded (/etc/systemd/system/challenger-bot.service; enabled)
   Active: active (running) since Mon 2026-02-10 14:35:25 UTC; 5min ago
```

### 5.5 Discord 테스트

Discord 서버에서 다음 명령어 실행:

```
!상태        # 유저 정보 확인
!도움말      # 명령어 목록 확인
!인증        # 사진 첨부하여 인증 테스트
```

### 5.6 웹 대시보드 테스트

브라우저에서 접속:

```
http://3.39.110.88:5001
```

1. `.env`의 `ADMIN_PASSWORD`로 로그인
2. 유저 목록 확인 (46명)
3. 챌린지 목록 확인 (50개)
4. 상태 차트 확인

---

## 6. 롤백 방법

### 6.1 문제 발생 시 즉시 롤백

**⚠️ 문제가 발생하면 이 명령어로 즉시 원복:**

```bash
cd /home/ubuntu/challenger-bot-mk2

# 1. 서비스 중지
sudo systemctl stop challenger-bot
sudo systemctl stop challenger-flask

# 2. DB 복원 (타임스탬프는 실제 값으로 교체)
cp data/bot_replaced_20260210_143525.db data/bot.db

# 3. 권한 설정
chmod 644 data/bot.db
chown ubuntu:ubuntu data/bot.db

# 4. 서비스 재시작
sudo systemctl start challenger-bot
sudo systemctl start challenger-flask

# 5. 상태 확인
sudo systemctl status challenger-bot
sudo systemctl status challenger-flask
```

### 6.2 롤백 후 검증

```bash
# DB 레코드 수 확인
sqlite3 data/bot.db "SELECT COUNT(*) as users FROM users; SELECT COUNT(*) as challenges FROM duck_challenge;"

# Discord 테스트
# Discord에서 !상태 명령어 실행
```

### 6.3 백업 파일 관리

**백업 파일 목록 확인:**

```bash
ls -lh data/bot_*.db
```

**출력 예시:**
```
-rw-r--r-- 1 ubuntu ubuntu 16K Feb 10 14:30 data/bot_before_replacement_20260210_143022.db
-rw-r--r-- 1 ubuntu ubuntu 16K Feb 10 14:35 data/bot_replaced_20260210_143525.db
```

**오래된 백업 삭제 (선택):**

```bash
# 30일 이상 된 백업 삭제
find data/ -name "bot_*.db" -mtime +30 -delete
```

---

## 7. 문제 해결

### 7.1 백업 DB 업로드 실패

**증상:**
```
Permission denied (publickey)
```

**해결 방법:**

```bash
# SSH 키 권한 확인
chmod 400 ~/Downloads/challenger-duck.pem

# 다시 시도
scp -i ~/Downloads/challenger-duck.pem \
    "/Users/mac/Documents/자료/요진편/Challenger/백업/challenge.db" \
    ubuntu@3.39.110.88:/tmp/challenge.db
```

### 7.2 서비스 시작 실패

**증상:**
```
❌ Discord 봇이 실행되지 않았습니다.
```

**해결 방법:**

```bash
# 상세 로그 확인
sudo journalctl -u challenger-bot -n 50 --no-pager

# 수동 실행으로 오류 확인
cd /home/ubuntu/challenger-bot-mk2
source venv/bin/activate
python src/main.py
```

**일반적인 원인:**
- ❌ `.env` 파일 문제 → `nano .env`로 확인
- ❌ 가상환경 문제 → `ls -la venv/bin/python`
- ❌ 권한 문제 → `chown -R ubuntu:ubuntu /home/ubuntu/challenger-bot-mk2`

### 7.3 Orphaned challenges 많음

**증상:**
```
⚠️  Orphaned challenges: 10개
```

**해결 방법:**

대화형 프롬프트에서 **옵션 2 (챌린지 삭제)** 선택 권장

또는 **옵션 1 (유저 생성)**을 선택하면 Unknown User가 생성됩니다.

### 7.4 DB 잠금 오류

**증상:**
```
Error: database is locked
```

**해결 방법:**

```bash
# 1. 서비스 중지
sudo systemctl stop challenger-bot
sudo systemctl stop challenger-flask

# 2. DB 잠금 파일 삭제
rm -f data/bot.db-shm data/bot.db-wal

# 3. 서비스 재시작
sudo systemctl start challenger-bot
sudo systemctl start challenger-flask
```

### 7.5 디스크 공간 부족

**증상:**
```
Error: No space left on device
```

**해결 방법:**

```bash
# 디스크 사용량 확인
df -h

# 오래된 백업 삭제
rm -f data/bot_before_replacement_*.db
rm -f data/bot_replaced_*.db

# 로그 정리
sudo journalctl --vacuum-time=7d
```

### 7.6 권한 문제

**증상:**
```
Permission denied: 'data/bot.db'
```

**해결 방법:**

```bash
# 모든 파일 권한 수정
cd /home/ubuntu/challenger-bot-mk2
sudo chown -R ubuntu:ubuntu .
chmod 644 data/bot.db
chmod 755 data logs
```

---

## 📊 교체 전후 비교

### Before (현재 DB)

```
유저: 48명
챌린지: 56개
총 골드: 2540G
마지막 업데이트: 2026-02-10
```

### After (백업 DB로 교체)

```
유저: 46명 (-2명 손실)
챌린지: 50개 (-6개 손실, orphaned 2개 제거)
총 골드: 2340G (-200G 롤백)
데이터 시점: 2025-02-02 (백업 생성 시점)
```

### 데이터 손실 항목

- **삭제될 유저**: 2명
- **삭제될 챌린지**: 4개 (신규) + 2개 (orphaned) = 6개
- **롤백될 진행 상황**:
  - Gold: -200G
  - Streak: 백업 이후 인증 기록 손실
  - Total days: 백업 이후 누적 기록 손실

---

## ✅ 완료 체크리스트

교체가 완료되면 다음 항목을 확인하세요:

- [ ] 백업 DB를 서버로 업로드 완료
- [ ] 스크립트 3개를 서버로 업로드 완료
- [ ] `prepare_db_replacement_server.sh` 실행 성공
- [ ] `convert_backup_to_new_schema_server.py` 실행 성공
- [ ] Orphaned challenges 처리 (2 선택 권장)
- [ ] `replace_database_server.sh` 실행 성공
- [ ] 서비스 상태 확인 (both active)
- [ ] DB 통계 검증 (46명, 50개)
- [ ] Orphaned challenges 0개 확인
- [ ] 로그 확인 (에러 없음)
- [ ] Discord 명령어 테스트 (`!상태`, `!도움말`)
- [ ] 웹 대시보드 접속 및 로그인
- [ ] 백업 파일 보관 확인
- [ ] 롤백 방법 숙지

---

## 📞 지원

문제가 발생하면:

1. **로그 확인:**
   ```bash
   sudo journalctl -u challenger-bot -n 100
   ```

2. **서비스 상태:**
   ```bash
   sudo systemctl status challenger-bot
   ```

3. **DB 검증:**
   ```bash
   sqlite3 data/bot.db "PRAGMA integrity_check;"
   ```

4. **롤백:**
   - [6. 롤백 방법](#6-롤백-방법) 참고

---

**작성일:** 2026-02-10
**대상 서버:** AWS Lightsail (3.39.110.88)
**프로젝트 경로:** /home/ubuntu/challenger-bot-mk2
**백업 DB 시점:** 2025-02-02
