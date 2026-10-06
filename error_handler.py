import hashlib
import os
import re
import secrets
import traceback
from datetime import datetime, timezone

import discord


# Set ERROR_LOG_CHANNEL_ID in Railway/environment variables to the channel where
# Enceladus should post its error reports.
ERROR_LOG_CHANNEL_ID = os.getenv("ERROR_LOG_CHANNEL_ID")
ERROR_ALERT_ROLE_ID = os.getenv("ERROR_ALERT_ROLE_ID")


def _generate_error_id():
    """Generate a short, unique ID that can be given to a member for support."""
    return f"ENC-{secrets.token_hex(6).upper()}"


def _normalize_for_fingerprint(text):
    """Remove unstable values so equivalent errors can share a fingerprint."""
    text = str(text)
    text = re.sub(r"0x[0-9a-fA-F]+", "<addr>", text)
    text = re.sub(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F-]{27,}\b", "<uuid>", text)
    text = re.sub(r"\b\d{15,}\b", "<id>", text)
    return text.strip()


def _get_error_fingerprint(source, info, error_type, error_message):
    """Return a stable short fingerprint for grouping repeated errors."""
    fingerprint_source = "|".join(
        (
            _normalize_for_fingerprint(source),
            _normalize_for_fingerprint(info.get("command", "Unknown command")),
            _normalize_for_fingerprint(error_type),
            _normalize_for_fingerprint(error_message),
        )
    )
    digest = hashlib.sha256(fingerprint_source.encode("utf-8", "replace")).hexdigest()
    return f"FP-{digest[:10].upper()}"


def _safe_text(value, limit=1000):
    """Turn a value into safe, bounded text for Discord logs."""
    if value is None:
        return "Unknown"

    text = str(value)
    text = re.sub(r"```", "[triple-backtick]", text)

    for name in ("DISCORD_TOKEN", "DEV_TOKEN", "NASA_API_KEY"):
        secret = os.getenv(name)
        if secret:
            text = text.replace(secret, "[REDACTED]")

    if len(text) > limit:
        text = text[: limit - 3] + "..."
    return text


def _safe_embed_field(value, limit=1024):
    """Return text guaranteed not to exceed Discord's embed field-value limit."""
    text = str(value) if value is not None else "Unknown"
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def _get_context_info(ctx=None, interaction=None):
    """Collect command/user/server/channel information without assuming it exists."""
    source = interaction or ctx
    user = getattr(source, "user", None) or getattr(source, "author", None)
    guild = getattr(source, "guild", None)
    channel = getattr(source, "channel", None)

    command = (
        getattr(interaction, "command", None)
        if interaction is not None
        else getattr(ctx, "command", None) if ctx else None
    )
    command_name = getattr(command, "qualified_name", None) or getattr(command, "name", None)

    return {
        "command": command_name or "Unknown command",
        "user": (
            f"{getattr(user, 'display_name', getattr(user, 'name', 'Unknown'))}"
            f" ({getattr(user, 'id', 'Unknown')})"
            if user else "Unknown user"
        ),
        "server": (
            f"{getattr(guild, 'name', 'Unknown')} ({getattr(guild, 'id', 'Unknown')})"
            if guild else "Direct Message / Unknown Server"
        ),
        "channel": (
            f"#{getattr(channel, 'name', 'Unknown')} ({getattr(channel, 'id', 'Unknown')})"
            if channel else "Unknown channel"
        ),
    }


def _format_traceback(error, limit=900):
    """Return a bounded traceback with room for Discord code-fence formatting."""
    try:
        tb = "".join(traceback.format_exception(type(error), error, error.__traceback__))
    except Exception:
        tb = repr(error)

    return _safe_text(tb, limit=limit) or "No traceback available."


async def _get_error_alert_role(bot):
    """Resolve the configured Discord role used for High/Critical alerts."""
    if not ERROR_ALERT_ROLE_ID:
        return None

    try:
        role_id = int(ERROR_ALERT_ROLE_ID)
    except ValueError:
        print("[ERROR LOGGER] ERROR_ALERT_ROLE_ID is not a valid integer.")
        return None

    for guild in getattr(bot, "guilds", []):
        role = guild.get_role(role_id)
        if role is not None:
            return role

    print(f"[ERROR LOGGER] Could not find alert role {role_id} in any bot guild.")
    return None


async def _get_error_channel(bot):
    """Resolve the configured Discord error-log channel."""
    if not ERROR_LOG_CHANNEL_ID:
        return None

    try:
        channel_id = int(ERROR_LOG_CHANNEL_ID)
    except ValueError:
        print("[ERROR LOGGER] ERROR_LOG_CHANNEL_ID is not a valid integer.")
        return None

    channel = bot.get_channel(channel_id)
    if channel is not None:
        return channel

    try:
        return await bot.fetch_channel(channel_id)
    except Exception as exc:
        print(
            f"[ERROR LOGGER] Could not access error-log channel {channel_id}: "
            f"{type(exc).__name__}: {exc}"
        )
        return None



def _determine_severity(source, error):
    """Assign a practical attention level based on where the error occurred."""
    source_text = str(source).lower()
    # Bot-wide startup/synchronization failures deserve immediate attention.
    if "setup_hook" in source_text or "startup" in source_text:
        return "🔴 Critical"

    # Uncaught event failures and background-task failures can affect more than
    # one user, so they should be investigated before ordinary command errors.
    if source_text.startswith("event:") or source_text.startswith("background task:"):
        return "🟠 High"

    # Individual commands, UI interactions, and explicit catches are normally
    # isolated to one operation/user.
    if (
        "command" in source_text
        or "ui interaction" in source_text
        or "explicit catch" in source_text
    ):
        return "🟡 Medium"

    # Anything that doesn't match a known category is still recorded, but gets
    # the lowest attention level rather than being treated as system-critical.
    return "🟢 Low"


async def send_error_log(
    bot,
    error,
    *,
    ctx=None,
    interaction=None,
    source="Unknown",
    context=None,
):
    """Send one centralized error report and return its member-safe Error ID."""
    error_id = _generate_error_id()

    try:
        now = datetime.now(timezone.utc)
        info = _get_context_info(ctx=ctx, interaction=interaction)
        error_type = type(error).__name__
        error_message = _safe_text(error, 1500)
        traceback_text = _format_traceback(error)
        severity = _determine_severity(source, error)
        fingerprint = _get_error_fingerprint(
            source, info, error_type, error_message
        )

        print(
            "[ENCELADUS ERROR] "
            f"{now.isoformat()} | error_id={error_id} | fingerprint={fingerprint} | "
            f"severity={severity} | source={source} | "
            f"command={info['command']} | user={info['user']} | "
            f"server={info['server']} | channel={info['channel']} | "
            f"{error_type}: {error_message}"
        )
        print(traceback_text)

        channel = await _get_error_channel(bot)
        if channel is None:
            if not ERROR_LOG_CHANNEL_ID:
                print(
                    "[ERROR LOGGER] ERROR_LOG_CHANNEL_ID is not configured; "
                    "Discord error reporting is disabled."
                )
            return error_id

        alert_role = None
        if severity in ("🟠 High", "🔴 Critical"):
            alert_role = await _get_error_alert_role(bot)

        severity_colors = {
            "🟢 Low": discord.Color.green(),
            "🟡 Medium": discord.Color.yellow(),
            "🟠 High": discord.Color.orange(),
            "🔴 Critical": discord.Color.red(),
        }

        embed = discord.Embed(
            title="🚨 Enceladus Error",
            color=severity_colors.get(severity, discord.Color.red()),
            timestamp=now,
        )
        embed.add_field(
            name="Severity",
            value=f"**{severity}**",
            inline=False,
        )
        embed.add_field(
            name="Error ID",
            value=f"`{error_id}`",
            inline=True,
        )
        embed.add_field(
            name="Fingerprint",
            value=f"`{fingerprint}`",
            inline=True,
        )
        embed.add_field(
            name="Command",
            value=f"`{_safe_text(info['command'], 256)}`",
            inline=False,
        )
        embed.add_field(name="User", value=_safe_embed_field(_safe_text(info["user"], 1000)), inline=True)
        embed.add_field(name="Server", value=_safe_embed_field(_safe_text(info["server"], 1000)), inline=True)
        embed.add_field(name="Channel", value=_safe_embed_field(_safe_text(info["channel"], 1000)), inline=True)
        embed.add_field(name="Source", value=f"`{_safe_text(source, 256)}`", inline=True)
        embed.add_field(name="Error Type", value=f"`{_safe_text(error_type, 256)}`", inline=True)
        embed.add_field(
            name="Error",
            value=_safe_embed_field(f"```text\\n{error_message[:900]}\\n```"),
            inline=False,
        )

        if context:
            embed.add_field(
                name="Context",
                value=_safe_embed_field(_safe_text(context, 1000)),
                inline=False,
            )

        embed.add_field(
            name="Traceback",
            value=_safe_embed_field(f"```py\\n{traceback_text}\\n```"),
            inline=False,
        )
        embed.set_footer(text="Centralized Enceladus error logging")

        try:
            if alert_role is not None:
                await channel.send(
                    content=alert_role.mention,
                    embed=embed,
                    allowed_mentions=discord.AllowedMentions(roles=True),
                )
            else:
                await channel.send(embed=embed)
        except Exception as send_error:
            print(
                "[ERROR LOGGER] Failed to send Discord error report: "
                f"{type(send_error).__name__}: {send_error}"
            )

    except Exception as logger_error:
        print(
            "[ERROR LOGGER] Error while preparing error report: "
            f"{type(logger_error).__name__}: {logger_error}"
        )

    return error_id


async def send_member_error_message(target, error_id):
    """Give the affected member a safe support ID without exposing diagnostics."""
    message = (
        "Something went wrong while processing your request.\n"
        f"**Error ID:** `{error_id}`\n"
        "Please give this ID to staff when reporting the issue."
    )

    try:
        if isinstance(target, discord.Interaction):
            if target.response.is_done():
                await target.followup.send(message, ephemeral=True)
            else:
                await target.response.send_message(message, ephemeral=True)
        else:
            await target.send(message)
    except Exception as send_error:
        print(
            "[ERROR LOGGER] Failed to send member-facing error ID: "
            f"{type(send_error).__name__}: {send_error}"
        )


async def log_caught_error(
    bot,
    error,
    source,
    *,
    ctx=None,
    interaction=None,
    context=None,
):
    """Log an exception that was explicitly caught instead of re-raised."""
    return await send_error_log(
        bot, error, ctx=ctx, interaction=interaction,
        source=f"Explicit Catch: {source}", context=context,
    )


async def log_command_error(bot, ctx, error):
    # Missing required arguments are normal command-usage mistakes, not bot
    # failures. Individual commands can provide their own friendly error
    # handlers, so do not duplicate those mistakes in the centralized log.
    if isinstance(error, discord.ext.commands.MissingRequiredArgument):
        return None

    # Discord formatting such as "-#" can be interpreted by the prefix
    # command handler as a request to run a command literally named "#".
    # This is harmless user input, not an Enceladus error worth logging.
    if type(error).__name__ == "CommandNotFound" and getattr(ctx, "invoked_with", "") == "#":
        return None

    return await send_error_log(bot, error, ctx=ctx, source="Prefix/Hybrid Command")


async def log_app_command_error(bot, interaction, error):
    return await send_error_log(bot, error, interaction=interaction, source="Application Command")


async def log_event_error(bot, event_method, error, *, context=None):
    return await send_error_log(
        bot,
        error,
        source=f"Event: {event_method}",
        context=context,
    )


async def log_task_error(bot, task_name, error, *, context=None):
    return await send_error_log(
        bot,
        error,
        source=f"Background Task: {task_name}",
        context=context,
    )


async def log_ui_error(bot, interaction, error, *, item=None, ui_type="View"):
    """Log an exception raised while processing a Discord UI interaction."""
    component = "Unknown component"
    component_type = "Unknown"
    if item is not None:
        component_type = type(item).__name__
        custom_id = getattr(item, "custom_id", None)
        label = getattr(item, "label", None)
        placeholder = getattr(item, "placeholder", None)

        details = []
        if label:
            details.append(f"label={label!r}")
        if custom_id:
            details.append(f"custom_id={custom_id!r}")
        if placeholder:
            details.append(f"placeholder={placeholder!r}")

        component = component_type
        if details:
            component += f" ({', '.join(details)})"

    context = f"UI Type: {ui_type}\nComponent: {component}"

    return await send_error_log(
        bot,
        error,
        interaction=interaction,
        source=f"UI Interaction: {ui_type}",
        context=context,
    )


# Discord.py normally handles View/Modal callback exceptions through these
# methods. Installing our centralized versions here means every current and
# future View/Modal in the bot is covered without wrapping every callback.
_UI_HANDLERS_INSTALLED = False


def install_ui_error_handlers():
    """Route Discord UI exceptions through the centralized error logger."""
    global _UI_HANDLERS_INSTALLED
    if _UI_HANDLERS_INSTALLED:
        return

    async def view_on_error(view, interaction, error, item):
        bot = getattr(interaction, "client", None)
        if bot is None:
            print(
                "[ERROR LOGGER] UI View error has no interaction.client: "
                f"{type(error).__name__}: {error}"
            )
            return

        error_id = await log_ui_error(
            bot,
            interaction,
            error,
            item=item,
            ui_type="View",
        )
        await send_member_error_message(interaction, error_id)

    async def modal_on_error(modal, interaction, error):
        bot = getattr(interaction, "client", None)
        if bot is None:
            print(
                "[ERROR LOGGER] UI Modal error has no interaction.client: "
                f"{type(error).__name__}: {error}"
            )
            return

        error_id = await log_ui_error(
            bot,
            interaction,
            error,
            ui_type="Modal",
        )
        await send_member_error_message(interaction, error_id)

    discord.ui.View.on_error = view_on_error
    discord.ui.Modal.on_error = modal_on_error
    _UI_HANDLERS_INSTALLED = True
