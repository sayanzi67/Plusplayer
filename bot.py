import os
import asyncio
from collections import deque
from datetime import datetime, timezone

import aiohttp
from aiohttp import web

import discord
from discord.ext import commands
from discord import app_commands

from mcstatus import JavaServer


# =========================================================
# ENV
# =========================================================

TOKEN = os.getenv("DISCORD_TOKEN")

GUILD_ID = int(os.getenv("GUILD_ID", "0"))
STATS_CHANNEL_ID = int(os.getenv("STATS_CHANNEL_ID", "0"))
MINE_CHAT_CHANNEL_ID = int(os.getenv("MINE_CHAT_CHANNEL_ID", "0"))

MC_HOST = os.getenv("MC_HOST", "")
MC_PORT = int(os.getenv("MC_PORT", "25565"))

BEDROCK_HOST = os.getenv("BEDROCK_HOST", "")
BEDROCK_PORT = int(os.getenv("BEDROCK_PORT", "19132"))

PARTNER_PANEL_URL = os.getenv("PARTNER_PANEL_URL", "").rstrip("/")
PARTNER_SERVER_ID = os.getenv("PARTNER_SERVER_ID", "")
PARTNER_API_KEY = os.getenv("PARTNER_API_KEY", "")


# =========================================================
# SETTINGS
# =========================================================

SERVER_NAME = "𝐅𝐢𝐫𝐬𝐭-𝐦𝐜"
SERVER_VERSION = "1.18 - 1.21.11"
MAX_PLAYERS = 100

OWNERS = {
    1446592341908652112,
    1476170066327371798,
    1499456366325010552,
    1011294015200706611,
}


# =========================================================
# BOT
# =========================================================

intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.presences = True
intents.message_content = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)


# =========================================================
# MINECRAFT CHAT QUEUE
# =========================================================

pending_messages = deque(maxlen=100)


# =========================================================
# HELPERS
# =========================================================

def is_owner(user_id: int) -> bool:
    return user_id in OWNERS


def now_text():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


async def get_minecraft_status():
    """
    يفحص سيرفر Java Minecraft.
    """

    if not MC_HOST:
        return {
            "online": False,
            "players": 0,
            "max": MAX_PLAYERS,
            "ping": 0,
            "version": SERVER_VERSION,
        }

    try:
        server = JavaServer.lookup(f"{MC_HOST}:{MC_PORT}")

        status = await asyncio.wait_for(
            asyncio.to_thread(server.status),
            timeout=5
        )

        players = status.players.online
        maximum = status.players.max or MAX_PLAYERS

        version = SERVER_VERSION

        if getattr(status.version, "name", None):
            version = status.version.name

        return {
            "online": True,
            "players": players,
            "max": maximum,
            "ping": round(status.latency),
            "version": version,
        }

    except Exception as e:
        print(f"[Minecraft Status Error] {type(e).__name__}: {e}")

        return {
            "online": False,
            "players": 0,
            "max": MAX_PLAYERS,
            "ping": 0,
            "version": SERVER_VERSION,
        }


def make_server_embed(data):
    status_text = "🟢 Online" if data["online"] else "🔴 Offline"

    embed = discord.Embed(
        title=f"{SERVER_NAME} :",
        description="",
        color=discord.Color.green() if data["online"] else discord.Color.red()
    )

    embed.add_field(
        name="📊 Stats",
        value=status_text,
        inline=False
    )

    embed.add_field(
        name="👥 Players Online",
        value=f"{data['players']}/{data['max']}",
        inline=True
    )

    embed.add_field(
        name="🎮 Version",
        value=str(data["version"]),
        inline=True
    )

    embed.add_field(
        name="📶 Ping",
        value=f"{data['ping']}ms" if data["online"] else "N/A",
        inline=True
    )

    embed.add_field(
        name="🕐 Last Update",
        value=now_text(),
        inline=False
    )

    embed.set_footer(
        text="First-mc Network"
    )

    return embed


# =========================================================
# REFRESH BUTTON
# =========================================================

class ServerView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Refresh",
        emoji="🔄",
        style=discord.ButtonStyle.primary,
        custom_id="firstmc_server_refresh"
    )
    async def refresh(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        try:
            await interaction.response.defer()

            data = await get_minecraft_status()

            await interaction.edit_original_response(
                embed=make_server_embed(data),
                view=self
            )

        except Exception as e:
            print(f"[Refresh Error] {type(e).__name__}: {e}")

            try:
                if interaction.response.is_done():
                    await interaction.followup.send(
                        "❌ حدث خطأ أثناء تحديث الحالة.",
                        ephemeral=True
                    )
                else:
                    await interaction.response.send_message(
                        "❌ حدث خطأ أثناء تحديث الحالة.",
                        ephemeral=True
                    )
            except Exception:
                pass


# =========================================================
# SERVER COMMAND
# =========================================================

@bot.tree.command(
    name="server",
    description="عرض حالة سيرفر First-mc"
)
async def server_command(interaction: discord.Interaction):

    try:
        # الرد الفوري يمنع Discord من اعتبار الأمر متوقفًا
        await interaction.response.defer()

        data = await get_minecraft_status()

        await interaction.followup.send(
            embed=make_server_embed(data),
            view=ServerView()
        )

    except Exception as e:

        print(
            f"[SERVER COMMAND ERROR] "
            f"{type(e).__name__}: {e}"
        )

        try:
            await interaction.followup.send(
                "❌ حدث خطأ أثناء تنفيذ الأمر.",
                ephemeral=True
            )
        except Exception:
            pass


# =========================================================
# POWER SERVER
# =========================================================

async def power_server(action: str):

    if not PARTNER_PANEL_URL:
        return False, "PARTNER_PANEL_URL غير موجود."

    if not PARTNER_SERVER_ID:
        return False, "PARTNER_SERVER_ID غير موجود."

    if not PARTNER_API_KEY:
        return False, "PARTNER_API_KEY غير موجود."

    url = (
        f"{PARTNER_PANEL_URL}"
        f"/api/client/servers/"
        f"{PARTNER_SERVER_ID}/power"
    )

    headers = {
        "Authorization": f"Bearer {PARTNER_API_KEY}",
        "Accept": "Application/vnd.pterodactyl.v1+json",
        "Content-Type": "application/json",
    }

    payload = {
        "signal": action
    }

    timeout = aiohttp.ClientTimeout(total=15)

    try:

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
                    f"[Power] action={action} "
                    f"status={response.status} "
                    f"body={body[:500]}"
                )

                if response.status in (200, 204):
                    return True, ""

                return False, (
                    f"HTTP {response.status}: "
                    f"{body[:300]}"
                )

    except Exception as e:

        print(
            f"[Power Error] "
            f"{type(e).__name__}: {e}"
        )

        return False, str(e)


# =========================================================
# START
# =========================================================

@bot.tree.command(
    name="start",
    description="تشغيل السيرفر"
)
async def start_command(interaction: discord.Interaction):

    try:

        if not is_owner(interaction.user.id):
            await interaction.response.send_message(
                "❌ ليس لديك صلاحية استخدام هذا الأمر.",
                ephemeral=True
            )
            return

        await interaction.response.defer(
            ephemeral=True
        )

        success, error = await power_server("start")

        if success:
            await interaction.followup.send(
                "🟢 تم إرسال أمر تشغيل السيرفر.",
                ephemeral=True
            )
        else:
            await interaction.followup.send(
                f"❌ فشل تشغيل السيرفر.\n```{error}```",
                ephemeral=True
            )

    except Exception as e:

        print(
            f"[START ERROR] "
            f"{type(e).__name__}: {e}"
        )

        try:
            await interaction.followup.send(
                "❌ حدث خطأ أثناء تنفيذ الأمر.",
                ephemeral=True
            )
        except Exception:
            pass


# =========================================================
# STOP
# =========================================================

@bot.tree.command(
    name="stop",
    description="إيقاف السيرفر"
)
async def stop_command(interaction: discord.Interaction):

    try:

        if not is_owner(interaction.user.id):
            await interaction.response.send_message(
                "❌ ليس لديك صلاحية استخدام هذا الأمر.",
                ephemeral=True
            )
            return

        await interaction.response.defer(
            ephemeral=True
        )

        success, error = await power_server("stop")

        if success:
            await interaction.followup.send(
                "🔴 تم إرسال أمر إيقاف السيرفر.",
                ephemeral=True
            )
        else:
            await interaction.followup.send(
                f"❌ فشل إيقاف السيرفر.\n```{error}```",
                ephemeral=True
            )

    except Exception as e:

        print(
            f"[STOP ERROR] "
            f"{type(e).__name__}: {e}"
        )

        try:
            await interaction.followup.send(
                "❌ حدث خطأ أثناء تنفيذ الأمر.",
                ephemeral=True
            )
        except Exception:
            pass


# =========================================================
# RESTART
# =========================================================

@bot.tree.command(
    name="restart",
    description="إعادة تشغيل السيرفر"
)
async def restart_command(interaction: discord.Interaction):

    try:

        if not is_owner(interaction.user.id):
            await interaction.response.send_message(
                "❌ ليس لديك صلاحية استخدام هذا الأمر.",
                ephemeral=True
            )
            return

        await interaction.response.defer(
            ephemeral=True
        )

        success, error = await power_server("restart")

        if success:
            await interaction.followup.send(
                "🔄 تم إرسال أمر إعادة تشغيل السيرفر.",
                ephemeral=True
            )
        else:
            await interaction.followup.send(
                f"❌ فشل إعادة التشغيل.\n```{error}```",
                ephemeral=True
            )

    except Exception as e:

        print(
            f"[RESTART ERROR] "
            f"{type(e).__name__}: {e}"
        )

        try:
            await interaction.followup.send(
                "❌ حدث خطأ أثناء تنفيذ الأمر.",
                ephemeral=True
            )
        except Exception:
            pass


# =========================================================
# CHAT-MINECRAFT
# =========================================================

@bot.tree.command(
    name="chat-minecraft",
    description="تحديد الروم الذي يربط Discord مع Minecraft"
)
async def chat_minecraft_command(
    interaction: discord.Interaction
):

    global MINE_CHAT_CHANNEL_ID

    try:

        if not is_owner(interaction.user.id):
            await interaction.response.send_message(
                "❌ ليس لديك صلاحية استخدام هذا الأمر.",
                ephemeral=True
            )
            return

        MINE_CHAT_CHANNEL_ID = interaction.channel_id

        await interaction.response.send_message(
            "✅ تم ربط هذا الروم مع Minecraft Chat.",
            ephemeral=True
        )

        print(
            f"[Minecraft Chat] "
            f"Channel changed to {MINE_CHAT_CHANNEL_ID}"
        )

    except Exception as e:

        print(
            f"[CHAT COMMAND ERROR] "
            f"{type(e).__name__}: {e}"
        )

        try:
            if interaction.response.is_done():
                await interaction.followup.send(
                    "❌ حدث خطأ.",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    "❌ حدث خطأ.",
                    ephemeral=True
                )
        except Exception:
            pass


# =========================================================
# DISCORD -> MINECRAFT
# =========================================================

@bot.event
async def on_message(message: discord.Message):

    if message.author.bot:
        return

    try:

        if (
            MINE_CHAT_CHANNEL_ID
            and message.channel.id == MINE_CHAT_CHANNEL_ID
        ):

            content = message.content.strip()

            if content:

                pending_messages.append({
                    "author": message.author.display_name,
                    "message": content,
                    "time": now_text()
                })

                print(
                    f"[Discord -> Minecraft] "
                    f"{message.author.display_name}: {content}"
                )

    except Exception as e:

        print(
            f"[on_message ERROR] "
            f"{type(e).__name__}: {e}"
        )

    await bot.process_commands(message)


# =========================================================
# MINECRAFT -> DISCORD
# =========================================================

async def send_minecraft_message(
    player: str,
    message: str
):

    channel_id = MINE_CHAT_CHANNEL_ID

    if not channel_id:
        return False

    channel = bot.get_channel(channel_id)

    if channel is None:
        try:
            channel = await bot.fetch_channel(channel_id)
        except Exception as e:
            print(
                f"[Minecraft -> Discord] "
                f"Channel error: {e}"
            )
            return False

    embed = discord.Embed(
        color=discord.Color.green()
    )

    embed.add_field(
        name=f"🎮 {player}",
        value=message,
        inline=False
    )

    try:
        await channel.send(embed=embed)
        return True
    except Exception as e:
        print(
            f"[Minecraft -> Discord ERROR] {e}"
        )
        return False


# =========================================================
# WEB SERVER
# =========================================================

async def health(request):
    return web.json_response({
        "status": "online",
        "bot": str(bot.user) if bot.user else None
    })


async def minecraft_pending(request):

    messages = list(pending_messages)

    return web.json_response({
        "messages": messages
    })


async def minecraft_ack(request):

    try:

        data = await request.json()

        count = int(
            data.get("count", 1)
        )

        count = max(
            0,
            min(count, len(pending_messages))
        )

        for _ in range(count):
            if pending_messages:
                pending_messages.popleft()

        return web.json_response({
            "success": True,
            "removed": count
        })

    except Exception as e:

        return web.json_response(
            {
                "success": False,
                "error": str(e)
            },
            status=400
        )


async def minecraft_chat(request):

    try:

        data = await request.json()

        player = str(
            data.get("player", "Minecraft")
        )

        message = str(
            data.get("message", "")
        )

        if not message:
            return web.json_response(
                {
                    "success": False,
                    "error": "message is empty"
                },
                status=400
            )

        success = await send_minecraft_message(
            player,
            message
        )

        return web.json_response({
            "success": success
        })

    except Exception as e:

        print(
            f"[Minecraft Chat API ERROR] "
            f"{type(e).__name__}: {e}"
        )

        return web.json_response(
            {
                "success": False,
                "error": str(e)
            },
            status=500
        )


async def start_web_server():

    app = web.Application()

    app.router.add_get(
        "/",
        health
    )

    app.router.add_get(
        "/minecraft/pending",
        minecraft_pending
    )

    app.router.add_post(
        "/minecraft/ack",
        minecraft_ack
    )

    app.router.add_post(
        "/minecraft/chat",
        minecraft_chat
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

    print(
        f"Web server started on port {port}"
    )


# =========================================================
# READY
# =========================================================

@bot.event
async def on_ready():

    print(
        f"Logged in as {bot.user}"
    )

    try:

        guild = discord.Object(
            id=GUILD_ID
        )

        synced = await bot.tree.sync(
            guild=guild
        )

        print(
            f"Synced {len(synced)} commands."
        )

        # Persistent refresh button
        bot.add_view(
            ServerView()
        )

    except Exception as e:

        print(
            f"[SYNC ERROR] "
            f"{type(e).__name__}: {e}"
        )


# =========================================================
# GLOBAL ERROR HANDLER
# =========================================================

@bot.tree.error
async def on_app_command_error(
    interaction: discord.Interaction,
    error: app_commands.AppCommandError
):

    print(
        f"[COMMAND ERROR] "
        f"{type(error).__name__}: {error}"
    )

    try:

        message = (
            "❌ حدث خطأ أثناء تنفيذ الأمر.\n"
            f"`{type(error).__name__}`"
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
            f"[ERROR HANDLER ERROR] {e}"
        )


# =========================================================
# START
# =========================================================

async def main():

    if not TOKEN:
        raise RuntimeError(
            "DISCORD_TOKEN غير موجود في Railway Variables"
        )

    await start_web_server()

    await bot.start(TOKEN)


if __name__ == "__main__":

    try:
        asyncio.run(main())

    except KeyboardInterrupt:
        pass

    except Exception as e:
        print(
            f"[FATAL ERROR] "
            f"{type(e).__name__}: {e}"
        )
