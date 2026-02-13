"""
Flask 서버 관리 Discord Skill (Cog)

Discord 명령어로 Flask 서버를 제어하고 상태를 모니터링합니다.
관리자 권한이 있는 사용자만 사용할 수 있습니다.
"""

import discord
from discord.ext import commands
import psutil
import os
import signal
import logging
import requests
from pathlib import Path

logger = logging.getLogger(__name__)


class FlaskAdmin(commands.Cog):
    """Flask 서버 관리 명령어"""
    
    def __init__(self, bot):
        self.bot = bot
        self.flask_pid_file = Path('.flask.pid')

    def get_flask_url(self) -> str:
        """Flask 서버 URL 가져오기"""
        port = os.getenv('FLASK_PORT', '5001')
        return f'http://localhost:{port}'
    
    def is_admin(self, ctx):
        """관리자 권한 확인"""
        return ctx.author.guild_permissions.administrator
    
    def get_flask_pid(self):
        """Flask 서버 PID 가져오기"""
        if not self.flask_pid_file.exists():
            return None
        try:
            with open(self.flask_pid_file, 'r') as f:
                return int(f.read().strip())
        except (ValueError, OSError):
            return None
    
    def get_process_info(self, pid):
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
    
    def check_http_response(self, url=None, timeout=5) -> bool:
        """HTTP 응답 확인"""
        if url is None:
            url = self.get_flask_url()
        try:
            response = requests.get(url, timeout=timeout)
            return response.status_code in [200, 302]
        except:
            return False
    
    @commands.group(name='admin', invoke_without_command=True)
    async def admin(self, ctx):
        """Flask 서버 관리 명령어"""
        if not self.is_admin(ctx):
            await ctx.send("❌ 관리자 권한이 필요합니다.", delete_after=10)
            return
        
        await ctx.send(
            "**Flask 서버 관리 명령어**\n"
            "`!admin start` - 서버 시작\n"
            "`!admin stop` - 서버 중지\n"
            "`!admin restart` - 서버 재시작\n"
            "`!admin status` - 상태 조회\n"
            "`!admin logs [줄수]` - 로그 조회 (기본 50줄)\n"
            "`!admin validate` - 환경 변수 검증"
        )
    
    @admin.command(name='start')
    async def start_server(self, ctx):
        """Flask 서버 시작"""
        if not self.is_admin(ctx):
            await ctx.send("❌ 관리자 권한이 필요합니다.", delete_after=10)
            return

        if self.check_http_response():
            await ctx.send(f"⚠️ Flask 서버가 이미 응답 중입니다.\n🌐 {self.get_flask_url()}")
            return
        
        pid = self.get_flask_pid()
        if pid and self.get_process_info(pid):
            await ctx.send(f"⚠️ Flask 서버가 이미 실행 중입니다 (PID: {pid}).")
            return
        
        await ctx.send("🔧 Flask 서버 시작 중...")
        
        # Hook 사용하여 서버 시작
        from hooks import flask_lifecycle
        success = flask_lifecycle.start_flask_server()
        
        if success:
            await ctx.send(f"✅ Flask 서버가 시작되었습니다!\n🌐 {self.get_flask_url()}")
        else:
            await ctx.send("❌ Flask 서버 시작 실패. 로그를 확인하세요.")
    
    @admin.command(name='stop')
    async def stop_server(self, ctx):
        """Flask 서버 중지"""
        if not self.is_admin(ctx):
            await ctx.send("❌ 관리자 권한이 필요합니다.", delete_after=10)
            return
        
        pid = self.get_flask_pid()
        if not pid:
            if self.check_http_response():
                await ctx.send("⚠️ Flask 서버가 외부 프로세스로 실행 중입니다. (PID 파일 없음)\n수동/systemd로 중지하세요.")
            else:
                await ctx.send("⚠️ Flask 서버가 실행 중이지 않습니다.")
            return
        
        await ctx.send("🛑 Flask 서버 중지 중...")
        
        # Hook 사용하여 서버 중지
        from hooks import flask_lifecycle
        success = flask_lifecycle.stop_flask_server()
        
        if success:
            await ctx.send("✅ Flask 서버가 중지되었습니다.")
        else:
            await ctx.send("❌ Flask 서버 중지 실패. 로그를 확인하세요.")
    
    @admin.command(name='restart')
    async def restart_server(self, ctx):
        """Flask 서버 재시작"""
        if not self.is_admin(ctx):
            await ctx.send("❌ 관리자 권한이 필요합니다.", delete_after=10)
            return
        
        await ctx.send("🔄 Flask 서버 재시작 중...")
        
        from hooks import flask_lifecycle
        
        pid = self.get_flask_pid()
        if not pid and self.check_http_response():
            await ctx.send("⚠️ Flask 서버가 외부 프로세스로 실행 중입니다. (PID 파일 없음)\n수동/systemd로 재시작하세요.")
            return

        # 서버 중지
        if pid:
            flask_lifecycle.stop_flask_server()
            await ctx.send("✅ 서버 중지 완료")
        
        # 서버 시작
        success = flask_lifecycle.start_flask_server()
        
        if success:
            await ctx.send(f"✅ Flask 서버가 재시작되었습니다!\n🌐 {self.get_flask_url()}")
        else:
            await ctx.send("❌ Flask 서버 재시작 실패. 로그를 확인하세요.")
    
    @admin.command(name='status')
    async def server_status(self, ctx):
        """Flask 서버 상태 조회"""
        if not self.is_admin(ctx):
            await ctx.send("❌ 관리자 권한이 필요합니다.", delete_after=10)
            return
        
        pid = self.get_flask_pid()
        
        # Embed 생성
        embed = discord.Embed(title="🌐 Flask 서버 상태", color=discord.Color.blue())
        
        if not pid:
            http_status = self.check_http_response()
            if http_status:
                embed.color = discord.Color.gold()
                embed.add_field(name="상태", value="⚠️ 실행 중 (외부 프로세스)", inline=False)
                embed.add_field(name="PID", value="추적 불가 (.flask.pid 없음)", inline=False)
                embed.add_field(
                    name="접속 링크",
                    value=f"[{self.get_flask_url()}]({self.get_flask_url()})",
                    inline=False
                )
            else:
                embed.color = discord.Color.red()
                embed.add_field(name="상태", value="❌ 중지됨", inline=False)
            await ctx.send(embed=embed)
            return
        
        # 프로세스 정보 가져오기
        process_info = self.get_process_info(pid)
        
        if not process_info or not process_info['running']:
            embed.color = discord.Color.red()
            embed.add_field(name="상태", value="❌ 중지됨 (PID 파일만 존재)", inline=False)
            # PID 파일 정리
            self.flask_pid_file.unlink(missing_ok=True)
            await ctx.send(embed=embed)
            return
        
        # 정상 실행 중
        embed.color = discord.Color.green()
        embed.add_field(name="상태", value="✅ 실행 중", inline=True)
        embed.add_field(name="PID", value=str(pid), inline=True)
        embed.add_field(name="프로세스 상태", value=process_info['status'], inline=True)
        embed.add_field(name="CPU 사용률", value=f"{process_info['cpu']}%", inline=True)
        embed.add_field(name="메모리 사용률", value=f"{process_info['memory']}%", inline=True)
        embed.add_field(name="메모리 사용량", value=f"{process_info['memory_mb']} MB", inline=True)
        
        # HTTP 응답 확인
        http_status = self.check_http_response()
        if http_status:
            embed.add_field(
                name="HTTP 응답",
                value=f"✅ {http_status}",
                inline=True
            )
            embed.add_field(
                name="접속 링크",
                value=f"[{self.get_flask_url()}]({self.get_flask_url()})",
                inline=True
            )
        else:
            embed.add_field(
                name="HTTP 응답",
                value="❌ 응답 없음",
                inline=True
            )
        
        await ctx.send(embed=embed)
    
    @admin.command(name='logs')
    async def view_logs(self, ctx, lines: int = 50):
        """Flask 로그 조회"""
        if not self.is_admin(ctx):
            await ctx.send("❌ 관리자 권한이 필요합니다.", delete_after=10)
            return
        
        log_file = Path('logs/flask.log')
        
        if not log_file.exists():
            await ctx.send("❌ 로그 파일이 존재하지 않습니다.")
            return
        
        try:
            # 마지막 N줄 읽기
            with open(log_file, 'r', encoding='utf-8') as f:
                all_lines = f.readlines()
                last_lines = all_lines[-lines:]
            
            log_content = ''.join(last_lines)
            
            # Discord 메시지 길이 제한 (2000자)
            if len(log_content) > 1900:
                log_content = log_content[-1900:]
                log_content = "...(생략)\n" + log_content
            
            await ctx.send(f"**Flask 로그 (최근 {len(last_lines)}줄)**\n```\n{log_content}\n```")
        
        except Exception as e:
            await ctx.send(f"❌ 로그 읽기 실패: {e}")
    
    @admin.command(name='validate')
    async def validate_env(self, ctx):
        """환경 변수 검증"""
        if not self.is_admin(ctx):
            await ctx.send("❌ 관리자 권한이 필요합니다.", delete_after=10)
            return
        
        embed = discord.Embed(title="🔍 환경 변수 검증", color=discord.Color.blue())
        
        # ADMIN_PASSWORD 확인
        admin_password = os.getenv('ADMIN_PASSWORD')
        if not admin_password or admin_password == 'your_secure_password_here':
            embed.add_field(
                name="ADMIN_PASSWORD",
                value="❌ 설정되지 않음",
                inline=False
            )
        elif admin_password == 'admin1234':
            embed.add_field(
                name="ADMIN_PASSWORD",
                value="⚠️ 기본값 사용 (보안 취약)",
                inline=False
            )
        elif len(admin_password) < 8:
            embed.add_field(
                name="ADMIN_PASSWORD",
                value=f"⚠️ 너무 짧음 ({len(admin_password)}자, 8자 이상 권장)",
                inline=False
            )
        else:
            embed.add_field(
                name="ADMIN_PASSWORD",
                value=f"✅ 설정됨 ({len(admin_password)}자)",
                inline=False
            )
        
        # FLASK_SECRET_KEY 확인
        flask_secret = os.getenv('FLASK_SECRET_KEY')
        if not flask_secret or flask_secret == 'your-random-secret-key-here':
            embed.add_field(
                name="FLASK_SECRET_KEY",
                value="❌ 설정되지 않음",
                inline=False
            )
        elif len(flask_secret) < 32:
            embed.add_field(
                name="FLASK_SECRET_KEY",
                value=f"⚠️ 너무 짧음 ({len(flask_secret)}자, 32자 이상 권장)",
                inline=False
            )
        else:
            embed.add_field(
                name="FLASK_SECRET_KEY",
                value=f"✅ 설정됨 ({len(flask_secret)}자)",
                inline=False
            )
        
        # DB_PATH 확인
        db_path = os.getenv('DB_PATH', 'data/bot.db')
        embed.add_field(
            name="DB_PATH",
            value=f"✅ {db_path}",
            inline=False
        )
        
        await ctx.send(embed=embed)


async def setup(bot):
    """Cog 설정"""
    await bot.add_cog(FlaskAdmin(bot))
