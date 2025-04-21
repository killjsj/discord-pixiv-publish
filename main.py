import json
import asyncio
import websockets
import requests
from urllib.parse import urljoin
my_application_id = ""
my_credentials_token = ""
my_bot_token = ""
class DiscordGateway:
    def __init__(self, token):
        self.token = token
        self.seq = None
        self.session_id = None
        self.heartbeat_interval = None
        self.ws = None

    async def connect(self):
        # 获取 Gateway URL
        r = requests.get("https://discord.com/api/v10/gateway")
        gateway_url = r.json()['url']
        
        # 连接到 Gateway
        self.ws = await websockets.connect(f"{gateway_url}?v=10&encoding=json")
        
        # 接收 hello 事件
        hello_data = await self.receive_json()
        self.heartbeat_interval = hello_data['d']['heartbeat_interval'] / 1000
        
        # 发送身份验证
        await self.identify()
        
        # 开始心跳
        asyncio.create_task(self.heartbeat())
        
        # 开始事件循环
        await self.event_loop()

    async def identify(self):
        identify_data = {
            "op": 2,
            "d": {
                "token": self.token,
                "intents": 513, # GUILDS (1 << 0) | GUILD_MESSAGES (1 << 9)
                "properties": {
                    "os": "windows",
                    "browser": "Custom",
                    "device": "Custom"
                }
            }
        }
        await self.send_json(identify_data)

    async def heartbeat(self):
        while True:
            heartbeat_data = {
                "op": 1,
                "d": self.seq
            }
            await self.send_json(heartbeat_data)
            await asyncio.sleep(self.heartbeat_interval)

    async def handle_interaction(self, interaction):
        if interaction['type'] == 2 and interaction['data']['name'] == 'setu':
            # 获取 r18 参数
            r18_value = next((opt['value'] for opt in interaction['data']['options'] 
                            if opt['name'] == 'r18'), 'random')
            
            # 调用 API 获取图片
            api_url = "https://api.lolicon.app/setu/v2"
            r18_param = {
                "no": 0,
                "yes": 1,
                "random": 2
            }.get(r18_value, 2)
            
            try:
                # 发送延迟响应
                await self.send_interaction_response(interaction['id'], 
                                                  interaction['token'], 
                                                  response_type=5)
                
                # 获取图片
                response = requests.get(api_url, params={"r18": r18_param})
                image_data = response.json()
                
                if image_data and "data" in image_data and len(image_data["data"]) > 0:
                    image_url = image_data["data"][0]["urls"]["original"]
                    
                    # 发送后续消息
                    await self.send_followup_message(interaction['token'], {
                        "embeds": [{
                            "title": "Pixiv Image",
                            "image": {
                                "url": image_url
                            }
                        }]
                    })
                else:
                    await self.send_followup_message(interaction['token'], {
                        "content": "未能获取图片，请稍后重试。"
                    })
                    
            except Exception as e:
                await self.send_followup_message(interaction['token'], {
                    "content": f"发生错误：{str(e)}"
                })

    async def send_interaction_response(self, interaction_id, token, response_type, data=None):
        url = f"https://discord.com/api/v10/interactions/{interaction_id}/{token}/callback"
        payload = {
            "type": response_type,
            "data": data or {}
        }
        requests.post(url, json=payload)

    async def send_followup_message(self, token, data):
        url = f"https://discord.com/api/v10/webhooks/{my_application_id}/{token}"
        requests.post(url, json=data)

    async def event_loop(self):
        while True:
            try:
                event = await self.receive_json()
                
                # 更新序列号
                if event['s']:
                    self.seq = event['s']
                
                # 处理事件
                if event['op'] == 0: # Dispatch
                    if event['t'] == 'READY':
                        self.session_id = event['d']['session_id']
                        print("Bot is ready!")
                    elif event['t'] == 'INTERACTION_CREATE':
                        await self.handle_interaction(event['d'])
                
            except Exception as e:
                print(f"Error in event loop: {e}")
                await asyncio.sleep(5)
                await self.connect()

    async def send_json(self, data):
        await self.ws.send(json.dumps(data))

    async def receive_json(self):
        return json.loads(await self.ws.recv())

# 注册斜杠命令
def register_commands():

    curl = f"https://discord.com/api/v10/applications/{my_application_id}/commands"

    # This is an example CHAT_INPUT or Slash Command, with a type of 1
    json = {
        "name": "setu",
        "type": 1,
        "description": "Send a random pixiv photo",
        "name_localizations": {
            "zh-CN": "发张pixiv图片"
        },
        "nsfw": True,
        "options": [
            {
                "name": "r18",
                "description": "r18?",
                "name_localizations": {
                    "zh-CN": "启用r18?"
                },
                "type": 3,
                "required": True,
                "choices": [
                    {
                        "name": "0",
                        "value": "no"
                    },
                    {
                        "name": "1",
                        "value": "yes"
                    },
                    {
                        "name": "2",
                        "value": "random"
                    }
                ],
                "default": "2"
            }
        ]
    }

    # For authorization, you can use either your bot token
    headers = {
        "Authorization": f"Bot {my_bot_token}"
    }

    # or a client credentials token for your app with the applications.commands.update scope
    headers = {
        "Authorization": f"Bearer {my_credentials_token}"
    }

    r = requests.post(curl, headers=headers, json=json)
    print(f"命令注册结果: {r.status_code}")

async def main():
    gateway = DiscordGateway(my_bot_token)
    register_commands()
    await gateway.connect()

if __name__ == "__main__":
    asyncio.run(main())