import discord
from discord.ext import commands, tasks
from config import MESSAGE_DELETE_AFTER
from database import get_top_users, get_system_config, set_system_config
from utils.embed_builder import EmbedBuilder
from utils.validators import get_kst_now
import os
import logging

logger = logging.getLogger(__name__)
RANKING_TITLE = "🏆 도전에 진심인 편 - 명예의 전당"
RANKING_MESSAGE_ID_KEY = "ranking_latest_message_id"

class RankingCog(commands.Cog):
    """랭킹 관련 명령어 그룹"""

    def __init__(self, bot):
        self.bot = bot
        self.ranking_channel_id = int(os.getenv('RANKING_CHANNEL_ID', 0))
        self.latest_ranking_message_id = None

        if self.ranking_channel_id > 0:
            self.hourly_ranking.start()
            logger.info(f"시간당 랭킹 작업 시작: 채널 {self.ranking_channel_id}")

    def cog_unload(self):
        """Cog 언로드 시 태스크 정리"""
        self.hourly_ranking.cancel()

    def _is_ranking_message(self, message: discord.Message) -> bool:
        """랭킹 시스템이 생성한 메시지인지 확인"""
        if message.author.id != self.bot.user.id:
            return False
        if not message.embeds:
            return False
        return message.embeds[0].title == RANKING_TITLE

    async def _get_ranking_channel(self):
        channel = self.bot.get_channel(self.ranking_channel_id)
        if channel:
            return channel
        try:
            return await self.bot.fetch_channel(self.ranking_channel_id)
        except Exception:
            return None

    def _load_saved_message_id(self):
        if self.latest_ranking_message_id is not None:
            return
        raw_value = get_system_config(RANKING_MESSAGE_ID_KEY)
        if not raw_value:
            return
        try:
            self.latest_ranking_message_id = int(raw_value)
        except ValueError:
            self.latest_ranking_message_id = None

    async def _get_saved_ranking_message(self, channel: discord.TextChannel):
        """저장된 메시지 ID로 랭킹 메시지 조회"""
        self._load_saved_message_id()
        if not self.latest_ranking_message_id:
            return None
        try:
            message = await channel.fetch_message(self.latest_ranking_message_id)
            if self._is_ranking_message(message):
                return message
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            pass
        return None

    async def _find_latest_ranking_message(self, channel: discord.TextChannel, limit: int = 200):
        """최근 메시지에서 최신 랭킹 메시지 1개 조회"""
        async for message in channel.history(limit=limit):
            if self._is_ranking_message(message):
                return message
        return None

    async def _delete_old_ranking_messages(self, channel: discord.TextChannel, keep_message_id: int):
        """최근 랭킹 메시지 중 최신 1개를 제외하고 정리"""
        deleted_count = 0

        async for old_message in channel.history(limit=500):
            if not self._is_ranking_message(old_message):
                continue
            if old_message.id == keep_message_id:
                continue
            try:
                await old_message.delete()
                deleted_count += 1
            except discord.NotFound:
                continue
            except discord.Forbidden:
                logger.error("랭킹 메시지 삭제 권한이 없습니다.")
                break
            except discord.HTTPException:
                logger.warning(f"랭킹 메시지 삭제 실패: {old_message.id}")

        if deleted_count > 0:
            logger.info(f"기존 랭킹 기록 {deleted_count}개 삭제 완료")

    async def _publish_latest_ranking(self, channel: discord.TextChannel):
        """랭킹 메시지를 단일 최신 메시지로 유지"""
        top_users = get_top_users(limit=10)
        timestamp = get_kst_now().strftime("%Y-%m-%d %H:%M")
        embed = EmbedBuilder.ranking(top_users, timestamp)
        embed.set_footer(text="⏰ 매시간 자동 갱신됩니다")

        latest_message = await self._get_saved_ranking_message(channel)
        if not latest_message:
            latest_message = await self._find_latest_ranking_message(channel)

        if latest_message:
            await latest_message.edit(embed=embed)
            logger.info(f"랭킹 메시지 갱신 완료 (message_id: {latest_message.id})")
            message = latest_message
        else:
            message = await channel.send(embed=embed)
            logger.info(f"랭킹 메시지 신규 생성 완료 (message_id: {message.id})")

        self.latest_ranking_message_id = message.id
        set_system_config(RANKING_MESSAGE_ID_KEY, str(message.id))
        await self._delete_old_ranking_messages(channel, keep_message_id=message.id)

    @commands.command(name='랭킹')
    async def ranking(self, ctx):
        """명예의 전당 (Top 10)"""
        # 랭킹 채널에서는 단일 최신 메시지 정책 유지
        if self.ranking_channel_id > 0 and ctx.channel.id == self.ranking_channel_id:
            try:
                await self._publish_latest_ranking(ctx.channel)
                try:
                    await ctx.message.add_reaction("✅")
                except Exception:
                    pass
            except Exception as e:
                logger.error(f"랭킹 수동 갱신 오류: {e}", exc_info=True)
                await ctx.send("❌ 랭킹 갱신 중 오류가 발생했습니다.", delete_after=10)
            return

        top_users = get_top_users(limit=10)
        timestamp = get_kst_now().strftime("%Y-%m-%d %H:%M")
        embed = EmbedBuilder.ranking(top_users, timestamp)
        await ctx.send(embed=embed, delete_after=MESSAGE_DELETE_AFTER)

    @tasks.loop(hours=1)
    async def hourly_ranking(self):
        """매 정각마다 랭킹 자동 게시"""
        try:
            channel = await self._get_ranking_channel()
            if not channel:
                logger.error(f"랭킹 채널 {self.ranking_channel_id}을 찾을 수 없음")
                return

            await self._publish_latest_ranking(channel)
            logger.info(f"시간당 랭킹이 채널 {self.ranking_channel_id}에 갱신됨")

        except Exception as e:
            logger.error(f"시간당 랭킹 게시 오류: {e}", exc_info=True)

    @hourly_ranking.before_loop
    async def before_hourly_ranking(self):
        """봇이 준비될 때까지 대기"""
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(RankingCog(bot))
