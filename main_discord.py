import asyncio
import time
from typing import Dict, List, Optional, Set
from PIL import Image
import uuid
import aiofiles
import aiohttp
import discord
from discord import Button, ButtonStyle, Interaction, Member, NSFWLevel, app_commands
from discord.ui import Button, View
import requests
import os
import random
MAX_DISCORD_FILE_SIZE = 8 * 1024 * 1024  # 8MB
# 配置
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()
my_bot_token = os.getenv("DISCORD_BOT_TOKEN")
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

    async def setup_hook(self):
        # 同步斜杠命令
        await self.tree.sync()
        print("Commands synced!")

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
    params_2 = {
        "num": max(1, min(num, 15)),  # 限制 num 在 1 到 15 之间
        "r18": r18_param,
    }
    if tags:
        # 将用户输入的 tags 按 '|' 分隔，适配 api2 的多关键词功能
        params_1["tag"] = tags  # 适用于 api1
        params_2["keyword"] = "|".join(tags)  # 适用于 api2
    api_url_1 = "https://api.lolicon.app/setu/v2"
    

    # API 2: https://image.anosu.top/pixiv/json
    api_url_2 = "https://image.anosu.top/pixiv/json"
    if not public:
            if num >4:
                await interaction.followup.send("在公开情况下数量超过4 可能刷屏 已拒绝执行;(",ephemeral=True)
                return
        
    
    try:
        image_data = []
        if api == 0:
            # 只使用 API 1
            response_api_1 = requests.post(api_url_1, json=params_1)
            response_api_1.raise_for_status()
            image_data = response_api_1.json().get("data", [])
        elif api == 1:
            print(f"API 2 {params_2}")
            
            # 只使用 API 2
            response_api_2 = requests.get(api_url_2, params=params_2)
            response_api_2.raise_for_status()
            image_data = response_api_2.json()
        elif api == 2:
            # 优先使用 API 1
            try:
                response_api_1 = requests.post(api_url_1, json=params_1)
                response_api_1.raise_for_status()
                image_data = response_api_1.json().get("data", [])
            except requests.exceptions.RequestException as e:
                print(f"API 1 请求失败: {e}")
            
            # 如果 API 1 没有找到图片，尝试使用 API 2
            if not image_data:
                print("API 1 没有找到符合条件的图片，尝试使用 API 2")
                response_api_2 = requests.get(api_url_2, params=params_2)
                print(f"API 2 {params_2}")
                response_api_2.raise_for_status()
                image_data = response_api_2.json()

        # 处理图片数据
        if not image_data:
            await interaction.followup.send("没有找到符合条件的图片", ephemeral=True)
            return
        # print(f"image_data: {image_data}")
        for image in image_data:
            # 优先从 im2 获取 original URL
            im2 = image.get("urls", {})
            image_url = im2.get("original")

            # 如果 original URL 不存在，则尝试从 image 的 url 字段获取
            if not image_url or not isinstance(image_url, str):
                # print(f"无效的图片 URL: {image_url}")
                image_url = image.get("url")
                # print(f"下载图片2: {image_url}")

            # 如果仍然无效，跳过该图片
            if not image_url or not isinstance(image_url, str):
                print(f"无效的图片 URL，跳过: {image_url}")
                continue

            temp_filename = f"temp_{uuid.uuid4()}.jpg"
            # print(f"下载图片: {image_url}")

            # 下载图片
            if not await download_image(image_url, temp_filename):
                # 如果下载失败，尝试使用 num=1 再次请求
                print(f"图片下载失败，尝试重新请求: {image_url}")
                params_1["num"] = 1
                params_2["num"] = 1
                retry_data = []

                if api in [0, 2]:
                    try:
                        response_api_1 = requests.post(api_url_1, json=params_1)
                        response_api_1.raise_for_status()
                        retry_data = response_api_1.json().get("data", [])
                    except Exception as e:
                        print(f"API 1 重试失败: {e}")

                if api in [1, 2] and not retry_data:
                    try:
                        response_api_2 = requests.get(api_url_2, params=params_2)
                        response_api_2.raise_for_status()
                        retry_data = response_api_2.json()
                    except Exception as e:
                        print(f"API 2 重试失败: {e}")

                if retry_data:
                    image = retry_data[0]
                    image_url = image.get("url")
                    if not image_url or not isinstance(image_url, str):
                        print(f"无效的图片 URL: {image_url}")
                        continue

                    if not await download_image(image_url, temp_filename):
                        await interaction.followup.send(f"图片下载失败: {image_url}", ephemeral=True)
                        continue

            try:
                # 检查文件大小，超限则压缩
                if os.path.getsize(temp_filename) > MAX_DISCORD_FILE_SIZE:
                    compressed_filename = await compress_image_to_limit(temp_filename, MAX_DISCORD_FILE_SIZE)
                    if not compressed_filename:
                        await interaction.followup.send("图片过大且压缩失败", ephemeral=True)
                        os.remove(temp_filename)
                        continue
                    temp_filename = compressed_filename  # 使用压缩后的文件名

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
                embed.add_field(name="URL", value=image_url, inline=False)
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
                embed.add_field(name="作者", value=a, inline=True)
                embed.add_field(name="PID", value=image.get("pid", "未知"), inline=True)
                embed.add_field(name="标签", value=", ".join(image.get("tags", [])), inline=False)
                embed.add_field(name="URL", value=image_url, inline=False)
                await interaction.followup.send(embed=embed, ephemeral=True)
                try:
                    os.remove(temp_filename)
                except Exception as remove_error:
                    print(f"删除文件失败：{remove_error}")
    except requests.exceptions.RequestException as e:
        embed = discord.Embed(title=f"api请求失败: {str(e)}")
        await interaction.followup.send(embed=embed, ephemeral=True)
    except Exception as e:
        embed = discord.Embed(title=f"Exception as e: {str(e)}")
        await interaction.followup.send(embed=embed, ephemeral=True)

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
        session.points_template[point_name] = 0  # 初始值为0
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
bot.tree.add_command(group)
bot.run(my_bot_token)