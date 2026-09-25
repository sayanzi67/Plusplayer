import os
import asyncio
from datetime import datetime, timezone

import aiohttp
from aiohttp import web
import discord
from discord.ext import commands
from discord import app_commands


# =========================
# ENVIRONMENT VARIABLES
# =========================

TOKEN = os.getenv("DISCORD_TOKEN")
BRIDGE_SECRET = os.getenv("BRIDGE_SECRET")

GUILD_ID = int(os.getenv("GUILD_ID", "1550471340610289795"))

MINE_CHAT_CHANNEL_ID = int(
    os.getenv("MINE_CHAT_CHANNEL_ID", "1552794391247192084")
)

STATS_CHANNEL_ID = int(
    os.getenv("STATS_CHANNEL_ID", "1552794085637488690")
)

PARTNER_PANEL_URL = os.getenv(
    "PARTNER_PANEL_URL",
    "https://panel.partner-hosting.com"
)

PARTNER_SERVER_ID = os.getenv(
    "PARTNER_SERVER_ID",
    "a594dd95"
)

PARTNER_API_KEY = os.getenv("PARTNER_API_KEY")

MC_HOST = os.getenv("MC_HOST", "95.156.225.24")
MC_PORT = os.getenv("MC_PORT", "26383")

BEDROCK_HOST = os.getenv("BEDROCK_HOST", "95.156.225.24")
BEDROCK_PORT = os.getenv("BEDROCK_PORT", "29510")


# =========================
# OWNERS
# =========================

OWNERS = {
    1446592341908652112,
    1476170066327371798,
    1499456366325010552,
    1011294015200706611,
}


# =========================
# MINECRAFT STATUS
# =========================

minecraft_status = {
    "online": False,
    "players": 0,
    "max_players": 100,
    "player_names": [],
    "updated": None,
}


# =========================
# DISCORD BOT
# =========================

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)


# =========================
# HELPERS
# =========================

def owner_only(interaction: discord.Interaction) -> bool:
    return interaction.user.id in OWNERS


async def partner_power(signal: str):
    if not PARTNER_API_KEY:
        return False, "PARTNER_API_KEY غير موجود في Railway."

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

                if response.status in (200, 202, 204):
                    return True, "OK"

                text = await response.text()
                return False, f"HTTP {response.status}: {text[:300]}"

    except Exception as e:
        return False, str(e)


# =========================
# WEB SERVER
# =========================

async def bridge_secret_ok(request):
    if not BRIDGE_SECRET:
        return False

    received = request.headers.get("X-Bridge-Secret")

    return (
        received is not None
        and received == BRIDGE_SECRET
    )


async def minecraft_status_endpoint(request):
    if not await bridge_secret_ok(request):
        return web.json_response(
            {"error": "Unauthorized"},
            status=401
        )

    try:
        data = await request.json()

        online = int(data.get("online", 0))
        max_players = int(data.get("max", 100))

        players = data.get("players", "")

        if isinstance(players, list):
            player_names = [
                str(x)[:32]
                for x in players
            ]
        else:
            player_names = [
                x.strip()[:32]
                for x in str(players).split(",")
                if x.strip()
            ]

        minecraft_status["online"] = True
        minecraft_status["players"] = max(0, online)
        minecraft_status["max_players"] = max(
            1,
            max_players
        )
        minecraft_status["player_names"] = player_names
        minecraft_status["updated"] = datetime.now(
            timezone.utc
        ).isoformat()

        return web.json_response({
            "success": True
        })

    except Exception as e:
        return web.json_response(
            {
                "success": False,
                "error": str(e)
            },
            status=400
        )


async def minecraft_pending_endpoint(request):
    if not await bridge_secret_ok(request):
        return web.json_response(
            {"error": "Unauthorized"},
            status=401
        )

    messages = getattr(
        minecraft_pending_endpoint,
        "messages",
        []
    )

    minecraft_pending_endpoint.messages = []

    return web.json_response({
        "messages": messages
    })


minecraft_pending_endpoint.messages = []


async def minecraft_chat_endpoint(request):
    if not await bridge_secret_ok(request):
        return web.json_response(
            {"error": "Unauthorized"},
            status=401
        )

    try:
        data = await request.json()

        player = str(
            data.get("player", "Minecraft")
        )[:32]

        message = str(
            data.get("message", "")
        )[:500]

        if not message.strip():
            return web.json_response(
                {"success": False},
                status=400
            )

        channel = bot.get_channel(
            MINE_CHAT_CHANNEL_ID
        )

        if channel is None:
            return web.json_response(
                {
                    "success": False,
                    "error": "Discord channel not found"
                },
                status=404
            )

        await channel.send(
            f"**{player}** » {message}"
        )

        return web.json_response({
            "success": True
        })

    except Exception as e:
        return web.json_response(
            {
                "success": False,
                "error": str(e)
            },
            status=400
        )


async def health_endpoint(request):
    return web.json_response({
        "status": "online",
        "bot": str(bot.user) if bot.user else None,
        "minecraft_online": minecraft_status["online"]
    })


async def start_web_server():
    app = web.Application()

    app.router.add_get(
        "/",
        health_endpoint
    )

    app.router.add_get(
        "/minecraft/pending",
        minecraft_pending_endpoint
    )

    app.router.add_post(
        "/minecraft/status",
        minecraft_status_endpoint
    )

    app.router.add_post(
        "/minecraft/chat",
        minecraft_chat_endpoint
    )

    port = int(
        os.getenv("PORT", "8080")
    )

    runner = web.AppRunner(app)

    await runner.setup()

    site = web.TCPSite(
        runner,
        "0.0.0.0",
        port
    )

    await site.start()

    print(f"Web server listening on port {port}")


# =========================
# DISCORD -> MINECRAFT QUEUE
# =========================

@bot.event
async def on_message(message: discord.Message):

    if message.author.bot:
        return

    if message.channel.id == MINE_CHAT_CHANNEL_ID:

        text = message.content.strip()

        if text:

            minecraft_pending_endpoint.messages.append({
                "player": str(message.author),
                "message": text[:500]
            })

    await bot.process_commands(message)


# =========================
# READY
# =========================

@bot.event
async def on_ready():

    print(f"Logged in as {bot.user}")

    guild = discord.Object(id=GUILD_ID)

    bot.tree.clear_commands(guild=guild)

    bot.tree.copy_global_to(guild=guild)

    synced = await bot.tree.sync(
        guild=guild
    )

    print(
        f"Synced {len(synced)} guild commands"
    )


# =========================
# /SERVER
# =========================

@bot.tree.command(
    name="server",
    description="عرض حالة سيرفر FirstMC"
)
async def server_command(
    interaction: discord.Interaction
):

    if not minecraft_status["online"]:
        embed = discord.Embed(
            title="🔴 SERVER OFFLINE",
            description=(
                "السيرفر غير متصل حاليًا "
                "أو لم تصل بيانات الحالة بعد."
            ),
            color=discord.Color.red()
        )

        embed.add_field(
            name="🎮 Version",
            value="1.18-1.21.11",
            inline=False
        )

        embed.add_field(
            name="🌐 Java",
            value=f"`{MC_HOST}:{MC_PORT}`",
            inline=False
        )

        embed.add_field(
            name="🟢 Bedrock",
            value=f"`{BEDROCK_HOST}:{BEDROCK_PORT}`",
            inline=False
        )

        await interaction.response.send_message(
            embed=embed
        )

        return

    online = minecraft_status["players"]
    maximum = minecraft_status["max_players"]

    embed = discord.Embed(
        title="🟢 SERVER ONLINE",
        color=discord.Color.green()
    )

    embed.add_field(
        name="👥 Players",
        value=f"**{online} / {maximum}**",
        inline=False
    )

    embed.add_field(
        name="⚡ Ping",
        value="Connected",
        inline=False
    )

    embed.add_field(
        name="🎮 Version",
        value="1.18-1.21.11",
        inline=False
    )

    embed.add_field(
        name="🌐 Java",
        value=f"`{MC_HOST}:{MC_PORT}`",
        inline=False
    )

    embed.add_field(
        name="🟢 Bedrock",
        value=f"`{BEDROCK_HOST}:{BEDROCK_PORT}`",
        inline=False
    )

    players = minecraft_status["player_names"]

    if players:
        names = "\n".join(
            f"• {name}"
            for name in players[:20]
        )

        embed.add_field(
            name="👤 Online Players",
            value=names,
            inline=False
        )

    await interaction.response.send_message(
        embed=embed
    )


# =========================
# /START
# =========================

@bot.tree.command(
    name="start",
    description="تشغيل سيرفر FirstMC"
)
async def start_command(
    interaction: discord.Interaction
):

    if not owner_only(interaction):
        await interaction.response.send_message(
            "❌ هذا الأمر للـOwners فقط.",
            ephemeral=True
        )
        return

    await interaction.response.defer(
        ephemeral=True
    )

    success, result = await partner_power(
        "start"
    )

    if success:
        await interaction.followup.send(
            "🟢 تم إرسال أمر تشغيل السيرفر."
        )
    else:
        await interaction.followup.send(
            f"❌ فشل التشغيل:\n`{result}`"
        )


# =========================
# /STOP
# =========================

@bot.tree.command(
    name="stop",
    description="إيقاف سيرفر FirstMC"
)
async def stop_command(
    interaction: discord.Interaction
):

    if not owner_only(interaction):
        await interaction.response.send_message(
            "❌ هذا الأمر للـOwners فقط.",
            ephemeral=True
        )
        return

    await interaction.response.defer(
        ephemeral=True
    )

    success, result = await partner_power(
        "stop"
    )

    if success:
        await interaction.followup.send(
            "🔴 تم إرسال أمر إيقاف السيرفر."
        )
    else:
        await interaction.followup.send(
            f"❌ فشل الإيقاف:\n`{result}`"
        )


# =========================
# /RESTART
# =========================

@bot.tree.command(
    name="restart",
    description="إعادة تشغيل سيرفر FirstMC"
)
async def restart_command(
    interaction: discord.Interaction
):

    if not owner_only(interaction):
        await interaction.response.send_message(
            "❌ هذا الأمر للـOwners فقط.",
            ephemeral=True
        )
        return

    await interaction.response.defer(
        ephemeral=True
    )

    success, result = await partner_power(
        "restart"
    )

    if success:
        await interaction.followup.send(
            "🔄 تم إرسال أمر إعادة تشغيل السيرفر."
        )
    else:
        await interaction.followup.send(
            f"❌ فشل إعادة التشغيل:\n`{result}`"
        )


# =========================
# /CHAT-MINECRAFT
# =========================

@bot.tree.command(
    name="chat-minecraft",
    description="إرسال رسالة إلى Minecraft"
)
@app_commands.describe(
    message="الرسالة التي تريد إرسالها"
)
async def chat_minecraft_command(
    interaction: discord.Interaction,
    message: str
):

    if not owner_only(interaction):
        await interaction.response.send_message(
            "❌ هذا الأمر للـOwners فقط.",
            ephemeral=True
        )
        return

    message = message.strip()[:500]

    if not message:
        await interaction.response.send_message(
            "❌ الرسالة فارغة.",
            ephemeral=True
        )
        return

    minecraft_pending_endpoint.messages.append({
        "player": str(interaction.user),
        "message": message
    })

    await interaction.response.send_message(
        "✅ تم إرسال الرسالة إلى Minecraft.",
        ephemeral=True
    )


# =========================
# START
# =========================

async def main():

    if not TOKEN:
        raise RuntimeError(
            "DISCORD_TOKEN غير موجود في Railway Variables."
        )

    await start_web_server()

    await bot.start(TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
