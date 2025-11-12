"""
음악 재생 명령어 Cog (Siri 봇용)
GPT 봇에게 직접 음악 재생을 요청
"""

import discord
from discord.ext import commands
from discord import app_commands
import logging

logger = logging.getLogger("cogs.music_commands")


class MusicCommandsCog(commands.Cog):
    """Siri 봇에서 GPT 봇의 음악 기능을 호출하는 명령어들"""

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="재생", description="GPT 봇을 통해 음악을 재생합니다")
    @app_commands.describe(검색어="유튜브 URL 또는 검색할 곡 이름")
    async def play_music(self, interaction: discord.Interaction, 검색어: str):
        """음악 재생 명령어 (GPT 봇에 전달)"""
        await interaction.response.defer()

        # 사용자가 음성 채널에 있는지 확인
        if not interaction.user.voice or not interaction.user.voice.channel:
            embed = discord.Embed(
                title="❌ 음성 채널 없음",
                description="음성 채널에 먼저 참여해주세요!",
                color=0xFF0000,
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        # GPT 봇이 준비되었는지 확인
        if not self.bot.gpt_bot or not self.bot.gpt_bot.is_ready():
            embed = discord.Embed(
                title="❌ 음악 봇 없음",
                description="음악 봇이 준비되지 않았습니다.",
                color=0xFF0000,
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            logger.error("GPT 봇이 준비되지 않음")
            return

        # GPT 봇에 직접 재생 요청
        try:
            logger.info(
                f"[Siri→GPT] 음악 재생 요청: {검색어} (사용자: {interaction.user.name})"
            )

            result = await self.bot.gpt_bot.play_music_direct(
                guild_id=interaction.guild.id,
                channel_id=interaction.user.voice.channel.id,
                query=검색어,
                user=interaction.user.name,
            )

            if result["status"] == "playing":
                # 재생 성공
                embed = discord.Embed(
                    title="🎵 재생 중",
                    description=f"**{result['song']}**",
                    color=0x00FF00,
                )

                if result.get("thumbnail"):
                    embed.set_image(url=result["thumbnail"])

                if result.get("uploader"):
                    embed.add_field(
                        name="🎤 아티스트", value=result["uploader"], inline=False
                    )

                embed.set_footer(text=f"요청자: {interaction.user.name}")

                await interaction.followup.send(embed=embed)
                logger.info(f"[Siri→GPT] 재생 성공: {result['song']}")

            else:
                # 재생 실패
                embed = discord.Embed(
                    title="❌ 재생 실패",
                    description=result.get("message", "알 수 없는 오류"),
                    color=0xFF0000,
                )
                await interaction.followup.send(embed=embed)
                logger.warning(f"[Siri→GPT] 재생 실패: {result.get('message')}")

        except Exception as e:
            logger.error(f"[Siri→GPT] 음악 재생 요청 중 예외: {e}", exc_info=True)
            embed = discord.Embed(
                title="❌ 오류",
                description=f"음악 재생 중 오류가 발생했습니다: {str(e)}",
                color=0xFF0000,
            )
            await interaction.followup.send(embed=embed)

    @app_commands.command(name="정지", description="음악 재생을 정지합니다")
    async def stop_music(self, interaction: discord.Interaction):
        """음악 정지 명령어 (GPT 봇에 전달)"""
        await interaction.response.defer(ephemeral=True)

        # GPT 봇이 준비되었는지 확인
        if not self.bot.gpt_bot or not self.bot.gpt_bot.is_ready():
            await interaction.followup.send(
                "❌ 음악 봇이 준비되지 않았습니다.", ephemeral=True
            )
            return

        try:
            logger.info(f"[Siri→GPT] 음악 정지 요청 (길드: {interaction.guild.id})")

            result = await self.bot.gpt_bot.stop_music_direct(
                guild_id=interaction.guild.id
            )

            if result["status"] == "stopped":
                await interaction.followup.send(
                    "✅ 음악이 정지되었습니다.", ephemeral=True
                )
                logger.info(f"[Siri→GPT] 정지 성공")
            else:
                await interaction.followup.send(
                    f"❌ {result.get('message', '정지 실패')}", ephemeral=True
                )
                logger.warning(f"[Siri→GPT] 정지 실패: {result.get('message')}")

        except Exception as e:
            logger.error(f"[Siri→GPT] 음악 정지 요청 중 예외: {e}", exc_info=True)
            await interaction.followup.send(f"❌ 오류: {str(e)}", ephemeral=True)


async def setup(bot):
    """Cog 로드"""
    await bot.add_cog(MusicCommandsCog(bot))
    logger.info("MusicCommandsCog 로드 완료 (Siri→GPT 직접 통신)")
