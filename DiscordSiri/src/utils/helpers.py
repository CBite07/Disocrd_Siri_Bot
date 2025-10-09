"""
유틸리티 함수 모듈
공통으로 사용되는 헬퍼 함수들
"""

import discord
from typing import Optional
from utils.config import Config

def create_embed(title: str, description: str = "", color: int = Config.COLORS['info']) -> discord.Embed:
    """공통 임베드 생성 함수"""
    embed = discord.Embed(
        title=title,
        description=description,
        color=color
    )
    embed.set_footer(text="Siri Bot")
    return embed

def create_success_embed(title: str, description: str = "") -> discord.Embed:
    """성공 메시지용 임베드"""
    return create_embed(title, description, Config.COLORS['success'])

def create_error_embed(title: str, description: str = "") -> discord.Embed:
    """오류 메시지용 임베드"""
    return create_embed(title, description, Config.COLORS['error'])

def create_level_up_embed(user: discord.Member, old_level: int, new_level: int) -> discord.Embed:
    """레벨업 메시지용 임베드"""
    embed = discord.Embed(
        title="🎉 레벨업!",
        description=f"{user.mention}님이 레벨 {old_level} → {new_level}로 올랐습니다!",
        color=Config.COLORS['level_up']
    )
    embed.set_thumbnail(url=user.display_avatar.url)
    return embed

def format_progress_bar(current: int, total: int, length: int = 10) -> str:
    """진행도 바 생성 (디스코드 이모지 사용, 10개 고정)"""
    if total == 0:
        percentage = 0
    else:
        percentage = min(current / total, 1.0)
    
    filled = int(length * percentage)
    
    # 디스코드 이모지를 사용한 프로그레스 바 (10개)
    filled_squares = "🟦" * filled
    empty_squares = "⬜" * (length - filled)
    
    percent = int(percentage * 100)
    
    return f"{filled_squares}{empty_squares} {percent}%"

def format_number(number: int) -> str:
    """숫자를 천 단위로 구분하여 포맷"""
    return f"{number:,}"

async def has_admin_permissions(member: discord.Member) -> bool:
    """관리자 권한 확인"""
    return member.guild_permissions.administrator

def get_role_by_id(guild: discord.Guild, role_id: int) -> Optional[discord.Role]:
    """역할 ID로 역할 객체 조회"""
    return guild.get_role(role_id)

def calculate_percentage(current: int, total: int) -> int:
    """퍼센트 계산"""
    if total == 0:
        return 0
    return min(int((current / total) * 100), 100)
