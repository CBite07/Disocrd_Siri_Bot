"""
Siri Bot 음악 인터페이스 Cog
GPT 봇에게 음악 재생 명령을 전달하는 인터페이스 역할

작성일: 2025년 1월 15일
"""

import logging
import discord
from discord.ext import commands
from discord import app_commands

from utils.gpt_client import gpt_client
from utils.helpers import create_error_embed

logger = logging.getLogger('cogs.siri_music')


class SiriMusicCog(commands.Cog):
    """Siri 봇 음악 인터페이스 - GPT 봇에게 명령 전달"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="재생", description="GPT 봇을 통해 유튜브 음악을 재생합니다")
    @app_commands.describe(검색어="유튜브 URL 또는 검색할 곡 이름")
    async def play_music(self, interaction: discord.Interaction, 검색어: str):
        """음악 재생 명령어 - GPT 봇에게 전달"""
        await interaction.response.defer()
        
        # 사용자가 음성 채널에 있는지 확인
        if not interaction.user.voice or not interaction.user.voice.channel:
            embed = create_error_embed(
                "음성 채널에 먼저 접속해주세요!",
                "음악을 재생하려면 음성 채널에 입장해야 합니다."
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        # GPT 봇 상태 확인
        is_ready = await gpt_client.health_check()
        if not is_ready:
            embed = create_error_embed(
                "GPT 봇을 사용할 수 없습니다",
                "GPT 봇이 실행 중이 아니거나 준비되지 않았습니다.\n관리자에게 문의하세요."
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        # 로딩 메시지
        loading_embed = discord.Embed(
            title="🎵 음악 재생 요청 중...",
            description=f"**검색어:** {검색어}\n**요청자:** {interaction.user.mention}",
            color=discord.Color.blue()
        )
        loading_embed.set_footer(text="GPT 봇에게 명령을 전달하는 중입니다...")
        loading_msg = await interaction.followup.send(embed=loading_embed)
        
        # GPT 봇에게 재생 요청
        result = await gpt_client.play_music(
            query=검색어,
            guild_id=interaction.guild.id,
            channel_id=interaction.user.voice.channel.id,
            user=str(interaction.user)
        )
        
        # 결과 처리
        if result.get("status") == "playing":
            # 성공
            success_embed = discord.Embed(
                title="🎵 재생 중",
                description=f"**{result.get('song', '알 수 없음')}**",
                color=discord.Color.green()
            )
            
            if result.get('uploader'):
                success_embed.add_field(
                    name="채널",
                    value=result['uploader'],
                    inline=True
                )
            
            success_embed.add_field(
                name="요청자",
                value=interaction.user.mention,
                inline=True
            )
            
            if result.get('thumbnail'):
                success_embed.set_thumbnail(url=result['thumbnail'])
            
            success_embed.set_footer(text="GPT 봇이 음악을 재생하고 있습니다")
            
            await loading_msg.edit(embed=success_embed)
            
        elif result.get("status") == "error":
            # 오류
            error_embed = create_error_embed(
                "재생 실패",
                result.get("message", "알 수 없는 오류가 발생했습니다.")
            )
            await loading_msg.edit(embed=error_embed)
        else:
            # 예상치 못한 응답
            error_embed = create_error_embed(
                "예상치 못한 응답",
                f"GPT 봇으로부터 알 수 없는 응답을 받았습니다.\n{result}"
            )
            await loading_msg.edit(embed=error_embed)
    
    @app_commands.command(name="정지", description="GPT 봇의 음악 재생을 정지합니다")
    async def stop_music(self, interaction: discord.Interaction):
        """음악 정지 명령어"""
        await interaction.response.defer(ephemeral=True)
        
        # GPT 봇에게 정지 요청
        result = await gpt_client.stop_music(interaction.guild.id)
        
        if result.get("status") == "stopped":
            await interaction.followup.send("⏹️ GPT 봇의 재생을 정지했습니다.", ephemeral=True)
        else:
            await interaction.followup.send(
                f"❌ 정지 실패: {result.get('message', '알 수 없는 오류')}",
                ephemeral=True
            )


async def setup(bot):
    """Cog 로드"""
    await bot.add_cog(SiriMusicCog(bot))
    logger.info("Siri 음악 인터페이스 로드 완료")
