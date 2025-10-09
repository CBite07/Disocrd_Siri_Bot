"""
디버그 및 개발자 도구 Cog
명령어 확인 및 봇 상태 점검용
"""

import discord
from discord.ext import commands
from discord import app_commands
import logging

logger = logging.getLogger(__name__)

class DebugCog(commands.Cog):
    """디버그 및 개발자 도구"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="명령어목록", description="등록된 모든 명령어를 확인합니다 (개발자용)")
    async def list_commands(self, interaction: discord.Interaction):
        """등록된 모든 슬래시 명령어 목록 표시"""
        
        # 봇 소유자나 관리자만 사용 가능하도록 제한
        if not (interaction.user.guild_permissions.administrator or 
                interaction.user.id == 442959929900326913):  # 봇 소유자 ID
            await interaction.response.send_message(
                "❌ 이 명령어는 관리자만 사용할 수 있습니다.", 
                ephemeral=True
            )
            return
        
        embed = discord.Embed(
            title="🔧 등록된 슬래시 명령어 목록",
            color=0x3498db
        )
        
        # 각 Cog별로 명령어 정리
        command_list = {}
        
        for command in self.bot.tree.get_commands():
            # Cog 이름 찾기
            cog_name = "기타"
            if hasattr(command, 'callback') and hasattr(command.callback, '__self__'):
                cog_name = command.callback.__self__.__class__.__name__
            
            if cog_name not in command_list:
                command_list[cog_name] = []
            
            command_list[cog_name].append({
                'name': command.name,
                'description': command.description
            })
        
        # 임베드에 추가
        for cog_name, cmd_list in command_list.items():
            if cmd_list:
                command_text = "\n".join([
                    f"`/{cmd['name']}` - {cmd['description']}" 
                    for cmd in cmd_list
                ])
                embed.add_field(
                    name=f"📂 {cog_name}",
                    value=command_text,
                    inline=False
                )
        
        embed.add_field(
            name="📊 통계",
            value=f"총 {len([cmd for cmd_list in command_list.values() for cmd in cmd_list])}개 명령어",
            inline=True
        )
        
        embed.set_footer(text="Siri Bot Debug Tool")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="상태", description="봇의 현재 상태를 확인합니다 (개발자용)")
    async def status_check(self, interaction: discord.Interaction):
        """봇 상태 확인"""
        
        if not (interaction.user.guild_permissions.administrator or 
                interaction.user.id == 442959929900326913):
            await interaction.response.send_message(
                "❌ 이 명령어는 관리자만 사용할 수 있습니다.", 
                ephemeral=True
            )
            return
        
        embed = discord.Embed(
            title="🤖 Siri Bot 상태",
            color=0x00ff00
        )
        
        # 기본 정보
        embed.add_field(
            name="📊 기본 정보",
            value=f"• 서버 수: {len(self.bot.guilds)}개\n"
                  f"• 사용자 수: {len(set(self.bot.get_all_members()))}명\n"
                  f"• 지연시간: {round(self.bot.latency * 1000)}ms",
            inline=True
        )
        
        # Cog 정보
        cog_list = [cog for cog in self.bot.cogs.keys()]
        embed.add_field(
            name="🔧 로드된 Cogs",
            value="\n".join([f"• {cog}" for cog in cog_list]) if cog_list else "없음",
            inline=True
        )
        
        # 명령어 수
        command_count = len(self.bot.tree.get_commands())
        embed.add_field(
            name="⚡ 슬래시 명령어",
            value=f"{command_count}개 등록됨",
            inline=True
        )
        
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        embed.set_footer(text=f"봇 ID: {self.bot.user.id}")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    """Cog 로드"""
    await bot.add_cog(DebugCog(bot))
