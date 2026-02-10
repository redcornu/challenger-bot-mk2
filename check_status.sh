#!/bin/bash

# 상태 확인 스크립트
# Discord 봇과 Flask 서버의 상태를 확인

set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# .env에서 Flask 포트 읽기
FLASK_PORT=$(grep -E '^FLASK_PORT=' .env 2>/dev/null | cut -d '=' -f2)
FLASK_PORT=${FLASK_PORT:-5001}  # 기본값 5001

echo "📊 서버 상태 확인"
echo "════════════════════════════════════════"
echo ""

# Discord 봇 상태
echo -e "${BLUE}🤖 Discord 봇${NC}"
if [ -f ".discord_bot.pid" ]; then
    PID=$(cat .discord_bot.pid)
    if ps -p $PID > /dev/null 2>&1; then
        echo -e "   상태: ${GREEN}실행 중${NC}"
        echo "   PID: $PID"
        
        # CPU 및 메모리 사용률 (macOS 호환)
        if command -v ps &> /dev/null; then
            CPU=$(ps -p $PID -o %cpu | tail -1 | xargs)
            MEM=$(ps -p $PID -o %mem | tail -1 | xargs)
            RSS=$(ps -p $PID -o rss | tail -1 | xargs)
            MEM_MB=$((RSS / 1024))
            
            echo "   CPU: ${CPU}%"
            echo "   메모리: ${MEM}% (${MEM_MB} MB)"
        fi
        
        # 로그 파일 크기
        if [ -f "logs/discord_bot.log" ]; then
            LOG_SIZE=$(du -h logs/discord_bot.log | cut -f1)
            echo "   로그: logs/discord_bot.log ($LOG_SIZE)"
        fi
    else
        echo -e "   상태: ${RED}중지됨${NC} (PID 파일만 존재)"
        rm .discord_bot.pid
    fi
else
    echo -e "   상태: ${RED}중지됨${NC}"
fi

echo ""

# Flask 서버 상태
echo -e "${BLUE}🌐 Flask 서버${NC}"
if [ -f ".flask.pid" ]; then
    PID=$(cat .flask.pid)
    if ps -p $PID > /dev/null 2>&1; then
        echo -e "   상태: ${GREEN}실행 중${NC}"
        echo "   PID: $PID"
        
        # CPU 및 메모리 사용률
        if command -v ps &> /dev/null; then
            CPU=$(ps -p $PID -o %cpu | tail -1 | xargs)
            MEM=$(ps -p $PID -o %mem | tail -1 | xargs)
            RSS=$(ps -p $PID -o rss | tail -1 | xargs)
            MEM_MB=$((RSS / 1024))
            
            echo "   CPU: ${CPU}%"
            echo "   메모리: ${MEM}% (${MEM_MB} MB)"
        fi
        
        # HTTP 응답 확인
        if curl -s -o /dev/null -w "%{http_code}" http://localhost:${FLASK_PORT} | grep -q "200\|302"; then
            echo -e "   HTTP: ${GREEN}응답함${NC}"
            echo "   URL: http://localhost:${FLASK_PORT}"
        else
            echo -e "   HTTP: ${YELLOW}응답 없음${NC}"
        fi
        
        # 로그 파일 크기
        if [ -f "logs/flask.log" ]; then
            LOG_SIZE=$(du -h logs/flask.log | cut -f1)
            echo "   로그: logs/flask.log ($LOG_SIZE)"
        fi
    else
        echo -e "   상태: ${RED}중지됨${NC} (PID 파일만 존재)"
        rm .flask.pid
    fi
else
    echo -e "   상태: ${RED}중지됨${NC}"
fi

echo ""

# Flask 포트 사용 확인
echo -e "${BLUE}🔌 포트 ${FLASK_PORT} 상태${NC}"
if lsof -i :${FLASK_PORT} > /dev/null 2>&1; then
    PORT_INFO=$(lsof -i :${FLASK_PORT} | tail -1)
    echo -e "   상태: ${GREEN}사용 중${NC}"
    echo "   프로세스: $PORT_INFO"
else
    echo -e "   상태: ${RED}미사용${NC}"
fi

echo ""
echo "════════════════════════════════════════"
echo ""
echo "💡 명령어:"
echo "   서버 시작: ./start_servers.sh"
echo "   서버 중지: ./stop_servers.sh"
echo "   로그 보기: tail -f logs/discord_bot.log"
echo "             tail -f logs/flask.log"
