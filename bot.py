import os
import asyncio
import aiohttp
import discord

from discord.ext import commands
from discord import app_commands
from mcstatus import JavaServer


# =========================================================
# ENV
# =========================================================

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

GUILD_ID = int(os.getenv("GUILD_ID", "1550471340610289795"))

MC_HOST = os.getenv("MC_HOST", "95.156.225.24")
MC_PORT = int(os.getenv("MC_PORT", "26383"))

MINE_CHAT_CHANNEL_ID = int(
    os.getenv("MINE_CHAT_CHANNEL_ID", "1552794391247192084")
)

PARTNER_PANEL_URL = os.getenv(
    "PARTNER_PANEL_URL",
    "https://panel.partner-hosting.com"
).rstrip("/")

PARTNER_SERVER_ID = os.getenv(
    "PARTNER_SERVER_ID",
    "a594dd95"
)

PARTNER_API_KEY = os.getenv("PARTNER_API_KEY")


# =========================================================
# OWNER IDS
# =========================================================

OWNER_IDS = {
    1446592341908652112,
    1476170066327371798,
    1499456366325010552,
    1011294015200706611,
}


# =========================================================
# DISCORD
# =========================================================

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)


# =========================================================
# CHECK OWNER
# =========================================================

def is_owner(user_id: int) -> bool:
    return user_id in OWNER_IDS


# =========================================================
# PARTNER HOST API
# =========================================================

async def partner_power(signal: str):
    """
    signal:
    start
    stop
    restart
    """

    if not PARTNER_API_KEY:
        return False, "PARTNER_API_KEY غير موجود في Railway Variables."

    url = (
        f"{PARTNER_PANEL_URL}"
        f"/api/client/servers/{PARTNER_SERVER_ID}/power"
    )

    headers = {
        "Authorization": f"Bearer {PARTNER_API_KEY}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    payload = {
        "signal": signal
    }

    try:
        timeout = aiohttp.ClientTimeout(total=15)

        async with aiohttp.ClientSession(timeout=timeout) as session:

            async with session.post(
                url,
                headers=headers,
                json=payload
            ) as response:

                text = await response.text()

                print(
                    f"[PARTNER API] {signal.upper()} "
                    f"HTTP {response.status}"
                )

                if response.status in (200, 204):
                    return True, "OK"

                return False, (
                    f"HTTP {response.status}\n"
                    f"{text[:1000]}"
                )

    except Exception as e:
        print(f"[PARTNER API ERROR] {e}")
        return False, str(e)


# =========================================================
# MC SERVER STATUS
# =========================================================

async def get_server_status():

    def check():
        server = JavaServer.lookup(
            f"{MC_HOST}:{MC_PORT}"
        )

        status = server.status()

        return {
            "online": True,
            "players": status.players.online,
            "max_players": status.players.max,
            "version": status.version.name,
            "ping": round(status.latency),
        }

    try:

        result = await asyncio.wait_for(
            asyncio.to_thread(check),
            timeout=8
        )

        return result

    except Exception as e:

        print(f"[MC STATUS ERROR] {e}")

        return {
            "online": False,
            "players": 0,
            "max_players": 0,
            "version": "Offline",
            "ping": 0,
        }


# =========================================================
# READY
# =========================================================

@bot.event
async def on_ready():

    print("=" * 50)
    print(f"Logged in as {bot.user}")
    print(f"Guild ID: {GUILD_ID}")
    print("=" * 50)

    guild = discord.Object(id=GUILD_ID)

    try:

        # تسجيل أوامر هذا البوت داخل السيرفر مباشرة
        synced = await bot.tree.sync(
            guild=guild
        )

        print(
            f"Synced {len(synced)} guild commands:"
        )

        for command in synced:
            print(f"  /{command.name}")

    except Exception as e:

        print(
            f"[SYNC ERROR] {type(e).__name__}: {e}"
        )


# =========================================================
# /SERVER
# =========================================================

@bot.tree.command(
    name="server",
    description="عرض حالة سيرفر Minecraft"
)
@app_commands.guilds(discord.Object(id=GUILD_ID))
async def server_command(
    interaction: discord.Interaction
):

    print(
        f"[COMMAND] /server "
        f"by {interaction.user} "
        f"({interaction.user.id})"
    )

    await interaction.response.defer()

    status = await get_server_status()

    if status["online"]:

        embed = discord.Embed(
            title="FirstMC Network",
            description="حالة سيرفر Minecraft",
            color=discord.Color.green()
        )

        embed.add_field(
            name="🟢 الحالة",
            value="Online",
            inline=True
        )

        embed.add_field(
            name="👥 اللاعبين",
            value=(
                f"{status['players']}/"
                f"{status['max_players']}"
            ),
            inline=True
        )

        embed.add_field(
            name="📡 Ping",
            value=f"{status['ping']} ms",
            inline=True
        )

        embed.add_field(
            name="⚔️ Version",
            value=status["version"],
            inline=True
        )

        embed.add_field(
            name="🌐 Java",
            value=f"`{MC_HOST}:{MC_PORT}`",
            inline=False
        )

    else:

        embed = discord.Embed(
            title="FirstMC Network",
            description="حالة سيرفر Minecraft",
            color=discord.Color.red()
        )

        embed.add_field(
            name="🔴 الحالة",
            value="Offline",
            inline=True
        )

        embed.add_field(
            name="🌐 Java",
            value=f"`{MC_HOST}:{MC_PORT}`",
            inline=False
        )

    await interaction.followup.send(
        embed=embed
    )


# =========================================================
# POWER COMMAND HELPER
# =========================================================

async def power_command(
    interaction: discord.Interaction,
    signal: str,
    emoji: str,
    title: str
):

    print(
        f"[COMMAND] /{signal} "
        f"by {interaction.user} "
        f"({interaction.user.id})"
    )

    # Owner check
    if not is_owner(interaction.user.id):

        await interaction.response.send_message(
            "❌ ليس لديك صلاحية استخدام هذا الأمر.",
            ephemeral=True
        )

        print(
            f"[DENIED] {interaction.user} "
            f"tried /{signal}"
        )

        return

    # لازم نرد بسرعة
    await interaction.response.defer(
        ephemeral=True
    )

    success, result = await partner_power(
        signal
    )

    if success:

        embed = discord.Embed(
            title=f"{emoji} {title}",
            description=(
                f"تم إرسال أمر **{signal}** "
                f"إلى سيرفر FirstMC."
            ),
            color=discord.Color.green()
        )

        embed.add_field(
            name="Server ID",
            value=f"`{PARTNER_SERVER_ID}`",
            inline=False
        )

        await interaction.followup.send(
            embed=embed,
            ephemeral=True
        )

    else:

        embed = discord.Embed(
            title="❌ حدث خطأ",
            description=(
                "لم أستطع تنفيذ الأمر."
            ),
            color=discord.Color.red()
        )

        embed.add_field(
            name="التفاصيل",
            value=f"```{result[:1500]}```",
            inline=False
        )

        await interaction.followup.send(
            embed=embed,
            ephemeral=True
        )


# =========================================================
# /START
# =========================================================

@bot.tree.command(
    name="start",
    description="تشغيل سيرفر Minecraft"
)
@app_commands.guilds(discord.Object(id=GUILD_ID))
async def start_command(
    interaction: discord.Interaction
):

    await power_command(
        interaction,
        "start",
        "🟢",
        "Starting Server"
    )


# =========================================================
# /STOP
# =========================================================

@bot.tree.command(
    name="stop",
    description="إيقاف سيرفر Minecraft"
)
@app_commands.guilds(discord.Object(id=GUILD_ID))
async def stop_command(
    interaction: discord.Interaction
):

    await power_command(
        interaction,
        "stop",
        "🔴",
        "Stopping Server"
    )


# =========================================================
# /RESTART
# =========================================================

@bot.tree.command(
    name="restart",
    description="إعادة تشغيل سيرفر Minecraft"
)
@app_commands.guilds(discord.Object(id=GUILD_ID))
async def restart_command(
    interaction: discord.Interaction
):

    await power_command(
        interaction,
        "restart",
        "🔄",
        "Restarting Server"
    )


# =========================================================
# /CHAT-MINECRAFT
# =========================================================

@bot.tree.command(
    name="chat-minecraft",
    description="تحديد روم ربط Discord مع Minecraft"
)
@app_commands.guilds(discord.Object(id=GUILD_ID))
async def chat_minecraft_command(
    interaction: discord.Interaction
):

    print(
        f"[COMMAND] /chat-minecraft "
        f"by {interaction.user} "
        f"({interaction.user.id})"
    )

    if not is_owner(interaction.user.id):

        await interaction.response.send_message(
            "❌ ليس لديك صلاحية استخدام هذا الأمر.",
            ephemeral=True
        )

        return

    global MINE_CHAT_CHANNEL_ID

    MINE_CHAT_CHANNEL_ID = interaction.channel_id

    await interaction.response.send_message(
        f"✅ تم تحديد هذا الروم كـ Minecraft Chat.\n"
        f"Channel ID: `{interaction.channel_id}`"
    )

    print(
        f"[CHAT] Minecraft channel set to "
        f"{interaction.channel_id}"
    )


# =========================================================
# ERROR HANDLER
# =========================================================

@bot.tree.error
async def on_app_command_error(
    interaction: discord.Interaction,
    error: app_commands.AppCommandError
):

    print(
        "[COMMAND ERROR]",
        repr(error)
    )

    try:

        if interaction.response.is_done():

            await interaction.followup.send(
                f"❌ حدث خطأ:\n`{str(error)[:1000]}`",
                ephemeral=True
            )

        else:

            await interaction.response.send_message(
                f"❌ حدث خطأ:\n`{str(error)[:1000]}`",
                ephemeral=True
            )

    except Exception as e:

        print(
            "[ERROR HANDLER FAILED]",
            repr(e)
        )


# =========================================================
# GLOBAL ERROR
# =========================================================

@bot.event
async def on_error(
    event,
    *args,
    **kwargs
):

    import traceback

    print(
        f"[GLOBAL ERROR] Event: {event}"
    )

    traceback.print_exc()


# =========================================================
# START
# =========================================================

if not DISCORD_TOKEN:

    raise RuntimeError(
        "DISCORD_TOKEN غير موجود في Railway Variables."
    )

print("Starting FirstMC Bot...")

bot.run(DISCORD_TOKEN)
