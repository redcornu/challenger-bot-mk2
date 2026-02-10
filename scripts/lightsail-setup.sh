#!/bin/bash

# AWS Lightsail 서버 초기 설정 스크립트
# 이 스크립트는 Ubuntu 22.04에서 테스트되었습니다.

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Challenger Bot 자동 배포 시작...${NC}"
echo ""

# 1. 시스템 업데이트
echo -e "${YELLOW}1️⃣ 시스템 업데이트 중...${NC}"
sudo apt update && sudo apt upgrade -y
echo -e "${GREEN}✅ 시스템 업데이트 완료${NC}"
echo ""

# 2. 필수 패키지 설치
echo -e "${YELLOW}2️⃣ 필수 패키지 설치 중...${NC}"
sudo apt install -y python3.9 python3-pip python3-venv git curl ufw
echo -e "${GREEN}✅ 필수 패키지 설치 완료${NC}"
echo ""

# 3. 방화벽 설정
echo -e "${YELLOW}3️⃣ 방화벽 설정 중...${NC}"
sudo ufw allow OpenSSH
sudo ufw allow 5001/tcp
sudo ufw --force enable
echo -e "${GREEN}✅ 방화벽 설정 완료 (SSH, 5001 포트 허용)${NC}"
echo ""

# 4. 프로젝트 클론 (이미 클론된 경우 스킵)
if [ ! -d "challenger-bot-mk2" ]; then
    echo -e "${YELLOW}4️⃣ 프로젝트 클론 중...${NC}"
    echo -e "${RED}⚠️ Git 저장소 URL을 입력해주세요:${NC}"
    read -p "URL: " REPO_URL
    git clone "$REPO_URL" challenger-bot-mk2
    echo -e "${GREEN}✅ 프로젝트 클론 완료${NC}"
else
    echo -e "${YELLOW}4️⃣ 프로젝트가 이미 존재합니다. 스킵...${NC}"
fi
echo ""

cd challenger-bot-mk2

# 5. 가상환경 생성
echo -e "${YELLOW}5️⃣ 가상환경 생성 및 의존성 설치 중...${NC}"
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
echo -e "${GREEN}✅ 가상환경 및 의존성 설치 완료${NC}"
echo ""

# 6. .env 파일 확인
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}6️⃣ .env 파일 생성 중...${NC}"
    cp .env.example .env
    echo -e "${RED}⚠️ 중요: .env 파일을 수정해야 합니다!${NC}"
    echo ""
    echo "다음 환경변수를 설정하세요:"
    echo "  - DISCORD_TOKEN (Discord 봇 토큰)"
    echo "  - ADMIN_PASSWORD (웹 대시보드 비밀번호, 8자 이상)"
    echo "  - FLASK_SECRET_KEY (32자 이상 랜덤 문자열)"
    echo ""
    echo -e "${YELLOW}.env 파일을 지금 편집하시겠습니까? [y/N]${NC}"
    read -p "> " EDIT_ENV
    if [[ "$EDIT_ENV" =~ ^[Yy]$ ]]; then
        nano .env
    else
        echo -e "${YELLOW}나중에 수동으로 편집하세요: nano .env${NC}"
    fi
else
    echo -e "${YELLOW}6️⃣ .env 파일이 이미 존재합니다. 스킵...${NC}"
fi
echo ""

# 7. 디렉토리 생성
echo -e "${YELLOW}7️⃣ 필수 디렉토리 생성 중...${NC}"
mkdir -p data logs
echo -e "${GREEN}✅ data/, logs/ 디렉토리 생성 완료${NC}"
echo ""

# 8. 환경변수 검증
echo -e "${YELLOW}8️⃣ 환경변수 검증 중...${NC}"
chmod +x validate_env.sh
if ./validate_env.sh; then
    echo -e "${GREEN}✅ 환경변수 검증 통과${NC}"
else
    echo -e "${RED}❌ 환경변수 검증 실패. .env 파일을 확인하세요.${NC}"
    echo "   nano .env"
    exit 1
fi
echo ""

# 9. Systemd 서비스 설치
echo -e "${YELLOW}9️⃣ Systemd 서비스 설치 중...${NC}"
sudo cp systemd/challenger-bot.service /etc/systemd/system/
sudo cp systemd/challenger-flask.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable challenger-bot
sudo systemctl enable challenger-flask
echo -e "${GREEN}✅ Systemd 서비스 설치 완료${NC}"
echo ""

# 10. 서비스 시작
echo -e "${YELLOW}🔟 서비스 시작 중...${NC}"
sudo systemctl start challenger-bot
sudo systemctl start challenger-flask
sleep 3
echo -e "${GREEN}✅ 서비스 시작 완료${NC}"
echo ""

# 11. 상태 확인
echo -e "${YELLOW}1️⃣1️⃣ 서비스 상태 확인 중...${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "[Discord 봇 상태]"
sudo systemctl status challenger-bot --no-pager | head -n 5
echo ""
echo "[Flask 서버 상태]"
sudo systemctl status challenger-flask --no-pager | head -n 5
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 12. 완료 메시지
echo -e "${GREEN}╔═══════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                                                   ║${NC}"
echo -e "${GREEN}║   ✅ 배포가 성공적으로 완료되었습니다! 🎉        ║${NC}"
echo -e "${GREEN}║                                                   ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════╝${NC}"
echo ""
echo "다음 단계:"
echo ""
echo "1️⃣ 웹 대시보드 접속:"
echo "   👉 http://$(curl -s ifconfig.me):5001"
echo ""
echo "2️⃣ Discord 봇 테스트:"
echo "   👉 Discord 서버에서 '!목표설정 테스트' 명령어 실행"
echo ""
echo "3️⃣ 로그 확인:"
echo "   Discord 봇: sudo journalctl -u challenger-bot -f"
echo "   Flask 서버: sudo journalctl -u challenger-flask -f"
echo ""
echo "4️⃣ 서비스 관리:"
echo "   재시작: sudo systemctl restart challenger-bot"
echo "   중지: sudo systemctl stop challenger-bot"
echo "   상태: sudo systemctl status challenger-bot"
echo ""
echo "문제가 발생하면 DEPLOYMENT_GUIDE.md의 '문제 해결' 섹션을 참고하세요."
echo ""
