#!/bin/bash

# 배포 업데이트 스크립트
# Git에서 최신 코드를 가져와 서비스를 재시작합니다.

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}🔄 Challenger Bot 업데이트 시작...${NC}"
echo ""

# 1. 현재 디렉토리 확인
if [ ! -f "src/main.py" ]; then
    echo -e "${RED}❌ 프로젝트 루트 디렉토리에서 실행해주세요.${NC}"
    exit 1
fi

# 2. 서비스 중지
echo -e "${YELLOW}1️⃣ 서비스 중지 중...${NC}"
sudo systemctl stop challenger-bot
sudo systemctl stop challenger-flask
echo -e "${GREEN}✅ 서비스 중지 완료${NC}"
echo ""

# 3. 데이터베이스 백업
echo -e "${YELLOW}2️⃣ 데이터베이스 백업 중...${NC}"
if [ -f "data/bot.db" ]; then
    BACKUP_FILE="data/backups/bot_$(date +%Y%m%d_%H%M%S).db"
    mkdir -p data/backups
    cp data/bot.db "$BACKUP_FILE"
    echo -e "${GREEN}✅ 백업 완료: $BACKUP_FILE${NC}"
else
    echo -e "${YELLOW}⚠️ 데이터베이스 파일이 없습니다. 스킵...${NC}"
fi
echo ""

# 4. Git 업데이트
echo -e "${YELLOW}3️⃣ Git에서 최신 코드 가져오는 중...${NC}"
git stash  # 로컬 변경사항 임시 저장
git pull origin main
echo -e "${GREEN}✅ 코드 업데이트 완료${NC}"
echo ""

# 5. 의존성 업데이트
echo -e "${YELLOW}4️⃣ 의존성 업데이트 중...${NC}"
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
echo -e "${GREEN}✅ 의존성 업데이트 완료${NC}"
echo ""

# 6. Systemd 서비스 재설치 (변경된 경우)
echo -e "${YELLOW}5️⃣ Systemd 서비스 확인 중...${NC}"
sudo cp systemd/challenger-bot.service /etc/systemd/system/
sudo cp systemd/challenger-flask.service /etc/systemd/system/
sudo systemctl daemon-reload
echo -e "${GREEN}✅ Systemd 서비스 업데이트 완료${NC}"
echo ""

# 7. 서비스 재시작
echo -e "${YELLOW}6️⃣ 서비스 재시작 중...${NC}"
sudo systemctl start challenger-bot
sudo systemctl start challenger-flask
sleep 3
echo -e "${GREEN}✅ 서비스 재시작 완료${NC}"
echo ""

# 8. 상태 확인
echo -e "${YELLOW}7️⃣ 서비스 상태 확인 중...${NC}"
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

echo -e "${GREEN}✅ 업데이트가 완료되었습니다!${NC}"
echo ""
echo "로그 확인:"
echo "  sudo journalctl -u challenger-bot -f"
echo "  sudo journalctl -u challenger-flask -f"
echo ""
