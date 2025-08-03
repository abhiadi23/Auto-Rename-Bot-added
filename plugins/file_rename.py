import os
import re
import time
import shutil
import asyncio
import logging
import uuid
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from PIL import Image
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from plugins.antinsfw import check_anti_nsfw
from helper.utils import progress_for_pyrogram, humanbytes, convert
from helper.database import codeflixbots
from config import Config
from functools import wraps
from os import makedirs

ADMIN_URL = Config.ADMIN_URL


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

active_sequences = {}
message_ids = {}
renaming_operations = {}

# --- Enhanced Semaphores for better concurrency ---

# Thread pool for CPU-intensive operations
thread_pool = ThreadPoolExecutor(max_workers=4)

# ========== Decorators ==========

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


def detect_quality(file_name):
    quality_order = {"360p": 0, "480p": 1, "720p": 2, "1080p": 3, "1440p": 4, "2160p": 5, "4k": 6}
    match = re.search(r"(360p|480p|720p|1080p|1440p|2160p|4k)\b", file_name, re.IGNORECASE)
    return quality_order.get(match.group(1).lower(), 7) if match else 7

# --- REVISED extract_episode_number ---
def extract_episode_number(filename):
    if not filename:
        return None

    print(f"DEBUG: Extracting episode from: '{filename}')")

    quality_and_year_indicators = [
        r'\d{2,4}[pP]',
        r'\dK',
        r'HD(?:RIP)?',
        r'WEB(?:-)?DL',
        r'BLURAY',
        r'X264',
        r'X265',
        r'HEVC',
        r'FHD',
        r'UHD',
        r'HDR',
        r'H\.264', r'H\.265',
        r'(?:19|20)\d{2}',
        r'Multi(?:audio)?',
        r'Dual(?:audio)?',
    ]
    quality_pattern_for_exclusion = r'(?:' + '|'.join([f'(?:[\s._-]*{ind})' for ind in quality_and_year_indicators]) + r')'

    patterns = [
        re.compile(r'S\d+[.-_]?E(\d+)', re.IGNORECASE),
        re.compile(r'(?:Episode|EP)[\s._-]*(\d+)', re.IGNORECASE),
        re.compile(r'\bE(\d+)\b', re.IGNORECASE),
        re.compile(r'[\[\(]E(\d+)[\]\)]', re.IGNORECASE),
        re.compile(r'\b(\d+)\s*of\s*\d+\b', re.IGNORECASE),

        re.compile(
            r'(?:^|[^0-9A-Z])'
            r'(\d{1,4})'
            r'(?:[^0-9A-Z]|$)'
            r'(?!' + quality_pattern_for_exclusion + r')'
            , re.IGNORECASE
        ),
    ]

    for i, pattern in enumerate(patterns):
        matches = pattern.findall(filename)
        if matches:
            for match in matches:
                try:
                    if isinstance(match, tuple):
                        episode_str = match[0]
                    else:
                        episode_str = match

                    episode_num = int(episode_str)

                    if 1 <= episode_num <= 9999:
                        if episode_num in [360, 480, 720, 1080, 1440, 2160, 2020, 2021, 2022, 2023, 2024, 2025]:
                            if re.search(r'\b' + str(episode_num) + r'(?:p|K|HD|WEB|BLURAY|X264|X265|HEVC|Multi|Dual)\b', filename, re.IGNORECASE) or \
                               re.search(r'\b(?:19|20)\d{2}\b', filename, re.IGNORECASE) and len(str(episode_num)) == 4:
                                print(f"DEBUG: Skipping {episode_num} as it is a common quality/year number.")
                                continue

                        print(f"DEBUG: Episode Pattern {i+1} found episode: {episode_num}")
                        return episode_num
                except ValueError:
                    continue

    print(f"DEBUG: No episode number found in: '{filename}'")
    return None

# --- MODIFIED: extract_season_number (added negative lookahead) ---
def extract_season_number(filename):
    if not filename:
        return None

    print(f"DEBUG: Extracting season from: '{filename}')")

    quality_and_year_indicators = [
        r'\d{2,4}[pP]',
        r'\dK',
        r'HD(?:RIP)?',
        r'WEB(?:-)?DL',
        r'BLURAY',
        r'X264',
        r'X265',
        r'HEVC',
        r'FHD',
        r'UHD',
        r'HDR',
        r'H\.264', r'H\.265',
        r'(?:19|20)\d{2}',
        r'Multi(?:audio)?',
        r'Dual(?:audio)?',
    ]
    quality_pattern_for_exclusion = r'(?:' + '|'.join([f'(?:[\s._-]*{ind})' for ind in quality_and_year_indicators]) + r')'


    patterns = [
        re.compile(r'S(\d+)[._-]?E\d+', re.IGNORECASE),

        re.compile(r'(?:Season|SEASON|season)[\s._-]*(\d+)', re.IGNORECASE),

        re.compile(r'\bS(\d+)\b(?!E\d|' + quality_pattern_for_exclusion + r')', re.IGNORECASE),

        re.compile(r'[\[\(]S(\d+)[\]\)]', re.IGNORECASE),

        re.compile(r'[._-]S(\d+)(?:[._-]|$)', re.IGNORECASE),

        re.compile(r'(?:season|SEASON|Season)[\s._-]*(\d+)', re.IGNORECASE),

        re.compile(r'(?:^|[\s._-])(?:season|SEASON|Season)[\s._-]*(\d+)(?:[\s._-]|$)', re.IGNORECASE),

        re.compile(r'[\[\(](?:season|SEASON|Season)[\s._-]*(\d+)[\]\)]', re.IGNORECASE),

        re.compile(r'(?:season|SEASON|Season)[._\s-]+(\d+)', re.IGNORECASE),

        re.compile(r'(?:^season|season$)[\s._-]*(\d+)', re.IGNORECASE),
    ]

    for i, pattern in enumerate(patterns):
        match = pattern.search(filename)
        if match:
            try:
                season_num = int(match.group(1))
                if 1 <= season_num <= 99:
                    print(f"DEBUG: Season Pattern {i+1} found season: {season_num}")
                    return season_num
            except ValueError:
                continue

    print(f"DEBUG: No season number found in: '{filename}'")
    return None

def extract_audio_info(filename):
    """Extract audio information from filename, including languages and 'dual'/'multi'."""
    audio_keywords = {
        'Hindi': re.compile(r'Hindi', re.IGNORECASE),
        'English': re.compile(r'English', re.IGNORECASE),
        'Multi': re.compile(r'Multi(?:audio)?', re.IGNORECASE),
        'Telugu': re.compile(r'Telugu', re.IGNORECASE),
        'Tamil': re.compile(r'Tamil', re.IGNORECASE),
        'Dual': re.compile(r'Dual(?:audio)?', re.IGNORECASE),
        'Dual_Enhanced': re.compile(r'(?:DUAL(?:[\s._-]?AUDIO)?|\[DUAL\])', re.IGNORECASE),
        'AAC': re.compile(r'AAC', re.IGNORECASE),
        'AC3': re.compile(r'AC3', re.IGNORECASE),
        'DTS': re.compile(r'DTS', re.IGNORECASE),
        'MP3': re.compile(r'MP3', re.IGNORECASE),
        '5.1': re.compile(r'5\.1', re.IGNORECASE),
        '2.0': re.compile(r'2\.0', re.IGNORECASE),
    }

    detected_audio = []

    if re.search(r'\bMulti(?:audio)?\b', filename, re.IGNORECASE):
        detected_audio.append("Multi")
    if re.search(r'\bDual(?:audio)?\b', filename, re.IGNORECASE):
        detected_audio.append("Dual")


    priority_keywords = ['Hindi', 'English', 'Telugu', 'Tamil']
    for keyword in priority_keywords:
        if audio_keywords[keyword].search(filename):
            if keyword not in detected_audio:
                detected_audio.append(keyword)

    for keyword in ['AAC', 'AC3', 'DTS', 'MP3', '5.1', '2.0']:
        if audio_keywords[keyword].search(filename):
            if keyword not in detected_audio:
                detected_audio.append(keyword)

    detected_audio = list(dict.fromkeys(detected_audio))

    if detected_audio:
        return ' '.join(detected_audio)

    return None

def extract_quality(filename):
    """Extract video quality from filename."""
    patterns = [
        re.compile(r'\b(4K|2K|2160p|1440p|1080p|720p|480p|360p)\b', re.IGNORECASE),
        re.compile(r'\b(HD(?:RIP)?|WEB(?:-)?DL|BLURAY)\b', re.IGNORECASE),
        re.compile(r'\b(X264|X265|HEVC)\b', re.IGNORECASE),
    ]

    for pattern in patterns:
        match = re.search(pattern, filename)
        if match:
            found_quality = match.group(1)
            if found_quality.lower() in ["4k", "2k", "hdrip", "web-dl", "bluray"]:
                return found_quality.upper() if found_quality.upper() in ["4K", "2K"] else found_quality.capitalize()
            return found_quality

    return None

@Client.on_message(filters.command("start_sequence") & filters.private)
@check_ban
async def start_sequence(client, message: Message):
    user_id = message.from_user.id
    if user_id in active_sequences:
        await message.reply_text("Hᴇʏ ᴅᴜᴅᴇ...!! A sᴇǫᴜᴇɴᴄᴇ ɪs ᴀʟʀᴇᴀᴅʏ ᴀᴄᴛɪᴠᴇ! Usᴇ /end_sequence ᴛᴏ ᴇɴᴅ ɪᴛ.")
    else:
        active_sequences[user_id] = []
        message_ids[user_id] = []
        msg = await message.reply_text("Sᴇǫᴜᴇɴᴄᴇ sᴛᴀʀᴛᴇᴅ! Sᴇɴᴅ ʏᴏᴜʀ ғɪʟᴇs ɴᴏᴡ ʙʀᴏ....Fᴀsᴛ")
        message_ids[user_id].append(msg.id)

@Client.on_message(filters.private & (filters.document | filters.video | filters.audio))
@check_ban
async def auto_rename_files(client, message):
    """Main handler for auto-renaming files"""
    user_id = message.from_user.id
    format_template = await codeflixbots.get_format_template(user_id)
    media_preference = await codeflixbots.get_media_preference(user_id)

    if not format_template:
        await message.reply_text("Pʟᴇᴀsᴇ Sᴇᴛ Aɴ Aᴜᴛᴏ Rᴇɴᴀᴍᴇ Fᴏʀᴍᴀᴛ Fɪʀsᴛ Usɪɴɢ /autorename")
        return
    

    # Correctly identify file properties and initial media type
    if message.document:
        file_id = message.document.file_id
        file_name = message.document.file_name
        file_size = message.document.file_size
        media_type = "document"
    elif message.video:
        file_id = message.video.file_id
        file_name = message.video.file_name or "video"
        file_size = message.video.file_size
        duration = message.video.duration
        media_type = "video"
    elif message.audio:
        file_id = message.audio.file_id
        file_name = message.audio.file_name or "audio"
        file_size = message.audio.file_size
        duration = message.audio.duration
        media_type = "audio"
    else:
        return await message.reply_text("Unsupported file type")

    # The block of code below was incorrectly indented.
    # It should be part of the main function body, not nested in a way that creates a syntax error.
    # The variables like file_name and media_type were not yet defined when this block was entered.
    
    # Corrected placement and logic
    if not file_name:
        await message.reply_text("Could not determine file name.")
        return

    # This part was also indented incorrectly. Correctly placing it after file info is gathered.
    if media_preference:
        media_type = media_preference
    else:
        # Fallback to intelligent guessing if no preference is set
        if file_name.endswith((".mp4", ".mkv", ".avi", ".webm")):
            media_type = "document"
        elif file_name.endswith((".mp3", ".flac", ".wav", ".ogg")):
            media_type = "audio"
        else:
            media_type = "video"

    if await check_anti_nsfw(file_name, message):
        await message.reply_text("NSFW ᴄᴏɴᴛᴇɴᴛ ᴅᴇᴛᴇᴄᴛᴇᴅ. Fɪʟe ᴜᴘʟᴏᴀᴅ ʀᴇᴊᴇᴄᴛᴇᴅ.")
        return

    if file_id in renaming_operations:
        if (datetime.now() - renaming_operations[file_id]).seconds < 10:
            return
    renaming_operations[file_id] = datetime.now()
            
    file_info = {
        "file_id": file_id,
        "file_name": file_name,
        "message": message,
        "episode_num": extract_episode_number(file_name)
    }

    if user_id in active_sequences:
        active_sequences[user_id].append(file_info)
        reply_msg = await message.reply_text("Wᴇᴡ...ғɪʟᴇs ʀᴇᴄᴇɪᴠᴇᴅ ɴᴏᴡ ᴜsᴇ /end_sequence ᴛᴏ ɢᴇᴛ ʏᴏᴜʀ ғɪʟᴇs...!!")
        message_ids[user_id].append(reply_msg.id)
        return

    episode_number = extract_episode_number(file_name)
    season_number = extract_season_number(file_name)
    audio_info_extracted = extract_audio_info(file_name)
    quality_extracted = extract_quality(file_name)

    print(f"DEBUG: Final extracted values - Season: {season_number}, Episode: {episode_number}, Quality: {quality_extracted}, Audio: {audio_info_extracted}")

    season_value_formatted = str(season_number).zfill(2) if season_number is not None else "01"
    episode_value_formatted = str(episode_number).zfill(2) if episode_number is not None else "01"

    template = re.sub(r'S(?:Season|season|SEASON)(\d+)', f'S{season_value_formatted}', format_template, flags=re.IGNORECASE)

    season_replacements = [
        (re.compile(r'\{season\}', re.IGNORECASE), season_value_formatted),
        (re.compile(r'\{Season\}', re.IGNORECASE), season_value_formatted),
        (re.compile(r'\{SEASON\}', re.IGNORECASE), season_value_formatted),

        (re.compile(r'\bseason\b', re.IGNORECASE), season_value_formatted),
        (re.compile(r'\bSeason\b', re.IGNORECASE), season_value_formatted),
        (re.compile(r'\bSEASON\b', re.IGNORECASE), season_value_formatted),

        (re.compile(r'Season[\s._-]*\d*', re.IGNORECASE), season_value_formatted),
        (re.compile(r'season[\s._-]*\d*', re.IGNORECASE), season_value_formatted),
        (re.compile(r'SEASON[\s._-]*\d*', re.IGNORECASE), season_value_formatted),
    ]

    for pattern, replacement in season_replacements:
        template = pattern.sub(replacement, template)
            
    template = re.sub(r'EP(?:Episode|episode|EPISODE)', f'EP{episode_value_formatted}', template, flags=re.IGNORECASE)

    episode_patterns = [
        re.compile(r'\{episode\}', re.IGNORECASE),
        re.compile(r'\bEpisode\b', re.IGNORECASE),
        re.compile(r'\bEP\b', re.IGNORECASE)
    ]

    for pattern in episode_patterns:
        template = pattern.sub(episode_value_formatted, template)

    audio_replacement = audio_info_extracted if audio_info_extracted else ""
    audio_patterns = [
        re.compile(r'\{audio\}', re.IGNORECASE),
        re.compile(r'\bAudio\b', re.IGNORECASE),
    ]

    for pattern in audio_patterns:
        template = pattern.sub(audio_replacement, template)

    quality_replacement = quality_extracted if quality_extracted else ""
    quality_patterns = [
        re.compile(r'\{quality\}', re.IGNORECASE),
        re.compile(r'\bQuality\b', re.IGNORECASE),
    ]

    for pattern in quality_patterns:
        template = pattern.sub(quality_replacement, template)

    template = re.sub(r'\[\s*\]', '', template)
    template = re.sub(r'\(\s*\)', '', template)
    template = re.sub(r'\{\s*\}', '', template)

    _, file_extension = os.path.splitext(file_name)

    print(f"Cleaned template: '{template}'")
    print(f"File extension: '{file_extension}'")

    if not file_extension.startswith('.'):
        file_extension = '.' + file_extension if file_extension else ''

    new_file_name = f"{template}{file_extension}"
    download_path = f"downloads/{new_file_name}"
    metadata_path = f"metadata/{new_file_name}"
    output_path = f"processed/{os.path.splitext(new_file_name)[0]}{os.path.splitext(new_file_name)[1]}"

    makedirs(os.path.dirname(download_path), exist_ok=True)
    makedirs(os.path.dirname(metadata_path), exist_ok=True)
    makedirs(os.path.dirname(output_path), exist_ok=True)


    msg = await message.reply_text("Wᴇᴡ... Iᴀm ᴅᴏᴡɴʟᴏᴀᴅɪɴɢ ʏᴏᴜʀ ғɪʟᴇ...!!")
    try:
        file_path = await client.download_media(
            message,
            file_name=download_path,
            progress=progress_for_pyrogram,
            progress_args=("Dᴏᴡɴʟᴏᴀᴅ sᴛᴀʀᴛᴇᴅ ᴅᴜᴅᴇ...!!", msg, time.time())
        )
    except Exception as e:
        await msg.edit(f"Download failed: {e}")
        raise

    try:
        await msg.edit("Nᴏᴡ ᴀᴅᴅɪɴɢ ᴍᴇᴛᴀᴅᴀᴛᴀ ᴅᴜᴅᴇ...!!")
        await add_metadata(file_path, metadata_path, user_id)
        file_path = metadata_path

        await msg.edit("Wᴇᴡ... Iᴀm Uᴘʟᴏᴀᴅɪɴɢ ʏᴏᴜʀ ғɪʟᴇ...!!")
        await codeflixbots.col.update_one(
            {"_id": user_id},
            {
                "$inc": {"rename_count": 1},
                "$set": {
                    "first_name": message.from_user.first_name,
                    "username": message.from_user.username,
                    "last_activity_timestamp": datetime.now()
                }
            }
        )

        c_caption = await codeflixbots.get_caption(message.chat.id) or f"**{new_file_name}**"
        c_thumb = await codeflixbots.get_thumbnail(message.chat.id)

        ph_path = None
        if c_thumb:
            ph_path = await client.download_media(c_thumb)
        elif media_type == "video" and getattr(message.video, "thumbs", None):
            if message.video.thumbs:
                ph_path = await client.download_media(message.video.thumbs[0].file_id)

        upload_params = {
            'chat_id': message.chat.id,
            'caption': caption,
            'thumb': ph_path,
            'progress': progress_for_pyrogram,
            'progress_args': ("Uᴘʟᴏᴀᴅ sᴛᴀʀᴛᴇᴅ ᴅᴜᴅᴇ...!!", msg, time.time())
        }

        if media_type == "document":
            await client.send_document(document=file_path, **upload_params)
        elif media_type == "video":
            await client.send_video(video=file_path, **upload_params)
        elif media_type == "audio":
            await client.send_audio(audio=file_path, **upload_params)

        await msg.delete()

    except Exception as e:
        await msg.edit(f"Metadata or upload failed: {e}")
        raise
        try:
        pass
    except Exception as e:
        await message.reply_text(f"❌ Eʀʀᴏʀ ᴅᴜʀɪɴɢ ʀᴇɴᴀᴍɪɴɢ: {str(e)}")
        raise
    finally:
        if file_id in renaming_operations:
            del renaming_operations[file_id]

        cleanup_files = [download_path, metadata_path, output_path]
        if ph_path:
            cleanup_files.append(ph_path)

        for file_path in cleanup_files:
            if file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except Exception as cleanup_e:
                    print(f"Error during file cleanup for {file_path}: {cleanup_e}")
                    pass

@Client.on_message(filters.command("end_sequence") & filters.private)
@check_ban
async def end_sequence(client, message: Message):
    user_id = message.from_user.id
    if user_id not in active_sequences:
        await message.reply_text("Wʜᴀᴛ ᴀʀᴇ ʏᴏᴜ ᴅᴏɪɴɢ ɴᴏ ᴀᴄᴛɪᴠᴇ sᴇǫᴜᴇɴᴄᴇ ғᴏᴜɴᴅ...!!")
    else:
        file_list = active_sequences.pop(user_id, [])
        delete_messages = message_ids.pop(user_id, [])
        count = len(file_list)

        if not file_list:
            await message.reply_text("Nᴏ ғɪʟᴇs ᴡᴇʀᴇ sᴇɴᴛ ɪɴ ᴛʜɪs sᴇǫᴜᴇɴᴄᴇ....ʙʀᴏ...!!")
        else:
            file_list.sort(key=lambda x: x["episode_num"] if x["episode_num"] is not None else float('inf'))
            await message.reply_text(f"Sᴇǫᴜᴇɴᴄᴇ ᴇɴᴅᴇᴅ. Nᴏᴡ sᴇɴᴅɪɴɢ ʏᴏᴜʀ {count} ғɪʟe(s) ʙᴀᴄᴋ ɪɴ sᴇǫᴜᴇɴᴄᴇ...!!")

            for index, file_info in enumerate(file_list, 1):
                try:
                    await asyncio.sleep(0.5)

                    original_message = file_info["message"]

                    if original_message.document:
                        await client.send_document(
                            message.chat.id,
                            original_message.document.file_id,
                            caption=f"{file_info['file_name']}"
                        )
                    elif original_message.video:
                        await client.send_video(
                            message.chat.id,
                            original_message.video.file_id,
                            caption=f"{file_info['file_name']}"
                        )
                    elif original_message.audio:
                        await client.send_audio(
                            message.chat.id,
                            original_message.audio.file_id,
                            caption=f"{file_info['file_name']}"
                        )
                except Exception as e:
                    await message.reply_text(f"Fᴀɪʟᴇᴅ ᴛᴏ sᴇɴᴅ ғɪʟᴇ: {file_info.get('file_name', '')}\n{e}")

            await message.reply_text(f"✅ Aʟʟ {count} ғɪʟes sᴇɴᴛ sᴜᴄᴄᴇssғᴜʟʟʏ ɪɴ sᴇǫᴜᴇɴᴄᴇ!")

        try:
            await client.delete_messages(chat_id=message.chat.id, message_ids=delete_messages)
        except Exception as e:
            print(f"Error deleting messages: {e}")

async def process_thumb_async(ph_path):
    def _resize_thumb(path):
        img = Image.open(path).convert("RGB")
        img = img.resize((320, 320))
        img.save(path, "JPEG")

    return await asyncio.to_thread(_resize_thumb, ph_path)

async def add_metadata(input_path, output_path, user_id):
    ffmpeg_cmd = shutil.which('ffmpeg')
    if not ffmpeg_cmd:
        raise RuntimeError("FFmpeg not found in PATH")

    metadata_command = [
        ffmpeg_cmd,
        '-i', input_path,
        '-metadata', f'title={await codeflixbots.get_title(user_id)}',
        '-metadata', f'artist={await codeflixbots.get_artist(user_id)}',
        '-metadata', f'author={await codeflixbots.get_author(user_id)}',
        '-metadata:s:v', f'title={await codeflixbots.get_video(user_id)}',
        '-metadata:s:a', f'title={await codeflixbots.get_audio(user_id)}',
        '-metadata:s:s', f'title={await codeflixbots.get_subtitle(user_id)}',
        '-metadata', f'encoded_by={await codeflixbots.get_encoded_by(user_id)}',
        '-metadata', f'custom_tag={await codeflixbots.get_custom_tag(user_id)}',
        '-map', '0',
        '-c', 'copy',
        '-loglevel', 'error',
        output_path
    ]

    process = await asyncio.create_subprocess_exec(
        *metadata_command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    _, stderr = await process.communicate()

    if process.returncode != 0:
        raise RuntimeError(f"FFmpeg error: {stderr.decode()}")
