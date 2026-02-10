# 봇 재시작 가이드

## 🚀 빠른 재시작 (macOS/Linux)

### 방법 1: 프로세스 직접 종료 후 재시작

```bash
# 1. 프로젝트 디렉토리로 이동
cd /Users/mac/Documents/자료/요진편/challenger-bot-mk2

# 2. 실행 중인 봇 프로세스 종료
pkill -f "python.*main.py"

# 3. 봇 재시작
python src/main.py

# 또는 백그라운드로 실행
nohup python src/main.py > logs/nohup.log 2>&1 &
```

### 방법 2: PID를 확인하고 종료

```bash
# 1. 실행 중인 봇 프로세스 찾기
ps aux | grep "python.*main.py" | grep -v grep

# 출력 예시:
# user  12345  0.5  1.2  ... python src/main.py
#       ^^^^^
#       이 숫자가 PID

# 2. PID를 사용하여 종료
kill 12345

# 강제 종료가 필요한 경우
kill -9 12345

# 3. 봇 재시작
python src/main.py
```

---

## 🔧 Hot Reload 사용 (봇 재시작 없이 코드 반영)

봇이 실행 중일 때 코드를 수정했다면, **봇을 재시작하지 않고** Cog만 다시 로드할 수 있습니다:

```
Discord에서 실행:
!reload challenge   # challenge.py 수정 시
!reload shop        # shop.py 수정 시
!reload ranking     # ranking.py 수정 시
```

**주의**: 
- 봇 소유자만 실행 가능합니다 (.env 파일의 OWNER_ID 설정 필요)
- `main.py`나 `config.py` 같은 코어 파일은 Hot Reload가 불가능하므로 봇을 재시작해야 합니다

### 기타 관리자 명령어

```
!load admin        # 새로운 Cog 로드
!unload shop       # Cog 언로드 (비활성화)
!cogs              # 로드된 모든 Cog 목록 확인
```

---

## 🐧 systemd 사용 (Linux 서버 배포 시)

### 초기 설정

```bash
# 1. 서비스 파일 복사
sudo cp deployment/challenger-bot.service /etc/systemd/system/

# 2. 서비스 파일 편집 (User, WorkingDirectory, ExecStart 경로 수정)
sudo nano /etc/systemd/system/challenger-bot.service

# 3. systemd 데몬 재시작
sudo systemctl daemon-reload

# 4. 서비스 활성화 (부팅 시 자동 시작)
sudo systemctl enable challenger-bot

# 5. 서비스 시작
sudo systemctl start challenger-bot
```

### 일상적인 사용

```bash
# 봇 재시작
sudo systemctl restart challenger-bot

# 봇 중지
sudo systemctl stop challenger-bot

# 봇 시작
sudo systemctl start challenger-bot

# 상태 확인
sudo systemctl status challenger-bot

# 실시간 로그 확인
sudo journalctl -u challenger-bot -f

# 최근 로그 100줄 확인
sudo journalctl -u challenger-bot -n 100
```

---

## ✅ 재시작 검증

### 1. 로그 확인

```bash
# 봇 로그 실시간 모니터링
tail -f logs/bot.log

# 확인할 내용:
# ✅ "봇이 시작되었습니다." 메시지
# ✅ "Cog 로드 완료: cogs.challenge" 메시지
# ✅ "Cog 로드 완료: cogs.admin" 메시지
# ❌ "Extension is already loaded" 에러가 없어야 함
```

### 2. Discord에서 테스트

```
1. 포럼 스레드로 이동
2. !인증 입력 + 사진 첨부 후 전송
3. ✅ "인증 완료!" 메시지 확인
4. ✅ 골드 지급 확인
```

### 3. 인증 명령어 로그 확인

```bash
# 인증 관련 로그만 필터링
tail -f logs/bot.log | grep -E "(인증|에러|ERROR)"

# 정상 작동 시 출력 예시:
# [인증 시작] 사용자: username (123456789)
# [골드 지급] 사용자: username (123456789) - 골드: 10
# [인증 완료] 사용자: username (123456789)
```

---

## 🔍 문제 해결

### 문제 1: "Extension is already loaded" 에러

**원인**: 이전 봇 인스턴스가 완전히 종료되지 않음

**해결**:
```bash
# 모든 Python 프로세스 확인
ps aux | grep python

# 봇 관련 프로세스 강제 종료
pkill -9 -f "python.*main.py"

# 잠시 대기
sleep 2

# 봇 재시작
python src/main.py
```

### 문제 2: 봇이 시작되지 않음

**확인 사항**:
```bash
# .env 파일 존재 여부
ls -la .env

# Python 의존성 설치 여부
pip list | grep discord

# 포트 충돌 (Flask 사용 시)
lsof -i :5000
```

### 문제 3: 로그에 에러가 계속 발생

```bash
# 전체 에러 로그 확인
grep -i "error\|traceback" logs/bot.log

# 특정 시간대의 로그 확인
grep "2024-01-15 14:" logs/bot.log
```

---

## 📝 봇 소유자 설정

Hot Reload 기능을 사용하려면 `.env` 파일에 봇 소유자 ID를 설정해야 합니다:

```bash
# .env 파일에 추가
OWNER_ID=123456789012345678
```

**봇 소유자 ID 확인 방법**:
1. Discord 설정 → 고급 → 개발자 모드 활성화
2. 본인 프로필 우클릭 → ID 복사

---

## 🎯 요약

| 상황 | 명령어 | 설명 |
|------|--------|------|
| Cog 수정 후 | `!reload challenge` (Discord) | 봇 재시작 없이 반영 |
| main.py 수정 후 | `pkill -f "python.*main.py" && python src/main.py` | 봇 재시작 필요 |
| Linux 서버 | `sudo systemctl restart challenger-bot` | systemd로 관리 |
| 로그 확인 | `tail -f logs/bot.log` | 실시간 로그 모니터링 |
| 문제 발생 | `pkill -9 -f "python.*main.py"` | 강제 종료 후 재시작 |
