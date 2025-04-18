import discord
from discord.ext import tasks
from discord import app_commands
import requests, os, json, threading, random
from flask import Flask
from dotenv import load_dotenv
from urllib.parse import urljoin
from datetime import datetime

# ✅ 載入 .env
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))
SELF_URL = os.getenv("SELF_URL")
REMOTE_DB = "https://raw.githubusercontent.com/Tseng-Gina/chiikawa-discord-bot-koyeb/main/products.json"

# ✅ Discord Bot 初始化
intents = discord.Intents.default()
intents.message_content = True
bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)

# ✅ 關鍵字對話語錄
keyword_responses = {
    "婆婆": ["我在呢", "怎麼了寶貝", "婆婆也想你"],
    "666": ["過來坐坐", "過來坐下"],
    "屁眼": ["炸屁眼"]
}

# ✅ 擷取遠端資料庫（GitHub）
def load_remote_db():
    try:
        res = requests.get(REMOTE_DB, timeout=10)
        res.raise_for_status()
        return res.json()
    except Exception as e:
        print(f"❌ 無法讀取 GitHub JSON：{e}")
        return []

# ✅ 擷取吉伊卡哇官網商品
def fetch_products():
    headers = {"User-Agent": "Mozilla/5.0"}
    page = 1
    products = []

    while True:
        try:
            url = f"https://chiikawamarket.jp/collections/all/products.json?page={page}"
            res = requests.get(url, headers=headers, timeout=10)
            res.raise_for_status()
            items = res.json().get("products", [])
            if not items:
                break

            for product in items:
                title = product.get("title", "無標題")
                handle = product.get("handle", "")
                link = f"https://chiikawamarket.jp/products/{handle}"
                price = product.get("variants", [{}])[0].get("price", "未知")
                image = ""
                if product.get("images") and product["images"][0].get("src"):
                    image = urljoin("https:", product["images"][0]["src"])
                products.append({"title": title, "link": link, "price": price, "image": image})
            page += 1
        except Exception as e:
            print(f"❌ 抓取第 {page} 頁失敗：{e}")
            break
    return products

# ✅ 比對商品
def compare_products(old, new):
    old_links = set(p["link"] for p in old)
    new_links = set(p["link"] for p in new)
    added = [p for p in new if p["link"] not in old_links]
    removed = [p for p in old if p["link"] not in new_links]
    return added, removed

# ✅ 結果推播
async def send_results(channel, added, removed):
    now = datetime.utcnow()
    tw_time = now.hour + 8
    await channel.send(f"🕒 我抓完了寶子們，現在是{tw_time % 24:02d}:{now.minute:02d}")

    if added:
        await channel.send(f"🆕 發現 {len(added)} 筆新商品：")
        for item in added:
            embed = discord.Embed(title=item["title"], url=item["link"], description=f"💰 {item['price']} 円", color=0x66ccff)
            if item["image"]:
                embed.set_image(url=item["image"])
            await channel.send(embed=embed)
    else:
        await channel.send("✅ 沒有新商品。")

    if removed:
        await channel.send("@everyone 寶子們有商品從官網下架了，請注意！")
        for item in removed:
            embed = discord.Embed(title=item["title"], url=item["link"], color=0xff6666)
            if item["image"]:
                embed.set_image(url=item["image"])
            await channel.send(embed=embed)
    else:
        await channel.send("✅ 沒有下架商品。")

# ✅ Slash 指令：/check_stock
@tree.command(name="check_stock", description="手動比對吉伊卡哇商品")
async def check_stock_slash(interaction: discord.Interaction):
    await interaction.response.send_message("🔍 正在比對吉伊卡哇商品...")
    old_data = load_remote_db()
    new_data = fetch_products()
    added, removed = compare_products(old_data, new_data)
    await send_results(interaction.channel, added, removed)

# ✅ Slash 指令：/helpme
@tree.command(name="helpme", description="查看機器人支援的功能")
async def helpme_slash(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Chiikawa 機器人幫助指令",
        description="以下是我可以做的事 🐻✨",
        color=0x99ccff
    )
    embed.add_field(name="🛍️ /check_stock", value="手動比對吉伊卡哇商品", inline=False)
    embed.add_field(name="⏰ 自動任務", value="每天 9:30、14:30 自動比對商品", inline=False)
    embed.add_field(name="💬 對話互動", value="說「婆婆」、「666」會有驚喜語錄💬", inline=False)
    embed.set_footer(text="Made with 🐹 by Tseng-Gina")
    await interaction.response.send_message(embed=embed)

# ✅ 關鍵詞語錄回應
@bot.event
async def on_message(message):
    if message.author.bot:
        return
    for keyword, responses in keyword_responses.items():
        if keyword in message.content:
            await message.channel.send(random.choice(responses))
            break
    await tree.process_commands(message)

# ✅ 自動任務：每日 9:30 / 14:30
@tasks.loop(minutes=1)
async def daily_check():
    await bot.wait_until_ready()
    now = datetime.utcnow()
    tw_hour = (now.hour + 8) % 24
    if (tw_hour == 9 and now.minute == 30) or (tw_hour == 14 and now.minute == 30):
        channel = bot.get_channel(CHANNEL_ID)
        if channel:
            old_data = load_remote_db()
            new_data = fetch_products()
            added, removed = compare_products(old_data, new_data)
            await send_results(channel, added, removed)

# ✅ Flask keep-alive
app = Flask(__name__)
@app.route('/')
def home():
    return "✅ Bot is alive"

def run_flask():
    app.run(host="0.0.0.0", port=8000)

def keep_alive():
    threading.Thread(target=run_flask).start()

# ✅ ping 自己保持活著
@tasks.loop(minutes=5)
async def ping_self():
    if SELF_URL:
        try:
            res = requests.get(SELF_URL, timeout=5)
            print(f"🌐 keep-alive ping 成功：{res.status_code}")
        except Exception as e:
            print(f"⚠️ ping 失敗：{e}")

# ✅ bot 啟動事件
@bot.event
async def on_ready():
    await tree.sync()
    print(f"✅ Bot 上線：{bot.user}")
    daily_check.start()
    ping_self.start()

# ✅ 啟動 Flask 與 Discord Bot
keep_alive()
bot.run(TOKEN)
