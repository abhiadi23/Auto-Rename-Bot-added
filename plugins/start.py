import requests
import random
import asyncio
import base64
import logging
import string
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.enums import ChatAction, ChatMemberStatus
from pyrogram.errors import UserNotParticipant
from datetime import datetime, timedelta
from functools import wraps

from helper.database import *
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
                "Wᴛғ ʏᴏᴜ ᴀʀᴇ ʙᴀɴɴᴇᴅ ғʀᴏᴍ ᴜsɪɴɢ ᴍᴇ ʙʏ ᴏᴜʀ ᴀᴅᴍɪɴ/ᴏᴡɴᴇʀ . Iғ ʏᴏᴜ ᴛʜɪɴᴋs ɪᴛ's ᴍɪsᴛᴀᴋᴇ ᴄʟɪᴄᴋ ᴏɴ ᴄᴏɴᴛᴀᴄᴛ ʜᴇʀᴇ...!!",
                reply_markup=keyboard
            )
        return await func(client, message, *args, **kwargs)
    return wrapper

async def check_user_premium(user_id):
    """Check if user has premium access - handles missing method gracefully"""
    try:
        # First check if the method exists
        if hasattr(codeflixbots, 'has_premium_access'):
            return await codeflixbots.has_premium_access(user_id)
        else:
            # Fallback: Check database directly
            user_data = await codeflixbots.col.find_one({"_id": user_id})
            if not user_data:
                return False
            
            # Check for premium in user data
            premium_data = user_data.get("premium", {})
            
            # Check if premium is active and not expired
            is_premium = premium_data.get("is_premium", False)
            expiry_date = premium_data.get("expiry_date")
            
            if is_premium and expiry_date:
                if isinstance(expiry_date, datetime):
                    return expiry_date > datetime.utcnow()
                else:
                    return True
            
            return is_premium
    except Exception as e:
        logger.error(f"Error checking premium status: {e}")
        return False

def check_verification(func):
    """Decorator to check if user is verified before allowing command usage"""
    @wraps(func)
    async def wrapper(client, message, *args, **kwargs):
        user_id = message.from_user.id
        
        try:
            # Check if user has premium - premium users bypass verification
            if await check_user_premium(user_id):
                logger.debug(f"User {user_id} has premium access, bypassing verification")
                return await func(client, message, *args, **kwargs)
        except Exception as e:
            logger.error(f"Error checking premium status in decorator: {e}")

        try:
            if not await is_user_verified(user_id):
            return await send_verification_message(client, message)
            return await func(client, message, *args, **kwargs)
                
        except Exception as e:
            logger.error(f"Error sending verification message: {e}")
            await message.reply_text(
                f"<b><i>! Eʀʀᴏʀ, Cᴏɴᴛᴀᴄᴛ ᴅᴇᴠᴇʟᴏᴘᴇʀ ᴛᴏ sᴏʟᴠᴇ ᴛʜᴇ ɪssᴜᴇs @seishiro_obito</i></b>\n"
                f"<blockquote expandable><b>Rᴇᴀsᴏɴ:</b> {str(e)}</blockquote>"
            )
            return 
            
    return wrapper

async def check_admin(filter, client, update):
    try:
        user_id = update.from_user.id
        return any([user_id == OWNER_ID, await codeflixbots.admin_exist(user_id)])
    except Exception as e:
        logger.error(f"Exception in check_admin: {e}")
        return False
            
admin = filters.create(check_admin)

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
@check_verification
@check_fsub
async def start(client, message: Message):
    logger.debug(f"/start command received from user {message.from_user.id}")
    user_id = message.from_user.id
    
    text = message.text
    
    # Check if there's a parameter after /start
    if len(text) > 7:
        try:
            param = text.split(" ", 1)[1]
            
            # Check if it's a verification callback
            if param.startswith("verify_"):
                token = param[7:]  # Remove "verify_" prefix
                await handle_verification_callback(client, message, token)
                return
        except Exception as e:
            logger.error(f"Error processing start parameter: {e}")
    
    # Normal start command - show welcome message
    await codeflixbots.add_user(client, message)
    await show_start_message(client, message)

async def show_start_message(client, message: Message):
    """Show the start message with buttons"""
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
            caption=Config.START_TXT.format(
                first=message.from_user.first_name,
                last=message.from_user.last_name,
                username=None if not message.from_user.username else '@' + message.from_user.username,
                mention=message.from_user.mention,
                id=message.from_user.id
            ),
            reply_markup=buttons
        )
    else:
        await message.reply_text(
            text=Config.START_TXT.format(
                first=message.from_user.first_name,
                last=message.from_user.last_name,
                username=None if not message.from_user.username else '@' + message.from_user.username,
                mention=message.from_user.mention,
                id=message.from_user.id
            ),
            reply_markup=buttons,
            disable_web_page_preview=True
        )

async def handle_verification_callback(client, message: Message, token: str):
    """Handle when user returns after completing verification through shortlink"""
    user_id = message.from_user.id
    current_time = datetime.utcnow()
    
    # Get verification settings to check if verification is enabled
    settings = await codeflixbots.get_verification_settings()
    verify_status_1 = settings.get("verify_status_1", False)
    verify_status_2 = settings.get("verify_status_2", False)
    verified_time_1 = settings.get("verified_time_1")
    verified_time_2 = settings.get("verified_time_2")
    
    # Check if verification is disabled - if so, just return
    if not verify_status_1 and not verify_status_2:
        await show_start_message(client, message)
        return 
    
    # Find the user who owns this token
    token_owner = await codeflixbots.col.find_one({"verification.pending_token": token})
    
    if not token_owner:
        await message.reply_text(
            "❌ Iɴᴠᴀʟɪᴅ ᴏʀ ᴇxᴘɪʀᴇᴅ ᴛᴏᴋᴇɴ!\n\n"
            "Pʟᴇᴀsᴇ ɢᴇɴᴇʀᴀᴛᴇ ᴀ ɴᴇᴡ ᴠᴇʀɪғɪᴄᴀᴛɪᴏɴ ʟɪɴᴋ ʙʏ ᴜsɪɴɢ /verify"
        )
        return
    
    token_user_id = token_owner.get("verification", {}).get("token_user_id")
    token_created_at = token_owner.get("verification", {}).get("token_created_at")
    
    # Check if token belongs to this user
    if token_user_id != user_id:
        await message.reply_text(
            "❌ Tʜɪs ɪs ɴᴏᴛ ʏᴏᴜʀ ᴠᴇʀɪғɪᴄᴀᴛɪᴏɴ ʟɪɴᴋ!\n\n"
            "Pʟᴇᴀsᴇ ɢᴇɴᴇʀᴀᴛᴇ ʏᴏᴜʀ ᴏᴡɴ ʟɪɴᴋ ᴜsɪɴɢ /verify"
        )
        return
    
    # Check if token has expired (24 hours)
    if token_created_at:
        time_diff = current_time - token_created_at
        if time_diff > timedelta(hours=24):
            await message.reply_text(
                "❌ Yᴏᴜʀ ᴠᴇʀɪғɪᴄᴀᴛɪᴏɴ ᴛᴏᴋᴇɴ ʜᴀs ᴇxᴘɪʀᴇᴅ!\n\n"
                "Pʟᴇᴀsᴇ ɢᴇɴᴇʀᴀᴛᴇ ᴀ ɴᴇᴡ ʟɪɴᴋ ᴜsɪɴɢ /verify"
            )
            # Clear expired token
            await codeflixbots.col.update_one(
                {"_id": user_id},
                {"$unset": {
                    "verification.pending_token": token,
                    "verification.token_created_at": current_time,
                    "verification.token_user_id": user_id
                }}
            )
            return
    
    # Check for bypass (verification completed too quickly - under 1 minute)
    if token_created_at:
        time_taken = current_time - token_created_at
        if time_taken < timedelta(minutes=1):
            await message.reply_text(
                f"⚠️ Bʏᴘᴀss Dᴇᴛᴇᴄᴛᴇᴅ!\n\n"
                f"• Yᴏᴜ ᴄᴏᴍᴘʟᴇᴛᴇᴅ ᴛʜᴇ ᴠᴇʀɪғɪᴄᴀᴛɪᴏɴ ᴛᴏᴏ ǫᴜɪᴄᴋʟʏ ({int(time_taken.total_seconds())} sᴇᴄᴏɴᴅs).\n\n"
                f"Pʟᴇᴀsᴇ ᴄᴏᴍᴘʟᴇᴛᴇ ᴛʜᴇ ᴠᴇʀɪғɪᴄᴀᴛɪᴏɴ ᴘʀᴏᴘᴇʀʟʏ.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("• Vᴇʀɪғʏ Aɢᴀɪɴ •", url=shortlink)
                ]])
            )
            # Clear the token so they have to verify again
            await codeflixbots.col.update_one(
                {"_id": user_id},
                {"$unset": {
                    "verification.pending_token": token,
                    "verification.token_created_at": current_time,
                    "verification.token_user_id": user_id
                }}
            )
            return
    
    # All checks passed - Update verification time (24 hour validity)
    await codeflixbots.col.update_one(
        {"_id": user_id},
        {"$set": {"verification.verified_time_1": current_time,
                  "verification.verified_time_2": current_time},
         "$unset": {
            "verification.pending_token": token,
            "verification.token_created_at": current_time,
            "verification.token_user_id": user_id
         }},
        upsert=True
    )
    
    # Calculate time taken for verification
    time_taken = current_time - token_created_at if token_created_at else timedelta(0)
    minutes_taken = int(time_taken.total_seconds() // 60)
    seconds_taken = int(time_taken.total_seconds() % 60)
    
    # Send success message
    await message.reply_text(
        f"✅ Vᴇʀɪғɪᴄᴀᴛɪᴏɴ Sᴜᴄᴄᴇssғᴜʟ!\n\n"
        f"›› ʏᴏᴜʀ ᴛᴏᴋᴇɴ ʜᴀs ʙᴇᴇɴ sᴜᴄᴄᴇssғᴜʟʟʏ ᴠᴇʀɪғɪᴇᴅ ᴀɴᴅ ɪs ᴠᴀʟɪᴅ ғᴏʀ 24ʜᴏᴜʀs ‼️\n\n"
        f"⏱️ Tɪᴍᴇ ᴛᴀᴋᴇɴ: {minutes_taken}m {seconds_taken}s",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("•Sᴇᴇ ᴘʟᴀɴs •", callback_data="seeplan")
        ]])
    )

async def send_verification_message(client, message: Message):
    """Generate and send verification shortlink to user"""
    user_id = message.from_user.id

    # Check if user has premium
    if await check_user_premium(user_id):
        await message.reply_text(
            "✨ <b>Yᴏᴜ ʜᴀᴠᴇ Pʀᴇᴍɪᴜᴍ Aᴄᴄᴇss!</b>\n\n"
            "Pʀᴇᴍɪᴜᴍ ᴜsᴇʀs ᴅᴏɴ'ᴛ ɴᴇᴇᴅ ᴛᴏ ᴠᴇʀɪғʏ.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("•Sᴇᴇ ᴘʟᴀɴs •", callback_data="seeplan")
            ]])
        )
        return

    # Get verification settings
    settings = await codeflixbots.get_verification_settings()
    verify_status_1 = settings.get("verify_status_1", False)
    verify_status_2 = settings.get("verify_status_2", False)
    verified_time_1 = settings.get("verified_time_1")
    verified_time_2 = settings.get("verified_time_2")
    
    # Get available shorteners
    available_shorteners = []
    if verify_status_1:
        available_shorteners.append(1)
    if verify_status_2:
        available_shorteners.append(2)
    
    if not available_shorteners:
        await show_start_message(client, message)
        return 
    
    # Randomly select a shortener from available ones
    selected_shortener = random.choice(available_shorteners)
    
    # Generate a random token for verification
    token = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
    
    # Store token with user_id and creation time (for expiry and ownership check)
    current_time = datetime.utcnow()
    await codeflixbots.col.update_one(
        {"_id": user_id},
        {"$set": {
            "verification.pending_token": token,
            "verification.token_created_at": current_time,
            "verification.token_user_id": user_id
        }},
        upsert=True
    )
    
    # This is the bot deep link that shortener will redirect to
    redirect_url = f"https://t.me/{Config.BOT_USERNAME}?start=verify_{token}"
    
    # Get shortlink from the shortener API
    shortlink = await get_shortlink(redirect_url, selected_shortener)
    
    if not shortlink:
        await message.reply_text(
            "Eʀʀᴏʀ ɢᴇɴᴇʀᴀᴛɪɴɢ sʜᴏʀᴛʟɪɴᴋ. Pʟᴇᴀsᴇ ᴛʀʏ ᴀɢᴀɪɴ ʟᴀᴛᴇʀ ᴏʀ ᴄᴏɴᴛᴀᴄᴛ @seishiro_obito."
        )
        return None
    
    # Send button with shortlink (e.g., https://lksfy.com/eARog)
    buttons = InlineKeyboardMarkup([[
        InlineKeyboardButton("• Vᴇʀɪғʏ •", url=shortlink)
    ]])
    
    await message.reply_text(
        f"ʜᴇʏ {message.from_user.mention},\n\n"
        "‼️ ʏᴏᴜ'ʀᴇ ɴᴏᴛ ᴠᴇʀɪғɪᴇᴅ ᴛᴏᴅᴀʏ ‼️\n\n"
        "⚠️ Yᴏᴜ ɴᴇᴇᴅ ᴛᴏ ᴠᴇʀɪғʏ ғɪʀsᴛ ᴛᴏ ɢᴇᴛ ᴛʜᴇ ᴀᴄᴄᴇss ᴏғ ʀᴇɴᴀᴍɪɴɢ ᴛʜᴇ ғɪʟᴇs\n\n"
        "Cʟɪᴄᴋ ᴛʜᴇ ʙᴜᴛᴛᴏɴ ʙᴇʟᴏᴡ ᴛᴏ ᴠᴇʀɪғʏ.\n\n"
        "⏰ <b>Vᴇʀɪғɪᴄᴀᴛɪᴏɴ ᴠᴀʟɪᴅ ғᴏʀ 24 ʜᴏᴜʀs</b>\n"
        "<b>Tᴏᴋᴇɴ ᴇxᴘɪʀᴇs ɪɴ 24 ʜᴏᴜʀs</b>",
        reply_markup=buttons
    )
    
    return shortlink

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
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("ᴠᴇʀɪꜰʏ 𝟷", callback_data="verify_1_cbb"), InlineKeyboardButton("ᴠᴇʀɪꜰʏ 𝟸", callback_data="verify_2_cbb")],
        [InlineKeyboardButton("ᴄᴏᴜɴᴛs", callback_data="verify_count")]
    ])
    await message.reply_text(
        "ʜᴇʀᴇ ʏᴏᴜ ᴄᴀɴ ᴍᴀɴᴀɢᴇ ʏᴏᴜʀ ᴠᴇʀɪꜰɪᴄᴀᴛɪᴏɴ ᴘʀᴏᴄᴇꜱꜱ:\n\n ➲ ʏᴏᴜ ᴄᴀɴ ᴅᴏ ᴛᴜʀɴ ᴏɴ/ᴏꜰꜰ ᴠᴇʀɪꜰɪᴄᴀᴛɪᴏɴ ᴘʀᴏᴄᴇꜱꜱ & Aʟsᴏ ʏᴏᴜ ᴄᴀɴ sᴇᴇ ᴄᴏᴜɴᴛs.",
        reply_markup=keyboard,
        disable_web_page_preview=True
    )

async def get_shortlink(link, shortener_num):
    """Generate a shortlink using the specified shortener (1 or 2)
    
    Args:
        link: The redirect URL (e.g., https://t.me/Bot?start=verify_token)
        shortener_num: Which shortener to use (1 or 2)
    
    Returns:
        Shortened URL (e.g., https://lksfy.com/eARog)
    """
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
    """Check if user is verified (either verified_time_1 or verified_time_2 is valid)"""
    try:
        user_data = await codeflixbots.col.find_one({"_id": user_id})
        if not user_data:
            return False
        
        verification_data = user_data.get("verification", {})
        verified_time_1 = verification_data.get("verified_time_1")
        verified_time_2 = verification_data.get("verified_time_2")
        
        current_time = datetime.utcnow()
        
        # Check if either verification is valid (within 24 hours)
        if verified_time_1:
            if isinstance(verified_time_1, datetime):
                if current_time < verified_time_1 + timedelta(hours=24):
                    return True
        
        if verified_time_2:
            if isinstance(verified_time_2, datetime):
                if current_time < verified_time_2 + timedelta(hours=24):
                    return True
        
        return False
    except Exception as e:
        logger.error(f"Error checking if user is verified: {e}")
        return False

@Client.on_message(filters.command("verify") & filters.private)
async def verify_command(client, message: Message):
    """Check verification status or initiate verification"""
    user_id = message.from_user.id
    
    try:
        # Check if user has premium
        if await check_user_premium(user_id):
            await message.reply_text(
                "✨ <b>Yᴏᴜ ʜᴀᴠᴇ Pʀᴇᴍɪᴜᴍ Aᴄᴄᴇss!</b>\n\n"
                "Pʀᴇᴍɪᴜᴍ ᴜsᴇʀs ᴅᴏɴ'ᴛ ɴᴇᴇᴅ ᴛᴏ ᴠᴇʀɪғʏ.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("•Sᴇᴇ ᴘʟᴀɴs •", callback_data="seeplan")
                ]])
            )
            return
    except Exception as e:
        logger.error(f"Error checking premium status in verify command: {e}")
        # Continue with verification check even if premium check fails

    try:
        # Check if user is already verified
        if await is_user_verified(user_id):
            try:
                user_data = await codeflixbots.col.find_one({"_id": user_id}) or {}
                verification_data = user_data.get("verification", {})
                
                # Get verification settings
                settings = await codeflixbots.get_verification_settings()
                verified_time_1 = verification_data.get("verified_time_1")
                verified_time_2 = verification_data.get("verified_time_2")
                
                current_time = datetime.utcnow()
                
                # Check if fully verified (shortener 1 within 24 hours)
                if verified_time_1:
                    try:
                        if isinstance(verified_time_1, datetime) and current_time < verified_time_1 + timedelta(hours=24):
                            time_left = timedelta(hours=24) - (current_time - verified_time_1)
                            hours_left = time_left.seconds // 3600
                            minutes_left = (time_left.seconds % 3600) // 60
                            
                            await message.reply_text(
                                f"✅ Yᴏᴜ ᴀʀᴇ ᴀʟʀᴇᴀᴅʏ ᴠᴇʀɪғɪᴇᴅ!\n\n"
                                f"⏰ Tɪᴍᴇ ʟᴇғᴛ: {hours_left}ʜ {minutes_left}ᴍ",
                                reply_markup=InlineKeyboardMarkup([[
                                    InlineKeyboardButton("•Sᴇᴇ ᴘʟᴀɴs •", callback_data="seeplan")
                                ]])
                            )
                            return
                    except Exception as e:
                        logger.error(f"Error checking verified_time_1: {e}")

                # Check if fully verified (shortener 2 within 24 hours)
                if verified_time_2:
                    try:
                        if isinstance(verified_time_2, datetime) and current_time < verified_time_2 + timedelta(hours=24):
                            time_left = timedelta(hours=24) - (current_time - verified_time_2)
                            hours_left = time_left.seconds // 3600
                            minutes_left = (time_left.seconds % 3600) // 60
                            
                            await message.reply_text(
                                f"✅ Yᴏᴜ ᴀʀᴇ ᴀʟʀᴇᴀᴅʏ ᴠᴇʀɪғɪᴇᴅ!\n\n"
                                f"⏰ Tɪᴍᴇ ʟᴇғᴛ: {hours_left}ʜ {minutes_left}ᴍ",
                                reply_markup=InlineKeyboardMarkup([[
                                    InlineKeyboardButton("•Sᴇᴇ ᴘʟᴀɴs •", callback_data="seeplan")
                                ]])
                            )
                            return
                    except Exception as e:
                        logger.error(f"Error checking verified_time_2: {e}")
                        
            except Exception as e:
                logger.error(f"Error checking verification status: {e}")
                # Continue to generate new verification link if there's an error
    
    except Exception as e:
        logger.error(f"Error in is_user_verified check: {e}")
    
    # User not verified - generate and send verification link
    try:
        await send_verification_message(client, message)
    except Exception as e:
        logger.error(f"Error sending verification message: {e}")
        await message.reply_text(
            f"<b><i>! Eʀʀᴏʀ, Cᴏɴᴛᴀᴄᴛ ᴅᴇᴠᴇʟᴏᴘᴇʀ ᴛᴏ sᴏʟᴠᴇ ᴛʜᴇ ɪssᴜᴇs @seishiro_obito</i></b>\n"
            f"<blockquote expandable><b>Rᴇᴀsᴏɴ:</b> {str(e)}</blockquote>"
        )
