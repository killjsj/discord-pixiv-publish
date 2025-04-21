import discord
from discord import app_commands
import requests
import os

# 配置
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()
my_bot_token = os.getenv("DISCORD_BOT_TOKEN")
class MyBot(discord.Client):
    def __init__(self):
        super().__init__(intents=discord.Intents.default())
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        # 同步斜杠命令
        await self.tree.sync()
        print("Commands synced!")

# 创建机器人实例
bot = MyBot()

@bot.tree.command(name="setu", description="Send a random pixiv photo")
@app_commands.describe(
    r18="Enable R18? (No: 0, Yes: 1, Random: 2)",
    num="Number of images to return (1-20)",
    tags0="Tags to filter images (e.g., '萝莉 少女|白丝 黑丝')",
    tags1="Tags to filter images (e.g., '萝莉 少女|白丝 黑丝')",
    tags2="Tags to filter images (e.g., '萝莉 少女|白丝 黑丝')",
    tags3="Tags to filter images (e.g., '萝莉 少女|白丝 黑丝')",
    tags4="Tags to filter images (e.g., '萝莉 少女|白丝 黑丝')"
)
@app_commands.choices(r18=[
    app_commands.Choice(name="No (Non-R18)", value="no"),
    app_commands.Choice(name="Yes (R18)", value="yes"),
    app_commands.Choice(name="Random (Mixed)", value="random")
])
async def setu(interaction: discord.Interaction, r18: str, num: int = 1, tags0: str = None,tags1: str = None,tags2: str = None
               ,tags3: str = None,tags4: str = None):
    await interaction.response.defer()  # 延迟响应

    # 调用 API 获取图片
    api_url = "https://api.lolicon.app/setu/v2"
    r18_param = {
        "no": 0,
        "yes": 1,
        "random": 2
    }.get(r18, 2)

    # 构建请求参数
    params = {
        "r18": r18_param,
        "num": max(1, min(num, 20)),  # 限制 num 在 1 到 20 之间
    }
    tags = [tag for tag in [tags0, tags1, tags2, tags3, tags4] if tag is not None]
    if tags:
        # 将用户输入的 tags 按 '|' 分组，每组按空格分割为二维数组
        params["tag"] = tags
    

    try:
        # 使用 POST 请求发送数据
        print(params)
        response = requests.post(api_url, json=params)
        response.raise_for_status()  # 检查 HTTP 错误
        image_data = response.json()
        print(image_data)
        if image_data and "data" in image_data and len(image_data["data"]) > 0:
            embeds = []
            for image in image_data["data"]:
                image_url = image["urls"]["original"]
                embed = discord.Embed(title="Pixiv Image")
                embed.set_image(url=image_url)
                embeds.append(embed)

            # 发送嵌入消息
            for embed in embeds:
                await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send("未能获取图片，请稍后重试。")
    except requests.exceptions.RequestException as e:
        await interaction.followup.send(f"HTTP 请求错误：{str(e)}")
    except Exception as e:
        await interaction.followup.send(f"发生错误：{str(e)}")
        
        
        
bot.run(my_bot_token)