"""
리더보드 시스템 Cog
서버 내 레벨 순위 표시 기능
"""

import discord
from discord.ext import commands
from discord import app_commands
import logging

from utils.config import Config
from utils.helpers import create_embed, format_number

logger = logging.getLogger(__name__)

class LeaderboardCog(commands.Cog):
    """리더보드 시스템"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="리더보드", description="서버 레벨 순위를 확인합니다")
    async def leaderboard(self, interaction: discord.Interaction):
        """리더보드 표시"""
        await interaction.response.defer()
        
        # 리더보드 데이터 조회
        leaderboard_data = await self.bot.db.get_leaderboard(interaction.guild.id, 10)
        
        if not leaderboard_data:
            embed = create_embed(
                "📊 리더보드",
                "아직 레벨 데이터가 없습니다.\n`/ㅊㅊ` 명령어로 출석 체크를 시작해보세요!",
                Config.COLORS['warning']
            )
            await interaction.followup.send(embed=embed)
            return
        
        # 임베드 생성
        embed = discord.Embed(
            title="🏆 서버 레벨 리더보드",
            description="상위 10명의 레벨 순위",
            color=Config.COLORS['info']
        )
        
        # 순위별 이모지
        rank_emojis = {
            1: "🥇",
            2: "🥈", 
            3: "🥉"
        }
        
        leaderboard_text = ""
        
        for rank, user_data in enumerate(leaderboard_data, 1):
            user_id = user_data['user_id']
            xp = user_data['xp']
            
            # XP를 기반으로 레벨 계산
            level = Config.calculate_level_from_xp(xp)
            
            # 서버 멤버 정보 가져오기 (서버 닉네임 사용)
            try:
                member = interaction.guild.get_member(user_id)
                if member:
                    username = member.display_name  # 서버 닉네임 우선
                else:
                    # 서버에 없는 경우 일반 유저 정보로 fallback
                    user = await self.bot.fetch_user(user_id)
                    username = user.display_name
            except Exception:
                username = f"User {user_id}"
            
            # 순위 이모지
            rank_emoji = rank_emojis.get(rank, f"{rank}️⃣")
            
            leaderboard_text += f"{rank_emoji} **{username}**\n"
            leaderboard_text += f"     Level {level} | {format_number(xp)} XP\n\n"
        
        embed.description = leaderboard_text
        embed.set_footer(text="Siri Bot • 매일 출석체크로 레벨업!")
        
        await interaction.followup.send(embed=embed)

async def setup(bot):
    """Cog 로드"""
    await bot.add_cog(LeaderboardCog(bot))
