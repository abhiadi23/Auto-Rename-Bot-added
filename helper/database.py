import motor.motor_asyncio
import pytz
import logging
from config import Config
from datetime import timedelta, datetime, date, timezone

class Database:
    def __init__(self, uri, database_name):
        try:
            self._client = motor.motor_asyncio.AsyncIOMotorClient(uri)
            self._client.server_info()
            logging.info("Successfully connected to MongoDB")
        except Exception as e:
            logging.error(f"Failed to connect to MongoDB: {e}")
            raise e
        self.database = self._client[database_name]
        self.channel_data = self.database['channels']
        self.admins_data = self.database['admins']
        self.autho_user_data = self.database['autho_user']
        self.fsub_data = self.database['fsub']
        self.rqst_fsub_data = self.database['request_forcesub']
        self.rqst_fsub_Channel_data = self.database['request_forcesub_channel']
        self.counts = self.database['counts']
        self.verification_data = self.database['verification']
        self.premium_users = self.database['premium_users']
        self.verification_settings = self.database['verification_settings']
        self.banned_users = self.database['banned_users']
        self.col = self.database.users
        self.timezone = timezone.utc

    def new_user(self, id, username=None):
        return dict(
            _id=int(id),
            username=username.lower() if username else None,
            join_date=date.today().isoformat(),
            file_id=None,
            caption=None,
            verification_mode_1=True,
            verification_mode_2=True,
            metadata=True,
            metadata_code="Telegram : @codeflixbots",
            format_template=None,
            rename_count=0,
            ban_status=dict(
                is_banned=False,
                ban_duration=0,
                banned_on=date.max.isoformat(),
                ban_reason='',
            )
        )

    async def save_verification(self, user_id):
    """Save verification timestamp when user completes shortlink"""
    now = datetime.now(self.timezone)
    verification = {"user_id": user_id, "verified_at": now}
    await self.verification_data.insert_one(verification)

def get_start_end_dates_verification(self, time_period, year=None):
    """Get start and end dates for verification counting"""
    now = datetime.now(self.timezone)
    
    if time_period == 'today':
        start_datetime = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_datetime = now.replace(hour=23, minute=59, second=59, microsecond=999999)
    elif time_period == 'yesterday':
        yesterday = now - timedelta(days=1)
        start_datetime = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
        end_datetime = yesterday.replace(hour=23, minute=59, second=59, microsecond=999999)
    elif time_period == 'this_week':
        start_datetime = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
        end_datetime = now
    elif time_period == 'this_month':
        start_datetime = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end_datetime = now
    elif time_period == 'last_month':
        first_day_of_current_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        last_day_of_last_month = first_day_of_current_month - timedelta(microseconds=1)
        start_datetime = last_day_of_last_month.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end_datetime = last_day_of_last_month.replace(hour=23, minute=59, second=59, microsecond=999999)
    elif time_period == 'year' and year:
        start_datetime = datetime(year, 1, 1, tzinfo=self.timezone)
        end_datetime = datetime(year, 12, 31, 23, 59, 59, 999999, tzinfo=self.timezone)
    else:
        raise ValueError("Invalid time period")
    
    return start_datetime, end_datetime

async def get_vr_count_combined(self, time_period, year=None):
    """
    Get verification count from users collection by checking verified timestamps
    This counts users who verified in the given time period
    """
    try:
        start_datetime, end_datetime = self.get_start_end_dates_verification(time_period, year)
        
        # Make sure both datetimes are timezone-aware
        if start_datetime.tzinfo is None:
            start_datetime = start_datetime.replace(tzinfo=self.timezone)
        if end_datetime.tzinfo is None:
            end_datetime = end_datetime.replace(tzinfo=self.timezone)
        
        # Count users who verified during this time period
        count = await self.col.count_documents({
            '$or': [
                {
                    'verify_status_1.is_verified_1': True,
                    'verify_status_1.verified_time_1': {
                        '$gte': start_datetime, 
                        '$lte': end_datetime
                    }
                },
                {
                    'verify_status_2.is_verified_2': True,
                    'verify_status_2.verified_time_2': {
                        '$gte': start_datetime, 
                        '$lte': end_datetime
                    }
                }
            ]
        })
        
        logging.info(f"Verification count for {time_period}: {count} (from {start_datetime} to {end_datetime})")
        return count
        
    except Exception as e:
        logging.error(f"Error getting verification count for {time_period}: {e}")
        return 0

    async def db_verify_status(self, user_id):
        default_verify = {
            'is_verified_1': False,
            'verified_time_1': 0,
            'is_verified_2': False,
            'verified_time_2': 0,
        }
        user = await self.col.find_one({'_id': user_id})
        if user:
            return {
                'verify_status_1': user.get('verify_status_1', default_verify),
                'verify_status_2': user.get('verify_status_2', default_verify)
            }
        return {'verify_status_1': default_verify, 'verify_status_2': default_verify}

    async def get_verify_status(self, user_id):
        return await self.db_verify_status(user_id)

    async def update_verify_status(self, user_id, is_verified_1=False, verified_time_1=None, is_verified_2=False, verified_time_2=None):
        verify_data = {
            'verify_status_1': {
                'is_verified_1': is_verified_1,
                'verified_time_1': verified_time_1 or datetime.now(self.timezone),
            },
            'verify_status_2': {
                'is_verified_2': is_verified_2,
                'verified_time_2': verified_time_2 or datetime.now(self.timezone),
            }
        }
        await self.db_update_verify_status(user_id, verify_data)

    async def db_update_verify_status(self, user_id, verify_data):
        await self.col.update_one({'_id': user_id}, {'$set': verify_data})

    async def get_verification_mode_1(self):
        settings = await self.verification_settings.find_one({'_id': 'global_settings'})
        return settings.get('verify_status_1', False) if settings else False
    
    async def set_verification_mode_1(self, status: bool):
        await self.verification_settings.update_one(
            {'_id': 'global_settings'}, 
            {'$set': {'verify_status_1': status}},
            upsert=True
        )

    async def get_verification_mode_2(self):
        settings = await self.verification_settings.find_one({'_id': 'global_settings'})
        return settings.get('verify_status_2', False) if settings else False
    
    async def set_verification_mode_2(self, status: bool):
        await self.verification_settings.update_one(
            {'_id': 'global_settings'}, 
            {'$set': {'verify_status_2': status}},
            upsert=True
        )
    
    async def get_verification_settings(self):
        settings = await self.verification_settings.find_one({'_id': 'global_settings'})
        if not settings:
            default_settings = {
                '_id': 'global_settings',
                'verify_token_1': "not set",
                'verify_status_1': False,
                'api_link_1': "not set",
                'verify_token_2': "not set",
                'verify_status_2': False,
                'api_link_2': "not set"
            }
            await self.verification_settings.insert_one(default_settings)
            settings = default_settings
        return settings

    async def update_verification_settings(self, verify_token_1=None, api_link_1=None, verify_token_2=None, api_link_2=None):
        settings_to_update = {}
        if verify_token_1 is not None:
            settings_to_update['verify_token_1'] = verify_token_1
        if api_link_1 is not None:
            settings_to_update['api_link_1'] = api_link_1
        if verify_token_2 is not None:
            settings_to_update['verify_token_2'] = verify_token_2
        if api_link_2 is not None:
            settings_to_update['api_link_2'] = api_link_2

        if settings_to_update:
            await self.verification_settings.update_one(
                {"_id": "global_settings"},
                {"$set": settings_to_update},
                upsert=True
            )

    async def set_verify_1(self, api_link: str, verify_token: str):
        """Sets the API link and verification token for verification method 1."""
        await self.update_verification_settings(api_link_1=api_link, verify_token_1=verify_token)

    async def set_verify_2(self, api_link: str, verify_token: str):
        """Sets the API link and verification token for verification method 2."""
        await self.update_verification_settings(api_link_2=api_link, verify_token_2=verify_token)

    async def add_user(self, b, m):
        u = m.from_user
        if not await self.is_user_exist(u.id):
            user = self.new_user(u.id, u.username)
            try:
                await self.col.insert_one(user)
                logging.info(f"New user added: {u.id}")
                await send_log(b, u)
            except Exception as e:
                logging.error(f"Error adding user {u.id}: {e}")
            else:
                logging.info(f"User {u.id} already exists") 

    async def ensure_user_exists(self, user_id, username=None):
        """Ensure user exists in database before operations"""
        if not await self.is_user_exist(user_id):
            user = self.new_user(user_id, username)
            try:
                await self.col.insert_one(user)
                logging.info(f"User {user_id} created in database")
                return True
            except Exception as e:
                logging.error(f"Error creating user {user_id}: {e}")
                return False
        return True
                
    async def get_user(self, user_id):
        user_data = await self.col.find_one({"_id": user_id})
        return user_data

    async def update_user(self, user_data):
        await self.col.update_one({"_id": user_data["_id"]}, {"$set": user_data}, upsert=True)

    async def is_user_exist(self, id):
        try:
            user = await self.col.find_one({"_id": int(id)})
            return bool(user)
        except Exception as e:
            logging.error(f"Error checking if user {id} exists: {e}")
            return False

    async def total_users_count(self):
        try:
            count = await self.col.count_documents({})
            return count
        except Exception as e:
            logging.error(f"Error counting users: {e}")
            return 0

    async def get_all_users(self):
        try:
            all_users = self.col.find({})
            return all_users
        except Exception as e:
            logging.error(f"Error getting all users: {e}")
            return None

    async def delete_user(self, user_id):
        try:
            await self.col.delete_many({"_id": int(user_id)})
        except Exception as e:
            logging.error(f"Error deleting user {user_id}: {e}")

    # ADMIN DATA
    async def admin_exist(self, admin_id: int):
        found = await self.admins_data.find_one({'_id': admin_id})
        return bool(found)

    async def add_admin(self, admin_id: int):
        if not await self.admin_exist(admin_id):
            await self.admins_data.insert_one({'_id': admin_id})

    async def del_admin(self, admin_id: int):
        if await self.admin_exist(admin_id):
            await self.admins_data.delete_one({'_id': admin_id})

    async def get_all_admins(self):
        users_docs = await self.admins_data.find().to_list(length=None)
        user_ids = [doc['_id'] for doc in users_docs]
        return user_ids

    # CHANNEL MANAGEMENT
    async def channel_exist(self, channel_id: int):
        found = await self.fsub_data.find_one({'_id': channel_id})
        return bool(found)

    async def add_channel(self, channel_id: int):
        if not await self.channel_exist(channel_id):
            await self.fsub_data.insert_one({'_id': channel_id})

    async def rem_channel(self, channel_id: int):
        if await self.channel_exist(channel_id):
            await self.fsub_data.delete_one({'_id': channel_id})

    async def show_channels(self):
        channel_docs = await self.fsub_data.find().to_list(length=None)
        channel_ids = [doc['_id'] for doc in channel_docs]
        return channel_ids

    async def get_channel_mode(self, channel_id: int):
        data = await self.fsub_data.find_one({'_id': channel_id})
        return data.get("mode", "off") if data else "off"

    async def set_channel_mode(self, channel_id: int, mode: str):
        await self.fsub_data.update_one(
            {'_id': channel_id},
            {'$set': {'mode': mode}},
            upsert=True
        )

    # REQUEST FORCE-SUB MANAGEMENT
    async def req_user(self, channel_id: int, user_id: int):
        try:
            await self.rqst_fsub_Channel_data.update_one(
                {'_id': int(channel_id)},
                {'$addToSet': {'user_ids': int(user_id)}},
                upsert=True
            )
        except Exception as e:
            logging.error(f"[DB ERROR] Failed to add user to request list: {e}")

    async def del_req_user(self, channel_id: int, user_id: int):
        await self.rqst_fsub_Channel_data.update_one(
            {'_id': channel_id},
            {'$pull': {'user_ids': user_id}}
        )

    async def req_user_exist(self, channel_id: int, user_id: int):
        try:
            found = await self.rqst_fsub_Channel_data.find_one({
                '_id': int(channel_id),
                'user_ids': int(user_id)
            })
            return bool(found)
        except Exception as e:
            logging.error(f"[DB ERROR] Failed to check request list: {e}")
            return False

    async def reqChannel_exist(self, channel_id: int):
        channel_ids = await self.show_channels()
        return channel_id in channel_ids

    # Premium Management - Fixed implementation
    async def add_premium(self, user_id: int, duration_days: int = 30):
        """Add premium access for a user"""
        expiration_time = datetime.now(self.timezone) + timedelta(days=duration_days)
        premium_data = {
            "_id": user_id,
            "expiry_time": expiration_time,
            "is_premium": True
        }
        await self.col.update_one(
            {"_id": user_id}, 
            {"$set": premium_data}, 
            upsert=True
        )

    async def has_premium_access(self, user_id):
        user_data = await self.get_user(user_id)
        if user_data:
            expiry_time = user_data.get("expiry_time")
            if expiry_time is None:
                return False
            elif isinstance(expiry_time, datetime):
                # Get current time with timezone
                current_time = datetime.now(self.timezone)
                
                # MongoDB returns datetime as naive even if stored as aware
                # Add timezone info back if it's missing
                if expiry_time.tzinfo is None:
                    expiry_time = expiry_time.replace(tzinfo=self.timezone)
                
                # Now both are timezone-aware, safe to compare
                if current_time <= expiry_time:
                    return True
                else:
                    # Premium expired, remove it
                    await self.col.update_one({"_id": user_id}, {"$set": {"expiry_time": None, "is_premium": False}})
            else:
                # Invalid expiry_time format, clean it up
                await self.col.update_one({"_id": user_id}, {"$set": {"expiry_time": None, "is_premium": False}})
        return False

    async def get_expired(self, current_time=None):
        if current_time is None:
            current_time = datetime.now(self.timezone)
        expired_users = []
        async for user in self.col.find({"expiry_time": {"$lt": current_time}}):
            expired_users.append(user)
        return expired_users

    async def remove_premium_access(self, user_id):
        return await self.col.update_one(
            {"_id": user_id}, 
            {"$set": {"expiry_time": None, "is_premium": False}}
        )

    async def all_premium_users(self):
        count = await self.col.count_documents({
            "expiry_time": {"$gt": datetime.now(self.timezone)}
        })
        return count

    async def set_thumbnail(self, id, file_id):
        try:
            await self.col.update_one({"_id": int(id)}, {"$set": {"file_id": file_id}})
        except Exception as e:
            logging.error(f"Error setting thumbnail for user {id}: {e}")

    async def get_thumbnail(self, id):
        try:
            user = await self.col.find_one({"_id": int(id)})
            return user.get("file_id", None) if user else None
        except Exception as e:
            logging.error(f"Error getting thumbnail for user {id}: {e}")
            return None

    async def set_caption(self, id, caption):
        try:
            await self.col.update_one({"_id": int(id)}, {"$set": {"caption": caption}})
        except Exception as e:
            logging.error(f"Error setting caption for user {id}: {e}")

    async def get_caption(self, id):
        try:
            user = await self.col.find_one({"_id": int(id)})
            return user.get("caption", None) if user else None
        except Exception as e:
            logging.error(f"Error getting caption for user {id}: {e}")
            return None

    async def set_format_template(self, id, format_template):
        try:
            result = await self.col.update_one(
                {"_id": int(id)}, 
                {"$set": {"format_template": format_template}},
                upsert=True
            )
            logging.info(f"Format template set for user {id}: {format_template}, Modified: {result.modified_count}, Upserted: {result.upserted_id}")
            return True
        except Exception as e:
            logging.error(f"Error setting format template for user {id}: {e}")
            return False

    async def get_format_template(self, id):
        try:
            user = await self.col.find_one({"_id": int(id)})
            if user:
                template = user.get("format_template", None)
                logging.info(f"Retrieved format template for user {id}: {template}")
                return template
            else:
                logging.warning(f"User {id} not found in database")
                return None
        except Exception as e:
            logging.error(f"Error getting format template for user {id}: {e}")
            return None

    async def set_media_preference(self, id, media_type):
        try:
            await self.col.update_one(
                {"_id": int(id)}, {"$set": {"media_type": media_type}}
            )
        except Exception as e:
            logging.error(f"Error setting media preference for user {id}: {e}")

    async def get_media_preference(self, id):
        try:
            user = await self.col.find_one({"_id": int(id)})
            return user.get("media_type", None) if user else None
        except Exception as e:
            logging.error(f"Error getting media preference for user {id}: {e}")
            return None

    async def ban_user(self, user_id):
        await self.banned_users.update_one(
            {"_id": user_id},
            {"$set": {
                "ban_status.is_banned": True,
                "ban_status.ban_reason": "reason",
                "ban_status.banned_on": date.today().isoformat()
            }},
            upsert=True
        )
 
    async def unban_user(self, user_id):
        await self.banned_users.update_one(
            {"_id": user_id},
            {"$set": {
                "ban_status.is_banned": False,
                "ban_status.ban_reason": "",
                "ban_status.banned_on": None
            }}
        )

    async def is_banned(self, user_id):
        return await self.banned_users.find_one({'_id': int(user_id)})

    async def get_banned_users(self, user_id):
        return self.banned_users.find({"ban_status.is_banned": True})

    async def get_metadata(self, user_id):
        user = await self.col.find_one({'_id': int(user_id)})
        return user.get('metadata', "Off")

    async def set_metadata(self, user_id, metadata):
        await self.col.update_one({'_id': int(user_id)}, {'$set': {'metadata': metadata}})

    async def get_title(self, user_id):
        user = await self.col.find_one({'_id': int(user_id)})
        return user.get('title', 'Botskingdom')

    async def set_title(self, user_id, title):
        await self.col.update_one({'_id': int(user_id)}, {'$set': {'title': title}})

    async def get_author(self, user_id):
        user = await self.col.find_one({'_id': int(user_id)})
        return user.get('author', 'Botskingdom')

    async def set_author(self, user_id, author):
        await self.col.update_one({'_id': int(user_id)}, {'$set': {'author': author}})

    async def get_artist(self, user_id):
        user = await self.col.find_one({'_id': int(user_id)})
        return user.get('artist', 'Botskingdom')

    async def set_artist(self, user_id, artist):
        await self.col.update_one({'_id': int(user_id)}, {'$set': {'artist': artist}})

    async def get_audio(self, user_id):
        user = await self.col.find_one({'_id': int(user_id)})
        return user.get('audio', 'Botskingdom')

    async def set_audio(self, user_id, audio):
        await self.col.update_one({'_id': int(user_id)}, {'$set': {'audio': audio}})

    async def get_subtitle(self, user_id):
        user = await self.col.find_one({'_id': int(user_id)})
        return user.get('subtitle', "Botskingdom")

    async def set_subtitle(self, user_id, subtitle):
        await self.col.update_one({'_id': int(user_id)}, {'$set': {'subtitle': subtitle}})

    async def get_video(self, user_id):
        user = await self.col.find_one({'_id': int(user_id)})
        return user.get('video', 'Botskingdom')

    async def set_video(self, user_id, video):
        await self.col.update_one({'_id': int(user_id)}, {'$set': {'video': video}})

    async def get_encoded_by(self, user_id):
        user = await self.col.find_one({'_id': int(user_id)})
        return user.get('encoded_by', "Botskingdom")

    async def set_encoded_by(self, user_id, encoded_by):
        await self.col.update_one({'_id': int(user_id)}, {'$set': {'encoded_by': encoded_by}})
        
    async def get_custom_tag(self, user_id):
        user = await self.col.find_one({'_id': int(user_id)})
        return user.get('custom_tag', "Botskingdom")

    async def set_custom_tag(self, user_id, custom_tag):
        await self.col.update_one({'_id': int(user_id)}, {'$set': {'custom_tag': custom_tag}})
        
codeflixbots = Database(Config.DB_URL, Config.DB_NAME)
