import discord
from discord.ext import commands, tasks
import requests
from datetime import datetime, timedelta, timezone
import json
from config import load_subscribe, save_subscribe ,load_config

config = load_config()

SUBSCRIBE_CHANNEL_ID = config.get("channel_id")

class Subscribe(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.subscribe_check_loop.start() 

    def cog_unload(self):
        self.subscribe_check_loop.cancel()

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction: discord.Reaction, user: discord.User):
        if user.bot or not reaction.message.embeds:
            return

        embed = reaction.message.embeds[0]
        footer_text = embed.footer.text

        if "CTF ID: " not in footer_text:
            return
        
        try:
            ctf_id = footer_text.split("CTF ID: ")[-1] 
        except Exception:
            return 

        data = load_subscribe()
        
        if ctf_id not in data.get('events', {}):
            response = requests.get(f"https://ctftime.org/api/v1/events/{ctf_id}/")
            if response.status_code == 200:
                if 'events' not in data:
                    data['events'] = {} 
                data['events'][ctf_id] = {
                    "info": response.json(),
                    "subscribers": [],
                    "notified": False
                }
            else:
                return 
        
        if user.id not in data['events'][ctf_id]['subscribers']:
            data['events'][ctf_id]['subscribers'].append(user.id)
            save_subscribe(data)
            
            try:
                dm_channel = await user.create_dm() 
                await dm_channel.send(f"✅ รอรับการแจ้งเตือนสำหรับ CTF: **{embed.title}** แล้ว\n\nบอทจะส่งข้อความแจ้งเตือนใน Public Channel 1 วันก่อนงานเริ่ม!")
            except discord.Forbidden:
                pass 
                
    @commands.Cog.listener()
    async def on_reaction_remove(self, reaction: discord.Reaction, user: discord.User):
        if user.bot or not reaction.message.embeds:
            return

        embed = reaction.message.embeds[0]
        footer_text = embed.footer.text

        if "CTF ID: " not in footer_text:
            return
        
        try:
            ctf_id = footer_text.split("CTF ID: ")[-1] 
        except Exception:
            return 

        data = load_subscribe()
        
        if ctf_id in data.get('events', {}):
            if user.id in data['events'][ctf_id]['subscribers']:
                data['events'][ctf_id]['subscribers'].remove(user.id)
                save_subscribe(data)
                
                try:
                    dm_channel = await user.create_dm() 
                    await dm_channel.send(f"❌ ยกเลิกการแจ้งเตือนสำหรับ CTF: **{embed.title}** เรียบร้อยแล้ว")
                except discord.Forbidden:
                    pass 
                
                if not data['events'][ctf_id]['subscribers']:
                    del data['events'][ctf_id]
                    save_subscribe(data)


    @tasks.loop(seconds=30) 
    async def subscribe_check_loop(self):
        await self.client.wait_until_ready()
        now_utc = datetime.now(timezone.utc)
        
        subscribe_data = load_subscribe()
        
        channel = self.client.get_channel(SUBSCRIBE_CHANNEL_ID)
        
        if not channel:
            print(f"Error: Fixed subscribe notification channel (ID: {SUBSCRIBE_CHANNEL_ID}) not found or inaccessible.")
            return

        events_to_remove = []

        if 'events' not in subscribe_data:
            subscribe_data['events'] = {}
            
        for ctf_id, event_data in subscribe_data['events'].items():
            ctf_info = event_data['info']
            start_time_iso = ctf_info.get('start')
            
            if event_data.get('notified'):
                try:
                    start_dt = datetime.fromisoformat(start_time_iso.replace('Z', '+00:00'))
                    if now_utc >= start_dt + timedelta(hours=2): 
                        events_to_remove.append(ctf_id)
                    continue
                except (ValueError, TypeError):
                    events_to_remove.append(ctf_id)
                    continue

            if not start_time_iso:
                events_to_remove.append(ctf_id)
                continue

            try:
                start_dt = datetime.fromisoformat(start_time_iso.replace('Z', '+00:00'))
            except ValueError:
                events_to_remove.append(ctf_id)
                continue
            
            notify_dt = start_dt - timedelta(days=1)
            
            if now_utc >= notify_dt and now_utc < start_dt:
                
                try:
                    embed = self.client.create_ctf_embed(ctf_info)
                except AttributeError:
                    print("Error: client.create_ctf_embed not found. Ensure it is defined and set in main.py.")
                    continue
                                
                subscriber_mentions = [f"<@{user_id}>" for user_id in event_data['subscribers']]
                mention_string = " ".join(subscriber_mentions)
                
                message_content = f"🔔 **[1 DAY LEFT]** งานใกล้เริ่มแล้วนะเตรียมพร้อมรึยังพี่ชาย:\n{mention_string}"
                await channel.send(content=message_content, embed=embed)

                event_data['notified'] = True
                
            if now_utc >= start_dt:
                events_to_remove.append(ctf_id)

        for ctf_id in events_to_remove:
            if ctf_id in subscribe_data['events']:
                del subscribe_data['events'][ctf_id]

        save_subscribe(subscribe_data) 

async def setup(client):
    await client.add_cog(Subscribe(client))