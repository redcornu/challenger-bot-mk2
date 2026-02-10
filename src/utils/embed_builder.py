import discord
from typing import List, Dict
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
        """랭킹 Embed 생성"""
        embed = discord.Embed(
            title="🏆 도전에 진심인 편 - 명예의 전당",
            description=f"📅 마지막 갱신: {timestamp}\n━━━━━━━━━━━━━━━━━",
            color=EMBED_COLORS['gold']
        )

        if top_users:
            rank_text = ""
            for i, user in enumerate(top_users):
                medal = "🥇" if i == 0 else "🥈" if i == 1 else "🥉" if i == 2 else f"**{i+1}.**"
                username = user['username'] or f"User {user['user_id']}"

                rank_text += f"{medal} **{username}**\n"
                rank_text += f"  └ 🎓 졸업 `{user['ducks_raised']}마리` | "
                rank_text += f"📅 인증 `{user['total_auth_days']}일` | "
                rank_text += f"💰 골드 `{user['gold']}G`\n\n"

            embed.add_field(name="", value=rank_text, inline=False)
            embed.set_footer(text="💡 졸업한 오리 → 총 인증일 → 골드 순으로 정렬됩니다")
        else:
            embed.description = "아직 랭킹 데이터가 없습니다."

        return embed
