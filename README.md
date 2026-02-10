# 오리와 66일의 약속 🦆

습관 형성을 위한 타마고치 스타일 Discord 봇

## 기능

- **66일 습관 형성 챌린지**: 과학적으로 입증된 습관 형성 기간
- **오리 육성 시뮬레이션**: 알 → 병아리 → 청소년 → 성체 → 졸업
- **랭킹 시스템**: 졸업한 오리 수 기준 명예의 전당
- **상점 및 아이템**: 골드로 아이템 구매, 복구 아이템 사용
- **페널티 시스템**: SULKY, RUNAWAY 상태 자동 적용

## 설치 방법

### 1. 프로젝트 클론

```bash
git clone <repository_url>
cd challenger-bot-mk2
```

### 2. 가상환경 생성 및 의존성 설치

```bash
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. 환경변수 설정

```bash
cp .env.example .env
# .env 파일을 열어서 Discord 토큰 입력
```

**.env 파일 예시:**
```env
DISCORD_TOKEN=your_discord_bot_token_here
DB_PATH=data/bot.db
DEBUG_MODE=False

# 시간당 자동 랭킹 (선택)
RANKING_CHANNEL_ID=0  # 0으로 설정하면 비활성화

# 관리자 대시보드 (선택)
ADMIN_PASSWORD=your_secure_password_here
FLASK_SECRET_KEY=your-random-secret-key-here

# Flask 서버 설정 (macOS AirPlay Receiver가 5000번 포트를 사용하므로 5001 사용)
FLASK_HOST=0.0.0.0
FLASK_PORT=5001

# Flask 모니터링 (선택)
MONITORING_CHANNEL_ID=0  # 0으로 설정하면 비활성화
```

### 4. Discord Bot 설정

1. [Discord Developer Portal](https://discord.com/developers/applications)에서 봇 생성
2. Bot 탭에서 토큰 복사 → .env 파일에 입력
3. OAuth2 → URL Generator에서 권한 설정:
   - Scopes: `bot`, `applications.commands`
   - Permissions: Send Messages, Embed Links, Attach Files, Read Message History, Use Threads
4. 생성된 URL로 봇을 서버에 초대
5. 포럼 채널 생성 (봇이 작동할 채널)

### 5. 봇 실행

#### 방법 1: 스크립트 사용 (추천)

```bash
# 서버 시작 (Discord 봇 + Flask 대시보드)
./start_servers.sh

# 상태 확인
./check_status.sh

# 서버 중지
./stop_servers.sh

# 환경 변수 검증
./validate_env.sh
```

#### 방법 2: 수동 실행

```bash
# Discord 봇 (Flask 서버 자동 시작됨)
python src/main.py
```

#### 방법 3: 개별 실행

```bash
# 터미널 1 - Discord 봇
python src/main.py

# 터미널 2 - 관리자 대시보드
python src/admin/app.py
```

### 6. 관리자 대시보드 접속

브라우저에서 `http://localhost:5001` 접속 후 `.env`에 설정한 비밀번호로 로그인

**참고:** macOS 사용자는 AirPlay Receiver가 기본적으로 5000번 포트를 사용하므로 Flask는 5001번 포트를 사용합니다. 필요시 `.env`에서 `FLASK_PORT`를 변경할 수 있습니다.

**기능:**
- 📊 유저 통계 대시보드
- 👥 유저 목록 및 검색
- ✏️ 유저 정보 수정 (골드, 오리 수)
- 🔒 비밀번호 기반 세션 인증

## 명령어

### 사용자 명령어

| 명령어 | 기능 | 사용법 |
|--------|------|--------|
| `!목표설정 [목표]` | 새로운 도전 시작 | `!목표설정 매일 운동하기` |
| `!인증` | 일일 인증 (사진 필수) | `!인증` (사진 첨부) |
| `!상태` | 현재 오리 상태 및 인벤토리 확인 | `!상태` |
| `!상점` | 아이템 목록 | `!상점` |
| `!구매 [아이템]` | 아이템 구매 | `!구매 회복약` |
| `!인벤토리` | !상태로 통합됨 (안내 메시지 표시) | `!인벤토리` |
| `!랭킹` | 명예의 전당 (Top 10) | `!랭킹` |

### 관리자 명령어 (Discord)

| 명령어 | 기능 | 사용법 |
|--------|------|--------|
| `!admin status` | Flask 서버 상태 조회 | `!admin status` |
| `!admin start` | Flask 서버 시작 | `!admin start` |
| `!admin stop` | Flask 서버 중지 | `!admin stop` |
| `!admin restart` | Flask 서버 재시작 | `!admin restart` |
| `!admin logs [줄수]` | Flask 로그 조회 (기본 50줄) | `!admin logs 100` |
| `!admin validate` | 환경 변수 검증 | `!admin validate` |

**⚠️ 관리자 권한 필요**: Discord 서버 관리자만 사용 가능

**💡 개선사항:**
- 🇰🇷 **한글 UX**: 오리 상태가 한글로 표시됩니다 (알, 병아리, 사춘기, 어른, 졸업 등)
- 📊 **통합 상태**: !상태 명령어에서 도전 현황, 내 정보, 인벤토리를 한 번에 확인
- 📈 **정확한 추적**: 총 인증일(total_days)이 정확하게 기록됩니다
- 🏆 **공정한 랭킹**: 졸업 오리 수 → 총 인증일 → 골드 순으로 정렬
- ⏰ **자동 랭킹**: 설정 시 매 시간마다 랭킹이 자동으로 게시됩니다
- 🤖 **자동화 시스템**: Flask 서버 자동 시작/중지, 헬스 체크, 자동 복구

## 자동화 기능 (NEW!)

### Hook: Flask 서버 생명주기 관리
- Discord 봇 시작 시 Flask 서버 자동 시작
- 봇 종료 시 Flask 서버 안전하게 종료
- 의존성 및 환경 변수 자동 검증

### Skill: Discord 명령어로 서버 제어
- `!admin` 명령어로 Flask 서버 관리
- 관리자 권한 확인
- 실시간 상태 모니터링 (CPU, 메모리, HTTP 응답)

### Subagent: 자동 모니터링 및 복구
- 5분마다 자동 헬스 체크
- 연속 3회 실패 시 자동 재시작
- Discord 채널로 실시간 알림
- 일일 리포트 자동 전송 (자정)

**설정 방법:**
```env
# .env 파일에 추가
MONITORING_CHANNEL_ID=1234567890  # Discord 채널 ID
```

## 🚀 AWS Lightsail 배포

AWS Lightsail에서 이 봇을 24/7 운영하려면 **[DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)** 를 참고하세요.

### 빠른 시작 (자동화 스크립트)

1. **Ubuntu 22.04 Lightsail 인스턴스 생성** ($5 또는 $10/월 플랜)
2. **SSH 연결 후 자동 설정 스크립트 실행:**
   ```bash
   git clone <repository_url> challenger-bot-mk2
   cd challenger-bot-mk2
   ./scripts/lightsail-setup.sh
   ```
3. **.env 파일 수정** (DISCORD_TOKEN, ADMIN_PASSWORD 등)
4. **웹 대시보드 접속:** `http://YOUR_IP:5001`

### 주요 기능

- ✅ **Systemd 서비스**: 자동 시작, 자동 재시작, 로그 관리
- ✅ **자동화 스크립트**: 배포, 업데이트, 백업 스크립트 제공
- ✅ **초보자 친화적**: AWS/Linux 경험 없어도 단계별 가이드로 따라하기
- ✅ **프로덕션 준비**: 방화벽, 보안 설정, 모니터링 포함

### 제공 스크립트

| 스크립트 | 기능 |
|---------|------|
| `scripts/lightsail-setup.sh` | 서버 초기 설정 자동화 (단계 3-5) |
| `scripts/update-deployment.sh` | Git에서 최신 코드 가져와 재배포 |
| `scripts/backup-db.sh` | 데이터베이스 백업 및 오래된 백업 정리 |

### 비용

- **$5/월**: 최소 사양 (512MB RAM, 테스트용)
- **$10/월**: 권장 사양 (1GB RAM, 안정적 운영)

자세한 단계는 **[DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)** 를 참고하세요.

## 오리 성장 단계

| 단계 | 조건 | 아이콘 | 설명 |
|------|------|-------|------|
| EGG | 시작 | 🥚 | 알에서 시작 |
| DUCKLING | 7일 | 🐣 | 부화! 귀여운 아기 오리 |
| ADOLESCENT | 22일 | 🦆 | 청소년기 오리 |
| ADULT | 43일 | 🦢 | 성체 오리 |
| DONE | 66일 | 🎓 | 졸업! 습관 형성 완료 |

### 페널티 상태

- **SULKY (삐침)**: 1일 건너뛰면 발생, 3일 이내 회복약 사용 가능
- **RUNAWAY (가출)**: 2일 연속 건너뛰면 발생, 7일 이내 귀환석 사용 가능

## 프로젝트 구조

```
challenger-bot-mk2/
├── src/
│   ├── main.py              # 봇 엔트리 포인트
│   ├── config.py            # 설정 및 상수
│   ├── database.py          # DB 레이어 (Context Manager 패턴)
│   ├── cogs/                # 명령어 그룹 (Cogs 패턴)
│   │   ├── challenge.py     # 도전 관련 명령어
│   │   ├── shop.py          # 상점 관련 명령어
│   │   └── ranking.py       # 랭킹 관련 명령어 (자동 게시)
│   ├── admin/               # 웹 관리자 대시보드
│   │   ├── app.py           # Flask 애플리케이션
│   │   ├── auth.py          # 인증 로직
│   │   ├── templates/       # HTML 템플릿
│   │   └── static/          # CSS 스타일
│   ├── hooks/               # 생명주기 Hook (NEW!)
│   │   └── flask_lifecycle.py  # Flask 자동 시작/중지
│   ├── skills/              # Discord 명령어 Skill (NEW!)
│   │   └── flask_admin.py   # Flask 서버 관리 명령어
│   ├── agents/              # 자동화 Subagent (NEW!)
│   │   └── dashboard_admin.py  # 자동 모니터링 및 복구
│   └── utils/               # 헬퍼 함수
│       ├── embed_builder.py # Embed 생성
│       └── validators.py    # 검증 로직
├── assets/                  # 이미지 리소스
├── tests/                   # 유닛 테스트
├── logs/                    # 로그 파일
├── data/                    # 데이터베이스
├── start_servers.sh         # 서버 시작 스크립트 (NEW!)
├── stop_servers.sh          # 서버 중지 스크립트 (NEW!)
├── check_status.sh          # 상태 확인 스크립트 (NEW!)
├── validate_env.sh          # 환경 변수 검증 스크립트 (NEW!)
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

## 개발

### 테스트 실행

```bash
pytest tests/ -v
```

### 보안 검증

```bash
python .claude/skills/discord-bot-creator/scripts/validate_security.py .
```

### 코드 포매팅

```bash
black src/ tests/
isort src/ tests/
```

## 기술 스택

- **Discord.py 2.3+**: Discord 봇 프레임워크
- **python-dotenv**: 환경변수 관리
- **SQLite3**: 경량 데이터베이스
- **Flask 3.0**: 관리자 대시보드 웹 프레임워크
- **Python 3.9+**: zoneinfo 사용 (timezone-aware)

## 보안

- ✅ .env 파일 Git 제외
- ✅ 환경변수 검증 on startup
- ✅ Context Manager DB 연결 (자동 commit/rollback)
- ✅ 안전한 JSON 파싱 (safe_json_loads)
- ✅ Timezone-aware datetime (get_kst_now)

## 베스트 프랙티스

이 프로젝트는 다음 베스트 프랙티스를 따릅니다:

1. **보안 우선**: .gitignore 가장 먼저 생성, .env 절대 커밋 금지
2. **코드 중복 제거**: config.py에 상수 중앙 집중, Context Manager 패턴
3. **모듈화**: Cogs 패턴으로 명령어 분리, 단일 책임 원칙
4. **에러 처리**: safe_json_loads, 전역 에러 핸들러
5. **Timezone 처리**: get_kst_now() 사용, datetime.utcnow() 금지

자세한 내용은 `workflow-guidebook.md`를 참조하세요.

## 라이선스

MIT

## 기여

이슈 및 PR 환영합니다!

## 제작

🤖 Generated with [Claude Code](https://claude.com/claude-code) using discord-bot-creator skill
