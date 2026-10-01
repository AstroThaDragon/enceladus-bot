import os
import re
import traceback
from datetime import datetime, timezone

import discord


# Set ERROR_LOG_CHANNEL_ID in Railway/environment variables to the channel where
# Enceladus should post its error reports.
ERROR_LOG_CHANNEL_ID = os.getenv("ERROR_LOG_CHANNEL_ID")


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


def _format_traceback(error, limit=3500):
    """Return a bounded traceback suitable for a Discord embed."""
    try:
        tb = "".join(traceback.format_exception(type(error), error, error.__traceback__))
    except Exception:
        tb = repr(error)

    return _safe_text(tb, limit=limit) or "No traceback available."


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


async def send_error_log(
    bot,
    error,
    *,
    ctx=None,
    interaction=None,
    source="Unknown",
    context=None,
):
    """Send one centralized error report to Discord and Railway's console."""
    try:
        now = datetime.now(timezone.utc)
        info = _get_context_info(ctx=ctx, interaction=interaction)
        error_type = type(error).__name__
        error_message = _safe_text(error, 1500)
        traceback_text = _format_traceback(error)

        print(
            "[ENCELADUS ERROR] "
            f"{now.isoformat()} | source={source} | "
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
            return

        embed = discord.Embed(
            title="🚨 Enceladus Error",
            color=discord.Color.red(),
            timestamp=now,
        )
        embed.add_field(
            name="Command",
            value=f"`{_safe_text(info['command'], 256)}`",
            inline=False,
        )
        embed.add_field(name="User", value=_safe_text(info["user"], 1024), inline=True)
        embed.add_field(name="Server", value=_safe_text(info["server"], 1024), inline=True)
        embed.add_field(name="Channel", value=_safe_text(info["channel"], 1024), inline=True)
        embed.add_field(name="Source", value=f"`{_safe_text(source, 256)}`", inline=True)
        embed.add_field(name="Error Type", value=f"`{_safe_text(error_type, 256)}`", inline=True)
        embed.add_field(
            name="Error",
            value=f"```text\n{error_message[:1000]}\n```",
            inline=False,
        )

        if context:
            embed.add_field(
                name="Context",
                value=_safe_text(context, 1000),
                inline=False,
            )

        embed.add_field(
            name="Traceback",
            value=f"```py\n{traceback_text}\n```",
            inline=False,
        )
        embed.set_footer(text="Centralized Enceladus error logging")

        try:
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
    await send_error_log(
        bot, error, ctx=ctx, interaction=interaction,
        source=f"Explicit Catch: {source}", context=context,
    )


async def log_command_error(bot, ctx, error):
    await send_error_log(bot, error, ctx=ctx, source="Prefix/Hybrid Command")


async def log_app_command_error(bot, interaction, error):
    await send_error_log(bot, error, interaction=interaction, source="Application Command")


async def log_event_error(bot, event_method, error, *, context=None):
    await send_error_log(
        bot,
        error,
        source=f"Event: {event_method}",
        context=context,
    )


async def log_task_error(bot, task_name, error, *, context=None):
    await send_error_log(
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

    await send_error_log(
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

        await log_ui_error(
            bot,
            interaction,
            error,
            item=item,
            ui_type="View",
        )

    async def modal_on_error(modal, interaction, error):
        bot = getattr(interaction, "client", None)
        if bot is None:
            print(
                "[ERROR LOGGER] UI Modal error has no interaction.client: "
                f"{type(error).__name__}: {error}"
            )
            return

        await log_ui_error(
            bot,
            interaction,
            error,
            ui_type="Modal",
        )

    discord.ui.View.on_error = view_on_error
    discord.ui.Modal.on_error = modal_on_error
    _UI_HANDLERS_INSTALLED = True
