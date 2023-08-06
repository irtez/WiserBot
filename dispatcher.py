from aiogram import Bot, Dispatcher
from config_reader import config
import routers.registration as registration
from middlewares.antispam import SpamMiddleware
from middlewares.againtimeout import TryAgainMiddleware
from redis_storage import storage
import routers.adminpanel as adminpanel
import routers.helpfaq as helpfaq
import routers.replyanswers as reply


bot = Bot(token=config.bot_token.get_secret_value(), parse_mode='HTML')


dp = Dispatcher(storage = storage)
dp.callback_query.outer_middleware(TryAgainMiddleware())
dp.message.outer_middleware(SpamMiddleware())
dp.include_router(adminpanel.router)
dp.include_router(registration.router)
dp.include_router(helpfaq.router)
dp.include_router(reply.router)

