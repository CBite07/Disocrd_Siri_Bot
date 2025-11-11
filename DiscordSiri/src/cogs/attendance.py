"""
관리자 기능 Cog
XP 조정, 데이터 초기화, 디버그 도구 등 관리 기능
"""

import discord
from discord.ext import commands
from discord import app_commands
import logging

from utils.config import Config
from utils.helpers import (
    create_success_embed, 
    create_error_embed, 
    has_admin_permissions,
    format_number,
    get_role_by_id
)

logger = logging.getLogger(__name__)

class AdminCog(commands.Cog):
    """관리자 전용 기능"""
    
    def __init__(self, bot):
        self.bot = bot
    
    async def assign_level_role(self, member: discord.Member, level: int) -> bool:
        """레벨에 따른 역할 자동 부여 (attendance.py와 동일한 로직)"""
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
                await member.remove_roles(*roles_to_remove, reason="레벨 변경으로 인한 역할 변경")
            
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
    
    @app_commands.command(name="레벨설정", description="특정 유저의 레벨을 설정합니다 (관리자 전용)")
    @app_commands.describe(
        유저="레벨을 설정할 대상 유저",
        레벨="설정할 레벨 (1~100)"
    )
    async def set_level(
        self, 
        interaction: discord.Interaction, 
        유저: discord.Member, 
        레벨: int
    ):
        """레벨 설정"""
        # 길드 컨텍스트 확인
        if interaction.guild is None or not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message("❌ 이 명령어는 서버에서만 사용할 수 있습니다.", ephemeral=True)
            return
        # 관리자 권한 확인
        from typing import cast
        member_user = cast(discord.Member, interaction.user)
        if not await has_admin_permissions(member_user):
            embed = create_error_embed(
                "❌ 권한 없음",
                "이 명령어는 관리자만 사용할 수 있습니다."
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # 레벨 유효성 검사
        if not (1 <= 레벨 <= 100):
            embed = create_error_embed(
                "❌ 잘못된 값",
                "레벨은 1부터 100까지만 설정할 수 있습니다."
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        # 사용자 데이터 확인 및 생성
        user_data = await self.bot.db.get_user_data(유저.id, interaction.guild.id)
        if not user_data:
            await self.bot.db.create_user(유저.id, interaction.guild.id)
        
        # 레벨에 해당하는 XP 계산
        target_xp = Config.calculate_xp_for_level(레벨)
        xp_capped = False
        if target_xp >= Config.MAX_XP:
            target_xp = Config.MAX_XP
            xp_capped = True
        
        # 현재 XP와의 차이 계산
        current_data = await self.bot.db.get_user_data(유저.id, interaction.guild.id)
        current_xp = current_data['xp'] if current_data else 0
        xp_difference = target_xp - current_xp
        
        # XP 업데이트
        success = await self.bot.db.update_user_xp(유저.id, interaction.guild.id, xp_difference)
        
        if success:
            # 역할 부여 시도
            role_assigned = await self.assign_level_role(유저, 레벨)
            role_message = ""
            if role_assigned:
                role_id = Config.get_role_for_level(레벨)
                if role_id is not None:
                    role = get_role_by_id(interaction.guild, role_id)
                    if role:
                        role_message = f"\n🎭 {role.mention} 역할이 부여되었습니다!"
            
            embed = create_success_embed(
                "✅ 레벨 설정 완료",
                f"{유저.mention}님의 레벨을 **{레벨}**로 설정했습니다.\n"
                f"총 경험치: {format_number(target_xp)} XP{role_message}"
            )
            if xp_capped:
                embed.add_field(
                    name="⚠️ XP 제한",
                    value="SQLite 한계를 넘어서는 경험치는 `MAX_XP`(~9e18)으로 제한되었습니다.",
                    inline=False,
                )
        else:
            embed = create_error_embed(
                "❌ 레벨 설정 실패",
                "레벨 설정 중 오류가 발생했습니다."
            )
        
        await interaction.followup.send(embed=embed)
    
    @app_commands.command(name="데이터초기화", description="특정 유저의 데이터를 초기화합니다 (관리자 전용)")
    @app_commands.describe(유저="데이터를 초기화할 대상 유저")
    async def reset_user_data(
        self, 
        interaction: discord.Interaction, 
        유저: discord.Member
    ):
        """사용자 데이터 초기화 (확인 절차 포함)"""
        # 길드/멤버 컨텍스트 확인 및 관리자 권한 확인
        if interaction.guild is None or not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message("❌ 이 명령어는 서버에서만 사용할 수 있습니다.", ephemeral=True)
            return
        from typing import cast
        member_user = cast(discord.Member, interaction.user)
        if not await has_admin_permissions(member_user):
            embed = create_error_embed(
                "❌ 권한 없음",
                "이 명령어는 관리자만 사용할 수 있습니다."
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # 확인 메시지 생성
        embed = discord.Embed(
            title="⚠️ 데이터 초기화 확인",
            description=f"{유저.mention}님의 모든 데이터를 초기화하시겠습니까?\n\n"
                       f"**이 작업은 되돌릴 수 없습니다!**\n"
                       f"• 레벨: 1로 초기화\n"
                       f"• XP: 0으로 초기화\n"
                       f"• 출석 기록: 삭제\n"
                       f"• 레벨 역할: 모두 제거",
            color=Config.COLORS['warning']
        )
        
        # 확인/취소 버튼 생성
        view = DataResetConfirmView(유저, self.bot.db)
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @app_commands.command(name="명령어목록", description="등록된 모든 명령어를 확인합니다 (개발자용)")
    async def list_commands(self, interaction: discord.Interaction):
        """등록된 모든 슬래시 명령어 목록 표시"""
        # 길드 컨텍스트 확인
        if interaction.guild is None:
            await interaction.response.send_message("❌ 이 명령어는 서버에서만 사용할 수 있습니다.", ephemeral=True)
            return
        # 봇 소유자나 관리자만 사용 가능하도록 제한
        if not (isinstance(interaction.user, discord.Member) and interaction.user.guild_permissions.administrator or 
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
        if interaction.guild is None or not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message("❌ 이 명령어는 서버에서만 사용할 수 있습니다.", ephemeral=True)
            return
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
    
    @app_commands.command(
        name="시스템상태",
        description="봇 시스템 상태 확인 (관리자 전용)"
    )
    async def system_status(self, interaction: discord.Interaction):
        """시스템 리소스 및 상태 확인"""
        if interaction.guild is None or not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message("❌ 이 명령어는 서버에서만 사용할 수 있습니다.", ephemeral=True)
            return
        from typing import cast
        member_user2 = cast(discord.Member, interaction.user)
        if not await has_admin_permissions(member_user2):
            await interaction.response.send_message("❌ 관리자 권한이 필요합니다.", ephemeral=True)
            return
        
        try:
            import psutil
        except ImportError:
            embed = create_error_embed(
                "❌ 시스템 모듈 없음",
                "`psutil` 패키지가 설치되어 있지 않아 시스템 정보를 불러올 수 없습니다."
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        from pathlib import Path
        
        # 메모리 사용량
        process = psutil.Process()
        memory_mb = process.memory_info().rss / 1024 / 1024
        
        # 데이터베이스 파일 크기
        db_path = Path(Config.get_database_path())
        db_size_mb = db_path.stat().st_size / 1024 / 1024 if db_path.exists() else 0
        
        # 레이턴시
        latency_ms = round(self.bot.latency * 1000, 2)
        
        # 사용자 통계
        total_guilds = len(self.bot.guilds)
        total_users = sum((g.member_count or 0) for g in self.bot.guilds)
        
        embed = discord.Embed(
            title="🖥️ 시스템 상태",
            color=Config.COLORS['info']
        )
        embed.add_field(name="💾 메모리", value=f"{memory_mb:.1f} MB", inline=True)
        embed.add_field(name="📊 DB 크기", value=f"{db_size_mb:.1f} MB", inline=True)
        embed.add_field(name="📡 레이턴시", value=f"{latency_ms} ms", inline=True)
        embed.add_field(name="🏠 서버 수", value=f"{total_guilds}", inline=True)
        embed.add_field(name="👥 사용자 수", value=f"{total_users}", inline=True)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

class DataResetConfirmView(discord.ui.View):
    """데이터 초기화 확인 뷰"""
    
    def __init__(self, target_user: discord.Member, database):
        super().__init__(timeout=30)  # 30초 타임아웃
        self.target_user = target_user
        self.database = database
    
    @discord.ui.button(label="✅ 확인", style=discord.ButtonStyle.danger)
    async def confirm_reset(self, interaction: discord.Interaction, button: discord.ui.Button):
        """데이터 초기화 확인"""
        await interaction.response.defer()
        
        # 데이터베이스 초기화
        if interaction.guild is None:
            await interaction.followup.send("❌ 이 작업은 서버에서만 가능합니다.", ephemeral=True)
            return
        success = await self.database.reset_user_data(self.target_user.id, interaction.guild.id)
        
        # 레벨 역할 제거
        roles_removed = await self.remove_level_roles(interaction.guild, self.target_user)
        
        if success:
            embed = create_success_embed(
                "✅ 데이터 초기화 완료",
                f"{self.target_user.mention}님의 모든 데이터가 초기화되었습니다.\n"
                f"제거된 역할: {roles_removed}개"
            )
        else:
            embed = create_error_embed(
                "❌ 초기화 실패",
                "데이터 초기화 중 오류가 발생했습니다."
            )
        
        # 버튼 비활성화
        for item in list(self.children):
            if isinstance(item, discord.ui.Button):
                item.disabled = True
        
        await interaction.edit_original_response(embed=embed, view=self)
    
    async def remove_level_roles(self, guild: discord.Guild, member: discord.Member) -> int:
        """레벨 관련 역할들을 제거"""
        level_role_ids = [
            1392422549174091868,  # 초보자
            1392431487697293465,  # 입문자
            1392431532592857182,  # 숙련자
            1392431564574687323,  # 전문가
            1392431591304990730,  # 마스터
            1392431665376264192,  # 그랜드마스터
            1392431727292448922,  # 레전드
        ]
        
        roles_to_remove = []
        removed_count = 0
        
        try:
            # 사용자가 가진 역할 중 레벨 역할들 찾기
            for role in member.roles:
                if role.id in level_role_ids:
                    roles_to_remove.append(role)
            
            # 역할 제거
            if roles_to_remove:
                await member.remove_roles(*roles_to_remove, reason="데이터 초기화로 인한 레벨 역할 제거")
                removed_count = len(roles_to_remove)
                logger.info(f"{member.display_name}에게서 {removed_count}개의 레벨 역할 제거 완료")
            
        except discord.Forbidden:
            logger.error(f"권한 부족으로 {member.display_name}의 역할 제거 실패")
        except Exception as e:
            logger.error(f"역할 제거 중 오류: {e}")
        
        return removed_count
    
    @discord.ui.button(label="❌ 취소", style=discord.ButtonStyle.secondary)
    async def cancel_reset(self, interaction: discord.Interaction, button: discord.ui.Button):
        """데이터 초기화 취소"""
        embed = create_error_embed(
            "❌ 취소됨",
            "데이터 초기화가 취소되었습니다."
        )
        
        # 버튼 비활성화
        for item in list(self.children):
            if isinstance(item, discord.ui.Button):
                item.disabled = True
        
        await interaction.response.edit_message(embed=embed, view=self)
    
    async def on_timeout(self):
        """타임아웃 처리"""
        for item in list(self.children):
            if isinstance(item, discord.ui.Button):
                item.disabled = True

async def setup(bot):
    """Cog 로드"""
    await bot.add_cog(AdminCog(bot))
