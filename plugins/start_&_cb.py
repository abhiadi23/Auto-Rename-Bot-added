import requests
import random
import asyncio
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

logger = logging.getLogger(__name__)
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
                "Wᴛғ ʏᴏᴜ ᴀʀᴇ ʙᴀɴɴᴇᴅ ғʀᴏᴍ ᴜsɪɴɢ ᴍᴇ ʙʏ ᴏᴜʀ ᴀᴅᴍɪɴ/ᴏᴡɴᴇʀ . Iғ ʏᴏᴜ ᴛʜɪɴᴋs ɪᴛ's ᴍɪsᴛᴀᴋᴇ ᴄʟɪᴄᴋ ᴏɴ **ᴄᴏɴᴛᴀᴄᴛ ʜᴇʀᴇ...!!**",
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
            await message.reply_text(f"An unexpected error occurred: `{e}`. Please contact the developer.")
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
    await codeflixbots.add_user(client, message)

    m = await message.reply_text("Wᴇᴡ...Hᴏᴡ ᴀʀᴇ ʏᴏᴜ ᴅᴜᴅᴇ \nᴡᴀɪᴛ ᴀ ᴍᴏᴍᴇɴᴛ. . .")
    await asyncio.sleep(0.4)
    await m.edit_text("🎊")
    await asyncio.sleep(0.5)
    await m.edit_text("⚡")
    await asyncio.sleep(0.5)
    await message.reply_chat_action(ChatAction.CHOOSE_STICKER)
    await asyncio.sleep(3)
    await m.edit_text("**Iᴀᴍ sᴛᴀʀᴛɪɴɢ...!!**")
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


async def get_shortlink(link, is_second_shortener=False):
    """Generate a shortlink using the configured shortener from verification settings."""
    settings = await codeflixbots.get_verification_settings()
    verify_status_1 = settings.get("verify_status_1", False)
    verify_status_2 = settings.get("verify_status_2", False)
    
    # Choose shortener based on is_second_shortener and status
    if is_second_shortener:
        if not verify_status_2:
            logger.error("Shortener 2 is disabled")
            return None
        api, site = settings.get("verify_token_2", "Not set"), settings.get("api_link_2", "Not set")
    else:
        if not verify_status_1:
            logger.error("Shortener 1 is disabled")
            return None
        api, site = settings.get("verify_token_1", "Not set"), settings.get("api_link_1", "Not set")
    
    if site == "Not set" or api == "Not set":
        logger.error(f"Shortener settings missing: {site} or {api}")
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

@Client.on_message(filters.command("verify") & filters.private)
async def verify_command(client, message: Message):
    user_id = message.from_user.id
    user_data = await codeflixbots.col.find_one({"_id": user_id}) or {}
    
    # Check verification status
    verification_data = user_data.get("verification", {})
    shortener1_time = verification_data.get("shortener1_time")
    shortener2_time = verification_data.get("shortener2_time")
    current_time = datetime.utcnow()
    
    # Check if fully verified (both shorteners done within 24 hours)
    if shortener1_time and shortener2_time:
        if current_time < shortener1_time + timedelta(hours=24):
            await message.reply_text("You are already fully verified for the next 24 hours!")
            return
    
    # Check if Shortener 1 is verified and waiting for Shortener 2 (6-hour gap)
    if shortener1_time and not shortener2_time:
        time_diff = current_time - shortener1_time
        if time_diff < timedelta(hours=6):
            remaining = timedelta(hours=6) - time_diff
            await message.reply_text(
                f"Please wait {remaining.seconds // 3600} hours and {(remaining.seconds % 3600) // 60} minutes before verifying Shortener 2."
            )
            return
    
    # Check if shorteners are enabled
    settings = await codeflixbots.get_verification_settings()
    verify_status_1 = settings.get("verify_status_1", False)
    verify_status_2 = settings.get("verify_status_2", False)
    
    # Determine which shortener to use
    is_second_shortener = bool(shortener1_time)
    if is_second_shortener and not verify_status_2:
        await message.reply_text("Shortener 2 is currently disabled. Please try again later.")
        return
    if not is_second_shortener and not verify_status_1:
        await message.reply_text("Shortener 1 is currently disabled. Please try again later.")
        return
    
    shortener_name = "Shortener 2" if is_second_shortener else "Shortener 1"
    
    # Generate shortlink
    base_url = "https://t.me/" + Config.BOT_USERNAME + "?start=verify_" + str(user_id)
    shortlink = await get_shortlink(base_url, is_second_shortener)
    
    if not shortlink:
        await message.reply_text(
            "Error generating shortlink. Please try again later or contact @seishiro_obito."
        )
        return
    
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"Verify {shortener_name}", url=shortlink)],
        [InlineKeyboardButton("Check Verification", callback_data="check_verify")]
    ])
    
    await message.reply_text(
        f"Please verify using {shortener_name} to proceed.\n"
        "Click the button below and complete the verification process.",
        reply_markup=buttons
    )

@Client.on_callback_query(filters.regex("check_verify"))
async def check_verify_callback(client, callback_query):
    user_id = callback_query.from_user.id
    current_time = datetime.utcnow()
    
    user_data = await codeflixbots.col.find_one({"_id": user_id}) or {}
    verification_data = user_data.get("verification", {})
    
    shortener1_time = verification_data.get("shortener1_time")
    shortener2_time = verification_data.get("shortener2_time")
    
    if shortener1_time and shortener2_time:
        if current_time < shortener1_time + timedelta(hours=24):
            await callback_query.message.edit_text(
                "Verification complete! You are verified for 24 hours."
            )
        else:
            await codeflixbots.col.update_one(
                {"_id": user_id},
                {"$unset": {"verification": ""}}
            )
            await callback_query.message.edit_text(
                "Verification expired. Please use /verify to start again."
            )
    elif shortener1_time:
        await codeflixbots.col.update_one(
            {"_id": user_id},
            {"$set": {"verification.shortener2_time": current_time}}
        )
        await callback_query.message.edit_text(
            "Shortener 2 verified! You are now fully verified for 24 hours."
        )
    else:
        await codeflixbots.col.update_one(
            {"_id": user_id},
            {"$set": {"verification.shortener1_time": current_time}}
        )
        await callback_query.message.edit_text(
            "Shortener 1 verified! Please verify Shortener 2 after 6 hours using /verify."
        )
    
    await callback_query.answer()
    
