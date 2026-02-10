#!/bin/bash

# 데이터베이스 백업 스크립트
# SQLite 데이터베이스를 백업하고 오래된 백업을 정리합니다.

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# 현재 디렉토리 확인
if [ ! -f "data/bot.db" ]; then
    echo -e "${RED}❌ 데이터베이스 파일을 찾을 수 없습니다: data/bot.db${NC}"
    exit 1
fi

# 백업 디렉토리 생성
mkdir -p data/backups

# 백업 파일명 생성 (날짜_시간)
BACKUP_FILE="data/backups/bot_$(date +%Y%m%d_%H%M%S).db"

# 백업 실행
echo -e "${YELLOW}💾 데이터베이스 백업 중...${NC}"
cp data/bot.db "$BACKUP_FILE"
echo -e "${GREEN}✅ 백업 완료: $BACKUP_FILE${NC}"

# 백업 파일 크기 확인
BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
echo -e "${GREEN}   파일 크기: $BACKUP_SIZE${NC}"

# 7일 이상 된 백업 삭제
echo ""
echo -e "${YELLOW}🗑️  오래된 백업 정리 중 (7일 이상)...${NC}"
DELETED_COUNT=$(find data/backups -name "bot_*.db" -mtime +7 -delete -print | wc -l)
if [ "$DELETED_COUNT" -gt 0 ]; then
    echo -e "${GREEN}✅ $DELETED_COUNT 개의 오래된 백업 삭제 완료${NC}"
else
    echo -e "${GREEN}✅ 삭제할 오래된 백업이 없습니다${NC}"
fi

# 현재 백업 파일 목록
echo ""
echo -e "${YELLOW}📁 현재 백업 파일 목록:${NC}"
ls -lh data/backups/bot_*.db 2>/dev/null | awk '{print "   " $9 " (" $5 ")"}'

echo ""
echo -e "${GREEN}✅ 백업 작업 완료!${NC}"
