import asyncio
import time
from typing import Dict, List, Optional, Set
from PIL import Image
import uuid
import aiofiles
import aiohttp
import discord
from discord import NSFWLevel, app_commands
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
        public="show it to another default true"
    )
@app_commands.choices(r18=[
        app_commands.Choice(name="No (Non-R18)", value="no"),
        app_commands.Choice(name="Yes (R18)", value="yes"),
        app_commands.Choice(name="Random (Mixed)", value="random")
    ])
async def setu(interaction: discord.Interaction, r18: str, num: int = 1, tags0: str = None,tags1: str = None,tags2: str = None
                ,tags3: str = None,tags4: str = None,public:bool = True):
    allowed, wait_time = bot.check_rate_limit(interaction.user.id)
    if not allowed:
            await interaction.response.send_message(
                f"您的使用频率过高，请等待 {wait_time} 秒后再试。",
                ephemeral=True
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
            # 将用户输入的 tags 按 '|' 分组，每组按空格分割为二维数组
            params_1["tag"] = tags
    if tags0:
            params_2["keyword"] = tags0
    elif tags1:
            params_2["keyword"] = tags1
    elif tags2:
            params_2["keyword"] = tags2
    elif tags3:
            params_2["keyword"] = tags3
    elif tags4:
            params_2["keyword"] = tags4
    
    api_url_1 = "https://api.lolicon.app/setu/v2"
    

    # API 2: https://image.anosu.top/pixiv/json
    api_url_2 = "https://image.anosu.top/pixiv/json"
    if not public:
            if num >4:
                await interaction.followup.send("在公开情况下数量超过4 可能刷屏 已拒绝执行;(",ephemeral=True)
                return
        
    

    try:
        # 请求 API 1
        response_api_1 = requests.post(api_url_1, json=params_1)
        response_api_1.raise_for_status()
        image_data_1 = response_api_1.json()
        print(f"API 1 响应: {image_data_1}")

        # 请求 API 2
        response_api_2 = requests.post(api_url_2, json=params_2)
        response_api_2.raise_for_status()
        image_data_2 = response_api_2.json()
        print(f"API 2 响应: {image_data_2}")

        # 合并两个 API 的数据
        combined_data = []
        seen_pids = set()

        if "data" in image_data_1 and len(image_data_1["data"]) > 0:
            for img in image_data_1["data"]:
                pid = str(img.get("pid") or img.get("pid", ""))
                if pid and pid not in seen_pids:
                    combined_data.append(img)
                    seen_pids.add(pid)

        if isinstance(image_data_2, list) and len(image_data_2) > 0:
            for img in image_data_2:
                pid = str(img.get("pid") or img.get("pid", ""))
                if pid and pid not in seen_pids:
                    combined_data.append(img)
                    seen_pids.add(pid)

        # 处理图片数据
        for image in combined_data:
            image_url = image.get("url") or image["urls"]["original"]  # 根据 API 数据结构选择 URL
            temp_filename = f"temp_{uuid.uuid4()}.jpg"

            # 下载图片
            if await download_image(image_url, temp_filename):
                try:
                    # 检查文件大小，超限则压缩
                    if os.path.getsize(temp_filename) > MAX_DISCORD_FILE_SIZE:
                        # 调用 compress_image_to_limit 并确保返回值是字符串路径
                        compressed_filename = await compress_image_to_limit( temp_filename, MAX_DISCORD_FILE_SIZE)
                        if not compressed_filename:
                            await interaction.followup.send("图片过大且压缩失败", ephemeral=True)
                            os.remove(temp_filename)
                            continue
                        temp_filename = compressed_filename  # 使用压缩后的文件名

                    # 上传图片
                    file = discord.File(temp_filename)
                    embed = discord.Embed(title=f"Pixiv Image")
                    embed.add_field(name="作者", value=image.get("author", "未知"), inline=True)
                    embed.add_field(name="PID", value=image.get("pid", "未知"), inline=True)
                    embed.add_field(name="标签", value=", ".join(image.get("tags", [])), inline=False)
                    embed.add_field(name="url:", value=image_url, inline=False)
                    embed.set_image(url=f"attachment://{os.path.basename(temp_filename)}")
                    await interaction.followup.send(file=file, embed=embed, ephemeral=public)
                    os.remove(temp_filename)
                except Exception as e:
                    embed = discord.Embed(title=f"上传图片错误：{str(e)}")
                    embed.add_field(name="作者", value=image.get("author", "未知"), inline=True)
                    embed.add_field(name="PID", value=image.get("pid", "未知"), inline=True)
                    embed.add_field(name="标签", value=", ".join(image.get("tags", [])), inline=False)
                    embed.add_field(name="url:", value=image_url, inline=False)
                    await interaction.followup.send(embed=embed, ephemeral=True)
                    try:
                        os.remove(temp_filename)
                    except Exception as remove_error:
                        print(f"删除文件失败：{remove_error}")
            else:
                await interaction.followup.send(f"下载图片失败: {image_url}", ephemeral=True)
    except requests.exceptions.RequestException as e:
        await interaction.followup.send(f"HTTP 请求错误：{str(e)}", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"发生错误：{str(e)}", ephemeral=True)

@bot.tree.command(name="thanks", description="Send a thanks(?)")
async def help(interaction: discord.Interaction):
    await interaction.followup.send("""1.框架:discord.py\n2.使用api:"https://api.lolicon.app/setu/v2" """,ephemeral=True)

class TRPGSession:
    def __init__(self, host_id: int, channel_id: int,start_channel_id: int):
        self.host_id = host_id
        self.channel_id = channel_id
        self.start_channel_id = start_channel_id  # 记录启动频道
        self.players: Set[int] = {host_id}
        self.points_template: Dict[str, int] = {}  # 点数项目列表
        self.player_points: Dict[int, Dict[str, int]] = {}  # 玩家的点数
        self.personal_memos: Dict[int, List[str]] = {}  # 每个人的个人备忘录
        self.host_player_memos: Dict[int, List[str]] = {}  # 主持人对玩家的备忘录
        self.total_points: int = 0  # 总点数
        self.player_hp: Dict[int, int] = {}  # 玩家血量
        self.max_hp: Dict[int, int] = {}  # 玩家最大血量
        
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
        bot.trpg_sessions[guild_id] = session
        
        await interaction.response.send_message(
            f"跑团已启动!\n"
            f"主持人: {interaction.user.mention}\n"
            f"频道: {channel.mention}", 
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
async def joinT(interaction: discord.Interaction):
    """加入当前跑团"""
    guild_id = interaction.guild_id
    if guild_id not in bot.trpg_sessions:
        await interaction.response.send_message("当前没有进行中的跑团!", ephemeral=True)
        return
    
    session = bot.trpg_sessions[guild_id]
    if interaction.user.id in session.players:
        await interaction.response.send_message("你已经在跑团中了!", ephemeral=True)
        return
    
    # 添加玩家到跑团
    session.players.add(interaction.user.id)
    
    # 给予频道权限
    channel = interaction.guild.get_channel(session.channel_id)
    await channel.set_permissions(interaction.user, read_messages=True,send_messages=True)
    
    await interaction.response.send_message(
        f"{interaction.user.mention} 加入了跑团!", 
        ephemeral=False
    )

# 修改 stopT 命令，添加聊天记录导出功能
@group.command(name="stop", description="结束跑团")
async def stopT(interaction: discord.Interaction):
    """结束跑团并保存聊天记录"""
    guild_id = interaction.guild_id
    if guild_id not in bot.trpg_sessions:
        await interaction.response.send_message("当前没有进行中的跑团!", ephemeral=True)
        return
    
    session = bot.trpg_sessions[guild_id]
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
        del bot.trpg_sessions[guild_id]
        
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
    guild_id = interaction.guild_id
    if guild_id not in bot.trpg_sessions:
        await interaction.response.send_message("当前没有进行中的跑团!", ephemeral=True)
        return
    
    session = bot.trpg_sessions[guild_id]
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
        app_commands.Choice(name="设置玩家点数", value="set_player"),
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
    hp_action: Optional[str] = None
):
    """管理背板点数"""
    guild_id = interaction.guild_id
    if guild_id not in bot.trpg_sessions:
        await interaction.response.send_message("当前没有进行中的跑团!", ephemeral=True)
        return
    
    session = bot.trpg_sessions[guild_id]
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
    elif action == "set_player":
        # 主持人设置玩家点数
        if not is_host:
            await interaction.response.send_message("只有主持人才能设置玩家点数!", ephemeral=True)
            return
        if not target or not point_name or value is None:
            await interaction.response.send_message("请指定目标玩家、点数名称和值!", ephemeral=True)
            return
        
        if target.id not in session.player_points:
            session.player_points[target.id] = {}
        
        session.player_points[target.id][point_name] = value
        await interaction.response.send_message(
            f"主持人已设置 {target.mention} 的 {point_name} 为 {value}",
            ephemeral=False  # 设为公开
        )

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
            session.max_hp[target.id] = value
            msg = f"已设置 {target.mention} 的血量为 {value}"

        elif hp_action == "damage":
            # 扣除血量
            if target.id not in session.player_hp:
                await interaction.response.send_message(f"请先设置 {target.mention} 的血量!", ephemeral=True)
                return
            session.player_hp[target.id] = max(0, session.player_hp[target.id] - value)
            msg = f"{target.mention} 受到 {value} 点伤害，当前血量: {session.player_hp[target.id]}/{session.max_hp[target.id]}"

        elif hp_action == "heal":
            # 恢复血量
            if target.id not in session.player_hp:
                await interaction.response.send_message(f"请先设置 {target.mention} 的血量!", ephemeral=True)
                return
            session.player_hp[target.id] = min(session.max_hp[target.id], session.player_hp[target.id] + value)
            msg = f"{target.mention} 恢复 {value} 点血量，当前血量: {session.player_hp[target.id]}/{session.max_hp[target.id]}"
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
            template_info += f"血量: {session.player_hp[user_id]}/{session.max_hp[user_id]}"
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
                        template_info += f"血量: {session.player_hp[player_id]}/{session.max_hp[player_id]}\n"
        
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
bot.tree.add_command(group)
bot.run(my_bot_token)