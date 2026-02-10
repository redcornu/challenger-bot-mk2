 디스코드 봇 프로젝트 생성 워크플로우 가이드                                                                                                                                                                                        
                                                 
 Context (배경)                                              
                                                         
 현재 Challenger-bot 프로젝트 분석 결과, 다음과 같은 문제점들이 발견되었습니다:
 - 보안: .env 파일이 Git에 노출되어 토큰 유출
 - 코드 중복: delete_after=600 31회 반복, DB 연결 패턴 21회 반복
 - 잠재적 버그: timezone 처리 불완전, JSON 파싱 예외 처리 없음, 중복 commit
 - 리소스 관리: 5개 이미지 누락, venv 디렉토리가 Git에 포함됨
 - 유지보수성: 642줄의 모놀리식 main.py, 하드코딩된 상수들

 이러한 문제들을 처음부터 방지하고, 확장 가능하고 안전한 디스코드 봇을 만들기 위한 체계적인 워크플로우를 제시합니다.

 ---
 디스코드 봇 프로젝트 생성 워크플로우

 Phase 1: 프로젝트 기획 및 초기 설정 (Day 1)

 Step 1.1: 프로젝트 요구사항 정의

 # 프로젝트 기획서 작성 (SPEC.md)

 ## 1. 봇의 목적
 - 주요 기능 1
 - 주요 기능 2
 - 타겟 사용자

 ## 2. 핵심 기능 명세
 | 명령어 | 기능 | 필수 여부 |
 |--------|------|----------|
 | !명령1 | 설명 | 필수 |
 | !명령2 | 설명 | 선택 |

 ## 3. 데이터 구조
 - 필요한 테이블/컬렉션
 - 관계도

 ## 4. 제약사항
 - 성능 요구사항
 - 보안 요구사항

 Step 1.2: 프로젝트 구조 생성

 # 1. 프로젝트 디렉토리 생성
 mkdir discord-bot-project
 cd discord-bot-project

 # 2. Git 초기화 (중요: 코드 작성 전에 먼저!)
 git init

 # 3. .gitignore 생성 (가장 먼저!)
 cat > .gitignore << 'EOF'
 # Python
 __pycache__/
 *.pyc
 *.pyo
 *.pyd
 .Python
 *.so
 *.egg
 *.egg-info/
 dist/
 build/

 # Virtual Environment
 venv/
 env/
 ENV/
 .venv/

 # Environment Variables (중요!)
 .env
 .env.local
 .env.*.local
 *.env

 # Database
 *.db
 *.sqlite
 *.sqlite3

 # IDE
 .vscode/
 .idea/
 *.swp
 *.swo
 .DS_Store

 # Logs
 *.log
 nohup.out
 logs/

 # Backups
 *백업*
 *.backup
 *.bak

 # Test files
 test_*.py
 debug_*.py
 EOF

 # 4. 가상환경 생성
 python3 -m venv venv
 source venv/bin/activate  # Windows: venv\Scripts\activate

 # 5. 기본 디렉토리 구조 생성
 mkdir -p src/{cogs,utils,models}
 mkdir -p assets
 mkdir -p tests
 mkdir -p docs

 권장 디렉토리 구조:
 discord-bot-project/
 ├── src/
 │   ├── main.py              # 봇 엔트리 포인트
 │   ├── config.py            # 설정 및 상수
 │   ├── database.py          # DB 레이어
 │   ├── cogs/                # 명령어 그룹 (Cogs)
 │   │   ├── __init__.py
 │   │   ├── challenge.py     # 도전 관련 명령어
 │   │   └── shop.py          # 상점 관련 명령어
 │   ├── utils/               # 헬퍼 함수들
 │   │   ├── __init__.py
 │   │   ├── embed_builder.py
 │   │   └── validators.py
 │   └── models/              # 데이터 모델
 │       ├── __init__.py
 │       └── user.py
 ├── assets/                  # 이미지, 리소스
 ├── tests/                   # 유닛 테스트
 │   ├── test_database.py
 │   └── test_commands.py
 ├── docs/                    # 문서
 │   ├── SPEC.md
 │   └── API.md
 ├── .env.example             # 환경변수 템플릿
 ├── .gitignore
 ├── requirements.txt
 ├── README.md
 └── Dockerfile (선택)

 Step 1.3: 환경변수 템플릿 생성

 # .env.example 생성 (Git에 포함)
 cat > .env.example << 'EOF'
 # Discord Bot Token (https://discord.com/developers/applications)
 DISCORD_TOKEN=your_token_here

 # Admin Password (Dashboard)
 ADMIN_PASSWORD=your_secure_password_here

 # Database
 DB_PATH=data/bot.db

 # Optional: Debug Mode
 DEBUG_MODE=False
 EOF

 # 실제 .env 파일은 사용자가 직접 생성하도록 README에 안내

 ---
 Phase 2: 핵심 아키텍처 구현 (Day 2-3)

 Step 2.1: config.py - 중앙 집중식 설정 관리

 # src/config.py
 import os
 from dotenv import load_dotenv

 # 환경변수 로드
 load_dotenv()

 # Discord 설정
 DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
 if not DISCORD_TOKEN:
     raise ValueError("🚨 DISCORD_TOKEN이 설정되지 않았습니다. .env 파일을 확인하세요.")

 # 데이터베이스 설정
 DB_PATH = os.getenv('DB_PATH', 'data/bot.db')

 # 봇 설정
 DEBUG_MODE = os.getenv('DEBUG_MODE', 'False').lower() == 'true'
 COMMAND_PREFIX = '!'
 MESSAGE_DELETE_AFTER = 600  # 10분

 # 상수 정의 (하드코딩 방지)
 class BotStates:
     """봇의 상태 상수"""
     EGG = "EGG"
     DUCKLING = "DUCKLING"
     ADOLESCENT = "ADOLESCENT"
     ADULT = "ADULT"
     SULKY = "SULKY"
     RUNAWAY = "RUNAWAY"
     DONE = "DONE"

 class BotConfig:
     """게임 설정"""
     HATCH_DAYS = 7
     ADOLESCENT_DAYS = 22
     ADULT_DAYS = 43
     GRADUATION_DAYS = 66

     SULKY_RECOVERY_DAYS = 3
     RUNAWAY_RECOVERY_DAYS = 7

     DAILY_GOLD_REWARD = 1

 # 이미지 경로 맵핑
 IMAGE_PATHS = {
     BotStates.EGG: "assets/egg.png",
     BotStates.DUCKLING: "assets/duck_duckling.png",
     BotStates.ADOLESCENT: "assets/duck_adolescent.png",
     BotStates.ADULT: "assets/duck_adult.png",
     BotStates.SULKY: "assets/duck_sulky.png",
     BotStates.RUNAWAY: "assets/runaway.png",
     BotStates.DONE: "assets/final.png",
 }

 # 색상 코드
 EMBED_COLORS = {
     'success': 0x00FF00,
     'error': 0xFF0000,
     'info': 0x3498DB,
     'warning': 0xFFAA00,
     'gold': 0xFFD700,
 }

 Step 2.2: database.py - Context Manager 패턴

 # src/database.py
 import sqlite3
 import json
 from contextlib import contextmanager
 from typing import Optional, Dict, List
 from config import DB_PATH

 @contextmanager
 def get_db_connection():
     """데이터베이스 연결 컨텍스트 매니저 - 자동 commit/close"""
     conn = sqlite3.connect(DB_PATH)
     conn.row_factory = sqlite3.Row
     try:
         yield conn
         conn.commit()
     except Exception as e:
         conn.rollback()
         raise e
     finally:
         conn.close()

 def init_db():
     """테이블 초기화"""
     with get_db_connection() as conn:
         c = conn.cursor()

         # 도전 테이블
         c.execute('''
             CREATE TABLE IF NOT EXISTS duck_challenge (
                 thread_id INTEGER PRIMARY KEY,
                 user_id INTEGER NOT NULL,
                 goal_text TEXT NOT NULL,
                 state TEXT NOT NULL,
                 streak INTEGER DEFAULT 0,
                 growth_days INTEGER DEFAULT 0,
                 total_days INTEGER DEFAULT 0,
                 last_auth_date TEXT,
                 created_at TEXT DEFAULT CURRENT_TIMESTAMP
             )
         ''')

         # 유저 테이블
         c.execute('''
             CREATE TABLE IF NOT EXISTS users (
                 user_id INTEGER PRIMARY KEY,
                 username TEXT,
                 ducks_raised INTEGER DEFAULT 0,
                 gold INTEGER DEFAULT 0,
                 inventory TEXT DEFAULT '{}',
                 created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                 updated_at TEXT DEFAULT CURRENT_TIMESTAMP
             )
         ''')

         # 시스템 설정 테이블
         c.execute('''
             CREATE TABLE IF NOT EXISTS system_config (
                 key TEXT PRIMARY KEY,
                 value TEXT
             )
         ''')

         # 인덱스 생성 (성능 최적화)
         c.execute('CREATE INDEX IF NOT EXISTS idx_user_id ON duck_challenge(user_id)')
         c.execute('CREATE INDEX IF NOT EXISTS idx_state ON duck_challenge(state)')

 def get_challenge(thread_id: int) -> Optional[Dict]:
     """도전 정보 조회"""
     with get_db_connection() as conn:
         c = conn.cursor()
         c.execute("SELECT * FROM duck_challenge WHERE thread_id = ?", (thread_id,))
         row = c.fetchone()
         return dict(row) if row else None

 def create_challenge(thread_id: int, user_id: int, goal_text: str) -> bool:
     """새로운 도전 생성"""
     try:
         with get_db_connection() as conn:
             c = conn.cursor()
             c.execute('''
                 INSERT INTO duck_challenge (thread_id, user_id, goal_text, state, streak, growth_days, total_days)
                 VALUES (?, ?, ?, 'EGG', 0, 0, 0)
             ''', (thread_id, user_id, goal_text))
             return True
     except sqlite3.IntegrityError:
         return False  # 이미 존재하는 도전

 # ... 나머지 DB 함수들

 Step 2.3: utils/validators.py - 검증 로직 분리

 # src/utils/validators.py
 import json
 from datetime import datetime
 from zoneinfo import ZoneInfo
 from typing import Dict, Optional

 def get_kst_now() -> datetime:
     """한국 시간 반환 (timezone-aware)"""
     return datetime.now(ZoneInfo("Asia/Seoul"))

 def safe_json_loads(json_str: str, default: Optional[Dict] = None) -> Dict:
     """안전한 JSON 파싱 - 실패 시 기본값 반환"""
     try:
         return json.loads(json_str)
     except (json.JSONDecodeError, TypeError):
         return default if default is not None else {}

 def safe_json_dumps(data: Dict) -> str:
     """안전한 JSON 직렬화"""
     try:
         return json.dumps(data, ensure_ascii=False)
     except (TypeError, ValueError):
         return '{}'

 def validate_image_exists(image_path: str) -> bool:
     """이미지 파일 존재 확인"""
     import os
     return os.path.exists(image_path)

 Step 2.4: utils/embed_builder.py - Embed 생성 로직 통합

 # src/utils/embed_builder.py
 import discord
 from typing import List, Dict, Optional
 from config import EMBED_COLORS

 class EmbedBuilder:
     """Discord Embed 빌더 - 일관된 스타일 제공"""

     @staticmethod
     def success(title: str, description: str, **kwargs) -> discord.Embed:
         """성공 메시지 Embed"""
         return discord.Embed(
             title=f"✅ {title}",
             description=description,
             color=EMBED_COLORS['success'],
             **kwargs
         )

     @staticmethod
     def error(title: str, description: str, **kwargs) -> discord.Embed:
         """에러 메시지 Embed"""
         return discord.Embed(
             title=f"❌ {title}",
             description=description,
             color=EMBED_COLORS['error'],
             **kwargs
         )

     @staticmethod
     def info(title: str, description: str, **kwargs) -> discord.Embed:
         """정보 메시지 Embed"""
         return discord.Embed(
             title=f"ℹ️ {title}",
             description=description,
             color=EMBED_COLORS['info'],
             **kwargs
         )

     @staticmethod
     def ranking(top_users: List[Dict], timestamp: str) -> discord.Embed:
         """랭킹 Embed 생성 - 중복 제거"""
         embed = discord.Embed(
             title="🏆 도전에 진심인 편 - 명예의 전당 (Top 10)",
             description=f"마지막 갱신: {timestamp}",
             color=EMBED_COLORS['gold']
         )

         if top_users:
             rank_text = ""
             for i, user in enumerate(top_users):
                 medal = "🥇" if i == 0 else "🥈" if i == 1 else "🥉" if i == 2 else f"{i+1}."
                 username = user['username'] if user['username'] else f"User {user['user_id']}"
                 growth = user.get('current_growth', 0)
                 growth_text = f" | 🌱 `D+{growth}`" if growth > 0 else " | 🥚 `도전 전`"

                 rank_text += f"{medal} **{username}**\n"
                 rank_text += f"└ 🎓 졸업: `{user['ducks_raised']}마리`{growth_text} | 💰 `{user['gold']}G`\n\n"

             embed.add_field(name="🏆 명예의 전당", value=rank_text, inline=False)
         else:
             embed.description = "아직 랭킹 데이터가 없습니다."

         return embed

 ---
 Phase 3: Cogs 패턴으로 명령어 분리 (Day 4-5)

 Step 3.1: Cog 구조 이해

 # src/cogs/challenge.py
 import discord
 from discord.ext import commands
 from config import BotStates, BotConfig, MESSAGE_DELETE_AFTER
 from database import get_challenge, create_challenge, update_challenge
 from utils.validators import get_kst_now
 from utils.embed_builder import EmbedBuilder

 class ChallengeCog(commands.Cog):
     """도전 관련 명령어 그룹"""

     def __init__(self, bot):
         self.bot = bot

     @commands.command(name='목표설정')
     async def set_goal(self, ctx, *, goal: str):
         """새로운 도전 시작"""
         # 스레드 검증
         if not isinstance(ctx.channel, discord.Thread):
             embed = EmbedBuilder.error(
                 "오류",
                 "이 명령어는 포럼 스레드에서만 사용 가능합니다."
             )
             await ctx.send(embed=embed, delete_after=MESSAGE_DELETE_AFTER)
             return

         # 기존 도전 확인
         existing = get_challenge(ctx.channel.id)
         if existing:
             embed = EmbedBuilder.error(
                 "이미 진행 중",
                 "이미 도전이 진행 중입니다."
             )
             await ctx.send(embed=embed, delete_after=MESSAGE_DELETE_AFTER)
             return

         # 도전 생성
         success = create_challenge(ctx.channel.id, ctx.author.id, goal)
         if success:
             embed = EmbedBuilder.success(
                 "도전 시작!",
                 f"목표: {goal}\n매일 인증하여 오리를 키워주세요!"
             )
             await ctx.send(embed=embed, delete_after=MESSAGE_DELETE_AFTER)
         else:
             embed = EmbedBuilder.error("생성 실패", "도전 생성 중 오류 발생")
             await ctx.send(embed=embed, delete_after=MESSAGE_DELETE_AFTER)

     @commands.command(name='인증')
     async def authenticate(self, ctx):
         """일일 인증 (사진 필수)"""
         # 사진 첨부 확인
         if not ctx.message.attachments:
             embed = EmbedBuilder.error(
                 "사진 필요",
                 "인증샷을 함께 첨부해주세요!"
             )
             await ctx.send(embed=embed, delete_after=MESSAGE_DELETE_AFTER)
             return

         # 도전 조회
         challenge = get_challenge(ctx.channel.id)
         if not challenge:
             embed = EmbedBuilder.error(
                 "도전 없음",
                 "먼저 !목표설정으로 도전을 시작하세요."
             )
             await ctx.send(embed=embed, delete_after=MESSAGE_DELETE_AFTER)
             return

         # 소유권 확인
         if not await self._check_ownership(ctx, challenge):
             return

         # 인증 처리 로직...
         # (여기에 실제 인증 로직 구현)

         embed = EmbedBuilder.success(
             "인증 완료!",
             f"연속 {challenge['streak'] + 1}일째 인증 중입니다!"
         )
         await ctx.send(embed=embed, delete_after=MESSAGE_DELETE_AFTER)

     async def _check_ownership(self, ctx, challenge) -> bool:
         """소유권 확인 헬퍼"""
         thread_owner = ctx.channel.owner_id
         if ctx.author.id != thread_owner:
             embed = EmbedBuilder.error(
                 "권한 없음",
                 "이 도전의 주인만 인증할 수 있습니다."
             )
             await ctx.send(embed=embed, delete_after=MESSAGE_DELETE_AFTER)
             return False
         return True

 # Cog 로드 함수 (main.py에서 호출)
 async def setup(bot):
     await bot.add_cog(ChallengeCog(bot))

 Step 3.2: main.py - 봇 엔트리 포인트

 # src/main.py
 import discord
 from discord.ext import commands
 import asyncio
 import logging
 from config import DISCORD_TOKEN, COMMAND_PREFIX
 from database import init_db

 # 로깅 설정
 logging.basicConfig(
     level=logging.INFO,
     format='%(asctime)s [%(levelname)s] %(message)s',
     handlers=[
         logging.FileHandler('logs/bot.log'),
         logging.StreamHandler()
     ]
 )
 logger = logging.getLogger(__name__)

 # Intents 설정
 intents = discord.Intents.default()
 intents.message_content = True
 intents.guilds = True

 # 봇 초기화
 bot = commands.Bot(command_prefix=COMMAND_PREFIX, intents=intents)

 @bot.event
 async def on_ready():
     """봇 시작 시 실행"""
     logger.info(f'{bot.user} 봇이 시작되었습니다.')

     # 데이터베이스 초기화
     init_db()
     logger.info('데이터베이스 초기화 완료')

     # Cogs 로드
     initial_extensions = [
         'cogs.challenge',
         'cogs.shop',
         'cogs.ranking',
     ]

     for extension in initial_extensions:
         try:
             await bot.load_extension(extension)
             logger.info(f'Cog 로드 완료: {extension}')
         except Exception as e:
             logger.error(f'Cog 로드 실패: {extension} - {e}')

 @bot.event
 async def on_command_error(ctx, error):
     """전역 에러 핸들러"""
     if isinstance(error, commands.CommandNotFound):
         return  # 무시
     elif isinstance(error, commands.MissingRequiredArgument):
         await ctx.send(f"❌ 필수 인자가 누락되었습니다: `{error.param.name}`", delete_after=10)
     else:
         logger.error(f'에러 발생: {error}', exc_info=True)
         await ctx.send("❌ 명령어 실행 중 오류가 발생했습니다.", delete_after=10)

 if __name__ == '__main__':
     try:
         bot.run(DISCORD_TOKEN)
     except Exception as e:
         logger.critical(f'봇 실행 실패: {e}', exc_info=True)

 ---
 Phase 4: 테스트 및 검증 (Day 6)

 Step 4.1: 유닛 테스트 작성

 # tests/test_database.py
 import unittest
 import os
 from src.database import init_db, create_challenge, get_challenge

 class TestDatabase(unittest.TestCase):

     @classmethod
     def setUpClass(cls):
         """테스트용 DB 생성"""
         os.environ['DB_PATH'] = 'test.db'
         init_db()

     @classmethod
     def tearDownClass(cls):
         """테스트용 DB 삭제"""
         if os.path.exists('test.db'):
             os.remove('test.db')

     def test_create_challenge(self):
         """도전 생성 테스트"""
         success = create_challenge(12345, 67890, "Test Goal")
         self.assertTrue(success)

         challenge = get_challenge(12345)
         self.assertIsNotNone(challenge)
         self.assertEqual(challenge['goal_text'], "Test Goal")
         self.assertEqual(challenge['state'], "EGG")

     def test_duplicate_challenge(self):
         """중복 도전 방지 테스트"""
         create_challenge(99999, 11111, "First")
         success = create_challenge(99999, 11111, "Second")
         self.assertFalse(success)  # 실패해야 함

 if __name__ == '__main__':
     unittest.main()

 Step 4.2: 통합 테스트 체크리스트

 # 테스트 체크리스트

 ## 기본 기능
 - [ ] 봇이 정상적으로 시작됨
 - [ ] !목표설정으로 도전 생성
 - [ ] !인증으로 일일 인증 (사진 첨부)
 - [ ] !상태로 현재 상태 확인
 - [ ] !상점 / !구매 / !인벤토리

 ## 권한 시스템
 - [ ] 스레드 소유자만 인증 가능
 - [ ] 타인의 스레드에서 명령어 실행 시 거부

 ## 페널티 시스템
 - [ ] 1일 건너뛰면 SULKY 상태
 - [ ] SULKY에서 또 건너뛰면 RUNAWAY
 - [ ] 아이템으로 복구 가능

 ## 보안
 - [ ] .env 파일이 Git에 없음
 - [ ] 환경변수 없이 실행 시 명확한 에러
 - [ ] 토큰이 로그에 출력되지 않음

 ## 성능
 - [ ] 100명 동시 인증 시 문제 없음
 - [ ] 랭킹 보드 갱신이 1초 이내

 ---
 Phase 5: 배포 및 문서화 (Day 7)

 Step 5.1: requirements.txt 작성 (버전 고정)

 discord.py==2.3.2
 python-dotenv==1.0.0
 streamlit==1.31.0  # dashboard용
 pandas==2.2.0      # dashboard용

 Step 5.2: README.md 작성

 # Discord Bot - 오리와 66일의 약속

 습관 형성을 위한 타마고치 스타일 Discord 봇

 ## 기능
 - 66일 습관 형성 챌린지
 - 오리 육성 시뮬레이션
 - 랭킹 시스템
 - 상점 및 아이템

 ## 설치 방법

 ### 1. 프로젝트 클론
 ```bash
 git clone https://github.com/username/discord-bot.git
 cd discord-bot

 2. 가상환경 생성 및 의존성 설치

 python3 -m venv venv
 source venv/bin/activate
 pip install -r requirements.txt

 3. 환경변수 설정

 cp .env.example .env
 # .env 파일을 열어서 Discord 토큰 입력

 4. 봇 실행

 python src/main.py

 명령어
 ┌──────────────────┬───────────────────────┐
 │      명령어      │         기능          │
 ├──────────────────┼───────────────────────┤
 │ !목표설정 [목표] │ 새로운 도전 시작      │
 ├──────────────────┼───────────────────────┤
 │ !인증            │ 일일 인증 (사진 필수) │
 ├──────────────────┼───────────────────────┤
 │ !상태            │ 현재 오리 상태 확인   │
 ├──────────────────┼───────────────────────┤
 │ !상점            │ 아이템 목록           │
 ├──────────────────┼───────────────────────┤
 │ !구매 [아이템]   │ 아이템 구매           │
 └──────────────────┴───────────────────────┘
 라이선스

 MIT

 #### Step 5.3: Dockerfile 작성 (선택)
 ```dockerfile
 FROM python:3.11-slim

 WORKDIR /app

 # 의존성 설치
 COPY requirements.txt .
 RUN pip install --no-cache-dir -r requirements.txt

 # 소스 복사
 COPY src/ ./src/
 COPY assets/ ./assets/

 # 데이터 디렉토리 생성
 RUN mkdir -p data logs

 # 봇 실행
 CMD ["python", "src/main.py"]

 ---
 핵심 원칙 요약

 ✅ DO (해야 할 것)

 1. 보안 우선
   - 프로젝트 시작 시 즉시 .gitignore 생성
   - .env.example 제공, 실제 .env는 Git에 포함 금지
   - 환경변수 없으면 명확한 에러 출력
 2. 코드 중복 제거
   - 상수는 config.py에 중앙 집중
   - 반복되는 로직은 함수/클래스로 분리
   - DB 연결은 Context Manager 사용
 3. 모듈화
   - Cogs 패턴으로 명령어 그룹화
   - utils/models 디렉토리로 로직 분리
   - 각 파일은 단일 책임 원칙 준수
 4. 에러 처리
   - JSON 파싱은 safe_json_loads 사용
   - DB 작업은 try-except로 감싸기
   - 사용자에게 명확한 에러 메시지 제공
 5. 타임존 처리
   - zoneinfo 사용 (timezone-aware)
   - datetime.utcnow() 사용 금지
 6. 테스트
   - 핵심 로직에 유닛 테스트 작성
   - 배포 전 통합 테스트 실행
 7. 문서화
   - README.md에 설치/실행 방법 명시
   - SPEC.md에 기능 명세 작성
   - 코드 주석은 "왜"를 설명

 ❌ DON'T (하지 말아야 할 것)

 1. 절대 하지 말 것
   - .env 파일을 Git에 커밋
   - 토큰/비밀번호 하드코딩
   - venv/ 디렉토리를 Git에 포함
 2. 코드 품질
   - 동일한 코드를 3번 이상 반복
   - 하드코딩된 숫자/문자열 남발
   - 600줄 이상의 단일 파일
 3. 에러 처리
   - 예외를 무시 (except: pass)
   - 사용자에게 스택 트레이스 노출
   - 의미 없는 에러 메시지 ("에러 발생")
 4. 데이터베이스
   - conn.close() 누락
   - SQL Injection 취약점 (raw SQL)
   - 트랜잭션 없이 다중 쿼리

 ---
 체크리스트: 프로젝트 생성 시 확인사항

 초기 설정

 - .gitignore 생성 (가장 먼저!)
 - .env.example 생성, .env는 제외
 - 디렉토리 구조 생성 (src/cogs/utils/tests)
 - requirements.txt 버전 고정

 코드 작성

 - config.py에 모든 상수 정의
 - database.py에 Context Manager 도입
 - Cogs 패턴으로 명령어 분리
 - utils/ 디렉토리로 헬퍼 함수 분리
 - 에러 핸들러 추가 (on_command_error)

 보안

 - 환경변수 필수 체크 로직
 - 토큰이 로그에 출력되지 않음
 - 권한 검증 로직 (소유권 확인)

 테스트

 - 유닛 테스트 작성 (최소 DB 레이어)
 - 통합 테스트 체크리스트 작성
 - 배포 전 전체 명령어 테스트

 문서화

 - README.md (설치/실행 방법)
 - SPEC.md (기능 명세)
 - 주요 함수에 Docstring

 배포

 - restart.sh에 가상환경 활성화
 - 로그 파일 로테이션 설정
 - Dockerfile 작성 (선택)

 ---
 이 워크플로우를 Claude에게 요청하는 방법

 새로운 디스코드 봇 프로젝트를 시작할 때 다음과 같이 요청하세요:

 디스코드 봇 프로젝트를 생성해주세요.

 **프로젝트 정보:**
 - 봇 이름: [봇 이름]
 - 주요 기능: [기능 1, 기능 2, ...]
 - 데이터: [필요한 데이터 구조]

 **요구사항:**
 - 위 워크플로우 가이드를 따라 프로젝트 생성
 - Cogs 패턴으로 명령어 분리
 - 보안 베스트 프랙티스 준수 (.gitignore, .env.example)
 - Context Manager로 DB 연결 관리
 - 유닛 테스트 포함
 - README.md 및 문서 작성

 **우선순위:**
 1. 보안 설정 (Phase 1)
 2. 핵심 아키텍처 (Phase 2-3)
 3. 테스트 및 문서화 (Phase 4-5)

 ---
 참고 자료

 핵심 파일 예시:
 - /Users/mac/Documents/자료/요진편/Challenger/Challenger-bot/main.py - 개선 전 (642줄 모놀리식)
 - 개선 후: src/cogs/challenge.py + src/config.py + src/utils/ 로 분리

 주요 라이브러리:
 - discord.py 2.3+ - Discord 봇 프레임워크
 - python-dotenv - 환경변수 관리
 - zoneinfo - Timezone 처리 (Python 3.9+)
 - streamlit - 관리자 대시보드 (선택)

 추천 리소스:
 - Discord.py 공식 문서: https://discordpy.readthedocs.io/
 - Cogs 튜토리얼: https://discordpy.readthedocs.io/en/stable/ext/commands/cogs.html