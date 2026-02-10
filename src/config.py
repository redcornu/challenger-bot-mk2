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

# Flask 서버 설정
FLASK_HOST = os.getenv('FLASK_HOST', '0.0.0.0')
FLASK_PORT = int(os.getenv('FLASK_PORT', '5001'))

# 봇 설정
DEBUG_MODE = os.getenv('DEBUG_MODE', 'False').lower() == 'true'
COMMAND_PREFIX = '!'
MESSAGE_DELETE_AFTER = 600  # 10분

# 상수 정의
class BotStates:
    """봇의 상태 상수"""
    EGG = "EGG"
    DUCKLING = "DUCKLING"
    ADOLESCENT = "ADOLESCENT"
    ADULT = "ADULT"
    SULKY = "SULKY"
    RUNAWAY = "RUNAWAY"
    DONE = "DONE"

# 한글 번역
STATE_KOREAN = {
    BotStates.EGG: "오리알",
    BotStates.DUCKLING: "병아리 오리",
    BotStates.ADOLESCENT: "사춘기 오리",
    BotStates.ADULT: "어른 오리",
    BotStates.SULKY: "삐진",
    BotStates.RUNAWAY: "가출",
    BotStates.DONE: "졸업"
}

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
