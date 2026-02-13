"""
Flask 대시보드 자동 모니터링 및 복구 Subagent

5분마다 Flask 서버의 헬스 체크를 수행하고,
문제 발생 시 자동으로 재시작하며 Discord 알림을 보냅니다.
"""

import discord
import asyncio
import logging
import os
import psutil
import requests
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional
from config import env_to_bool

logger = logging.getLogger(__name__)


class DashboardAdminAgent:
    """Flask 대시보드 자동 관리 Agent"""
    
    def __init__(self, bot, monitoring_channel_id: int):
        """
        Args:
            bot: Discord 봇 인스턴스
            monitoring_channel_id: 알림을 보낼 Discord 채널 ID
        """
        self.bot = bot
        self.monitoring_channel_id = monitoring_channel_id
        self.flask_pid_file = Path('.flask.pid')
        self.manage_flask_lifecycle = env_to_bool('MANAGE_FLASK_LIFECYCLE', False)
        
        # 모니터링 상태
        self.consecutive_failures = 0
        self.last_health_check = None
        self.health_check_interval = 300  # 5분 (초 단위)
        self.max_consecutive_failures = 3
        
        # 통계
        self.total_checks = 0
        self.total_failures = 0
        self.total_restarts = 0
        self.response_times = []
        
        # 일일 리포트
        self.daily_report_time = "00:00"  # 자정
        self.last_report_date = None
        
        self.monitoring_task = None

    def get_flask_url(self) -> str:
        """Flask 서버 URL 가져오기"""
        port = os.getenv('FLASK_PORT', '5001')
        return f'http://localhost:{port}'
    
    async def get_monitoring_channel(self) -> Optional[discord.TextChannel]:
        """모니터링 채널 가져오기"""
        try:
            channel = self.bot.get_channel(self.monitoring_channel_id)
            if not channel:
                channel = await self.bot.fetch_channel(self.monitoring_channel_id)
            return channel
        except Exception as e:
            logger.error(f"모니터링 채널 가져오기 실패: {e}")
            return None
    
    def get_flask_pid(self) -> Optional[int]:
        """Flask 서버 PID 가져오기"""
        if not self.flask_pid_file.exists():
            return None
        try:
            with open(self.flask_pid_file, 'r') as f:
                return int(f.read().strip())
        except (ValueError, OSError):
            return None
    
    def get_process_info(self, pid: int) -> Optional[dict]:
        """프로세스 정보 가져오기"""
        try:
            process = psutil.Process(pid)
            return {
                'pid': pid,
                'cpu': round(process.cpu_percent(interval=1), 2),
                'memory': round(process.memory_percent(), 2),
                'memory_mb': round(process.memory_info().rss / 1024 / 1024, 2),
                'status': process.status(),
                'running': process.is_running()
            }
        except psutil.NoSuchProcess:
            return None
    
    def check_http_response(self, url=None, timeout=5) -> tuple:
        """
        HTTP 응답 확인
        
        Args:
            url: 확인할 URL (None이면 get_flask_url() 사용)
            timeout: 타임아웃 (초)
        
        Returns:
            (success: bool, status_code: int, response_time: float)
        """
        if url is None:
            url = self.get_flask_url()
            
        try:
            start_time = datetime.now()
            response = requests.get(url, timeout=timeout)
            response_time = (datetime.now() - start_time).total_seconds()
            
            success = response.status_code in [200, 302]
            return (success, response.status_code, response_time)
        except requests.RequestException as e:
            logger.warning(f"HTTP 요청 실패: {e}")
            return (False, None, None)
    
    async def perform_health_check(self) -> bool:
        """
        헬스 체크 수행
        
        Returns:
            bool: 정상 여부
        """
        self.total_checks += 1
        self.last_health_check = datetime.now()
        
        # 1. PID 확인
        pid = self.get_flask_pid()
        process_info = None
        if not pid:
            logger.info("Flask 서버 PID 파일이 없습니다. HTTP 기반 외부 프로세스 상태를 확인합니다.")
        else:
            # 2. 프로세스 확인
            process_info = self.get_process_info(pid)
            if not process_info or not process_info['running']:
                logger.warning(f"Flask 서버 프로세스가 실행 중이지 않습니다 (PID: {pid}).")
                self.total_failures += 1
                return False

        # 3. HTTP 응답 확인 (PID 유무와 무관)
        success, status_code, response_time = self.check_http_response()
        if not success:
            logger.warning("Flask 서버가 HTTP 응답하지 않습니다.")
            self.total_failures += 1
            return False
        
        # 응답 시간 기록
        if response_time:
            self.response_times.append(response_time)
            # 최근 100개만 유지
            if len(self.response_times) > 100:
                self.response_times = self.response_times[-100:]
        
        # 4. 리소스 경고
        channel = await self.get_monitoring_channel()
        if channel and process_info:
            if process_info['cpu'] > 80:
                await self.send_warning(
                    channel,
                    "CPU 사용률 높음",
                    f"Flask 서버의 CPU 사용률이 {process_info['cpu']}%입니다."
                )
            
            if process_info['memory'] > 80:
                await self.send_warning(
                    channel,
                    "메모리 사용률 높음",
                    f"Flask 서버의 메모리 사용률이 {process_info['memory']}%입니다."
                )
            
            if response_time and response_time > 5:
                await self.send_warning(
                    channel,
                    "응답 시간 지연",
                    f"Flask 서버의 응답 시간이 {response_time:.2f}초입니다."
                )
        
        return True
    
    async def auto_restart(self) -> bool:
        """Flask 서버 자동 재시작"""
        if not self.manage_flask_lifecycle:
            logger.warning("MANAGE_FLASK_LIFECYCLE=False: 자동 재시작을 건너뜁니다.")
            return False

        logger.info("Flask 서버 자동 재시작 시도 중...")
        
        from hooks import flask_lifecycle
        
        # 서버 중지
        pid = self.get_flask_pid()
        if pid:
            flask_lifecycle.stop_flask_server()
            await asyncio.sleep(2)
        
        # 서버 시작
        success = flask_lifecycle.start_flask_server()
        
        if success:
            self.total_restarts += 1
            logger.info("✅ Flask 서버 자동 재시작 성공")
            return True
        else:
            logger.error("❌ Flask 서버 자동 재시작 실패")
            return False
    
    async def send_error(self, channel: discord.TextChannel, title: str, description: str):
        """에러 알림 전송"""
        embed = discord.Embed(
            title=f"❌ {title}",
            description=description,
            color=discord.Color.red(),
            timestamp=datetime.now()
        )
        await channel.send(embed=embed)
    
    async def send_warning(self, channel: discord.TextChannel, title: str, description: str):
        """경고 알림 전송"""
        embed = discord.Embed(
            title=f"⚠️ {title}",
            description=description,
            color=discord.Color.orange(),
            timestamp=datetime.now()
        )
        await channel.send(embed=embed)
    
    async def send_success(self, channel: discord.TextChannel, title: str, description: str):
        """성공 알림 전송"""
        embed = discord.Embed(
            title=f"✅ {title}",
            description=description,
            color=discord.Color.green(),
            timestamp=datetime.now()
        )
        await channel.send(embed=embed)
    
    async def monitoring_loop(self):
        """모니터링 루프"""
        await self.bot.wait_until_ready()
        logger.info("🔍 Flask 서버 모니터링 시작")
        
        while not self.bot.is_closed():
            try:
                # 헬스 체크 수행
                is_healthy = await self.perform_health_check()
                
                channel = await self.get_monitoring_channel()
                
                if is_healthy:
                    # 정상 - 연속 실패 카운트 초기화
                    if self.consecutive_failures > 0:
                        self.consecutive_failures = 0
                        if channel:
                            await self.send_success(
                                channel,
                                "Flask 서버 복구",
                                "Flask 서버가 정상적으로 응답하고 있습니다."
                            )
                else:
                    # 실패 - 연속 실패 카운트 증가
                    self.consecutive_failures += 1
                    logger.warning(f"헬스 체크 실패 ({self.consecutive_failures}/{self.max_consecutive_failures})")
                    
                    if self.consecutive_failures >= self.max_consecutive_failures:
                        # 자동 재시작
                        if channel:
                            await self.send_error(
                                channel,
                                "Flask 서버 다운",
                                f"Flask 서버가 {self.max_consecutive_failures}회 연속 헬스 체크에 실패했습니다.\n"
                                "자동 재시작을 시도합니다..."
                            )
                        
                        restart_success = await self.auto_restart()
                        
                        if restart_success:
                            if channel:
                                await self.send_success(
                                    channel,
                                    "Flask 서버 재시작 성공",
                                    f"Flask 서버가 자동으로 재시작되었습니다.\n"
                                    f"🌐 {self.get_flask_url()}"
                                )
                            self.consecutive_failures = 0
                        else:
                            if channel:
                                await self.send_error(
                                    channel,
                                    "Flask 서버 재시작 실패",
                                    "Flask 서버 자동 재시작에 실패했습니다.\n"
                                    "로그를 확인하고 수동으로 재시작하세요."
                                )
                
                # 일일 리포트
                await self.check_daily_report()
                
            except Exception as e:
                logger.error(f"모니터링 루프 에러: {e}", exc_info=True)
            
            # 다음 체크까지 대기
            await asyncio.sleep(self.health_check_interval)
    
    async def check_daily_report(self):
        """일일 리포트 확인 및 전송"""
        now = datetime.now()
        today = now.date()
        
        # 자정이 지났고 아직 오늘 리포트를 보내지 않았으면
        if self.last_report_date != today and now.hour == 0:
            await self.send_daily_report()
            self.last_report_date = today
    
    async def send_daily_report(self):
        """일일 리포트 전송"""
        channel = await self.get_monitoring_channel()
        if not channel:
            return
        
        # 평균 응답 시간 계산
        avg_response_time = 0
        if self.response_times:
            avg_response_time = sum(self.response_times) / len(self.response_times)
        
        # 가동 시간 계산
        pid = self.get_flask_pid()
        uptime_str = "알 수 없음"
        if pid:
            process_info = self.get_process_info(pid)
            if process_info:
                try:
                    process = psutil.Process(pid)
                    create_time = datetime.fromtimestamp(process.create_time())
                    uptime = datetime.now() - create_time
                    uptime_str = str(uptime).split('.')[0]  # 소수점 제거
                except:
                    pass
        
        embed = discord.Embed(
            title="📊 Flask 서버 일일 리포트",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        embed.add_field(name="총 헬스 체크", value=str(self.total_checks), inline=True)
        embed.add_field(name="실패 횟수", value=str(self.total_failures), inline=True)
        embed.add_field(name="자동 재시작", value=str(self.total_restarts), inline=True)
        
        if self.total_checks > 0:
            success_rate = ((self.total_checks - self.total_failures) / self.total_checks) * 100
            embed.add_field(name="성공률", value=f"{success_rate:.1f}%", inline=True)
        
        embed.add_field(
            name="평균 응답 시간",
            value=f"{avg_response_time:.3f}초" if avg_response_time > 0 else "데이터 없음",
            inline=True
        )
        
        embed.add_field(name="가동 시간", value=uptime_str, inline=True)
        
        await channel.send(embed=embed)
        
        # 통계 초기화 (옵션)
        # self.total_checks = 0
        # self.total_failures = 0
        # self.total_restarts = 0
        # self.response_times = []
    
    async def start_monitoring(self):
        """모니터링 시작"""
        if self.monitoring_task and not self.monitoring_task.done():
            logger.warning("모니터링이 이미 실행 중입니다.")
            return
        
        self.monitoring_task = self.bot.loop.create_task(self.monitoring_loop())
        logger.info("🚀 Flask 서버 모니터링 Agent 시작됨")
    
    async def stop_monitoring(self):
        """모니터링 중지"""
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
            logger.info("🛑 Flask 서버 모니터링 Agent 중지됨")
