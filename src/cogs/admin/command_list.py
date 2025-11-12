import discord


def get_cog_name(command):
    cog_instance = getattr(command.callback, "__self__", None)
    return cog_instance.__class__.__name__ if cog_instance else "기타"


def format_command_text(cmd_list):
    return "\n".join(f"`/{cmd['name']}` - {cmd['description']}" 
                    for cmd in cmd_list)


def create_cmd_list_embed(bot: discord.Client):
    embed = discord.Embed(title="🔧 등록된 슬래시 명령어 목록", color=0x3498db)
    command_list = {}

    for command in bot.tree.get_commands():
        cog_name = get_cog_name(command)
        command_list.setdefault(cog_name, []).append(
            {"name": command.name, "description": command.description or "설명 없음"}
        )

    for cog_name, cmd_list in command_list.items():
        embed.add_field(name=f"📂 {cog_name}", 
                        value=format_command_text(cmd_list), inline=False)

    total_commands = sum(len(cmd_list) for cmd_list in command_list.values())
    embed.add_field(name="📊 통계", value=f"총 {total_commands}개 명령어", inline=True)

    return embed