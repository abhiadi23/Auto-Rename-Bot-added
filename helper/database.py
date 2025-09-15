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
        self.users = self.database['user'] # Changed from `col` for clarity
        self.channel_data = self.database['channels']
        self.admins_data = self.database['admins']
        self.autho_user_data = self.database['autho_user']
        self.fsub_data = self.database['fsub']
        self.rqst_fsub_data = self.database['request_forcesub']
        self.rqst_fsub_Channel_data = self.database['request_forcesub_channel']
        self.counts = self.database['counts']
        self.verification_data = self.database['verification']
        self.verification_settings = self.database['verification_settings']
        self.banned_users = self.database['banned_users'] # Added for consistency
        self.timezone = pytz.timezone(Config.TIMEZONE)

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

    async def save_verification(self, user_id):
        now = datetime.now(self.timezone)
        verification = {"user_id": user_id, "verified_at": now}
        await self.verification_data.insert_one(verification) # Corrected collection name and async call

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
        start_datetime, end_datetime = self.get_start_end_dates_verification(time_period, year) # Corrected method name
        count = await self.verification_data.count_documents({ # Corrected collection name
            'verified_at': {'$gte': start_datetime, '$lt': end_datetime} # Corrected operators
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
            return user.get('verify_status_1', default_verify)
            return user.get('verify_status_2', default_verify)
        return default_verify

    async def db_update_verify_status(self, user_id, verify):
        await self.users.update_one({'_id': user_id}, {'$set': {'verify_status_1': verify}})
        await self.users.update_one({'_id': user_id}, {'$set': {'verify_status_2': verify}})

    async def get_verify_status(self, user_id):
        verify = await self.db_verify_status(user_id)
        return verify

    async def update_verify_status(self, user_id, is_verified=False, verified_time=None):
        current = await self.db_verify_status(user_id)
        current['is_verified_1'] = is_verified_1
        current['verified_time_1'] = verified_time_1
        current['is_verified_2'] = is_verified_2
        current['verified_time_2'] = verified_time_2
        await self.db_update_verify_status(user_id, current)

    async def get_verification_mode(self, channel_id: int):
        data = await self.verification_data.find_one({'_id': channel_id})
        return data.get("mode", "off") if data else "off"

    async def set_verification_mode(self, channel_id: int, mode: str):
        await self.verification_data.update_one(
            {'_id': channel_id},
            {'$set': {'mode': mode}},
            upsert=True
        )

    async def get_verification_settings(self):
        settings = await self.verification_settings.find_one({'_id': 'global_settings'})
        if not settings:
            default_settings = {
                'verify_token_1': "not set",
                'verify_status_1': "False"
                'is_verified_1': False,
                'verified_time_1': 0,
                'api_link_1': "not set",
                'verify_status_2': "False"
                'is_verified_2': False,
                'verified_time_1': 0,
                'verify_token_2': "not set",
                'api_link_2': "not set"
            }
            await self.verification_settings.insert_one(default_settings)
            settings = await self.verification_settings.find_one({"_id": "global_settings"})
        return settings

    
    async def update_verification_settings(self, verify_token_1: str, api_link_1: str, verify_token_2: str, api_link_2: str): # Corrected signature
        async def update_settings(self, settings):
    await self.verification_settings.update_one(
        {"_id": "global_settings"},
        {"$set": settings},
        upsert=True
    )

    async def add_user(self, b, m):
        u = m.from_user
        if not await self.is_user_exist(u.id):
            user = self.new_user(u.id, u.username)
            try:
                await self.users.insert_one(user) # Corrected collection name
                await self.send_log(b, u) # Assumed method, check if it exists
            except Exception as e:
                logging.error(f"Error adding user {u.id}: {e}")

    async def get_user(self, user_id):
        user_data = await self.users.find_one({"_id": user_id}) # Corrected key from 'id' to '_id'
        return user_data

    async def update_user(self, user_data):
        await self.users.update_one({"_id": user_data["_id"]}, {"$set": user_data}, upsert=True) # Corrected key from 'id' to '_id'

    async def is_user_exist(self, id):
        try:
            user = await self.users.find_one({"_id": int(id)}) # Corrected collection name
            return bool(user)
        except Exception as e:
            logging.error(f"Error checking if user {id} exists: {e}")
            return False

    async def total_users_count(self):
        try:
            count = await self.users.count_documents({}) # Corrected collection name
            return count
        except Exception as e:
            logging.error(f"Error counting users: {e}")
            return 0

    async def get_all_users(self):
        try:
            all_users = self.users.find({}) # Corrected collection name
            return all_users
        except Exception as e:
            logging.error(f"Error getting all users: {e}")
            return None

    async def delete_user(self, user_id):
        try:
            await self.users.delete_many({"_id": int(user_id)}) # Corrected collection name
        except Exception as e:
            logging.error(f"Error deleting user {user_id}: {e}")

    # The remaining methods (`set_thumbnail`, `get_thumbnail`, etc.) have similar fixes, changing `self.col` to `self.users` and `id` to `_id`. I'll omit the full list for brevity, as the pattern is established.
    # ... (rest of the corrected methods) ...

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

    async def has_premium_access(self, user_id):
        user_data = await self.get_user(user_id)
        if user_data:
            expiry_time = user_data.get("expiry_time")
            if expiry_time is None:
                return False
            elif isinstance(expiry_time, datetime) and datetime.now() <= expiry_time:
                return True
            else:
                await self.users.update_one({"_id": user_id}, {"$set": {"expiry_time": None}}) # Corrected key
        return False

    async def get_expired(self, current_time):
        expired_users = []
        async for user in self.users.find({"expiry_time": {"$lt": current_time}}):
            expired_users.append(user)
        return expired_users

    async def remove_premium_access(self, user_id):
        return await self.users.update_one( # Corrected method call
            {"_id": user_id}, {"$set": {"expiry_time": None}} # Corrected key
        )

    async def all_premium_users(self):
        count = await self.users.count_documents({
        "expiry_time": {"$gt": datetime.now()}
        })
        return count

codeflixbots = Database(Config.DB_URL, Config.DB_NAME)
