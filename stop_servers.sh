#!/bin/bash

# 서버 중지 스크립트
# Discord 봇과 Flask 서버를 안전하게 종료

set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "🛑 서버 중지 중..."
echo ""

STOPPED=0

# Discord 봇 중지
if [ -f ".discord_bot.pid" ]; then
    PID=$(cat .discord_bot.pid)
    if ps -p $PID > /dev/null 2>&1; then
        echo "🤖 Discord 봇 중지 중 (PID: $PID)..."
        kill -SIGTERM $PID 2>/dev/null || true
        
        # 종료 대기 (최대 10초)
        for i in {1..10}; do
            if ! ps -p $PID > /dev/null 2>&1; then
                echo -e "${GREEN}✅ Discord 봇이 종료되었습니다.${NC}"
                rm .discord_bot.pid
                STOPPED=$((STOPPED + 1))
                break
            fi
            sleep 1
        done
        
        # 강제 종료
        if ps -p $PID > /dev/null 2>&1; then
            echo -e "${YELLOW}⚠️  정상 종료 실패. 강제 종료 중...${NC}"
            kill -9 $PID 2>/dev/null || true
            rm .discord_bot.pid
            STOPPED=$((STOPPED + 1))
        fi
    else
        echo -e "${YELLOW}⚠️  Discord 봇이 실행 중이지 않습니다 (PID 파일만 존재).${NC}"
        rm .discord_bot.pid
    fi
else
    echo -e "${YELLOW}⚠️  Discord 봇 PID 파일이 없습니다.${NC}"
fi

echo ""

# Flask 서버 중지
if [ -f ".flask.pid" ]; then
    PID=$(cat .flask.pid)
    if ps -p $PID > /dev/null 2>&1; then
        echo "🌐 Flask 서버 중지 중 (PID: $PID)..."
        kill -SIGTERM $PID 2>/dev/null || true
        
        # 종료 대기 (최대 10초)
        for i in {1..10}; do
            if ! ps -p $PID > /dev/null 2>&1; then
                echo -e "${GREEN}✅ Flask 서버가 종료되었습니다.${NC}"
                rm .flask.pid
                STOPPED=$((STOPPED + 1))
                break
            fi
            sleep 1
        done
        
        # 강제 종료
        if ps -p $PID > /dev/null 2>&1; then
            echo -e "${YELLOW}⚠️  정상 종료 실패. 강제 종료 중...${NC}"
            kill -9 $PID 2>/dev/null || true
            rm .flask.pid
            STOPPED=$((STOPPED + 1))
        fi
    else
        echo -e "${YELLOW}⚠️  Flask 서버가 실행 중이지 않습니다 (PID 파일만 존재).${NC}"
        rm .flask.pid
    fi
else
    echo -e "${YELLOW}⚠️  Flask 서버 PID 파일이 없습니다.${NC}"
fi

echo ""

if [ $STOPPED -gt 0 ]; then
    echo -e "${GREEN}✅ 서버 중지 완료 ($STOPPED개 프로세스 종료됨)${NC}"
else
    echo -e "${YELLOW}⚠️  실행 중인 서버가 없었습니다.${NC}"
fi
