"""
공지 및 규칙 시스템 Cog
관리자용 메시지 게시 기능
"""

import discord
from discord.ext import commands
from discord import app_commands
import json
import logging
from pathlib import Path
from typing import Optional

from utils.config import Config
from utils.helpers import create_success_embed, create_error_embed, has_admin_permissions

logger = logging.getLogger(__name__)

class AnnouncementCog(commands.Cog):
    """공지 및 규칙 시스템"""
    
    def __init__(self, bot):
        self.bot = bot
        self.rules_file_path = Path("./data/rules.json")
    
    def load_rules_from_json(self) -> dict:
        """JSON 파일에서 규칙 데이터 로드"""
        try:
            if self.rules_file_path.exists():
                with open(self.rules_file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                # 기본 규칙 데이터 (파일이 없을 경우)
                logger.warning(f"규칙 파일 {self.rules_file_path}를 찾을 수 없음. 기본 규칙 사용")
                return {
                    "title": "📋 서버 규칙",
                    "color": Config.COLORS['info'],
                    "rules": ["규칙 파일이 없습니다. 관리자에게 문의하세요."],
                    "footer": "Siri Bot"
                }
        except Exception as e:
            logger.error(f"규칙 파일 로드 실패: {e}")
            return {
                "title": "📋 서버 규칙",
                "color": Config.COLORS['error'],
                "rules": ["규칙을 불러올 수 없습니다. 관리자에게 문의하세요."],
                "footer": "Siri Bot - 오류 발생"
            }
    
    @app_commands.command(name="공지", description="공지사항을 게시합니다 (관리자 전용)")
    @app_commands.describe(
        제목="공지사항 제목",
        내용="공지사항 내용",
        채널="공지를 게시할 채널 (선택사항)"
    )
    async def announce(
        self, 
        interaction: discord.Interaction, 
        제목: str, 
        내용: str,
        채널: Optional[discord.TextChannel] = None
    ):
        """공지사항 게시"""
        # 관리자 권한 확인
        if not await has_admin_permissions(interaction.user):
            embed = create_error_embed(
                "❌ 권한 없음",
                "이 명령어는 관리자만 사용할 수 있습니다."
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        await interaction.response.defer()
        
        # 채널 설정 (지정하지 않으면 현재 채널)
        target_channel = 채널 or interaction.channel
        
        # 기존 봇 메시지 삭제 (같은 채널에서)
        await self.delete_bot_messages(target_channel)
        
        # 공지 임베드 생성
        embed = discord.Embed(
            title=f"📢 {제목}",
            description=내용,
            color=Config.COLORS['info']
        )
        
        embed.set_footer(text=f"작성자: {interaction.user.display_name} | Siri Bot")
        embed.timestamp = discord.utils.utcnow()
        
        try:
            # 공지 메시지 전송
            await target_channel.send(embed=embed)
            
            # 성공 메시지
            success_embed = create_success_embed(
                "✅ 공지 게시 완료",
                f"{target_channel.mention} 채널에 공지가 게시되었습니다."
            )
            await interaction.followup.send(embed=success_embed, ephemeral=True)
            
        except discord.Forbidden:
            error_embed = create_error_embed(
                "❌ 권한 부족",
                f"{target_channel.mention} 채널에 메시지를 보낼 권한이 없습니다."
            )
            await interaction.followup.send(embed=error_embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"공지 게시 중 오류: {e}")
            error_embed = create_error_embed(
                "❌ 오류 발생",
                "공지 게시 중 오류가 발생했습니다."
            )
            await interaction.followup.send(embed=error_embed, ephemeral=True)
    
    @app_commands.command(name="규칙", description="서버 규칙을 게시합니다 (관리자 전용)")
    @app_commands.describe(채널="규칙을 게시할 채널 (선택사항)")
    async def rules(
        self, 
        interaction: discord.Interaction,
        채널: Optional[discord.TextChannel] = None
    ):
        """서버 규칙 게시"""
        # 관리자 권한 확인
        if not await has_admin_permissions(interaction.user):
            embed = create_error_embed(
                "❌ 권한 없음",
                "이 명령어는 관리자만 사용할 수 있습니다."
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        await interaction.response.defer()
        
        # 채널 설정
        target_channel = 채널 or interaction.channel
        
        # 기존 봇 메시지 삭제
        await self.delete_bot_messages(target_channel)
        
        # 규칙 임베드 생성 및 전송
        embed = self.create_rules_embed()
        
        try:
            await target_channel.send(embed=embed)
            
            success_embed = create_success_embed(
                "✅ 규칙 게시 완료",
                f"{target_channel.mention} 채널에 규칙이 게시되었습니다."
            )
            await interaction.followup.send(embed=success_embed, ephemeral=True)
            
        except discord.Forbidden:
            error_embed = create_error_embed(
                "❌ 권한 부족",
                f"{target_channel.mention} 채널에 메시지를 보낼 권한이 없습니다."
            )
            await interaction.followup.send(embed=error_embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"규칙 게시 중 오류: {e}")
            error_embed = create_error_embed(
                "❌ 오류 발생",
                "규칙 게시 중 오류가 발생했습니다."
            )
            await interaction.followup.send(embed=error_embed, ephemeral=True)
    
    def create_rules_embed(self) -> discord.Embed:
        """규칙 임베드 생성 (JSON에서 동적 로드)"""
        rules_data = self.load_rules_from_json()
        
        embed = discord.Embed(
            title=rules_data["title"],
            color=rules_data["color"]
        )
        
        # 규칙 내용 추가
        rules_text = "\n\n".join(rules_data["rules"])
        embed.description = rules_text
        
        # 푸터 및 업데이트 정보 추가
        footer_text = rules_data["footer"]
        if "last_updated" in rules_data:
            footer_text += f" | 최종 업데이트: {rules_data['last_updated']}"
        
        embed.set_footer(text=footer_text)
        embed.timestamp = discord.utils.utcnow()
        
        return embed
    
    @app_commands.command(name="규칙수정", description="규칙을 JSON 파일에서 다시 로드합니다 (관리자 전용)")
    async def reload_rules(self, interaction: discord.Interaction):
        """규칙 JSON 파일 새로고침"""
        if not await has_admin_permissions(interaction.user):
            embed = create_error_embed(
                "❌ 권한 없음",
                "이 명령어는 관리자만 사용할 수 있습니다."
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        try:
            rules_data = self.load_rules_from_json()
            
            embed = create_success_embed(
                "✅ 규칙 파일 새로고침 완료",
                f"**{rules_data['title']}**\n"
                f"규칙 {len(rules_data['rules'])}개가 로드되었습니다.\n"
                f"파일 위치: `{self.rules_file_path}`"
            )
            
            if "last_updated" in rules_data:
                embed.add_field(
                    name="📅 최종 업데이트",
                    value=rules_data["last_updated"],
                    inline=True
                )
            
        except Exception as e:
            embed = create_error_embed(
                "❌ 규칙 로드 실패",
                f"규칙 파일을 불러올 수 없습니다: {str(e)}"
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    async def delete_bot_messages(self, channel: discord.TextChannel, limit: int = 50):
        """해당 채널에서 봇이 보낸 임베드 메시지 삭제"""
        try:
            async for message in channel.history(limit=limit):
                if (message.author == self.bot.user and 
                    message.embeds and 
                    len(message.embeds) > 0):
                    await message.delete()
                    break  # 가장 최근 메시지만 삭제
        except discord.Forbidden:
            logger.warning(f"{channel.name} 채널에서 메시지 삭제 권한 없음")
        except Exception as e:
            logger.error(f"메시지 삭제 중 오류: {e}")

async def setup(bot):
    """Cog 로드"""
    await bot.add_cog(AnnouncementCog(bot))
