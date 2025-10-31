import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional
import requests
from datetime import datetime
import time
from config import load_config

GUILD_ID = discord.Object(id=978976733296459807)

class SearchCommands(commands.Cog):
    """
    Cog สำหรับคำสั่ง /search เพื่อค้นหา CTF จาก CTFTime
    """
    def __init__(self, client):
        self.client = client
        self.GUILD_ID = GUILD_ID

    @app_commands.command(name="search", description="Command to search CTF you need to")
    @app_commands.guilds(GUILD_ID)
    @app_commands.describe(
        name="ชื่องานที่ต้องการ",
        format="รูปแบบของงาน",
        weight="ค่าความยากมากกว่าหรือเท่ากับเท่าใด (เช่น 50.0)",
        location="เป็น onsite หรือ online",
        restrictions="แข่งเดียวหรือทีม",
        ctf_id="ไอดีของ CTF ที่ต้องการหา (ตัวเลข)"
    )
    @app_commands.choices(
        format=[
            app_commands.Choice(name="Jeopardy", value="Jeopardy"),
            app_commands.Choice(name="Attack-Defense", value="Attack-Defense"),
            app_commands.Choice(name="Hack-quest", value="Hack-quest")
        ],
        location=[
            app_commands.Choice(name="Onsite", value="onsite"),
            app_commands.Choice(name="Online", value="online"),
        ],
        restrictions=[
            app_commands.Choice(name="Individual", value="Individual"),
            app_commands.Choice(name="Open", value="Open") # Open หมายถึงแข่งทีม/ไม่จำกัด
        ]
    )
    async def search(
        self,
        interaction: discord.Interaction,
        name: Optional[str] = None,
        format: Optional[app_commands.Choice[str]] = None,
        weight: Optional[float] = None,
        location: Optional[app_commands.Choice[str]] = None,
        restrictions: Optional[app_commands.Choice[str]] = None,
        ctf_id: Optional[int] = None,
    ):
        await interaction.response.defer(ephemeral=False) 

        if ctf_id:
            url = f"https://ctftime.org/api/v1/events/{ctf_id}/"
            try:
                response = requests.get(url)
                response.raise_for_status()
                info = response.json()
                
                if 'detail' in info or not info.get('id'): 
                    return await interaction.followup.send(f"❌ ไม่พบ CTF ID: `{ctf_id}` ในระบบ CTFTime")

                embed = self.client.create_ctf_embed(info)
                return await interaction.followup.send(f"✅ พบผลลัพธ์สำหรับ CTF ID: `{ctf_id}`", embed=embed)
            except Exception as e:
                print(f"Error during CTF ID search: {e}")
                return await interaction.followup.send(f"❌ เกิดข้อผิดพลาดในการค้นหา CTF ID: {e}")

        if not any([name, format, weight, location, restrictions]):
             return await interaction.followup.send("⚠️ กรุณาใส่เกณฑ์การค้นหาอย่างน้อยหนึ่งอย่าง (เช่น ชื่อ, Format, หรือ ID)", ephemeral=True)
        
        now_ts = int(time.time())
        three_months_later = now_ts + 90 * 24 * 60 * 60 
        
        url = f"https://ctftime.org/api/v1/events/?limit=100&start={now_ts}&finish={three_months_later}"
        
        try:
            response = requests.get(url)
            response.raise_for_status()
            ctf_list = response.json()
        except Exception as e:
            return await interaction.followup.send(f"❌ เกิดข้อผิดพลาดในการดึงรายการ CTF: {e}")
        
        
        results = []
        
        for ctf in ctf_list:
            match = True
            
            if name and name.lower() not in ctf.get('title', '').lower():
                match = False
            
            if format and format.value != ctf.get('format'):
                match = False

            if weight is not None and ctf.get('weight', 0.0) < weight:
                match = False
                
            if location:
                is_onsite = ctf.get('onsite', False)
                required_onsite = location.value == 'onsite'
                if is_onsite != required_onsite:
                    match = False
            
            if restrictions and restrictions.value != ctf.get('restrictions'):
                match = False
                
            if match:
                results.append(ctf)

        config = load_config()
        if not results:
             return await interaction.followup.send("🔍 ไม่พบงาน CTF ที่ตรงตามเงื่อนไขที่คุณระบุในช่วง 3 เดือนข้างหน้า.", ephemeral=False)
        
        await interaction.followup.send(f"✅ พบงาน CTF ที่ตรงตามเงื่อนไข **{len(results)}** รายการ แสดงผมรายการสูงสุด **{config['limit']}** รายการ")
        
        for info in results[:config['limit']]:
            try:
                embed = self.client.create_ctf_embed(info)
                await interaction.channel.send(embed=embed)
            except Exception as e:
                print(f"Error creating embed for CTF {info.get('id', 'Unknown')}: {e}")
                pass 

async def setup(client):
    await client.add_cog(SearchCommands(client))