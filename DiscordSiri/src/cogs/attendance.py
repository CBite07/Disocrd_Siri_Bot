"""
출석 체크 및 레벨링 시스템 Cog
핵심 기능: /ㅊㅊ 명령어를 통한 출석 체크 및 XP 획득
"""

import discord
from discord.ext import commands
from discord import app_commands
import logging
import random

from utils.config import Config
from utils.helpers import (
    create_success_embed, 
    create_error_embed, 
    create_level_up_embed,
    format_progress_bar,
    format_number,
    get_role_by_id
)

logger = logging.getLogger(__name__)

class AttendanceCog(commands.Cog):
    """출석 체크 시스템"""
    
    def __init__(self, bot):
        self.bot = bot
        
        # 랜덤 출석체크 완료 메시지 목록
        self.attendance_messages = [
            "님 출석체크가 완료되었습니다!",
            "님 오늘도 좋은 하루 되세요!",
            "님 오늘도 화이팅! 출석 완료!",
            "님 벌써 이렇게 성장하시다니! 대단해요!",
            "님 꾸준함이 최고의 재능이에요!",
            "님 오늘도 멋진 하루 보내세요!",
            "님 출석체크 완료! 레벨업까지 화이팅!",
            "님 성실함에 박수를 보냅니다! 👏",
            "님 오늘도 최고예요! 출석 완료!",
            "님 한 걸음 더 성장했어요! 축하해요!"
        ]
    
    @app_commands.command(name="ㅊㅊ", description="출석 체크를 합니다")
    async def attendance(self, interaction: discord.Interaction):
        """출석 체크 명령어"""
        user_id = interaction.user.id
        guild_id = interaction.guild.id
        
        # 사용자 데이터 확인 및 생성
        user_data = await self.bot.db.get_user_data(user_id, guild_id)
        if not user_data:
            await self.bot.db.create_user(user_id, guild_id)
            user_data = await self.bot.db.get_user_data(user_id, guild_id)
        
        # 출석 체크 처리
        success, old_level, new_level = await self.bot.db.update_attendance(
            user_id, guild_id, Config.XP_PER_ATTENDANCE
        )
        
        if not success:
            # 이미 출석한 경우 - ephemeral 메시지로 즉시 응답
            embed = create_error_embed(
                "❌ 출석 체크 실패",
                "오늘은 이미 출석 체크를 완료했습니다!\n내일 다시 시도해주세요."
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # 성공한 경우에만 defer 사용
        await interaction.response.defer()
        
        # 현재 사용자 데이터 다시 조회 (XP 업데이트 후)
        updated_user_data = await self.bot.db.get_user_data(user_id, guild_id)
        current_xp = updated_user_data['xp']
        
        # XP 기반으로 실제 레벨 계산
        actual_old_level = Config.calculate_level_from_xp(current_xp - Config.XP_PER_ATTENDANCE)
        actual_new_level = Config.calculate_level_from_xp(current_xp)
        current_level = actual_new_level
        
        # 레벨 100 (최대 레벨) 처리
        if current_level >= 100:
            progress_info = "**다음 레벨까지:**\n    🏆 **LEVEL MAX** - 더 이상 올릴 레벨이 없습니다!"
        else:
            current_level, progress_xp, needed_xp = Config.get_level_progress(current_xp)
            progress_bar = format_progress_bar(progress_xp, needed_xp)
            progress_info = f"**다음 레벨까지:**\n    {progress_bar}"
        
        # 랜덤 출석체크 완료 메시지 선택
        random_message = random.choice(self.attendance_messages)
        
        # 성공적인 출석 체크 메시지
        embed = create_success_embed(
            "✅ 출석 체크 완료!",
            f"{interaction.user.mention}{random_message}\n\n"
            f"**현재 레벨:** {current_level}\n"
            f"{progress_info}"
        )
        
        # 레벨업 확인 (실제 XP 기반 레벨로 확인)
        if actual_new_level > actual_old_level:
            # 레벨업 메시지 추가 (실제 레벨 변화 표시)
            level_up_embed = create_level_up_embed(interaction.user, actual_old_level, actual_new_level)
            
            # 역할 부여 시도
            role_assigned = await self.assign_level_role(interaction.user, actual_new_level)
            if role_assigned:
                role_id = Config.get_role_for_level(actual_new_level)
                role = get_role_by_id(interaction.guild, role_id)
                if role:
                    level_up_embed.add_field(
                        name="🎭 역할 부여",
                        value=f"{role.mention} 역할이 부여되었습니다!",
                        inline=False
                    )
            
            await interaction.followup.send(embed=embed)
            await interaction.followup.send(embed=level_up_embed)
        else:
            await interaction.followup.send(embed=embed)
    
    @app_commands.command(name="내정보", description="현재 레벨과 진행도를 확인합니다")
    @app_commands.describe(공개="다른 사람도 볼 수 있게 공개할지 선택 (기본값: 비공개)")
    async def my_info(self, interaction: discord.Interaction, 공개: bool = False):
        """레벨 정보 조회 - 자신의 정보만 확인 가능"""
        target_user = interaction.user
        user_data = await self.bot.db.get_user_data(target_user.id, interaction.guild.id)
        
        if not user_data:
            embed = create_error_embed(
                "❌ 데이터 없음",
                f"{target_user.mention}님의 데이터를 찾을 수 없습니다."
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        current_xp = user_data['xp']
        current_level = Config.calculate_level_from_xp(current_xp)
        
        # 공개 여부에 따른 이모지와 제목 설정
        if 공개:
            title_prefix = "🌟"
            footer_text = f"{target_user.display_name}님이 자신의 정보를 자랑하고 있어요! ✨"
        else:
            title_prefix = "📊"
            footer_text = "비공개 정보 조회 • Siri Bot"
        
        embed = discord.Embed(
            title=f"{title_prefix} {target_user.display_name}님의 레벨 정보",
            color=Config.COLORS['info']
        )
        
        embed.add_field(
            name="🎯 현재 레벨",
            value=f"**Level {current_level}**",
            inline=True
        )
        
        embed.add_field(
            name="⚡ 총 경험치",
            value=f"**{format_number(current_xp)} XP**",
            inline=True
        )
        
        # 레벨 100 (최대 레벨) 처리
        if current_level >= 100:
            embed.add_field(
                name="🏆 다음 레벨까지",
                value="**LEVEL MAX**",
                inline=True
            )
            
            embed.add_field(
                name="📊 진행도",
                value="🟦🟦🟦🟦🟦🟦🟦🟦🟦🟦 **MAX**\n더 이상 올릴 레벨이 없습니다!",
                inline=False
            )
        else:
            current_level, progress_xp, needed_xp = Config.get_level_progress(current_xp)
            progress_bar = format_progress_bar(progress_xp, needed_xp)
            
            embed.add_field(
                name="📈 다음 레벨까지",
                value=f"{format_number(progress_xp)}/{format_number(needed_xp)} XP",
                inline=True
            )
            
            embed.add_field(
                name="📊 진행도",
                value=f"**{progress_bar}**",
                inline=False
            )
        
        # 사용자가 가진 레벨 역할 표시
        level_roles = self.get_user_level_roles(target_user)
        if level_roles:
            embed.add_field(
                name="🎭 보유 역할",
                value=" ".join([role.mention for role in level_roles]),
                inline=False
            )
        
        # 마지막 출석일 표시
        last_attendance = user_data.get('last_attendance')
        if last_attendance:
            embed.add_field(
                name="📅 마지막 출석",
                value=last_attendance,
                inline=True
            )
        
        embed.set_thumbnail(url=target_user.display_avatar.url)
        embed.set_footer(text=footer_text)
        
        # 공개/비공개에 따른 메시지 전송
        # 공개=False (비공개): ephemeral=True로 나만 보기
        # 공개=True (공개): ephemeral=False로 모두 보기
        await interaction.response.send_message(embed=embed, ephemeral=not 공개)
    
    def get_user_level_roles(self, member: discord.Member) -> list:
        """사용자가 가진 레벨 관련 역할들 반환"""
        level_role_ids = [
            1392422549174091868,  # 초보자
            1392431487697293465,  # 입문자
            1392431532592857182,  # 숙련자
            1392431564574687323,  # 전문가
            1392431591304990730,  # 마스터
            1392431665376264192,  # 그랜드마스터
            1392431727292448922,  # 레전드
        ]
        
        user_level_roles = []
        for role in member.roles:
            if role.id in level_role_ids:
                user_level_roles.append(role)
        
        return user_level_roles
    
    async def assign_level_role(self, member: discord.Member, level: int) -> bool:
        """레벨에 따른 역할 자동 부여"""
        try:
            # 현재 레벨에 맞는 역할 ID 가져오기
            target_role_id = Config.get_role_for_level(level)
            if not target_role_id:
                return False
            
            target_role = get_role_by_id(member.guild, target_role_id)
            if not target_role:
                logger.warning(f"역할 ID {target_role_id}를 찾을 수 없음")
                return False
            
            # 봇 권한 확인
            bot_member = member.guild.get_member(self.bot.user.id)
            if not bot_member or target_role >= bot_member.top_role:
                logger.warning(f"봇이 {target_role.name} 역할을 부여할 권한이 없음")
                return False
            
            # 기존 레벨 역할 제거
            roles_to_remove = []
            for role in member.roles:
                for role_level_range, role_id in Config.ROLE_LEVELS.items():
                    if role.id == role_id and role.id != target_role_id:
                        roles_to_remove.append(role)
            
            if roles_to_remove:
                await member.remove_roles(*roles_to_remove, reason="레벨업으로 인한 역할 변경")
            
            # 새 역할 부여 (이미 가지고 있지 않은 경우)
            if target_role not in member.roles:
                await member.add_roles(target_role, reason=f"레벨 {level} 달성")
            
            logger.info(f"{member.display_name}에게 {target_role.name} 역할 부여 완료")
            return True
            
        except discord.Forbidden:
            logger.error(f"권한 부족으로 {member.display_name}에게 역할 부여 실패")
            return False
        except Exception as e:
            logger.error(f"역할 부여 중 오류: {e}")
            return False

async def setup(bot):
    """Cog 로드"""
    await bot.add_cog(AttendanceCog(bot))
