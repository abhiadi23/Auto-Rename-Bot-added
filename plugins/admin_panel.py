from config import *
from helper.database import codeflixbots
from pyrogram.types import Message
from pyrogram import Client, filters
from pyrogram.errors import FloodWait, InputUserDeactivated, UserIsBlocked, PeerIdInvalid
import os, sys, time, asyncio, logging
import datetime # Keep this for datetime.date.today() and datetime.timedelta
from datetime import timedelta # Explicitly import timedelta for cleaner usage
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from functools import wraps
from plugins.helper_func import *
import html # Import html for escaping names

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
        user = await codeflixbots.col.find_one({"_id": user_id})
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

# Commands for adding admins by owner
@Client.on_message(filters.command('add_admin') & filters.private & admin)
async def add_admins(client: Client, message: Message):
    pro = await message.reply("<b><i>ᴘʟᴇᴀsᴇ ᴡᴀɪᴛ..</i></b>", quote=True)
    check = 0
    admin_ids = await codeflixbots.get_all_admins()
    admins = message.text.split()[1:]

    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("ᴄʟᴏsᴇ", callback_data="close")]])

    if not admins:
        return await pro.edit(
            "<b>You need to provide user ID(s) to add as admin.</b>\n\n"
            "<b>Usage:</b>\n"
            "<code>/add_admin [user_id]</code> — Add one or more user IDs\n\n"
            "<b>Example:</b>\n"
            "<code>/add_admin 1234567890 9876543210</code>",
            reply_markup=reply_markup
        )

    admin_list = ""
    for id in admins:
        try:
            id = int(id)
        except:
            admin_list += f"<blockquote><b>Invalid ID: <code>{id}</code></b></blockquote>\n"
            continue

        if id in admin_ids:
            admin_list += f"<blockquote><b>ID <code>{id}</code> already exists.</b></blockquote>\n"
            continue

        id = str(id)
        if id.isdigit() and len(id) == 10:
            admin_list += f"<b><blockquote>(ID: <code>{id}</code>) added.</blockquote></b>\n"
            check += 1
        else:
            admin_list += f"<blockquote><b>Invalid ID: <code>{id}</code></b></blockquote>\n"

    if check == len(admins):
        for id in admins:
            await codeflixbots.add_admin(int(id))
        await pro.edit(f"<b>✅ Admin(s) added successfully:</b>\n\n{admin_list}", reply_markup=reply_markup)
    else:
        await pro.edit(
            f"<b>❌ Some errors occurred while adding admins:</b>\n\n{admin_list.strip()}\n\n"
            "<b><i>Please check and try again.</i></b>",
            reply_markup=reply_markup
        )


@Client.on_message(filters.command('deladmin') & filters.private & admin)
async def delete_admins(client: Client, message: Message):
    pro = await message.reply("<b><i>ᴘʟᴇᴀsᴇ ᴡᴀɪᴛ..</i></b>", quote=True)
    admin_ids = await codeflixbots.get_all_admins()
    admins = message.text.split()[1:]

    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("ᴄʟᴏsᴇ", callback_data="close")]])

    if not admins:
        return await pro.edit(
            "<b>Please provide valid admin ID(s) to remove.</b>\n\n"
            "<b>Usage:</b>\n"
            "<code>/deladmin [user_id]</code> — Remove specific IDs\n"
            "<code>/deladmin all</code> — Remove all admins",
            reply_markup=reply_markup
        )

    if len(admins) == 1 and admins[0].lower() == "all":
        if admin_ids:
            for id in admin_ids:
                await codeflixbots.del_admin(id)
            ids = "\n".join(f"<blockquote><code>{admin}</code> ✅</blockquote>" for admin in admin_ids)
            return await pro.edit(f"<b>⛔️ All admin IDs have been removed:</b>\n{ids}", reply_markup=reply_markup)
        else:
            return await pro.edit("<b><blockquote>No admin IDs to remove.</blockquote></b>", reply_markup=reply_markup)

    if admin_ids:
        passed = ''
        for admin_id in admins:
            try:
                id = int(admin_id)
            except:
                passed += f"<blockquote><b>Invalid ID: <code>{admin_id}</code></b></blockquote>\n"
                continue

            if id in admin_ids:
                await codeflixbots.del_admin(id)
                passed += f"<blockquote><code>{id}</code> ✅ Removed</blockquote>\n"
            else:
                passed += f"<blockquote><b>ID <code>{id}</code> not found in admin list.</b></blockquote>\n"

        await pro.edit(f"<b>⛔️ Admin removal result:</b>\n\n{passed}", reply_markup=reply_markup)
    else:
        await pro.edit("<b><blockquote>No admin IDs available to delete.</blockquote></b>", reply_markup=reply_markup)


@Client.on_message(filters.command('admins') & filters.private & admin)
async def get_admins(client: Client, message: Message):
    pro = await message.reply("<b><i>ᴘʟᴇᴀsᴇ ᴡᴀɪᴛ..</i></b>", quote=True)
    admin_ids = await codeflixbots.get_all_admins()

    if not admin_ids:
        admin_list = "<b><blockquote>❌ No admins found.</blockquote></b>"
    else:
        admin_list = "\n".join(f"<b><blockquote>ID: <code>{id}</code></blockquote></b>" for id in admin_ids)

    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("ᴄʟᴏsᴇ", callback_data="close")]])
    await pro.edit(f"<b>⚡ Current Admin List:</b>\n\n{admin_list}", reply_markup=reply_markup)

@Client.on_message(filters.private & filters.command("restart") & filters.private & admin)
async def restart_bot(b, m):
    global is_restarting
    if not is_restarting:
        is_restarting = True
        await m.reply_text("**Hᴇʏ...!! Oᴡɴᴇʀ/Aᴅᴍɪɴ Jᴜsᴛ ʀᴇʟᴀx ɪᴀᴍ ʀᴇsᴛᴀʀᴛɪɴɢ...!!**")
        # Gracefully stop the bot's event loop
        b.stop()
        time.sleep(2)
        # Restart the bot process
        os.execl(sys.executable, sys.executable, *sys.argv)
        

@Client.on_message(filters.private & filters.command(["tutorial"]))
async def tutorial(bot, message):
    user_id = message.from_user.id
    format_template = await codeflixbots.get_format_template(user_id)
    await message.reply_text(
        text=Config.FILE_NAME_TXT.format(format_template=format_template),
        disable_web_page_preview=True,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("•Sᴜᴘᴘᴏʀᴛ•", url="https://t.me/BOTSKINGDOMSGROUP"), InlineKeyboardButton("•⚡Main hub•", url="https://t.me/botskingdoms")]
        ])
    )

@Client.on_message(filters.command(["stats", "status"]) & filters.private & admin)
async def get_stats(bot, message):
    total_users = await codeflixbots.total_users_count()
    uptime = time.strftime("%Hh%Mm%Ss", time.gmtime(time.time() - bot.uptime))
    start_t = time.time()
    st = await message.reply('**Accessing The Details.....**')
    end_t = time.time()
    time_taken_s = (end_t - start_t) * 1000
    await st.edit(text=f"**Bᴏᴛ Sᴛᴀᴛᴜꜱ:** \n\n**➲ Bᴏᴛ Uᴘᴛɪᴍᴇ:** `{uptime}` \n**➲ Pɪɴɢ:** `{time_taken_s:.3f} ms` \n**➲ Vᴇʀsɪᴏɴ:** 2.0.0 \n**➲ Tᴏᴛᴀʟ Uꜱᴇʀꜱ:** `{total_users}`")

@Client.on_message(filters.command("broadcast") & filters.private & admin & filters.reply)
async def broadcast_handler(bot: Client, m: Message):
    await bot.send_message(Config.LOG_CHANNEL, f"Bʀᴏᴀᴅᴄᴀsᴛ Sᴛᴀʀᴛᴇᴅ Bʏ {m.from_user.mention} or {m.from_user.id}")
    all_users = await codeflixbots.get_all_users()
    broadcast_msg = m.reply_to_message
    sts_msg = await m.reply_text("**Bʀᴏᴀᴅᴄᴀsᴛ Sᴛᴀʀᴛᴇᴅ...!!**") 
    done = 0
    failed = 0
    success = 0
    start_time = time.time()
    total_users = await codeflixbots.total_users_count()
    async for user in all_users:
        sts = await send_msg(user['_id'], broadcast_msg)
        if sts == 200:
           success += 1
        else:
           failed += 1
        if sts == 400:
           await codeflixbots.delete_user(user['_id'])
        done += 1
        if not done % 20:
           await sts_msg.edit(f"Broadcast In Progress: \n\nTotal Users {total_users} \nCompleted : {done} / {total_users}\nSuccess : {success}\nFailed : {failed}")
    completed_in = datetime.timedelta(seconds=int(time.time() - start_time)) # Corrected to datetime.timedelta
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

# --- Ban User Command ---
@Client.on_message(filters.command("ban") & filters.private & admin)
async def ban_user(bot, message):
    try:
        parts = message.text.split(maxsplit=2)
        user_id = int(parts[1])
        reason = parts[2] if len(parts) > 2 else "No reason provided"
        await codeflixbots.col.update_one(
            {"_id": user_id},
            {"$set": {
                "ban_status.is_banned": True,
                "ban_status.ban_reason": reason,
                "ban_status.banned_on": datetime.date.today().isoformat() # Corrected to datetime.date.today()
            }},
            upsert=True
        )
        await message.reply_text(f"**Usᴇʀ - `{user_id}` Is sᴜᴄᴄᴇssғᴜʟʟʏ ʙᴀɴɴᴇᴅ.\nRᴇᴀsᴏɴ:- {reason}**")
    except Exception as e:
        await message.reply_text(f"Dᴜᴅᴇ ᴜsᴇ ɪᴛ ʟɪᴋᴇ ᴛʜɪs /ban <ᴜsᴇʀ_ɪᴅ> ʀᴇᴀsᴏɴ")

# --- Unban User Command ---
@Client.on_message(filters.command("unban") & filters.private & admin)
async def unban_user(bot, message):
    try:
        user_id = int(message.text.split()[1])
        await codeflixbots.col.update_one(
            {"_id": user_id},
            {"$set": {
                "ban_status.is_banned": False,
                "ban_status.ban_reason": "",
                "ban_status.banned_on": None
            }}
        )
        await message.reply_text(f"**Usᴇʀ - `{user_id}` Is sᴜᴄᴄᴇssғᴜʟʟʏ ᴜɴʙᴀɴɴᴇᴅ.**")
    except Exception as e:
        await message.reply_text(f"Dᴜᴅᴇ ᴜsᴇ ɪᴛ ʟɪᴋᴇ ᴛʜɪs /unban <ᴜsᴇʀ_ɪᴅ>")

#banned user status 

@Client.on_message(filters.command("banned") & filters.private & admin)
async def banned_list(bot, message):
    msg = await message.reply("**Pʟᴇᴀsᴇ ᴡᴀɪᴛ...**")
    cursor = codeflixbots.col.find({"ban_status.is_banned": True})
    lines = []
    async for user in cursor:
        uid = user['_id']
        reason = user.get('ban_status', {}).get('ban_reason', '')
        try:
            user_obj = await bot.get_users(uid)
            name = user_obj.mention  # clickable name
        except PeerIdInvalid:
            name = f"`{uid}` (Name not found)"
        lines.append(f"• {name} - {reason}")
    
    if not lines:
        await msg.edit("**Nᴏ ᴜsᴇʀ(s) ɪs ᴄᴜʀʀᴇɴᴛʟʏ ʙᴀɴɴᴇᴅ**")
    else:
        await msg.edit("🚫 **Bᴀɴɴᴇᴅ ᴜsᴇʀ(s)**\n\n" + "\n".join(lines[:50]))

@Client.on_message((filters.group | filters.private) & filters.command("leaderboard"))
async def leaderboard_handler(bot: Client, message: Message):
    try:
        user_id = message.from_user.id if message.from_user else None
        
        async def generate_leaderboard(filter_type):
            pipeline = []
            current_time = datetime.datetime.now() 
            
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
                users = await codeflixbots.col.aggregate(pipeline).to_list(10)
            elif filter_type == "lifetime":
                users = await codeflixbots.col.find().sort("rename_count", -1).limit(10).to_list(10)
            else: 
                users = await codeflixbots.col.find().sort("rename_count", -1).limit(10).to_list(10)
            
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

                    user_data = await codeflixbots.col.aggregate(user_data_pipeline_for_current_user).to_list(1)
                    
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
                        
                        higher_count_docs = await codeflixbots.col.aggregate(higher_count_pipeline).to_list(None)
                        user_rank = len(higher_count_docs) + 1
                else: 
                    user_data = await codeflixbots.col.find_one({"_id": user_id})
                    if user_data:
                        user_count = user_data.get("rename_count", 0)
                        higher_count = await codeflixbots.col.count_documents({"rename_count": {"$gt": user_count}})
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
            
            leaderboard.append(f"\nLᴀsᴛ ᴜᴘᴅᴀᴛᴇᴅ: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")
            leaderboard.append(f"\n<i>**Tʜɪs ᴍᴇssᴀɢᴇ ᴡɪʟʟ ᴀᴜᴛᴏ-ᴅᴇʟᴇᴛᴇ ɪɴ {Config.LEADERBOARD_DELETE_TIMER} sᴇᴄᴏɴᴅs**</i>")
            
            return "\n".join(leaderboard)

        # Call the generate_leaderboard function, but it will always use "lifetime" now
        leaderboard_text = await generate_leaderboard("lifetime")
        
        if not leaderboard_text:
            no_data_msg = await message.reply_text("<blockquote>Nᴏ ʟᴇᴀᴅᴇʀʙᴏᴀʀᴅ ᴅᴀᴛᴀ ᴀᴠᴀɪʟᴀʙʟᴇ ʏᴇᴛ!</blockquote>")
            await asyncio.sleep(10)
            await no_data_msg.delete()
            return
        
        # FIX: Removed reply_markup=keyboard from the reply_text call
        sent_msg = await message.reply_photo(
            photo=Config.LEADERBOARD_PIC, 
            caption=leaderboard_text
        )
        
        # NOTE: The leaderboard_callback function is no longer needed or registered, 
        # so it has been removed.
        
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
