import discord
from discord.ext import commands
from discord.ui import View, Select, Button, Modal, TextInput
import os
import json
import time
import asyncio
import re
import threading

COOLDOWN_FILE = "verification_cooldowns.json"

VERIFICATION_CHANNEL_ID = 1297033393313288263
VERIFICATION_LOG_CHANNEL_ID = 1352834838478061608
PENDING_VERIFICATION_ROLE_ID = 1504001672576241665

LEVEL_10_ROLE_ID = 1295861102483210260

VERIFICATION_TEAM_ROLE_ID = 1502764416356319413
OWNER_ID = 395453475284320268
ADMIN_ROLE_ID = 593718477831929858

ROLE_18_VERIFIED = 1353561740238913636
ROLE_NSFW = 593907668515815424
ROLE_NSFW_PLUS = 935884854753624115

APPLICATION_TYPES = {
    "18plus": {
        "label": "18+ Verification",
        "roles": [
            ROLE_18_VERIFIED
        ]
    },

    "nsfw": {
        "label": "NSFW Access",
        "roles": [
            ROLE_18_VERIFIED,
            ROLE_NSFW
        ]
    },

    "nsfw_plus": {
        "label": "NSFW+ Access",
        "roles": [
            ROLE_18_VERIFIED,
            ROLE_NSFW,
            ROLE_NSFW_PLUS
        ]
    }
}

COOLDOWN_LOCK = threading.Lock()

def get_cooldown(user_id):
    with COOLDOWN_LOCK:
        if not os.path.exists(COOLDOWN_FILE):
            return 0, None
        try:
            with open(COOLDOWN_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError):
            return 0, None
        user_data = data.get(str(user_id))
        if not user_data:
            return 0, None
        return user_data.get("expires_at", 0), user_data.get("reason", "a previous application")

def set_cooldown(user_id, hours, reason):
    with COOLDOWN_LOCK:
        data = {}
        if os.path.exists(COOLDOWN_FILE):
            try:
                with open(COOLDOWN_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except (OSError, json.JSONDecodeError):
                try:
                    os.replace(COOLDOWN_FILE, f"{COOLDOWN_FILE}.corrupt")
                except OSError:
                    pass
        data[str(user_id)] = {
            "expires_at": time.time() + (hours * 3600),
            "reason": reason
        }
        temp_file = f"{COOLDOWN_FILE}.tmp"
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp_file, COOLDOWN_FILE)

class ReasonModal(Modal):
    def __init__(self, cog, member, application_key, approved):
        super().__init__(
            title="Verification Reason"
        )

        self.cog = cog
        self.member = member
        self.application_key = application_key

        self.approved = approved

        self.reason = TextInput(
            label="Reason",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=1000
        )

        self.add_item(self.reason)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        await self.cog.finish_verification(
            interaction=interaction,
            member=self.member,
            application_key=self.application_key,
            approved=self.approved,
            reason=self.reason.value
        )

class CancelConfirmView(View):
    def __init__(self, original_view):
        super().__init__(timeout=30)
        self.original_view = original_view

    @discord.ui.button(
        label="Yes, Cancel",
        style=discord.ButtonStyle.danger,
        emoji="🛑"
    )
    async def confirm_cancel(self, interaction, button):
        await self.original_view.cancel_application(interaction)

    @discord.ui.button(
        label="Nevermind",
        style=discord.ButtonStyle.secondary,
        emoji="↩️"
    )
    async def nevermind(self, interaction, button):
        await interaction.response.edit_message(
            content="✅ Cancelled the cancellation.",
            view=None
        )

class VerificationReviewView(View):
    def __init__(self, cog, member, application_key, custom_ids=None):
        super().__init__(timeout=None)

        self.cog = cog
        self.member = member
        self.application_key = application_key

        custom_ids = custom_ids or {}
        button_ids = {
            "Accept": custom_ids.get("accept", f"verification_accept:{member.id}:{application_key}"),
            "Accept w/ Reason": custom_ids.get("accept_reason", f"verification_accept_reason:{member.id}:{application_key}"),
            "Deny": custom_ids.get("deny", f"verification_deny:{member.id}:{application_key}"),
            "Deny w/ Reason": custom_ids.get("deny_reason", f"verification_deny_reason:{member.id}:{application_key}"),
            "Cancel Application": custom_ids.get("cancel", f"verification_cancel:{member.id}:{application_key}"),
        }

        for child in self.children:
            if isinstance(child, discord.ui.Button) and child.label in button_ids:
                child.custom_id = button_ids[child.label]

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message(
                "❌ This action can only be performed in a server.",
                ephemeral=True
            )
            return False

        custom_id = None
        if isinstance(interaction.data, dict):
            custom_id = interaction.data.get("custom_id")

        if custom_id and "cancel" in custom_id and interaction.user.id == self.member.id:
            return True

        allowed_roles = [
            VERIFICATION_TEAM_ROLE_ID,
            ADMIN_ROLE_ID,
        ]

        if interaction.user.id == OWNER_ID:
            return True

        for role in interaction.user.roles:
            if role.id in allowed_roles:
                return True

        await interaction.response.send_message(
            "❌ You are not allowed to use verification controls. Nice try, though! 😏",
            ephemeral=True
        )

        return False

    @discord.ui.button(
        label="Accept",
        style=discord.ButtonStyle.success,
        emoji="✅"
    )
    async def accept_button(self, interaction, button):
        await interaction.response.defer(ephemeral=True)

        await self.cog.finish_verification(
            interaction=interaction,
            member=self.member,
            application_key=self.application_key,
            approved=True,
            reason=None
        )

    @discord.ui.button(
        label="Accept w/ Reason",
        style=discord.ButtonStyle.success,
        emoji="📝",
        custom_id="verification_accept_reason"
    )
    async def accept_reason_button(self, interaction, button):
        await interaction.response.send_modal(
            ReasonModal(
                self.cog,
                self.member,
                self.application_key,
                True
            )
        )

    @discord.ui.button(
        label="Deny",
        style=discord.ButtonStyle.danger,
        emoji="❌"
    )
    async def deny_button(self, interaction, button):
        await interaction.response.defer(ephemeral=True)

        await self.cog.finish_verification(
            interaction=interaction,
            member=self.member,
            application_key=self.application_key,
            approved=False,
            reason=None
        )

    @discord.ui.button(
        label="Deny w/ Reason",
        style=discord.ButtonStyle.danger,
        emoji="📝",
        custom_id="verification_deny_reason"
    )
    async def deny_reason_button(self, interaction, button):
        await interaction.response.send_modal(
            ReasonModal(
                self.cog,
                self.member,
                self.application_key,
                False
            )
        )

    @discord.ui.button(
        label="Cancel Application",
        style=discord.ButtonStyle.secondary,
        emoji="🛑",
        custom_id="verification_cancel"
    )
    async def cancel_button(self, interaction, button):
        allowed_roles = [
            VERIFICATION_TEAM_ROLE_ID,
            ADMIN_ROLE_ID
        ]
        
        is_staff = interaction.user.id == OWNER_ID or any(role.id in allowed_roles for role in interaction.user.roles)
        is_applicant = interaction.user.id == self.member.id

        # Catch-all just in case someone slips through the interaction_check
        if not is_applicant and not is_staff:
            return await interaction.response.send_message(
                "❌🪲 You do not have permission to cancel this verification request. If you're seeing this, it is an error! Please inform staff!",
                ephemeral=True
            )

        # Response for the applicant
        if is_applicant:
            await interaction.response.send_message(
                "⚠️ Are you sure you want to cancel your verification request? You can reapply for an application later.",
                view=CancelConfirmView(self),
                ephemeral=True
            )
        # Response for staff/owner
        else:
            await interaction.response.send_message(
                f"⚠️ **Staff Action:** Are you sure you want to forcibly cancel {self.member.display_name}'s verification request?",
                view=CancelConfirmView(self),
                ephemeral=True
            )

    async def cancel_application(self, interaction):
        lock = self.cog.get_application_lock(interaction.guild.id, self.member.id)
        async with lock:
            return await self._cancel_application_locked(interaction)

    async def _cancel_application_locked(self, interaction):
        guild = interaction.guild
        thread = interaction.channel
        is_applicant = interaction.user.id == self.member.id

        # Apply 30-minute cooldown only if applicant cancels
        if is_applicant:
            set_cooldown(self.member.id, 0.5, reason="cancellation")

        try:
            refreshed_member = await guild.fetch_member(self.member.id)
            pending_role = guild.get_role(PENDING_VERIFICATION_ROLE_ID)

            if pending_role and pending_role in refreshed_member.roles:
                await refreshed_member.remove_roles(pending_role)

            try:
                await refreshed_member.send("🛑 Your verification request has been cancelled.")
            except:
                pass
            
            if is_applicant:
                cancellation_text = f"🛑 {refreshed_member.mention} cancelled their verification request."
            else:
                cancellation_text = f"🛑 Verification request for {refreshed_member.mention} was cancelled by staff ({interaction.user.mention})."
        except discord.NotFound:
            cancellation_text = "🛑 The verification request was cancelled, but the user is no longer in the server."

        await interaction.response.edit_message(
            content="🛑 Verification request cancelled.",
            view=None
        )

        await thread.send(cancellation_text)
        await thread.edit(archived=True, locked=True)

class VerificationDropdown(Select):
    def __init__(self, cog):
        self.cog = cog

        options = [
            discord.SelectOption(
                label="18+ Verified",
                description="Gain the 18+ verified role.",
                emoji="🔞",
                value="18plus"
            ),
            discord.SelectOption(
                label="NSFW Access",
                description="Gain access to NSFW channels.",
                emoji="🌶️",
                value="nsfw"
            ),
            discord.SelectOption(
                label="NSFW+ Access",
                description="Gain access to 'spicier' NSFW channels.",
                emoji="🔥",
                value="nsfw_plus"
            )
        ]

        super().__init__(
            placeholder="Choose a verification type...",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="verification_dropdown"
        )

    async def callback(self, interaction: discord.Interaction):
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return await interaction.response.send_message(
                "❌ This action can only be performed in a server.",
                ephemeral=True
            )

        guild = interaction.guild
        member = interaction.user

        lock = self.cog.get_application_lock(guild.id, member.id)
        if lock.locked():
            return await interaction.response.send_message(
                "⚠️ You already have a verification request being created. Please wait a moment.",
                ephemeral=True
            )

        async with lock:
            try:
                return await self._callback_locked(interaction)
            except Exception as e:
                print(f"[VERIFICATION CREATE ERROR] {e}")
                pending_role = guild.get_role(PENDING_VERIFICATION_ROLE_ID)
                if pending_role and pending_role in member.roles:
                    try:
                        await member.remove_roles(
                            pending_role,
                            reason="Verification application creation failed"
                        )
                    except discord.HTTPException:
                        pass

                if interaction.response.is_done():
                    await interaction.followup.send(
                        "❌ I couldn't create your verification request. No application was finalized; please try again in a moment.",
                        ephemeral=True
                    )
                else:
                    await interaction.response.send_message(
                        "❌ I couldn't create your verification request. No application was created; please try again in a moment.",
                        ephemeral=True
                    )

    async def _callback_locked(self, interaction: discord.Interaction):
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return await interaction.response.send_message(
                "❌ This action can only be performed in a server.",
                ephemeral=True
            )

        guild = interaction.guild
        member = interaction.user

        # Cooldown check with reason
        current_time = time.time()
        cooldown_end, reason = get_cooldown(member.id)

        if current_time < cooldown_end:
            reason_text = "a recent denial" if reason == "denial" else "cancelling your previous request"
            return await interaction.response.send_message(
                f"❌ You are on a cooldown due to {reason_text}. You can apply again <t:{int(cooldown_end)}:R>.",
                ephemeral=True
            )

        level_10_role = guild.get_role(LEVEL_10_ROLE_ID)

        # Check if user has Level 10 role or higher (defaults to True if role ID is missing/invalid)
        has_required_level = True if not level_10_role else False
        if level_10_role:
            for role in member.roles:
                if role.position >= level_10_role.position:
                    has_required_level = True
                    break

        if not has_required_level:
            return await interaction.response.send_message(
                "❌ You must be level 10 (Stellar Specialist) or higher to apply for NSFW and NSFW+ access.",
                ephemeral=True
            )

        await interaction.response.defer(ephemeral=True)

        pending_role = guild.get_role(PENDING_VERIFICATION_ROLE_ID)

        if pending_role is None:
            return await interaction.followup.send(
                "⚠️ The verification system is missing its Pending Verification role. Please contact staff.",
                ephemeral=True
            )

        if pending_role in member.roles:
            return await interaction.followup.send(
                "⚠️ You already have an active verification request. Please use your existing verification thread.",
                ephemeral=True
            )

        await member.add_roles(pending_role, reason="Started verification application")

        application_key = self.values[0]
        application_name = APPLICATION_TYPES[application_key]["label"]

        verification_channel = guild.get_channel(VERIFICATION_CHANNEL_ID)
        if verification_channel is None:
            try:
                verification_channel = await guild.fetch_channel(VERIFICATION_CHANNEL_ID)
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                await member.remove_roles(pending_role, reason="Verification channel unavailable")
                return await interaction.followup.send(
                    "⚠️ The verification channel could not be found or accessed. Please contact staff.",
                    ephemeral=True
                )

        if not isinstance(verification_channel, discord.TextChannel):
            await member.remove_roles(pending_role, reason="Verification channel invalid")
            return await interaction.followup.send(
                "⚠️ The verification channel is not a text channel. Please contact staff.",
                ephemeral=True
            )

        request_message = await verification_channel.send(
            f"<@&{VERIFICATION_TEAM_ROLE_ID}> <@{OWNER_ID}> <@&{ADMIN_ROLE_ID}>\n"
            f"**New Verification Request**\n\n"
            f"**User:** {member.mention}\n"
            f"**Application:** {application_name}\n\n"
            f"Open the attached thread to review this request."
        )

        safe_name = member.display_name.lower().replace(" ", "-")
        thread = await request_message.create_thread(
            name=f"verification-{safe_name}",
            auto_archive_duration=1440
        )

        await thread.add_user(member)

        await interaction.followup.send(
            f"✅ Your verification thread has been created. A staff member will be with you shortly: {thread.mention}",
            ephemeral=True
        )

        try:
            await member.send(
                f"✅ Your **{application_name}** request has been opened in **{guild.name}**.\n\n"
                f"Please continue in your verification thread here: {thread.mention}\n\n"
                "A verification team member will review your request as soon as possible."
            )
        except discord.Forbidden:
            await interaction.followup.send(
                "⚠️ I couldn't DM you. Please check your Discord privacy settings, but your verification thread was still created.",
                ephemeral=True
            )
        except Exception as e:
            print(f"Verification DM failed: {e}")

        await thread.send(
            f"Welcome {member.mention}!\n\n"
            f"Please answer the questions below and upload your verification images here.\n\n"
            f"⚠️ **Cover sensitive information. Only DOB and photo should remain visible!**"
        )

        questions = [
            "1. Are you 18 years or older?",
            "2. Have you read our server rules?",
            (
                "3. Please provide a valid form of ID for verification, such as an ID, driver's license, "
                "passport, or another document that clearly shows your age and photo.\n\n"
                "Make sure your DOB and photo are visible. Take a selfie holding the ID near your face, "
                "and also hold a piece of paper with your current Discord username written on it. "
                "This helps confirm the photo belongs to you and was not taken from somewhere online.\n\n"
                "We do **NOT** allow ID numbers, addresses, or other sensitive details to be shown for your safety. "
                "Please edit or cover those details before uploading.\n\n"
                "-# *(The ID photo process is reviewed manually by staff for safety reasons. We do **not** keep photos on file; they are removed after acceptance or denial.)*"
            ),
            "4. Please upload your verification images here. These are reviewed by our staff team, not by a bot.",
            "5. By applying for this application, you confirm that you understand the content in those channels may be explicit and is intended for **adults only.**",
            "6. If you are applying for NSFW+ access, you are stating that you understand that the content is more explicit than the standard NSFW channels.",
            "7. By applying for this application, you agree to follow all server rules and guidelines. Any violation may result in removal of NSFW access by gaining the `On Watchlist` role.",
            "8. Please note that if you are applying on desktop, and later using an iOS device, that they restrict NSFW content by default, and our server is age-restricted. You will need to use a desktop or Android device to view NSFW content, or activate the option in settings to allow it by going to Settings > Messaging Permissions > Allow access to age-restricted servers on iOS.\n\n",
            "If you do not agree to these conditions, please cancel the application now. You can reapply later if you change your mind."
        ]

        await thread.send("\n".join(questions))

        review_view = VerificationReviewView(self.cog, member, application_key)
        review_message = await thread.send(
            "Staff review controls:",
            view=review_view
        )
        self.cog.register_review_view(review_view, review_message.id)

class VerificationPanelView(View):
    def __init__(self, cog):
        super().__init__(timeout=None)

        self.add_item(
            VerificationDropdown(cog)
        )

class Verification(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._application_locks = {}
        self._review_view_keys = set()

        self.bot.add_view(
            VerificationPanelView(self)
        )

    def get_application_lock(self, guild_id, user_id):
        key = (guild_id, user_id)
        if key not in self._application_locks:
            self._application_locks[key] = asyncio.Lock()
        return self._application_locks[key]

    def register_review_view(self, view, message_id):
        if message_id not in self._review_view_keys:
            self.bot.add_view(view, message_id=message_id)
            self._review_view_keys.add(message_id)

    async def restore_review_views(self):
        labels = {
            "Accept": "accept",
            "Accept w/ Reason": "accept_reason",
            "Deny": "deny",
            "Deny w/ Reason": "deny_reason",
            "Cancel Application": "cancel",
        }
        app_by_label = {v["label"]: k for k, v in APPLICATION_TYPES.items()}
        channel = self.bot.get_channel(VERIFICATION_CHANNEL_ID)
        if channel is None:
            try:
                # Fetch directly by ID instead of depending on bot.guilds/cache
                # during startup. This works even before guild caches are ready.
                channel = await self.bot.fetch_channel(VERIFICATION_CHANNEL_ID)
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                channel = None

        if channel is None:
            print("[VERIFICATION] Could not restore review views: verification channel unavailable.")
            return

        for thread in getattr(channel, "threads", []):
            try:
                starter = await channel.fetch_message(thread.id)
                user_match = re.search(r"\*\*User:\*\*\s*<@!?(\d+)>", starter.content or "")
                app_match = re.search(r"\*\*Application:\*\*\s*(.+)", starter.content or "")
                if not user_match or not app_match:
                    continue
                application_key = app_by_label.get(app_match.group(1).strip())
                if application_key is None:
                    continue
                user_id = int(user_match.group(1))
                member = thread.guild.get_member(user_id)
                if member is None:
                    try:
                        member = await thread.guild.fetch_member(user_id)
                    except (discord.NotFound, discord.HTTPException):
                        continue

                review_message = None
                async for message in thread.history(limit=25, oldest_first=False):
                    if message.content == "Staff review controls:" and message.components:
                        review_message = message
                        break
                if review_message is None:
                    continue

                custom_ids = {}
                for row in review_message.components:
                    for component in row.children:
                        label = getattr(component, "label", None)
                        key = labels.get(label) if isinstance(label, str) else None
                        component_custom_id = getattr(component, "custom_id", None)
                        if key and isinstance(component_custom_id, str):
                            custom_ids[key] = component_custom_id
                if len(custom_ids) != 5:
                    continue

                view = VerificationReviewView(self, member, application_key, custom_ids)
                self.register_review_view(view, review_message.id)
                print(f"[VERIFICATION] Restored review controls for {member} in thread {thread.id}.")
            except (discord.NotFound, discord.Forbidden, discord.HTTPException) as e:
                print(f"[VERIFICATION] Could not restore thread {thread.id}: {e}")
            except Exception as e:
                print(f"[VERIFICATION] Unexpected restore error for thread {thread.id}: {e}")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def sendverificationpanel(self, ctx):
        embed = discord.Embed(
            title="🔞 Verification Center",
            description=(
                "Select the type of verification you want below.\n\n"
                "Verification is manually reviewed by staff.\n"
                "Please follow all instructions carefully!\n\n"
                "**Please note: You must be level 10 (Stellar Specialist) or higher to apply for NSFW and NSFW+ access.**"
            ),
            color=discord.Color.red()
        )

        await ctx.send(
            embed=embed,
            view=VerificationPanelView(self)
        )

    async def create_thread_transcript(self, thread):
        messages = []

        async for message in thread.history(limit=None, oldest_first=True):
            content = message.content or ""

            if message.attachments:
                attachments = "\n".join(a.url for a in message.attachments)
                content += f"\n[Attachments]\n{attachments}"

            messages.append(
                f"[{message.created_at}] {message.author}: {content}"
            )

        transcript_text = "\n\n".join(messages)
        file_name = f"transcript-{thread.id}.txt"

        with open(file_name, "w", encoding="utf-8") as f:
            f.write(transcript_text)

        return file_name

    async def finish_verification(self, interaction, member, application_key, approved, reason):
        lock = self.get_application_lock(interaction.guild.id, member.id)
        async with lock:
            if getattr(interaction.channel, "locked", False) or getattr(interaction.channel, "archived", False):
                return await interaction.followup.send(
                    "ℹ️ This verification request has already been processed.",
                    ephemeral=True
                )
            return await self._finish_verification_locked(
                interaction, member, application_key, approved, reason
            )

    async def _finish_verification_locked(self, interaction, member, application_key, approved, reason):

        guild = interaction.guild

        log_channel = guild.get_channel(VERIFICATION_LOG_CHANNEL_ID)
        if log_channel is None:
            try:
                log_channel = await guild.fetch_channel(VERIFICATION_LOG_CHANNEL_ID)
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                log_channel = None

        thread = interaction.channel

        if approved:
            roles_to_add = APPLICATION_TYPES[
                application_key
            ]["roles"]

            roles = []
            missing_roles = []

            for role_id in roles_to_add:
                role = guild.get_role(role_id)
                if role is None or (guild.me and guild.me.top_role <= role):
                    missing_roles.append(role_id)
                else:
                    roles.append(role)

            if missing_roles:
                return await interaction.followup.send(
                    "❌ This application cannot be approved because one or more required verification roles are missing or below Enceladus' role hierarchy. Please contact the server owner.",
                    ephemeral=True
                )

            added_roles = []
            try:
                for role in roles:
                    if role not in member.roles:
                        await member.add_roles(role, reason=f"Approved {application_key} verification")
                        added_roles.append(role)
            except discord.HTTPException as e:
                for role in reversed(added_roles):
                    try:
                        await member.remove_roles(role, reason="Rollback failed verification approval")
                    except discord.HTTPException:
                        pass
                print(f"[VERIFICATION ROLE ERROR] {e}")
                return await interaction.followup.send(
                    "❌ I couldn't safely assign all required verification roles. No approval was finalized; please try again or contact staff.",
                    ephemeral=True
                )

            message = (
                f"✅ You have been approved for **{APPLICATION_TYPES[application_key]['label']}**."
            )

            if reason:
                message += f"\n\nReason:\n{reason}"

            try:
                await member.send(message)
            except:
                pass

            await interaction.followup.send(
                f"✅ {member.mention} approved.")

            if log_channel:
                await log_channel.send(
                    f"✅ {member.mention} approved for **{APPLICATION_TYPES[application_key]['label']}**"
                )

        else:
            message = (
                f"❌ Your verification request for **{APPLICATION_TYPES[application_key]['label']}** was denied."
            )

            if reason:
                message += f"\n\nReason:\n{reason}"

            try:
                await member.send(message)
            except:
                pass

            await interaction.followup.send(
                f"❌ {member.mention} denied."
            )

            if log_channel:
                await log_channel.send(
                    f"❌ {member.mention} denied for **{APPLICATION_TYPES[application_key]['label']}**"
                )

            # Apply 48-hour denial cooldown inside the else block
            set_cooldown(member.id, 48, reason="denial")

        try:
            member = await guild.fetch_member(member.id)
            pending_role = guild.get_role(PENDING_VERIFICATION_ROLE_ID)

            if pending_role and pending_role in member.roles:
                await member.remove_roles(pending_role)
        except discord.NotFound:
            pass

        transcript_file = None
        try:
            transcript_file = await self.create_thread_transcript(thread)
            if log_channel:
                await log_channel.send(
                    content=f"📜 Transcript for {thread.name}:",
                    file=discord.File(transcript_file)
                )
        except discord.HTTPException as e:
            print(f"[VERIFICATION TRANSCRIPT ERROR] {e}")
        finally:
            if transcript_file:
                try:
                    os.remove(transcript_file)
                except OSError:
                    pass

        await thread.edit(
            archived=True,
            locked=True
        )

async def setup(bot):
    cog = Verification(bot)
    await bot.add_cog(cog)

    async def restore_after_ready():
        try:
            await bot.wait_until_ready()
            await cog.restore_review_views()
        except asyncio.CancelledError:
            raise
        except Exception as e:
            print(f"[VERIFICATION] Review-view restoration failed: {e}")

    # setup_hook runs before the bot is fully ready, so restoration must wait
    # until Discord has finished establishing the guild/channel state.
    asyncio.create_task(restore_after_ready())
