import motor.motor_asyncio
import datetime
import pytz
import logging
from config import Config
from datetime import timedelta, datetime

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
        self.users = self.database['user']
        self.channel_data = self.database['channels']
        self.admins_data = self.database['admins']
        self.autho_user_data = self.database['autho_user']
        self.fsub_data = self.database['fsub']
        self.rqst_fsub_data = self.database['request_forcesub']
        self.rqst_fsub_Channel_data = self.database['request_forcesub_channel']
        self.counts = self.database['counts']
        self.verification_data = self.database['verification']
        self.verification_settings = self.database['verification_settings']
        self.banned_users = self.database['banned_users']

    def new_user(self, id, username=None):
        return dict(
            _id=int(id),
            username=username.lower() if username else None,
            join_date=datetime.date.today().isoformat(),
            file_id=None,
            caption=None,
            metadata=True,
            metadata_code="Telegram : @codeflixbots",
            format_template=None,
            rename_count=0,
            ban_status=dict(
                is_banned=False,
                ban_duration=0,
                banned_on=datetime.date.max.isoformat(),
                ban_reason='',
            )
        )

    async def save_verification(self, user_id):
        now = datetime.now(self.timezone)
        verification = {"user_id": user_id, "verified_at": now}
        await self.verification_data.insert_one(verification)

    def get_start_end_dates_verification(self, time_period, year=None):
        now = datetime.now(self.timezone)
        
        if time_period == 'today':
            start_datetime = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end_datetime = now
        elif time_period == 'yesterday':
            start_datetime = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            end_datetime = start_datetime + timedelta(days=1)
        elif time_period == 'this_week':
            start_datetime = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
            end_datetime = now
        elif time_period == 'this_month':
            start_datetime = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end_datetime = now
        elif time_period == 'last_month':
            first_day_of_current_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            last_month_end_datetime = first_day_of_current_month - timedelta(microseconds=1)
            start_datetime = last_month_end_datetime.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end_datetime = last_month_end_datetime
        elif time_period == 'year' and year:
            start_datetime = datetime(year, 1, 1, tzinfo=self.timezone)
            end_datetime = datetime(year + 1, 1, 1, tzinfo=self.timezone) - timedelta(microseconds=1)
        else:
            raise ValueError("Invalid time period")
        
        return start_datetime, end_datetime

    async def get_vr_count(self, time_period, year=None):
        start_datetime, end_datetime = self.get_start_end_dates_verification(time_period, year)
        count = await self.verification_data.count_documents({
            'verified_at': {'$gte': start_datetime, '$lt': end_datetime}
        })
        return count

    async def get_vr_count_combined(self, time_period, year=None):
        start_datetime, end_datetime = self.get_start_end_dates_verification(time_period, year)
        count = await self.users.count_documents({
            '$or': [
                {'verify_status_1.verified_time_1': {'$gte': start_datetime, '$lt': end_datetime}},
                {'verify_status_2.verified_time_2': {'$gte': start_datetime, '$lt': end_datetime}}
            ]
        })
        return count

    async def db_verify_status(self, user_id):
        default_verify = {
            'is_verified_1': False,
            'verified_time_1': 0,
            'is_verified_2': False,
            'verified_time_2': 0,
        }
        user = await self.users.find_one({'_id': user_id})
        if user:
            return {
                'verify_status_1': user.get('verify_status_1', default_verify),
                'verify_status_2': user.get('verify_status_2', default_verify)
            }
        return {'verify_status_1': default_verify, 'verify_status_2': default_verify}

    async def db_update_verify_status(self, user_id, verify_data):
        await self.users.update_one({'_id': user_id}, {'$set': verify_data})

    async def get_verify_status(self, user_id):
        return await self.db_verify_status(user_id)

    async def update_verify_status(self, user_id, is_verified_1=False, verified_time_1=None, is_verified_2=False, verified_time_2=None):
        verify_data = {
            'is_verified_1': is_verified_1,
            'verified_time_1': verified_time_1,
            'is_verified_2': is_verified_2,
            'verified_time_2': verified_time_2
        }
        await self.db_update_verify_status(user_id, verify_data)

    async def get_verification_mode_2(self, channel_id: int):
        data = await self.verification_data.find_one({'_id': channel_id})
        return data.get("mode", "off") if data else "off"

    async def set_verification_mode_2(self, channel_id: int, mode: str):
        await self.verification_data.update_one(
            {'_id': channel_id},
            {'$set': {'mode': mode}},
            upsert=True
        )

    async def get_verification_mode_1(self, channel_id: int):
        data = await self.verification_data.find_one({'_id': channel_id})
        return data.get("mode", "off") if data else "off"

    async def set_verification_mode_1(self, channel_id: int, mode: str):
        await self.verification_data.update_one(
            {'_id': channel_id},
            {'$set': {'mode': mode}},
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

    async def update_verification_settings(self, verify_token_1: str = None, api_link_1: str = None, verify_token_2: str = None, api_link_2: str = None):
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
        await self.update_verification_settings(api_link_1_s=api_link_1, verify_token_1_s=verify_token_1)

    async def set_verify_2(self, api_link: str, verify_token: str):
        """Sets the API link and verification token for verification method 2."""
        await self.update_verification_settings(api_link_2_s=api_link_2, verify_token_2_s=verify_token_2)

    async def add_user(self, b, m):
        u = m.from_user
        if not await self.is_user_exist(u.id):
            user = self.new_user(u.id, u.username)
            try:
                await self.users.insert_one(user)
                # Assuming send_log is defined elsewhere
                await self.send_log(b, u)
            except Exception as e:
                logging.error(f"Error adding user {u.id}: {e}")

    async def get_user(self, user_id):
        user_data = await self.users.find_one({"_id": user_id})
        return user_data

    async def update_user(self, user_data):
        await self.users.update_one({"_id": user_data["_id"]}, {"$set": user_data}, upsert=True)

    async def is_user_exist(self, id):
        try:
            user = await self.users.find_one({"_id": int(id)})
            return bool(user)
        except Exception as e:
            logging.error(f"Error checking if user {id} exists: {e}")
            return False

    async def total_users_count(self):
        try:
            count = await self.users.count_documents({})
            return count
        except Exception as e:
            logging.error(f"Error counting users: {e}")
            return 0

    async def get_all_users(self):
        try:
            all_users = self.users.find({})
            return all_users
        except Exception as e:
            logging.error(f"Error getting all users: {e}")
            return None

    async def delete_user(self, user_id):
        try:
            await self.users.delete_many({"_id": int(user_id)})
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
            print(f"[DB ERROR] Failed to add user to request list: {e}")

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
            print(f"[DB ERROR] Failed to check request list: {e}")
            return False

    async def reqChannel_exist(self, channel_id: int):
        channel_ids = await self.show_channels()
        return channel_id in channel_ids

    async def update_premium_user(self, user_data):
        await self.users.update_one({"_id": user_data["_id"]}, {"$set": premium_data}, upsert=True)

    async def has_premium_access(self, user_id):
        user_data = await self.get_user(user_id)
        if user_data:
            expiry_time = user_data.get("expiry_time")
            if expiry_time is None:
                return False
            elif isinstance(expiry_time, datetime) and datetime.now() <= expiry_time:
                return True
            else:
                await self.users.update_one({"_id": user_id}, {"$set": {"expiry_time": None}})
        return False

    async def get_expired(self, current_time):
        expired_users = []
        async for user in self.users.find({"expiry_time": {"$lt": current_time}}):
            expired_users.append(user)
        return expired_users

    async def remove_premium_access(self, user_id):
        return await self.users.update_one(
            {"_id": user_id}, {"$set": {"expiry_time": None}}
        )

    async def all_premium_users(self):
        count = await self.users.count_documents({
            "expiry_time": {"$gt": datetime.now()}
        })
        
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
            await self.col.update_one(
                {"_id": int(id)}, {"$set": {"format_template": format_template}}
            )
        except Exception as e:
            logging.error(f"Error setting format template for user {id}: {e}")

    async def get_format_template(self, id):
        try:
            user = await self.col.find_one({"_id": int(id)})
            return user.get("format_template", None) if user else None
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

    async def get_metadata(self, user_id):
        user = await self.col.find_one({'_id': int(user_id)})
        return user.get('metadata', "Off")

    async def set_metadata(self, user_id, metadata):
        await self.col.update_one({'_id': int(user_id)}, {'$set': {'metadata': metadata}})

    async def get_title(self, user_id):
        user = await self.col.find_one({'_id': int(user_id)})
        return user.get('title', 'Bots kingdom')

    async def set_title(self, user_id, title):
        await self.col.update_one({'_id': int(user_id)}, {'$set': {'title': title}})

    async def get_author(self, user_id):
        user = await self.col.find_one({'_id': int(user_id)})
        return user.get('author', 'Botskingdoms')

    async def set_author(self, user_id, author):
        await self.col.update_one({'_id': int(user_id)}, {'$set': {'author': author}})

    async def get_artist(self, user_id):
        user = await self.col.find_one({'_id': int(user_id)})
        return user.get('artist', 'Botskingdoms')

    async def set_artist(self, user_id, artist):
        await self.col.update_one({'_id': int(user_id)}, {'$set': {'artist': artist}})

    async def get_audio(self, user_id):
        user = await self.col.find_one({'_id': int(user_id)})
        return user.get('audio', 'Bots kingdom')

    async def set_audio(self, user_id, audio):
        await self.col.update_one({'_id': int(user_id)}, {'$set': {'audio': audio}})

    async def get_subtitle(self, user_id):
        user = await self.col.find_one({'_id': int(user_id)})
        return user.get('subtitle', "Botskingdoms")

    async def set_subtitle(self, user_id, subtitle):
        await self.col.update_one({'_id': int(user_id)}, {'$set': {'subtitle': subtitle}})

    async def get_video(self, user_id):
        user = await self.col.find_one({'_id': int(user_id)})
        return user.get('video', 'Botskingdoms')

    async def set_video(self, user_id, video):
        await self.col.update_one({'_id': int(user_id)}, {'$set': {'video': video}})

    async def get_encoded_by(self, user_id):
        user = await self.col.find_one({'_id': int(user_id)})
        return user.get('encoded_by', "Botskingdoms")

    async def set_encoded_by(self, user_id, encoded_by):
        await self.col.update_one({'_id': int(user_id)}, {'$set': {'encoded_by': encoded_by}})

    async def get_custom_tag(self, user_id):
        user = await self.col.find_one({'_id': int(user_id)})
        return user.get('customtag', "Botskingdoms")

    async def set_custom_tag(self, user_id, custom_tag):
        await self.col.update_one({'_id': int(user_id)}, {'$set': {'custom_tag': custom_tag}})

codeflixbots = Database(Config.DB_URL, Config.DB_NAME)
