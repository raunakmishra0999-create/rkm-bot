import discord
from discord.ext import commands, tasks
import re
import sqlite3
import asyncio
from datetime import datetime
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

# ============ HEALTH CHECK SERVER (Render ke liye ZAROORI) ============
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running!")
    def log_message(self, format, *args):
        pass

def run_health_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    print(f"✅ Health server on port {port}")
    server.serve_forever()

thread = threading.Thread(target=run_health_server, daemon=True)
thread.start()

# ============ BOT SETUP ============
intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)

# ============ DATABASE SETUP ============
conn = sqlite3.connect('tournament.db', check_same_thread=False)
c = conn.cursor()

c.execute('''CREATE TABLE IF NOT EXISTS verified_tags
             (team_name TEXT, players TEXT, uids TEXT, discord_id TEXT PRIMARY KEY)''')
c.execute('''CREATE TABLE IF NOT EXISTS registrations
             (channel_id TEXT, team_name TEXT, discord_id TEXT, timestamp TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS matches
             (team_name TEXT, match_time TEXT, id_password TEXT, result TEXT, screenshot_url TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS idp_messages
             (idp_number TEXT, message TEXT, sent_to TEXT)''')
conn.commit()

# ============ CONFIGURATION - APNI IDs YAHAN DALO ============
TAG_CHECK_CHANNEL    = 1501156569713348609
REG_CATEGORY         = 1501157421610041395
MATCH_RESULT_CHANNEL = 1502270253785157712
LEADERBOARD_CHANNEL  = 1501157176482336848
T2_CATEGORY          = 1501167625466544198
IDP_SOURCE_CHANNEL   = 1502264927212015637

# ============ TAG CHECK + REGISTRATION SYSTEM ============
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # --- Tag Check Channel ---
    if message.channel.id == TAG_CHECK_CHANNEL:
        pattern = r"Team Name:\s*(.+)\nPlayers:\s*(.+)\nUID:\s*(.+)"
        match = re.match(pattern, message.content.strip())
        if match:
            team_name = match.group(1).strip()
            players   = match.group(2).strip()
            uids      = match.group(3).strip()
            c.execute("INSERT OR REPLACE INTO verified_tags VALUES (?, ?, ?, ?)",
                      (team_name, players, uids, str(message.author.id)))
            conn.commit()
            await message.add_reaction("✅")
            await message.channel.send(f"✅ **{team_name}** verified! Ab register kar sakte ho.")
        else:
            await message.add_reaction("❌")
            await message.channel.send(
                "❌ **Wrong format!** Aise likho:\n"
                "```\nTeam Name: YourTeam\nPlayers: @tag1 @tag2\nUID: 123456, 789012\n```"
            )

    # --- Registration Category Channels ---
    if message.channel.category_id == REG_CATEGORY:
        perms = message.channel.permissions_for(message.guild.default_role)
        if not perms.send_messages:
            await message.channel.send("🔒 Registration closed!", delete_after=3)
            await message.delete()
            return

        c.execute("SELECT team_name FROM verified_tags WHERE discord_id = ?", (str(message.author.id),))
        verified = c.fetchone()
        if not verified:
            await message.channel.send("❌ Pehle **#tag-check** mein apna tag verify karo!", delete_after=5)
            await message.delete()
            return

        team_name = verified[0]
        c.execute("SELECT * FROM registrations WHERE channel_id = ? AND discord_id = ?",
                  (str(message.channel.id), str(message.author.id)))
        if c.fetchone():
            await message.channel.send("❌ Tumne already register kar liya hai!", delete_after=3)
            await message.delete()
            return

        c.execute("INSERT INTO registrations VALUES (?, ?, ?, ?)",
                  (str(message.channel.id), team_name, str(message.author.id), str(datetime.now())))
        conn.commit()

        c.execute("SELECT COUNT(*) FROM registrations WHERE channel_id = ?", (str(message.channel.id),))
        count = c.fetchone()[0]
        await message.add_reaction("✅")
        await message.channel.send(f"✅ **{team_name}** registered! ({count}/25)")

        if count >= 25:
            await message.channel.set_permissions(message.guild.default_role, send_messages=False)
            await message.channel.send("🔒 **REGISTRATION LOCKED!** 25 teams ho gaye.")
            await create_idp_channel(message.channel)

    # --- IDP Source Channel ---
    if message.channel.id == IDP_SOURCE_CHANNEL:
        idp_match = re.match(r'idp(\d+)', message.content.strip().lower())
        if idp_match:
            idp_number = idp_match.group(1)
            for channel in message.guild.channels:
                if channel.name == f"idp{idp_number}":
                    await channel.send(message.content)
                    await message.add_reaction("✅")
                    break

    await bot.process_commands(message)


async def create_idp_channel(reg_channel):
    guild = reg_channel.guild
    c.execute("SELECT COUNT(*) FROM registrations WHERE channel_id = ?", (str(reg_channel.id),))
    reg_count = c.fetchone()[0]
    idp_number = reg_count // 25
    idp_channel_name = f"idp{idp_number}"

    idp_channel = discord.utils.get(guild.channels, name=idp_channel_name, category=reg_channel.category)
    if not idp_channel:
        idp_channel = await guild.create_text_channel(
            idp_channel_name,
            category=reg_channel.category,
            position=reg_channel.position + 1
        )
        await idp_channel.set_permissions(guild.default_role, send_messages=False, read_messages=False)

    c.execute("SELECT discord_id FROM registrations WHERE channel_id = ?", (str(reg_channel.id),))
    users = c.fetchall()
    for (user_id,) in users:
        member = guild.get_member(int(user_id))
        if member:
            await idp_channel.set_permissions(member, read_messages=True, send_messages=False)

    await reg_channel.send(f"✅ IDP channel ready: {idp_channel.mention}")


# ============ MATCH RESULT SYSTEM ============
@bot.command(name='result')
async def add_result(ctx, *, result: str = None):
    if ctx.channel.id != MATCH_RESULT_CHANNEL:
        return
    if not result:
        await ctx.send("Usage: `!result TeamName: Win/Loss`")
        return
    team = result.split(':')[0].strip()
    c.execute("INSERT INTO matches VALUES (?, ?, ?, ?, ?)",
              (team, str(datetime.now()), "N/A", result, "manual"))
    conn.commit()
    await ctx.send(f"✅ Result saved: **{result}**")


# ============ LEADERBOARD ============
@tasks.loop(minutes=1)
async def check_leaderboard_time():
    now = datetime.now()
    if now.weekday() == 6 and now.hour == 19 and now.minute == 0:
        await send_leaderboard()

async def send_leaderboard():
    channel = bot.get_channel(LEADERBOARD_CHANNEL)
    if not channel:
        return
    c.execute('''
        SELECT team_name, COUNT(*) as matches,
               SUM(CASE WHEN result LIKE '%Win%' THEN 1 ELSE 0 END) as wins
        FROM matches GROUP BY team_name ORDER BY wins DESC, matches DESC LIMIT 10
    ''')
    results = c.fetchall()
    if not results:
        await channel.send("📊 Is hafte koi match result nahi mila!")
        return

    embed = discord.Embed(title="🏆 WEEKLY LEADERBOARD", color=discord.Color.gold())
    text = "```\nRank | Team Name        | Matches | Wins\n" + "-"*42 + "\n"
    for i, (team, matches, wins) in enumerate(results, 1):
        text += f"#{i:<3} | {team[:16]:<16} | {matches:<7} | {wins}\n"
    text += "```"
    embed.description = text
    embed.set_footer(text=f"Updated: {datetime.now().strftime('%d/%m/%Y %I:%M %p')}")
    await channel.send(embed=embed)
    await assign_t2_roles(results)

async def assign_t2_roles(teams):
    for team_name, _, _ in teams:
        c.execute("SELECT discord_id FROM verified_tags WHERE team_name = ?", (team_name,))
        players = c.fetchall()
        for guild in bot.guilds:
            role = discord.utils.get(guild.roles, name="T2 Qualifier")
            if not role:
                try:
                    role = await guild.create_role(name="T2 Qualifier")
                except:
                    continue
            category = guild.get_channel(T2_CATEGORY)
            if category:
                await category.set_permissions(role, read_messages=True, send_messages=False)
            for (player_id,) in players:
                member = guild.get_member(int(player_id))
                if member and role not in member.roles:
                    await member.add_roles(role)


# ============ ADMIN COMMANDS ============
@bot.command()
@commands.has_permissions(administrator=True)
async def sendidp(ctx, idp_number: int, *, message_text: str):
    """!sendidp 1 ID:123 Pass:456"""
    for channel in ctx.guild.channels:
        if channel.name == f"idp{idp_number}":
            await channel.send(f"🔐 **ID & Password for Match**\n{message_text}")
            await ctx.send(f"✅ Bhej diya: {channel.mention}")
            return
    await ctx.send(f"❌ 'idp{idp_number}' channel nahi mila")

@bot.command()
@commands.has_permissions(administrator=True)
async def lockch(ctx, channel: discord.TextChannel = None):
    channel = channel or ctx.channel
    await channel.set_permissions(ctx.guild.default_role, send_messages=False)
    await ctx.send(f"🔒 Locked: {channel.mention}")

@bot.command()
@commands.has_permissions(administrator=True)
async def unlockch(ctx, channel: discord.TextChannel = None):
    channel = channel or ctx.channel
    await channel.set_permissions(ctx.guild.default_role, send_messages=True)
    await ctx.send(f"🔓 Unlocked: {channel.mention}")

@bot.command()
@commands.has_permissions(administrator=True)
async def clearresults(ctx):
    c.execute("DELETE FROM matches")
    conn.commit()
    await ctx.send("🗑️ Saare results delete ho gaye!")

@bot.command()
@commands.has_permissions(administrator=True)
async def clearregs(ctx, channel: discord.TextChannel = None):
    channel = channel or ctx.channel
    c.execute("DELETE FROM registrations WHERE channel_id = ?", (str(channel.id),))
    conn.commit()
    await ctx.send(f"🗑️ {channel.mention} ki registrations clear!")

@bot.command()
@commands.has_permissions(administrator=True)
async def showregs(ctx, channel: discord.TextChannel = None):
    channel = channel or ctx.channel
    c.execute("SELECT team_name FROM registrations WHERE channel_id = ?", (str(channel.id),))
    teams = c.fetchall()
    if not teams:
        await ctx.send("📋 Koi registration nahi.")
        return
    text = "\n".join([f"{i+1}. {t[0]}" for i, t in enumerate(teams)])
    embed = discord.Embed(
        title=f"📋 Registrations - #{channel.name}",
        description=f"```\n{text}\n```",
        color=discord.Color.blue()
    )
    embed.set_footer(text=f"Total: {len(teams)}/25")
    await ctx.send(embed=embed)

@bot.command()
@commands.has_permissions(administrator=True)
async def leaderboard(ctx):
    await send_leaderboard()
    await ctx.send("✅ Leaderboard post kar diya!")


# ============ UTILITY COMMANDS ============
@bot.command()
async def ping(ctx):
    await ctx.send(f'🏓 Pong! `{round(bot.latency * 1000)}ms`')

@bot.command()
async def stats(ctx):
    tags  = c.execute("SELECT COUNT(*) FROM verified_tags").fetchone()[0]
    regs  = c.execute("SELECT COUNT(*) FROM registrations").fetchone()[0]
    mat   = c.execute("SELECT COUNT(*) FROM matches").fetchone()[0]
    embed = discord.Embed(title="📊 Bot Stats", color=discord.Color.green())
    embed.add_field(name="✅ Verified Tags", value=str(tags), inline=True)
    embed.add_field(name="📝 Registrations", value=str(regs), inline=True)
    embed.add_field(name="⚔️ Matches",       value=str(mat),  inline=True)
    await ctx.send(embed=embed)

@bot.command(name='helpme')
async def helpme(ctx):
    embed = discord.Embed(title="📖 Bot Commands", color=discord.Color.blurple())
    embed.add_field(name="👤 Player", value=(
        "`!ping` - Latency\n`!stats` - Statistics\n`!helpme` - Commands list"
    ), inline=False)
    embed.add_field(name="🛡️ Admin Only", value=(
        "`!sendidp [n] [msg]` - IDP bhejo\n"
        "`!lockch` - Channel lock\n`!unlockch` - Unlock\n"
        "`!showregs` - Registrations dekho\n`!clearregs` - Clear karo\n"
        "`!clearresults` - Results clear\n`!leaderboard` - Post karo\n"
        "`!result [team:win/loss]` - Result submit"
    ), inline=False)
    embed.add_field(name="📋 Tag Format (#tag-check mein)", value=(
        "```\nTeam Name: YourTeam\nPlayers: @p1 @p2\nUID: 111, 222\n```"
    ), inline=False)
    await ctx.send(embed=embed)


# ============ TIME-BASED AUTO OPEN ============
@tasks.loop(minutes=1)
async def check_time_based_channels():
    now = datetime.now()
    current_time = now.strftime("%I%p").lower().lstrip('0')
    for guild in bot.guilds:
        for channel in guild.channels:
            if channel.category_id == REG_CATEGORY:
                time_match = re.search(r'(\d+)(am|pm)', channel.name.lower())
                if time_match:
                    channel_time = f"{time_match.group(1)}{time_match.group(2)}"
                    if channel_time == current_time:
                        perms = channel.permissions_for(guild.default_role)
                        if not perms.send_messages:
                            await channel.set_permissions(guild.default_role, send_messages=True)
                            await channel.send("🔓 **Registration OPEN!** Apna verified tag bhejo.")


# ============ ERROR HANDLING ============
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ Tumhare paas yeh command use karne ki permission nahi!")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("❌ Kuch argument missing hai! `!helpme` dekho.")
    elif isinstance(error, commands.CommandNotFound):
        pass
    else:
        print(f"Error: {error}")


# ============ ON READY ============
@bot.event
async def on_ready():
    print(f'✅ Bot Online: {bot.user}')
    print(f'✅ Guilds: {len(bot.guilds)}')
    check_time_based_channels.start()
    check_leaderboard_time.start()
    await bot.change_presence(
        activity=discord.Activity(type=discord.ActivityType.watching, name="🏆 Tournaments")
    )


# ============ RUN ============
TOKEN = os.environ.get("DISCORD_TOKEN")
if not TOKEN:
    print("❌ ERROR: DISCORD_TOKEN set nahi hai!")
    exit(1)

bot.run(TOKEN)
