import discord
from discord.ext import commands, tasks
from config import MESSAGE_DELETE_AFTER
from database import get_top_users
from utils.embed_builder import EmbedBuilder
from utils.validators import get_kst_now
import os
import logging

logger = logging.getLogger(__name__)
RANKING_TITLE = "🏆 도전에 진심인 편 - 명예의 전당"

class RankingCog(commands.Cog):
    """랭킹 관련 명령어 그룹"""

    def __init__(self, bot):
        self.bot = bot
        self.ranking_channel_id = int(os.getenv('RANKING_CHANNEL_ID', 0))

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

    async def _delete_old_ranking_messages(self, channel: discord.TextChannel):
        """기존 랭킹 메시지를 정리하고 최신 1개만 반환"""
        ranking_messages = []

        async for message in channel.history(limit=None):
            if self._is_ranking_message(message):
                ranking_messages.append(message)

        if not ranking_messages:
            return None

        # 최신 메시지를 남기고 나머지 삭제
        ranking_messages.sort(key=lambda m: m.created_at, reverse=True)
        latest_message = ranking_messages[0]

        deleted_count = 0
        for old_message in ranking_messages[1:]:
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

        return latest_message

    async def _publish_latest_ranking(self, channel: discord.TextChannel):
        """랭킹 메시지를 단일 최신 메시지로 유지"""
        top_users = get_top_users(limit=10)
        timestamp = get_kst_now().strftime("%Y-%m-%d %H:%M")
        embed = EmbedBuilder.ranking(top_users, timestamp)
        embed.set_footer(text="⏰ 매시간 자동 갱신됩니다")

        latest_message = await self._delete_old_ranking_messages(channel)

        if latest_message:
            await latest_message.edit(embed=embed)
            logger.info(f"랭킹 메시지 갱신 완료 (message_id: {latest_message.id})")
            return

        message = await channel.send(embed=embed)
        logger.info(f"랭킹 메시지 신규 생성 완료 (message_id: {message.id})")

    @commands.command(name='랭킹')
    async def ranking(self, ctx):
        """명예의 전당 (Top 10)"""
        # 랭킹 채널에서는 단일 최신 메시지 정책 유지
        if self.ranking_channel_id > 0 and ctx.channel.id == self.ranking_channel_id:
            try:
                await self._publish_latest_ranking(ctx.channel)
                await ctx.message.add_reaction("✅")
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
