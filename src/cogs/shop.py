import discord
from discord.ext import commands
from config import MESSAGE_DELETE_AFTER
from database import get_user, update_user_inventory
from utils.embed_builder import EmbedBuilder
from utils.validators import safe_json_loads, safe_json_dumps

SHOP_ITEMS = {
    "회복약": {"price": 5, "description": "삐진 상태를 즉시 회복", "emoji": "💊"},
    "귀환석": {"price": 10, "description": "가출 상태를 즉시 회복", "emoji": "🔮"},
}

class ShopCog(commands.Cog):
    """상점 관련 명령어 그룹"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='상점')
    async def shop(self, ctx):
        """상점 아이템 목록"""
        embed = discord.Embed(
            title="🏪 상점",
            description="아이템을 구매하려면 !구매 [아이템명]",
            color=0xFFD700
        )

        for item_name, item_data in SHOP_ITEMS.items():
            embed.add_field(
                name=f"{item_data['emoji']} {item_name} - {item_data['price']}G",
                value=item_data['description'],
                inline=False
            )

        await ctx.send(embed=embed, delete_after=MESSAGE_DELETE_AFTER)

    @commands.command(name='구매')
    async def buy(self, ctx, *, item_name: str):
        """아이템 구매"""
        if item_name not in SHOP_ITEMS:
            embed = EmbedBuilder.error(
                "아이템 없음",
                f"'{item_name}'은(는) 존재하지 않는 아이템입니다."
            )
            await ctx.send(embed=embed, delete_after=MESSAGE_DELETE_AFTER)
            return

        user = get_user(ctx.author.id)
        if not user:
            embed = EmbedBuilder.error(
                "유저 없음",
                "먼저 도전을 시작하세요."
            )
            await ctx.send(embed=embed, delete_after=MESSAGE_DELETE_AFTER)
            return

        item = SHOP_ITEMS[item_name]
        if user['gold'] < item['price']:
            embed = EmbedBuilder.error(
                "골드 부족",
                f"필요: {item['price']}G | 보유: {user['gold']}G"
            )
            await ctx.send(embed=embed, delete_after=MESSAGE_DELETE_AFTER)
            return

        # 아이템 구매 처리
        inventory = safe_json_loads(user['inventory'])
        inventory[item_name] = inventory.get(item_name, 0) + 1

        # DB 업데이트
        update_user_inventory(ctx.author.id, user['gold'] - item['price'], safe_json_dumps(inventory))

        embed = EmbedBuilder.success(
            "구매 완료!",
            f"{item['emoji']} {item_name}을(를) 구매했습니다!"
        )
        await ctx.send(embed=embed, delete_after=MESSAGE_DELETE_AFTER)

    @commands.command(name='인벤토리')
    async def inventory(self, ctx):
        """인벤토리는 !상태 명령어에 통합되었습니다"""
        embed = EmbedBuilder.info(
            "인벤토리 확인",
            "인벤토리는 이제 **!상태** 명령어에서 확인할 수 있습니다!\n도전 스레드에서 !상태를 사용해보세요."
        )
        await ctx.send(embed=embed, delete_after=MESSAGE_DELETE_AFTER)

    @commands.command(name='사용')
    async def use_item(self, ctx, *, item_name: str):
        """아이템 사용"""
        if item_name not in SHOP_ITEMS:
            embed = EmbedBuilder.error(
                "아이템 없음",
                f"'{item_name}'은(는) 존재하지 않는 아이템입니다."
            )
            await ctx.send(embed=embed, delete_after=MESSAGE_DELETE_AFTER)
            return

        # 스레드 검증
        if not isinstance(ctx.channel, discord.Thread):
            embed = EmbedBuilder.error(
                "오류",
                "이 명령어는 도전 스레드에서만 사용 가능합니다."
            )
            await ctx.send(embed=embed, delete_after=MESSAGE_DELETE_AFTER)
            return

        from database import get_challenge, update_challenge
        from config import BotStates, BotConfig
        
        # 도전 정보 확인
        challenge = get_challenge(ctx.channel.id)
        if not challenge:
            embed = EmbedBuilder.error(
                "도전 없음",
                "이 스레드에는 활성화된 도전이 없습니다."
            )
            await ctx.send(embed=embed, delete_after=MESSAGE_DELETE_AFTER)
            return

        # 소유권 확인
        if ctx.author.id != ctx.channel.owner_id:
            embed = EmbedBuilder.error(
                "권한 없음",
                "이 도전의 주인만 아이템을 사용할 수 있습니다."
            )
            await ctx.send(embed=embed, delete_after=MESSAGE_DELETE_AFTER)
            return

        # 유저 정보 확인
        user = get_user(ctx.author.id)
        if not user:
            embed = EmbedBuilder.error(
                "유저 없음",
                "유저 정보를 찾을 수 없습니다."
            )
            await ctx.send(embed=embed, delete_after=MESSAGE_DELETE_AFTER)
            return

        # 인벤토리 확인
        inventory = safe_json_loads(user['inventory'])
        if inventory.get(item_name, 0) <= 0:
            embed = EmbedBuilder.error(
                "아이템 없음",
                f"{item_name}을(를) 보유하고 있지 않습니다."
            )
            await ctx.send(embed=embed, delete_after=MESSAGE_DELETE_AFTER)
            return

        current_state = challenge['state']
        success = False
        result_message = ""

        # 아이템별 효과
        if item_name == "회복약":
            if current_state == BotStates.SULKY:
                # SULKY → 정상 상태로 복구
                new_state = BotStates.EGG
                growth_days = challenge['growth_days']
                
                # growth_days에 따라 적절한 상태로 복구
                if growth_days >= BotConfig.ADULT_DAYS:
                    new_state = BotStates.ADULT
                elif growth_days >= BotConfig.ADOLESCENT_DAYS:
                    new_state = BotStates.ADOLESCENT
                elif growth_days >= BotConfig.HATCH_DAYS:
                    new_state = BotStates.DUCKLING
                
                update_challenge(ctx.channel.id, state=new_state, streak=0)
                success = True
                result_message = f"💊 **회복약을 사용했습니다!**\n\n💚 오리의 기분이 좋아졌습니다!\n**상태:** {BotStates.SULKY} → {new_state}"
            else:
                result_message = "😤 회복약은 **삐진 상태**일 때만 사용할 수 있습니다."
                
        elif item_name == "귀환석":
            if current_state == BotStates.RUNAWAY:
                # RUNAWAY → 정상 상태로 복구
                new_state = BotStates.EGG
                growth_days = challenge['growth_days']
                
                # growth_days에 따라 적절한 상태로 복구
                if growth_days >= BotConfig.ADULT_DAYS:
                    new_state = BotStates.ADULT
                elif growth_days >= BotConfig.ADOLESCENT_DAYS:
                    new_state = BotStates.ADOLESCENT
                elif growth_days >= BotConfig.HATCH_DAYS:
                    new_state = BotStates.DUCKLING
                
                update_challenge(ctx.channel.id, state=new_state, streak=0)
                success = True
                result_message = f"🔮 **귀환석을 사용했습니다!**\n\n🏠 오리가 집으로 돌아왔습니다!\n**상태:** {BotStates.RUNAWAY} → {new_state}"
            else:
                result_message = "🏃 귀환석은 **가출 상태**일 때만 사용할 수 있습니다."

        if success:
            # 아이템 소모
            inventory[item_name] -= 1
            if inventory[item_name] == 0:
                del inventory[item_name]
            
            update_user_inventory(ctx.author.id, user['gold'], safe_json_dumps(inventory))
            
            embed = EmbedBuilder.success("아이템 사용 완료", result_message)
        else:
            embed = EmbedBuilder.error("사용 불가", result_message)

        await ctx.send(embed=embed, delete_after=MESSAGE_DELETE_AFTER)

async def setup(bot):
    await bot.add_cog(ShopCog(bot))
