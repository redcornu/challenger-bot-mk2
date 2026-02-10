#!/bin/bash

# 서버 시작 스크립트
# Discord 봇과 Flask 대시보드를 백그라운드로 실행

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# .env에서 Flask 포트 읽기
FLASK_PORT=$(grep -E '^FLASK_PORT=' .env 2>/dev/null | cut -d '=' -f2)
FLASK_PORT=${FLASK_PORT:-5001}  # 기본값 5001

echo "🚀 서버 시작 중..."
echo ""

# 환경 변수 검증
echo "1️⃣  환경 변수 검증..."
if ! bash validate_env.sh; then
    echo -e "${RED}❌ 환경 변수 검증 실패. 서버를 시작할 수 없습니다.${NC}"
    exit 1
fi
echo ""

# 가상환경 확인 및 활성화
echo "2️⃣  가상환경 확인..."
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}⚠️  가상환경이 존재하지 않습니다. 생성 중...${NC}"
    python3 -m venv venv
fi

source venv/bin/activate
echo -e "${GREEN}✅ 가상환경 활성화됨${NC}"
echo ""

# 의존성 설치 확인
echo "3️⃣  의존성 확인..."
if ! python -c "import flask" 2>/dev/null; then
    echo -e "${YELLOW}⚠️  Flask가 설치되어 있지 않습니다. 설치 중...${NC}"
    pip install -r requirements.txt
else
    echo -e "${GREEN}✅ 모든 의존성이 설치되어 있습니다.${NC}"
fi
echo ""

# 필수 디렉토리 생성
echo "4️⃣  디렉토리 생성..."
mkdir -p data logs
echo -e "${GREEN}✅ data/, logs/ 디렉토리 확인됨${NC}"
echo ""

# 이미 실행 중인 서버 확인
echo "5️⃣  실행 중인 서버 확인..."
if [ -f ".discord_bot.pid" ]; then
    PID=$(cat .discord_bot.pid)
    if ps -p $PID > /dev/null 2>&1; then
        echo -e "${YELLOW}⚠️  Discord 봇이 이미 실행 중입니다 (PID: $PID)${NC}"
        echo "   중지하려면: ./stop_servers.sh"
        exit 1
    else
        rm .discord_bot.pid
    fi
fi

if [ -f ".flask.pid" ]; then
    PID=$(cat .flask.pid)
    if ps -p $PID > /dev/null 2>&1; then
        echo -e "${YELLOW}⚠️  Flask 서버가 이미 실행 중입니다 (PID: $PID)${NC}"
        echo "   중지하려면: ./stop_servers.sh"
        exit 1
    else
        rm .flask.pid
    fi
fi
echo -e "${GREEN}✅ 실행 중인 서버 없음${NC}"
echo ""

# Discord 봇 시작
echo "6️⃣  Discord 봇 시작..."
nohup python src/main.py > logs/discord_bot.log 2>&1 &
DISCORD_PID=$!
echo $DISCORD_PID > .discord_bot.pid
echo -e "${GREEN}✅ Discord 봇 시작됨 (PID: $DISCORD_PID)${NC}"
echo ""

# Flask 서버 시작
echo "7️⃣  Flask 서버 시작..."
nohup python src/admin/app.py > logs/flask.log 2>&1 &
FLASK_PID=$!
echo $FLASK_PID > .flask.pid
echo -e "${GREEN}✅ Flask 서버 시작됨 (PID: $FLASK_PID)${NC}"
echo ""

# 헬스 체크
echo "8️⃣  헬스 체크..."
sleep 3

# Discord 봇 확인
if ps -p $DISCORD_PID > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Discord 봇 실행 중${NC}"
else
    echo -e "${RED}❌ Discord 봇이 시작 직후 종료되었습니다.${NC}"
    echo "   로그 확인: tail -f logs/discord_bot.log"
fi

# Flask 서버 확인
if ps -p $FLASK_PID > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Flask 서버 실행 중${NC}"
    
    # HTTP 응답 확인 (최대 5회 재시도)
    for i in {1..5}; do
        if curl -s http://localhost:${FLASK_PORT} > /dev/null 2>&1; then
            echo -e "${GREEN}✅ Flask 서버 HTTP 응답 확인됨${NC}"
            break
        else
            if [ $i -eq 5 ]; then
                echo -e "${YELLOW}⚠️  Flask 서버가 아직 준비되지 않았습니다. 잠시 후 다시 시도하세요.${NC}"
            else
                sleep 1
            fi
        fi
    done
else
    echo -e "${RED}❌ Flask 서버가 시작 직후 종료되었습니다.${NC}"
    echo "   로그 확인: tail -f logs/flask.log"
fi

echo ""
echo "════════════════════════════════════════"
echo -e "${GREEN}✅ 서버가 성공적으로 시작되었습니다!${NC}"
echo ""
echo "📊 상태 확인: ./check_status.sh"
echo "🌐 대시보드: http://localhost:${FLASK_PORT}"
echo "🛑 서버 중지: ./stop_servers.sh"
echo ""
echo "📝 로그 확인:"
echo "   Discord 봇: tail -f logs/discord_bot.log"
echo "   Flask 서버: tail -f logs/flask.log"
echo "════════════════════════════════════════"
