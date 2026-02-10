import discord
from discord.ext import commands, tasks
from config import MESSAGE_DELETE_AFTER
from database import get_top_users
from utils.embed_builder import EmbedBuilder
from utils.validators import get_kst_now
import os
import logging

logger = logging.getLogger(__name__)

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

    @commands.command(name='랭킹')
    async def ranking(self, ctx):
        """명예의 전당 (Top 10)"""
        top_users = get_top_users(limit=10)
        timestamp = get_kst_now().strftime("%Y-%m-%d %H:%M")
        embed = EmbedBuilder.ranking(top_users, timestamp)
        await ctx.send(embed=embed, delete_after=MESSAGE_DELETE_AFTER)

    @tasks.loop(hours=1)
    async def hourly_ranking(self):
        """매 정각마다 랭킹 자동 게시"""
        try:
            channel = self.bot.get_channel(self.ranking_channel_id)
            if not channel:
                logger.error(f"랭킹 채널 {self.ranking_channel_id}을 찾을 수 없음")
                return

            top_users = get_top_users(limit=10)
            timestamp = get_kst_now().strftime("%Y-%m-%d %H:%M")

            embed = EmbedBuilder.ranking(top_users, timestamp)
            embed.set_footer(text="⏰ 매시간 자동 갱신됩니다")

            await channel.send(embed=embed)
            logger.info(f"시간당 랭킹이 채널 {self.ranking_channel_id}에 게시됨")

        except Exception as e:
            logger.error(f"시간당 랭킹 게시 오류: {e}", exc_info=True)

    @hourly_ranking.before_loop
    async def before_hourly_ranking(self):
        """봇이 준비될 때까지 대기"""
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(RankingCog(bot))
