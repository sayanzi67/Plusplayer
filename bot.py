import os
import asyncio
import aiohttp
import discord

from discord.ext import commands
from discord import app_commands
from mcstatus import JavaServer


# =========================================================
# SETTINGS
# =========================================================

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

GUILD_ID = int(
    os.getenv("GUILD_ID", "1550471340610289795")
)

MC_HOST = os.getenv(
    "MC_HOST",
    "95.156.225.24"
)

MC_PORT = int(
    os.getenv("MC_PORT", "26383")
)

MINE_CHAT_CHANNEL_ID = int(
    os.getenv(
        "MINE_CHAT_CHANNEL_ID",
        "1552794391247192084"
    )
)

PARTNER_PANEL_URL = os.getenv(
    "PARTNER_PANEL_URL",
    "https://panel.partner-hosting.com"
).rstrip("/")

PARTNER_SERVER_ID = os.getenv(
    "PARTNER_SERVER_ID",
    "a594dd95"
)

PARTNER_API_KEY = os.getenv(
    "PARTNER_API_KEY"
)


# =========================================================
# OWNERS
# =========================================================

OWNER_IDS = {
    1446592341908652112,
    1476170066327371798,
    1499456366325010552,
    1011294015200706611,
}


# =========================================================
# DISCORD BOT
# =========================================================

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)


# =========================================================
# OWNER CHECK
# =========================================================

def is_owner(user_id: int) -> bool:
    return user_id in OWNER_IDS


# =========================================================
# PARTNER HOST API
# =========================================================

async def partner_power(signal: str):

    if not PARTNER_API_KEY:
        return False, "PARTNER_API_KEY غير موجود."

    url = (
        f"{PARTNER_PANEL_URL}"
        f"/api/client/servers/"
        f"{PARTNER_SERVER_ID}/power"
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

        timeout = aiohttp.ClientTimeout(
            total=15
        )

        async with aiohttp.ClientSession(
            timeout=timeout
        ) as session:

            async with session.post(
                url,
                headers=headers,
                json=payload
            ) as response:

                response_text = await response.text()

                print(
                    f"[PARTNER API] "
                    f"{signal.upper()} "
                    f"HTTP {response.status}"
                )

                if response.status in (200, 204):
                    return True, "OK"

                return False, (
                    f"HTTP {response.status}\n"
                    f"{response_text[:1000]}"
                )

    except Exception as e:

        print(
            f"[PARTNER API ERROR] {repr(e)}"
        )

        return False, str(e)


# =========================================================
# MINECRAFT STATUS
# =========================================================

async def get_minecraft_status():

    def get_status():

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
            asyncio.to_thread(get_status),
            timeout=8
        )

        return result

    except Exception as e:

        print(
            f"[MC STATUS ERROR] {repr(e)}"
        )

        return {
            "online": False,
            "players": 0,
            "max_players": 0,
            "version": "Offline",
            "ping": 0,
        }


# =========================================================
# BOT READY + SLASH COMMAND SYNC
# =========================================================

@bot.event
async def on_ready():

    print("")
    print("=" * 60)
    print(f"Logged in as: {bot.user}")
    print(f"Bot ID: {bot.user.id}")
    print(f"Guild ID: {GUILD_ID}")
    print("=" * 60)

    guild = discord.Object(
        id=GUILD_ID
    )

    try:

        # نحذف أوامر Guild القديمة
        bot.tree.clear_commands(
            guild=guild
        )

        # ننسخ أوامر الكود الحالية إلى Guild
        bot.tree.copy_global_to(
            guild=guild
        )

        # نسجلها مباشرة في السيرفر
        synced = await bot.tree.sync(
            guild=guild
        )

        print("")
        print(
            f"SUCCESS: Synced "
            f"{len(synced)} commands"
        )

        for command in synced:
            print(
                f"  /{command.name}"
            )

        print("")
        print("=" * 60)

    except Exception as e:

        print("")
        print(
            "[COMMAND SYNC ERROR]"
        )
        print(
            repr(e)
        )
        print("")
        print("=" * 60)


# =========================================================
# /server
# =========================================================

@bot.tree.command(
    name="server",
    description="عرض حالة سيرفر Minecraft"
)
async def server_command(
    interaction: discord.Interaction
):

    print(
        f"[COMMAND] /server "
        f"-> {interaction.user} "
        f"({interaction.user.id})"
    )

    await interaction.response.defer()

    status = await get_minecraft_status()

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
            value=(
                f"`{MC_HOST}:{MC_PORT}`"
            ),
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
            value=(
                f"`{MC_HOST}:{MC_PORT}`"
            ),
            inline=False
        )

    await interaction.followup.send(
        embed=embed
    )


# =========================================================
# POWER COMMAND
# =========================================================

async def execute_power_command(
    interaction: discord.Interaction,
    signal: str,
    emoji: str,
    title: str
):

    print(
        f"[COMMAND] /{signal} "
        f"-> {interaction.user} "
        f"({interaction.user.id})"
    )

    # صلاحية المالك
    if not is_owner(
        interaction.user.id
    ):

        await interaction.response.send_message(
            "❌ ليس لديك صلاحية استخدام هذا الأمر.",
            ephemeral=True
        )

        print(
            f"[DENIED] {interaction.user.id}"
        )

        return

    # نرد مباشرة حتى لا يحصل Interaction Timeout
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
                f"تم إرسال أمر "
                f"`{signal}` بنجاح إلى السيرفر."
            ),
            color=discord.Color.green()
        )

        embed.add_field(
            name="Server",
            value="`Firstmc`",
            inline=True
        )

        embed.add_field(
            name="Server ID",
            value=f"`{PARTNER_SERVER_ID}`",
            inline=True
        )

        await interaction.followup.send(
            embed=embed,
            ephemeral=True
        )

    else:

        embed = discord.Embed(
            title="❌ فشل تنفيذ الأمر",
            color=discord.Color.red()
        )

        embed.add_field(
            name="الخطأ",
            value=f"```{result[:1500]}```",
            inline=False
        )

        await interaction.followup.send(
            embed=embed,
            ephemeral=True
        )


# =========================================================
# /start
# =========================================================

@bot.tree.command(
    name="start",
    description="تشغيل سيرفر Minecraft"
)
async def start_command(
    interaction: discord.Interaction
):

    await execute_power_command(
        interaction,
        "start",
        "🟢",
        "Starting FirstMC"
    )


# =========================================================
# /stop
# =========================================================

@bot.tree.command(
    name="stop",
    description="إيقاف سيرفر Minecraft"
)
async def stop_command(
    interaction: discord.Interaction
):

    await execute_power_command(
        interaction,
        "stop",
        "🔴",
        "Stopping FirstMC"
    )


# =========================================================
# /restart
# =========================================================

@bot.tree.command(
    name="restart",
    description="إعادة تشغيل سيرفر Minecraft"
)
async def restart_command(
    interaction: discord.Interaction
):

    await execute_power_command(
        interaction,
        "restart",
        "🔄",
        "Restarting FirstMC"
    )


# =========================================================
# /chat-minecraft
# =========================================================

@bot.tree.command(
    name="chat-minecraft",
    description="تحديد روم Minecraft Chat"
)
async def chat_minecraft_command(
    interaction: discord.Interaction
):

    print(
        f"[COMMAND] /chat-minecraft "
        f"-> {interaction.user}"
    )

    if not is_owner(
        interaction.user.id
    ):

        await interaction.response.send_message(
            "❌ ليس لديك صلاحية استخدام هذا الأمر.",
            ephemeral=True
        )

        return

    global MINE_CHAT_CHANNEL_ID

    MINE_CHAT_CHANNEL_ID = (
        interaction.channel_id
    )

    await interaction.response.send_message(
        "✅ تم تحديد هذا الروم "
        "كروم Minecraft Chat.\n\n"
        f"Channel ID: `{interaction.channel_id}`"
    )

    print(
        f"[CHAT CHANNEL] "
        f"{interaction.channel_id}"
    )


# =========================================================
# ERROR HANDLER
# =========================================================

@bot.tree.error
async def command_error(
    interaction: discord.Interaction,
    error: app_commands.AppCommandError
):

    print("")
    print(
        "[SLASH COMMAND ERROR]"
    )
    print(
        repr(error)
    )
    print("")

    try:

        message = (
            "❌ حدث خطأ أثناء تنفيذ الأمر.\n"
            f"`{str(error)[:1000]}`"
        )

        if interaction.response.is_done():

            await interaction.followup.send(
                message,
                ephemeral=True
            )

        else:

            await interaction.response.send_message(
                message,
                ephemeral=True
            )

    except Exception as e:

        print(
            "[ERROR HANDLER ERROR]",
            repr(e)
        )


# =========================================================
# DISCORD GLOBAL ERROR
# =========================================================

@bot.event
async def on_error(
    event,
    *args,
    **kwargs
):

    import traceback

    print(
        f"[GLOBAL ERROR] {event}"
    )

    traceback.print_exc()


# =========================================================
# START BOT
# =========================================================

if not DISCORD_TOKEN:

    raise RuntimeError(
        "DISCORD_TOKEN غير موجود في Railway Variables."
    )


print("")
print("Starting FirstMC Bot...")
print("")


bot.run(
    DISCORD_TOKEN
)
