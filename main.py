# ✅ Chiikawa & Nagano Discord Bot 完整版
import discord
from discord.ext import tasks
from discord import app_commands
import requests, os, json, threading, random
from flask import Flask
from dotenv import load_dotenv
from urllib.parse import urljoin
from datetime import datetime

# ✅ 載入環境變數
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))
SELF_URL = os.getenv("SELF_URL")
CHIIKAWA_DB = "https://raw.githubusercontent.com/Tseng-Gina/chiikawa-discord-bot-koyeb/main/chiikawa.json"
NAGONO_DB = "https://raw.githubusercontent.com/Tseng-Gina/chiikawa-discord-bot-koyeb/main/nagono.json"

# ✅ 初始化 Bot
intents = discord.Intents.default()
intents.message_content = True
bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)

# ✅ 關鍵字回應設定
keyword_responses = {
    "婆婆": ["我在呢🩷", "怎麼了寶貝💖", "婆婆也想你💞", "吃我唧唧"],
    "幹": ["唉呦這麼兇兇喔人家會怕怕", "不要森氣嘛", "要幫你吹吹?"],
    "操": ["唉呦這麼兇兇喔人家會怕怕", "不要森氣嘛", "要幫你吹吹?"],
    "你媽": ["唉呦這麼兇兇喔人家會怕怕", "不要森氣嘛", "要幫你吹吹?"],
    "芸柵": ["<@1224380279611719704>愛<@855009651010437171>💗forever💗"],
    "錢包": ["<@855009651010437171>愛<@1224380279611719704>💗forever💗"],
    "去死": ["不要啦~我怕你會想我"],
    "離婚": ["<@855009651010437171>"],
    "閉嘴": ["你他媽才閉嘴"],
    "666": ["過來坐坐🪑", "過來坐下🪑"],
    "雞巴": ["操你媽曾靜儒"],
    "正男": ["https://tenor.com/view/clash-of-clans-gif-23752619", "https://tenor.com/view/shomp-scary-goblin-running-gif-13908288"],
    "正豪": ["https://tenor.com/view/clash-of-clans-gif-23752619", "https://tenor.com/view/shomp-scary-goblin-running-gif-13908288"],
    "屌": ["https://tenor.com/view/mikhail-perez-mikhail-dick-penis-hotdog-gif-19442083", "https://tenor.com/view/mikhail-perez-mikhail-dick-penis-hotdog-gif-19442083", "https://tenor.com/view/dick-penis-dildo-forest-running-gif-16272085"],
    "皮炎": ["https://cdn.discordapp.com/attachments/1355201012914327594/1362651119641165975/image0.gif", "https://tenor.com/view/howlpro-howlprotocol-howl-howlup-crypto-gif-25551815", "https://tenor.com/view/taco-bell-gif-20228662"],
    "屁眼": ["https://cdn.discordapp.com/attachments/1355201012914327594/1362651119641165975/image0.gif", "https://tenor.com/view/howlpro-howlprotocol-howl-howlup-crypto-gif-25551815", "https://tenor.com/view/taco-bell-gif-20228662"]
}

# ✅ 擷取遠端 JSON
def load_remote_db(url):
    try:
        res = requests.get(url, timeout=10)
        res.raise_for_status()
        return res.json()
    except Exception as e:
        print(f"❌ 無法讀取 JSON：{e}")
        return []

# ✅ 擷取商品
# ✅ 補貨比對邏輯
def compare_products_with_restock(old, new):
    old_dict = {p["link"]: p for p in old}
    new_dict = {p["link"]: p for p in new}

    added = [p for link, p in new_dict.items() if link not in old_dict]
    removed = [p for link, p in old_dict.items() if link not in new_dict]

    restocked = []
    for link, new_item in new_dict.items():
        old_item = old_dict.get(link)
        if old_item and not old_item.get("in_stock") and new_item.get("in_stock"):
            restocked.append(new_item)

    return added, removed, restocked

# ✅ 修改 fetch_products() 加入 in_stock
def fetch_products(base_url):
    headers = {"User-Agent": "Mozilla/5.0"}
    page = 1
    products = []
    while True:
        try:
            url = f"{base_url}?page={page}"
            res = requests.get(url, headers=headers, timeout=10)
            res.raise_for_status()
            items = res.json().get("products", [])
            if not items:
                break
            for product in items:
                title = product.get("title", "無標題")
                handle = product.get("handle", "")
                link = base_url.replace("/collections/all/products.json", f"/products/{handle}")
                variant = product.get("variants", [{}])[0]
                price = variant.get("price", "未知")
                inventory = variant.get("inventory_quantity", 0)
                in_stock = inventory > 0
                image = ""
                if product.get("images") and product["images"][0].get("src"):
                    image = urljoin("https:", product["images"][0]["src"])
                products.append({
                    "title": title,
                    "link": link,
                    "price": price,
                    "image": image,
                    "inventory": inventory,
                    "in_stock": in_stock
                })
            page += 1
        except Exception as e:
            print(f"❌ 抓取第 {page} 頁失敗：{e}")
            break
    return products

# ✅ send_results() 支援補貨通知
async def send_results(channel, added, removed, restocked, tag=""):
    now = datetime.utcnow()
    time_str = f"{(now.hour + 8)%24:02}:{now.minute:02}"
    await channel.send(f"寶子們我抓完了{tag}，現在是🕒[{time_str}] ")

    if added:
        await channel.send(f"🆕 ⚠️寶子們❗看看我發現了 {tag} {len(added)} 筆新商品：")
        for item in added:
            embed = discord.Embed(title=item["title"], url=item["link"],
                                  description=f"💰 {item['price']} 円",
                                  color=0x66ccff)
            if item["image"]:
                embed.set_image(url=item["image"])
            await channel.send(embed=embed)
    else:
        await channel.send(f"✅ {tag} 沒有新商品。")

    if removed:
        await channel.send(f"⚠️寶子們⚠️ {tag} 有 {len(removed)} 筆商品下架了：")
        for item in removed:
            embed = discord.Embed(title=item["title"], url=item["link"],
                                  color=0xff6666)
            if item["image"]:
                embed.set_image(url=item["image"])
            await channel.send(embed=embed)
    else:
        await channel.send(f"✅ {tag} 沒有下架商品。")

    if restocked:
        await channel.send(f"@everyone 🔔 {tag} 有 {len(restocked)} 筆商品補貨囉～")
        for item in restocked:
            embed = discord.Embed(title=item["title"], url=item["link"],
                                  description=f"✅ 補貨成功！💰{item['price']} 円 | 庫存：{item['inventory']}",
                                  color=0x66ff66)
            if item["image"]:
                embed.set_image(url=item["image"])
            await channel.send(embed=embed)
    else:
        await channel.send(f"✅ {tag} 沒有補貨商品。")


# ✅ Slash 指令：/check_stock
@tree.command(name="check_stock", description="比對吉伊卡哇商品")
async def check_chiikawa(interaction: discord.Interaction):
    await interaction.response.send_message("🔍 正在比對吉伊卡哇商品...")
    old = load_remote_db(CHIIKAWA_DB)
    new = fetch_products("https://chiikawamarket.jp/collections/all/products.json")
    added, removed = compare_products_with_restock(old, new)
    await send_results(interaction.channel, added, removed, tag="吉伊卡哇")

# ✅ Slash 指令：/check_nagono
@tree.command(name="check_nagono", description="比對自嘲熊商品")
async def check_nagono(interaction: discord.Interaction):
    await interaction.response.send_message("🔍 正在比對自嘲熊商品...")
    old = load_remote_db(NAGONO_DB)
    new = fetch_products("https://nagano-market.jp/collections/all/products.json")
    added, removed = compare_products_with_restock(old, new)
    await send_results(interaction.channel, added, removed, tag="自嘲熊")

# ✅ Slash 指令：/helpme
@tree.command(name="helpme", description="顯示可用功能")
async def helpme(interaction: discord.Interaction):
    embed = discord.Embed(title="Chiikawa Bot 幫助指令", description="🐻 支援吉伊卡哇 & 自嘲熊商品追蹤", color=0x99ccff)
    embed.add_field(name="/check_stock", value="手動查吉伊卡哇", inline=False)
    embed.add_field(name="/check_nagono", value="手動查自嘲熊", inline=False)
    embed.add_field(name="⏰ 自動任務", value="每天 9:30 / 14:30 自動比對", inline=False)
    embed.add_field(name="💬 對話互動", value="無聊可以跟我打打招呼呦", inline=False)
    await interaction.response.send_message(embed=embed)

# ✅ 自動任務
@tasks.loop(minutes=1)
async def daily_check():
    await bot.wait_until_ready()
    now = datetime.utcnow()
    h, m = (now.hour + 8) % 24, now.minute
    if (h, m) in [(9, 30), (11, 30), (13, 30), (15, 30), (17, 30)]:
        channel = bot.get_channel(CHANNEL_ID)
        if channel:
            chi_old = load_remote_db(CHIIKAWA_DB)
            chi_new = fetch_products("https://chiikawamarket.jp/collections/all/products.json")
            chi_added, chi_removed = compare_products_with_restock(chi_old, chi_new)
            await send_results(channel, chi_added, chi_removed, tag="吉伊卡哇")

            naga_old = load_remote_db(NAGONO_DB)
            naga_new = fetch_products("https://nagano-market.jp/collections/all/products.json")
            naga_added, naga_removed = compare_products_with_restock(naga_old, naga_new)
            await send_results(channel, naga_added, naga_removed, tag="自嘲熊")

# ✅ 對話關鍵字
@bot.event
async def on_message(msg):
    if msg.author.bot: return
    for key, res in keyword_responses.items():
        if key in msg.content:
            await msg.channel.send(random.choice(res))
            break
    await tree.process_commands(msg)

# ✅ keep-alive
app = Flask(__name__)
@app.route('/')
def home():
    return "✅ Bot is alive"
def run_flask(): app.run(host="0.0.0.0", port=8000)
def keep_alive(): threading.Thread(target=run_flask).start()

@tasks.loop(minutes=5)
async def ping_self():
    if SELF_URL:
        try:
            requests.get(SELF_URL, timeout=5)
            print("🌐 ping 成功")
        except: print("⚠️ ping 失敗")

# ✅ 上線
@bot.event
async def on_ready():
    await tree.sync()
    print(f"✅ 上線囉：{bot.user}")
    daily_check.start()
    ping_self.start()

keep_alive()
bot.run(TOKEN)
