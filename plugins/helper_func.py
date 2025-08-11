#(©)CodeFlix_Bots
#rohit_1888 on Tg #Dont remove this line

import re
import asyncio
from pyrogram import filters
from pyrogram.enums import ChatMemberStatus
from config import *
from pyrogram.errors.exceptions.bad_request_400 import UserNotParticipant
from helper.database import *


# Used for checking if a user is an admin. The bot owner is also treated as an admin.
async def check_admin(filter, client, update):
    try:
        user_id = update.from_user.id
        # Directly check if the user_id is in the OWNER_ID list.
        # This assumes OWNER_ID is a list or tuple of user IDs.
        return user_id in OWNER_ID or await codeflixbots.admin_exist(user_id)
    except Exception as e:
        print(f"!! Exception in check_admin: {e}")
        return False


async def is_subscribed(client, user_id):
    channel_ids = await codeflixbots.show_channels()

    if not channel_ids:
        return True

    # Check if the user is the bot owner first.
    if user_id in OWNER_ID:
        return True

    for cid in channel_ids:
        if not await is_sub(client, user_id, cid):
            # Retry once if a join request might be processing.
            mode = await codeflixbots.get_channel_mode(cid)
            if mode == "on":
                await asyncio.sleep(2)  # give time for @on_chat_join_request to process
                if await is_sub(client, user_id, cid):
                    continue
            return False

    return True


async def is_sub(client, user_id, channel_id):
    try:
        member = await client.get_chat_member(channel_id, user_id)
        status = member.status
        # print(f"[SUB] User {user_id} in {channel_id} with status {status}")
        return status in {
            ChatMemberStatus.OWNER,
            ChatMemberStatus.ADMINISTRATOR,
            ChatMemberStatus.MEMBER
        }

    except UserNotParticipant:
        mode = await codeflixbots.get_channel_mode(channel_id)
        if mode == "on":
            exists = await codeflixbots.req_user_exist(channel_id, user_id)
            # print(f"[REQ] User {user_id} join request for {channel_id}: {exists}")
            return exists
        # print(f"[NOT SUB] User {user_id} not in {channel_id} and mode != on")
        return False

    except Exception as e:
        print(f"!! Error in is_sub(): {e}")
        return False


subscribed = filters.create(is_subscribed)
admin = filters.create(check_admin)

# rohit_1888 on Tg :
