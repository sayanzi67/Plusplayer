import os
import asyncio
import time
from collections import deque

import aiohttp
from aiohttp import web
import discord
from discord.ext import commands
from discord import app_commands
from mcstatus import JavaServer


# =========================================================
# CONFIG
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

BEDROCK_HOST = os.getenv(
    "BEDROCK_HOST",
    "95.156.225.24"
)

BEDROCK_PORT = int(
    os.getenv("BEDROCK_PORT", "29510")
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

# Web API secret
BRIDGE_SECRET = os.getenv(
    "BRIDGE_SECRET",
    "CHANGE_THIS_SECRET"
)

# Railway PORT
WEB_PORT = int(
    os.getenv("PORT", "8080")
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
# BOT
# =========================================================

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)


# =========================================================
# CHAT QUEUE
# =========================================================

minecraft_queue = deque(maxlen=100)

last_chat_message = {}


# =========================================================
# OWNER CHECK
# =========================================================

def is_owner(user_id: int) -> bool:
    return user_id in OWNER_IDS


# =========================================================
# PARTNER HOST POWER
# =========================================================

async def partner_power(signal: str):

    if not PARTNER_API_KEY:
        return False, "PARTNER_API_KEY غير موجود في Railway."

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

                body = await response.text()

                print(
                    f"[PARTNER] "
                    f"{signal.upper()} "
                    f"HTTP {response.status}"
                )

                if response.status in (200, 204):
                    return True, "OK"

                return False, (
                    f"HTTP {response.status}\n"
                    f"{body[:1000]}"
                )

    except Exception as e:

        print(
            "[PARTNER ERROR]",
            repr(e)
        )

        return False, str(e)


# =========================================================
# MINECRAFT STATUS
# =========================================================

async def get_mc_status():

    def check():

        server = JavaServer.lookup(
            f"{MC_HOST}:{MC_PORT}"
        )

        status = server.status()

        return {
            "online": True,
            "players": status.players.online,
            "max_players": status.players.max,
            "ping": round(status.latency),
        }

    try:

        result = await asyncio.wait_for(
            asyncio.to_thread(check),
            timeout=8
        )

        return result

    except Exception as e:

        print(
            "[MC STATUS ERROR]",
            repr(e)
        )

        return {
            "online": False,
            "players": 0,
            "max_players": 0,
            "ping": 0,
        }


# =========================================================
# SERVER EMBED
# =========================================================

async def create_server_embed():

    status = await get_mc_status()

    if status["online"]:

        embed = discord.Embed(
            title="FirstMC Network",
            description=(
                "```ansi\n"
                "\u001b[1;32m🟢 SERVER ONLINE\u001b[0m\n"
                "```"
            ),
            color=discord.Color.green()
        )

        embed.add_field(
            name="👥 Players",
            value=(
                f"**{status['players']} / "
                f"{status['max_players']}**"
            ),
            inline=False
        )

        embed.add_field(
            name="⚡ Ping",
            value=f"**{status['ping']}ms**",
            inline=True
        )

        embed.add_field(
            name="🎮 Version",
            value="**1.18-1.21.11**",
            inline=True
        )

        embed.add_field(
            name="🌐 Java",
            value=(
                f"`{MC_HOST}:{MC_PORT}`"
            ),
            inline=False
        )

        embed.add_field(
            name="🟢 Bedrock",
            value=(
                f"`{BEDROCK_HOST}:{BEDROCK_PORT}`"
            ),
            inline=False
        )

    else:

        embed = discord.Embed(
            title="FirstMC Network",
            description=(
                "```ansi\n"
                "\u001b[1;31m🔴 SERVER OFFLINE\u001b[0m\n"
                "```"
            ),
            color=discord.Color.red()
        )

        embed.add_field(
            name="👥 Players",
            value="**0 / —**",
            inline=False
        )

        embed.add_field(
            name="⚡ Ping",
            value="**—**",
            inline=True
        )

        embed.add_field(
            name="🎮 Version",
            value="**1.18-1.21.11**",
            inline=True
        )

        embed.add_field(
            name="🌐 Java",
            value=(
                f"`{MC_HOST}:{MC_PORT}`"
            ),
            inline=False
        )

        embed.add_field(
            name="🟢 Bedrock",
            value=(
                f"`{BEDROCK_HOST}:{BEDROCK_PORT}`"
            ),
            inline=False
        )

    embed.set_footer(
        text="FirstMC Network • Server Status"
    )

    return embed


# =========================================================
# SERVER BUTTON
# =========================================================

class ServerView(discord.ui.View):

    def __init__(self):
        super().__init__(
            timeout=None
        )

    @discord.ui.button(
        label="Refresh",
        emoji="🔄",
        style=discord.ButtonStyle.secondary,
        custom_id="firstmc_server_refresh"
    )
    async def refresh(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        print(
            f"[REFRESH] "
            f"{interaction.user} "
            f"({interaction.user.id})"
        )

        embed = await create_server_embed()

        await interaction.response.edit_message(
            embed=embed,
            view=self
        )


# =========================================================
# READY / COMMAND SYNC
# =========================================================

@bot.event
async def on_ready():

    print("=" * 60)
    print(
        f"Logged in as {bot.user} "
        f"({bot.user.id})"
    )
    print("=" * 60)

    guild = discord.Object(
        id=GUILD_ID
    )

    try:

        # تنظيف أوامر Guild القديمة
        bot.tree.clear_commands(
            guild=guild
        )

        # نسخ الأوامر الحالية
        bot.tree.copy_global_to(
            guild=guild
        )

        synced = await bot.tree.sync(
            guild=guild
        )

        print(
            f"[SYNC] {len(synced)} commands"
        )

        for command in synced:
            print(
                f"[SYNC] /{command.name}"
            )

        print("=" * 60)

    except Exception as e:

        print(
            "[SYNC ERROR]",
            repr(e)
        )

    # Persistent button
    bot.add_view(
        ServerView()
    )


# =========================================================
# /SERVER
# =========================================================

@bot.tree.command(
    name="server",
    description="عرض حالة سيرفر FirstMC"
)
async def server_command(
    interaction: discord.Interaction
):

    print(
        f"[COMMAND] /server "
        f"{interaction.user.id}"
    )

    await interaction.response.defer()

    embed = await create_server_embed()

    await interaction.followup.send(
        embed=embed,
        view=ServerView()
    )


# =========================================================
# POWER COMMAND
# =========================================================

async def power_command(
    interaction: discord.Interaction,
    signal: str,
    emoji: str,
    title: str
):

    print(
        f"[COMMAND] /{signal} "
        f"{interaction.user.id}"
    )

    # Owners only
    if not is_owner(
        interaction.user.id
    ):

        await interaction.response.send_message(
            "❌ هذا الأمر للـOwners فقط.",
            ephemeral=True
        )

        print(
            f"[DENIED] /{signal} "
            f"{interaction.user.id}"
        )

        return

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
                f"تم تنفيذ `{signal}` بنجاح."
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
            title="❌ Power Error",
            description=(
                "فشل تنفيذ الأمر."
            ),
            color=discord.Color.red()
        )

        embed.add_field(
            name="Error",
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
    description="تشغيل السيرفر"
)
async def start_command(
    interaction: discord.Interaction
):

    await power_command(
        interaction,
        "start",
        "🟢",
        "Starting FirstMC"
    )


# =========================================================
# /STOP
# =========================================================

@bot.tree.command(
    name="stop",
    description="إيقاف السيرفر"
)
async def stop_command(
    interaction: discord.Interaction
):

    await power_command(
        interaction,
        "stop",
        "🔴",
        "Stopping FirstMC"
    )


# =========================================================
# /RESTART
# =========================================================

@bot.tree.command(
    name="restart",
    description="إعادة تشغيل السيرفر"
)
async def restart_command(
    interaction: discord.Interaction
):

    await power_command(
        interaction,
        "restart",
        "🔄",
        "Restarting FirstMC"
    )


# =========================================================
# /CHAT-MINECRAFT
# =========================================================

@bot.tree.command(
    name="chat-minecraft",
    description="تحديد روم شات Minecraft"
)
async def chat_minecraft_command(
    interaction: discord.Interaction
):

    global MINE_CHAT_CHANNEL_ID

    print(
        f"[COMMAND] /chat-minecraft "
        f"{interaction.user.id}"
    )

    if not is_owner(
        interaction.user.id
    ):

        await interaction.response.send_message(
            "❌ هذا الأمر للـOwners فقط.",
            ephemeral=True
        )

        return

    MINE_CHAT_CHANNEL_ID = (
        interaction.channel_id
    )

    await interaction.response.send_message(
        "✅ تم تفعيل Minecraft Chat هنا."
    )

    print(
        f"[CHAT] Channel = "
        f"{MINE_CHAT_CHANNEL_ID}"
    )


# =========================================================
# DISCORD → MINECRAFT
# =========================================================

@bot.event
async def on_message(
    message: discord.Message
):

    # لا نتعامل مع رسائل البوتات
    if message.author.bot:
        return

    # Discord Chat → Minecraft
    if (
        message.channel.id
        == MINE_CHAT_CHANNEL_ID
    ):

        content = message.content.strip()

        if content:

            minecraft_queue.append({
                "author": message.author.display_name,
                "message": content,
                "timestamp": int(time.time())
            })

            print(
                f"[DISCORD -> MC] "
                f"{message.author.display_name}: "
                f"{content}"
            )

    await bot.process_commands(
        message
    )


# =========================================================
# API AUTH
# =========================================================

def check_bridge_secret(request):

    provided = request.headers.get(
        "X-Bridge-Secret"
    )

    return (
        provided
        and BRIDGE_SECRET
        and provided == BRIDGE_SECRET
    )


# =========================================================
# GET PENDING DISCORD MESSAGES
# Minecraft plugin calls this
# =========================================================

async def api_pending(request):

    if not check_bridge_secret(request):

        return web.json_response(
            {
                "error": "unauthorized"
            },
            status=401
        )

    messages = []

    while minecraft_queue:

        messages.append(
            minecraft_queue.popleft()
        )

    return web.json_response({
        "messages": messages
    })


# =========================================================
# MC → DISCORD
# Minecraft plugin sends chat here
# =========================================================

async def api_minecraft_chat(request):

    if not check_bridge_secret(request):

        return web.json_response(
            {
                "error": "unauthorized"
            },
            status=401
        )

    try:

        data = await request.json()

    except Exception:

        return web.json_response(
            {
                "error": "invalid_json"
            },
            status=400
        )

    player = str(
        data.get(
            "player",
            "Minecraft"
        )
    ).strip()

    message = str(
        data.get(
            "message",
            ""
        )
    ).strip()

    if not message:

        return web.json_response(
            {
                "error": "empty_message"
            },
            status=400
        )

    channel = bot.get_channel(
        MINE_CHAT_CHANNEL_ID
    )

    if channel is None:

        try:

            channel = await bot.fetch_channel(
                MINE_CHAT_CHANNEL_ID
            )

        except Exception as e:

            print(
                "[MC -> DISCORD] "
                "Channel error:",
                repr(e)
            )

            return web.json_response(
                {
                    "error": "channel_not_found"
                },
                status=404
            )

    try:

        await channel.send(
            f"**{player}** » {message}"
        )

        print(
            f"[MC -> DISCORD] "
            f"{player}: {message}"
        )

        return web.json_response({
            "success": True
        })

    except Exception as e:

        print(
            "[MC -> DISCORD ERROR]",
            repr(e)
        )

        return web.json_response(
            {
                "error": str(e)
            },
            status=500
        )


# =========================================================
# API STATUS
# =========================================================

async def api_status(request):

    return web.json_response({
        "bot": "online",
        "server_id": PARTNER_SERVER_ID,
        "minecraft": f"{MC_HOST}:{MC_PORT}",
        "bedrock": f"{BEDROCK_HOST}:{BEDROCK_PORT}"
    })


# =========================================================
# WEB SERVER
# =========================================================

async def start_web_server():

    app = web.Application()

    app.router.add_get(
        "/",
        api_status
    )

    app.router.add_get(
        "/minecraft/pending",
        api_pending
    )

    app.router.add_post(
        "/minecraft/chat",
        api_minecraft_chat
    )

    runner = web.AppRunner(
        app
    )

    await runner.setup()

    site = web.TCPSite(
        runner,
        "0.0.0.0",
        WEB_PORT
    )

    await site.start()

    print(
        f"[WEB] Listening on port "
        f"{WEB_PORT}"
    )


# =========================================================
# COMMAND ERROR
# =========================================================

@bot.tree.error
async def command_error(
    interaction: discord.Interaction,
    error: app_commands.AppCommandError
):

    print(
        "[COMMAND ERROR]",
        repr(error)
    )

    try:

        text = (
            "❌ حدث خطأ:\n"
            f"`{str(error)[:1000]}`"
        )

        if interaction.response.is_done():

            await interaction.followup.send(
                text,
                ephemeral=True
            )

        else:

            await interaction.response.send_message(
                text,
                ephemeral=True
            )

    except Exception as e:

        print(
            "[ERROR HANDLER ERROR]",
            repr(e)
        )


# =========================================================
# START
# =========================================================

async def main():

    if not DISCORD_TOKEN:

        raise RuntimeError(
            "DISCORD_TOKEN غير موجود."
        )

    if not PARTNER_API_KEY:

        raise RuntimeError(
            "PARTNER_API_KEY غير موجود."
        )

    await start_web_server()

    await bot.start(
        DISCORD_TOKEN
    )


if __name__ == "__main__":

    asyncio.run(
        main()
    )
