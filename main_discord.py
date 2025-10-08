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
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_API_BASE = os.getenv("OPENAI_API_BASE")  # 添加自定义API基础URL
ai = openai.OpenAI(api_key=OPENAI_API_KEY,base_url=OPENAI_API_BASE)  # 使用自定义API基础URL
from pixivpy3 import ByPassSniApi,AppPixivAPI
import pixiv_auth
import traceback

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
# aapi.require_appapi_hosts()
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
        tags="Tags to filter images (e.g., '萝莉 少女|白丝 黑丝')",
        public="show it to another default true",
        api="API to use (0: lolicon, 1: anosu,2: both)"
    )
@app_commands.choices(r18=[
        app_commands.Choice(name="No (Non-R18)", value="no"),
        app_commands.Choice(name="Yes (R18)", value="yes"),
        app_commands.Choice(name="Yes (Include R18-G)", value="R18-G"),
        app_commands.Choice(name="Random (Mixed)", value="random")
    ],api = [
        app_commands.Choice(name="lolicon", value=0),
        app_commands.Choice(name="anosu", value=1),
        app_commands.Choice(name="both", value=2)
    ])
async def setu(interaction: discord.Interaction, r18: str, num: int = 1, tags: str = None,public:bool = True,api:int = 2):
    allowed, wait_time = bot.check_rate_limit(interaction.user.id)
    if not allowed:
            await interaction.response.send_message(
                f"人要节制点 注意身体，请等待 {wait_time} 秒后再试。",
            )
            return
    public = not public
        
    await interaction.response.defer(ephemeral=public,thinking=True)  # 延迟响应
    r18_param = {
            "no": 0,
            "yes": 1,
            "R18-G": 2, #random in api1
            "random": 3
        }.get(r18, 3)
    if interaction.channel.type != discord.ChannelType.private or type(interaction.channel) != discord.DMChannel:
        if not interaction.channel.is_nsfw():
                if r18_param == 1:
                        await interaction.followup.send("不准在非r18里色色!",ephemeral=True)
                        return
                elif r18_param == 2:
                    r18_param = 0
    params_1 = {
        "r18": max(0, min(r18_param, 2)),  # 限制 r18 在 0 到 2 之间
        "num": max(1, min(num, 20)),  # 限制 num 在 1 到 20 之间
    }
    params_2:Dict[str,Any] = {
        "num": max(1, min(num, 15)),  # 限制 num 在 1 到 15 之间
        "r18": r18_param,
    } 
    if tags:
        # 将用户输入的 tags 按 '|' 分隔，适配 api2 的多关键词功能
        params_1["tag"] = tags  # 适用于 api1
        params_2["keyword"] = tags  # 适用于 pixiv
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
                if r18_param == 3:
                    UnPar = aapi.illust_ranking(mode=random.choice(RANDOM_MODE))
                elif r18_param == 1:
                    UnPar = aapi.illust_ranking(mode=random.choice(R18_MODE))
                elif r18_param == 2:
                    UnPar = aapi.illust_ranking(mode="week_r18g")
                else:
                    UnPar = aapi.illust_ranking(mode=random.choice(NORMAL_MODE))
            with open("log.txt", "a+", encoding="utf-8") as f:
                    f.write(f"Debug:P0:UnPar:{UnPar}\n")
            if not UnPar or "illusts" not in UnPar:
                    if "OAuth" in UnPar["error"]["message"]:
                        aapi.auth(refresh_token=pixiv_refresh_token)
                        if tags:
                            UnPar = aapi.search_illust(params_2["keyword"],sort=random.choice(["date_desc", "date_asc", "popular_desc"]))
                        else:
                            if r18_param == 3:
                                UnPar = aapi.illust_ranking(mode=random.choice(RANDOM_MODE))
                            elif r18_param == 1:
                                UnPar = aapi.illust_ranking(mode=random.choice(R18_MODE))
                            elif r18_param == 2:
                                UnPar = aapi.illust_ranking(mode="week_r18g")
                            else:
                                UnPar = aapi.illust_ranking(mode=random.choice(NORMAL_MODE))
            UnPar["illusts"] = [i for i in UnPar["illusts"] if (i.x_restrict == r18_param or (i.x_restrict == 1 and r18_param == 2) or r18_param == 3) and not i.is_manga]  
            with open("log.txt", "a+", encoding="utf-8") as f:
                    f.write(f"Debug:P0.5:UnPar:{UnPar}\n")
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
                print(f"Debug:NextParm:{NextParm}")
                if tags:
                    UnPar = aapi.search_illust(**NextParm)
                else:
                    UnPar = aapi.illust_ranking(**NextParm)
                with open("log.txt", "a+", encoding="utf-8") as f:
                    f.write(f"Debug:P1:UnPar:{UnPar}\n")
                if not UnPar or "illusts" not in UnPar:
                    if "OAuth" in UnPar["message"]:
                        aapi.auth(refresh_token=pixiv_refresh_token)
                        
                UnPar["illusts"] = [i for i in UnPar["illusts"] if (i.x_restrict == r18_param or (i.x_restrict == 1 and r18_param == 2) or r18_param == 3) and not i.is_manga] 
                with open("log.txt", "a+", encoding="utf-8") as f:
                    f.write(f"Debug:P2:UnPar:{UnPar}\n")
                
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
            with open("log.txt", "a+", encoding="utf-8") as f:
                    f.write(f"Debug:final:image_data:{image_data}\n")
            
            # 处理图片数据
            if not image_data:
                await interaction.followup.send("没有找到符合条件的图片", ephemeral=True)
                return

            print(f"image_data: {image_data}")
            random.shuffle(image_data)
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
                    await interaction.followup.send(f"正在下载图片: {image_url} 重试次数: {retry_count + 1}",ephemeral=True)
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
            Etraceback: str = traceback.format_exc()
            embed.add_field(name="Traceback:", value=Etraceback, inline=False)
            await interaction.followup.send(embed=embed)
    
@bot.tree.command(name="thanks", description="Send a thanks(?)")
async def help(interaction: discord.Interaction):
    await interaction.followup.send("""1.框架:discord.py
2.使用api:"https://api.lolicon.app/setu/v2"
3.gui我实在不想写了所以感谢copilot""",ephemeral=True)


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
bot.run(my_bot_token)