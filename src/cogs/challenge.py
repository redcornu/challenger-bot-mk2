import asyncio
import discord
from discord.ext import commands
import logging
import re
from config import BotStates, BotConfig, MESSAGE_DELETE_AFTER, IMAGE_PATHS, STATE_KOREAN, normalize_state
from database import (
    get_challenge,
    create_challenge,
    update_challenge,
    get_user,
    create_user,
    update_user_inventory,
    upsert_user_profile,
    record_challenge_event,
)
from config import EMBED_COLORS
from utils.validators import get_kst_now, safe_json_loads, safe_json_dumps
from utils.embed_builder import EmbedBuilder
from utils.duck_voice import pick_duck_line

class ChallengeCog(commands.Cog):
    """도전 관련 명령어 그룹"""

    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger(__name__)
        self._auth_locks = {}
        self._last_duck_line_by_thread = {}

    def _author_display_name(self, author) -> str:
        return getattr(author, 'display_name', None) or author.name

    def _is_auth_test_bypass_user(self, author) -> bool:
        """테스트 전용 인증 제한 우회 유저 확인"""
        bypass_names = {'요진편'}
        display_name = (getattr(author, 'display_name', None) or '').strip()
        username = (getattr(author, 'name', None) or '').strip()
        return display_name in bypass_names or username in bypass_names

    def _state_from_growth_days(self, growth_days: int) -> str:
        """성장일 기준 정상 상태 계산"""
        if growth_days >= BotConfig.GRADUATION_DAYS:
            return BotStates.DONE
        if growth_days >= BotConfig.ADULT_DAYS:
            return BotStates.ADULT
        if growth_days >= BotConfig.ADOLESCENT_DAYS:
            return BotStates.ADOLESCENT
        if growth_days >= BotConfig.HATCH_DAYS:
            return BotStates.DUCKLING
        return BotStates.EGG

    def _get_auth_lock(self, thread_id: int) -> asyncio.Lock:
        lock = self._auth_locks.get(thread_id)
        if lock is None:
            lock = asyncio.Lock()
            self._auth_locks[thread_id] = lock
        return lock

    def _resolve_duck_voice_context(self, old_state: str, new_state: str) -> str:
        normal_states = {
            BotStates.EGG,
            BotStates.DUCKLING,
            BotStates.ADOLESCENT,
            BotStates.ADULT,
        }
        if new_state == BotStates.DONE:
            return 'DONE'
        if new_state == BotStates.SULKY and old_state != BotStates.SULKY:
            return 'SULKY_ENTER'
        if new_state == BotStates.RUNAWAY and old_state != BotStates.RUNAWAY:
            return 'RUNAWAY_ENTER'
        if old_state == BotStates.SULKY and new_state in normal_states:
            return 'SULKY_RECOVER'
        if old_state == BotStates.RUNAWAY and new_state in normal_states:
            return 'RUNAWAY_RECOVER'
        if old_state != new_state and new_state in normal_states:
            return 'LEVEL_UP'
        return 'NORMAL_GROWTH'

    def _make_progress_bar(self, filled: int, total: int) -> str:
        return '[' + ('■' * filled) + ('□' * (total - filled)) + ']'

    def _make_growth_meter(self, growth_days: int, total_days: int = 66, width: int = 12) -> str:
        safe_growth = max(0, growth_days)
        ratio = min(1.0, safe_growth / total_days) if total_days > 0 else 0.0
        filled = int(round(ratio * width))
        filled = min(width, max(0, filled))
        return '█' * filled + '░' * (width - filled)

    def _build_ansi_hud(
        self,
        *,
        state: str,
        streak: int,
        growth_days: int,
        total_days: int,
        gold: int,
        runaway_recovery_progress: str = None
    ) -> str:
        state_label = STATE_KOREAN.get(state, state)
        growth_meter = self._make_growth_meter(growth_days, BotConfig.GRADUATION_DAYS)
        state_color = {
            BotStates.RUNAWAY: "1;31",
            BotStates.SULKY: "1;33",
            BotStates.DONE: "1;35",
        }.get(state, "1;36")

        lines = [
            "\u001b[1;33m┌─ 상태창 ───────────────────────────┐\u001b[0m",
            f"\u001b[1;37m│ 상태     : \u001b[{state_color}m{state_label:<20}\u001b[0m",
            (
                f"\u001b[1;37m│ 성장일   : \u001b[1;32mD+{growth_days:>2}/{BotConfig.GRADUATION_DAYS:<2}"
                f"  {growth_meter}\u001b[0m"
            ),
            (
                f"\u001b[1;37m│ 연속일   : \u001b[1;32m{streak:>2}일\u001b[0m"
                f"\u001b[1;37m   총 인증: \u001b[1;36m{total_days:>3}일\u001b[0m"
            ),
            f"\u001b[1;37m│ GOLD     : \u001b[1;33m{gold:>4}G\u001b[0m",
        ]

        if runaway_recovery_progress:
            lines.append(
                (
                    "\u001b[1;37m│ 가출 복구: "
                    f"\u001b[1;31m{runaway_recovery_progress}\u001b[0m"
                    f"\u001b[1;37m (목표 {BotConfig.RUNAWAY_RECOVERY_DAYS}일)\u001b[0m"
                )
            )

        lines.append("\u001b[1;33m└───────────────────────────────────┘\u001b[0m")
        return "```ansi\n" + "\n".join(lines) + "\n```"

    async def _run_auth_loading_animation(self, ctx):
        frames = [
            (
                "⚔️ 오늘의 도전 처리 중",
                "🍽️ 도전 조각을 수집합니다.\n"
                f"진행률 33% {self._make_progress_bar(1, 3)}"
            ),
            (
                "⚔️ 오늘의 도전 처리 중",
                "🥣 도전을 영양분으로 변환합니다.\n"
                f"진행률 66% {self._make_progress_bar(2, 3)}"
            ),
            (
                "⚔️ 오늘의 도전 처리 중",
                "✨ 성장 반영을 완료합니다.\n"
                f"진행률 100% {self._make_progress_bar(3, 3)}"
            ),
        ]
        try:
            loading_message = await ctx.send(
                embed=EmbedBuilder.info(frames[0][0], frames[0][1]),
                delete_after=MESSAGE_DELETE_AFTER
            )
        except Exception as e:
            self.logger.warning(f"[인증 로딩] 로딩 메시지 전송 실패: {type(e).__name__}: {e}")
            return None

        for frame_title, frame_text in frames[1:]:
            await asyncio.sleep(1.5)
            try:
                await loading_message.edit(embed=EmbedBuilder.info(frame_title, frame_text))
            except Exception as e:
                self.logger.warning(f"[인증 로딩] 로딩 메시지 edit 실패: {type(e).__name__}: {e}")
                break

        # 마지막 프레임도 1.5초 유지해 총 4.5초(1.5초 x 3단계) 연출
        await asyncio.sleep(1.5)
        return loading_message

    @commands.command(name='목표설정')
    async def set_goal(self, ctx, *, goal: str):
        """새로운 도전 시작"""
        upsert_user_profile(ctx.author.id, self._author_display_name(ctx.author))

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
            success = create_user(ctx.author.id, self._author_display_name(ctx.author))
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
            created_challenge = get_challenge(ctx.channel.id)
            record_challenge_event(
                user_id=ctx.author.id,
                thread_id=ctx.channel.id,
                event_type='CHALLENGE_CREATED',
                before_challenge=None,
                after_challenge=created_challenge,
                event_date=get_kst_now().date().isoformat(),
                source='BOT',
                meta={'goal_text': goal}
            )

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
        upsert_user_profile(ctx.author.id, self._author_display_name(ctx.author))

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

        thread_id = ctx.channel.id
        auth_lock = self._get_auth_lock(thread_id)

        async with auth_lock:
            # lock 획득 직후 도전 상태 재조회 (중복 처리 방지)
            challenge = get_challenge(thread_id)
            if not challenge:
                embed = EmbedBuilder.error(
                    "도전 없음",
                    "먼저 !목표설정으로 도전을 시작하세요."
                )
                await ctx.send(embed=embed, delete_after=MESSAGE_DELETE_AFTER)
                return

            if not await self._check_ownership(ctx, challenge):
                return

            # 중복 인증 방지 (락 내부 재검증)
            is_test_bypass_user = self._is_auth_test_bypass_user(ctx.author)
            today = get_kst_now().date().isoformat()
            self.logger.info(f"[중복 인증 체크] 사용자: {ctx.author.id}, 오늘: {today}, 마지막 인증: {challenge['last_auth_date']}")
            if challenge['last_auth_date'] == today and not is_test_bypass_user:
                self.logger.warning(f"[중복 인증 차단] 사용자: {ctx.author.id}가 오늘 이미 인증함")
                embed = EmbedBuilder.error(
                    "이미 인증 완료",
                    "오늘은 이미 인증하셨습니다!"
                )
                await ctx.send(embed=embed, delete_after=MESSAGE_DELETE_AFTER)
                return
            if challenge['last_auth_date'] == today and is_test_bypass_user:
                self.logger.info(f"[테스트 우회] 사용자: {ctx.author.id} 중복 인증 제한 우회 허용")

            loading_message = await self._run_auth_loading_animation(ctx)

            # 페널티 및 인증 처리 로직
            from datetime import datetime

            current_state = normalize_state(challenge['state'])
            if current_state != challenge['state']:
                update_challenge(thread_id, state=current_state)
                challenge['state'] = current_state

            valid_states = {
                BotStates.EGG, BotStates.DUCKLING, BotStates.ADOLESCENT,
                BotStates.ADULT, BotStates.SULKY, BotStates.RUNAWAY, BotStates.DONE
            }
            if current_state not in valid_states:
                self.logger.warning(f"알 수 없는 상태값 감지: {current_state}, EGG로 복구합니다.")
                current_state = BotStates.EGG
                update_challenge(thread_id, state=current_state)
                challenge['state'] = current_state

            old_state = current_state
            new_state = current_state
            new_streak = challenge['streak']
            new_growth = challenge['growth_days']
            new_total = challenge['total_days']
            message_extra = ""
            before_snapshot = {
                'state': challenge['state'],
                'streak': challenge['streak'],
                'growth_days': challenge['growth_days'],
                'total_days': challenge['total_days'],
                'last_auth_date': challenge['last_auth_date'],
            }

            # 마지막 인증 날짜와의 차이 계산
            if challenge['last_auth_date']:
                last_date = datetime.fromisoformat(challenge['last_auth_date']).date()
                today_date = datetime.fromisoformat(today).date()
                days_diff = (today_date - last_date).days
            else:
                days_diff = 1  # 첫 인증
            if is_test_bypass_user and days_diff <= 0:
                # 테스트 계정은 같은 날 반복 인증도 1일 진행으로 처리
                days_diff = 1

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
                    # 삐짐 진입 당일 인증을 복구 1일차로 카운트
                    new_streak = 1
                    new_total += 1
                    message_extra = "\n\n😤 **오리가 삐쳤습니다!**\n3일 연속 인증하면 다시 돌아옵니다."

                elif days_diff >= 3:
                    # 2일 이상 건너뛰었음 → RUNAWAY
                    new_state = BotStates.RUNAWAY
                    new_streak = 0
                    new_total += 1
                    message_extra = f"\n\n🏃 **오리가 가출했습니다!**\n{BotConfig.RUNAWAY_RECOVERY_DAYS}일 연속 인증하면 돌아옵니다."

            elif current_state == BotStates.SULKY:
                # 삐진 상태
                if days_diff == 1:
                    # 연속 인증 중
                    new_streak += 1
                    new_total += 1

                    if new_streak >= BotConfig.SULKY_RECOVERY_DAYS:
                        # 3일 연속 인증 → 복구!
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
                    message_extra = f"\n\n🏃 **오리가 가출했습니다!**\n{BotConfig.RUNAWAY_RECOVERY_DAYS}일 연속 인증하면 돌아옵니다."

            elif current_state == BotStates.RUNAWAY:
                # 가출 상태
                if days_diff == 1:
                    # 연속 인증 중
                    new_streak += 1
                    new_total += 1

                    if new_streak >= BotConfig.RUNAWAY_RECOVERY_DAYS:
                        # RUNAWAY_RECOVERY_DAYS 연속 인증 → 복구!
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
            self.logger.info(f"[인증 DB 업데이트 시작] 사용자: {ctx.author.id}, 채널: {thread_id}, 상태: {new_state}, 연속: {new_streak}일")
            update_success = update_challenge(
                thread_id,
                state=new_state,
                streak=new_streak,
                growth_days=new_growth,
                total_days=new_total,
                last_auth_date=today
            )
            if update_success:
                after_snapshot = {
                    'state': new_state,
                    'streak': new_streak,
                    'growth_days': new_growth,
                    'total_days': new_total,
                    'last_auth_date': today,
                }
                record_challenge_event(
                    user_id=ctx.author.id,
                    thread_id=thread_id,
                    event_type='AUTH_SUCCESS',
                    before_challenge=before_snapshot,
                    after_challenge=after_snapshot,
                    event_date=today,
                    source='BOT'
                )
            else:
                self.logger.error(f"[인증 DB 업데이트 실패] 사용자: {ctx.author.id}, 채널: {thread_id}")
                fail_embed = EmbedBuilder.error("인증 실패", "인증 처리 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.")
                if loading_message:
                    try:
                        await loading_message.edit(embed=fail_embed)
                    except Exception:
                        await ctx.send(embed=fail_embed, delete_after=MESSAGE_DELETE_AFTER)
                else:
                    await ctx.send(embed=fail_embed, delete_after=MESSAGE_DELETE_AFTER)
                return

            self.logger.info(f"[인증 DB 업데이트 완료] 사용자: {ctx.author.id}, 채널: {thread_id}")

            # 골드 지급 (정상 상태일 때만)
            if new_state not in [BotStates.SULKY, BotStates.RUNAWAY]:
                user = get_user(ctx.author.id)
                if not user:
                    # 이 시점에서 유저가 없으면 심각한 문제
                    self.logger.error(f"[Critical] 골드 지급 실패: 유저 {ctx.author.id} 찾을 수 없음")
                    # 복구 시도
                    create_user(ctx.author.id, self._author_display_name(ctx.author))
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
            if new_state == BotStates.RUNAWAY:
                status_text = f"**상태:** {STATE_KOREAN.get(new_state, new_state)}\n**가출 복구:** {new_streak}/{BotConfig.RUNAWAY_RECOVERY_DAYS}일"
            elif new_state == BotStates.SULKY:
                status_text = f"**상태:** {STATE_KOREAN.get(new_state, new_state)}"
            else:
                status_text = f"**연속 {new_streak}일째** 인증 중입니다!\n**성장일:** D+{new_growth}/{BotConfig.GRADUATION_DAYS}\n**상태:** {STATE_KOREAN.get(new_state, new_state)}"

            duck_voice_context = self._resolve_duck_voice_context(old_state, new_state)
            previous_line = self._last_duck_line_by_thread.get(thread_id)
            duck_line = pick_duck_line(
                context=duck_voice_context,
                goal_text=challenge.get('goal_text'),
                previous_line=previous_line
            )
            self._last_duck_line_by_thread[thread_id] = duck_line

            embed = EmbedBuilder.success(
                "인증 완료!",
                status_text + message_extra
            )
            embed.add_field(name="🗨️ 오리의 한마디", value=duck_line, inline=False)

            final_user = get_user(ctx.author.id)
            final_gold = final_user['gold'] if final_user else 0
            runaway_recovery_progress = None
            if new_state == BotStates.RUNAWAY:
                runaway_recovery_progress = f"{new_streak}/{BotConfig.RUNAWAY_RECOVERY_DAYS}"
            ansi_hud = self._build_ansi_hud(
                state=new_state,
                streak=new_streak,
                growth_days=new_growth,
                total_days=new_total,
                gold=final_gold,
                runaway_recovery_progress=runaway_recovery_progress
            )

            if loading_message:
                try:
                    await loading_message.edit(embed=embed, content=None)
                except Exception as e:
                    self.logger.warning(f"[인증 완료] 로딩 메시지 편집 실패: {type(e).__name__}: {e}")
                    await ctx.send(embed=embed, delete_after=MESSAGE_DELETE_AFTER)
            else:
                await ctx.send(embed=embed, delete_after=MESSAGE_DELETE_AFTER)

            # ANSI HUD는 content-only 메시지로 분리해 렌더링 안정성 확보
            await ctx.send(content=ansi_hud, delete_after=MESSAGE_DELETE_AFTER)

            self.logger.info(f"[인증 완료] 사용자: {ctx.author.id}, 채널: {thread_id}, 메시지 ID: {ctx.message.id}")

    @commands.command(name='상태')
    async def status(self, ctx):
        """현재 오리 상태 및 인벤토리 확인"""
        upsert_user_profile(ctx.author.id, self._author_display_name(ctx.author))

        challenge = get_challenge(ctx.channel.id)
        if not challenge:
            embed = EmbedBuilder.error("도전 없음", "먼저 !목표설정으로 도전을 시작하세요.")
            await ctx.send(embed=embed, delete_after=MESSAGE_DELETE_AFTER)
            return

        # 레거시 상태(DUCK) 호환
        normalized_state = normalize_state(challenge['state'])
        if normalized_state != challenge['state']:
            update_challenge(ctx.channel.id, state=normalized_state)
            challenge['state'] = normalized_state

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
        current_gold = 0
        if user:
            from cogs.shop import SHOP_ITEMS

            inventory = safe_json_loads(user['inventory'])
            items_text = "\n".join([
                f"{SHOP_ITEMS[name]['emoji']} {name}: {count}개"
                for name, count in inventory.items() if name in SHOP_ITEMS
            ]) or "보유한 아이템이 없습니다."

            current_gold = user['gold']
            user_stats = f"💰 **골드:** {user['gold']}G\n🎓 **졸업한 오리:** {user['ducks_raised']}마리"
            embed.add_field(name="👤 내 정보", value=user_stats, inline=True)
            embed.add_field(name="🎒 인벤토리", value=items_text, inline=True)

        runaway_recovery_progress = None
        if challenge['state'] == BotStates.RUNAWAY:
            runaway_recovery_progress = f"{challenge['streak']}/{BotConfig.RUNAWAY_RECOVERY_DAYS}"

        ansi_hud = self._build_ansi_hud(
            state=challenge['state'],
            streak=challenge['streak'],
            growth_days=challenge['growth_days'],
            total_days=challenge['total_days'],
            gold=current_gold,
            runaway_recovery_progress=runaway_recovery_progress
        )

        await ctx.send(embed=embed, delete_after=MESSAGE_DELETE_AFTER)
        # ANSI HUD는 content-only 메시지로 분리해 렌더링 안정성 확보
        await ctx.send(content=ansi_hud, delete_after=MESSAGE_DELETE_AFTER)

    @commands.command(name='수정')
    async def edit_growth_day(self, ctx, *, day_text: str):
        """성장일 수정 (예: !수정 10일차)"""
        upsert_user_profile(ctx.author.id, self._author_display_name(ctx.author))

        if not isinstance(ctx.channel, discord.Thread):
            embed = EmbedBuilder.error("오류", "이 명령어는 도전 스레드에서만 사용 가능합니다.")
            await ctx.send(embed=embed, delete_after=MESSAGE_DELETE_AFTER)
            return

        challenge = get_challenge(ctx.channel.id)
        if not challenge:
            embed = EmbedBuilder.error("도전 없음", "먼저 !목표설정으로 도전을 시작하세요.")
            await ctx.send(embed=embed, delete_after=MESSAGE_DELETE_AFTER)
            return

        if not await self._check_ownership(ctx, challenge):
            return

        # 허용 형식: 10 / 10일 / 10일차 / 10일 차
        match = re.match(r'^\s*(\d+)\s*일?\s*차?\s*$', day_text)
        if not match:
            embed = EmbedBuilder.error(
                "형식 오류",
                "사용법: `!수정 10일차` 또는 `!수정 10일 차`"
            )
            await ctx.send(embed=embed, delete_after=MESSAGE_DELETE_AFTER)
            return

        new_growth_days = int(match.group(1))
        if new_growth_days < 0:
            embed = EmbedBuilder.error("입력 오류", "일차는 0 이상이어야 합니다.")
            await ctx.send(embed=embed, delete_after=MESSAGE_DELETE_AFTER)
            return
        if new_growth_days > 20:
            embed = EmbedBuilder.error("입력 오류", "수정 가능한 최대 일차는 20일차입니다.")
            await ctx.send(embed=embed, delete_after=MESSAGE_DELETE_AFTER)
            return

        old_growth_days = challenge['growth_days']
        old_state = normalize_state(challenge['state'])
        new_state = self._state_from_growth_days(new_growth_days)

        # total_days는 성장일보다 작으면 보정
        new_total_days = challenge['total_days']
        if new_total_days < new_growth_days:
            new_total_days = new_growth_days

        success = update_challenge(
            ctx.channel.id,
            state=new_state,
            growth_days=new_growth_days,
            total_days=new_total_days
        )
        if not success:
            embed = EmbedBuilder.error("수정 실패", "성장일 수정 중 오류가 발생했습니다.")
            await ctx.send(embed=embed, delete_after=MESSAGE_DELETE_AFTER)
            return

        record_challenge_event(
            user_id=ctx.author.id,
            thread_id=ctx.channel.id,
            event_type='USER_EDIT',
            before_challenge=challenge,
            after_challenge={
                **challenge,
                'state': new_state,
                'growth_days': new_growth_days,
                'total_days': new_total_days,
            },
            event_date=get_kst_now().date().isoformat(),
            source='BOT'
        )

        embed = EmbedBuilder.success(
            "수정 완료",
            (
                f"📅 성장일: D+{old_growth_days} → D+{new_growth_days}\n"
                f"🦆 상태: {STATE_KOREAN.get(old_state, old_state)} → {STATE_KOREAN.get(new_state, new_state)}"
            )
        )
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
`!수정 [일차]`: 성장일을 수정합니다. (최대 20일차, 예: `!수정 10일차`)
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
        challenge_owner = challenge.get('user_id') or ctx.channel.owner_id
        if ctx.author.id != challenge_owner:
            embed = EmbedBuilder.error(
                "권한 없음",
                "이 도전의 생성자만 인증할 수 있습니다."
            )
            await ctx.send(embed=embed, delete_after=MESSAGE_DELETE_AFTER)
            return False
        return True

# Cog 로드 함수
async def setup(bot):
    await bot.add_cog(ChallengeCog(bot))
