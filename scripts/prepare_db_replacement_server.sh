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
SELECT 'DUCKLING 상태', COUNT(*) FROM duck_challenge WHERE state = 'DUCKLING';
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
