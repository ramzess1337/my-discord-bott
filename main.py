import discord
from discord.ext import commands
import json, asyncio, random
from datetime import datetime, timedelta
from flask import Flask
from threading import Thread

# ==== Flask Keep Alive ====
app = Flask('')

@app.route('/')
def home():
    return "Бот работает!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# ==== Настройки ====
TOKEN = "MTM4ODI0OTkzNzY2NTU4OTQ0OA.G1VmBV.RsKeEDOGc1RNC7WXosgifbX6bq216qBtg1OEaM"
SHOP_CHANNEL_ID = 1388256880274702336
BALANCE_CHANNEL_ID = 1388256944833167522
CASINO_CHANNEL_ID = 1388265779333431406

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)
user_data = {}
voice_times = {}
cooldowns = {}
events = {"active": False}

# ==== Загрузка и сохранение данных ====
def load_data():
    global user_data
    try:
        with open("data.json", "r") as f:
            user_data = json.load(f)
    except:
        user_data = {}

def save_data():
    with open("data.json", "w") as f:
        json.dump(user_data, f, indent=4)

def ensure_user(uid):
    if uid not in user_data:
        user_data[uid] = {
            "coins": 0,
            "messages": 0,
            "voice_minutes": 0,
            "purchases": 0,
            "achievements": []
        }

# ==== События ====
@bot.event
async def on_ready():
    load_data()
    print(f"✅ Бот {bot.user.name} успешно запущен и подключён к Discord!")

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    uid = str(message.author.id)
    ensure_user(uid)
    user_data[uid]["messages"] += 1
    gain = 2 if events["active"] else 1
    user_data[uid]["coins"] += gain
    save_data()
    await bot.process_commands(message)

@bot.event
async def on_voice_state_update(member, before, after):
    uid = str(member.id)
    ensure_user(uid)
    if after.channel and not before.channel:
        voice_times[uid] = datetime.utcnow()
    elif before.channel and not after.channel and uid in voice_times:
        minutes = int((datetime.utcnow() - voice_times[uid]).total_seconds() / 60)
        gained = minutes * 3 * (2 if events["active"] else 1)
        user_data[uid]["coins"] += gained
        user_data[uid]["voice_minutes"] += minutes
        del voice_times[uid]
        save_data()

# ==== Команды ====
@bot.command()
async def wallet(ctx):
    if ctx.channel.id != BALANCE_CHANNEL_ID:
        return
    uid = str(ctx.author.id)
    ensure_user(uid)
    await ctx.send(f"💰 У тебя {user_data[uid]['coins']} 🧩")

@bot.command()
async def daily(ctx):
    uid = str(ctx.author.id)
    now = datetime.utcnow()
    if uid in cooldowns and now - cooldowns[uid] < timedelta(hours=24):
        remaining = timedelta(hours=24) - (now - cooldowns[uid])
        minutes = int(remaining.total_seconds() // 60)
        return await ctx.send(f"⏳ Возвращайся через {minutes} минут.")
    ensure_user(uid)
    user_data[uid]["coins"] += 200
    cooldowns[uid] = now
    save_data()
    await ctx.send("🎁 Ты получил 200 🧩 за ежедневный бонус!")

@bot.command()
async def top(ctx):
    top_users = sorted(user_data.items(), key=lambda x: x[1]["coins"], reverse=True)[:10]
    medals = ["🥇", "🥈", "🥉"] + ["🏅"] * 7
    lines = []
    for i, (uid, data) in enumerate(top_users):
        member = ctx.guild.get_member(int(uid))
        name = member.display_name if member else f"User {uid}"
        lines.append(f"{medals[i]} {name} — {data['coins']} 🧩")
    await ctx.send("\n".join(lines))

@bot.command()
async def eventstorm(ctx):
    if not ctx.author.guild_permissions.administrator:
        return
    events["active"] = True
    await ctx.send("📢 Ивент запущен! x2 пазлов за 30 минут!")
    await asyncio.sleep(1800)
    events["active"] = False
    await ctx.send("⛈️ Ивент завершён!")

@bot.command()
async def casino(ctx, amount: int):
    if ctx.channel.id != CASINO_CHANNEL_ID:
        return
    uid = str(ctx.author.id)
    ensure_user(uid)
    if user_data[uid]["coins"] < amount:
        return await ctx.send("❌ Недостаточно пазлов.")
    win = random.choices([True, False], weights=[40, 60])[0]
    if win:
        user_data[uid]["coins"] += amount
        msg = await ctx.send(f"🎉 Ты выиграл {amount} 🧩! Теперь у тебя {user_data[uid]['coins']} 🧩")
    else:
        user_data[uid]["coins"] -= amount
        msg = await ctx.send(f"💀 Ты проиграл {amount} 🧩... Теперь у тебя {user_data[uid]['coins']} 🧩")
    await asyncio.sleep(30)
    await msg.delete()
    save_data()

@bot.command()
async def fruit(ctx, amount: int):
    if ctx.channel.id != CASINO_CHANNEL_ID:
        return
    uid = str(ctx.author.id)
    ensure_user(uid)
    if user_data[uid]["coins"] < amount:
        return await ctx.send("❌ Недостаточно пазлов.")
    emojis = ["🍒", "🍋", "🍉", "🍇", "🍓", "7️⃣"]
    line = [random.choice(emojis) for _ in range(3)]
    result = f"🎰 {line[0]} | {line[1]} | {line[2]}"
    if line[0] == line[1] == line[2]:
        if random.randint(1, 100) <= 10:
            reward = amount * 15
            user_data[uid]["coins"] += reward
            msg = await ctx.send(f"{result} — 🎉 Джекпот! Ты выиграл {reward} 🧩")
        else:
            user_data[uid]["coins"] -= amount
            msg = await ctx.send(f"{result} — Не повезло! (шанс был 10%)")
    else:
        user_data[uid]["coins"] -= amount
        msg = await ctx.send(f"{result} — Попробуй снова!")
    await asyncio.sleep(30)
    await msg.delete()
    save_data()

@bot.command()
@commands.has_permissions(administrator=True)
async def deletecoin(ctx, amount: int):
    uid = str(ctx.author.id)
    ensure_user(uid)
    user_data[uid]["coins"] = max(0, user_data[uid]["coins"] - amount)
    save_data()
    await ctx.send(f"🗑️ У тебя удалено {amount} 🧩. Осталось: {user_data[uid]['coins']} 🧩")

# ==== Запуск ====
keep_alive()
load_data()
bot.run(TOKEN)
