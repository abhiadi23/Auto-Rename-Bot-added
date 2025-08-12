# (©)CodeFlix_Bots
# rohit_1888 on Tg #Dont remove this line

import re
import asyncio
from pyrogram import filters, Client
from pyrogram.types import Message, CallbackQuery, Update
from pyrogram.enums import ChatMemberStatus
from config import OWNER_ID
from pyrogram.errors.exceptions.bad_request_400 import UserNotParticipant
from helper.database import codeflixbots # Assuming this is where your database functions are

# This decorator-like function is for creating custom filters.
# You can use it like @client.on_message(admin) to restrict a command to admins.
# The 'filter' parameter is not used in the function signature, as the pyrogram filter framework
# handles the client and update objects.
async def check_admin(filter, client: Client, update: Update):
    """
    Checks if a user is a bot admin or the owner.
    
    Args:
        filter: The filter object from Pyrogram.
        client: The Pyrogram client.
        update: The incoming update (Message, CallbackQuery, etc.).
        
    Returns:
        True if the user is an admin or owner, False otherwise.
    """
    try:
        user_id = update.from_user.id
        
        # Check if the user is the bot owner. OWNER_ID can be a single int or a list/tuple.
        if isinstance(OWNER_ID, (list, tuple)):
            is_owner = user_id in OWNER_ID
        else:
            is_owner = user_id == OWNER_ID
        
        # Check if the user is an admin from the database.
        is_db_admin = await codeflixbots.admin_exist(user_id)
        
        return is_owner or is_db_admin
        
    except Exception as e:
        print(f"‼️ Exception in check_admin: {e}")
        return False

# This function checks a user's subscription status across all required channels.
async def is_subscribed(client: Client, user_id: int):
    """
    Checks if a user is subscribed to all mandatory channels.
    
    Args:
        client: The Pyrogram client.
        user_id: The ID of the user to check.
        
    Returns:
        True if the user is subscribed to all channels or is the bot owner, False otherwise.
    """
    channel_ids = await codeflixbots.show_channels()
    
    # If there are no channels configured, everyone is considered subscribed.
    if not channel_ids:
        return True
    
    # Bot owner is always considered subscribed.
    if user_id in (OWNER_ID if isinstance(OWNER_ID, (list, tuple)) else [OWNER_ID]):
        return True
    
    for cid in channel_ids:
        if not await is_sub(client, user_id, cid):
            # Give a small delay and re-check if a join request might be pending.
            mode = await codeflixbots.get_channel_mode(cid)
            if mode == "on":
                await asyncio.sleep(2)  # Give time for the join request handler to process.
                if await is_sub(client, user_id, cid):
                    continue
            return False
            
    return True

# This is a helper function to check a single channel's subscription status.
async def is_sub(client: Client, user_id: int, channel_id: int):
    """
    Checks if a user is a member of a specific channel.
    
    Args:
        client: The Pyrogram client.
        user_id: The ID of the user.
        channel_id: The ID of the channel.
        
    Returns:
        True if the user is a member or has a pending join request (in "on" mode), False otherwise.
    """
    try:
        member = await client.get_chat_member(channel_id, user_id)
        status = member.status
        return status in {
            ChatMemberStatus.OWNER,
            ChatMemberStatus.ADMINISTRATOR,
            ChatMemberStatus.MEMBER
        }
        
    except UserNotParticipant:
        # User is not a participant. Check for pending join requests.
        mode = await codeflixbots.get_channel_mode(channel_id)
        if mode == "on":
            exists = await codeflixbots.req_user_exist(channel_id, user_id)
            return exists
        return False
        
    except Exception as e:
        print(f"‼️ Error in is_sub(): {e}")
        return False

# Create Pyrogram filters using the functions above.
subscribed = filters.create(is_subscribed)
admin = filters.create(check_admin)

# rohit_1888 on Tg :
