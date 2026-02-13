import discord
from discord.ext import commands
import logging
import os
import atexit
from config import DISCORD_TOKEN, COMMAND_PREFIX, MANAGE_FLASK_LIFECYCLE
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()
from database import init_db, get_user_ids_missing_username, upsert_user_profile
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


async def backfill_missing_usernames():
    """username이 비어있는 유저를 Discord 프로필 정보로 백필"""
    missing_user_ids = get_user_ids_missing_username(limit=500)
    if not missing_user_ids:
        return

    updated = 0
    unresolved = 0

    for user_id in missing_user_ids:
        display_name = None

        # 캐시에 멤버가 있으면 서버 닉네임(display_name) 우선 사용
        for guild in bot.guilds:
            member = guild.get_member(user_id)
            if member:
                display_name = member.display_name
                break

        # 캐시에 없으면 Discord 사용자명으로 보정
        if not display_name:
            try:
                user = await bot.fetch_user(user_id)
                display_name = user.name
            except Exception:
                unresolved += 1
                continue

        if upsert_user_profile(user_id, display_name):
            updated += 1

    logger.info(f'유저명 백필 완료: {updated}명 갱신, {unresolved}명 미해결')

@bot.event
async def on_ready():
    """봇 시작 시 실행"""
    logger.info(f'{bot.user} 봇이 시작되었습니다.')

    # 데이터베이스 초기화
    if not getattr(bot, '_db_initialized', False):
        init_db()
        bot._db_initialized = True
        logger.info('데이터베이스 초기화 완료')
    if not getattr(bot, '_username_backfill_done', False):
        await backfill_missing_usernames()
        bot._username_backfill_done = True

    # Flask 서버 자동 시작 (옵션)
    if MANAGE_FLASK_LIFECYCLE and not getattr(bot, '_flask_lifecycle_started', False):
        flask_lifecycle.on_bot_start()
        bot._flask_lifecycle_started = True
    elif not MANAGE_FLASK_LIFECYCLE:
        logger.info('MANAGE_FLASK_LIFECYCLE=False: Flask 생명주기 자동 관리를 건너뜁니다.')
    
    # Flask 서버 모니터링 Agent 시작 (선택 사항)
    monitoring_channel_id = os.getenv('MONITORING_CHANNEL_ID')
    if monitoring_channel_id and monitoring_channel_id != '0':
        try:
            monitoring_channel_id = int(monitoring_channel_id)
            if monitoring_channel_id > 0 and not getattr(bot, '_dashboard_agent_started', False):
                from agents.dashboard_admin import DashboardAdminAgent

                dashboard_agent = DashboardAdminAgent(bot, monitoring_channel_id)
                await dashboard_agent.start_monitoring()
                bot._dashboard_agent = dashboard_agent
                bot._dashboard_agent_started = True
                logger.info(f'Flask 모니터링 Agent 시작됨 (채널 ID: {monitoring_channel_id})')
            elif monitoring_channel_id > 0:
                logger.info('Flask 모니터링 Agent가 이미 실행 중입니다.')
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
        'cogs.admin',  # 관리자 명령어 (Hot Reload)
        'skills.flask_admin',  # Flask 서버 관리 Skill
    ]

    for extension in initial_extensions:
        if extension in bot.extensions:
            continue
        try:
            await bot.load_extension(extension)
            logger.info(f'Cog 로드 완료: {extension}')
        except Exception as e:
            logger.error(f'Cog 로드 실패: {extension} - {e}')

@bot.event
async def on_command_error(ctx, error):
    """전역 에러 핸들러 (개선된 버전)"""
    if isinstance(error, commands.CommandNotFound):
        return  # 무시
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ 필수 인자가 누락되었습니다: `{error.param.name}`", delete_after=10)
    elif isinstance(error, commands.CheckFailure):
        # 권한 부족 (예: @commands.is_owner())
        await ctx.send("❌ 이 명령어를 실행할 권한이 없습니다.", delete_after=10)
    elif isinstance(error, commands.CommandInvokeError):
        # 명령어 실행 중 발생한 실제 에러
        original_error = error.original
        logger.error(
            f'명령어 실행 중 에러 발생\n'
            f'  - 명령어: {ctx.command}\n'
            f'  - 사용자: {ctx.author} (ID: {ctx.author.id})\n'
            f'  - 채널: {ctx.channel} (ID: {ctx.channel.id})\n'
            f'  - 에러 타입: {type(original_error).__name__}\n'
            f'  - 에러 메시지: {original_error}',
            exc_info=error.original
        )
        await ctx.send("❌ 명령어 실행 중 오류가 발생했습니다. 관리자에게 문의하세요.", delete_after=10)
    else:
        # 기타 에러
        logger.error(
            f'알 수 없는 에러\n'
            f'  - 명령어: {ctx.command}\n'
            f'  - 사용자: {ctx.author} (ID: {ctx.author.id})\n'
            f'  - 에러 타입: {type(error).__name__}\n'
            f'  - 에러: {error}',
            exc_info=True
        )
        await ctx.send("❌ 명령어 실행 중 오류가 발생했습니다.", delete_after=10)

if __name__ == '__main__':
    # 봇 종료 시 Flask 서버도 종료 (Hook)
    if MANAGE_FLASK_LIFECYCLE:
        atexit.register(flask_lifecycle.on_bot_stop)
    
    try:
        bot.run(DISCORD_TOKEN)
    except Exception as e:
        logger.critical(f'봇 실행 실패: {e}', exc_info=True)
