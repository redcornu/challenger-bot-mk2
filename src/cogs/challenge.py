import discord
from discord.ext import commands
import logging
from config import BotStates, BotConfig, MESSAGE_DELETE_AFTER, IMAGE_PATHS, STATE_KOREAN
from database import get_challenge, create_challenge, update_challenge, get_user, create_user, update_user_inventory
from config import EMBED_COLORS
from utils.validators import get_kst_now, safe_json_loads, safe_json_dumps
from utils.embed_builder import EmbedBuilder

class ChallengeCog(commands.Cog):
    """도전 관련 명령어 그룹"""

    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger(__name__)

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

        # 유저 생성 (없으면)
        user = get_user(ctx.author.id)
        if not user:
            success = create_user(ctx.author.id, ctx.author.name)
            if not success:
                # Race condition 가능성: 다른 프로세스가 먼저 생성했을 수 있음
                user = get_user(ctx.author.id)
                if not user:
                    # 여전히 없으면 심각한 에러
                    self.logger.error(f"[Critical] 유저 생성/조회 실패: {ctx.author.id}")
                    embed = EmbedBuilder.error("오류", "유저 생성 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.")
                    await ctx.send(embed=embed, delete_after=MESSAGE_DELETE_AFTER)
                    return

        # 도전 생성
        success = create_challenge(ctx.channel.id, ctx.author.id, goal)
        if success:
            embed = EmbedBuilder.success(
                "도전 시작!",
                f"**목표:** {goal}\n\n🥚 알이 부화하기 시작했습니다!\n매일 인증하여 오리를 키워주세요!"
            )
            # 이미지 첨부 (있으면)
            if IMAGE_PATHS.get(BotStates.EGG):
                try:
                    file = discord.File(IMAGE_PATHS[BotStates.EGG], filename="egg.png")
                    embed.set_image(url="attachment://egg.png")
                    await ctx.send(embed=embed, file=file, delete_after=MESSAGE_DELETE_AFTER)
                    return
                except:
                    pass

            await ctx.send(embed=embed, delete_after=MESSAGE_DELETE_AFTER)
        else:
            embed = EmbedBuilder.error("생성 실패", "도전 생성 중 오류 발생")
            await ctx.send(embed=embed, delete_after=MESSAGE_DELETE_AFTER)

    @commands.command(name='인증')
    async def authenticate(self, ctx):
        """일일 인증 (사진 필수)"""
        # 중복 실행 추적을 위한 로그
        self.logger.info(f"[인증 시작] 사용자: {ctx.author.id}, 채널: {ctx.channel.id}, 메시지 ID: {ctx.message.id}")

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

        # 사진 첨부 확인
        if not ctx.message.attachments:
            embed = EmbedBuilder.error(
                "사진 필요",
                "인증샷을 함께 첨부해주세요!"
            )
            await ctx.send(embed=embed, delete_after=MESSAGE_DELETE_AFTER)
            return

        # 중복 인증 방지
        today = get_kst_now().date().isoformat()
        self.logger.info(f"[중복 인증 체크] 사용자: {ctx.author.id}, 오늘: {today}, 마지막 인증: {challenge['last_auth_date']}")
        if challenge['last_auth_date'] == today:
            self.logger.warning(f"[중복 인증 차단] 사용자: {ctx.author.id}가 오늘 이미 인증함")
            embed = EmbedBuilder.error(
                "이미 인증 완료",
                "오늘은 이미 인증하셨습니다!"
            )
            await ctx.send(embed=embed, delete_after=MESSAGE_DELETE_AFTER)
            return

        # 페널티 및 인증 처리 로직
        from datetime import datetime
        
        current_state = challenge['state']
        new_state = current_state
        new_streak = challenge['streak']
        new_growth = challenge['growth_days']
        new_total = challenge['total_days']
        message_extra = ""
        
        # 마지막 인증 날짜와의 차이 계산
        if challenge['last_auth_date']:
            last_date = datetime.fromisoformat(challenge['last_auth_date']).date()
            today_date = datetime.fromisoformat(today).date()
            days_diff = (today_date - last_date).days
        else:
            days_diff = 1  # 첫 인증
        
        # 상태별 처리
        if current_state in [BotStates.EGG, BotStates.DUCKLING, BotStates.ADOLESCENT, BotStates.ADULT]:
            # 정상 상태
            if days_diff == 1:
                # 정상 인증
                new_streak += 1
                new_growth += 1
                new_total += 1
                
                # 성장 단계 체크
                if new_growth >= BotConfig.GRADUATION_DAYS:
                    new_state = BotStates.DONE
                elif new_growth >= BotConfig.ADULT_DAYS:
                    new_state = BotStates.ADULT
                elif new_growth >= BotConfig.ADOLESCENT_DAYS:
                    new_state = BotStates.ADOLESCENT
                elif new_growth >= BotConfig.HATCH_DAYS:
                    new_state = BotStates.DUCKLING
                    
            elif days_diff == 2:
                # 1일 건너뛰었음 → SULKY
                new_state = BotStates.SULKY
                new_streak = 0
                new_total += 1
                message_extra = "\n\n😤 **오리가 삐쳤습니다!**\n3일 연속 인증하면 다시 돌아옵니다."
                
            elif days_diff >= 3:
                # 2일 이상 건너뛰었음 → RUNAWAY
                new_state = BotStates.RUNAWAY
                new_streak = 0
                new_total += 1
                message_extra = "\n\n🏃 **오리가 가출했습니다!**\n7일 연속 인증하면 돌아옵니다."
                
        elif current_state == BotStates.SULKY:
            # 삐진 상태
            if days_diff == 1:
                # 연속 인증 중
                new_streak += 1
                new_total += 1
                
                if new_streak >= BotConfig.SULKY_RECOVERY_DAYS:
                    # 3일 연속 인증 → 복구!
                    new_state = BotStates.EGG  # 또는 이전 상태로
                    # growth_days로 상태 복구
                    if new_growth >= BotConfig.ADULT_DAYS:
                        new_state = BotStates.ADULT
                    elif new_growth >= BotConfig.ADOLESCENT_DAYS:
                        new_state = BotStates.ADOLESCENT
                    elif new_growth >= BotConfig.HATCH_DAYS:
                        new_state = BotStates.DUCKLING
                    else:
                        new_state = BotStates.EGG
                    message_extra = "\n\n💚 **오리가 기분이 풀렸습니다!**"
                else:
                    message_extra = f"\n\n😤 복구까지 {BotConfig.SULKY_RECOVERY_DAYS - new_streak}일 남았습니다."
                    
            elif days_diff >= 2:
                # 또 건너뛰었음 → RUNAWAY
                new_state = BotStates.RUNAWAY
                new_streak = 0
                new_total += 1
                message_extra = "\n\n🏃 **오리가 가출했습니다!**\n7일 연속 인증하면 돌아옵니다."
                
        elif current_state == BotStates.RUNAWAY:
            # 가출 상태
            if days_diff == 1:
                # 연속 인증 중
                new_streak += 1
                new_total += 1
                
                if new_streak >= BotConfig.RUNAWAY_RECOVERY_DAYS:
                    # 7일 연속 인증 → 복구!
                    # growth_days로 상태 복구
                    if new_growth >= BotConfig.ADULT_DAYS:
                        new_state = BotStates.ADULT
                    elif new_growth >= BotConfig.ADOLESCENT_DAYS:
                        new_state = BotStates.ADOLESCENT
                    elif new_growth >= BotConfig.HATCH_DAYS:
                        new_state = BotStates.DUCKLING
                    else:
                        new_state = BotStates.EGG
                    message_extra = "\n\n🏠 **오리가 집으로 돌아왔습니다!**"
                else:
                    message_extra = f"\n\n🏃 복구까지 {BotConfig.RUNAWAY_RECOVERY_DAYS - new_streak}일 남았습니다."
            else:
                # 또 건너뛰었음 (이미 최악)
                new_total += 1
                message_extra = "\n\n🏃 오리는 여전히 가출 중입니다..."
        
        elif current_state == BotStates.DONE:
            # 졸업 상태 - 인증만 기록
            new_total += 1

        # DB 업데이트
        self.logger.info(f"[인증 DB 업데이트 시작] 사용자: {ctx.author.id}, 채널: {ctx.channel.id}, 상태: {new_state}, 연속: {new_streak}일")
        update_challenge(ctx.channel.id, state=new_state, streak=new_streak,
                         growth_days=new_growth, total_days=new_total, last_auth_date=today)
        self.logger.info(f"[인증 DB 업데이트 완료] 사용자: {ctx.author.id}, 채널: {ctx.channel.id}")

        # 골드 지급 (정상 상태일 때만)
        if new_state not in [BotStates.SULKY, BotStates.RUNAWAY]:
            user = get_user(ctx.author.id)
            if not user:
                # 이 시점에서 유저가 없으면 심각한 문제
                self.logger.error(f"[Critical] 골드 지급 실패: 유저 {ctx.author.id} 찾을 수 없음")
                # 복구 시도
                create_user(ctx.author.id, ctx.author.name)
                user = get_user(ctx.author.id)

            if user:
                old_gold = user['gold']
                new_gold = old_gold + BotConfig.DAILY_GOLD_REWARD
                self.logger.info(f"[골드 지급] 사용자: {ctx.author.id}, 기존: {old_gold}G -> 신규: {new_gold}G")

                success = update_user_inventory(ctx.author.id, new_gold, user['inventory'])
                if not success:
                    self.logger.error(f"[Error] 골드 업데이트 실패: 유저 {ctx.author.id}")
            else:
                self.logger.error(f"[Critical] 골드 지급 완전 실패: 유저 {ctx.author.id}")

        # 결과 메시지
        if new_state in [BotStates.SULKY, BotStates.RUNAWAY]:
            status_text = f"**상태:** {STATE_KOREAN.get(new_state, new_state)}\n**복구 진행:** {new_streak}/{BotConfig.SULKY_RECOVERY_DAYS if new_state == BotStates.SULKY else BotConfig.RUNAWAY_RECOVERY_DAYS}일"
        else:
            status_text = f"**연속 {new_streak}일째** 인증 중입니다!\n**성장일:** D+{new_growth}/{BotConfig.GRADUATION_DAYS}\n**상태:** {STATE_KOREAN.get(new_state, new_state)}"
        
        embed = EmbedBuilder.success(
            "인증 완료!",
            status_text + message_extra
        )
        await ctx.send(embed=embed, delete_after=MESSAGE_DELETE_AFTER)
        self.logger.info(f"[인증 완료] 사용자: {ctx.author.id}, 채널: {ctx.channel.id}, 메시지 ID: {ctx.message.id}")

    @commands.command(name='상태')
    async def status(self, ctx):
        """현재 오리 상태 및 인벤토리 확인"""
        challenge = get_challenge(ctx.channel.id)
        if not challenge:
            embed = EmbedBuilder.error("도전 없음", "먼저 !목표설정으로 도전을 시작하세요.")
            await ctx.send(embed=embed, delete_after=MESSAGE_DELETE_AFTER)
            return

        user = get_user(ctx.author.id)

        state_emoji = {
            BotStates.EGG: "🥚", BotStates.DUCKLING: "🐣",
            BotStates.ADOLESCENT: "🦆", BotStates.ADULT: "🦢",
            BotStates.SULKY: "😤", BotStates.RUNAWAY: "🏃", BotStates.DONE: "🎓"
        }

        embed = discord.Embed(
            title=f"{state_emoji.get(challenge['state'], '❓')} {challenge['goal_text']}",
            color=EMBED_COLORS['info']
        )

        # 도전 현황
        progress = (
            f"**상태:** {STATE_KOREAN.get(challenge['state'], challenge['state'])}\n"
            f"**연속:** {challenge['streak']}일\n"
            f"**성장일:** D+{challenge['growth_days']}/{BotConfig.GRADUATION_DAYS}\n"
            f"**총 인증일:** {challenge['total_days']}일"
        )
        embed.add_field(name="📊 도전 현황", value=progress, inline=False)

        # 내 정보 + 인벤토리
        if user:
            from cogs.shop import SHOP_ITEMS

            inventory = safe_json_loads(user['inventory'])
            items_text = "\n".join([
                f"{SHOP_ITEMS[name]['emoji']} {name}: {count}개"
                for name, count in inventory.items() if name in SHOP_ITEMS
            ]) or "보유한 아이템이 없습니다."

            user_stats = f"💰 **골드:** {user['gold']}G\n🎓 **졸업한 오리:** {user['ducks_raised']}마리"
            embed.add_field(name="👤 내 정보", value=user_stats, inline=True)
            embed.add_field(name="🎒 인벤토리", value=items_text, inline=True)

        await ctx.send(embed=embed, delete_after=MESSAGE_DELETE_AFTER)

    @commands.command(name='가이드')
    async def guide(self, ctx):
        """사용 설명서"""
        guide_text = """📖 **오리와 66일의 약속 - 사용 설명서**
습관을 만드는 66일간의 여정, 귀여운 오리와 함께하세요!

🌱 **시작하기**
포럼 게시글(스레드)을 만들고
`!목표설정 [목표]`를 입력하세요.

✅ **매일 인증**
매일 인증샷과 함께 `!인증`을 입력하세요.
(하루 1회 가능, 성공 시 +1 Gold)

🦆 **오리의 성장**
• 오리알 (EGG): 7일까지
• 병아리 오리 (DUCKLING): 7~22일
• 사춘기 오리 (ADOLESCENT): 22~42일
• 어른 오리 (ADULT): 43~65일
• 졸업 (DONE): 66일

⚠️ **주의사항 (페널티 시스템)**
• 1일 건너뛰면 → 😤 **삐진 상태** (3일 연속 인증 시 회복)
• 삐진 상태에서 또 건너뛰면 → 🏃 **가출 상태** (7일 연속 인증 시 귀가)
• 페널티 상태에서는 골드를 받을 수 없습니다!

💊 **아이템으로 즉시 복구**
• 회복약 (5G): 삐진 상태 즉시 회복
• 귀환석 (10G): 가출 상태 즉시 회복

📋 **명령어 목록**
`!상태`: 현재 진행 상황과 인벤토리를 확인합니다.
`!상점`: 구매 가능한 아이템을 확인합니다.
`!구매 [아이템]`: 아이템을 구매합니다.
`!사용 [아이템]`: 아이템을 사용합니다.
`!가이드`: 이 도움말을 다시 봅니다."""

        embed = discord.Embed(
            title="📚 오리와 66일의 약속",
            description=guide_text,
            color=EMBED_COLORS['info']
        )
        embed.set_footer(text="💡 질문이 있으면 관리자에게 문의하세요!")

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

# Cog 로드 함수
async def setup(bot):
    await bot.add_cog(ChallengeCog(bot))
