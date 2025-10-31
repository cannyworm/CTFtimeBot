import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional
from config import load_config, save_config


class ConfigurationGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="config", description="ตั้งค่าครับ")
    

    def validate_time_format(self, time_str: str):
        try:
            if ':' not in time_str:
                raise ValueError("ต้องมีเครื่องหมาย ':' คั่น ชั่วโมงและนาที")

            parts = time_str.split(':')
            if len(parts) != 2:
                raise ValueError("รูปแบบไม่ถูกต้อง ต้องเป็น HH:MM หรือ H:MM เท่านั้น")
                
            hour_str, minute_str = parts

            hour = int(hour_str)
            if not 0 <= hour <= 23:
                raise ValueError("ชั่วโมงต้องอยู่ระหว่าง 00 ถึง 23")
            
            minute = int(minute_str)
            if not 0 <= minute <= 59:
                raise ValueError("นาทีต้องอยู่ระหว่าง 00 ถึง 59")
            
            if len(minute_str) != 2:
                raise ValueError("นาทีต้องมีสองหลัก (เช่น 09 แทน 9)")

            if len(hour_str) > 2:
                raise ValueError("ชั่วโมงต้องไม่เกินสองหลัก")

            return True, None 
        except ValueError as e:
            return False, str(e)
        except Exception:
            return False, "รูปแบบเวลาไม่ถูกต้อง"

    def process_roles(self, role_string: str, interaction: discord.Interaction):
        if not role_string:
            raise ValueError(f"กรุณาพิมพ์ Role Tag (@role) ครับ")
        
        role_ids = []
        role_names = []
        
        for r in role_string.split():
            if r.lower() == '@everyone':
                everyone_role = interaction.guild.default_role
                role_ids.append(everyone_role.id)
                role_names.append(everyone_role.name)
            elif r.startswith("<@&") and r.endswith(">"):
                try:
                    role_id = int(r.strip("<@&>"))
                    role_object = interaction.guild.get_role(role_id)
                    role_ids.append(role_id)
                    role_names.append(role_object.name if role_object else f"Unknown Role ({role_id})")
                except ValueError:
                    raise ValueError(f"รูปแบบ Role ที่ป้อนไม่ถูกต้องในข้อความ: {r}")
            else:
                raise ValueError(f"รูปแบบ Role ที่ป้อนไม่ถูกต้องในข้อความ: {r}")

        return role_ids, ", ".join(role_names)


    @app_commands.default_permissions(manage_guild=False) 
    @app_commands.command(name="setconfig", description="Set configurable bot options (limit, channel, roles, time)")
    @app_commands.describe(
        limit="จำนวน CTF ที่ต้องดึง",
        time="เวลาที่ต้องการแจ้งเตือน ชม:นาที เช่น 00:00 ตามรูปแบบเวลาไทย", 
        channel="ส่งไปช่องไหน", 
        admin_roles="Role ผู้ดูแลที่สามารถตั้งค่าบอทได้ (พิมพ์ @role1 @role2)", 
        notify_roles="Role ที่ได้รับการแจ้งเตือน (พิมพ์ @role1 @role2)"
    )
    async def setconfig(
        self,
        interaction: discord.Interaction,
        limit: Optional[int] = None,
        time: Optional[str] = None,
        channel: Optional[discord.TextChannel] = None,
        admin_roles: Optional[str] = None,
        notify_roles: Optional[str] = None
    ):
        await interaction.response.defer(ephemeral=True)
        config = load_config()
        
        configured_admin_roles = config.get('admin_roles', [])
        user_permissions = interaction.user.guild_permissions
        
        has_required_role = any(role.id in configured_admin_roles for role in interaction.user.roles)
        has_admin_perms = user_permissions.administrator or user_permissions.manage_guild
        
        if configured_admin_roles:
            if not has_required_role and not has_admin_perms:
                return await interaction.followup.send("❌ คุณไม่มีสิทธิ์ใช้งานคำสั่งนี้ (สิทธิ์ถูกจำกัดไว้สำหรับคนที่มี Admin/Manage Guild Perms หรือ Role ผู้ดูแลที่ถูกตั้งค่าไว้)", ephemeral=True)
        
        
        changes = []
        
        if limit is not None:
            if limit <= 0:
                return await interaction.followup.send("❌ Limit ต้องเป็นจำนวนเต็มบวกเท่านั้น (มากกว่า 0)", ephemeral=True)
            
            config['limit'] = limit
            changes.append(f"Limit: **{limit}**")
        
        if time is not None:
            is_valid, error_msg = self.validate_time_format(time)
            if not is_valid:
                return await interaction.followup.send(f"❌ รูปแบบเวลาไม่ถูกต้อง: **{time}**\nกรุณาใช้รูปแบบ `HH:MM` หรือ `H:MM` และค่าต้องอยู่ระหว่าง 00:00 - 23:59 ตามรูปแบบเวลาไทย\nข้อผิดพลาด: {error_msg}", ephemeral=True)

            config['time'] = time
            changes.append(f"Time: **{time}**")

        if channel is not None:
            config['channel_id'] = channel.id
            changes.append(f"Channel: **#{channel.name}**")


        if admin_roles is not None:
            try:
                role_ids, role_names = self.process_roles(admin_roles, interaction)
                
                config['admin_roles'] = role_ids
                
                changes.append(f"Admin Roles: **{role_names}**")

            except ValueError as e:
                await interaction.followup.send(f"❌ {e}", ephemeral=True)
                return
            
        if notify_roles is not None:
            try:
                role_ids, role_names = self.process_roles(notify_roles, interaction)
                config['notify_roles'] = role_ids
                changes.append(f"Notify Roles: **{role_names}**")
            except ValueError as e:
                await interaction.followup.send(f"❌ {e}", ephemeral=True)
                return

        if not changes:
            await interaction.followup.send("ท่านไม่ได้ระบุค่าที่ต้องการตั้งค่าใดๆ ครับ.", ephemeral=True)
            return
            
        save_config(config)
        
        response_message = "บันทึกการตั้งค่าเรียบร้อยแล้วครับ:\n" + "\n".join(f"- {c}" for c in changes)
        await interaction.followup.send(response_message, ephemeral=True)


    @app_commands.default_permissions(manage_guild=False)
    @app_commands.command(name="removeconfig", description="Remove roles from Admin or Notify list")
    @app_commands.describe(
        setting="เลือกรายการที่จะลบ Role ออก", 
        roles="Role ที่ต้องการลบ (พิมพ์ @role1 @role2)"
    )
    @app_commands.choices(
        setting=[
            app_commands.Choice(name="admin_roles", value="admin_roles"),
            app_commands.Choice(name="notify_roles", value="notify_roles")
        ]
    )
    async def removeconfig(
        self,
        interaction: discord.Interaction,
        setting: app_commands.Choice[str], 
        roles: Optional[str] = None
    ):
        await interaction.response.defer(ephemeral=True)
        config = load_config()

        configured_admin_roles = config.get('admin_roles', [])
        user_permissions = interaction.user.guild_permissions

        has_required_role = any(role.id in configured_admin_roles for role in interaction.user.roles)
        has_admin_perms = user_permissions.administrator or user_permissions.manage_guild
        
        if configured_admin_roles:
            if not has_required_role and not has_admin_perms:
                 return await interaction.followup.send("❌ คุณไม่มีสิทธิ์ใช้งานคำสั่งนี้ (สิทธิ์ถูกจำกัดไว้สำหรับคนที่มี Admin/Manage Guild Perms หรือ Role ผู้ดูแลที่ถูกตั้งค่าไว้)", ephemeral=True)
        elif not has_admin_perms:
             return await interaction.followup.send("❌ คุณไม่มีสิทธิ์ใช้งานคำสั่งนี้ (สิทธิ์ถูกจำกัดไว้สำหรับคนที่มี Admin/Manage Guild Perms)", ephemeral=True)


        if not roles:
            return await interaction.followup.send("เลือก role ที่ต้องการลบด้วยครับ", ephemeral=True)

        try:
            role_ids_to_remove, _ = self.process_roles(roles, interaction)
        except ValueError as e:
            return await interaction.followup.send(f"❌ {e}", ephemeral=True)

        current_roles_key = setting.value
        current_roles_list = config.get(current_roles_key, [])
        
        roles_removed = 0
        new_roles = []

        for role_id in current_roles_list:
            if role_id in role_ids_to_remove:
                roles_removed += 1
            else:
                new_roles.append(role_id)

        config[current_roles_key] = new_roles
        
        save_config(config)
        
        if roles_removed > 0:
            response_message = f"✅ ลบ Role ออกจากรายการ **{current_roles_key}** จำนวน **{roles_removed}** รายการเรียบร้อยแล้ว."
            await interaction.followup.send(response_message, ephemeral=True)
            return

        elif roles_removed == 0:
            await interaction.followup.send(f"⚠️ ไม่พบ Role ที่ระบุในรายการ **{current_roles_key}** ที่ถูกตั้งค่าไว้.", ephemeral=True)
            return


async def setup(bot: commands.Bot):
    group = ConfigurationGroup()
    bot.tree.add_command(group)
    print("ConfigurationGroup added to tree")