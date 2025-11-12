from config import *
from helper.database import *
from pyrogram.types import Message
from pyrogram import Client, filters
from pyrogram.errors import FloodWait, InputUserDeactivated, UserIsBlocked, PeerIdInvalid, MessageTooLong
import os, re, sys, time, asyncio, logging
from helper.utils import get_seconds
from datetime import datetime, timedelta, date
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from functools import wraps
from plugins.helper_func import *
import html
import pytz

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

OWNER_ID = Config.OWNER_ID
ADMIN_URL = Config.ADMIN_URL

# Flag to indicate if the bot is restarting
is_restarting = False

# --- Ban Check Decorator ---
def check_ban(func):
    @wraps(func)
    async def wrapper(client, message, *args, **kwargs):
        user_id = message.from_user.id
        user = await rexbots.col.find_one({"_id": user_id})
        if user and user.get("ban_status", {}).get("is_banned", False):
            keyboard = InlineKeyboardMarkup(
                [[InlineKeyboardButton("Cᴏɴᴛᴀᴄᴛ ʜᴇʀᴇ...!!", url=ADMIN_URL)]]
            )
            return await message.reply_text(
                "**Wᴛғ ʏᴏᴜ ᴀʀᴇ ʙᴀɴɴᴇᴅ ғʀᴏᴍ ᴜsɪɴɢ ᴍᴇ ʙʏ ᴏᴜʀ ᴀᴅᴍɪɴ/ᴏᴡɴᴇʀ . Iғ ʏᴏᴜ ᴛʜɪɴᴋs ɪᴛ's ᴍɪsᴛᴀᴋᴇ ᴄʟɪᴄᴋ ᴏɴ ᴄᴏɴᴛᴀᴄᴛ ʜᴇʀᴇ...!!**",
                reply_markup=keyboard
            )
        return await func(client, message, *args, **kwargs)
    return wrapper
    
#============== Admin commands =============================

# Commands for adding admins by owner
@Client.on_message(filters.command('add_admin') & filters.private & admin)
async def add_admins(client: Client, message: Message):
    try:
        pro = await message.reply("<b><i>ᴘʟᴇᴀsᴇ ᴡᴀɪᴛ..</i></b>", quote=True)
        admin_ids = await rexbots.get_all_admins()
        admins = message.text.split()[1:]

        reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("ᴄʟᴏsᴇ", callback_data="close")]])

        if not admins:
            return await pro.edit(
                "<b>Usᴇ ɪᴛ ʟɪᴋᴇ ᴛʜɪs:</b> <code>/add_admin 1234567890</code>\n<b>Oʀ:</b> <code>/add_admin 1234567890 9876543210</code>",
                reply_markup=reply_markup
            )

        successfully_added = []
        admin_list = ""
        
        for admin_id in admins:
            try:
                user_id = int(admin_id)
            except:
                admin_list += f"<blockquote><b>❌ Iɴᴠᴀʟɪᴅ ID: <code>{admin_id}</code></b></blockquote>\n"
                continue

            if user_id in admin_ids:
                try:
                    user = await client.get_users(user_id)
                    admin_list += f"<blockquote><b>⚠️ {user.mention} (<code>{user_id}</code>) ᴀʟʀᴇᴀᴅʏ ᴇxɪsᴛs.</b></blockquote>\n"
                except:
                    admin_list += f"<blockquote><b>⚠️ ID <code>{user_id}</code> ᴀʟʀᴇᴀᴅʏ ᴇxɪsᴛs.</b></blockquote>\n"
                continue

            try:
                user = await client.get_users(user_id)
                await rexbots.add_admin(user_id)
                successfully_added.append(user_id)
                admin_list += f"<b>• Nᴀᴍᴇ: {user.mention}\n⚡ Iᴅ: <code>{user_id}</code></b>\n\n"
            except Exception as e:
                admin_list += f"<blockquote><b>❌ Cᴀɴ'ᴛ ғᴇᴛᴄʜ ᴜsᴇʀ: <code>{user_id}</code></b></blockquote>\n"

        if successfully_added:
            await pro.edit(
                f"<b><u>✅ Aᴅᴍɪɴ(s) ᴀᴅᴅᴇᴅ sᴜᴄᴄᴇssғᴜʟʟʏ</u></b>\n\n{admin_list}",
                reply_markup=reply_markup
            )
        else:
            await pro.edit(
                f"<b>❌ Nᴏ ᴀᴅᴍɪɴs ᴡᴇʀᴇ ᴀᴅᴅᴇᴅ:</b>\n\n{admin_list.strip()}",
                reply_markup=reply_markup
            )
    except Exception as e:
        await pro.edit(f"<b>❌ Eʀʀᴏʀ ᴏᴄᴄᴜʀʀᴇᴅ:</b> <code>{str(e)}</code>")


@Client.on_message(filters.command('deladmin') & filters.private & admin)
async def delete_admins(client: Client, message: Message):
    try:
        pro = await message.reply("<b><i>ᴘʟᴇᴀsᴇ ᴡᴀɪᴛ..</i></b>", quote=True)
        admin_ids = await rexbots.get_all_admins()
        admins = message.text.split()[1:]

        reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("ᴄʟᴏsᴇ", callback_data="close")]])

        if not admins:
            return await pro.edit(
                "<b>Usᴇ ɪᴛ ʟɪᴋᴇ ᴛʜɪs:</b> <code>/deladmin 1234567890</code>\n<b>Oʀ ᴜsᴇ:</b> <code>/deladmin all</code> <b>ᴛᴏ ʀᴇᴍᴏᴠᴇ ᴀʟʟ ᴀᴅᴍɪɴs</b>",
                reply_markup=reply_markup
            )

        if len(admins) == 1 and admins[0].lower() == "all":
            if admin_ids:
                removed_list = ""
                for id in admin_ids:
                    try:
                        user = await client.get_users(id)
                        removed_list += f"<b>• Nᴀᴍᴇ: {user.mention}\n⚡ Iᴅ: <code>{id}</code></b>\n\n"
                    except:
                        removed_list += f"<b>• Iᴅ: <code>{id}</code></b>\n\n"
                    await rexbots.del_admin(id)
                return await pro.edit(
                    f"<b><u>✅ Rᴇᴍᴏᴠᴇᴅ ᴀʟʟ ᴀᴅᴍɪɴs:</u></b>\n\n{removed_list}",
                    reply_markup=reply_markup
                )
            else:
                return await pro.edit(
                    "<b><blockquote>⚠️ Nᴏ ᴀᴅᴍɪɴ IDs ᴛᴏ ʀᴇᴍᴏᴠᴇ.</blockquote></b>",
                    reply_markup=reply_markup
                )

        if admin_ids:
            passed = ''
            for admin_id in admins:
                try:
                    id = int(admin_id)
                except:
                    passed += f"<blockquote><b>❌ Iɴᴠᴀʟɪᴅ ID: <code>{admin_id}</code></b></blockquote>\n"
                    continue

                if id in admin_ids:
                    try:
                        user = await client.get_users(id)
                        passed += f"<b>• Nᴀᴍᴇ: {user.mention}\n⚡ Iᴅ: <code>{id}</code></b>\n\n"
                    except:
                        passed += f"<b>• Iᴅ: <code>{id}</code></b>\n\n"
                    await rexbots.del_admin(id)
                else:
                    passed += f"<blockquote><b>⚠️ ID <code>{id}</code> ɴᴏᴛ ғᴏᴜɴᴅ ɪɴ ᴀᴅᴍɪɴ ʟɪsᴛ.</b></blockquote>\n"

            await pro.edit(
                f"<b><u>✅ Rᴇᴍᴏᴠᴇᴅ ᴀᴅᴍɪɴ ɪᴅ:</u></b>\n\n{passed}",
                reply_markup=reply_markup
            )
        else:
            await pro.edit(
                "<b><blockquote>⚠️ Nᴏ ᴀᴅᴍɪɴ IDs ᴀᴠᴀɪʟᴀʙʟᴇ ᴛᴏ ᴅᴇʟᴇᴛᴇ.</blockquote></b>",
                reply_markup=reply_markup
            )
    except Exception as e:
        await pro.edit(f"<b>❌ Eʀʀᴏʀ ᴏᴄᴄᴜʀʀᴇᴅ:</b> <code>{str(e)}</code>")


@Client.on_message(filters.command('admins') & filters.private & admin)
async def get_admins(client: Client, message: Message):
    try:
        pro = await message.reply("<b><i>ᴘʟᴇᴀsᴇ ᴡᴀɪᴛ..</i></b>", quote=True)
        admin_ids = await rexbots.get_all_admins()

        if not admin_ids:
            admin_list = "<b><blockquote>❌ Nᴏ ᴀᴅᴍɪɴs ғᴏᴜɴᴅ.</blockquote></b>"
        else:
            admin_list = ""
            for idx, id in enumerate(admin_ids, 1):
                try:
                    user = await client.get_users(id)
                    admin_list += f"<b>{idx}. Nᴀᴍᴇ: {user.mention}\n⚡ Iᴅ: <code>{id}</code></b>\n\n"
                except:
                    admin_list += f"<b>{idx}. Iᴅ: <code>{id}</code></b>\n\n"

        reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("ᴄʟᴏsᴇ", callback_data="close")]])
        await pro.edit(
            f"<b>⚡ Cᴜʀʀᴇɴᴛ ᴀᴅᴍɪɴ ʟɪsᴛ:</b>\n\n{admin_list}",
            reply_markup=reply_markup
        )
    except Exception as e:
        await pro.edit(f"<b>❌ Eʀʀᴏʀ ᴏᴄᴄᴜʀʀᴇᴅ:</b> <code>{str(e)}</code>")

@Client.on_message(filters.command("ban") & filters.private & admin)
async def ban_user(bot, message):
    try:
        command_parts = message.text.split(maxsplit=2)
        if len(command_parts) < 2:
            await message.reply_text(
                "<b>Usᴇ ɪᴛ ʟɪᴋᴇ ᴛʜɪs:</b> <code>/ban &lt;ᴜsᴇʀ_ɪᴅ&gt; [ʀᴇᴀsᴏɴ]</code>"
            )
            return

        user_id_str = command_parts[1]
        reason = command_parts[2] if len(command_parts) > 2 else "Nᴏ ʀᴇᴀsᴏɴ ᴘʀᴏᴠɪᴅᴇᴅ"

        if not user_id_str.isdigit():
            await message.reply_text(
                "<b>Usᴇ ɪᴛ ʟɪᴋᴇ ᴛʜɪs:</b> <code>/ban &lt;ᴜsᴇʀ_ɪᴅ&gt; [ʀᴇᴀsᴏɴ]</code>"
            )
            return
            
        user_id = int(user_id_str)
        
        try:
            user = await bot.get_users(user_id)
            user_mention = user.mention
        except:
            user_mention = f"<code>{user_id}</code>"
            
        await rexbots.col.update_one(
            {"_id": user_id},
            {"$set": {
                "ban_status.is_banned": True,
                "ban_status.ban_reason": reason,
                "ban_status.banned_on": date.today().isoformat()
            }},
            upsert=True
        )
        
        await message.reply_text(
            f"<b>🚫 Usᴇʀ ʙᴀɴɴᴇᴅ sᴜᴄᴄᴇssғᴜʟʟʏ</b>\n\n"
            f"<b>• Usᴇʀ: {user_mention}\n"
            f"⚡ Usᴇʀ ID: <code>{user_id}</code>\n"
            f"📝 Rᴇᴀsᴏɴ: {reason}\n"
            f"📅 Bᴀɴɴᴇᴅ ᴏɴ: {date.today().strftime('%d-%m-%Y')}</b>"
        )
        
        # Notify user
        try:
            await bot.send_message(
                chat_id=user_id,
                text=f"<b>🚫 Yᴏᴜ ʜᴀᴠᴇ ʙᴇᴇɴ ʙᴀɴɴᴇᴅ</b>\n\n"
                     f"<blockquote><b>Rᴇᴀsᴏɴ: {reason}\n"
                     f"Dᴀᴛᴇ: {date.today().strftime('%d-%m-%Y')}</b></blockquote>",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Cᴏɴᴛᴀᴄᴛ Aᴅᴍɪɴ", url=ADMIN_URL)]])
            )
        except:
            pass
            
    except Exception as e:
        await message.reply_text(f"<b>❌ Eʀʀᴏʀ ᴏᴄᴄᴜʀʀᴇᴅ:</b> <code>{str(e)}</code>")


@Client.on_message(filters.command("unban") & filters.private & admin)
async def unban_user(bot, message):
    try:
        if len(message.text.split()) < 2:
            await message.reply_text(
                "<b>Usᴇ ɪᴛ ʟɪᴋᴇ ᴛʜɪs:</b> <code>/unban &lt;ᴜsᴇʀ_ɪᴅ&gt;</code>"
            )
            return
            
        user_id = int(message.text.split()[1])
        
        try:
            user = await bot.get_users(user_id)
            user_mention = user.mention
        except:
            user_mention = f"<code>{user_id}</code>"
            
        await rexbots.col.update_one(
            {"_id": user_id},
            {"$set": {
                "ban_status.is_banned": False,
                "ban_status.ban_reason": "",
                "ban_status.banned_on": None
            }}
        )
        
        await message.reply_text(
            f"<b>✅ Usᴇʀ ᴜɴʙᴀɴɴᴇᴅ sᴜᴄᴄᴇssғᴜʟʟʏ</b>\n\n"
            f"<b>• Usᴇʀ: {user_mention}\n"
            f"⚡ Usᴇʀ ID: <code>{user_id}</code>\n"
            f"📅 Uɴʙᴀɴɴᴇᴅ ᴏɴ: {date.today().strftime('%d-%m-%Y')}</b>"
        )
        
        # Notify user
        try:
            await bot.send_message(
                chat_id=user_id,
                text=f"<b>✅ Yᴏᴜ ʜᴀᴠᴇ ʙᴇᴇɴ ᴜɴʙᴀɴɴᴇᴅ</b>\n\n"
                     f"<blockquote><b>Yᴏᴜ ᴄᴀɴ ɴᴏᴡ ᴜsᴇ ᴛʜᴇ ʙᴏᴛ ᴀɢᴀɪɴ!\n"
                     f"Dᴀᴛᴇ: {date.today().strftime('%d-%m-%Y')}</b></blockquote>"
            )
        except:
            pass
            
    except Exception as e:
        await message.reply_text(
            "<b>Usᴇ ɪᴛ ʟɪᴋᴇ ᴛʜɪs:</b> <code>/unban &lt;ᴜsᴇʀ_ɪᴅ&gt;</code>\n\n"
            f"<b>❌ Eʀʀᴏʀ:</b> <code>{str(e)}</code>"
        )


@Client.on_message(filters.command("banned") & filters.private & admin)
async def banned_list(bot, message):
    try:
        msg = await message.reply("<b><i>ᴘʟᴇᴀsᴇ ᴡᴀɪᴛ..</i></b>")
        cursor = rexbots.col.find({"ban_status.is_banned": True})
        lines = []
        count = 0
        
        async for user in cursor:
            count += 1
            uid = user['_id']
            reason = user.get('ban_status', {}).get('ban_reason', 'Nᴏ ʀᴇᴀsᴏɴ')
            banned_date = user.get('ban_status', {}).get('banned_on', 'Uɴᴋɴᴏᴡɴ')
            
            try:
                user_obj = await bot.get_users(uid)
                name = user_obj.mention
            except PeerIdInvalid:
                name = f"<code>{uid}</code>"
            except:
                name = f"<code>{uid}</code>"
                
            lines.append(
                f"<b>{count}. {name}\n"
                f"⚡ ID: <code>{uid}</code>\n"
                f"📝 Rᴇᴀsᴏɴ: {reason}\n"
                f"📅 Dᴀᴛᴇ: {banned_date}</b>\n"
            )

        if not lines:
            await msg.edit(
                "<b><blockquote>✅ Nᴏ ᴜsᴇʀ(s) ɪs ᴄᴜʀʀᴇɴᴛʟʏ ʙᴀɴɴᴇᴅ</blockquote></b>",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("ᴄʟᴏsᴇ", callback_data="close")]])
            )
        else:
            banned_text = f"<b>🚫 Bᴀɴɴᴇᴅ Usᴇʀs Lɪsᴛ</b>\n\n{''.join(lines[:50])}"
            if len(lines) > 50:
                banned_text += f"\n<i>...ᴀɴᴅ {len(lines) - 50} ᴍᴏʀᴇ</i>"
                
            await msg.edit(
                banned_text,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("ᴄʟᴏsᴇ", callback_data="close")]])
            )
    except Exception as e:
        await msg.edit(f"<b>❌ Eʀʀᴏʀ ᴏᴄᴄᴜʀʀᴇᴅ:</b> <code>{str(e)}</code>")
        
#============== Premium commands ====================

@Client.on_message(filters.command("remove_premium") & admin)
async def remove_premium(client, message):
    try:
        if len(message.command) == 2:
            user_id = int(message.command[1])
            user = await client.get_users(user_id)
            if hasattr(rexbots, "remove_premium_access"):
                if await rexbots.remove_premium_access(user_id):
                    await message.reply_text("ᴜꜱᴇʀ ʀᴇᴍᴏᴠᴇᴅ ꜱᴜᴄᴄᴇꜱꜱꜰᴜʟʟʏ ✅")
                    await client.send_message(
                        chat_id=user_id,
                        text=f"<b>ʜᴇʏ {user.mention},\n\n<blockquote>Yᴏᴜʀ ᴘʀᴇᴍɪᴜᴍ ᴀᴄᴄᴇss ʜᴀs ʙᴇᴇɴ ʀᴇᴍᴏᴠᴇᴅ. Tʜᴀɴᴋs ғᴏʀ ᴜsɪɴɢ ᴏᴜʀ sᴇʀᴠɪᴄᴇs. Usᴇ /ᴘʟᴀɴ ᴛᴏ ᴄʜᴇᴄᴋ ᴏᴛʜᴇʀ ᴘʟᴀɴs...!!</blockquote></b>"
                    )
                else:
                    await message.reply_text("ᴜɴᴀʙʟᴇ ᴛᴏ ʀᴇᴍᴏᴠᴇ ᴜꜱᴇʀ! \nᴀʀᴇ ʏᴏᴜ ꜱᴜʀᴇ, ɪᴛ ᴡᴀꜱ ᴀ ᴘʀᴇᴍɪᴜᴍ ᴜꜱᴇʀ ɪᴅ?")
            else:
                await message.reply_text("ᴜɴᴀʙʟᴇ ᴛᴏ ʀᴇᴍᴏᴠᴇ ᴜꜱᴇʀ! \nᴀʀᴇ ʏᴏᴜ ꜱᴜʀᴇ, ɪᴛ ᴡᴀꜱ ᴀ ᴘʀᴇᴍɪᴜᴍ ᴜꜱᴇʀ ɪᴅ?")
        else:
            await message.reply_text("Dᴜᴅᴇ ᴜsᴇ ɪᴛ ʟɪᴋᴇ ᴛʜɪs /remove_premium <ᴜsᴇʀ_ɪᴅ>")
    except Exception as e:
        await message.reply_text(f"❌ Error occurred: {str(e)}")
        
@Client.on_message(filters.command("myplan"))
async def myplan(client, message):
    user = message.from_user.mention
    user_id = message.from_user.id
    data = await rexbots.get_user(message.from_user.id)
    if data and data.get("expiry_time"):
        expiry = data.get("expiry_time")
        expiry_ist = expiry.astimezone(pytz.timezone("Asia/Kolkata"))
        expiry_str_in_ist = expiry.astimezone(pytz.timezone("Asia/Kolkata")).strftime("%d-%m-%Y\n⏱️ ᴇxᴘɪʀʏ ᴛɪᴍᴇ : %I:%M:%S %p")
        # Calculate time difference
        current_time = datetime.now(pytz.timezone("Asia/Kolkata"))
        time_left = expiry_ist - current_time

        # Calculate days, hours, and minutes
        days = time_left.days
        hours, remainder = divmod(time_left.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        # Format time left as a string
        time_left_str = f"{days} ᴅᴀʏꜱ, {hours} ʜᴏᴜʀꜱ, {minutes} ᴍɪɴᴜᴛᴇꜱ"
        await message.reply_text(f"• ᴘʀᴇᴍɪᴜᴍ ᴜꜱᴇʀ ᴅᴀᴛᴀ :\n\n• ᴜꜱᴇʀ : {user}\n⚡ ᴜꜱᴇʀ ɪᴅ : <code>{user_id}</code>\n⏰ ᴛɪᴍᴇ ʟᴇꜰᴛ : {time_left_str}\n⌛️ ᴇxᴘɪʀʏ ᴅᴀᴛᴇ : {expiry_str_in_ist}")
    else:
        await message.reply_text(
            f"<b>ʜᴇʏ {user},\n\n<blockquote>Yᴏᴜ ᴅᴏ ɴᴏᴛ ʜᴀᴠᴇ ᴀɴʏ ᴀᴄᴛɪᴠᴇ ᴘʀᴇᴍɪᴜᴍ ᴘʟᴀɴ, ɪғ ʏᴏᴜ ᴡᴀɴᴛ ᴛʜᴇɴ ᴄʟɪᴄᴋ ᴏɴ ᴛʜᴇ ʙᴇʟᴏᴡ ʙᴜᴛᴛᴏɴ...!!</blockquote></b>",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("• ᴄʜᴇᴄᴋᴏᴜᴛ ᴘʀᴇᴍɪᴜᴍ ᴘʟᴀɴꜱ •", callback_data='seeplan')]])
        )

@Client.on_message(filters.command("premium_info") & admin)
async def get_premium(client, message):
    try:
        if len(message.command) == 2:
            user_id = int(message.command[1])
            user = await client.get_users(user_id)
            data = await rexbots.get_user(user_id)
            if data and data.get("expiry_time"):
                expiry = data.get("expiry_time") 
                expiry_ist = expiry.astimezone(pytz.timezone("Asia/Kolkata"))
                expiry_str_in_ist = expiry.astimezone(pytz.timezone("Asia/Kolkata")).strftime("%d-%m-%Y\n⏱️ ᴇxᴘɪʀʏ ᴛɪᴍᴇ : %I:%M:%S %p")        
                # Calculate time difference
                current_time = datetime.now(pytz.timezone("Asia/Kolkata"))
                time_left = expiry_ist - current_time
                
                # Calculate days, hours, and minutes
                days = time_left.days
                hours, remainder = divmod(time_left.seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                # Format time left as a string
                time_left_str = f"{days} days, {hours} hours, {minutes} minutes"
                await message.reply_text(f"• ᴘʀᴇᴍɪᴜᴍ ᴜꜱᴇʀ ᴅᴀᴛᴀ :\n\n• ᴜꜱᴇʀ : {user.mention}\n⚡ ᴜꜱᴇʀ ɪᴅ : <code>{user_id}</code>\n⏰ ᴛɪᴍᴇ ʟᴇꜰᴛ : {time_left_str}\n⌛️ ᴇxᴘɪʀʏ ᴅᴀᴛᴇ : {expiry_str_in_ist}")
            else:
                await message.reply_text("ɴᴏ ᴀɴʏ ᴘʀᴇᴍɪᴜᴍ ᴅᴀᴛᴀ ᴏꜰ ᴛʜᴇ ᴡᴀꜱ ꜰᴏᴜɴᴅ ɪɴ ᴅᴀᴛᴀʙᴀꜱᴇ !")
        else:
            await message.reply_text("Dᴜᴅᴇ ᴜsᴇ ɪᴛ ʟɪᴋᴇ ᴛʜɪs /premium_info <ᴜsᴇʀ_ɪᴅ>")
    except Exception as e:
        await message.reply_text(f"❌ Error occurred: {str(e)}")

@Client.on_message(filters.command("add_premium") & admin)
async def give_premium_cmd_handler(client, message):
    try:
        if len(message.command) == 4:
            time_zone = datetime.now(pytz.timezone("Asia/Kolkata"))
            current_time = time_zone.strftime("%d-%m-%Y\n⏱️ ᴊᴏɪɴɪɴɢ ᴛɪᴍᴇ : %I:%M:%S %p") 
            user_id = int(message.command[1])  
            user = await client.get_users(user_id)
            time = message.command[2]+" "+message.command[3]
            seconds = await get_seconds(time)
            if seconds > 0:
                expiry_time = datetime.now() + timedelta(seconds=seconds)
                user_data = {"_id": user_id, "expiry_time": expiry_time}  
                await rexbots.update_user(user_data)
                data = await rexbots.get_user(user_id)
                expiry = data.get("expiry_time")    
                expiry_str_in_ist = expiry.astimezone(pytz.timezone("Asia/Kolkata")).strftime("%d-%m-%Y\n⏱️ ᴇxᴘɪʀʏ ᴛɪᴍᴇ : %I:%M:%S %p")
                
                await message.reply_text(f"ᴘʀᴇᴍɪᴜᴍ ᴀᴅᴅᴇᴅ ꜱᴜᴄᴄᴇꜱꜱꜰᴜʟʟʏ ✅\n\n• ᴜꜱᴇʀ : {user.mention}\n⚡ ᴜꜱᴇʀ ɪᴅ : <code>{user_id}</code>\n⏰ ᴘʀᴇᴍɪᴜᴍ ᴀᴄᴄᴇꜱꜱ : <code>{time}</code>\n\n⏳ ᴊᴏɪɴɪɴɢ ᴅᴀᴛᴇ : {current_time}\n\n⌛️ ᴇxᴘɪʀʏ ᴅᴀᴛᴇ : {expiry_str_in_ist}", disable_web_page_preview=True)
                
                await client.send_message(
                    chat_id=user_id,
                    text=f"👋 ʜᴇʏ {user.mention},\nᴛʜᴀɴᴋ ʏᴏᴜ ꜰᴏʀ ᴘᴜʀᴄʜᴀꜱɪɴɢ ᴘʀᴇᴍɪᴜᴍ.\nᴇɴᴊᴏʏ !! ✨🎉\n\n⏰ ᴘʀᴇᴍɪᴜᴍ ᴀᴄᴄᴇꜱꜱ : <code>{time}</code>\n⏳ ᴊᴏɪɴɪɴɢ ᴅᴀᴛᴇ : {current_time}\n\n⌛️ ᴇxᴘɪʀʏ ᴅᴀᴛᴇ : {expiry_str_in_ist}", disable_web_page_preview=True
                )
                
                await client.send_message(
                    chat_id=Config.LOG_CHANNEL,
                    text=f"#Added_Premium\n\n• ᴜꜱᴇʀ : {user.mention}\n⚡ ᴜꜱᴇʀ ɪᴅ : <code>{user_id}</code>\n⏰ ᴘʀᴇᴍɪᴜᴍ ᴀᴄᴄᴇꜱꜱ : <code>{time}</code>\n\n⏳ ᴊᴏɪɴɪɴɢ ᴅᴀᴛᴇ : {current_time}\n\n⌛️ ᴇxᴘɪʀʏ ᴅᴀᴛᴇ : {expiry_str_in_ist}", 
                    disable_web_page_preview=True
                )
            else:
                await message.reply_text("Iɴᴠᴀʟɪᴅ ᴛɪᴍᴇ ғᴏʀᴍᴀᴛ. Pʟᴇᴀsᴇ ᴜsᴇ '1 ᴅᴀʏ ғᴏʀ ᴅᴀʏs', '1 ʜᴏᴜʀ ғᴏʀ ʜᴏᴜʀs', ᴏʀ '1 ᴍɪɴ ғᴏʀ ᴍɪɴᴜᴛᴇs', ᴏʀ '1 ᴍᴏɴᴛʜ ғᴏʀ ᴍᴏɴᴛʜs' ᴏʀ '1 ʏᴇᴀʀ ғᴏʀ ʏᴇᴀʀ'.")
        else:
            await message.reply_text("Dᴜᴅᴇ ᴜsᴇ ɪᴛ ʟɪᴋᴇ ᴛʜɪs: `/add_premium <ᴜsᴇʀ_ɪᴅ> <ᴛɪᴍᴇ_ᴠᴀʟᴜᴇ> <ᴛɪᴍᴇ_ᴜɴɪᴛ>`.\n\nExample: `/add_premium 1234567890 30 days`")
    except Exception as e:
        await message.reply_text(f"❌ Error occurred: {str(e)}")

@Client.on_message(filters.command("premium_users") & admin)
async def premium_user(client, message):
    try:
        aa = await message.reply_text("<i>ꜰᴇᴛᴄʜɪɴɢ...</i>")
        new = f" ᴘʀᴇᴍɪᴜᴍ ᴜꜱᴇʀꜱ ʟɪꜱᴛ :\n\n"
        user_count = 1
        found_premium_users = False
        users = await rexbots.get_all_users()
        current_time = datetime.now(pytz.timezone("Asia/Kolkata"))
        
        async for user in users:
            data = await rexbots.get_user(user['_id'])
            if data and data.get("expiry_time"):
                expiry = data.get("expiry_time")
                expiry_ist = expiry.astimezone(pytz.timezone("Asia/Kolkata"))
                
                # Check if premium is still active
                if expiry_ist > current_time:
                    expiry_str_in_ist = expiry_ist.strftime("%d-%m-%Y\n⏱️ ᴇxᴘɪʀʏ ᴛɪᴍᴇ : %I:%M:%S %p")
                    time_left = expiry_ist - current_time
                    days = time_left.days
                    hours, remainder = divmod(time_left.seconds, 3600)
                    minutes, seconds = divmod(remainder, 60)
                    time_left_str = f"{days} days, {hours} hours, {minutes} minutes"
                    
                    # Get user mention with error handling
                    try:
                        user_obj = await client.get_users(user['_id'])
                        user_mention = user_obj.mention
                    except PeerIdInvalid:
                        # Use stored name from database or fallback to ID
                        stored_name = data.get('first_name', 'Unknown')
                        user_mention = f"{stored_name} (<code>{user['_id']}</code>)"
                    except Exception:
                        # Any other error, use ID only
                        user_mention = f"User <code>{user['_id']}</code>"
                    
                    new += f"{user_count}. {user_mention}\n• ᴜꜱᴇʀ ɪᴅ : <code>{user['_id']}</code>\n⏳ ᴇxᴘɪʀʏ ᴅᴀᴛᴇ : {expiry_str_in_ist}\n⏰ ᴛɪᴍᴇ ʟᴇꜰᴛ : {time_left_str}\n\n"
                    user_count += 1
                    found_premium_users = True
        
        if not found_premium_users:
            await aa.edit_text("Nᴏ ᴀᴄᴛɪᴠᴇ ᴘʀᴇᴍɪᴜᴍ ᴜsᴇʀ ғᴏᴜɴᴅ ɪɴ ᴛʜᴇ ᴅᴀᴛᴀʙᴀsᴇ")
        else:
            try:
                await aa.edit_text(new)
            except MessageTooLong:
                with open('usersplan.txt', 'w+') as outfile:
                    outfile.write(new)
                await message.reply_document('usersplan.txt', caption="<u>Pʀᴇᴍɪᴜᴍ ᴜsᴇʀs</u>:\n\n")
                await aa.delete()
                os.remove('usersplan.txt')
    except Exception as e:
        await aa.edit_text(f"❌ Error occurred: {str(e)}")
        
@Client.on_message(filters.command("plan"))
async def plan(client, message):
    user_id = message.from_user.id
    mention = message.from_user.mention
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton('⇋ ʙᴀᴄᴋ ᴛᴏ ʜᴏᴍᴇ ⇋', callback_data='home')]])

    PREMIUM_TXT = f"<b>👋 ʜᴇʏ {mention}\n\n🎁 ᴘʀᴇᴍɪᴜᴍ ғᴇᴀᴛᴜʀᴇ ʙᴇɴɪꜰɪᴛꜱ:</blockquote>\n\n›› ɴᴏ ɴᴇᴇᴅ ᴛᴏ ᴏᴘᴇɴ ʟɪɴᴋꜱ\n❏ Gᴇᴛ ᴅɪʀᴇᴄᴛ ᴀᴜᴛᴏ ʀᴇɴᴀᴍɪɴɢ ғᴇᴀᴛᴜʀᴇ ɴᴏ ɴᴇᴇᴅ ғᴏʀ ᴠᴇʀɪғʏ\n›› ᴀᴅ-ғʀᴇᴇ ᴇxᴘᴇʀɪᴇɴᴄᴇ\n❏ Uɴʟɪᴍɪᴛᴇᴅ ᴀᴜᴛᴏ ʀᴇɴᴀᴍɪɴɢ\n\n›› ᴄʜᴇᴄᴋ ʏᴏᴜʀ ᴀᴄᴛɪᴠᴇ ᴘʟᴀɴ: /myplan\n\n • ₹80 - 1 ᴡᴇᴇᴋ\n • ₹100 - 1 ᴍᴏɴᴛʜ\n • ₹750 - 1 ʏᴇᴀʀ\n\n Cᴜsᴛᴏᴍ ᴘʟᴀɴ ᴀʟsᴏ ᴀᴠᴀɪʟᴀʙʟᴇ ᴄᴏɴᴛᴀᴄᴛ ᴀᴛ :- @RexBots_Official</b>"

    await message.reply_photo(
        photo="https://envs.sh/Wdj.jpg",
        caption=PREMIUM_TXT,
        reply_markup=keyboard)

@Client.on_message(filters.private & filters.command("restart") & filters.private & admin)
async def restart_bot(b, m):
    global is_restarting
    if not is_restarting:
        is_restarting = True
        await m.reply_text("**Hᴇʏ...!! Oᴡɴᴇʀ/Aᴅᴍɪɴ Jᴜsᴛ ʀᴇʟᴀx ɪᴀᴍ ʀᴇsᴛᴀʀᴛɪɴɢ...!!**")
        b.stop()
        time.sleep(2)
        os.execl(sys.executable, sys.executable, *sys.argv)


@Client.on_message(filters.private & filters.command(["tutorial"]))
async def tutorial(bot, message):
    user_id = message.from_user.id
    format_template = await rexbots.get_format_template(user_id)
    await message.reply_text(
        text=Config.FILE_NAME_TXT.format(format_template=format_template),
        disable_web_page_preview=True,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("• Sᴜᴘᴘᴏʀᴛ •", url="https://t.me/BOTSKINGDOMSGROUP"), InlineKeyboardButton("•⚡Mᴀɪɴ ʜᴜʙ •", url="https://t.me/botskingdoms")]
        ])
    )

@Client.on_message(filters.command(["stats", "status"]) & filters.private & admin)
async def get_stats(bot, message):
    total_users = await rexbots.total_users_count()
    uptime = time.strftime("%Hh%Mm%Ss", time.gmtime(time.time() - bot.uptime))
    start_t = time.time()
    st = await message.reply('<b><i>ᴘʟᴇᴀsᴇ ᴡᴀɪᴛ..</i></b>')
    end_t = time.time()
    time_taken_s = (end_t - start_t) * 1000
    await st.edit(text=f"**Bᴏᴛ Sᴛᴀᴛᴜꜱ:** \n\n**➲ Bᴏᴛ Uᴘᴛɪᴍᴇ:** `{uptime}` \n**➲ Pɪɴɢ:** `{time_taken_s:.3f} ms` \n**➲ Vᴇʀsɪᴏɴ:** 2.0.0 \n**➲ Tᴏᴛᴀʟ Uꜱᴇʀꜱ:** `{total_users}`")

@Client.on_message(filters.command("broadcast") & filters.private & admin & filters.reply)
async def broadcast_handler(bot: Client, m: Message):
    await bot.send_message(Config.LOG_CHANNEL, f"Bʀᴏᴀᴅᴄᴀsᴛ Sᴛᴀʀᴛᴇᴅ Bʏ {m.from_user.mention}")
    all_users = await rexbots.get_all_users()
    broadcast_msg = m.reply_to_message
    sts_msg = await m.reply_text("**Bʀᴏᴀᴅᴄᴀsᴛ Sᴛᴀʀᴛᴇᴅ...!!**")
    done = 0
    failed = 0
    success = 0
    start_time = time.time()
    total_users = await rexbots.total_users_count()
    async for user in all_users:
        sts = await send_msg(user['_id'], broadcast_msg)
        if sts == 200:
            success += 1
        else:
            failed += 1
        if sts == 400:
            await rexbots.delete_user(user['_id'])
        done += 1
        if not done % 20:
            await sts_msg.edit(f"Broadcast In Progress: \n\nTotal Users {total_users} \nCompleted : {done} / {total_users}\nSuccess : {success}\nFailed : {failed}")
    completed_in = timedelta(seconds=int(time.time() - start_time))
    await sts_msg.edit(f"Bʀᴏᴀᴅᴄᴀꜱᴛ Cᴏᴍᴩʟᴇᴛᴇᴅ: \nCᴏᴍᴩʟᴇᴛᴇᴅ Iɴ `{completed_in}`.\n\nTotal Users {total_users}\nCompleted: {done} / {total_users}\nSuccess: {success}\nFailed: {failed}")

async def send_msg(user_id, message):
    try:
        await message.copy(chat_id=int(user_id))
        return 200
    except FloodWait as e:
        await asyncio.sleep(e.value)
        return send_msg(user_id, message)
    except InputUserDeactivated:
        logger.info(f"{user_id} : Deactivated")
        return 400
    except UserIsBlocked:
        logger.info(f"{user_id} : Blocked The Bot")
        return 400
    except PeerIdInvalid:
        logger.info(f"{user_id} : User ID Invalid")
        return 400
    except Exception as e:
        logger.error(f"{user_id} : {e}")
        return 500
        
@Client.on_message((filters.group | filters.private) & filters.command("leaderboard"))
async def leaderboard_handler(bot: Client, message: Message):
    try:
        user_id = message.from_user.id if message.from_user else None

        async def generate_leaderboard(filter_type):
            pipeline = []
            current_time = datetime.now(pytz.timezone("Asia/Kolkata"))

            if filter_type == "today":
                start_time = current_time.replace(hour=0, minute=0, second=0, microsecond=0)
                pipeline.append({"$match": {"rename_timestamp": {"$gte": start_time}}})
            elif filter_type == "week":
                days_since_monday = current_time.weekday()
                start_time = (current_time - timedelta(days=days_since_monday)).replace(hour=0, minute=0, second=0, microsecond=0)
                pipeline.append({"$match": {"rename_timestamp": {"$gte": start_time}}})
            elif filter_type == "month":
                start_time = current_time.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                pipeline.append({"$match": {"rename_timestamp": {"$gte": start_time}}})
            elif filter_type == "year":
                start_time = current_time.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
                pipeline.append({"$match": {"rename_timestamp": {"$gte": start_time}}})

            if filter_type != "lifetime":
                pipeline.extend([
                    {"$group": {
                        "_id": "$_id",
                        "rename_count": {"$sum": 1},
                        "first_name": {"$first": "$first_name"},
                        "username": {"$first": "$username"}
                    }},
                    {"$sort": {"rename_count": -1}},
                    {"$limit": 10}
                ])

            if pipeline and filter_type != "lifetime":
                users = await rexbots.col.aggregate(pipeline).to_list(10)
            elif filter_type == "lifetime":
                users = await rexbots.col.find().sort("rename_count", -1).limit(10).to_list(10)
            else:
                users = await rexbots.col.find().sort("rename_count", -1).limit(10).to_list(10)

            if not users:
                return None

            user_rank = None
            user_count = 0

            if user_id:
                if filter_type != "lifetime":
                    user_data_pipeline_for_current_user = [
                        {"$match": {"_id": user_id, "rename_timestamp": {"$gte": start_time}}}
                    ]
                    user_data_pipeline_for_current_user.extend([
                        {"$group": {
                            "_id": "$_id",
                            "rename_count": {"$sum": 1}
                        }}
                    ])

                    user_data = await rexbots.col.aggregate(user_data_pipeline_for_current_user).to_list(1)

                    if user_data:
                        user_count = user_data[0].get("rename_count", 0)

                        higher_count_pipeline = [
                            {"$match": {"rename_timestamp": {"$gte": start_time}}}
                        ]
                        higher_count_pipeline.extend([
                            {"$group": {
                                "_id": "$_id",
                                "rename_count": {"$sum": 1}
                            }},
                            {"$match": {"rename_count": {"$gt": user_count}}}
                        ])

                        higher_count_docs = await rexbots.col.aggregate(higher_count_pipeline).to_list(None)
                        user_rank = len(higher_count_docs) + 1
                else:
                    user_data = await rexbots.col.find_one({"_id": user_id})
                    if user_data:
                        user_count = user_data.get("rename_count", 0)
                        higher_count = await rexbots.col.count_documents({"rename_count": {"$gt": user_count}})
                        user_rank = higher_count + 1

            filter_title = {
                "today": "Tᴏᴅᴀʏ's",
                "week": "Tʜɪs Wᴇᴇᴋ's",
                "month": "Tʜɪs Mᴏɴᴛʜ's",
                "year": "Tʜɪs Yᴇᴀʀ's",
                "lifetime": "Aʟʟ-Tɪᴍᴇ"
            }

            leaderboard = [f"<b>{filter_title[filter_type]} Tᴏᴘ 10 Rᴇɴᴀᴍᴇʀs</b>\n"]

            for idx, user in enumerate(users, 1):
                u_id = user['_id']
                count = user.get('rename_count', 0)

                try:
                    tg_user = await bot.get_users(u_id)
                    name = html.escape(tg_user.first_name or "Anonymous")
                    username = f"@{tg_user.username}" if tg_user.username else "No UN"
                except Exception:
                    name = html.escape(user.get('first_name', 'Anonymous').strip())
                    username = f"@{user['username']}" if user.get('username') else "No UN"

                leaderboard.append(
                    f"{idx}. <b>{name}</b> "
                    f"(<code>{username}</code>) ➜ "
                    f"<i>{count} ʀᴇɴᴀᴍᴇs</i>"
                )

            if user_rank:
                leaderboard.append(f"\n<b>Yᴏᴜʀ Rᴀɴᴋ:</b> {user_rank} ᴡɪᴛʜ {user_count} ʀᴇɴᴀᴍᴇs")

            leaderboard.append(f"\nLᴀsᴛ ᴜᴘᴅᴀᴛᴇᴅ: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
            leaderboard.append(f"\n<i>**Tʜɪs ᴍᴇssᴀɢᴇ ᴡɪʟʟ ᴀᴜᴛᴏ-ᴅᴇʟᴇᴛᴇ ɪɴ {Config.LEADERBOARD_DELETE_TIMER} sᴇᴄᴏɴᴅs**</i>")

            return "\n".join(leaderboard)

        leaderboard_text = await generate_leaderboard("lifetime")

        if not leaderboard_text:
            no_data_msg = await message.reply_text("<blockquote>Nᴏ ʟᴇᴀᴅᴇʀʙᴏᴀʀᴅ ᴅᴀᴛᴀ ᴀᴠᴀɪʟᴀʙʟᴇ ʏᴇᴛ!</blockquote>")
            await asyncio.sleep(10)
            await no_data_msg.delete()
            return

        sent_msg = await message.reply_photo(
            photo=Config.LEADERBOARD_PIC,
            caption=leaderboard_text
        )

        async def delete_messages():
            await asyncio.sleep(Config.LEADERBOARD_DELETE_TIMER)
            try:
                await sent_msg.delete()
            except Exception as e:
                logger.error(f"Error deleting sent_msg: {e}")
            try:
                await message.delete()
            except Exception as e:
                logger.error(f"Error deleting original message: {e}")

        asyncio.create_task(delete_messages())

    except Exception as e:
        logger.error(f"Error in leaderboard_handler: {e}")
        error_msg = await message.reply_text(
            "<b>Eʀʀᴏʀ ɢᴇɴᴇʀᴀᴛɪɴɢ ʟᴇᴀᴅᴇʀʙᴏᴀʀᴅ!</b>\n"
            f"<code>{str(e)}</code>\n\n"
            f"**Tʜɪs ᴍᴇssᴀɢᴇ ᴡɪʟʟ sᴇʟғ-ᴅᴇsᴛʀᴜᴄᴛ ɪɴ {Config.LEADERBOARD_DELETE_TIMER} sᴇᴄᴏɴᴅs.**"
        )
        await asyncio.sleep(Config.LEADERBOARD_DELETE_TIMER)
        try:
            await error_msg.delete()
        except Exception as e:
            logger.error(f"Error deleting error_msg: {e}")
