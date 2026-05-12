import discord
from discord import app_commands
from discord.ext import commands

ALL_COLOR_ROLES = [
    941482022445125712, 941483503277719632, 941483971647246358, 941484130787557516, 941492061146869790, 941484563761352798, 941484658191917116, 941484797111439430,
    941484975180611614, 941495959731437598, 941485050212532284, 941485208962727966, 941485316584403046, 941485501133783091, 941485609317441576, 941487975420801125,
    941485727089307649, 941485814569918515, 941491908407099413, 941485961370538004, 941486020849958933, 941486280825536603, 941486412899946527, 941486671634002011,
    941489550256111646, 941486762407116821, 941486878425768046, 941486961384894506, 941487097083199508, 941487227391856680, 941487368437911582, 941487546041532456,
    941487675721007195, 941487725222170715, 941487911260532826 
]

class ColorSelect(discord.ui.Select):
    def __init__(self, placeholder, options, custom_id):
        # custom_id is CRITICAL for persistent views
        super().__init__(placeholder=placeholder, min_values=1, max_values=1, options=options, custom_id=custom_id)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        # 1. Check which color roles the user currently has
        member_roles = [role for role in interaction.user.roles if role.id in ALL_COLOR_ROLES]
        
        # 2. Handle Removal
        if self.values[0] == "remove":
            if member_roles:
                await interaction.user.remove_roles(*member_roles)
                return await interaction.followup.send("All cosmic colors have been stripped.", ephemeral=True)
            return await interaction.followup.send("You don't have a color role to remove!", ephemeral=True)

        # 3. Handle Assignment
        selected_role_id = int(self.values[0])
        new_role = interaction.guild.get_role(selected_role_id)

        if new_role:
            # Check hierarchy safety
            if interaction.guild.me.top_role <= new_role:
                return await interaction.followup.send("I can't assign this role! Move my 'Enceladus' role higher in settings.", ephemeral=True)
            
            await interaction.user.remove_roles(*member_roles)
            await interaction.user.add_roles(new_role)
            await interaction.followup.send(f"Your color is now **{new_role.name}**!", ephemeral=True)

class PersistentColorView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None) 

        # --- PAGE 1 ---
        p1_options = [
            discord.SelectOption(label="Bright Red", value="941482022445125712"),
            discord.SelectOption(label="Dark Red", value="941483503277719632"),
            discord.SelectOption(label="Hot Pink", value="941483971647246358"),
            discord.SelectOption(label="Coral", value="941484130787557516"),
            discord.SelectOption(label="Light Salmon", value="941492061146869790"),
            discord.SelectOption(label="Pumpkin Orange", value="941484563761352798"),
            discord.SelectOption(label="Orange", value="941484658191917116"),
            discord.SelectOption(label="Gold", value="941484797111439430"),
            discord.SelectOption(label="Banana Yellow", value="941484975180611614"),
            discord.SelectOption(label="Bright Yellow", value="941495959731437598"),
            discord.SelectOption(label="Peach", value="941485050212532284"),
            discord.SelectOption(label="Lavender", value="941485208962727966"),
            discord.SelectOption(label="Violet", value="941485316584403046"),
            discord.SelectOption(label="Fushia", value="941485501133783091"),
            discord.SelectOption(label="Royal Purple", value="941485609317441576"),
            discord.SelectOption(label="Dark Purple", value="941487975420801125"),
            discord.SelectOption(label="Lime Green", value="941485727089307649"),
            discord.SelectOption(label="Spring Green", value="941485814569918515"),
            discord.SelectOption(label="Dark Olive", value="941491908407099413"),
            discord.SelectOption(label="Grassy Green", value="941485961370538004"),
            discord.SelectOption(label="Sea Green", value="941486020849958933"),
            discord.SelectOption(label="Aqua", value="941486280825536603"),
            discord.SelectOption(label="Dark Turquoise", value="941486412899946527"),
            discord.SelectOption(label="Sky Blue", value="941486671634002011"),
            discord.SelectOption(label="Night Sky", value="941489550256111646"),
        ]
        self.add_item(ColorSelect("Cosmic Palette: Page 1", p1_options, custom_id="color_select_p1"))

        # --- PAGE 2 ---
        p2_options = [
            discord.SelectOption(label="Royal Blue", value="941486762407116821"),
            discord.SelectOption(label="Navy Blue", value="941486878425768046"),
            discord.SelectOption(label="Chocolate", value="941486961384894506"),
            discord.SelectOption(label="Sand", value="941487097083199508"),
            discord.SelectOption(label="Maroon", value="941487227391856680"),
            discord.SelectOption(label="Honeydew Green", value="941487368437911582"),
            discord.SelectOption(label="Lavender Blush", value="941487546041532456"),
            discord.SelectOption(label="Bright White", value="941487675721007195"),
            discord.SelectOption(label="Void Black", value="941487725222170715"),
            discord.SelectOption(label="Gray", value="941487911260532826"),
            discord.SelectOption(label="❌ Remove Color", value="remove", description="Reset to default")
        ]
        self.add_item(ColorSelect("Cosmic Palette: Page 2", p2_options, custom_id="color_select_p2"))

# --- SHARED TOGGLE LOGIC ---
async def toggle_role(interaction: discord.Interaction, role_id: int):
    role = interaction.guild.get_role(role_id)
    if not role:
        return await interaction.response.send_message("Role not found! Check the code IDs.", ephemeral=True)
    
    if role in interaction.user.roles:
        await interaction.user.remove_roles(role)
        await interaction.response.send_message(f"Removed **{role.name}** role.", ephemeral=True)
    else:
        await interaction.user.add_roles(role)
        await interaction.response.send_message(f"Added **{role.name}** role!", ephemeral=True)

# --- REUSABLE COMPONENTS ---
class RoleButton(discord.ui.Button):
    def __init__(self, label, role_id, emoji=None, style=discord.ButtonStyle.gray):
        super().__init__(label=label, emoji=emoji, style=style, custom_id=f"role_{role_id}")
        self.role_id = role_id

    async def callback(self, interaction: discord.Interaction):
        await toggle_role(interaction, self.role_id)

class RoleSelect(discord.ui.Select):
    def __init__(self, placeholder, options, custom_id):
        super().__init__(placeholder=placeholder, min_values=1, max_values=1, options=options, custom_id=custom_id)

    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "remove":
            # Specialized removal for the Color dropdowns
            member_roles = [r for r in interaction.user.roles if r.id in ALL_COLOR_ROLES]
            await interaction.user.remove_roles(*member_roles)
            return await interaction.response.send_message("All cosmic colors cleared!", ephemeral=True)
        
        await toggle_role(interaction, int(self.values[0]))

# --- THE VIEWS (One for each screenshot category) ---

class PronounView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(RoleButton("He/Him", 927535319778197554, "🚹"))
        self.add_item(RoleButton("She/Her", 927535749274951750, "🚺"))
        self.add_item(RoleButton("They/Them", 927535867172626524, "💛"))
        self.add_item(RoleButton("Any Pronoun", 1036615505773084762, "💎"))

class DMStatusView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(RoleButton("DMs Open", 1117449650790731919, "✅", discord.ButtonStyle.green))
        self.add_item(RoleButton("Ask to DM", 1117449682734563328, "⚠️", discord.ButtonStyle.blurple))
        self.add_item(RoleButton("DMs Closed", 1117449709414514748, "❌", discord.ButtonStyle.red))

class PingView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        pings = [
            ("Announcements", 1117441565657419787, "📢"), ("Bump Reminder", 1295212860720418887, "🔔"),
            ("Welcome Ping", 1295670300674883646, "👋"), ("Giveaways", 1295670387501436970, "🎁"),
            ("Events", 1295670451988594760, "🎭"), ("Partnerships", 1306077625428611082, "🤝"),
            ("Stream Alerts", 1307275275431841802, "📺"), ("Astro Content Alerts", 1440168122639454380, "🐲"),
            ("Fact of the Day", 1473410135161573416, "💡"), ("Question of the Day", 1473410588557185209, "❓"),
            ("Poll Alerts", 1496356983320743946, "🗳️"), ("Daily Fortune Ping", 1503642487586029568, "🥠")
        ]
        for label, rid, emo in pings:
            self.add_item(RoleButton(label, rid, emo))

class SpeciesSelectView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        options = [
            discord.SelectOption(label="Canine", value="1295670753408192512", emoji="🐺"),
            discord.SelectOption(label="Feline", value="1295671149740556299", emoji="🐱"),
            discord.SelectOption(label="Vulpine", value="1295670778615955467", emoji="🦊"),
            discord.SelectOption(label="Protogen", value="1295670812078243882", emoji="🍞"),
            discord.SelectOption(label="Synth", value="1295704143918403624", emoji="🤖"),
            discord.SelectOption(label="Raccoon", value="1295670843359367168", emoji="🦝"),
            discord.SelectOption(label="Bat", value="1295670875542257694", emoji="🦇"),
            discord.SelectOption(label="Dragon", value="1295670895335182399", emoji="🐲"),
            discord.SelectOption(label="Kobold", value="1503673317633036288", emoji="🐲🦎"),
            discord.SelectOption(label="Lizard", value="1295670941027799084", emoji="🦎"),
            discord.SelectOption(label="Sergal", value="1295670958920695869", emoji="🧀"),
            discord.SelectOption(label="Deer", value="1295670981712543806", emoji="🦌"),
            discord.SelectOption(label="Shark", value="1295671004588408832", emoji="🦈"),
            discord.SelectOption(label="Rabbit", value="1295671022711869532", emoji="🐰"),
            discord.SelectOption(label="Equine", value="1295671043146383371", emoji="🐴"),
            discord.SelectOption(label="Avian", value="1295671061420965889", emoji="🐦"),
            discord.SelectOption(label="Bear", value="1295671101090697259", emoji="🐻"),
            discord.SelectOption(label="Rodent", value="1503105638585204928", emoji="🐭"),
            discord.SelectOption(label="Hyena", value="1503105694839341209", emoji="🦴"),
            discord.SelectOption(label="Goat", value="1295671123995918346", emoji="🐐"),
            discord.SelectOption(label="Otter", value="1503105754322698392", emoji="🦦"),
            discord.SelectOption(label="Red Panda", value="1503105723037650944", emoji="🐾"),
            discord.SelectOption(label="Sheep", value="1295705466050973718", emoji="🐑"),
            discord.SelectOption(label="Slime", value="1295671199237406721", emoji="🦠"),
            discord.SelectOption(label="Other/Hybrid", value="1295671231722291243", emoji="✨"),
        ]
        self.add_item(RoleSelect("Select your OC species!", options, "species_dropdown"))

class SexualityView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        # We use RoleButton just like we did in IdentityView
        self.add_item(RoleButton("Straight", 1295668771339370546, "👫"))
        self.add_item(RoleButton("Bisexual", 1295668827362693190, "💗"))
        self.add_item(RoleButton("Gay", 1295668848716025857, "👬"))
        self.add_item(RoleButton("Lesbian", 1295668867049328641, "👭"))
        self.add_item(RoleButton("Pansexual", 1295668898464792637, "💛"))
        self.add_item(RoleButton("Asexual", 1295668916554567691, "♠️"))
        self.add_item(RoleButton("Other Orientation", 1295668942307721237, "✨"))

class RegionView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(RoleButton("North America", 1306593842602053692, "🌎"))
        self.add_item(RoleButton("South America", 1503672483176255558, "🌎"))
        self.add_item(RoleButton("Europe", 1306593981378986005, "🌍"))
        self.add_item(RoleButton("Oceania", 1306593932473401405, "🌏"))
        self.add_item(RoleButton("Africa", 1306594172102246421, "🌍"))
        self.add_item(RoleButton("Asia", 1306594194122346517, "🌏"))
        self.add_item(RoleButton("Antarctica", 1503672527095074886, "🧊"))

class PlatformView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(RoleButton("PlayStation", 1036568587151867955, "🔵"))
        self.add_item(RoleButton("Xbox", 1036568737005969438, "🟢"))
        self.add_item(RoleButton("Nintendo", 1036569121464262696, "🔴"))
        self.add_item(RoleButton("PC", 1036568197933039637, "🖥️"))
        self.add_item(RoleButton("PCVR", 1036598348976762890, "🥽"))
        self.add_item(RoleButton("Mobile", 1036568766391271504, "📱"))
        self.add_item(RoleButton("Gamer", 933525968662962216, "👾"))
        self.add_item(RoleButton("Tabletop Gamer", 1036567825835380826, "🎲"))

class FandomView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(RoleButton("Furry", 1118022152675921940, "🦊"))
        self.add_item(RoleButton("Brony", 1118022235681214485, "🐴"))


# --- THE COG CLASS ---
class RoleCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="setup_all_roles", description="Posts all self-role menus")
    @app_commands.checks.has_permissions(administrator=True)
    async def setup_all_roles(self, interaction: discord.Interaction):
        await interaction.response.send_message("Deploying The Cosmic Lair Role System...", ephemeral=True)
        
        # 1. Post Pronouns
        emb_pro = discord.Embed(title="🆔 Pronouns", description="Select your preferred pronouns.", color=0x6a0dad)
        await interaction.channel.send(embed=emb_pro, view=PronounView())

        # 2. Post DM Status
        emb_dm = discord.Embed(title="💬 DM Status", description="Let others know if your DMs are open.", color=0x6a0dad)
        await interaction.channel.send(embed=emb_dm, view=DMStatusView())

        # 3. Post Species
        emb_spec = discord.Embed(title="🐾 OC Species", description="Choose your primary fursona species.", color=0x6a0dad)
        await interaction.channel.send(embed=emb_spec, view=SpeciesSelectView())

        # 4. Post Sexuality
        emb_sex = discord.Embed(title="🌈 Orientation", description="Select your orientation.", color=0x6a0dad)
        await interaction.channel.send(embed=emb_sex, view=SexualityView())

        # 5. Post Pings
        emb_ping = discord.Embed(title="🔔 Community Notifications", description="What should we ping you for?", color=0x6a0dad)
        await interaction.channel.send(embed=emb_ping, view=PingView())

        # 6. Post Regional
        emb_region = discord.Embed(title="🌍 Regional Roles", description="Where in the world are you?", color=0x6a0dad)
        await interaction.channel.send(embed=emb_region, view=RegionView())

        # 7. Post Platforms
        emb_platform = discord.Embed(title="🎮 Gaming Platforms", description="What platform do you play on?", color=0x6a0dad)
        await interaction.channel.send(embed=emb_platform, view=PlatformView())

        # 8. Fandoms
        emb_fandom = discord.Embed(title="🎮 Fandom Roles", description="What fandoms do you identify with?", color=0x6a0dad)
        await interaction.channel.send(embed=emb_fandom, view=FandomView())

        # 9. Post Colors
        emb_color = discord.Embed(title="✨ Cosmic Color Roles", description="Pick a color for your name!", color=0x6a0dad)
        await interaction.channel.send(embed=emb_color, view=PersistentColorView())

async def setup(bot):
    await bot.add_cog(RoleCog(bot))