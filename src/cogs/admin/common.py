import discord


def is_admin(interaction: discord.Interaction) -> bool:
    if interaction.guild is None or not isinstance(interaction.user, discord.Member):
        return False
    return (
        interaction.user.guild_permissions.administrator
        or interaction.user.id == 442959929900326913
    )
