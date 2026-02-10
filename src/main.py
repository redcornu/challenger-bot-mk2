import discord
from discord.ext import commands
import logging
import os
import atexit
from config import DISCORD_TOKEN, COMMAND_PREFIX
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()
from database import init_db
from hooks import flask_lifecycle

# 로그 디렉토리 생성
os.makedirs('logs', exist_ok=True)

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
    
    # Flask 서버 자동 시작 (Hook)
    flask_lifecycle.on_bot_start()
    
    # Flask 서버 모니터링 Agent 시작 (선택 사항)
    monitoring_channel_id = os.getenv('MONITORING_CHANNEL_ID')
    if monitoring_channel_id and monitoring_channel_id != '0':
        try:
            monitoring_channel_id = int(monitoring_channel_id)
            if monitoring_channel_id > 0:
                from agents.dashboard_admin import DashboardAdminAgent

                dashboard_agent = DashboardAdminAgent(bot, monitoring_channel_id)
                await dashboard_agent.start_monitoring()
                logger.info(f'Flask 모니터링 Agent 시작됨 (채널 ID: {monitoring_channel_id})')
            else:
                logger.info('Flask 모니터링이 비활성화되어 있습니다.')
        except ValueError:
            logger.warning(f'잘못된 MONITORING_CHANNEL_ID: {monitoring_channel_id}')
        except Exception as e:
            logger.error(f'모니터링 Agent 시작 실패: {e}', exc_info=True)
    else:
        logger.info('Flask 모니터링이 비활성화되어 있습니다 (MONITORING_CHANNEL_ID=0).')

    # Cogs 로드
    initial_extensions = [
        'cogs.challenge',
        'cogs.shop',
        'cogs.ranking',
        'skills.flask_admin',  # Flask 서버 관리 Skill
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
    # 봇 종료 시 Flask 서버도 종료 (Hook)
    atexit.register(flask_lifecycle.on_bot_stop)
    
    try:
        bot.run(DISCORD_TOKEN)
    except Exception as e:
        logger.critical(f'봇 실행 실패: {e}', exc_info=True)
