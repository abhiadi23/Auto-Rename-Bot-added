 import random
import asyncio
import logging
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from pyrogram.enums import ChatAction, ChatMemberStatus
from pyrogram.errors import UserNotParticipant
from datetime import datetime, timedelta
from functools import wraps

from helper.database import codeflixbots
from config import Config

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

#=============================================================

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
        #=====================================================================================================
@Client.on_message(filters.command("cancel"))
async def cancel_handler(client, message):
    user_id = message.from_user.id
    
    # Check if the user has an active task
    if user_id in active_tasks:
        task = active_tasks.pop(user_id)
        
        # Cancel the task
        task.cancel()
        await message.reply_text("Pʀᴏᴄᴇss ᴄᴀɴᴄᴇʟʟᴇᴅ...!!")
    else:
        await message.reply_text("Nᴏ ᴀᴄᴛɪᴠᴇ ᴘʀᴏᴄᴇss ᴛᴏ ᴄᴀɴᴄᴇʟ...!!")
#======================================================================================

@Client.on_callback_query()
async def cb_handler(client, query: CallbackQuery):
    data = query.data
    user_id = query.from_user.id

    try:
        user = await codeflixbots.col.find_one({"_id": user_id})
        if user and user.get("ban_status", {}).get("is_banned", False):
            return await query.message.edit_text(
                "🚫 You are banned from using this bot.\n\nIf you think this is a mistake, contact the admin.",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("📩 Contact Admin", url=ADMIN_URL)]]
                )
            )

        if data == "home":
            await query.message.edit_text(
                text=Config.START_TXT.format(
                    first=query.from_user.first_name,
                    last=query.from_user.last_name or "",
                    username=f"@{query.from_user.username}" if query.from_user.username else "None",
                    mention=query.from_user.mention,
                    id=query.from_user.id
                ),
                disable_web_page_preview=True,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("• ᴍʏ ᴀʟʟ ᴄᴏᴍᴍᴀɴds •", callback_data='help')],
                    [InlineKeyboardButton('• ᴜᴘᴅᴀᴛᴇs', url='https://t.me/botskingdoms'), InlineKeyboardButton('sᴜᴘᴘᴏʀᴛ •', url='https://t.me/botskingdomsgroup')],
                    [InlineKeyboardButton('• ᴀʙᴏᴜᴛ', callback_data='about'), InlineKeyboardButton('Dᴇᴠᴇʟᴏᴘᴇʀ •', url='https://t.me/botskingdoms')]
                ])
            )
        elif data == "caption":
            await query.message.edit_text(
                text=Config.CAPTION_TXT,
                disable_web_page_preview=True,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("• sᴜᴘᴘᴏʀᴛ", url='https://t.me/botskingdomsgroup'), InlineKeyboardButton("ʙᴀᴄᴋ •", callback_data="help")]
                ])
            )
        elif data == "help":
            await query.message.edit_text(
                text=Config.HELP_TXT.format(query.from_user.mention),
                disable_web_page_preview=True,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("• ᴀᴜᴛᴏ ʀᴇɴᴀᴍᴇ ғᴏʀᴍᴀᴛ •", callback_data='file_names')],
                    [InlineKeyboardButton('• ᴛʜᴜᴍʙɴᴀɪʟ', callback_data='thumbnail'), InlineKeyboardButton('ᴄᴀᴘᴛɪᴏɴ •', callback_data='caption')],
                    [InlineKeyboardButton('• ᴍᴇᴛᴀᴅᴀᴛᴀ', callback_data='meta'), InlineKeyboardButton('ᴅᴏɴᴀᴛᴇ •', callback_data='donate')],
                    [InlineKeyboardButton("• Sᴇǫᴜᴇɴᴄᴇ" , callback_data='sequence')],
                    [InlineKeyboardButton('• ʜᴏᴍᴇ •', callback_data='home')]
                ])
            )
        elif data == "sequence":
            await query.message.edit_text(
                "<b>Sᴇɴᴅ ᴍᴇ ғɪʟᴇs ᴀɴᴅ I ᴡɪʟʟ ɢɪᴠᴇ ʏᴏᴜ ᴛʜᴀᴛ ғɪʟᴇs ɪɴ ᴀ ᴘᴇʀғᴇᴄᴛ sᴇǫᴜᴇɴᴄᴇ...!! \n\nʜᴇʀᴇ ɪꜱ ʜᴇʟᴘ ᴍᴇɴᴜ ғᴏʀ sᴇǫᴜᴇɴᴄᴇ ᴄᴏᴍᴍᴀɴᴅꜱ: \n\nᴀᴡᴇsᴏᴍᴇ Cᴏᴍᴍᴀɴds🫧 \n\n/start_sequence - Tᴏ sᴛᴀʀᴛ sᴇǫᴜᴇɴᴄᴇ. \n/end_sequence - Tᴏ ᴇɴᴅ sᴇǫᴜᴇɴᴄᴇ.</b>",
                disable_web_page_preview=True,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("ᴄʟᴏsᴇ", callback_data="close"),
                    InlineKeyboardButton("ʙᴀᴄᴋ", callback_data="help")
                ]])
            )
        elif data == "meta":
            await query.message.edit_text("<b>--Metadata Settings:--</b> \n\n➜ /metadata: Turn on or off metadata. \n\n<b><u>Description</u></b> <b><i>: Metadata will change MKV video files including all audio, streams, and subtitle titles.</i></b>",
                disable_web_page_preview=True,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("• ᴄʟᴏsᴇ", callback_data="close"), InlineKeyboardButton("ʙᴀᴄᴋ •", callback_data="help")]
                ])
            )
        elif data == "donate":
            await query.message.edit_text(
                text=Config.DONATE_TXT,
                disable_web_page_preview=True,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("• ʙᴀᴄᴋ", callback_data="help"), InlineKeyboardButton("ᴏᴡɴᴇʀ •", url='https://t.me/botskingdoms')]
                ])
            )
        elif data == "file_names":
            format_template = await codeflixbots.get_format_template(user_id)
            await query.message.edit_text(
                text=Config.FILE_NAME_TXT.format(format_template=format_template),
                disable_web_page_preview=True,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("• ᴄʟᴏsᴇ", callback_data="close"), InlineKeyboardButton("ʙᴀᴄᴋ •", callback_data="help")]
                ])
            )      
        elif data == "thumbnail":
            await query.message.edit_text(
                text=Config.THUMBNAIL_TXT,
                disable_web_page_preview=True,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("• ᴄʟᴏsᴇ", callback_data="close"), InlineKeyboardButton("ʙᴀᴄᴋ •", callback_data="help")]
                ])
            )      
        elif data == "about":
            await query.message.edit_text(
                text=Config.ABOUT_TXT,
                disable_web_page_preview=True,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("ᴄʟᴏsᴇ", callback_data="close"),
                    InlineKeyboardButton("ʙᴀᴄᴋ", callback_data="home")
                ]])
            )
        elif data == "close":
            try:
                await query.message.delete()
                if query.message.reply_to_message:
                    await query.message.reply_to_message.delete()
            except Exception:
                await query.message.delete()

        elif data.startswith("rfs_ch_"):
            cid = int(data.split("_")[2])
            try:
                chat = await client.get_chat(cid)
                mode = await codeflixbots.get_channel_mode(cid)
                status = "🟢 ᴏɴ" if mode == "on" else "🔴 ᴏғғ"
                new_mode = "off" if mode == "on" else "on"
                buttons = [
                    [InlineKeyboardButton(f"ʀᴇǫ ᴍᴏᴅᴇ {'OFF' if mode == 'on' else 'ON'}", callback_data=f"rfs_toggle_{cid}_{new_mode}")],
                    [InlineKeyboardButton("‹ ʙᴀᴄᴋ", callback_data="fsub_back")]
                ]
                await query.message.edit_text(
                    f"Channel: {chat.title}\nCurrent Force-Sub Mode: {status}",
                    reply_markup=InlineKeyboardMarkup(buttons)
                )
            except Exception:
                await query.answer("Failed to fetch channel info", show_alert=True)

        elif data.startswith("rfs_toggle_"):
            cid, action = data.split("_")[2:]
            cid = int(cid)
            mode = "on" if action == "on" else "off"

            await codeflixbots.set_channel_mode(cid, mode)
            await query.answer(f"Force-Sub set to {'ON' if mode == 'on' else 'OFF'}")

            chat = await client.get_chat(cid)
            status = "🟢 ON" if mode == "on" else "🔴 OFF"
            new_mode = "off" if mode == 'on' else "on"
            buttons = [
                [InlineKeyboardButton(f"ʀᴇǫ ᴍᴏᴅᴇ {'OFF' if mode == 'on' else 'ON'}", callback_data=f"rfs_toggle_{cid}_{new_mode}")],
                [InlineKeyboardButton("‹ ʙᴀᴄᴋ", callback_data="fsub_back")]
            ]
            await query.message.edit_text(
                f"Channel: {chat.title}\nCurrent Force-Sub Mode: {status}",
                reply_markup=InlineKeyboardMarkup(buttons)
            )

        elif data == "fsub_back":
            channels = await codeflixbots.show_channels()
            buttons = []
            for cid in channels:
                try:
                    chat = await client.get_chat(cid)
                    mode = await codeflixbots.get_channel_mode(cid)
                    status = "🟢" if mode == "on" else "🔴"
                    buttons.append([InlineKeyboardButton(f"{status} {chat.title}", callback_data=f"rfs_ch_{cid}")])
                except Exception:
                    continue
            if not buttons:
                buttons.append([InlineKeyboardButton("No Channels Found", callback_data="no_channels")])
            await query.message.edit_text(
                "sᴇʟᴇᴄᴛ ᴀ ᴄʜᴀɴɴᴇʟ ᴛᴏ ᴛᴏɢɢʟᴇ ɪᴛs ғᴏʀᴄᴇ-sᴜʙ ᴍᴏᴅᴇ:",
                reply_markup=InlineKeyboardMarkup(buttons)
            )
        elif data == "verify_settings":
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("ᴠᴇʀɪꜰʏ 𝟷", callback_data="verify_1_cbb"), InlineKeyboardButton("ᴠᴇʀɪꜰʏ 𝟸", callback_data="verify_2_cbb")],
                [InlineKeyboardButton("ᴄᴏᴜɴᴛs", callback_data="verify_count")]
            ])
            await query.message.edit_text("ʜᴇʀᴇ ʏᴏᴜ ᴄᴀɴ ᴍᴀɴᴀɢᴇ ʏᴏᴜʀ ᴠᴇʀɪꜰɪᴄᴀᴛɪᴏɴ ᴘʀᴏᴄᴇꜱꜱ:\n\n ➲ ʏᴏᴜ ᴄᴀɴ ᴅᴏ ᴛᴜʀɴ ᴏɴ/ᴏꜰꜰ ᴠᴇʀɪꜰɪᴄᴀᴛɪᴏɴ ᴘʀᴏᴄᴇꜱꜱ & Aʟsᴏ ʏᴏᴜ ᴄᴀɴ sᴇᴇ ᴄᴏᴜɴᴛs.", reply_markup=keyboard)

        elif data == "verify_1_cbb":
            settings = await codeflixbots.get_verification_settings()
            verify_status_1 = settings.get("verify_status_1", False)
            verify_token_1 = settings.get("verify_token_1", "Not set")
            api_link_1 = settings.get("api_link_1", "Not set")
            current_status = "On" if verify_status_1 else "Off"
            
            buttons = [
                [
                    InlineKeyboardButton(f"Oɴ{' ✅' if current_status == 'On' else ''}", callback_data='on_vrfy_1'),
                    InlineKeyboardButton(f"Oғғ{' ✅' if current_status == 'Off' else ''}", callback_data='off_vrfy_1')
                ],
                [
                    InlineKeyboardButton("Sᴇᴛ ᴠᴇʀɪғɪᴄᴀᴛɪᴏɴ", callback_data="vrfy_set_1")
                ]
            ]
            keyboard = InlineKeyboardMarkup(buttons)
            await query.message.edit_text(f"<b>ᴠᴇʀɪꜰʏ 𝟷 ꜱᴇᴛᴛɪɴɢꜱ:\n\nꜱʜᴏʀᴛɴᴇʀ: {api_link_1}\nAPI: {verify_token_1}\n\nꜱᴛᴀᴛᴜꜱ:</b> {current_status}", reply_markup=keyboard)

        elif data == "verify_2_cbb":
            settings = await codeflixbots.get_verification_settings()
            verify_status_2 = settings.get("verify_status_2", False)
            verify_token_2 = settings.get("verify_token_2", "Not set")
            api_link_2 = settings.get("api_link_2", "Not set")
            current_status = "On" if verify_status_2 else "Off"

            buttons = [
                [
                    InlineKeyboardButton(f"Oɴ{' ✅' if current_status == 'On' else ''}", callback_data='on_vrfy_2'),
                    InlineKeyboardButton(f"Oғғ{' ✅' if current_status == 'Off' else ''}", callback_data='off_vrfy_2')
                ],
                [
                    InlineKeyboardButton("Sᴇᴛ ᴠᴇʀɪғɪᴄᴀᴛɪᴏɴ", callback_data="vrfy_set_2")
                ]
            ]
            keyboard = InlineKeyboardMarkup(buttons)
            await query.message.edit_text(f"<b>ᴠᴇʀɪꜰʏ 𝟸 ꜱᴇᴛᴛɪɴɢꜱ:\n\nꜱʜᴏʀᴛɴᴇʀ: {api_link_2}\nAPI: {verify_token_2}\n\nꜱᴛᴀᴛᴜꜱ:</b> {current_status}", reply_markup=keyboard)

    except Exception as e:
        logger.error(f"Error handling callback query: {e}")
        await query.answer(f"An unexpected error occurred: {e}", show_alert=True)

@Client.on_callback_query(filters.regex(r"on_vrfy_2|off_vrfy_2|vrfy_set_2"))
async def vrfy_2_callback(client, query: CallbackQuery):
    user_id = query.from_user.id
    data = query.data

    if data == "on_vrfy_2":
        await codeflixbots.set_verification_mode_2(True)
        await query.answer("Verification 2 turned ON")
    elif data == "off_vrfy_2":
        await codeflixbots.set_verification_mode_2(False)
        await query.answer("Verification 2 turned OFF")
    elif data == "vrfy_set_2":
        msg = await query.message.edit_text("<b>ꜱᴇɴᴅ ᴠᴇʀɪꜰʏ 𝟸 ꜱʜᴏʀᴛɴᴇʀ ᴜʀʟ:\n\nʟɪᴋᴇ - `gplinks.com`\n\n/cancel ᴛᴏ ᴄᴀɴᴄᴇʟ</b>")
        try:
            api_data_2 = await client.listen(chat_id=query.message.chat.id, filters=filters.text, timeout=300)
            await msg.delete()
            api_link_2_s = api_data_2.text.strip()
            
            msg = await api_data_2.reply("<b>ꜱᴇɴᴅ ᴠᴇʀɪꜰʏ 𝟸 ꜱʜᴏʀᴛɴᴇʀ ᴀᴘɪ ᴋᴇʏ:\n\nʟɪᴋᴇ - 064438447747gdg4\n\n/cancel ᴛᴏ ᴄᴀɴᴄᴇʟ</b>")
            verify_data_2 = await client.listen(chat_id=query.message.chat.id, filters=filters.text, timeout=300)
            await msg.delete()
            verify_token_2_s = verify_data_2.text.strip()
            
            await codeflixbots.set_verify_2(api_link_2_s, verify_token_2_s)
            await query.message.reply_text(
                "<b>ᴠᴇʀɪꜰɪᴄᴀᴛɪᴏɴ 2 ꜱᴇᴛᴛɪɴɢꜱ ᴜᴘᴅᴀᴛᴇᴅ!</b>",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("Hᴏᴍᴇ", callback_data="home"), InlineKeyboardButton("Bᴀᴄᴋ", callback_data="verify_settings")]
                ])
            )
        except asyncio.TimeoutError:
            await query.message.reply_text("Tɪᴍᴇᴏᴜᴛ. Pʟᴇᴀsᴇ ᴛʀʏ ᴀɢᴀɪɴ.")
        except Exception as e:
            logger.error(f"Error setting verification 1: {e}")
            await query.message.reply_text(f"An error occurred: {e}")

except Exception as e:
        logger.error(f"Error handling callback query: {e}")
        await query.answer(f"An unexpected error occurred: {e}", show_alert=True)        
            
@Client.on_callback_query(filters.regex(r"on_vrfy_1|off_vrfy_1|vrfy_set_1"))
async def vrfy_1_callback(client, query: CallbackQuery):
    user_id = query.from_user.id
    data = query.data

    if data == "on_vrfy_1":
        await codeflixbots.set_verification_mode_1(True)
        await query.answer("Verification 1 turned ON")
    elif data == "off_vrfy_1":
        await codeflixbots.set_verification_mode_1(False)
        await query.answer("Verification 1 turned OFF")
    elif data == "vrfy_set_1":
        msg = await query.message.edit_text("<b>ꜱᴇɴᴅ ᴠᴇʀɪꜰʏ 𝟷 ꜱʜᴏʀᴛɴᴇʀ ᴜʀʟ:\n\nʟɪᴋᴇ - `gplinks.com`\n\n/cancel ᴛᴏ ᴄᴀɴᴄᴇʟ</b>")
        try:
            api_data_1 = await client.listen(chat_id=query.message.chat.id, filters=filters.text, timeout=300)
            await msg.delete()
            api_link_1_s = api_data_1.text.strip()

            msg = await api_data_1.reply("<b>ꜱᴇɴᴅ ᴠᴇʀɪꜰʏ 𝟷 ꜱʜᴏʀᴛɴᴇʀ ᴀᴘɪ ᴋᴇʏ:\n\nʟɪᴋᴇ - 064438447747gdg4\n\n/cancel ᴛᴏ ᴄᴀɴᴄᴇʟ</b>")
            verify_data_1 = await client.listen(chat_id=query.message.chat.id, filters=filters.text, timeout=300)
            await msg.delete()
            verify_token_1_s = verify_data_1.text.strip()

            await codeflixbots.set_verify_1(api_link_1_s, verify_token_1_s)
            await query.message.reply_text(
                "<b>ᴠᴇʀɪꜰɪᴄᴀᴛɪᴏɴ 1 ꜱᴇᴛᴛɪɴɢꜱ ᴜᴘᴅᴀᴛᴇᴅ!</b>",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("Hᴏᴍᴇ", callback_data="home"), InlineKeyboardButton("Bᴀᴄᴋ", callback_data="verify_settings")]
                ])
            )
        except asyncio.TimeoutError:
            await query.message.reply_text("Tɪᴍᴇᴏᴜᴛ. Pʟᴇᴀsᴇ ᴛʀʏ ᴀɢᴀɪɴ.")
        except Exception as e:
            logger.error(f"Error setting verification 1: {e}")
            await query.message.reply_text(f"An error occurred: {e}")

except Exception as e:
        logger.error(f"Error handling callback query: {e}")
        await query.answer(f"An unexpected error occurred: {e}", show_alert=True)

#============================================================================================================================================
@Client.on_message(filters.command("verify_settings"))
async def verify_settings(client, message):
    user_id = message.from_user.id
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("ᴠᴇʀɪꜰʏ 𝟷", callback_data="verify_1_cbb"), InlineKeyboardButton("ᴠᴇʀɪꜰʏ 𝟸", callback_data="verify_2_cbb")],
        [InlineKeyboardButton("ᴄᴏᴜɴᴛs", callback_data="verify_count")]
    ])
    await message.reply_text(
        "ʜᴇʀᴇ ʏᴏᴜ ᴄᴀɴ ᴍᴀɴᴀɢᴇ ʏᴏᴜʀ ᴠᴇʀɪꜰɪᴄᴀᴛɪᴏɴ ᴘʀᴏᴄᴇꜱꜱ:\n\n ➲ ʏᴏᴜ ᴄᴀɴ ᴅᴏ ᴛᴜʀɴ ᴏɴ/ᴏꜰꜰ ᴠᴇʀɪꜰɪᴄᴀᴛɪᴏɴ ᴘʀᴏᴄᴇꜱꜱ & Aʟsᴏ ʏᴏᴜ ᴄᴀɴ sᴇᴇ ᴄᴏᴜɴᴛs.",
        reply_markup=keyboard,
        disable_web_page_preview=True
    )
