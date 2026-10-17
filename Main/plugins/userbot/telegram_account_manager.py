# Copyright (C) 2021-present by Altruix@Github, < https://github.com/Altruix >.
#
# This file is part of < https://github.com/Altruix/Altruix > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/Altriux/Altruix/blob/main/LICENSE >
#
# All rights reserved.

from Main import Altruix
from telethon import functions, types
from Main.core.types import AltruixTelegramClient as Client, Message
from Main.utils.suppress import suppress_error


@Altruix.register_on_cmd(
    ["set", "modify", "profile", "account"],
    bot_mode_unsupported=True,
    cmd_help={
        "help": "Manage and change your Telegram account settings, profile, and privacy.",
        "example": "set -f John",
        "user_args": [
            {"arg": "f", "help": "Change your first name", "requires_input": True},
            {"arg": "l", "help": "Change your last name", "requires_input": True},
            {"arg": "name", "help": "Change both first and last name (-name First Last)", "requires_input": True},
            {"arg": "b", "help": "Change your bio / about (-b Text or -b clear)", "requires_input": True},
            {"arg": "u", "help": "Check and change your username (-u name or -u clear)", "requires_input": True},
            {"arg": "p", "help": "Set new profile picture (reply to image/photo)", "requires_input": False},
            {"arg": "dp", "help": "Delete current profile photo", "requires_input": False},
            {"arg": "s", "help": "View active login sessions", "requires_input": False},
            {"arg": "ts", "help": "Terminate all other active login sessions", "requires_input": False},
            {"arg": "ttl", "help": "View or set account self-destruct TTL (-ttl 180)", "requires_input": False},
            {"arg": "sensitive", "help": "Toggle sensitive/NSFW media display (-sensitive on|off)", "requires_input": True},
            {"arg": "archive", "help": "Toggle archive & mute new non-contact chats (-archive on|off)", "requires_input": True},
            {"arg": "signup", "help": "Toggle contact joined Telegram notifications (-signup on|off)", "requires_input": True},
            {"arg": "channel", "help": "Set or remove personal channel on profile (-channel @chan|id|off)", "requires_input": True},
            {"arg": "bday", "help": "Set or remove birthday (-bday DD MM [YYYY]|off)", "requires_input": True},
            {"arg": "privacy", "help": "View your account privacy rules and visibility settings", "requires_input": False},
        ],
    },
)
async def account_modify(c: Client, m: Message):
    msg = await m.handle_message("PROCESSING")
    args = m.user_args

    # 1. DEFAULT OVERVIEW: If no flags and no text provided, show a comprehensive Profile & Settings dashboard
    if not args and not m.user_input:
        me = getattr(c, "myself", None) or await c.get_me()
        user_full = None
        with suppress_error(msg="Fetch full user profile"):
            user_full = await c(functions.users.GetFullUserRequest(id=me.id))

        ttl_days = "Unknown"
        with suppress_error(msg="Fetch TTL"):
            ttl_res = await c(functions.account.GetAccountTTLRequest())
            ttl_days = f"{ttl_res.days} days"

        sess_count = "N/A"
        with suppress_error(msg="Fetch sessions count"):
            auth_res = await c(functions.account.GetAuthorizationsRequest())
            sess_count = str(len(auth_res.authorizations))

        sensitive_status = "Unknown"
        with suppress_error(msg="Fetch content settings"):
            c_res = await c(functions.account.GetContentSettingsRequest())
            sensitive_status = "Enabled" if getattr(c_res, "sensitive_enabled", False) else "Disabled"

        archive_status = "Unknown"
        with suppress_error(msg="Fetch global privacy"):
            g_res = await c(functions.account.GetGlobalPrivacySettingsRequest())
            archive_status = "Enabled" if getattr(g_res, "archive_and_mute_new_noncontact_peers", False) else "Disabled"

        signup_status = "Unknown"
        with suppress_error(msg="Fetch contact signup notifications"):
            s_res = await c(functions.account.GetContactSignUpNotificationRequest())
            signup_status = "Muted" if getattr(s_res, "silent", False) else "Active"

        about_text = getattr(user_full, "about", "") if user_full else ""
        first_name = me.first_name or ""
        last_name = me.last_name or ""
        username = f"@{me.username}" if me.username else "None"
        phone = f"+{me.phone}" if getattr(me, "phone", None) else "Hidden"
        premium_status = "Yes (Premium)" if getattr(me, "premium", False) else "No (Standard)"
        dc_id = getattr(getattr(c, "session", None), "dc_id", "Unknown")

        birthday_str = "None"
        if user_full and getattr(user_full, "birthday", None):
            b = user_full.birthday
            b_day = getattr(b, "day", None)
            b_month = getattr(b, "month", None)
            b_year = getattr(b, "year", None)
            if isinstance(b_day, int) and isinstance(b_month, int):
                y_str = f"/{b_year}" if isinstance(b_year, int) else ""
                birthday_str = f"{b_day:02d}/{b_month:02d}{y_str}"
            elif b_day is not None and b_month is not None:
                birthday_str = f"{b_day}/{b_month}"

        personal_channel_str = "None"
        p_chan_id = getattr(user_full, "personal_channel_id", None) if user_full else None
        if p_chan_id and isinstance(p_chan_id, (int, str)):
            personal_channel_str = f"<code>-100{p_chan_id}</code>"

        overview = (
            "<b>⚙️ Telegram Account Settings & Profile:</b>\n\n"
            "<b>👤 User Information:</b>\n"
            f"  • <b>Name:</b> <code>{first_name} {last_name}</code>\n"
            f"  • <b>Username:</b> <code>{username}</code>\n"
            f"  • <b>User ID:</b> <code>{me.id}</code>\n"
            f"  • <b>Phone:</b> <code>{phone}</code>\n"
            f"  • <b>Premium:</b> <i>{premium_status}</i>\n"
            f"  • <b>Data Center:</b> <code>DC {dc_id}</code>\n"
            f"  • <b>Bio:</b> <i>{about_text or 'None'}</i>\n"
            f"  • <b>Birthday:</b> <code>{birthday_str}</code>\n"
            f"  • <b>Personal Channel:</b> {personal_channel_str}\n\n"
            "<b>🔒 Security & Preferences:</b>\n"
            f"  • <b>Self-Destruct TTL:</b> <code>{ttl_days}</code>\n"
            f"  • <b>Active Sessions:</b> <code>{sess_count}</code>\n"
            f"  • <b>Sensitive Content (18+):</b> <code>{sensitive_status}</code>\n"
            f"  • <b>Auto-Archive Non-Contacts:</b> <code>{archive_status}</code>\n"
            f"  • <b>Contact Joined Alerts:</b> <code>{signup_status}</code>\n\n"
            f"<i>Modify using flags:</i> <code>{Altruix.user_command_handler}set -f &lt;name&gt;</code>, "
            f"<code>-l</code>, <code>-name</code>, <code>-b</code>, <code>-u</code>, <code>-p</code>, "
            f"<code>-dp</code>, <code>-s</code>, <code>-ts</code>, <code>-ttl</code>, <code>-sensitive</code>, "
            f"<code>-archive</code>, <code>-signup</code>, <code>-channel</code>, <code>-bday</code>, <code>-privacy</code>"
        )
        return await msg.edit_msg(overview)

    # 2. UPDATE FULL NAME: -name First Last
    if "name" in args or "-name" in args:
        if not m.user_input:
            return await msg.edit_msg("INPUT_REQUIRED")
        parts = m.user_input.split(" ", 1)
        fname = parts[0]
        lname = parts[1] if len(parts) > 1 else ""
        await c(functions.account.UpdateProfileRequest(first_name=fname, last_name=lname))
        full_name = f"{fname} {lname}".strip()
        return await msg.edit_msg(f"✅ Successfully updated profile name to: <b>{full_name}</b>")

    # 3. UPDATE FIRST NAME: -f First
    if "f" in args or "-f" in args:
        if not m.user_input:
            return await msg.edit_msg("INPUT_REQUIRED")
        fname = m.user_input
        await c(functions.account.UpdateProfileRequest(first_name=fname))
        return await msg.edit_msg("CHANGE", string_args=("FirstName", fname))

    # 4. UPDATE LAST NAME: -l Last
    if "l" in args or "-l" in args:
        if not m.user_input:
            return await msg.edit_msg("INPUT_REQUIRED")
        lname = m.user_input
        await c(functions.account.UpdateProfileRequest(last_name=lname))
        return await msg.edit_msg("CHANGE", string_args=("LastName", lname))

    # 5. UPDATE BIO / ABOUT: -b text or -b clear
    if "b" in args or "-b" in args:
        if not m.user_input:
            return await msg.edit_msg("INPUT_REQUIRED")
        bio = "" if m.user_input.strip().lower() in ("clear", "none", "off", "rm") else m.user_input
        await c(functions.account.UpdateProfileRequest(about=bio))
        return await msg.edit_msg(f"📝 Bio updated: <b>{bio or 'Cleared'}</b>")

    # 6. UPDATE USERNAME: -u username or -u clear
    if "u" in args or "-u" in args:
        if not m.user_input:
            return await msg.edit_msg("INPUT_REQUIRED")
        raw_u = m.user_input.replace("@", "").strip()
        if raw_u.lower() in ("clear", "none", "off", "rm"):
            await c(functions.account.UpdateUsernameRequest(username=""))
            return await msg.edit_msg("USERNAME_CLEARED")
        try:
            check = await c(functions.account.CheckUsernameRequest(username=raw_u))
            if not check:
                return await msg.edit_msg("USERNAME_TAKEN", string_args=(f"@{raw_u}",))
            await c(functions.account.UpdateUsernameRequest(username=raw_u))
            return await msg.edit_msg("USERNAME_UPDATED", string_args=(raw_u,))
        except errors.UsernameInvalidError:
            return await msg.edit_msg("USERNAME_INVALID")
        except errors.UsernameOccupiedError:
            return await msg.edit_msg("USERNAME_OCCUPIED", string_args=(raw_u,))

    # 7. UPDATE PROFILE PHOTO: -p (replying to photo)
    if "p" in args or "-p" in args:
        rm = m.reply_to_message or (await m.get_reply_message() if hasattr(m, "get_reply_message") else None)
        if not rm:
            return await msg.edit_msg("REPLY_REQUIRED")
        temp_dir = os.path.abspath("./temp")
        os.makedirs(temp_dir, exist_ok=True)
        temp_pic_path = os.path.join(temp_dir, f"temp_profile_{int(time.time() * 1000)}.jpg")
        pic = await c.download_media(rm, file=temp_pic_path)
        if not pic or not os.path.exists(pic):
            return await msg.edit_msg("404_FILE_NOT_FOUND")
        try:
            uploaded = await c.upload_file(pic)
            await c(functions.photos.UploadProfilePhotoRequest(file=uploaded))
            return await msg.edit_msg("CHNG_PHOTO")
        finally:
            if pic and os.path.exists(pic):
                os.remove(pic)

    # 8. DELETE PROFILE PHOTO: -dp
    if "dp" in args or "-dp" in args:
        photos_res = await c(functions.photos.GetUserPhotosRequest(user_id="me", offset=0, max_id=0, limit=1))
        if photos_res and photos_res.photos:
            p = photos_res.photos[0]
            await c(functions.photos.DeletePhotosRequest(
                id=[types.InputPhoto(id=p.id, access_hash=p.access_hash, file_reference=p.file_reference)]
            ))
            return await msg.edit_msg("PROFILE_PHOTO_REMOVED")
        return await msg.edit_msg("NO_PROFILE_PHOTO")

    # 9. SELF-DESTRUCT TTL: -ttl <days>
    if "ttl" in args or "-ttl" in args:
        if m.user_input and m.user_input.strip().isdigit():
            days = int(m.user_input.strip())
            valid_days = [30, 90, 180, 365, 548, 730]
            if days not in valid_days:
                closest = min(valid_days, key=lambda x: abs(x - days))
                days = closest
            await c(functions.account.SetAccountTTLRequest(ttl=types.AccountDaysTTL(days=days)))
            return await msg.edit_msg("TTL_UPDATED", string_args=(days,))
        ttl_res = await c(functions.account.GetAccountTTLRequest())
        return await msg.edit_msg(
            f"<b>Current Account Self-Destruct TTL:</b> <code>{ttl_res.days} days</code>\n\n"
            f"<i>To change:</i> <code>{Altruix.user_command_handler}set -ttl &lt;days&gt;</code> (30, 90, 180, 365, 548, 730)"
        )

    # 10. LIST ACTIVE SESSIONS: -s
    if "s" in args or "-s" in args:
        res = await c(functions.account.GetAuthorizationsRequest())
        sessions = res.authorizations
        text_ = f"<b>Active Login Sessions:</b> ({len(sessions)})\n\n"
        for session in sessions:
            current_tag = " <i>[Current]</i>" if getattr(session, "current", False) else ""
            text_ += (
                f"> <b>Device:</b> <code>{session.device_model} {session.platform} v{session.system_version}</code>{current_tag}\n"
                f"<b>App:</b> <code>{session.app_name} v{session.app_version}</code>\n"
                f"<b>Location:</b> <code>{session.country} - {session.region} ({session.ip})</code>\n\n"
            )
        text_ += f"<i>To terminate other sessions:</i> <code>{Altruix.user_command_handler}set -ts</code>"
        return await msg.edit_msg(text_)

    # 11. TERMINATE OTHER SESSIONS: -ts
    if "ts" in args or "-ts" in args:
        try:
            await c(functions.auth.ResetAuthorizationsRequest())
            return await msg.edit_msg("🔒 All other sessions terminated successfully.")
        except Exception as e:
            return await msg.edit_msg("SESSIONS_TERMINATE_FAILED", string_args=(str(e),))

    # 12. SENSITIVE CONTENT TOGGLE: -sensitive on|off
    if "sensitive" in args or "-sensitive" in args or "nsfw" in args or "-nsfw" in args:
        val_str = (m.user_input or "").strip().lower()
        if val_str in ("on", "true", "1", "enable"):
            await c(functions.account.SetContentSettingsRequest(sensitive_enabled=True))
            return await msg.edit_msg("🔞 Sensitive content filter disabled (showing 18+ content).")
        elif val_str in ("off", "false", "0", "disable"):
            await c(functions.account.SetContentSettingsRequest(sensitive_enabled=False))
            return await msg.edit_msg("🛡 Sensitive content filter enabled (filtering 18+ content).")
        else:
            c_res = await c(functions.account.GetContentSettingsRequest())
            curr = "Enabled (Showing 18+ content)" if getattr(c_res, "sensitive_enabled", False) else "Disabled (Filtering 18+ content)"
            return await msg.edit_msg(
                f"<b>Sensitive Content Status:</b> <code>{curr}</code>\n\n"
                f"<i>To change:</i> <code>{Altruix.user_command_handler}set -sensitive on|off</code>"
            )

    # 13. AUTO-ARCHIVE NON-CONTACTS: -archive on|off
    if "archive" in args or "-archive" in args:
        val_str = (m.user_input or "").strip().lower()
        if val_str in ("on", "true", "1", "enable"):
            await c(functions.account.SetGlobalPrivacySettingsRequest(
                settings=types.GlobalPrivacySettings(archive_and_mute_new_noncontact_peers=True)
            ))
            return await msg.edit_msg("📦 Auto-archive enabled for new non-contact chats.")
        elif val_str in ("off", "false", "0", "disable"):
            await c(functions.account.SetGlobalPrivacySettingsRequest(
                settings=types.GlobalPrivacySettings(archive_and_mute_new_noncontact_peers=False)
            ))
            return await msg.edit_msg("📦 Auto-archive disabled for new non-contact chats.")
        else:
            g_res = await c(functions.account.GetGlobalPrivacySettingsRequest())
            curr = "Enabled" if getattr(g_res, "archive_and_mute_new_noncontact_peers", False) else "Disabled"
            return await msg.edit_msg(
                f"<b>Auto-Archive Non-Contacts:</b> <code>{curr}</code>\n\n"
                f"<i>To change:</i> <code>{Altruix.user_command_handler}set -archive on|off</code>"
            )

    # 14. CONTACT JOINED NOTIFICATIONS: -signup on|off
    if "signup" in args or "-signup" in args or "joined" in args or "-joined" in args:
        val_str = (m.user_input or "").strip().lower()
        if val_str in ("off", "mute", "silent", "disable"):
            await c(functions.account.SetContactSignUpNotificationRequest(silent=True))
            return await msg.edit_msg("🔕 Contact joined alerts: Disabled")
        elif val_str in ("on", "active", "enable"):
            await c(functions.account.SetContactSignUpNotificationRequest(silent=False))
            return await msg.edit_msg("🔔 Contact joined alerts: Enabled")
        else:
            s_res = await c(functions.account.GetContactSignUpNotificationRequest())
            curr = "Muted" if getattr(s_res, "silent", False) else "Active"
            return await msg.edit_msg(
                f"<b>Contact Joined Notifications:</b> <code>{curr}</code>\n\n"
                f"<i>To change:</i> <code>{Altruix.user_command_handler}set -signup on|off</code>"
            )

    # 15. PERSONAL CHANNEL: -channel <@channel|id|off>
    if "channel" in args or "-channel" in args:
        if not m.user_input:
            return await msg.edit_msg("INPUT_REQUIRED")
        target = m.user_input.strip()
        if target.lower() in ("off", "none", "clear", "rm"):
            await c(functions.account.UpdatePersonalChannelRequest(channel=types.InputChannelEmpty()))
            return await msg.edit_msg("PERSONAL_CHANNEL_REMOVED")
        try:
            ent = await c.get_input_entity(target)
            if not isinstance(ent, (types.InputChannel, types.InputPeerChannel)):
                return await msg.edit_msg("CHANNEL_ONLY")
            channel_input = types.InputChannel(channel_id=ent.channel_id, access_hash=ent.access_hash)
            await c(functions.account.UpdatePersonalChannelRequest(channel=channel_input))
            return await msg.edit_msg("PERSONAL_CHANNEL_UPDATED", string_args=(target,))
        except Exception as e:
            return await msg.edit_msg("FAILED_TRANSFER", string_args=(str(e),))

    # 16. BIRTHDAY: -bday DD MM [YYYY] or -bday off
    if "bday" in args or "-bday" in args or "birthday" in args or "-birthday" in args:
        if not m.user_input:
            return await msg.edit_msg("INPUT_REQUIRED")
        target = m.user_input.strip()
        if target.lower() in ("off", "none", "clear", "rm"):
            await c(functions.account.UpdateBirthdayRequest(birthday=None))
            return await msg.edit_msg("BDAY_REMOVED")
        parts = target.replace("/", " ").replace("-", " ").split()
        if len(parts) < 2 or not all(p.isdigit() for p in parts[:2]):
            return await msg.edit_msg("INVALID_INPUT")
        day = int(parts[0])
        month = int(parts[1])
        year = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else None
        try:
            await c(functions.account.UpdateBirthdayRequest(birthday=types.Birthday(day=day, month=month, year=year)))
            y_str = f"/{year}" if year else ""
            return await msg.edit_msg(f"🎂 Birthday set to: <b>{day:02d}/{month:02d}{y_str}</b>")
        except Exception as e:
            return await msg.edit_msg("INVALID_INPUT")

    # 17. PRIVACY OVERVIEW: -privacy
    if "privacy" in args or "-privacy" in args:
        keys = [
            ("Phone Number", types.InputPrivacyKeyPhoneNumber()),
            ("Last Seen / Online", types.InputPrivacyKeyStatusTimestamp()),
            ("Profile Photo", types.InputPrivacyKeyProfilePhoto()),
            ("Forwarded Messages", types.InputPrivacyKeyForwards()),
            ("Phone Calls", types.InputPrivacyKeyPhoneCall()),
            ("Voice Messages", types.InputPrivacyKeyVoiceMessages()),
            ("Group Invites", types.InputPrivacyKeyChatInvite()),
        ]
        text_ = "<b>🔒 Telegram Privacy Settings:</b>\n\n"
        for label, p_key in keys:
            try:
                p_res = await c(functions.account.GetPrivacyRequest(key=p_key))
                rules = p_res.rules
                rule_desc = "Nobody"
                if any(isinstance(r, types.PrivacyValueAllowAll) for r in rules):
                    rule_desc = "Everybody"
                elif any(isinstance(r, types.PrivacyValueAllowContacts) for r in rules):
                    rule_desc = "My Contacts"
                elif any(isinstance(r, types.PrivacyValueAllowUsers) for r in rules):
                    rule_desc = "Allowed Users"
                text_ += f"  • <b>{label}:</b> <code>{rule_desc}</code>\n"
            except Exception:
                text_ += f"  • <b>{label}:</b> <code>Hidden</code>\n"
        return await msg.edit_msg(text_)

    return await msg.edit_msg("INPUT_REQUIRED")
