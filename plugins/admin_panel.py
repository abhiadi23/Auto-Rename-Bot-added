from config import Config, Txt
from helper.database import codeflixbots
from pyrogram.types import Message
from pyrogram import Client, filters
from pyrogram.errors import FloodWait, InputUserDeactivated, UserIsBlocked, PeerIdInvalid
import os, sys, time, asyncio, logging
import datetime # Keep this for datetime.date.today() and datetime.timedelta
from datetime import timedelta # Explicitly import timedelta for cleaner usage
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from functools import wraps
import html # Import html for escaping names

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

ADMIN_USER_ID = Config.ADMIN
ADMIN_URL = Config.ADMIN_URL # Assuming ADMIN_URL is defined in Config

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

@Client.on_message(filters.private & filters.command("restart") & filters.user(ADMIN_USER_ID))
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
        text=Txt.FILE_NAME_TXT.format(format_template=format_template),
        disable_web_page_preview=True,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("•Sᴜᴘᴘᴏʀᴛ•", url="https://t.me/BOTSKINGDOMSGROUP"), InlineKeyboardButton("•⚡Main hub•", url="https://t.me/botskingdoms")]
        ])
    )

@Client.on_message(filters.command(["stats", "status"]) & filters.user(Config.ADMIN))
async def get_stats(bot, message):
    total_users = await codeflixbots.total_users_count()
    uptime = time.strftime("%Hh%Mm%Ss", time.gmtime(time.time() - bot.uptime))
    start_t = time.time()
    st = await message.reply('**Accessing The Details.....**')
    end_t = time.time()
    time_taken_s = (end_t - start_t) * 1000
    await st.edit(text=f"**--Bot Status--** \n\n**⌚️ Bot Uptime :** {uptime} \n**🐌 Current Ping :** `{time_taken_s:.3f} ms` \n**👭 Total Users :** `{total_users}`")

@Client.on_message(filters.command("broadcast") & filters.user(Config.ADMIN) & filters.reply)
async def broadcast_handler(bot: Client, m: Message):
    await bot.send_message(Config.LOG_CHANNEL, f"{m.from_user.mention} or {m.from_user.id} Is Started The Broadcast......")
    all_users = await codeflixbots.get_all_users()
    broadcast_msg = m.reply_to_message
    sts_msg = await m.reply_text("Broadcast Started..!") 
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
@Client.on_message(filters.command("ban") & filters.user(Config.ADMIN))
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
@Client.on_message(filters.command("unban") & filters.user(Config.ADMIN))
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

@Client.on_message(filters.command("banned") & filters.user(Config.ADMIN))
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
        # time_filter = "lifetime" # This variable is not actually used to determine the initial filter.
                                 # The generate_leaderboard function is called with "lifetime" directly.

        async def generate_leaderboard(filter_type):
            pipeline = []
            current_time = datetime.datetime.now() # Corrected: Use datetime.datetime.now()
            
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
            
            # For lifetime, no initial date filter is needed, but we still need the group stage for aggregation.
            # Assuming 'rename_count' is directly stored for 'lifetime' or calculated via the pipeline.
            if filter_type != "lifetime":
                pipeline.extend([
                    {"$group": {
                        "_id": "$_id",
                        "rename_count": {"$sum": 1},
                        "first_name": {"$first": "$first_name"}, # These fields need to be present in the documents
                        "username": {"$first": "$username"} # if you want to use them in the group stage.
                    }},
                     {"$sort": {"rename_count": -1}}, # Sort after grouping
                     {"$limit": 10} # Limit after sorting
                ])
            # Note: The logic for fetching users based on 'pipeline' vs. 'find()' was a bit convoluted.
            # Simplified below to ensure proper query execution.
            
            if pipeline and filter_type != "lifetime": # Execute pipeline for filtered views
                # The 'codeflixbots.col.aggregate(pipeline)' part needs to be the correct collection for the data.
                # Assuming 'Botskingdom.col' was a typo and should be 'codeflixbots.col'
                users = await codeflixbots.col.aggregate(pipeline).to_list(10)
            elif filter_type == "lifetime":
                users = await codeflixbots.col.find().sort("rename_count", -1).limit(10).to_list(10)
            else: # Fallback, should ideally not be reached if filter_type is always one of the specified
                users = await codeflixbots.col.find().sort("rename_count", -1).limit(10).to_list(10)
            
            if not users:
                return None
            
            user_rank = None
            user_count = 0
            
            if user_id:
                if filter_type != "lifetime": # Logic for filtered leaderboards
                    # Re-constructing the pipeline for the specific user's count and rank based on the filter.
                    # This needs to be carefully constructed to avoid counting across the entire collection
                    # when a time-based filter is active.
                    user_data_pipeline_for_current_user = [
                        {"$match": {"_id": user_id, "rename_timestamp": {"$gte": start_time}}}
                    ]
                    # If we already have a grouping for count, we can reuse that for the user's data
                    user_data_pipeline_for_current_user.extend([
                        {"$group": {
                            "_id": "$_id",
                            "rename_count": {"$sum": 1}
                        }}
                    ])

                    user_data = await codeflixbots.col.aggregate(user_data_pipeline_for_current_user).to_list(1)
                    
                    if user_data:
                        user_count = user_data[0].get("rename_count", 0)
                        
                        # To find rank, count users with higher rename_count within the same filter
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
                else: # Logic for lifetime leaderboard
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
                except Exception: # Catch general exceptions during get_users to avoid crashes
                    name = html.escape(user.get('first_name', 'Anonymous').strip())
                    username = f"@{user['username']}" if user.get('username') else "No UN"
                
                leaderboard.append(
                    f"{idx}. <b>{name}</b> "
                    f"(<code>{username}</code>) ➜ "
                    f"<i>{count} ʀᴇɴᴀᴍᴇs</i>"
                )
            
            if user_rank:
                leaderboard.append(f"\n<b>Yᴏᴜʀ Rᴀɴᴋ:</b> {user_rank} ᴡɪᴛʜ {user_count} ʀᴇɴᴀᴍᴇs")
            
            leaderboard.append(f"\nLᴀsᴛ ᴜᴘᴅᴀᴛᴇᴅ: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}") # Corrected: Use datetime.datetime.now()
            leaderboard.append(f"\n<i>**Tʜɪs ᴍᴇssᴀɢᴇ ᴡɪʟʟ ᴀᴜᴛᴏ-ᴅᴇʟᴇᴛᴇ ɪɴ {Config.LEADERBOARD_DELETE_TIMER} sᴇᴄᴏɴᴅs**</i>")
            
            return "\n".join(leaderboard)
        
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("Tᴏᴅᴀʏ", callback_data="lb_today"),
                InlineKeyboardButton("Wᴇᴇᴋ", callback_data="lb_week"),
                InlineKeyboardButton("Mᴏɴᴛʜ", callback_data="lb_month"),
                InlineKeyboardButton("Yᴇᴀʀ", callback_data="lb_year"),
                InlineKeyboardButton("Aʟʟ-Tɪᴍᴇ", callback_data="lb_lifetime")
            ]
        ])

        leaderboard_text = await generate_leaderboard("lifetime")
        
        if not leaderboard_text:
            no_data_msg = await message.reply_text("<blockquote>Nᴏ ʟᴇᴀᴅᴇʀʙᴏᴀʀᴅ ᴅᴀᴛᴀ ᴀᴠᴀɪʟᴀʙʟᴇ ʏᴇᴛ!</blockquote>")
            await asyncio.sleep(10)
            await no_data_msg.delete()
            return
        
        sent_msg = await message.reply_text(leaderboard_text, reply_markup=keyboard)
        
        # NOTE: Defining callbacks inside an event handler can lead to multiple registrations
        # if the command is triggered multiple times. For simple bots, it might work,
        # but for robustness, consider registering callbacks at the top level or
        # using a state management system.
        @bot.on_callback_query(filters.regex("^lb_"))
        async def leaderboard_callback(client, callback_query):
            if callback_query.from_user.id != message.from_user.id:
                await callback_query.answer("Tʜɪs ɪs ɴᴏᴛ ʏᴏᴜʀ ʟᴇᴀᴅᴇʀʙᴏᴀʀᴅ!", show_alert=True)
                return

            selected_filter = callback_query.data.split("_")[1]

            new_leaderboard = await generate_leaderboard(selected_filter)
            
            if not new_leaderboard:
                await callback_query.answer(f"Nᴏ ᴅᴀᴛᴀ ᴀᴠᴀɪʟᴀʙʟᴇ ғᴏʀ {selected_filter} ғɪʟᴛᴇʀ", show_alert=True)
                return
            
            await callback_query.message.edit_text(
                new_leaderboard,
                reply_markup=keyboard 
            )
            
            await callback_query.answer()
        
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
