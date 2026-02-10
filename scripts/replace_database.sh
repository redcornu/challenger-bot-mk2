#!/bin/bash

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

NEW_DB="data/bot_new.db"
CURRENT_DB="data/bot.db"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo -e "${GREEN}=== DB 교체 시작 ===${NC}"
echo ""

# 1. 새 DB 존재 확인
if [ ! -f "$NEW_DB" ]; then
    echo -e "${RED}❌ 새 DB를 찾을 수 없습니다: $NEW_DB${NC}"
    echo "먼저 python3 scripts/convert_backup_to_new_schema.py를 실행하세요."
    exit 1
fi
echo -e "${GREEN}✅ 새 DB 확인: $NEW_DB${NC}"

# 2. 서비스 중지 (로컬 환경인 경우 건너뜀)
echo ""
echo -e "${YELLOW}서비스 중지 중...${NC}"
if command -v systemctl &> /dev/null; then
    sudo systemctl stop challenger-bot 2>/dev/null || true
    sudo systemctl stop challenger-flask 2>/dev/null || true
    echo -e "${GREEN}✅ 서비스 중지 완료${NC}"
else
    echo -e "${YELLOW}⚠️  systemctl 없음 (로컬 환경)${NC}"
fi

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
echo -e "${GREEN}✅ 권한 설정 완료${NC}"

# 6. 서비스 재시작
echo ""
echo -e "${YELLOW}서비스 재시작 중...${NC}"
if command -v systemctl &> /dev/null; then
    sudo systemctl start challenger-bot
    sudo systemctl start challenger-flask
    sleep 3
    echo -e "${GREEN}✅ 서비스 재시작 완료${NC}"
else
    echo -e "${YELLOW}⚠️  수동으로 봇을 재시작하세요: python src/main.py${NC}"
fi

# 7. 상태 확인
echo ""
echo -e "${YELLOW}서비스 상태 확인 중...${NC}"
if command -v systemctl &> /dev/null; then
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
fi

echo ""
echo -e "${GREEN}=== DB 교체 완료! ===${NC}"
echo ""
echo -e "${YELLOW}다음 단계:${NC}"
echo "  1. Discord에서 !상태 명령어 테스트"
echo "  2. 대시보드 접속: http://YOUR_IP:5001"
echo "  3. !인증 명령어 테스트"
echo ""
echo -e "${YELLOW}롤백 방법 (문제 발생 시):${NC}"
echo "  cp data/bot_replaced_${TIMESTAMP}.db data/bot.db"
echo "  sudo systemctl restart challenger-bot challenger-flask"
