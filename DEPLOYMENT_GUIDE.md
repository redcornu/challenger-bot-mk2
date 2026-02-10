# AWS Lightsail 배포 가이드

> **오리와 66일의 약속** Discord 챗봇을 AWS Lightsail에서 24/7 운영하기 위한 완전한 배포 가이드입니다.

이 가이드는 AWS/Linux 경험이 없는 초보자도 단계별로 따라할 수 있도록 작성되었습니다.

---

## 📋 목차

1. [AWS Lightsail 인스턴스 생성](#단계-1-aws-lightsail-인스턴스-생성)
2. [SSH 연결](#단계-2-ssh-연결)
3. [서버 초기 설정](#단계-3-서버-초기-설정)
4. [프로젝트 배포](#단계-4-프로젝트-배포)
5. [Systemd 서비스 설정](#단계-5-systemd-서비스-설정-프로덕션-권장)
6. [Lightsail 방화벽 설정](#단계-6-lightsail-방화벽-설정)
7. [배포 확인](#단계-7-배포-확인)
8. [자동화 스크립트 사용 (선택)](#단계-8-선택-자동화-스크립트-사용)
9. [모니터링 및 유지보수](#단계-9-모니터링-및-유지보수)
10. [문제 해결](#단계-10-문제-해결)
11. [부록 A: Discord 봇 토큰 발급](#부록-a-discord-봇-토큰-발급)
12. [부록 B: 비용 분석](#부록-b-비용-분석)

---

## 단계 1: AWS Lightsail 인스턴스 생성

### 1.1 AWS 계정 생성

이미 AWS 계정이 있다면 이 단계를 스킵하세요.

1. [AWS 계정 생성 페이지](https://aws.amazon.com/)로 이동
2. "AWS 계정 생성" 클릭
3. 이메일, 비밀번호, 계정 이름 입력
4. 연락처 정보 및 결제 정보 입력
5. 본인 확인 (전화 인증)

### 1.2 Lightsail 콘솔 접근

1. [AWS Lightsail 콘솔](https://lightsail.aws.amazon.com/)에 로그인
2. 우측 상단에서 리전을 **Seoul (ap-northeast-2)** 로 변경 (권장)

### 1.3 인스턴스 생성

1. **"인스턴스 생성"** 버튼 클릭

2. **인스턴스 위치 선택:**
   - 리전: `Seoul (ap-northeast-2)` (한국에 가장 가까움)
   - 가용 영역: `ap-northeast-2a` (기본값)

3. **플랫폼 선택:**
   - **Linux/Unix** 선택

4. **운영 체제 선택:**
   - **OS 전용** 선택
   - **Ubuntu 22.04 LTS** 선택

5. **인스턴스 플랜 선택:**
   - **$5/월 플랜** (512MB RAM, 1 vCPU, 20GB SSD) - 최소 사양, 테스트용
   - **$10/월 플랜** (1GB RAM, 1 vCPU, 40GB SSD) - **권장**, 안정적 운영

6. **인스턴스 이름 지정:**
   - 예: `challenger-bot` 또는 `discord-bot`

7. **"인스턴스 생성"** 클릭

### 1.4 SSH 키 다운로드

1. 인스턴스 생성 시 자동으로 SSH 키가 생성됩니다.
2. **계정 페이지 → SSH 키** 탭에서 `LightsailDefaultKey-ap-northeast-2.pem` 다운로드
3. 안전한 위치에 저장 (예: `~/Downloads/LightsailDefaultKey-ap-northeast-2.pem`)

### 1.5 고정 IP 생성 및 연결 (선택, 권장)

고정 IP를 사용하면 인스턴스를 재시작해도 IP가 변경되지 않습니다.

1. Lightsail 콘솔 → **네트워킹** 탭
2. **고정 IP 생성** 클릭
3. 생성한 인스턴스(`challenger-bot`)에 연결
4. 고정 IP 주소를 메모 (예: `13.125.xxx.xxx`)

---

## 단계 2: SSH 연결

### 2.1 방법 1: 로컬 터미널에서 SSH 연결 (macOS/Linux)

1. **SSH 키 권한 설정:**
   ```bash
   chmod 400 ~/Downloads/challenger-duck.pem
   ```

2. **SSH 연결:**
   ```bash
   ssh -i ~/Downloads/challenger-duck.pem ubuntu@3.39.110.88
   ```
   `YOUR_IP`를 실제 Lightsail 인스턴스 IP로 교체하세요.

3. 처음 연결 시 fingerprint 확인 메시지가 나타나면 `yes` 입력

### 2.2 방법 2: Lightsail 브라우저 기반 SSH (초보자 권장)

1. Lightsail 콘솔에서 인스턴스 선택
2. 우측 상단의 **터미널 아이콘** 클릭
3. 브라우저에서 바로 SSH 터미널이 열립니다.

> **팁:** 브라우저 기반 SSH가 초보자에게 가장 간단합니다. SSH 키 설정이 필요 없습니다.

---

## 단계 3: 서버 초기 설정

SSH로 서버에 연결된 상태에서 다음 명령어를 실행합니다.

### 3.1 시스템 업데이트

```bash
sudo apt update && sudo apt upgrade -y
```

이 과정은 5-10분 소요될 수 있습니다.

### 3.2 필수 패키지 설치

```bash
sudo apt install -y python3.9 python3-pip python3-venv git curl ufw
```

### 3.3 방화벽 설정

```bash
sudo ufw allow OpenSSH
sudo ufw allow 5001/tcp
sudo ufw enable
```

- `OpenSSH`: SSH 연결 허용 (22번 포트)
- `5001/tcp`: Flask 웹 대시보드 포트 허용
- `sudo ufw status`: 방화벽 상태 확인

---

## 단계 4: 프로젝트 배포

### 4.1 Git 저장소 클론

```bash
cd /home/ubuntu
git clone <REPOSITORY_URL> challenger-bot-mk2
cd challenger-bot-mk2
```

> **참고:** `<REPOSITORY_URL>`을 실제 Git 저장소 URL로 교체하세요.
>
> 예: `git clone https://github.com/yourusername/challenger-bot-mk2.git`

### 4.2 가상환경 생성 및 의존성 설치

```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

설치 과정은 3-5분 소요됩니다.

### 4.3 .env 파일 생성

```bash
cp .env.example .env
nano .env
```

**필수 환경변수 입력:**

```env
# Discord 봇 토큰 (Discord Developer Portal에서 발급)
DISCORD_TOKEN=your_discord_bot_token_here

# 웹 대시보드 비밀번호 (8자 이상 권장)
ADMIN_PASSWORD=your_secure_password_here

# Flask 세션 암호화 키 (32자 이상 랜덤 문자열)
FLASK_SECRET_KEY=your_random_32_character_secret_key_here

# 선택: Discord 모니터링 채널 ID (오류 알림 받을 채널)
MONITORING_CHANNEL_ID=1234567890123456789
```

**Discord 토큰 발급 방법은 [부록 A](#부록-a-discord-봇-토큰-발급)를 참고하세요.**

**nano 에디터 사용법:**
- 화살표 키로 이동
- `Ctrl + X` → `Y` → `Enter` 순서로 저장

### 4.4 환경변수 검증

```bash
chmod +x validate_env.sh
./validate_env.sh
```

**출력 예시:**
```
✅ 환경변수 검증 통과
  - DISCORD_TOKEN: OK
  - ADMIN_PASSWORD: OK (길이: 16)
  - FLASK_SECRET_KEY: OK (길이: 32)
```

오류가 발생하면 `.env` 파일을 다시 확인하세요:
```bash
nano .env
```

### 4.5 필수 디렉토리 생성

```bash
mkdir -p data logs
```

---

## 단계 5: Systemd 서비스 설정 (프로덕션 권장)

Systemd를 사용하면 다음과 같은 이점이 있습니다:
- 서버 재부팅 시 자동으로 봇 시작
- 봇이 크래시되면 자동으로 재시작
- 로그 관리가 용이
- 서비스 상태 모니터링 간편

### 5.1 Discord 봇 서비스 설치

```bash
sudo cp systemd/challenger-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable challenger-bot
```

### 5.2 Flask 서버 서비스 설치

```bash
sudo cp systemd/challenger-flask.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable challenger-flask
```

### 5.3 서비스 시작

```bash
sudo systemctl start challenger-bot
sudo systemctl start challenger-flask
```

### 5.4 서비스 상태 확인

```bash
sudo systemctl status challenger-bot
sudo systemctl status challenger-flask
```

**정상 출력 예시:**
```
● challenger-bot.service - Challenger Discord Bot (오리와 66일의 약속)
   Loaded: loaded (/etc/systemd/system/challenger-bot.service; enabled)
   Active: active (running) since ...
```

`active (running)` 상태가 표시되어야 합니다.

---

## 단계 6: Lightsail 방화벽 설정

Lightsail 콘솔에서 추가 방화벽 설정이 필요합니다.

1. **Lightsail 콘솔**로 이동
2. 인스턴스(`challenger-bot`) 선택
3. **네트워킹** 탭 클릭
4. **IPv4 방화벽** 섹션에서 **규칙 추가** 클릭

**규칙 추가:**
- 애플리케이션: `Custom`
- 프로토콜: `TCP`
- 포트 범위: `5001`
- 소스: `0.0.0.0/0` (전체 허용) 또는 특정 IP 주소

5. **생성** 클릭

**기본 규칙 확인:**
- SSH (22번 포트)는 기본으로 열려 있어야 합니다.

---

## 단계 7: 배포 확인

### 7.1 서비스 상태 확인

```bash
sudo systemctl status challenger-bot
sudo systemctl status challenger-flask
```

### 7.2 로그 확인

**실시간 로그 보기:**
```bash
# Discord 봇 로그
sudo journalctl -u challenger-bot -f

# Flask 서버 로그
sudo journalctl -u challenger-flask -f
```

**최근 로그 100줄 보기:**
```bash
sudo journalctl -u challenger-bot -n 100 --no-pager
```

**또는 파일 기반 로그:**
```bash
tail -f logs/discord_bot.log
tail -f logs/flask.log
```

### 7.3 웹 대시보드 접속

1. 브라우저에서 다음 URL로 접속:
   ```
   http://YOUR_IP:5001
   ```

2. `.env`에 설정한 `ADMIN_PASSWORD`로 로그인

3. 대시보드에서 다음을 확인:
   - 활성 챌린지 수
   - 등록된 사용자 수
   - 시스템 상태

### 7.4 Discord 봇 테스트

Discord 서버에서 다음 명령어를 실행하여 봇이 응답하는지 확인:

```
!목표설정 테스트
!도움말
!상태
```

봇이 응답하면 배포가 성공적으로 완료되었습니다!

---

## 단계 8: (선택) 자동화 스크립트 사용

위의 단계 3-5를 자동화하려면 `lightsail-setup.sh` 스크립트를 사용할 수 있습니다.

### 8.1 스크립트 실행

```bash
cd /home/ubuntu
git clone <REPOSITORY_URL> challenger-bot-mk2
cd challenger-bot-mk2
chmod +x scripts/lightsail-setup.sh
./scripts/lightsail-setup.sh
```

### 8.2 스크립트가 수행하는 작업

1. 시스템 업데이트
2. 필수 패키지 설치
3. 방화벽 설정
4. 가상환경 생성 및 의존성 설치
5. `.env` 파일 생성 및 편집 안내
6. 환경변수 검증
7. Systemd 서비스 설치 및 시작
8. 배포 상태 확인

스크립트 실행 중 `.env` 파일 편집을 위해 일시 중지됩니다. 필수 환경변수를 입력한 후 계속 진행하세요.

---

## 단계 9: 모니터링 및 유지보수

### 9.1 로그 확인

**실시간 로그 모니터링:**
```bash
sudo journalctl -u challenger-bot -f
```

**특정 기간 로그 확인:**
```bash
sudo journalctl -u challenger-bot --since "1 hour ago"
sudo journalctl -u challenger-bot --since "2024-01-01" --until "2024-01-02"
```

**로그 파일로 저장:**
```bash
sudo journalctl -u challenger-bot -n 1000 > bot_logs.txt
```

### 9.2 서비스 관리

**서비스 재시작:**
```bash
sudo systemctl restart challenger-bot
sudo systemctl restart challenger-flask
```

**서비스 중지:**
```bash
sudo systemctl stop challenger-bot
sudo systemctl stop challenger-flask
```

**서비스 시작:**
```bash
sudo systemctl start challenger-bot
sudo systemctl start challenger-flask
```

**서비스 상태 확인:**
```bash
sudo systemctl status challenger-bot
```

### 9.3 코드 업데이트

Git 저장소에서 최신 코드를 가져와 배포하려면:

```bash
cd /home/ubuntu/challenger-bot-mk2
chmod +x scripts/update-deployment.sh
./scripts/update-deployment.sh
```

**스크립트가 수행하는 작업:**
1. 서비스 중지
2. 데이터베이스 백업
3. Git에서 최신 코드 pull
4. 의존성 업데이트
5. Systemd 서비스 재설치
6. 서비스 재시작
7. 상태 확인

### 9.4 데이터베이스 백업

**수동 백업:**
```bash
cd /home/ubuntu/challenger-bot-mk2
chmod +x scripts/backup-db.sh
./scripts/backup-db.sh
```

**자동 백업 설정 (매일 새벽 2시):**
```bash
crontab -e
```

다음 줄 추가:
```cron
0 2 * * * /home/ubuntu/challenger-bot-mk2/scripts/backup-db.sh >> /home/ubuntu/challenger-bot-mk2/logs/backup.log 2>&1
```

저장 후 종료 (nano: `Ctrl+X` → `Y` → `Enter`)

**백업 파일 확인:**
```bash
ls -lh /home/ubuntu/challenger-bot-mk2/data/backups/
```

### 9.5 Discord 모니터링 알림 설정

봇에는 자동 모니터링 기능이 내장되어 있습니다.

1. Discord 서버에서 모니터링 전용 채널 생성 (예: `#bot-monitoring`)

2. 채널 ID 확인:
   - Discord 개발자 모드 활성화 (설정 → 고급 → 개발자 모드)
   - 채널 우클릭 → "ID 복사"

3. `.env` 파일에 추가:
   ```bash
   nano /home/ubuntu/challenger-bot-mk2/.env
   ```
   ```env
   MONITORING_CHANNEL_ID=1234567890123456789
   ```

4. 봇 재시작:
   ```bash
   sudo systemctl restart challenger-bot
   ```

이제 봇이 크래시하거나 오류가 발생하면 Discord 채널로 알림이 전송됩니다.

### 9.6 리소스 사용량 모니터링

**CPU 및 메모리 사용량 확인:**
```bash
htop
```
또는
```bash
top
```

**디스크 사용량 확인:**
```bash
df -h
```

**특정 프로세스 리소스 확인:**
```bash
ps aux | grep python
```

---

## 단계 10: 문제 해결

### 10.1 Discord 토큰 오류

**증상:**
```
Error: Improper token has been passed
```

**해결 방법:**
1. `.env` 파일에서 `DISCORD_TOKEN` 확인:
   ```bash
   nano /home/ubuntu/challenger-bot-mk2/.env
   ```

2. Discord Developer Portal에서 토큰 재발급 ([부록 A](#부록-a-discord-봇-토큰-발급) 참고)

3. 봇 재시작:
   ```bash
   sudo systemctl restart challenger-bot
   ```

### 10.2 Flask 포트 충돌

**증상:**
```
Error: Address already in use (Port 5001)
```

**해결 방법:**
1. 5001 포트를 사용 중인 프로세스 확인:
   ```bash
   sudo lsof -i :5001
   ```

2. 프로세스 종료:
   ```bash
   sudo systemctl stop challenger-flask
   ```
   또는 특정 PID 종료:
   ```bash
   sudo kill -9 <PID>
   ```

3. 서비스 재시작:
   ```bash
   sudo systemctl start challenger-flask
   ```

### 10.3 메모리 부족 (OOM)

**증상:**
```
Error: Killed (Out of Memory)
```
또는 로그에 `OOMKiller` 메시지

**해결 방법:**

**옵션 1: Lightsail 플랜 업그레이드 (권장)**
- $5/월 → $10/월 플랜으로 업그레이드 (512MB → 1GB RAM)

**옵션 2: Swap 메모리 추가**
```bash
sudo fallocate -l 1G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

Swap 확인:
```bash
free -h
```

### 10.4 권한 문제

**증상:**
```
Error: Permission denied
```

**해결 방법:**
```bash
chmod 600 /home/ubuntu/challenger-bot-mk2/.env
chown -R ubuntu:ubuntu /home/ubuntu/challenger-bot-mk2
```

### 10.5 서비스 시작 실패

**증상:**
```
Job for challenger-bot.service failed
```

**해결 방법:**

1. 상세 로그 확인:
   ```bash
   sudo journalctl -u challenger-bot -n 50 --no-pager
   ```

2. 서비스 파일 검증:
   ```bash
   sudo systemctl cat challenger-bot
   ```

3. 수동으로 실행하여 오류 확인:
   ```bash
   cd /home/ubuntu/challenger-bot-mk2
   source venv/bin/activate
   python src/main.py
   ```

4. 일반적인 원인:
   - 환경변수 미설정 → `.env` 파일 확인
   - 경로 오류 → 서비스 파일의 `WorkingDirectory` 확인
   - Python 의존성 누락 → `pip install -r requirements.txt` 재실행

### 10.6 데이터베이스 오류

**증상:**
```
Error: database is locked
```

**해결 방법:**
1. 봇 재시작:
   ```bash
   sudo systemctl restart challenger-bot
   ```

2. 데이터베이스 파일 권한 확인:
   ```bash
   ls -l /home/ubuntu/challenger-bot-mk2/data/bot.db
   chown ubuntu:ubuntu /home/ubuntu/challenger-bot-mk2/data/bot.db
   ```

### 10.7 Git 업데이트 충돌

**증상:**
```
error: Your local changes to the following files would be overwritten by merge
```

**해결 방법:**
1. 로컬 변경사항 백업:
   ```bash
   git stash save "local_changes_backup"
   ```

2. 최신 코드 pull:
   ```bash
   git pull origin main
   ```

3. 필요시 변경사항 복원:
   ```bash
   git stash pop
   ```

### 10.8 서비스 자동 재시작 안 됨

**증상:**
서버 재부팅 후 봇이 자동으로 시작되지 않음

**해결 방법:**
1. 서비스 활성화 확인:
   ```bash
   sudo systemctl is-enabled challenger-bot
   ```

2. 활성화되지 않았다면:
   ```bash
   sudo systemctl enable challenger-bot
   sudo systemctl enable challenger-flask
   ```

3. 재부팅하여 테스트:
   ```bash
   sudo reboot
   ```

---

## 부록 A: Discord 봇 토큰 발급

### A.1 Discord Developer Portal 접속

1. [Discord Developer Portal](https://discord.com/developers/applications) 접속
2. Discord 계정으로 로그인

### A.2 애플리케이션 생성

1. **"New Application"** 버튼 클릭
2. 봇 이름 입력 (예: `오리와 66일의 약속`)
3. **"Create"** 클릭

### A.3 봇 생성

1. 좌측 메뉴에서 **"Bot"** 선택
2. **"Add Bot"** 클릭 → **"Yes, do it!"** 확인

### A.4 봇 토큰 복사

1. **"Reset Token"** 클릭 (처음이면 "Copy" 버튼만 표시)
2. 토큰 복사 (한 번만 표시되므로 안전한 곳에 저장!)
3. 이 토큰을 `.env` 파일의 `DISCORD_TOKEN`에 입력

> **경고:** 토큰을 절대 공개 저장소에 업로드하지 마세요! 토큰이 노출되면 즉시 "Reset Token"으로 재발급하세요.

### A.5 Privileged Gateway Intents 활성화

봇이 메시지를 읽고 멤버 정보에 접근하려면 다음 권한이 필요합니다:

1. 봇 설정 페이지에서 아래로 스크롤
2. **Privileged Gateway Intents** 섹션에서 다음 활성화:
   - ✅ **PRESENCE INTENT**
   - ✅ **SERVER MEMBERS INTENT**
   - ✅ **MESSAGE CONTENT INTENT**
3. **"Save Changes"** 클릭

### A.6 봇 초대 URL 생성

1. 좌측 메뉴에서 **"OAuth2"** → **"URL Generator"** 선택

2. **Scopes** 섹션에서 선택:
   - ✅ `bot`
   - ✅ `applications.commands`

3. **Bot Permissions** 섹션에서 선택:
   - **권장:** `Administrator` (모든 권한)
   - **또는 최소 권한:**
     - ✅ Read Messages/View Channels
     - ✅ Send Messages
     - ✅ Manage Messages
     - ✅ Embed Links
     - ✅ Read Message History
     - ✅ Add Reactions
     - ✅ Use Slash Commands

4. 하단의 **Generated URL** 복사

5. 브라우저에서 URL 열기 → 봇을 초대할 Discord 서버 선택 → **"승인"** 클릭

### A.7 봇 초대 확인

Discord 서버의 멤버 목록에서 봇이 표시되는지 확인하세요.

---

## 부록 B: 비용 분석

### B.1 Lightsail 인스턴스 비용

#### $5/월 플랜 (최소 사양)
- **월 비용:** $5 USD
- **연 비용:** $60 USD
- **사양:**
  - 512MB RAM
  - 1 vCPU
  - 20GB SSD 스토리지
  - 1TB 데이터 전송 포함
- **적합성:** 테스트 및 소규모 서버 (20-50명)

#### $10/월 플랜 (권장)
- **월 비용:** $10 USD
- **연 비용:** $120 USD
- **사양:**
  - 1GB RAM
  - 1 vCPU
  - 40GB SSD 스토리지
  - 2TB 데이터 전송 포함
- **적합성:** 안정적인 운영, 중소형 서버 (100-500명)

#### $20/월 플랜 (대형 서버)
- **월 비용:** $20 USD
- **연 비용:** $240 USD
- **사양:**
  - 2GB RAM
  - 1 vCPU
  - 60GB SSD 스토리지
  - 3TB 데이터 전송 포함
- **적합성:** 대형 서버 (500+ 명) 또는 여러 봇 운영

### B.2 추가 비용

#### 고정 IP
- **비용:** 무료 (인스턴스에 연결된 경우)
- 인스턴스에 연결되지 않은 채로 방치하면 월 $0.005/시간 ($3.60/월)

#### 스냅샷 백업
- **비용:** $0.05/GB/월
- 예: 5GB 스냅샷 = $0.25/월

#### 데이터 전송 초과
- 플랜에 포함된 전송량 초과 시 추가 비용 발생
- $5 플랜: 1TB 초과 시 $0.09/GB
- 일반적으로 Discord 봇은 데이터 전송량이 적어 초과 가능성 낮음

### B.3 총 예상 비용

#### 일반적인 사용 사례 (권장 $10 플랜)
- **Lightsail 인스턴스:** $10/월
- **고정 IP:** $0 (인스턴스에 연결)
- **스냅샷 백업 (선택):** ~$0.50/월 (월 1회 백업 가정)
- **총 비용:** 약 $10-11/월 (연 $120-132)

#### 최소 사용 사례 ($5 플랜)
- **Lightsail 인스턴스:** $5/월
- **고정 IP:** $0
- **스냅샷 백업:** $0 (사용 안 함)
- **총 비용:** $5/월 (연 $60)

### B.4 비용 절감 팁

1. **무료 티어 활용:**
   - AWS 신규 계정은 처음 12개월간 일부 서비스 무료 (Lightsail은 제외)

2. **스냅샷 대신 Git + 데이터베이스 백업:**
   - 스냅샷 비용 절약
   - 제공된 `backup-db.sh` 스크립트 활용

3. **불필요한 고정 IP 삭제:**
   - 사용하지 않는 고정 IP는 즉시 삭제

4. **리소스 모니터링:**
   - 사용하지 않는 인스턴스는 중지 또는 삭제

5. **연간 결제 (일부 서비스):**
   - Lightsail은 월 단위 결제만 지원

### B.5 대안 비교

| 서비스 | 월 비용 | 장점 | 단점 |
|--------|---------|------|------|
| **AWS Lightsail** | $5-10 | 간단한 설정, 고정 가격 | AWS 계정 필요 |
| **DigitalOcean** | $6-12 | 유사한 사양, 간단한 UI | 미국 기반 (지연 가능) |
| **Vultr** | $5-10 | 서울 리전 있음 | Lightsail보다 복잡 |
| **Heroku** | $7 (Eco) | 배포 매우 간단 | 월 1000시간 제한 |
| **Oracle Cloud** | 무료 | 평생 무료 티어 | 복잡한 설정, 계정 제한 가능 |
| **Google Cloud** | $5-15 | 강력한 인프라 | 복잡한 UI |

### B.6 비용 알림 설정

과금 방지를 위해 AWS 예산 알림을 설정하세요:

1. [AWS Budgets](https://console.aws.amazon.com/billing/home#/budgets) 접속
2. **"Create budget"** 클릭
3. 예산 유형: "Cost budget"
4. 월 예산 설정 (예: $15)
5. 알림 이메일 설정
6. 80%, 100% 초과 시 알림 받도록 설정

---

## 🎉 축하합니다!

Discord 챗봇을 AWS Lightsail에 성공적으로 배포했습니다!

### 다음 단계:

1. **Discord 서버에서 봇 테스트**
   - `!목표설정`, `!도움말` 등의 명령어 실행

2. **웹 대시보드 활용**
   - `http://YOUR_IP:5001`에서 통계 확인

3. **자동 백업 설정**
   - Cron으로 매일 백업 자동화

4. **모니터링 채널 설정**
   - Discord 채널로 오류 알림 받기

5. **정기적인 업데이트**
   - `./scripts/update-deployment.sh`로 최신 코드 반영

---

## 📚 추가 리소스

- [AWS Lightsail 공식 문서](https://lightsail.aws.amazon.com/ls/docs/en_us/articles/amazon-lightsail-quick-start-guide)
- [Discord.py 공식 문서](https://discordpy.readthedocs.io/)
- [Ubuntu 서버 관리 가이드](https://ubuntu.com/server/docs)
- [Systemd 서비스 관리](https://www.freedesktop.org/software/systemd/man/systemctl.html)

---

## 🆘 도움이 필요하신가요?

문제가 발생하면:
1. [문제 해결](#단계-10-문제-해결) 섹션 확인
2. 로그 확인: `sudo journalctl -u challenger-bot -n 100`
3. GitHub Issues에 질문 등록
4. Discord 서버에서 커뮤니티에 질문

---

**제작:** 오리와 66일의 약속 팀
**문서 버전:** 1.0.0
**마지막 업데이트:** 2024-01-15
