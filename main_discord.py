import asyncio
import json
import time
from typing import Any, Dict, List, Literal, Optional, Set, TypeAlias
from PIL import Image
import uuid
import aiofiles
import aiohttp
import discord
from discord import Button, ButtonStyle, Interaction, Member, NSFWLevel, SoundboardSound, app_commands
from discord.ui import Button, View
import requests
import os
import random
import openai
# Discord 文件大小限制（8MB）
MAX_DISCORD_FILE_SIZE = 8 * 1024 * 1024  # 8MB

# 配置
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()
my_bot_token = os.getenv("DISCORD_BOT_TOKEN")

my_bot_token = os.getenv("DISCORD_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_API_BASE = os.getenv("OPENAI_API_BASE")  # 添加自定义API基础URL
ai = openai.OpenAI(api_key=OPENAI_API_KEY,base_url=OPENAI_API_BASE)  # 使用自定义API基础URL
from pixivpy3 import AppPixivAPI
import pixiv_auth

def get_refresh_token() -> str:
    with open("token.txt", "r+") as f:
        if refresh_token := f.read().strip():
            return refresh_token
        refresh_token = pixiv_auth.login()["refresh_token"]
        f.write(refresh_token)
        return refresh_token

pixiv_refresh_token = get_refresh_token()
class ModQuestionButton(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="开始提问", style=discord.ButtonStyle.primary,custom_id="mod_question_button")
    async def mod_question(self, interaction: discord.Interaction, button: discord.ui.Button):
        # 创建用户专属频道
        channel_name = f"mod-qa-{interaction.user.name}"
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            interaction.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        
        question_channel = await interaction.guild.create_text_channel(
            channel_name,
            overwrites=overwrites
        )
        
        self.bot.mod_channels[question_channel.id] = {
            "user_id": interaction.user.id,
            "context": [{"role": "system", "content": """你是0协的一个机器人，专门帮助用户解决0协mod安装问题。 注意:你不能使用MARKDOWN!  正常安装流程:下载并打开0协工具箱(安装链接:国内:https://download.zeroasso.top/files/LLC_MOD_Toolbox_Installer.exe 海外:https://github.com/LocalizeLimbusCompany/LLC_MOD_Toolbox/releases 官方wiki:https://www.zeroasso.top/docs/install/autoinstall 需要使用.NET 8.0 Runtime 下载:https://dotnet.microsoft.com/zh-cn/download/dotnet/thank-you/runtime-desktop-8.0.8-windows-x64-installer ) 双击运行LLC_MOD_Toolbox.exe，点击开始安装，并等待安装完成后运行游戏即可。 安装视频:https://www.bilibili.com/video/BV1XfZXYxEa8 (推荐) 以下为部分wiki内容,根据这些指导用户解决问题:\"更改游戏基础语言:
注意,如果您的游戏基础语言为日文，则可能会出现中文文本字体不一致的问题，影响您的阅读体验。
请进入游戏，在游戏设置内将游戏基础语言设定为英文，以获得最佳体验。常见问题
写在前面：
插件安装器(也称工具箱)仅是我们为了方便用户们下载并更新插件而制作的工具。安装器的工作涉及互联网服务器的开发及运行维护、API的使用以及在线下载、本地安装的服务，因此可能会受到包括但不限于网络环境与系统环境在内的多方面影响。
这意味着，安装器的可用性，可能在不同用户之间存在差别。

因此，安装器仅仅是安装插件的工具之一，并非唯一安装途径。
如果您无法使用安装器，则可尝试手动进行插件安装。翻译插件的手动安装与日常更新实际上也非常简单。

对于各位遇到的不同问题，我们也感到非常抱歉与遗憾。但由于我们所受到的开发能力，以及经济能力等限制，我们往往很难将任何问题都完美解决。我们将会持续努力，尽量让更多用户体验到方便、快捷的安装服务，与准确、优质的文本翻译。

感谢各位一贯的理解与支持。

TL;DR：笼统的解决方案
插件安装器(即工具箱)出现问题
无法使用安装器安装插件时：
暂时关闭任何杀毒软件或防火墙等，或解除其对插件文件的影响与限制,
对安装器执行一次干净的重装,
确保您完整的删除干净全部旧版本遗留文件,
从我们提供的渠道下载最新版本安装器并重试,
进入设置页面调整插件设置,点击切换插件开关状态按钮，确保插件为开启,切换下载节点与API节点，参考这里(https://www.zeroasso.top/docs/configuration/nodes ),考虑使用其他安装方式,考虑进行手动安装,考虑使用文件覆盖，参考这里(https://www.zeroasso.top/docs/FAQ#override-using-working-files )
安装器启动即闪退时：
手动对LimbusCompany路径进行设置,参考这里(https://www.zeroasso.top/docs/FAQ#set-folder-path )
考虑使用其他安装方式,考虑进行手动安装,考虑使用文件覆盖，参考这里(https://www.zeroasso.top/docs/FAQ#override-using-working-files ),翻译插件出现问题,
插件启动但出现问题时：
可能是月亮计划提供的接口出现问题。请关注零协会BiliBili账号动态并等待。您的问题可能是普遍的问题，且往往很可能已经被其他人反馈过。此种情况下，还请您耐心等到我们的通告与更新.
对翻译插件执行一次干净的重装
确保您完整的删除干净全部旧版本遗留文件,
推荐使用安装器设置页面内的卸载插件按钮，这将确保一个干净完整的卸载,
若不使用安装器，确保所有插件相关的文件已经被卸载。如果您不确定是否有残留文件，则删除所有可疑的文件，并使用Steam验证游戏完整性。
从我们提供的渠道下载最新版本翻译插件并重试,
推荐使用安装器下载插件,
若您无法使用安装器安装插件，则可尝试进行手动安装.
汉化常见问题:
游戏内中文字体参差不齐，简繁混杂
如果您的游戏基础语言为日文，则可能会出现中文文本字体不一致的问题，影响您的阅读体验。
请进入游戏，在游戏设置内将游戏基础语言设定为英文，以获得最佳体验。

已经正确安装插件，但启动仍是英文:
请您点击游戏启动页左下角的第二个按钮，以打开语言选择框，将语言设为LLC_zh-CN。然后重启游戏即可。

我的字体出现问题:
您是否正确装载了零协会提供的字体？

请确认您的字体文件夹Limbus Company\\LimbusCompany_Data\\Lang\\LLC_zh-CN\\Font内部是否有且仅有我们提供的ChineseFont.ttf字体文件。
请删除其它额外字体以恢复您的体验。

安装工具箱常见问题:
无法使用插件安装器安装翻译插件，安装器报错,
事实证明，大部分问题是网络问题。针对网络问题，敬请参考排除安装器网络问题的综合指引(https://www.zeroasso.top/docs/FAQ#network-fix )。

校验Hash失败:
如果您是在插件刚释放最新版本时就更新的，请先等待几分钟，刷个视频再回来继续,
切换节点(https://www.zeroasso.top/docs/configuration/nodes )再尝试,
选择一个可用的节点非常重要，对您是否能顺利下载起决定性作用。
更换网络环境再尝试:
例如：开/关加速器或代理、更换另一个网络、使用手机热点.
找不到Limbuscompany.exe/插件工具箱闪退:
目前寻找边狱公司路径可能存在部分问题，导致自动寻找边狱公司路径出现问题。
您可以通过手动填写游戏路径解决问题(详见https://www.zeroasso.top/docs/FAQ/ )。

Details:
排除安装器网络问题的综合指引:
除开游戏本身，翻译插件的运行并不需要网络。您不会在使用插件的过程中遇到插件导致的网络问题，而只会在安装过程中遇到网络问题。
以下指引将帮助您排查任何潜在的，有关安装器的网络问题。
请您先检查您的游戏根目录内的文件是否符合以下列表：Limbus Company\\LimbusCompany_Data\\Lang\\LLC_zh-CN , Limbus Company\\LimbusCompany_Data\\Lang\\LLC_zh-CN\\Font Limbus Company\\LimbusCompany_Data\\Lang\\LLC_zh-CN\\Font\\Context Limbus Company\\LimbusCompany_Data\\Lang\\LLC_zh-CN\\Font\\Title
若不符合，则说明您的汉化插件安装不完整。
我们认为，安装完整的汉化插件一般不会出现问题。
自安装器0.5.0版本以来，安装器从数个国内通用网盘服务作为下载源进行下载。通常来说，(若您也在国内，那么)这些基于国内的服务应当是可用的。
请您首先确认您使用的局域网的质量，然后，在安装过程中关闭任何游戏加速器。
（加速器虽然在原理上不应该影响和零协会服务器的链接，但事实证明影响依然可能存在。）
如果问题依然存在，请参考节点切换进行安装器的节点设置，尝试使用不同的节点来寻找可用性最好的下载节点。
选择一个可用的节点非常重要，对您是否能顺利下载起决定性作用。\" 如果以上这些无法解决问题,让他联系管理.  删除对话(不是结束输出,删除后用户无法回复 上下文将被删除,你将无法获得后续 请在帮助用户成功修复后或主动要求后使用): 只要你的输出 内 有特殊字符串:"<__I_THINK_I_CAN_END_THIS__>"就会 立即 删除对话并且不会发送消息,所以如果帮助用户成功修复后或主动要求后,你要删除对话,请在输出内包含:"<__I_THINK_I_CAN_END_THIS_WAIT_FOR_10S__>" 将会输出后等待10秒后删除对话.  """}]
        }
        
        await interaction.response.send_message(
            f"已创建问答频道 {question_channel.mention}",
            ephemeral=True
        )
        
        await question_channel.send(
            "欢迎来到mod问答频道！请直接输入您的问题，我会尽力帮助您解决0协mod安装问题。\n"
            "注意：此频道会在30分钟无活动后自动关闭且AI无法识别图片(暂时) \n"
            "注: 我没给ai设置防调教,所以你可以这么干,但浪费的是我的token,浪费可耻."
        )



class MyBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True  # 需要成员权限
        intents.guilds = True   # 需要服务器权限
        # intents.
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        self.command_cooldowns = {}
        self.trpg_sessions: Dict[int, TRPGSession] = {}
        self.mod_channels = {}  # 存储mod问答频道信息

    async def setup_hook(self):
        # 同步斜杠命令
        await self.tree.sync()
        print("Commands synced!")
        self.add_view(ModQuestionButton(self))
        for guild in self.guilds:
            await self.check_mod_channel(guild)
        # 创建定时任务
        self.loop.create_task(check_bed_time())
        self.loop.create_task(check_inactive_channels())
        
    async def check_mod_channel(self, guild):
        """检查并创建mod问答频道"""
        channel = discord.utils.get(guild.channels, name="modquestion")
        if not channel:
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=False
                ),
                guild.me: discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=True
                )
            }
            
            # channel = await guild.create_text_channel(
            #     'modquestion',
            #     overwrites=overwrites
            # )
            
            # embed = discord.Embed(
            #     title="安装问答助手",
            #     description="点击下方按钮开始提问",
            #     color=discord.Color.blue()
            # )
            
            # await channel.send(embed=embed, view=ModQuestionButton(self))

    
    def check_rate_limit(self, user_id: int) -> tuple[bool, float]:
        """
        检查用户是否超过频率限制
        返回: (是否允许使用, 剩余等待时间)
        """
        current_time = time.time()
        user_times = self.command_cooldowns.get(user_id, [])
        
        # 清理超过60秒的记录
        user_times = [t for t in user_times if current_time - t < 60]
        self.command_cooldowns[user_id] = user_times or []
        
        if len(user_times) >= 5:
            wait_time = 60 - (current_time - user_times[0])
            return False, round(wait_time)
            
        user_times.append(current_time)
        return True, 0


async def download_image(url: str, filename: str) -> bool:
    """下载图片到本地"""
    try:
        # print(f"下载图片: {url}")
        headers = {
            "Referer": "https://i.pixiv.re/"  # 设置 Referer 头
        }
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    async with aiofiles.open(filename, 'wb') as f:
                        await f.write(await resp.read())
                    return True
                elif resp.status == 404:
                    print(f"图片下载失败: 404 Not Found - {url}")
                    return False
                else:
                    print(f"图片下载失败: 状态码 {resp.status} - {url}")
                    return False
    except Exception as e:
        print(f"下载图片错误: {e}")
    return False
async def compress_image_to_limit(filename: str, max_size: int = MAX_DISCORD_FILE_SIZE) -> str:
    """压缩图片到不超过max_size，返回压缩后文件名（覆盖原文件）"""
    try:
        quality = 95
        with Image.open(filename) as img:
            img = img.convert("RGB")
            while os.path.getsize(filename) > max_size and quality > 10:
                img.save(filename, format="JPEG", quality=quality)
                quality -= 10
        return filename if os.path.getsize(filename) <= max_size else None
    except Exception as e:
        print(f"图片压缩失败: {e}")
        return None


# 创建机器人实例
bot = MyBot()
aapi = AppPixivAPI()
loginJson = aapi.auth(refresh_token=pixiv_refresh_token)
pixiv_logined = aapi.access_token != None
aapi.set_accept_language("zh-cn")  # 设置语言为中文
print("Pixiv logined:",loginJson)
@bot.tree.command(name="createmod", description="创建mod问答频道")
@app_commands.describe(
    name="频道名称(可选)"
)
async def createmod(interaction: discord.Interaction, name: str = "ModQuestion"):
    """创建新的mod问答频道"""
    # 检查权限
    if not interaction.user.guild_permissions.manage_channels:
        await interaction.response.send_message("你没有权限创建频道!", ephemeral=True)
        return
        
    # 检查是否已存在同名频道
    channel = discord.utils.get(interaction.guild.channels, name=name)
    if channel:
        await interaction.response.send_message(f"频道 #{name} 已存在!", ephemeral=True)
        return

    try:
        # 创建新频道
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(
                read_messages=True,
                send_messages=False
            ),
            interaction.guild.me: discord.PermissionOverwrite(
                read_messages=True,
                send_messages=True
            )
        }

        channel = await interaction.guild.create_text_channel(
            name,
            overwrites=overwrites
        )
        
        embed = discord.Embed(
            title="Mod问答助手",
            description="点击下方按钮开始提问,将为您创建专属问答频道(自动删除)。\n注意:不要在同一时间创建过多频道,这会增加服务器负担。\n注:机器人回答会有些许延迟,这是正常现象。",
            color=discord.Color.blue()
        )
        
        await channel.send(embed=embed, view=ModQuestionButton(bot))
        await interaction.response.send_message(
            f"已创建mod问答频道 {channel.mention}",
            ephemeral=True
        )
        
    except discord.Forbidden:
        await interaction.response.send_message(
            "创建频道失败:权限不足",
            ephemeral=True
        )
    except Exception as e:
        await interaction.response.send_message(
            f"创建频道时发生错误: {str(e)}",
            ephemeral=True
        )

    
RANDOM_MODE = [
    "day",
    "week",
    "month",
    "day_male",
    "day_female",
    "week_original",
    "week_rookie",
    "day_manga",
    "day_r18",
    "day_male_r18",
    "day_female_r18",
    "week_r18",
    "week_r18g",
]

R18_MODE = [
    "day_r18",
    "day_male_r18",
    "day_female_r18",
    "week_r18",
    "week_r18g",
]
NORMAL_MODE = [
    "day",
    "week",
    "month",
    "day_male",
    "day_female",
    "week_original",
    "week_rookie",
    "day_manga",
]

@bot.tree.command(name="setu", description="Send a random pixiv photo"
                      )
@app_commands.describe(
        r18="Enable R18? (No: 0, Yes: 1, Random: 2)",
        num="Number of images to return (1-20)",
        tags0="Tags to filter images (e.g., '萝莉 少女|白丝 黑丝')",
        tags1="Tags to filter images (e.g., '萝莉 少女|白丝 黑丝')",
        tags2="Tags to filter images (e.g., '萝莉 少女|白丝 黑丝')",
        tags3="Tags to filter images (e.g., '萝莉 少女|白丝 黑丝')",
        tags4="Tags to filter images (e.g., '萝莉 少女|白丝 黑丝')",
        public="show it to another default true",
        api="API to use (0: lolicon, 1: anosu,2: both)"
    )
@app_commands.choices(r18=[
        app_commands.Choice(name="No (Non-R18)", value="no"),
        app_commands.Choice(name="Yes (R18)", value="yes"),
        app_commands.Choice(name="Random (Mixed)", value="random")
    ],api = [
        app_commands.Choice(name="lolicon", value=0),
        app_commands.Choice(name="anosu", value=1),
        app_commands.Choice(name="both", value=2)
    ])
async def setu(interaction: discord.Interaction, r18: str, num: int = 1, tags0: str = None,tags1: str = None,tags2: str = None
                ,tags3: str = None,tags4: str = None,public:bool = True,api:int = 2):
    allowed, wait_time = bot.check_rate_limit(interaction.user.id)
    if not allowed:
            await interaction.response.send_message(
                f"人要节制点 注意身体，请等待 {wait_time} 秒后再试。",
            )
            return
    public = not public
        
    await interaction.response.defer(ephemeral=public,thinking=True)  # 延迟响应
        # 调用 API 获取图片
    tags = [tag for tag in [tags0, tags1, tags2, tags3, tags4] if tag is not None]
    r18_param = {
            "no": 0,
            "yes": 1,
            "random": 2
        }.get(r18, 2)
    if interaction.channel.type != discord.ChannelType.private or type(interaction.channel) != discord.DMChannel:
        if not interaction.channel.is_nsfw():
                if r18_param == 1:
                        await interaction.followup.send("不准在非r18里色色!",ephemeral=True)
                        return
                elif r18_param == 2:
                    r18_param = 0
    params_1 = {
        "r18": r18_param,
        "num": max(1, min(num, 20)),  # 限制 num 在 1 到 20 之间
    }
    params_2:Dict[str,Any] = {
        "num": max(1, min(num, 15)),  # 限制 num 在 1 到 15 之间
        "r18": r18_param,
    } 
    if tags:
        # 将用户输入的 tags 按 '|' 分隔，适配 api2 的多关键词功能
        params_1["tag"] = tags  # 适用于 api1
        params_2["keyword"] = " ".join(tags)  # 适用于 pixiv
    api_url_1 = "https://api.lolicon.app/setu/v2"
    

    # API 2: https://image.anosu.top/pixiv/json
    # api_url_2 = "https://image.anosu.top/pixiv/json" # 寄-----
    if not public:
            if num >4:
                await interaction.followup.send("在公开情况下数量超过4 可能刷屏 已拒绝执行;(",ephemeral=True)
                return
        
    if not pixiv_logined:
        try:
            image_data = []
            if api == 0 or api == 2 or api == 1:
                # 只使用 API 1
                response_api_1 = requests.post(api_url_1, json=params_1)
                response_api_1.raise_for_status()
                image_data = response_api_1.json().get("data", [])

                    

            # 处理图片数据
            if not image_data:
                await interaction.followup.send("没有找到符合条件的图片", ephemeral=True)
                return

            print(f"image_data: {image_data}")
            for image in image_data:
                image_url = image.get("url")
                if image_url == None:
                    image_url = image.get("urls", {}).get("original")
                if not image_url or not isinstance(image_url, str):
                    print(f"无效的图片 URL: {image_url}")
                    continue

                temp_filename = f"temp_{uuid.uuid4()}.jpg"
                print(f"下载图片: {image_url}")
                max_retries = 4
                retry_count = 0
                show_url = "https://www.pixiv.net/artworks/" + str(image.get("pid", "unknown"))
                # 下载图片
                while retry_count < max_retries:
                    if await download_image(image_url, temp_filename):
                        print(f"图片下载成功: {image_url}")
                        break
                    else:
                        print(f"图片下载失败: {image_url}，重试次数: {retry_count + 1}")
                        retry_count += 1

                        # # 如果达到最大重试次数，切换到 API 2
                        # if retry_count == max_retries:
                        #     print("切换到 API 2 获取新图片...")
                        #     response_api_2 = requests.get(api_url_2, params=params_2)
                        #     response_api_2.raise_for_status()
                        #     new_image_data = response_api_2.json()
                        #     if new_image_data:
                        #         image = new_image_data[0]  # 获取新图片
                        #         image_url = image.get("url")
                        #         if image_url == None:
                        #             image_url = image.get("urls", {}).get("original")
                        #         retry_count = 0  # 重置重试计数
                        #     else:
                        #         print("API 2 没有返回有效图片，跳过当前图片")
                        #         break

                if retry_count == max_retries:
                    embed = discord.Embed(title=f"下载图片错误：")
                    a = ""
                    if image.get("author", "") != "":
                        a = image.get("author", "")
                    elif image.get("user", "") != "":
                        a = image.get("user", "")
                    else:
                        a = "未知"
                    embed.add_field(name="标题", value=image.get("title", "未知"), inline=True)
                    embed.add_field(name="作者", value=a, inline=True)
                    embed.add_field(name="PID", value=show_url, inline=True)
                    embed.add_field(name="标签", value=", ".join(image.get("tags", [])), inline=False)
                    embed.add_field(name="URL", value=image_url, inline=False)
                    embed.add_field(name="重试次数:", value=retry_count, inline=False)
                    await interaction.followup.send(embed=embed, ephemeral=True)
                    continue  # 跳过当前图片

                try:
                    # 检查文件大小，超限则压缩
                    if os.path.getsize(temp_filename) > MAX_DISCORD_FILE_SIZE:
                        compressed_filename = await compress_image_to_limit(temp_filename, MAX_DISCORD_FILE_SIZE)
                        if not compressed_filename:
                            await interaction.followup.send("图片过大且压缩失败", ephemeral=True)
                            os.remove(temp_filename)
                            continue
                        temp_filename = compressed_filename

                    # 上传图片
                    file = discord.File(temp_filename)
                    embed = discord.Embed(title=f"Pixiv Image")
                    embed.add_field(name="标题", value=image.get("title", "未知"), inline=True)
                    a = ""
                    if image.get("author", "") != "":
                        a = image.get("author", "")
                    elif image.get("user", "") != "":
                        a = image.get("user", "")
                    else:
                        a = "未知"
                    embed.add_field(name="作者", value=a, inline=True)
                    embed.add_field(name="PID", value=show_url, inline=True)
                    embed.add_field(name="标签", value=", ".join(image.get("tags", [])), inline=False)
                    embed.add_field(name="URL", value=image_url, inline=False)
                    embed.add_field(name="重试次数:", value=retry_count, inline=False)
                    
                    embed.set_image(url=f"attachment://{os.path.basename(temp_filename)}")
                    await interaction.followup.send(file=file, embed=embed, ephemeral=public)
                    os.remove(temp_filename)
                except Exception as e:
                    embed = discord.Embed(title=f"上传图片错误：{str(e)}")
                    a = ""
                    if image.get("author", "") != "":
                        a = image.get("author", "")
                    elif image.get("user", "") != "":
                        a = image.get("user", "")
                    else:
                        a = "未知"
                    embed.add_field(name="标题", value=image.get("title", "未知"), inline=True)
                    embed.add_field(name="作者", value=a, inline=True)
                    embed.add_field(name="PID", value=show_url, inline=True)
                    embed.add_field(name="标签", value=", ".join(image.get("tags", [])), inline=False)
                    embed.add_field(name="URL", value=image_url, inline=False)
                    embed.add_field(name="重试次数:", value=retry_count, inline=False)
                    
                    await interaction.followup.send(embed=embed, ephemeral=True)
                    os.remove(temp_filename)

        except requests.exceptions.RequestException as e:
            await interaction.followup.send(f"API 请求失败: {str(e)}", ephemeral=True)
        except Exception as e:
            embed = discord.Embed(title=f"Exception as e: {str(e)}")
            await interaction.followup.send(embed=embed, ephemeral=True)
    else:
        try:
            image_data = []
            random.seed(time.time())
            if tags:
                UnPar = aapi.search_illust(params_2["keyword"],sort=random.choice(["date_desc", "date_asc", "popular_desc"]))
            else:
                if r18_param == 2:
                    UnPar = aapi.illust_ranking(mode=random.choice(RANDOM_MODE))
                elif r18_param == 1:
                    UnPar = aapi.illust_ranking(mode=random.choice(R18_MODE))
                else:
                    UnPar = aapi.illust_ranking(mode=random.choice(NORMAL_MODE))
            UnPar["illusts"] = [i for i in UnPar["illusts"] if (i.x_restrict == r18_param or r18_param == 2) and not i.is_manga]  # 只获取已收藏的插画
            for i in UnPar["illusts"]:
                image_data.append({
                        "pid": i["id"],
                        "title": i["title"],
                        "author": i["user"]["name"],
                        "tags": [tag["name"]for tag in i["tags"]],
                        "url": i["image_urls"].get("large", i["image_urls"].get("medium")),
                        "user": i["user"]["name"]
                    })
            
            get_count = num + 2
            wi = 0
            while UnPar["next_url"] != None:
                wi += 1
                NextParm = aapi.parse_qs(UnPar["next_url"])
                if tags:
                    UnPar = aapi.search_illust(**NextParm)
                else:
                    UnPar = aapi.illust_ranking(**NextParm)
                UnPar["illusts"] = [i for i in UnPar["illusts"] if (i.x_restrict == r18_param or r18_param == 2) and not i.is_manga]  # 只获取已收藏的插画
                for i in UnPar["illusts"]:
                    image_data.append({
                        "pid": i["id"],
                        "title": i["title"],
                        "author": i["user"]["name"],
                        "tags": [tag["name"]for tag in i["tags"]],
                        "url": i["image_urls"].get("large", i["image_urls"].get("medium")),
                        "user": i["user"]["name"],
                        "x_restrict": i["x_restrict"]
                    })
                if wi == get_count:
                    break
                print(wi)
            # 处理图片数据
            if not image_data:
                await interaction.followup.send("没有找到符合条件的图片", ephemeral=True)
                return

            print(f"image_data: {image_data}")
            random.shuffle(image_data)  # 打乱图片顺序
            image_data = random.choices(image_data, k=num)
            for image in image_data:
                image_url = image.get("url")
                show_url = "https://www.pixiv.net/artworks/" + str(image.get("pid", "unknown"))
                
                if image_url == None:
                    image_url = image.get("urls", {}).get("original")
                if not image_url or not isinstance(image_url, str):
                    print(f"无效的图片 URL: {image_url}")
                    continue

                temp_filename = f"temp_{uuid.uuid4()}.jpg"
                print(f"下载图片: {image_url}")
                max_retries = 4
                retry_count = 0
                # 下载图片
                # 
                while retry_count < max_retries:
                    if aapi.download(image_url, name=temp_filename):
                        print(f"图片下载成功: {image_url}")
                        break
                    else:
                        print(f"图片下载失败: {image_url}，重试次数: {retry_count + 1}")
                        retry_count += 1

                        # # 如果达到最大重试次数，切换到 API 2
                        # if retry_count == max_retries:
                        #     print("切换到 API 2 获取新图片...")
                        #     response_api_2 = requests.get(api_url_2, params=params_2)
                        #     response_api_2.raise_for_status()
                        #     new_image_data = response_api_2.json()
                        #     if new_image_data:
                        #         image = new_image_data[0]  # 获取新图片
                        #         image_url = image.get("url")
                        #         if image_url == None:
                        #             image_url = image.get("urls", {}).get("original")
                        #         retry_count = 0  # 重置重试计数
                        #     else:
                        #         print("API 2 没有返回有效图片，跳过当前图片")
                        #         break

                if retry_count == max_retries:
                    embed = discord.Embed(title=f"下载图片错误：")
                    a = ""
                    if image.get("author", "") != "":
                        a = image.get("author", "")
                    elif image.get("user", "") != "":
                        a = image.get("user", "")
                    else:
                        a = "未知"
                    embed.add_field(name="标题", value=image.get("title", "未知"), inline=True)
                    embed.add_field(name="作者", value=a, inline=True)
                    embed.add_field(name="PID", value=image.get("pid", "未知"), inline=True)
                    embed.add_field(name="标签", value=", ".join(image.get("tags", [])), inline=False)
                    embed.add_field(name="URL", value=image_url, inline=False)
                    embed.add_field(name="重试次数:", value=retry_count, inline=False)
                    await interaction.followup.send(embed=embed, ephemeral=True)
                    continue  # 跳过当前图片

                try:
                    # 检查文件大小，超限则压缩
                    if os.path.getsize(temp_filename) > MAX_DISCORD_FILE_SIZE:
                        compressed_filename = await compress_image_to_limit(temp_filename, MAX_DISCORD_FILE_SIZE)
                        if not compressed_filename:
                            await interaction.followup.send("图片过大且压缩失败", ephemeral=True)
                            os.remove(temp_filename)
                            continue
                        temp_filename = compressed_filename

                    # 上传图片
                    file = discord.File(temp_filename)
                    embed = discord.Embed(title=f"Pixiv Image")
                    embed.add_field(name="标题", value=image.get("title", "未知"), inline=True)
                    a = ""
                    if image.get("author", "") != "":
                        a = image.get("author", "")
                    elif image.get("user", "") != "":
                        a = image.get("user", "")
                    else:
                        a = "未知"
                    embed.add_field(name="作者", value=a, inline=True)
                    embed.add_field(name="PID", value=image.get("pid", "未知"), inline=True)
                    embed.add_field(name="标签", value=", ".join(image.get("tags", [])), inline=False)
                    embed.add_field(name="URL", value=show_url, inline=False)
                    embed.add_field(name="重试次数:", value=retry_count, inline=False)
                    
                    embed.set_image(url=f"attachment://{os.path.basename(temp_filename)}")
                    await interaction.followup.send(file=file, embed=embed, ephemeral=public)
                    os.remove(temp_filename)
                except Exception as e:
                    embed = discord.Embed(title=f"上传图片错误：{str(e)}")
                    a = ""
                    if image.get("author", "") != "":
                        a = image.get("author", "")
                    elif image.get("user", "") != "":
                        a = image.get("user", "")
                    else:
                        a = "未知"
                    embed.add_field(name="标题", value=image.get("title", "未知"), inline=True)
                    embed.add_field(name="作者", value=a, inline=True)
                    embed.add_field(name="PID", value=image.get("pid", "未知"), inline=True)
                    embed.add_field(name="标签", value=", ".join(image.get("tags", [])), inline=False)
                    embed.add_field(name="URL", value=show_url, inline=False)
                    embed.add_field(name="重试次数:", value=retry_count, inline=False)
                    
                    await interaction.followup.send(embed=embed, ephemeral=True)
                    os.remove(temp_filename)

        except requests.exceptions.RequestException as e:
            await interaction.followup.send(f"API 请求失败: {str(e)}", ephemeral=True)
        except Exception as e:
            embed = discord.Embed(title=f"Exception as e: {str(e)}")
            await interaction.followup.send(embed=embed)
    
@bot.tree.command(name="thanks", description="Send a thanks(?)")
async def help(interaction: discord.Interaction):
    await interaction.followup.send("""1.框架:discord.py
2.使用api:"https://api.lolicon.app/setu/v2"
3.gui我实在不想写了所以感谢copilot""",ephemeral=True)




class TRPGSession:
    def __init__(self, host_id: int, channel_id: int,start_channel_id: int):
        self.host_id = host_id
        self.channel_id = channel_id
        self.start_channel_id = start_channel_id  # 记录启动频道
        self.players: Set[int] = {host_id}
        self.ban_players: dict[int,list[int]] = {}
        # self.waiting_players: list[dict[int,int]] = {}
        self.points_template: Dict[str, int] = {}  # 点数项目列表
        self.player_points: Dict[int, Dict[str, int]] = {}  # 玩家的点数
        self.personal_memos: Dict[int, List[str]] = {}  # 每个人的个人备忘录
        self.host_player_memos: Dict[int, List[str]] = {}  # 主持人对玩家的备忘录
        self.total_points: int = 0  # 总点数
        self.player_hp: Dict[int, int] = {}  # 玩家血量
        
group = app_commands.Group(name="trpo", description="TRPO")

@group.command(name="start", description="跑团启动!")
@app_commands.describe(
    public="是否公开频道（可见但不可发言）"
)
async def startT(interaction: discord.Interaction,public:bool = False):
    """创建新的跑团会话"""
    # 检查机器人权限
    required_permissions = discord.Permissions(
        manage_channels=True,
        read_messages=True,
        send_messages=True,
        manage_permissions=True
    )
    
    missing_permissions = []
    for perm_name, perm_value in required_permissions:
        if perm_value and not getattr(interaction.guild.me.guild_permissions, perm_name):
            missing_permissions.append(perm_name)
    
    if missing_permissions:
        await interaction.response.send_message(
            f"错误：机器人缺少以下权限：\n" + 
            "\n".join([f"- {perm.replace('_', ' ').title()}" for perm in missing_permissions]) +
            "\n请确保给予足够权限。",
            ephemeral=True,
        )
        return

    guild_id = interaction.guild_id
    if guild_id in bot.trpg_sessions:
        await interaction.response.send_message("本服务器已有跑团在进行中!", ephemeral=True)
        return

    try:
        # 创建新的文字频道
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(
                read_messages=public,  # public=True 时可见
                send_messages=False    # 始终不可发言
            ),
            interaction.guild.me: discord.PermissionOverwrite(
                read_messages=True, 
                send_messages=True
            ),
            interaction.user: discord.PermissionOverwrite(
                read_messages=True, 
                send_messages=True
            )
        }
        
        channel = await interaction.guild.create_text_channel(
            f'trpg-{interaction.user.display_name}', 
            overwrites=overwrites,
            reason=f"TRPG session started by {interaction.user.display_name}"
        )
        
        # 创建新的跑团会话
        session = TRPGSession(interaction.user.id, channel.id,start_channel_id=interaction.channel_id)
        bot.trpg_sessions[interaction.user.id] = session
        
        await interaction.response.send_message(
            f"跑团已启动!\n"
            f"主持人: {interaction.user.mention}\n"
            f"频道: {channel.mention}\n", 
            ephemeral=False
        )
    
    except discord.Forbidden:
        await interaction.response.send_message(
            "错误：没有足够的权限创建频道。请确保机器人有管理频道的权限。",
            ephemeral=True
        )
    except Exception as e:
        await interaction.response.send_message(
            f"创建频道时发生错误：{str(e)}",
            ephemeral=True
        )

@group.command(name="join", description="加入跑团")
@app_commands.describe(
    host="主持人"
)
async def joinT(interaction: discord.Interaction, host: Member):
    """加入当前跑团"""
    if host.id not in bot.trpg_sessions:
        await interaction.response.send_message("host当前没有进行中的跑团!", ephemeral=True)
        return

    session = bot.trpg_sessions[host.id]
    if interaction.user.id in session.players:
        await interaction.response.send_message("你已经在跑团中了!", ephemeral=True)
        return
    if interaction.user.id in session.ban_players:
        await interaction.response.send_message("你已被主持人拒绝加入跑团!", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True,thinking=True)  # 延迟响应
    await interaction.followup.send("申请已发送，等待主持人批准...", ephemeral=True)

    # 获取频道
    channel = interaction.guild.get_channel(session.channel_id)
    applicant = interaction.user  # 保存一下申请人对象
    
    

    # 创建审批按钮视图
    class ApproveView(View):
        def __init__(self):
            super().__init__(timeout=60)  # ⏱️ 设置超时时间为 60 秒
            self.message = None  # 后面用于保存消息引用

        async def interaction_check(self, i: Interaction) -> bool:
            if i.user.id != host.id:
                await i.response.send_message("你不是主持人，无法审批。", ephemeral=True)
                return False
            return True

        @discord.ui.button(label="✅ 同意加入", style=ButtonStyle.success)
        async def approve(self, i: Interaction, button: Button):
            session.players.add(applicant.id)
            await channel.set_permissions(applicant, read_messages=True, send_messages=True)

            # 通知申请人
            await interaction.followup.send(f"✅ 你的加入请求已被主持人批准 频道:{channel.mention}", ephemeral=True)


            # 修改审批消息
            await i.response.edit_message(content=f"✅ {applicant.mention} 已被主持人批准加入跑团！", view=None)
            self.stop()

        @discord.ui.button(label="❌ 拒绝加入", style=ButtonStyle.danger)
        async def reject(self, i: Interaction, button: Button):
            
            await i.response.edit_message(content=f"❌ {applicant.mention} 的申请被主持人拒绝。", view=None)
            await interaction.followup.send(f"❌ {applicant.mention} 你的加入请求已被主持人拒绝",ephemeral=True)
            
            self.stop()
            
        @discord.ui.button(label="❌ 拒绝加入并在此次跑团内 永久 拒绝", style=ButtonStyle.danger)
        async def reject_ban(self, i: Interaction, button: Button):
            origin_channel = interaction.channel  # 原始 /join 执行频道
            
            session.ban_players.add(applicant.id)
            await i.response.edit_message(content=f"❌ {applicant.mention} 的申请被主持人拒绝。", view=None)
            await interaction.followup.send(f"❌ {applicant.mention} 你的加入请求已被主持人在此次跑团内 永久 拒绝",ephemeral=True)
            
            self.stop()

        async def on_timeout(self):
            if not self.message:  # 安全检查
                return
            await self.message.edit(content=f"⌛ {applicant.mention} 的申请已超时，系统自动拒绝。", view=None)
            origin_channel = interaction.channel  # 原始 /join 执行频道
            await origin_channel.send(f"❌ {applicant.mention} 你的加入请求已被主持人拒绝(超时)")
            
    # 发送审批消息到频道
    await channel.send(
        f"📨 {host.mention} 玩家 {applicant.mention} 请求加入跑团，是否批准？(60秒超时自动拒绝)",
        view=ApproveView()
    )
    
@group.command(name="player",description="玩家管理")
@app_commands.choices(option=[
        app_commands.Choice(name="list", value="list"),
        app_commands.Choice(name="kick", value="kick"),

    ])
async def playerT(interaction : discord.Interaction,option:str,target:Optional[Member] = None,banned:Optional[bool]=False):
    session = bot.trpg_sessions[interaction.user.id]
    if interaction.user.id != session.host_id:
        await interaction.response.send_message("只有主持人才能使用", ephemeral=True)
        return
    re:str ="如果你见到这句话 包出错了"
    if option == "list":
        re = "===目前玩家===:\n"
        for n in session.players:
            re += bot.get_user(n).name + "\n"
        re += "===永久拒绝===:"
        for n in session.ban_players:
            re += bot.get_user(n).name + "\n"
        await interaction.response.send_message(re,ephemeral=True)
        return
    elif option == "kick":
        del session.player_points[target.id]
        del session.personal_memos[target.id]
        del session.host_player_memos[target.id]
        await bot.get_channel(session.channel_id).set_permissions(target, read_messages=True, send_messages=True)
        session.players.remove(target.id)
        re = f"{target.name} 已被主持人移除!"
        await interaction.response.send_message(re)
        return
        
@group.command(name="stop", description="结束跑团")
async def stopT(interaction: discord.Interaction):
    """结束跑团并保存聊天记录"""
    session = None
    for n,k in bot.trpg_sessions.items():
        if interaction.channel_id == k.channel_id:
            session = k
    if session == None:
        await interaction.response.send_message("未发现加入的跑团!", ephemeral=True)
        return
    
    session = bot.trpg_sessions[interaction.user.id]
    if interaction.user.id != session.host_id:
        await interaction.response.send_message("只有主持人才能结束跑团!", ephemeral=True)
        return

    # 获取频道
    channel = interaction.guild.get_channel(session.channel_id)
    start_channel = interaction.guild.get_channel(session.start_channel_id)
    
    if not channel or not start_channel:
        await interaction.response.send_message("找不到跑团频道或原始频道!", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=False)
    
    try:
        # 获取所有消息
        messages = []
        async for message in channel.history(limit=None, oldest_first=True):
            timestamp = message.created_at.strftime("%Y-%m-%d %H:%M:%S")
            content = f"[{timestamp}] {message.author.display_name}: {message.content}"
            if message.attachments:
                content += "\n附件: " + ", ".join(a.url for a in message.attachments)
            messages.append(content)

        # 创建日志文件
        log_filename = f"trpg_log_{interaction.guild.id}_{int(time.time())}.txt"
        with open(log_filename, "w", encoding="utf-8") as f:
            f.write("\n".join(messages))

        # 发送日志文件到启动频道
        await start_channel.send(
            f"跑团已结束，这是 {channel.mention} 的聊天记录(有bug)：",
            file=discord.File(log_filename)
        )

        # 删除本地日志文件
        os.remove(log_filename)
        
        # 发送频道删除通知
        await channel.send("跑团已结束，频道将在 5 秒后删除...")
        await asyncio.sleep(5)
        
        # 删除频道
        await channel.delete()
        
        # 清理会话
        del bot.trpg_sessions[interaction.user.id]
        
        # await interaction.followup.send("跑团已结束，记录已保存。", ephemeral=False)
        
    except Exception as e:
        await interaction.followup.send(f"结束跑团时发生错误：{str(e)}", ephemeral=True)

async def check_trpg_channel(interaction: discord.Interaction, session: TRPGSession) -> bool:
    """检查是否在跑团频道中"""
    if interaction.channel_id != session.channel_id:
        await interaction.response.send_message(
            f"请在跑团频道 <#{session.channel_id}> 中使用此命令!",
            ephemeral=True
        )
        return False
    return True

@group.command(name="memo", description="备忘录")
@app_commands.describe(
    action="操作类型（write: 写入, read: 读取）",
    content="备忘内容（写入时必填）",
    memo_type="备忘类型（personal: 个人备忘, host: 主持人对玩家的备忘）",
    target="目标玩家（仅当主持人使用 host 类型时需要）"
)
@app_commands.choices(
    action=[
        app_commands.Choice(name="写入备忘", value="write"),
        app_commands.Choice(name="读取备忘", value="read")
    ],
    memo_type=[
        app_commands.Choice(name="个人备忘", value="personal"),
        app_commands.Choice(name="主持人备忘", value="host")
    ]
)
async def memoT(
    interaction: discord.Interaction,
    action: str,
    memo_type: str,
    content: Optional[str] = None,
    target: Optional[discord.Member] = None
):
    """备忘录系统"""
    if interaction.channel_id not in bot.trpg_sessions:
        await interaction.response.send_message("该频道当前没有进行中的跑团!", ephemeral=True)
        return
    
    session = None
    for n,k in bot.trpg_sessions.items():
        if interaction.channel_id == k.channel_id:
            session = k
    if session == None:
        await interaction.response.send_message("未发现加入的跑团!", ephemeral=True)
        return
    is_host = interaction.user.id == session.host_id
    if not await check_trpg_channel(interaction, session):
        return
    if action == "write":
        if not content:
            await interaction.response.send_message("写入备忘时必须提供内容!", ephemeral=True)
            return
        
        if memo_type == "personal":
            # 个人备忘录
            if interaction.user.id not in session.personal_memos:
                session.personal_memos[interaction.user.id] = []
            session.personal_memos[interaction.user.id].append(content)
            await interaction.response.send_message(f"已记录个人备忘: {content}", ephemeral=True)
            
        elif memo_type == "host":
            # 主持人对玩家的备忘
            if not is_host:
                await interaction.response.send_message("只有主持人可以使用主持人备忘功能!", ephemeral=True)
                return
            if not target:
                await interaction.response.send_message("需要指定目标玩家!", ephemeral=True)
                return
            if target.id not in session.host_player_memos:
                session.host_player_memos[target.id] = []
            session.host_player_memos[target.id].append(content)
            await interaction.response.send_message(
                f"已记录对 {target.mention} 的备忘: {content}",
                ephemeral=True
            )
    
    elif action == "read":
        if memo_type == "personal":
            # 读取个人备忘录
            memos = session.personal_memos.get(interaction.user.id, [])
            memo_type_str = "个人"
        
        elif memo_type == "host":
            # 读取主持人对玩家的备忘
            if not is_host:
                await interaction.response.send_message("只有主持人可以查看主持人备忘!", ephemeral=True)
                return
            if not target:
                await interaction.response.send_message("需要指定目标玩家!", ephemeral=True)
                return
            memos = session.host_player_memos.get(target.id, [])
            memo_type_str = f"对 {target.mention} 的"
        
        if not memos:
            await interaction.response.send_message(f"没有{memo_type_str}备忘记录!", ephemeral=True)
            return
        
        # 构建备忘列表
        memo_list = "\n".join([f"{i+1}. {memo}" for i, memo in enumerate(memos)])
        await interaction.response.send_message(
            f"===== {memo_type_str}备忘录 =====\n{memo_list}",
            ephemeral=True
        )

@group.command(name="points", description="背板点数管理")
@app_commands.describe(
    action="操作类型（set_total: 设置总点数, assign: 分配点数, list: 查看模板, set_point: 设置点数项目, set_player: 主持人设置玩家点数, hp: 血量管理）",
    point_name="点数名称",
    value="点数值",
    target="目标玩家",
    hp_action="血量操作(set: 设置, damage: 扣除, heal: 恢复)"
)
@app_commands.choices(
    action=[
        app_commands.Choice(name="设置总点数", value="set_total"),
        app_commands.Choice(name="分配点数", value="assign"),
        app_commands.Choice(name="查看模板", value="list"),
        app_commands.Choice(name="设置点数项目", value="set_point"),
        app_commands.Choice(name="血量管理", value="hp")
    ],
    hp_action=[
        app_commands.Choice(name="设置血量", value="set"),
        app_commands.Choice(name="扣除血量", value="damage"),
        app_commands.Choice(name="恢复血量", value="heal")
    ]
)
async def pointsT(
    interaction: discord.Interaction,
    action: str,
    point_name: Optional[str] = None,
    value: Optional[int] = None,
    target: Optional[discord.Member] = None,
    hp_action: Optional[str] = "set"
):
    """管理背板点数"""
    session = None
    for n,k in bot.trpg_sessions.items():
        if interaction.channel_id == k.channel_id:
            session = k
    if session == None:
        await interaction.response.send_message("未发现加入的跑团!", ephemeral=True)
        return
    is_host = interaction.user.id == session.host_id
    if not await check_trpg_channel(interaction, session):
        return
    if action == "set_total":
        # 设置总点数（仅主持人可用）
        if not is_host:
            await interaction.response.send_message("只有主持人才能设置总点数!", ephemeral=True)
            return
        if not value:
            await interaction.response.send_message("请指定总点数!", ephemeral=True)
            return
        session.total_points = value
        await interaction.response.send_message(f"已设置总点数为: {value}", ephemeral=False)

    elif action == "set_point":
        # 设置点数项目（仅主持人可用）
        if not is_host:
            await interaction.response.send_message("只有主持人才能设置点数项目!", ephemeral=True)
            return
        if not point_name:
            await interaction.response.send_message("请指定点数名称!", ephemeral=True)
            return
        session.points_template[point_name] = 0 # 初始值为0
        await interaction.response.send_message(f"已添加点数项目: {point_name}", ephemeral=False)
    
    elif action == "assign":
    # 玩家分配点数
        if not point_name or value is None:
            await interaction.response.send_message("请指定点数名称和值!", ephemeral=True)
            return
        
        if point_name not in session.points_template:
            await interaction.response.send_message(f"点数项目 {point_name} 不存在!", ephemeral=True)
            return
        
        # 确定目标用户（允许主持人为其他玩家分配点数）
        target_id = target.id if target and is_host else interaction.user.id
        target_mention = target.mention if target else interaction.user.mention
        
        if target_id not in session.player_points:
            session.player_points[target_id] = {}
        
        # 计算当前已分配的总点数
        current_total = sum(session.player_points[target_id].values())
        new_total = current_total - session.player_points[target_id].get(point_name, 0) + value
        
        if new_total > getattr(session, 'total_points', 0):
            await interaction.response.send_message(
                f"分配失败：总点数不能超过 {session.total_points}\n"
                f"当前已分配: {current_total}\n"
                f"本次将增加: {value - session.player_points[target_id].get(point_name, 0)}",
                ephemeral=True
            )
            return
        
        session.player_points[target_id][point_name] = value
        
        # 构建剩余点数信息
        remaining = session.total_points - new_total
        
        # 如果是主持人为其他人分配，则公开显示
        is_public_message = target is not None and is_host
        
        await interaction.response.send_message(
            f"已为 {target_mention} 设置 {point_name}: {value}\n"
            f"已分配总点数: {new_total}\n"
            f"剩余可分配: {remaining}",
            ephemeral=not is_public_message  # 主持人分配时公开，自己分配时私密
        )
    # elif action == "set_player":
    #     # 主持人设置玩家点数
    #     if not is_host:
    #         await interaction.response.send_message("只有主持人才能设置玩家点数!", ephemeral=True)
    #         return
    #     if not target or not point_name or value is None:
    #         await interaction.response.send_message("请指定目标玩家、点数名称和值!", ephemeral=True)
    #         return
        
    #     if target.id not in session.player_points:
    #         session.player_points[target.id] = {}
        
    #     session.player_points[target.id][point_name] = value
    #     await interaction.response.send_message(
    #         f"主持人已设置 {target.mention} 的 {point_name} 为 {value}",
    #         ephemeral=False  # 设为公开
    #     )

    elif action == "hp":
        if not is_host:
            await interaction.response.send_message("只有主持人才能管理血量!", ephemeral=True)
            return
        if not target or not value:
            await interaction.response.send_message("请指定目标玩家和数值!", ephemeral=True)
            return
        msg = ""
        if hp_action == "set":
            # 设置血量和最大血量
            session.player_hp[target.id] = value
            msg = f"已设置 {target.mention} 的血量为 {value}"

        elif hp_action == "damage":
            # 扣除血量
            if target.id not in session.player_hp:
                await interaction.response.send_message(f"请先设置 {target.mention} 的血量!", ephemeral=True)
                return
            session.player_hp[target.id] = max(0, session.player_hp[target.id] - value)
            msg = f"{target.mention} 受到 {value} 点伤害，当前血量: {session.player_hp[target.id]}"

        elif hp_action == "heal":
            # 恢复血量
            if target.id not in session.player_hp:
                await interaction.response.send_message(f"请先设置 {target.mention} 的血量!", ephemeral=True)
                return
            session.player_hp[target.id] =  session.player_hp[target.id] + value
            msg = f"{target.mention} 恢复 {value} 点血量，当前血量: {session.player_hp[target.id]}"
        else:
            msg = "错误:需要设置 hp_action"
        await interaction.response.send_message(msg, ephemeral=False)
    elif action == "list":
        # 查看模板和分配情况
        if not hasattr(session, 'total_points'):
            await interaction.response.send_message("主持人还未设置总点数!", ephemeral=True)
            return
        
        # 构建模板信息
        template_info = "=== 点数模板 ===\n"
        template_info += f"总点数: {session.total_points}\n"
        template_info += "可用点数项目:\n"
        for point_name in session.points_template.keys():
            template_info += f"- {point_name}\n"
        
        # 如果是查看自己的分配情况
        user_id = interaction.user.id
        if user_id in session.player_points:
            current_points = session.player_points[user_id]
            total_assigned = sum(current_points.values())
            template_info += "\n=== 当前分配 ===\n"
            for point_name, value in current_points.items():
                template_info += f"{point_name}: {value}\n"
            template_info += f"\n已分配: {total_assigned}"
            template_info += f"\n剩余: {session.total_points - total_assigned}"
            
        # 添加玩家血量显示
        if user_id in session.player_hp and not is_host:
            template_info += f"\n\n=== 当前血量 ===\n"
            template_info += f"血量: {session.player_hp[user_id]}"
        if is_host:
            template_info += "\n=== 玩家状态 ===\n"
            for player_id in session.players:
                member = interaction.guild.get_member(player_id)
                if member:
                    template_info += f"\n{member.display_name}:\n"
                    if player_id in session.player_points:
                        points = session.player_points[player_id]
                        template_info += "点数分配:\n"
                        for point_name, value in points.items():
                            template_info += f"- {point_name}: {value}\n"
                    if player_id in session.player_hp:
                        template_info += f"血量: {session.player_hp[player_id]}\n"
        
        await interaction.response.send_message(template_info, ephemeral=True)


@group.command(name="roll", description="摇点 魅力时刻")
@app_commands.describe(
    max="最大值",
    min="最小值"
)
async def randomT(interaction: discord.Interaction, max: int, min: int):
    """摇骰子"""
    # 修正最大值和最小值的顺序
    if max < min:
        max, min = min, max  # 交换最大值和最小值
        
    # 使用 response.send_message 而不是 followup
    await interaction.response.send_message(
        f"{interaction.user.mention} 掷骰结果: {random.randint(min, max)}"
    )

    
# 添加基础 UI 视图类
class BaseTRPGView(View):
    def __init__(self, session: TRPGSession, user_id: int):
        super().__init__(timeout=180)
        self.session = session
        self.user_id = user_id
    
    async def interaction_check(self, interaction: Interaction) -> bool:
        """检查交互者是否有权限"""
        return interaction.user.id == self.user_id

class MainMenuView(BaseTRPGView):
    """主菜单视图"""
    @discord.ui.button(label="点数管理", style=ButtonStyle.primary)
    async def points_menu(self, interaction: Interaction, button: Button):
        await interaction.response.send_message("点数管理面板", view=PointsView(self.session, interaction.user.id), ephemeral=True)

    @discord.ui.button(label="备忘录", style=ButtonStyle.primary)
    async def memo_menu(self, interaction: Interaction, button: Button):
        await interaction.response.send_message("备忘录面板", view=MemoView(self.session, interaction.user.id), ephemeral=True)

    @discord.ui.button(label="掷骰", style=ButtonStyle.primary)
    async def roll_menu(self, interaction: Interaction, button: Button):
        await interaction.response.send_message("掷骰面板", view=RollView(self.session, interaction.user.id), ephemeral=True)
    
    @discord.ui.button(label="玩家管理", style=ButtonStyle.primary)
    async def player_manage(self, interaction: Interaction, button: Button):
        if interaction.user.id != self.session.host_id:
            await interaction.response.send_message("只有主持人才能管理玩家!", ephemeral=True)
            return

        view = PlayerManageView(self.session)
        await interaction.response.send_message("玩家管理面板", view=view, ephemeral=True)


class PointsView(BaseTRPGView):
    """点数管理视图"""
    def __init__(self, session: TRPGSession, user_id: int):
        self.session = session
        self.user_id = user_id
        super().__init__(session, user_id)

    @discord.ui.button(label="查看状态", style=ButtonStyle.primary)
    async def view_status(self, interaction: Interaction, button: Button):
        # 使用 list 功能的逻辑
        if not hasattr(self.session, 'total_points'):
            await interaction.response.send_message("主持人还未设置总点数!", ephemeral=True)
            return
        
        template_info = "=== 点数模板 ===\n"
        template_info += f"总点数: {self.session.total_points}\n"
        template_info += "可用点数项目:\n"
        for point_name in self.session.points_template.keys():
            template_info += f"- {point_name}\n"
        
        user_id = interaction.user.id
        if user_id in self.session.player_points:
            current_points = self.session.player_points[user_id]
            total_assigned = sum(current_points.values())
            template_info += "\n=== 当前分配 ===\n"
            for point_name, value in current_points.items():
                template_info += f"{point_name}: {value}\n"
            template_info += f"\n已分配: {total_assigned}"
            template_info += f"\n剩余: {self.session.total_points - total_assigned}"
        
        if user_id in self.session.player_hp:
            template_info += f"\n\n=== 当前血量 ===\n"
            template_info += f"血量: {self.session.player_hp[user_id]}"
            
        await interaction.response.send_message(template_info, ephemeral=True)

    @discord.ui.button(label="设置总点数", style=ButtonStyle.primary)
    async def set_total(self, interaction: Interaction, button: Button):
        if interaction.user.id != self.session.host_id:
            await interaction.response.send_message("只有主持人才能设置总点数!", ephemeral=True)
            return
        modal = TotalPointsModal(self.session)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="设置点数项目", style=ButtonStyle.primary)
    async def set_point(self, interaction: Interaction, button: Button):
        if interaction.user.id != self.session.host_id:
            await interaction.response.send_message("只有主持人才能设置点数项目!", ephemeral=True)
            return
        modal = PointItemModal(self.session)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="分配点数", style=ButtonStyle.primary)
    async def assign_points(self, interaction: Interaction, button: Button):
        view = SelectTargetView(self.session,interaction.user.id)
        await interaction.response.send_message(
            "请选择要分配点数的目标：",
            view=view,
            ephemeral=True
        )

    @discord.ui.button(label="血量管理", style=ButtonStyle.primary)
    async def manage_hp(self, interaction: Interaction, button: Button):
        if interaction.user.id != self.session.host_id:
            await interaction.response.send_message("只有主持人才能管理血量!", ephemeral=True)
            return
        view = HPManageView(self.session)
        await interaction.response.send_message("血量管理面板", view=view, ephemeral=True)

# 添加新的 Modal 类
class TotalPointsModal(discord.ui.Modal):
    def __init__(self, session: TRPGSession):
        super().__init__(title="设置总点数")
        self.session = session
        self.value = discord.ui.TextInput(
            label="总点数",
            placeholder="请输入总点数值"
        )
        self.add_item(self.value)

    async def on_submit(self, interaction: Interaction):
        try:
            value = int(self.value.value)
            self.session.total_points = value
            await interaction.response.send_message(
                f"已设置总点数为: {value}",
                ephemeral=False
            )
        except ValueError:
            await interaction.response.send_message("请输入有效的数字!", ephemeral=True)

class PointItemModal(discord.ui.Modal):
    def __init__(self, session: TRPGSession):
        super().__init__(title="设置点数项目")
        self.session = session
        self.point_name = discord.ui.TextInput(
            label="项目名称",
            placeholder="请输入点数项目名称"
        )
        self.add_item(self.point_name)

    async def on_submit(self, interaction: Interaction):
        name = self.point_name.value
        self.session.points_template[name] = 0
        await interaction.response.send_message(
            f"已添加点数项目: {name}",
            ephemeral=False
        )
class HPManageView(BaseTRPGView):
    def __init__(self, session: TRPGSession):
        super().__init__(session, session.host_id)
        self.session = session
        self.selected_player = None
        
        # 创建玩家选择下拉菜单
        options = []
        for player_id in session.players:
                member = bot.get_channel(session.channel_id).guild.get_member(player_id)
                if member:
                    options.append(
                        discord.SelectOption(
                            label=member.display_name,
                            value=str(player_id)
                        )
                    )
        
        # 如果没有可选玩家，添加默认选项
        if not options:
            options = [
                discord.SelectOption(
                    label="无可选玩家",
                    value="none",
                    description="当前没有可管理的玩家"
                )
            ]

        # 创建选择菜单，放在第一行
        self.select = discord.ui.Select(
            placeholder="选择玩家",
            options=options[:5],  # 限制选项数量为5
        )
        self.select.callback = self.select_callback
        self.add_item(self.select)
        
        # 添加按钮，放在第二行
        set_hp_button = discord.ui.Button(
            label="设置血量",
            style=ButtonStyle.primary,
            row=1
        )
        set_hp_button.callback = self.set_hp
        self.add_item(set_hp_button)
        
        damage_button = discord.ui.Button(
            label="扣除血量",
            style=ButtonStyle.danger,
        )
        damage_button.callback = self.damage_hp
        self.add_item(damage_button)
        
        heal_button = discord.ui.Button(
            label="恢复血量",
            style=ButtonStyle.success,
        )
        heal_button.callback = self.heal_hp
        self.add_item(heal_button)

    async def select_callback(self, interaction: discord.Interaction):
        """选择玩家的回调函数"""
        if self.select.values[0] != "none":
            self.selected_player = int(self.select.values[0])
            await interaction.response.send_message(
                f"已选择玩家：<@{self.selected_player}>",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "当前没有可选择的玩家",
                ephemeral=True
            )

    async def set_hp(self, interaction: discord.Interaction):
        """设置血量"""
        if not self.selected_player:
            await interaction.response.send_message(
                "请先选择一个玩家!",
                ephemeral=True
            )
            return
        modal = HPSetModal(self.session, self.selected_player)
        await interaction.response.send_modal(modal)

    async def damage_hp(self, interaction: discord.Interaction):
        """扣除血量"""
        if not self.selected_player:
            await interaction.response.send_message(
                "请先选择一个玩家!",
                ephemeral=True
            )
            return
        modal = HPModifyModal(self.session, "damage", self.selected_player)
        await interaction.response.send_modal(modal)

    async def heal_hp(self, interaction: discord.Interaction):
        """恢复血量"""
        if not self.selected_player:
            await interaction.response.send_message(
                "请先选择一个玩家!",
                ephemeral=True
            )
            return
        modal = HPModifyModal(self.session, "heal", self.selected_player)
        await interaction.response.send_modal(modal)
class HPSetModal(discord.ui.Modal):
    def __init__(self, session: TRPGSession, target_id: int):
        super().__init__(title="设置血量")
        self.session = session
        self.target_id = target_id
        self.value = discord.ui.TextInput(label="血量值")
        self.add_item(self.value)
class HPModifyModal(discord.ui.Modal):
    def __init__(self, session: TRPGSession, action: str, target_id: int):
        super().__init__(title=f"{'扣除' if action == 'damage' else '恢复'}血量")
        self.session = session
        self.action = action
        self.target_id = target_id
        self.value = discord.ui.TextInput(label="数值")
        self.add_item(self.value)
class PlayerManageView(BaseTRPGView):
    def __init__(self, session: TRPGSession):
        super().__init__(session, session.host_id)
        self.session = session
        self.selected = None
        
        # 创建玩家选择下拉菜单
        options = []
        guild = bot.get_channel(session.channel_id).guild
        for player_id in session.players:
            # if player_id != session.host_id:  # 排除主持人
                member = guild.get_member(player_id)
                if member:
                    options.append(
                        discord.SelectOption(
                            label=member.display_name,
                            value=str(player_id)
                        )
                    )

        # 如果没有可选玩家，添加默认选项
        if not options:
            options = [
                discord.SelectOption(
                    label="无可选玩家",
                    value="none",
                    description="当前没有可管理的玩家"
                )
            ]

        # 创建选择菜单，放在第一行
        self.select = discord.ui.Select(
            placeholder="选择玩家",
            options=options[:5],  # 限制选项数量为5
            # row=0  # 放在第一行
        )
        self.select.callback = self.select_callback
        self.add_item(self.select)
        
        # 添加按钮，放在第二行
        kick_button = discord.ui.Button(
            label="踢出玩家",
            style=ButtonStyle.danger,
            # row=1  # 放在第二行
        )
        kick_button.callback = self.kick_player
        self.add_item(kick_button)
        
        list_button = discord.ui.Button(
            label="查看玩家列表",
            style=ButtonStyle.primary,
            # row=1  # 放在第二行
        )
        list_button.callback = self.list_players
        self.add_item(list_button)
        
        ban_button = discord.ui.Button(
            label="永久拒绝列表",
            style=ButtonStyle.secondary,
            # row=1  # 放在第二行
        )
        ban_button.callback = self.ban_list
        self.add_item(ban_button)

    async def select_callback(self, interaction: discord.Interaction):
        """选择玩家的回调函数"""
        if self.select.values[0] != "none":
            self.selected = int(self.select.values[0])
            await interaction.response.send_message(
                f"已选择玩家：<@{self.selected}>",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "当前没有可选择的玩家",
                ephemeral=True
            )

    async def kick_player(self, interaction: discord.Interaction):
        if interaction.user.id != self.session.host_id:
            await interaction.response.send_message(
                "只有主持人才能踢出玩家!",
                ephemeral=True
            )
            return

        if not self.selected:
            await interaction.response.send_message(
                "请先选择要踢出的玩家!",
                ephemeral=True
            )
            return

        if self.selected == self.session.host_id:
            await interaction.response.send_message(
                "不能踢出主持人!",
                ephemeral=True
            )
            return

        if self.selected in self.session.players:
            # 获取要踢出的玩家对象
            guild = interaction.guild
            member = guild.get_member(self.selected)
            
            # 移除玩家相关数据
            self.session.players.remove(self.selected)
            if self.selected in self.session.player_points:
                del self.session.player_points[self.selected]
            if self.selected in self.session.personal_memos:
                del self.session.personal_memos[self.selected]
            if self.selected in self.session.host_player_memos:
                del self.session.host_player_memos[self.selected]
            
            # 移除频道权限
            channel = bot.get_channel(self.session.channel_id)
            await channel.set_permissions(member, overwrite=None)
            
            # 重新加载视图
            await interaction.response.edit_message(
                content="玩家管理面板",
                view=PlayerManageView(self.session)
            )
            
            # 发送踢出通知
            await interaction.followup.send(
                f"已将 <@{self.selected}> 踢出跑团!",
                ephemeral=False
            )
        else:
            await interaction.response.send_message(
                "该玩家已不在跑团中!",
                ephemeral=True
            )

    async def list_players(self, interaction: discord.Interaction):
        guild = interaction.guild
        player_list = []
        for player_id in self.session.players:
            member = guild.get_member(player_id)
            if member:
                role = "主持人" if player_id == self.session.host_id else "玩家"
                player_list.append(f"- {member.mention} ({role})")

        if player_list:
            await interaction.response.send_message(
                "当前玩家列表:\n" + "\n".join(player_list),
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "当前没有玩家!",
                ephemeral=True
            )

    async def ban_list(self, interaction: discord.Interaction):
        if interaction.user.id != self.session.host_id:
            await interaction.response.send_message(
                "只有主持人才能查看此列表!",
                ephemeral=True
            )
            return

        guild = interaction.guild
        ban_list = []
        for player_id in self.session.ban_players:
            member = guild.get_member(player_id)
            if member:
                ban_list.append(f"- {member.mention}")

        if ban_list:
            await interaction.response.send_message(
                "永久拒绝列表:\n" + "\n".join(ban_list),
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "永久拒绝列表为空",
                ephemeral=True
            )
            
class SelectTargetView(BaseTRPGView):
    def __init__(self, session: TRPGSession, user_id: int):
        super().__init__(session, session.host_id)
        self.session = session
        self.selected = None
        self.user_id = user_id
        # 创建玩家选择下拉菜单
        player_options = []

        # 如果是主持人，添加所有玩家选项
        if user_id == session.host_id:
            guild = bot.get_channel(session.channel_id).guild
            for player_id in session.players:
                # if player_id != session.host_id:  # 排除主持人自己
                    member = guild.get_member(player_id)
                    if member:
                        player_options.append(
                            discord.SelectOption(
                                label=member.display_name,
                                value=str(player_id)
                            )
                        )
        else:
            # 如果是普通玩家，只能选择自己
            player_options.append(
                discord.SelectOption(
                    label="自己",
                    value="self",
                    description="对自己进行操作"
                )
            )

        # 如果没有可选玩家，添加默认选项
        if not player_options:
            player_options = [
                discord.SelectOption(
                    label="无可选玩家",
                    value="none",
                    description="当前没有可管理的玩家"
                )
            ]
        # 创建选择菜单
        self.select = discord.ui.Select(
            placeholder="选择目标",
            options=player_options[:5],  # 限制最大选项数为5
        )
        self.select.placeholder = "选择目标"
        # self.select.callback = self.on_select
        self.select.callback = self.select_callback
        self.add_item(self.select)

        # 添加确认按钮
        confirm_button = discord.ui.Button(
            label="确认分配点数",
            style=ButtonStyle.primary,
            row=1
        )
        confirm_button.callback = self.confirm_points
        self.add_item(confirm_button)
    
    async def select_callback(self, interaction: discord.Interaction):
        """选择回调处理"""
        if not self.select.values:
            await interaction.response.send_message("请选择一个目标!", ephemeral=True)
            return

        selected_value = self.select.values[0]
        if selected_value == "self":
            self.selected = interaction.user.id
        elif selected_value == "none":
            self.selected = None
        else:
            self.selected = int(selected_value)

        # 必须发送响应，否则交互会挂起
        await interaction.response.send_message(
            f"已选择目标：<@{self.selected}>" if self.selected else "无有效目标",
            ephemeral=True
        )


    async def confirm_points(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        """确认分配点数"""
        if not self.selected:
            await interaction.followup.send(
                "请先选择一个目标!",
                ephemeral=True
            )
            return

        # 弹出点数分配对话框
        point_options = []
        for point_name in self.session.points_template.keys():
            point_options.append(
                discord.SelectOption(
                    label=point_name,
                    value=point_name
                )
            )

        if not point_options:
            await interaction.followup.send(
                "当前没有可用的点数项目!",
                ephemeral=True
            )
            return

        view = PointsAssignView(self.session, self.selected, point_options)
        await interaction.followup.send(
            content=f"请为 <@{self.selected}> 分配点数：",
            view=view
        )
class PointsAssignView(BaseTRPGView):
    def __init__(self, session: TRPGSession, target_id: int, point_options: list):
        super().__init__(session, session.host_id)
        self.point_select = discord.ui.Select(
            placeholder="选择点数项目",
            options=point_options,
        )
        self.target_id = target_id
        self.point_select.callback = self.point_select_callback  # 确保回调函数绑定
        self.add_item(self.point_select)

        # 分配点数按钮
        assign_button = discord.ui.Button(
            label="设置点数值",
            style=discord.ButtonStyle.primary,
        )
        assign_button.callback = self.assign_button_points  # 确保回调函数绑定
        self.add_item(assign_button)
        
    async def point_select_callback(self, interaction: discord.Interaction):
        if not self.point_select.values:
            await interaction.response.send_message("请选择一个目标!", ephemeral=True)
            return

        selected_value = self.point_select.values[0]
        await interaction.response.send_message(f"已选择目标：{selected_value}", ephemeral=True)


    async def assign_button_points(self, interaction: discord.Interaction):
        """点数值输入对话框"""
        if not self.point_select.values:
            await interaction.response.send_message(
                "请先选择点数项目!",
                ephemeral=True
            )
            return

        point_name = self.point_select.values[0]
        modal = PointValueModal(self.session, self.target_id, point_name)
        await interaction.response.send_modal(modal)
class PointValueModal(discord.ui.Modal):
    def __init__(self, session: TRPGSession, target_id: int, point_name: str):
        super().__init__(title=f"设置 {point_name} 的值")
        self.session = session
        self.target_id = target_id
        self.point_name = point_name
        self.value = discord.ui.TextInput(
            label="点数值",
            placeholder="请输入数值",
            min_length=1,
            max_length=4
        )
        self.add_item(self.value)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            value = int(self.value.value)
            if value < 0:
                await interaction.response.send_message("点数不能为负数!", ephemeral=True)
                return

            # 确保目标玩家的点数字典存在
            if self.target_id not in self.session.player_points:
                self.session.player_points[self.target_id] = {}

            # 更新点数
            self.session.player_points[self.target_id][self.point_name] = value

            await interaction.response.send_message(
                f"已为 <@{self.target_id}> 设置 {self.point_name}: {value}",
                ephemeral=True
            )
        except ValueError:
            await interaction.response.send_message(
                "请输入有效的数字!",
                ephemeral=True
            )
class MemoView(BaseTRPGView):
    """备忘录视图"""
    @discord.ui.button(label="写备忘", style=ButtonStyle.primary)
    async def write_memo(self, interaction: Interaction, button: Button):
        modal = MemoWriteModal(self.session)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="读备忘", style=ButtonStyle.primary)
    async def read_memo(self, interaction: Interaction, button: Button):
        memos = self.session.personal_memos.get(self.user_id, [])
        memo_list = "\n".join([f"{i+1}. {memo}" for i, memo in enumerate(memos)])
        await interaction.response.send_message(f"===== 个人备忘录 =====\n{memo_list}", ephemeral=True)

class RollView(BaseTRPGView):
    """掷骰视图"""
    @discord.ui.button(label="D20", style=ButtonStyle.primary)
    async def roll_d20(self, interaction: Interaction, button: Button):
        result = random.randint(1, 20)
        await interaction.response.send_message(f"{interaction.user.mention} D20: {result}")

    @discord.ui.button(label="D100", style=ButtonStyle.primary)
    async def roll_d100(self, interaction: Interaction, button: Button):
        result = random.randint(1, 100)
        await interaction.response.send_message(f"{interaction.user.mention} D100: {result}")

    @discord.ui.button(label="自定义", style=ButtonStyle.primary)
    async def roll_custom(self, interaction: Interaction, button: Button):
        modal = RollCustomModal()
        await interaction.response.send_modal(modal)

# 添加模态框类

class MemoWriteModal(discord.ui.Modal):
    def __init__(self, session: TRPGSession):
        super().__init__(title="写备忘")
        self.session = session
        self.content = discord.ui.TextInput(label="备忘内容", style=discord.TextStyle.paragraph)
        self.add_item(self.content)

    async def on_submit(self, interaction: Interaction):
        if interaction.user.id not in self.session.personal_memos:
            self.session.personal_memos[interaction.user.id] = []
        self.session.personal_memos[interaction.user.id].append(self.content.value)
        await interaction.response.send_message(f"已记录备忘: {self.content.value}", ephemeral=True)

class RollCustomModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="掷骰")
        self.min_value = discord.ui.TextInput(label="最小值", placeholder="1")
        self.max_value = discord.ui.TextInput(label="最大值", placeholder="100")
        self.add_item(self.min_value)
        self.add_item(self.max_value)

    async def on_submit(self, interaction: Interaction):
        try:
            min_val = int(self.min_value.value)
            max_val = int(self.max_value.value)
            if max_val < min_val:
                max_val, min_val = min_val, max_val
            result = random.randint(min_val, max_val)
            await interaction.response.send_message(
                f"{interaction.user.mention} D{max_val}-{min_val}: {result}"
            )
        except ValueError:
            await interaction.response.send_message("请输入有效的数字!", ephemeral=True)
            
@group.command(name="menu", description="打开TRPG菜单")
async def menuT(interaction: discord.Interaction):
    """打开TRPG主菜单"""
    session = None
    for n,k in bot.trpg_sessions.items():
        if interaction.channel_id == k.channel_id:
            session = k
    if session is None:
        await interaction.response.send_message("未发现加入的跑团!", ephemeral=True)
        return

    await interaction.response.send_message(
        "TRPG 主菜单",
        view=MainMenuView(session, interaction.user.id),
        ephemeral=True
    )
# @bot.event
# async def on_error(event_method, *args, **kwargs):
#     print(f"错误出现在 {event_method}：{args}, {kwargs}")
config = {}
if not os.path.exists('config_discord.json'):
    with open('config_discord.json', 'w') as f:
        json.dump({}, f)



async def bed_not_comfortable(id):
    with open('config_discord.json', 'r+') as f:
        config = json.load(f)
    config_guild = config.get(str(id))
    if config_guild is None:
        return
    # print(f"guild:{id} + {config_guild} time:{time.localtime().tm_hour}:{time.localtime().tm_min}")
    if time.localtime().tm_hour == int(config_guild["hour_to_wake_up"]) and time.localtime().tm_min == int(config_guild["minute_to_wake_up"]):
        if config_guild.get("pass",False) is False:
            voice_channel = bot.get_channel(config_guild["channel_id"])
            if voice_channel and isinstance(voice_channel, discord.VoiceChannel):
                if voice_channel.members == []:
                    return
                
                vc = await voice_channel.connect()
                for file in config_guild["audio_files"]:
                    vc.play(discord.FFmpegPCMAudio(file))
                    while vc.is_playing():
                        await asyncio.sleep(1)
                await vc.disconnect()

async def check_bed_time():
    await bot.wait_until_ready()
    while not bot.is_closed():
        # print("check!")
        for guild in bot.guilds:
            # print(f"checking:{guild.id}")
            if time.localtime().tm_hour == 12:
                config[str(guild.id)]["pass"] = False
            await bed_not_comfortable(guild.id)
            
        await asyncio.sleep(30)  # 每1分钟检查一次

async def check_inactive_channels():
    """检查并关闭不活跃的问答频道"""
    await bot.wait_until_ready()
    while not bot.is_closed():
        for channel_id, data in list(bot.mod_channels.items()):
            channel = bot.get_channel(channel_id)
            if channel:
                async for message in channel.history(limit=1):
                    if (discord.utils.utcnow() - message.created_at).seconds > 1800:  # 30分钟
                        await channel.delete()
                        del bot.mod_channels[channel_id]
                        break
        await asyncio.sleep(300)  # 每5分钟检查一次

bed = app_commands.Group(name="bed", description="神秘闹钟")

@bed.command(name="setbedtime", description="设置闹钟时间和音频")
@app_commands.describe(
    time_to_wake_up="闹钟时间(HH:MM 格式)",
    channel_id="频道ID",
    audio_files='音频文件列表(机器人本地, ","分割)'
)
async def setbedtime(interaction: discord.Interaction, time_to_wake_up: str, channel_id: discord.VoiceChannel, audio_files: str):
    """设置闹钟时间和音频"""
    guild_id = interaction.guild_id
    if guild_id is None:
        await interaction.response.send_message("此命令只能在服务器中使用!", ephemeral=True)
        return
    if interaction.user.guild_permissions.administrator is False:
        await interaction.response.send_message("你没有权限使用此命令!", ephemeral=True)
        return

    # 验证时间格式
    try:
        hour, minute = map(int, time_to_wake_up.split(":"))
        if not (0 <= hour < 24 and 0 <= minute < 60):
            raise ValueError
    except ValueError:
        await interaction.response.send_message("时间格式无效，请使用 HH:MM 格式!", ephemeral=True)
        return

    # 解析音频文件列表
    audio_files_list = [file.strip() for file in audio_files.split(",")]
    for file in audio_files_list:
        if not os.path.exists(file):
            await interaction.response.send_message(f"音频文件 {file} 不存在!", ephemeral=True)
            return

    # 更新配置
    config[str(guild_id)] = {
        "hour_to_wake_up": hour,
        "minute_to_wake_up": minute,
        "channel_id": channel_id.id,
        "audio_files": audio_files_list,
        "pass": False
    }

    # 保存到文件
    with open('config_discord.json', 'w') as f:
        save_c = json.dumps(config, indent=4)
        f.write(save_c)
        print(save_c)

    await interaction.response.send_message(
        f"闹钟已设置:\n时间: {time_to_wake_up}\n频道: {channel_id.mention}\n音频文件: {', '.join(audio_files_list)}",
    )

@bed.command(name="clearbedtime", description="取消本频道闹钟")
async def clear_all_bedtime(interaction: discord.Interaction):
    """取消闹钟"""
    guild_id = interaction.guild_id
    if guild_id is None:
        await interaction.response.send_message("此命令只能在服务器中使用!", ephemeral=True)
        return
    if interaction.user.guild_permissions.administrator is False:
        await interaction.response.send_message("你没有权限使用此命令!", ephemeral=True)
        return
    # 更新配置
    config[str(guild_id)] = {}

    # 保存到文件
    with open('config_discord.json', 'w') as f:
        json.dump(config, f, indent=4)

    await interaction.response.send_message("闹钟已清除")

@bed.command(name="passbedtime", description="暂时跳过本频道闹钟(12:00点重置)")
async def pass_bedtime(interaction: discord.Interaction):
    """跳过闹钟"""
    guild_id = interaction.guild_id
    if guild_id is None:
        await interaction.response.send_message("此命令只能在服务器中使用!", ephemeral=True)
        return
    # 更新配置
    try:
        config[str(guild_id)]["pass"] = not config[str(guild_id)].get("pass", False)
    except KeyError:
        await interaction.response.send_message("未设置闹钟!", ephemeral=True)
        return

    # 保存到文件
    with open('config_discord.json', 'w') as f:
        json.dump(config, f, indent=4)

    await interaction.response.send_message("闹钟已跳过")

@bed.command(name="timeforbed", description="直接触发闹钟(管理限定)")
async def timeforbed(interaction: discord.Interaction):
    """直接触发闹钟"""
    guild_id = interaction.guild_id
    if guild_id is None:
        await interaction.response.send_message("此命令只能在服务器中使用!", ephemeral=True)
        return
    if interaction.user.guild_permissions.administrator is False:
        await interaction.response.send_message("你没有权限使用此命令!", ephemeral=True)
        return
    await interaction.response.defer()
    with open('config_discord.json', 'r+') as f:
        config = json.load(f)
    config_guild: dict = config.get(str(guild_id))
    if True:
        if config_guild.get("audio_files") is None:
            await interaction.followup.send("未发现音频:(", ephemeral=True)
            return
        if config_guild.get("channel_id") is None:
            await interaction.followup.send("未设置频道:(", ephemeral=True)
            return
        voice_channel = bot.get_channel(config_guild["channel_id"])
        await interaction.followup.send(f"起床了!!!! ---来着管理:{interaction.user.display_name}")

        if voice_channel and isinstance(voice_channel, discord.VoiceChannel):
            vc = await voice_channel.connect()
            for file in config_guild["audio_files"]:
                vc.play(discord.FFmpegPCMAudio(file))
                while vc.is_playing():
                    await asyncio.sleep(1)
            await interaction.followup.send("播放完成", ephemeral=True)

            await vc.disconnect()

@bot.event
async def on_message(message):
    # 忽略机器人自己的消息
    if message.author.bot:
        return
        
    # 检查是否为mod问答频道的消息
    if message.channel.id in bot.mod_channels:
        channel_data = bot.mod_channels[message.channel.id]
        
        # 检查发送者是否是频道创建者
        if message.author.id != channel_data["user_id"]:
            return
            
        async with message.channel.typing():
            try:
                # 添加新消息到上下文
                channel_data["context"].append({
                    "role": "user",
                    "content": message.content
                })
                print(f"Received message in mod channel {message.channel.id}: {message.content}")
                # 调用API获取回复
                response = ai.chat.completions.create(
                    model="qwen-plus-latest",
                    messages=channel_data["context"],
                    
                )
                
                reply = response.choices[0].message.content
                print(f"Reply from AI: {reply}")
                if not reply:
                    reply = "抱歉，我无法处理您的请求。"
                channel_data["context"].pop(0)  # 移除最旧的消息以保持上下文长度
                if "<__I_THINK_I_CAN_END_THIS__>" in reply:
                    reply = reply.replace("<__I_THINK_I_CAN_END_THIS__>", "对话结束")
                    # 结束问答频道
                    await message.channel.send("问答结束，频道5秒后将被删除。")
                    await asyncio.sleep(5)
                    await message.channel.delete()
                    del bot.mod_channels[message.channel.id]
                    return
                if "<__I_THINK_I_CAN_END_THIS_WAIT_FOR_10S__>" in reply:
                    reply = reply.replace("<__I_THINK_I_CAN_END_THIS_WAIT_FOR_10S__>", "对话结束")
                    await message.channel.send(reply)
                    # 结束问答频道
                    await message.channel.send("问答结束，频道10秒后将被删除。")
                    await asyncio.sleep(10)
                    await message.channel.delete()
                    del bot.mod_channels[message.channel.id]
                    return
                # 保存回复到上下文
                channel_data["context"].append({
                    "role": "assistant",
                    "content": reply
                })
                
                # 发送回复
                await message.channel.send(reply)
                
            except Exception as e:
                await message.channel.send(f"抱歉，处理您的问题时出现错误：{str(e)}")


bot.tree.add_command(bed)

# 在 bot 启动时新建线程执行
bot.tree.add_command(group)
bot.run(my_bot_token)