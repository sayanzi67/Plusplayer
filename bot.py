import os
import time
import asyncio
from datetime import datetime, timezone

import discord
from discord.ext import commands
from discord import app_commands
from aiohttp import web
from mcstatus import JavaServer

# =========================
# CONFIG
# =========================

TOKEN = os.getenv("DISCORD_TOKEN")

MC_HOST = os.getenv("MC_HOST", "YOUR_SERVER_IP")
MC_PORT = int(os.getenv("MC_PORT", "25565"))

CHAT_CHANNEL_ID = 1551824169291882628

ALLOWED_USERS = {
    1446592341908652112,
    1476170066327371798,
    1499456366325010552,
    1011294015200706611,
}

SERVER_NAME = "𝐅𝐢𝐫𝐬𝐭-𝐦𝐜"
SERVER_VERSION = "1.18 - 1.21.11"

MAX_PLAYERS = 100

BOT_START = time.time()

# =========================
# DISCORD
# =========================

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)


# =========================
# MINECRAFT STATUS
# =========================

async def get_server_status():

    def check():
        try:
            server = JavaServer.lookup(
                f"{MC_HOST}:{MC_PORT}"
            )

            status = server.status()

            return {
                "online": True,
                "players": status.players.online,
                "max": status.players.max,
                "ping": round(status.latency),
                "version": status.version.name,
                "names": [
                    p.name
                    for p in (status.players.sample or [])
                    if p.name
                ]
            }

        except Exception:
            return {
                "online": False,
                "players": 0,
                "max": MAX_PLAYERS,
                "ping": 0,
                "version": SERVER_VERSION,
                "names": []
            }

    return await asyncio.to_thread(check)


def uptime():

    seconds = int(time.time() - BOT_START)

    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)

    if days:
        return f"{days}d {hours}h {minutes}m"

    if hours:
        return f"{hours}h {minutes}m"

    return f"{minutes}m {seconds}s"


async def create_server_embed():

    data = await get_server_status()

    if data["online"]:
        stats = "🟢 Online"
        ping = f"{data['ping']}ms"
    else:
        stats = "🔴 Offline"
        ping = "N/A"

    embed = discord.Embed(
        title=SERVER_NAME,
        color=(
            discord.Color.green()
            if data["online"]
            else discord.Color.red()
        )
    )

    embed.description = (
        f"📊 Stats: {stats}\n"
        f"👥 Players Online: {data['players']}/{data['max']}\n"
        f"🎮 Version: {SERVER_VERSION}\n"
        f"⏱️ Uptime: {uptime()}\n"
        f"📶 Ping: {ping}\n\n"
        f"Last Update: <t:{int(time.time())}:R>"
    )

    return embed


# =========================
# REFRESH BUTTON
# =========================

class RefreshView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Refresh",
        emoji="🔄",
        style=discord.ButtonStyle.secondary,
        custom_id="firstmc_refresh"
    )
    async def refresh(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        embed = await create_server_embed()

        await interaction.response.edit_message(
            embed=embed,
            view=RefreshView()
        )


# =========================
# READY
# =========================

@bot.event
async def on_ready():

    print(f"Logged in as {bot.user}")

    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} commands")

    except Exception as e:
        print("Command sync error:", e)

    bot.add_view(RefreshView())


# =========================
# /server
# =========================

@bot.tree.command(
    name="server",
    description="عرض حالة سيرفر First-mc"
)
async def server(interaction: discord.Interaction):

    embed = await create_server_embed()

    await interaction.response.send_message(
        embed=embed,
        view=RefreshView()
    )


# =========================
# /players
# =========================

@bot.tree.command(
    name="players",
    description="عرض اللاعبين الموجودين في First-mc"
)
async def players(interaction: discord.Interaction):

    data = await get_server_status()

    if not data["online"]:
        await interaction.response.send_message(
            "🔴 السيرفر Offline."
        )
        return

    if not data["names"]:
        names = "لا يوجد لاعبين حاليًا."
    else:
        names = "\n".join(
            f"• {name}"
            for name in data["names"]
        )

    embed = discord.Embed(
        title="𝐅𝐢𝐫𝐬𝐭-𝐦𝐜",
        description=(
            f"👥 Players Online: "
            f"{data['players']}/{data['max']}\n\n"
            f"{names}"
        ),
        color=discord.Color.green()
    )

    await interaction.response.send_message(
        embed=embed
    )


# =========================
# PERMISSION
# =========================

def allowed(user_id):

    return user_id in ALLOWED_USERS


# =========================
# START
# =========================

@bot.tree.command(
    name="start",
    description="تشغيل السيرفر"
)
async def start(interaction: discord.Interaction):

    if not allowed(interaction.user.id):

        await interaction.response.send_message(
            "❌ ليس لديك صلاحية استخدام هذا الأمر.",
            ephemeral=True
        )

        return

    await interaction.response.send_message(
        "🟢 جاري تشغيل First-mc..."
    )

    # سيتم ربطه بـ API الاستضافة لاحقًا


# =========================
# STOP
# =========================

@bot.tree.command(
    name="stop",
    description="إيقاف السيرفر"
)
async def stop(interaction: discord.Interaction):

    if not allowed(interaction.user.id):

        await interaction.response.send_message(
            "❌ ليس لديك صلاحية استخدام هذا الأمر.",
            ephemeral=True
        )

        return

    await interaction.response.send_message(
        "🔴 جاري إيقاف First-mc..."
    )

    # سيتم ربطه بـ API الاستضافة لاحقًا


# =========================
# RESTART
# =========================

@bot.tree.command(
    name="restart",
    description="إعادة تشغيل السيرفر"
)
async def restart(interaction: discord.Interaction):

    if not allowed(interaction.user.id):

        await interaction.response.send_message(
            "❌ ليس لديك صلاحية استخدام هذا الأمر.",
            ephemeral=True
        )

        return

    await interaction.response.send_message(
        "🔄 جاري إعادة تشغيل First-mc..."
    )

    # سيتم ربطه بـ API الاستضافة لاحقًا


# =========================
# MINECRAFT → DISCORD
# =========================

async def minecraft_message(
    player,
    message
):

    channel = bot.get_channel(
        CHAT_CHANNEL_ID
    )

    if channel is None:
        return

    embed = discord.Embed(
        description=message,
        color=discord.Color.blurple()
    )

    embed.set_author(
        name=player
    )

    await channel.send(
        embed=embed
    )


# =========================
# HTTP API
# =========================

async def mc_chat(request):

    try:

        data = await request.json()

        player = data.get("player")
        message = data.get("message")

        if not player or not message:
            return web.json_response(
                {"error": "missing data"},
                status=400
            )

        await minecraft_message(
            player,
            message
        )

        return web.json_response(
            {"success": True}
        )

    except Exception as e:

        print("Minecraft chat error:", e)

        return web.json_response(
            {"error": "server error"},
            status=500
        )


async def health(request):

    return web.json_response(
        {"status": "online"}
    )


# =========================
# WEB SERVER
# =========================

async def start_web():

    app = web.Application()

    app.router.add_post(
        "/minecraft/chat",
        mc_chat
    )

    app.router.add_get(
        "/",
        health
    )

    runner = web.AppRunner(app)

    await runner.setup()

    port = int(
        os.getenv("PORT", "8080")
    )

    site = web.TCPSite(
        runner,
        "0.0.0.0",
        port
    )

    await site.start()

    print(
        f"Web server started on port {port}"
    )


# =========================
# START EVERYTHING
# =========================

async def main():

    await start_web()

    await bot.start(TOKEN)


asyncio.run(main())
