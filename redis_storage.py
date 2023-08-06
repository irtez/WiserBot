from aioredis import Redis
from aiogram.fsm.storage.redis import RedisStorage

redis = Redis(host='127.0.0.1', port=6379)
storage = RedisStorage(redis=redis)