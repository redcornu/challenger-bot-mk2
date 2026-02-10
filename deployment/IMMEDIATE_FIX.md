# ⚡ !인증 명령어 에러 즉시 해결 가이드

## 🚨 현재 상황

✅ **코드 수정 완료**: `src/cogs/challenge.py`에 `update_user_inventory` import 추가됨  
❌ **봇이 구버전 실행 중**: 2026-02-10 20:48:35 기준, 여전히 `NameError` 발생 중  
⚠️ **OWNER_ID 미설정**: Hot Reload 기능 사용 불가

---

## 🔧 즉시 해결 방법

### Step 1: 봇 완전 종료

```bash
cd /Users/mac/Documents/자료/요진편/challenger-bot-mk2

# 실행 중인 모든 봇 프로세스 강제 종료
pkill -9 -f "python.*main.py"

# 프로세스가 완전히 종료되었는지 확인 (출력이 없어야 정상)
ps aux | grep "python.*main.py" | grep -v grep
```

### Step 2: OWNER_ID 설정 (Hot Reload 기능 활성화)

```bash
# .env 파일 열기
nano .env

# 또는
vim .env
```

**파일 맨 아래에 추가**:
```env
# Discord 봇 소유자 ID (본인 Discord 사용자 ID)
OWNER_ID=YOUR_DISCORD_USER_ID
```

**Discord 사용자 ID 확인 방법**:
1. Discord 설정 → 고급 → **개발자 모드 활성화**
2. 본인 프로필 우클릭 → **ID 복사**
3. 복사한 ID를 위 `YOUR_DISCORD_USER_ID` 위치에 붙여넣기

**예시**:
```env
OWNER_ID=123456789012345678
```

저장 후 종료:
- nano: `Ctrl+X` → `Y` → `Enter`
- vim: `:wq` → `Enter`

### Step 3: 봇 재시작

```bash
# 봇 시작
python src/main.py

# 또는 백그라운드로 실행 (터미널 종료해도 계속 실행)
nohup python src/main.py > logs/nohup.log 2>&1 &
```

### Step 4: 재시작 확인

**터미널에서 로그 모니터링**:
```bash
tail -f logs/bot.log
```

**확인할 내용**:
```
✅ "봇이 시작되었습니다." - 봇 시작 성공
✅ "Cog 로드 완료: cogs.challenge" - Challenge Cog 로드 성공
✅ "Cog 로드 완료: cogs.admin" - Admin Cog 로드 성공 (Hot Reload 기능)
❌ "Extension is already loaded" - 이 에러가 없어야 함
```

---

## ✅ 테스트

### Discord에서 !인증 테스트

1. Discord 포럼 스레드로 이동
2. 메시지 작성:
   - 텍스트: `!인증`
   - 파일 첨부: 사진 추가
3. **한 번에 전송** (Ctrl+Enter 또는 전송 버튼)

**예상 결과**:
```
✅ 인증 완료! 골드 10개를 획득했습니다.
```

**로그에서 확인**:
```bash
tail -f logs/bot.log | grep "인증"

# 출력 예시 (정상 작동 시):
# [인증 시작] 사용자: username (123456789)
# [골드 지급] 사용자: username (123456789) - 골드: 10
# [인증 완료] 사용자: username (123456789)
```

---

## 🔥 Hot Reload 테스트 (선택 사항)

봇을 재시작하지 않고 코드를 수정한 후:

```
Discord에서 실행:
!reload challenge
```

**예상 결과**:
```
✅ `cogs.challenge` Cog이 다시 로드되었습니다.
```

**주의**: 
- `!reload` 명령어는 **봇 소유자만** 실행 가능합니다
- OWNER_ID가 올바르게 설정되어 있어야 합니다
- `main.py`, `config.py`, `database.py` 같은 코어 파일은 Hot Reload 불가 (봇 재시작 필요)

---

## 🆘 문제 해결

### 문제 1: "Extension is already loaded" 에러

봇 프로세스가 완전히 종료되지 않았습니다.

```bash
# 강제 종료
pkill -9 -f "python.*main.py"

# 2초 대기
sleep 2

# 프로세스 확인 (출력이 없어야 정상)
ps aux | grep "python.*main.py" | grep -v grep

# 봇 재시작
python src/main.py
```

### 문제 2: !reload 명령어 실행 시 "권한이 없습니다" 에러

OWNER_ID가 올바르게 설정되지 않았습니다.

```bash
# .env 파일 확인
grep OWNER_ID .env

# 출력이 없거나 잘못된 ID라면 다시 설정
nano .env
```

**Discord 사용자 ID 확인**:
- Discord 설정 → 고급 → 개발자 모드 ON
- 본인 프로필 우클릭 → ID 복사

### 문제 3: 봇이 시작되지 않음

```bash
# 의존성 확인
pip list | grep discord.py

# 없으면 설치
pip install -r requirements.txt

# .env 파일 확인
cat .env

# DISCORD_TOKEN이 있는지 확인
```

### 문제 4: !인증 명령어가 여전히 에러 발생

```bash
# 봇이 정말로 재시작되었는지 확인
tail -20 logs/bot.log

# "봇이 시작되었습니다." 메시지가 최근에 있어야 함
# 만약 없다면 봇이 재시작되지 않은 것

# 다시 강제 종료 후 재시작
pkill -9 -f "python.*main.py"
sleep 2
python src/main.py
```

---

## 📊 개선 사항 요약

이번 수정으로 추가된 기능:

### 1. Hot Reload 기능 (`cogs/admin.py`)
- `!reload <cog_name>`: Cog 다시 로드 (봇 재시작 없이)
- `!load <cog_name>`: 새로운 Cog 로드
- `!unload <cog_name>`: Cog 언로드
- `!cogs`: 로드된 Cog 목록 확인

### 2. 개선된 에러 로깅 (`main.py`)
- 명령어 실행 위치 추적
- 사용자 정보 기록
- 에러 타입 및 스택 트레이스 자세히 기록
- 권한 에러 처리 추가

### 3. 배포 문서
- `deployment/RESTART_GUIDE.md`: 상세한 재시작 가이드
- `deployment/challenger-bot.service`: systemd 서비스 파일 (Linux 서버용)
- `deployment/IMMEDIATE_FIX.md`: 이 파일 (즉시 해결 가이드)

---

## 🎯 체크리스트

- [ ] 봇 프로세스 완전 종료 (`pkill -9 -f "python.*main.py"`)
- [ ] `.env`에 `OWNER_ID` 추가
- [ ] 봇 재시작 (`python src/main.py`)
- [ ] 로그 확인 (`tail -f logs/bot.log`)
- [ ] Discord에서 `!인증` 테스트
- [ ] (선택) `!reload` 명령어 테스트

---

## 📞 추가 도움이 필요하면

1. `logs/bot.log` 파일의 최근 50줄 확인:
   ```bash
   tail -50 logs/bot.log
   ```

2. 에러 로그만 필터링:
   ```bash
   grep -i "error\|traceback" logs/bot.log | tail -20
   ```

3. 실시간 인증 로그 모니터링:
   ```bash
   tail -f logs/bot.log | grep -E "(인증|에러|ERROR)"
   ```
