import discord
from discord.ext import commands, tasks
from flask import Flask
import requests, os, json, threading
from urllib.parse import urljoin
from dotenv import load_dotenv
from datetime import datetime

# 🟢 載入 .env
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))
SELF_URL = os.getenv("SELF_URL")
REMOTE_DB = "https://raw.githubusercontent.com/Tseng-Gina/chiikawa-discord-bot-koyeb/refs/heads/main/products.json?token=GHSAT0AAAAAADCMJPINGXB3UA2TGSNWXPQ22ABC6PQ"

# 🧠 Discord Bot 初始化
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ✅ 只從 GitHub 抓 JSON 資料
def load_remote_db():
    try:
        res = requests.get(REMOTE_DB, timeout=10)
        res.raise_for_status()
        return res.json()
    except Exception as e:
        print(f"❌ 無法讀取 GitHub JSON：{e}")
        return []

# ✅ 抓最新官網商品
def fetch_products():
    headers = {"User-Agent": "Mozilla/5.0"}
    page = 1
    products = []

    while True:
        try:
            url = f"https://chiikawamarket.jp/collections/all/products.json?page={page}"
            res = requests.get(url, headers=headers, timeout=5)
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

# 📤 推送結果
async def send_results(channel, added, removed):
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
        await channel.send(f"❌ 有 {len(removed)} 筆商品從官網下架：")
        for item in removed:
            embed = discord.Embed(title=item["title"], url=item["link"], color=0xff6666)
            if item["image"]:
                embed.set_image(url=item["image"])
            await channel.send(embed=embed)
    else:
        await channel.send("✅ 沒有下架商品。")

# 🧾 !check_stock 指令
@bot.command()
async def check_stock(ctx):
    await ctx.send("🔍 正在比對吉伊卡哇商品...")
    old_data = load_remote_db()
    new_data = fetch_products()
    added, removed = compare_products(old_data, new_data)
    await send_results(ctx.channel, added, removed)

# 🕘 每天早上 9 點自動執行
@tasks.loop(minutes=1)
async def daily_check():
    await bot.wait_until_ready()
    now = datetime.utcnow()
    tw_hour = (now.hour + 8) % 24
    if tw_hour == 9 and now.minute == 0:
        print("⏰ 自動比對觸發")
        channel = bot.get_channel(CHANNEL_ID)
        if channel:
            old_data = load_remote_db()
            new_data = fetch_products()
            added, removed = compare_products(old_data, new_data)
            await send_results(channel, added, removed)

# 🌐 Flask keep-alive
app = Flask(__name__)
@app.route('/')
def home():
    return "✅ Bot is alive"

def run_flask():
    app.run(host="0.0.0.0", port=8000)

def keep_alive():
    threading.Thread(target=run_flask).start()

# 🔁 ping 自己避免 Koyeb idle
@tasks.loop(minutes=5)
async def ping_self():
    if SELF_URL:
        try:
            res = requests.get(SELF_URL, timeout=5)
            print(f"🌐 keep-alive ping 成功：{res.status_code}")
        except Exception as e:
            print(f"⚠️ ping 失敗：{e}")

# 🎯 Bot 啟動
@bot.event
async def on_ready():
    print(f"✅ Bot 上線：{bot.user}")
    daily_check.start()
    ping_self.start()

# 🟢 開始 Flask + Discord bot
keep_alive()
bot.run(TOKEN)
