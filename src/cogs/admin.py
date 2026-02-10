import discord
from discord.ext import commands
import logging

class AdminCog(commands.Cog):
    """관리자 전용 명령어"""

    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger(__name__)

    @commands.command(name='reload')
    @commands.is_owner()  # 봇 소유자만 실행 가능
    async def reload_cog(self, ctx, cog_name: str):
        """Cog 다시 로드 (봇 재시작 없이)
        
        사용법: !reload challenge
        """
        try:
            # cogs. 접두사가 없으면 추가
            if not cog_name.startswith('cogs.'):
                extension_name = f'cogs.{cog_name}'
            else:
                extension_name = cog_name
            
            await self.bot.reload_extension(extension_name)
            self.logger.info(f'[Admin] {extension_name} Cog이 다시 로드되었습니다. (명령 실행자: {ctx.author})')
            await ctx.send(f'✅ `{extension_name}` Cog이 다시 로드되었습니다.')
        except commands.ExtensionNotLoaded:
            await ctx.send(f'❌ `{extension_name}` Cog이 로드되어 있지 않습니다.')
        except commands.ExtensionNotFound:
            await ctx.send(f'❌ `{extension_name}` Cog을 찾을 수 없습니다.')
        except Exception as e:
            self.logger.error(f'[Admin] Cog 로드 실패: {extension_name} - {e}', exc_info=True)
            await ctx.send(f'❌ 로드 실패: {e}')

    @commands.command(name='load')
    @commands.is_owner()
    async def load_cog(self, ctx, cog_name: str):
        """새로운 Cog 로드
        
        사용법: !load shop
        """
        try:
            if not cog_name.startswith('cogs.'):
                extension_name = f'cogs.{cog_name}'
            else:
                extension_name = cog_name
                
            await self.bot.load_extension(extension_name)
            self.logger.info(f'[Admin] {extension_name} Cog이 로드되었습니다. (명령 실행자: {ctx.author})')
            await ctx.send(f'✅ `{extension_name}` Cog이 로드되었습니다.')
        except commands.ExtensionAlreadyLoaded:
            await ctx.send(f'❌ `{extension_name}` Cog이 이미 로드되어 있습니다.')
        except commands.ExtensionNotFound:
            await ctx.send(f'❌ `{extension_name}` Cog을 찾을 수 없습니다.')
        except Exception as e:
            self.logger.error(f'[Admin] Cog 로드 실패: {extension_name} - {e}', exc_info=True)
            await ctx.send(f'❌ 로드 실패: {e}')

    @commands.command(name='unload')
    @commands.is_owner()
    async def unload_cog(self, ctx, cog_name: str):
        """Cog 언로드
        
        사용법: !unload challenge
        """
        try:
            if not cog_name.startswith('cogs.'):
                extension_name = f'cogs.{cog_name}'
            else:
                extension_name = cog_name
                
            await self.bot.unload_extension(extension_name)
            self.logger.info(f'[Admin] {extension_name} Cog이 언로드되었습니다. (명령 실행자: {ctx.author})')
            await ctx.send(f'✅ `{extension_name}` Cog이 언로드되었습니다.')
        except commands.ExtensionNotLoaded:
            await ctx.send(f'❌ `{extension_name}` Cog이 로드되어 있지 않습니다.')
        except Exception as e:
            self.logger.error(f'[Admin] Cog 언로드 실패: {extension_name} - {e}', exc_info=True)
            await ctx.send(f'❌ 언로드 실패: {e}')

    @commands.command(name='cogs')
    @commands.is_owner()
    async def list_cogs(self, ctx):
        """로드된 모든 Cog 목록 표시"""
        cogs = [ext for ext in self.bot.extensions.keys()]
        
        if cogs:
            cog_list = '\n'.join([f'• `{cog}`' for cog in cogs])
            embed = discord.Embed(
                title='📦 로드된 Cog 목록',
                description=cog_list,
                color=discord.Color.blue()
            )
            embed.set_footer(text=f'총 {len(cogs)}개의 Cog')
            await ctx.send(embed=embed)
        else:
            await ctx.send('❌ 로드된 Cog이 없습니다.')

async def setup(bot):
    await bot.add_cog(AdminCog(bot))
