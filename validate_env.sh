#!/bin/bash

# 환경 변수 검증 스크립트
# 필수 환경변수 확인 및 보안 검사

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "🔍 환경 변수 검증 시작..."
echo ""

# .env 파일 존재 확인
if [ ! -f ".env" ]; then
    echo -e "${RED}❌ .env 파일이 존재하지 않습니다.${NC}"
    echo "   .env.example을 .env로 복사하고 필수 값을 입력하세요:"
    echo "   cp .env.example .env"
    exit 1
fi

# .env 파일 로드
export $(grep -v '^#' .env | xargs)

# 검증 카운터
ERRORS=0
WARNINGS=0

echo "📋 필수 환경변수 확인:"
echo ""

# DISCORD_TOKEN 확인
if [ -z "$DISCORD_TOKEN" ] || [ "$DISCORD_TOKEN" = "your_token_here" ]; then
    echo -e "${RED}❌ DISCORD_TOKEN이 설정되지 않았습니다.${NC}"
    ERRORS=$((ERRORS + 1))
else
    echo -e "${GREEN}✅ DISCORD_TOKEN: 설정됨${NC}"
fi

# ADMIN_PASSWORD 확인
if [ -z "$ADMIN_PASSWORD" ] || [ "$ADMIN_PASSWORD" = "your_secure_password_here" ]; then
    echo -e "${RED}❌ ADMIN_PASSWORD가 설정되지 않았습니다.${NC}"
    ERRORS=$((ERRORS + 1))
elif [ "$ADMIN_PASSWORD" = "admin1234" ]; then
    echo -e "${YELLOW}⚠️  ADMIN_PASSWORD가 기본값(admin1234)입니다. 보안을 위해 변경하세요.${NC}"
    WARNINGS=$((WARNINGS + 1))
elif [ ${#ADMIN_PASSWORD} -lt 8 ]; then
    echo -e "${YELLOW}⚠️  ADMIN_PASSWORD가 너무 짧습니다 (8자 이상 권장).${NC}"
    WARNINGS=$((WARNINGS + 1))
else
    echo -e "${GREEN}✅ ADMIN_PASSWORD: 설정됨 (${#ADMIN_PASSWORD}자)${NC}"
fi

# FLASK_SECRET_KEY 확인
if [ -z "$FLASK_SECRET_KEY" ] || [ "$FLASK_SECRET_KEY" = "your-random-secret-key-here" ]; then
    echo -e "${RED}❌ FLASK_SECRET_KEY가 설정되지 않았습니다.${NC}"
    ERRORS=$((ERRORS + 1))
elif [ ${#FLASK_SECRET_KEY} -lt 32 ]; then
    echo -e "${YELLOW}⚠️  FLASK_SECRET_KEY가 너무 짧습니다 (32자 이상 권장).${NC}"
    WARNINGS=$((WARNINGS + 1))
else
    echo -e "${GREEN}✅ FLASK_SECRET_KEY: 설정됨 (${#FLASK_SECRET_KEY}자)${NC}"
fi

# DB_PATH 확인
if [ -z "$DB_PATH" ]; then
    echo -e "${YELLOW}⚠️  DB_PATH가 설정되지 않았습니다. 기본값(data/bot.db) 사용.${NC}"
    WARNINGS=$((WARNINGS + 1))
    DB_PATH="data/bot.db"
else
    echo -e "${GREEN}✅ DB_PATH: $DB_PATH${NC}"
fi

echo ""
echo "📊 검증 결과:"
echo "   에러: $ERRORS"
echo "   경고: $WARNINGS"
echo ""

if [ $ERRORS -gt 0 ]; then
    echo -e "${RED}❌ 환경 변수 검증 실패. .env 파일을 수정하세요.${NC}"
    exit 1
elif [ $WARNINGS -gt 0 ]; then
    echo -e "${YELLOW}⚠️  경고가 있지만 실행 가능합니다.${NC}"
    exit 0
else
    echo -e "${GREEN}✅ 모든 환경 변수가 올바르게 설정되었습니다.${NC}"
    exit 0
fi
