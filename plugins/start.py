import requests
import random
import asyncio
import base64
import logging
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.enums import ChatAction, ChatMemberStatus
from pyrogram.errors import UserNotParticipant
from datetime import datetime, timedelta
from functools import wraps

from helper.database import codeflixbots
from config import Config
from .callbacks import cb_handler
from plugins.helper_func import *

chat_data_cache = {}
ADMIN_URL = Config.ADMIN_URL
FSUB_PIC = Config.FSUB_PIC
BOT_USERNAME = Config.BOT_USERNAME
OWNER_ID = Config.OWNER_ID
FSUB_LINK_EXPIRY = 10
active_tasks = {}

logger = logging.getLogger(name)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

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
                "Wᴛғ ʏᴏᴜ ᴀʀᴇ ʙᴀɴɴᴇᴅ ғʀᴏᴍ ᴜsɪɴɢ ᴍᴇ ʙʏ ᴏᴜʀ ᴀᴅᴍɪɴ/ᴏᴡɴᴇʀ . Iғ ʏᴏᴜ ᴛʜɪɴᴋs ɪᴛ's ᴍɪsᴛᴀᴋᴇ ᴄʟɪᴄᴋ ᴏɴ ᴄᴏɴᴛᴀᴄᴛ ʜᴇʀᴇ...!!",
                reply_markup=keyboard
            )
        return await func(client, message, *args, **kwargs)
    return wrapper

def check_fsub(func):
    @wraps(func)
    async def wrapper(client, message, *args, **kwargs):
        user_id = message.from_user.id
        logger.debug(f"check_fsub decorator called for user {user_id}")

        async def is_sub(client, user_id, channel_id):
            try:
                member = await client.get_chat_member(channel_id, user_id)
                return member.status in {
                    ChatMemberStatus.OWNER,
                    ChatMemberStatus.ADMINISTRATOR,
                    ChatMemberStatus.MEMBER
                }
            except UserNotParticipant:
                mode = await codeflixbots.get_channel_mode(channel_id)
                if mode == "on":
                    exists = await codeflixbots.req_user_exist(channel_id, user_id)
                    return exists
                return False
            except Exception as e:
                logger.error(f"Error in is_sub(): {e}")
                return False

        async def is_subscribed(client, user_id):
            channel_ids = await codeflixbots.show_channels()
            if not channel_ids:
                return True
            if user_id == OWNER_ID:
                return True
            for cid in channel_ids:
                if not await is_sub(client, user_id, cid):
                    mode = await codeflixbots.get_channel_mode(cid)
                    if mode == "on":
                        await asyncio.sleep(2)
                        if await is_sub(client, user_id, cid):
                            continue
                    return False
            return True
        
        try:
            is_sub_status = await is_subscribed(client, user_id)
            logger.debug(f"User {user_id} subscribed status: {is_sub_status}")
            
            if not is_sub_status:
                logger.debug(f"User {user_id} is not subscribed, calling not_joined.")
                return await not_joined(client, message)
            
            logger.debug(f"User {user_id} is subscribed, proceeding with function call.")
            return await func(client, message, *args, **kwargs)
        
        except Exception as e:
            logger.error(f"FATAL ERROR in check_fsub: {e}")
            await message.reply_text(f"An unexpected error occurred: {e}. Please contact the developer.")
            return

    return wrapper

async def check_admin(filter, client, update):
    try:
        user_id = update.from_user.id
        return any([user_id == OWNER_ID, await codeflixbots.admin_exist(user_id)])
    except Exception as e:
        logger.error(f"Exception in check_admin: {e}")
        return False

async def not_joined(client: Client, message: Message):
    logger.debug(f"not_joined function called for user {message.from_user.id}")
    temp = await message.reply("<b><i>ᴡᴀɪᴛ ᴀ sᴇᴄ..</i></b>")

    user_id = message.from_user.id
    buttons = []
    count = 0

    try:
        all_channels = await codeflixbots.show_channels()
        for chat_id in all_channels:
            await message.reply_chat_action(ChatAction.TYPING)

            is_member = False
            try:
                member = await client.get_chat_member(chat_id, user_id)
                is_member = member.status in {
                    ChatMemberStatus.OWNER,
                    ChatMemberStatus.ADMINISTRATOR,
                    ChatMemberStatus.MEMBER
                }
            except UserNotParticipant:
                is_member = False
            except Exception as e:
                is_member = False
                logger.error(f"Error checking member in not_joined: {e}")

            if not is_member:
                try:
                    if chat_id in chat_data_cache:
                        data = chat_data_cache[chat_id]
                    else:
                        data = await client.get_chat(chat_id)
                        chat_data_cache[chat_id] = data

                    name = data.title
                    mode = await codeflixbots.get_channel_mode(chat_id)

                    if mode == "on" and not data.username:
                        invite = await client.create_chat_invite_link(
                            chat_id=chat_id,
                            creates_join_request=True,
                            expire_date=datetime.utcnow() + timedelta(seconds=FSUB_LINK_EXPIRY) if FSUB_LINK_EXPIRY else None
                        )
                        link = invite.invite_link
                    else:
                        if data.username:
                            link = f"https://t.me/{data.username}"
                        else:
                            invite = await client.create_chat_invite_link(
                                chat_id=chat_id,
                                expire_date=datetime.utcnow() + timedelta(seconds=FSUB_LINK_EXPIRY) if FSUB_LINK_EXPIRY else None
                            )
                            link = invite.invite_link

                    buttons.append([InlineKeyboardButton(text=name, url=link)])
                    count += 1
                    await temp.edit(f"<b>{'! ' * count}</b>")

                except Exception as e:
                    logger.error(f"Error with chat {chat_id}: {e}")
                    await temp.edit(
                        f"<b><i>! Eʀʀᴏʀ, Cᴏɴᴛᴀᴄᴛ ᴅᴇᴠᴇʟᴏᴘᴇʀ ᴛᴏ sᴏʟᴠᴇ ᴛʜᴇ ɪssᴜᴇs @seishiro_obito</i></b>\n"
                        f"<blockquote expandable><b>Rᴇᴀsᴏɴ:</b> {e}</blockquote>"
                    )
                    return

        try:
            buttons.append([
                InlineKeyboardButton(
                    text='• Jᴏɪɴᴇᴅ •',
                    url=f"https://t.me/{Config.BOT_USERNAME}?start=true"
                )
            ])
        except IndexError:
            pass

        text = "<b>Yᴏᴜ Bᴀᴋᴋᴀᴀ...!! \n\n<blockquote>Jᴏɪɴ ᴍʏ ᴄʜᴀɴɴᴇʟ ᴛᴏ ᴜsᴇ ᴍʏ ᴏᴛʜᴇʀᴡɪsᴇ Yᴏᴜ ᴀʀᴇ ɪɴ ʙɪɢ sʜɪᴛ...!!</blockquote></b>"
        await temp.delete()
        
        logger.debug(f"Sending final reply photo to user {user_id}")
        await message.reply_photo(
            photo=FSUB_PIC,
            caption=text,
            reply_markup=InlineKeyboardMarkup(buttons),
        )

except Exception as e:
        logger.error(f"Final Error in not_joined: {e}")
        await temp.edit(
            f"<b><i>! Eʀʀᴏʀ, Cᴏɴᴛᴀᴄᴛ ᴅᴇᴠᴇʟᴏᴘᴇʀ ᴛᴏ sᴏʟᴠᴇ ᴛʜᴇ ɪssᴜᴇs @seishiro_obito</i></b>\n"
            f"<blockquote expandable><b>Rᴇᴀsᴏɴ:</b> {e}</blockquote>"
        )

@Client.on_message(filters.private & filters.command("start"))
@check_ban
@check_fsub
async def start(client, message: Message):
    logger.debug(f"/start command received from user {message.from_user.id}")
    user_id = message.from_user.id
            
            text = message.text
            if len(text) > 7:
        try:
            base64_string = text.split(" ", 1)[1]
            verify_request = base64_string.startswith("verify_")
            
            if verify_request:
                base64_string = base64_string[4:]
                msg_id = range(start, end + 1) if start <= end else list(range(start, end - 1, -1))
            except Exception as e:
                print(f"Error decoding IDs: {e}")
                return

# Get verification settings
    settings = await codeflixbots.get_verification_settings()
    verify_status_1 = settings.get("verify_status_1", False)
    verify_status_2 = settings.get("verify_status_2", False)
    
    # Get available shorteners
    available_shorteners = []
    if verify_status_1:
        available_shorteners.append(1)
    if verify_status_2:
        available_shorteners.append(2)
    
    # Randomly select a shortener from available ones
    selected_shortener = random.choice(available_shorteners)
    shortener_name = f"Sʜᴏʀᴛᴇɴᴇʀ {selected_shortener}"
    
# This is the URL that shortener will redirect to after verification
    base_url = f"https://t.me/{Config.BOT_USERNAME}?start=verify_{base64_string}"
    shortlink = await get_shortlink(base_url, selected_shortener)

    if not verify_status_1 and not verify_status_2:
        pass
    
    # Store verify attempt to track callback
    current_time = datetime.utcnow()
    await codeflixbots.col.update_one(
        {"_id": user_id},
        {"$set": {
            "verification.last_verify_attempt": {
                "time": current_time,
                "base64_string": base64_string
            }
        }},
        upsert=True
    )
    
    # Send button with shortlink directly
    buttons = InlineKeyboardMarkup([[
        InlineKeyboardButton("• Vᴇʀɪғʏ •", url=shortlink)
    ]])


    if not await is_user_verified(user_id):
    await message.reply_text(
        "ʜᴇʏ {message.from_user.mention}, \n\n‼️ ʏᴏᴜ'ʀᴇ ɴᴏᴛ ᴠᴇʀɪғɪᴇᴅ ᴛᴏᴅᴀʏ ‼️
        "⚠️ Yᴏᴜ ɴᴇᴇᴅ ᴛᴏ ᴠᴇʀɪғʏ ғɪʀsᴛ ᴛᴏ ɢᴇᴛ ᴛʜᴇ ᴀᴄᴄᴇss ᴏғ ʀᴇɴᴀᴍɪɴɢ ᴛʜᴇ ғɪʟᴇs \n\n"
        "Cʟɪᴄᴋ ᴛʜᴇ ʙᴜᴛᴛᴏɴ ʙᴇʟᴏᴡ ᴛᴏ ᴠᴇʀɪғʏ.\n\n"
        "⏰ <b>Lɪɴᴋ ᴇxᴘɪʀᴇs ɪɴ 24 ʜᴏᴜʀs</b>",
        reply_markup=buttons
    )
    
    if not shortlink:
        await message.reply_text(
            "Eʀʀᴏʀ ɢᴇɴᴇʀᴀᴛɪɴɢ sʜᴏʀᴛʟɪɴᴋ. Pʟᴇᴀsᴇ ᴛʀʏ ᴀɢᴀɪɴ ʟᴀᴛᴇʀ ᴏʀ ᴄᴏɴᴛᴀᴄᴛ @seishiro_obito."
        )
        return
    
async def process_verify_request(client, message: Message, base64_string: str):
    """Process verification request."""
    user_id = message.from_user.id
    
    if await is_user_verified(user_id):
        await message.reply_text(
            "›› ʏᴏᴜʀ ᴛᴏᴋᴇɴ ʜᴀs ʙᴇᴇɴ sᴜᴄᴄᴇssғᴜʟʟʏ ᴠᴇʀɪғɪᴇᴅ ᴀɴᴅ ɪs ᴠᴀʟɪᴅ ғᴏʀ 24ʜᴏᴜʀs ‼️",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("•Sᴇᴇ ᴘʟᴀɴs •", callback_data="seeplan")
            ]])
        )
        return

async def handle_verification_callback(client, message: Message, base64_string: str):
    """Handle when user returns after completing verification through shortlink"""
    user_id = message.from_user.id
    current_time = datetime.utcnow()
    
    # Get user data
    user_data = await codeflixbots.col.find_one({"_id": user_id}) or {}
    verification_data = user_data.get("verification", {})
    
    # Update verification time (24 hour validity)
    await codeflixbots.col.update_one(
        {"_id": user_id},
        {"$set": {"verification.verified_time": current_time}},
        upsert=True
    )
            
    await codeflixbots.add_user(client, message)

    m = await message.reply_text("Wᴇᴡ...Hᴏᴡ ᴀʀᴇ ʏᴏᴜ ᴅᴜᴅᴇ \nᴡᴀɪᴛ ᴀ ᴍᴏᴍᴇɴᴛ. . .")
    await asyncio.sleep(0.4)
    await m.edit_text("🎊")
    await asyncio.sleep(0.5)
    await m.edit_text("⚡")
    await asyncio.sleep(0.5)
    await message.reply_chat_action(ChatAction.CHOOSE_STICKER)
    await asyncio.sleep(3)
    await m.edit_text("Iᴀᴍ sᴛᴀʀᴛɪɴɢ...!!")
    await asyncio.sleep(0.4)
    await m.delete()

    await message.reply_sticker("CAACAgUAAxkBAAEOtVNoUAphgIzDsgHV10rbfmFKNIgMlwACPQsAApWaqVbHL7SvWBBaITYE")

    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("• ᴍʏ ᴀʟʟ ᴄᴏᴍᴍᴀɴds •", callback_data='help')
        ],
        [
            InlineKeyboardButton('• ᴜᴘᴅᴀᴛᴇs', url='https://t.me/botskingdoms'),

InlineKeyboardButton('sᴜᴘᴘᴏʀᴛ •', url='https://t.me/botskingdomsgroup')
        ],
        [
            InlineKeyboardButton('• ᴀʙᴏᴜᴛ', callback_data='about'),
            InlineKeyboardButton('Dᴇᴠᴇʟᴏᴘᴇʀ•', url='https://t.me/botskingdoms')
        ]
    ])

    if Config.START_PIC:
        await message.reply_photo(
            Config.START_PIC,
            caption=Config.START_TXT.format(first=message.from_user.first_name,
                last=message.from_user.last_name,
                username=None if not message.from_user.username else '@' + message.from_user.username,
                mention=message.from_user.mention,
                id=message.from_user.id
            ),
            reply_markup=buttons)
    else:
        await message.reply_text(
            text=Config.START_TXT.format(first=message.from_user.first_name,
                last=message.from_user.last_name,
                username=None if not message.from_user.username else '@' + message.from_user.username,
                mention=message.from_user.mention,
                id=message.from_user.id
            ),
            reply_markup=buttons,
            disable_web_page_preview=True)

@Client.on_message(filters.command("cancel"))
async def cancel_handler(client, message):
    user_id = message.from_user.id
    
    if user_id in active_tasks:
        task = active_tasks.pop(user_id)
        task.cancel()
        await message.reply_text("Pʀᴏᴄᴇss ᴄᴀɴᴄᴇʟʟᴇᴅ...!!")
    else:
        await message.reply_text("Nᴏ ᴀᴄᴛɪᴠᴇ ᴘʀᴏᴄᴇss ᴛᴏ ᴄᴀɴᴄᴇʟ...!!")

@Client.on_message(filters.command("verify_settings") & admin)
async def verify_settings(client, message):
    user_id = message.from_user.id
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("ᴠᴇʀɪꜰʏ 𝟷", callback_data="verify_1_cbb"), InlineKeyboardButton("ᴠᴇʀɪꜰʏ 𝟸", callback_data="verify_2_cbb")],
        [InlineKeyboardButton("ᴄᴏᴜɴᴛs", callback_data="verify_count")]
    ])
    await message.reply_text(
        "ʜᴇʀᴇ ʏᴏᴜ ᴄᴀɴ ᴍᴀɴᴀɢᴇ ʏᴏᴜʀ ᴠᴇʀɪꜰɪᴄᴀᴛɪᴏɴ ᴘʀᴏᴄᴇꜱꜱ:\n\n ➲ ʏᴏᴜ ᴄᴀɴ ᴅᴏ ᴛᴜʀɴ ᴏɴ/ᴏꜰꜰ ᴠᴇʀɪꜰɪᴄᴀᴛɪᴏɴ ᴘʀᴏᴄᴇꜱꜱ & Aʟsᴏ ʏᴏᴜ ᴄᴀɴ sᴇᴇ ᴄᴏᴜɴᴛs.",
        reply_markup=keyboard,
        disable_web_page_preview=True)


async def get_shortlink(link, shortener_num):
    """Generate a shortlink using the specified shortener (1 or 2)"""
    settings = await codeflixbots.get_verification_settings()
    
    if shortener_num == 1:
        api = settings.get("verify_token_1", "Not set")
        site = settings.get("api_link_1", "Not set")
    else:
        api = settings.get("verify_token_2", "Not set")
        site = settings.get("api_link_2", "Not set")
    
    if site == "Not set" or api == "Not set":
        logger.error(f"Shortener {shortener_num} settings missing: {site} or {api}")
        return None
    
    try:
        resp = requests.get(f"https://{site}/api?api={api}&url={link}").json()
        if resp.get('status') == 'success' and 'shortenedUrl' in resp:
            return resp['shortenedUrl']
        else:
            logger.error(f"Shortlink API error: {resp}")
            return None
    except Exception as e:
        logger.error(f"Error generating shortlink: {e}")
        try:
            resp = requests.get(f"https://{site}/api?api={api}&url={link}").json()
            return resp.get('shortenedUrl') if resp.get('status') == 'success' else None
        except Exception as e2:
            logger.error(f"Fallback shortlink failed: {e2}")
            return None


async def is_user_verified(user_id):
    """Check if user has valid verification (within 24 hours)"""
    user_data = await codeflixbots.col.find_one({"_id": user_id}) or {}
    verification_data = user_data.get("verification", {})
    verified_time = verification_data.get("verified_time")
    
    if not verified_time:
        return False
    
    current_time = datetime.utcnow()
    time_diff = current_time - verified_time
    
    # Check if verification is still valid (within 24 hours)
    return time_diff < timedelta(hours=24)

@Client.on_message(filters.command("verify") & filters.private)
async def verify_command(client, message: Message):
    """Check verification status"""
    user_id = message.from_user.id
    
    # Check if user is already verified
    if await is_user_verified(user_id):
        user_data = await codeflixbots.col.find_one({"_id": user_id}) or {}
        verification_data = user_data.get("verification", {})
        verified_time = verification_data.get("verified_time")
        
        if verified_time:
            current_time = datetime.utcnow()
            time_left = timedelta(hours=24) - (current_time - verified_time)
            hours_left = time_left.seconds // 3600
            minutes_left = (time_left.seconds % 3600) // 60
            
            await message.reply_text(
                f""›› ʏᴏᴜʀ ᴛᴏᴋᴇɴ ʜᴀs ʙᴇᴇɴ sᴜᴄᴄᴇssғᴜʟʟʏ ᴠᴇʀɪғɪᴇᴅ ᴀɴᴅ ɪs ᴠᴀʟɪᴅ ғᴏʀ 24ʜᴏᴜʀs ‼️",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("•Sᴇᴇ ᴘʟᴀɴs •", callback_data="seeplan")
            ]]))
    else:
# Send button with shortlink directly
    buttons = InlineKeyboardMarkup([[
        InlineKeyboardButton("• Vᴇʀɪғʏ •", url=shortlink)
    ]])
        await message.reply_text(
            "ʜᴇʏ {message.from_user.mention}, \n\n‼️ ʏᴏᴜ'ʀᴇ ɴᴏᴛ ᴠᴇʀɪғɪᴇᴅ ᴛᴏᴅᴀʏ ‼️
        "⚠️ Yᴏᴜ ɴᴇᴇᴅ ᴛᴏ ᴠᴇʀɪғʏ ғɪʀsᴛ ᴛᴏ ɢᴇᴛ ᴛʜᴇ ᴀᴄᴄᴇss ᴏғ ʀᴇɴᴀᴍɪɴɢ ᴛʜᴇ ғɪʟᴇs \n\n"
        "Cʟɪᴄᴋ ᴛʜᴇ ʙᴜᴛᴛᴏɴ ʙᴇʟᴏᴡ ᴛᴏ ᴠᴇʀɪғʏ.\n\n"
        "⏰ <b>Lɪɴᴋ ᴇxᴘɪʀᴇs ɪɴ 24 ʜᴏᴜʀs</b>", reply_markup=buttons)
