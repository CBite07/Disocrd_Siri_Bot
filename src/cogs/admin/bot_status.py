import discord
from pathlib import Path
import psutil
from utils.config import Config


def get_db_path() -> Path:
    return Path(__file__).parent.parent / "data" / "siri_bot.db"


def create_status_embed(bot: discord.Client, db_path: Path) -> discord.Embed:
    process = psutil.Process()
    memory_mb = process.memory_info().rss / 1024 / 1024

    # 데이터베이스 파일 크기
    db_size_mb = db_path.stat().st_size / 1024 / 1024 if db_path.exists() else 0

    # 레이턴시
    latency_ms = round(bot.latency * 1000, 2)

    # 사용자 통계
    total_guilds = len(bot.guilds)
    total_users = sum((g.member_count or 0) for g in bot.guilds)

    # Cog 목록
    cog_list = list(bot.cogs.keys())

    # 명령어 수
    command_count = len(bot.tree.get_commands())

    embed = discord.Embed(
        title="🖥️ 시스템 상태", color=Config.COLORS.get("info", 0x00FF00)
    )

    embed.set_thumbnail(url=bot.user.display_avatar.url)
    embed.set_footer(text=f"봇 ID: {bot.user.id}")

    # 기본 정보
    embed.add_field(
        name="📊 기본 정보",
        value=(
            f"• 서버 수: {total_guilds}개\n"
            f"• 사용자 수: {total_users}명\n"
            f"• 레이턴시: {latency_ms}ms"
        ),
        inline=True,
    )

    # Cog 정보
    embed.add_field(
        name="🔧 로드된 Cogs",
        value="\n".join(f"• {c}" for c in cog_list) if cog_list else "없음",
        inline=True,
    )

    # 슬래시 명령어 수
    embed.add_field(
        name="⚡ 슬래시 명령어", value=f"{command_count}개 등록됨", inline=True
    )

    # 시스템 정보
    embed.add_field(name="💾 메모리", value=f"{memory_mb:.1f} MB", inline=True)
    embed.add_field(name="📊 DB 크기", value=f"{db_size_mb:.1f} MB", inline=True)

    return embed
