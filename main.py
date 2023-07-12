import logging
import sqlite3
import requests
import atexit

from khl import Bot, Message
from secret import token, super_admin

from library.bf1_stat import init_stat
from library.bf1_account import init_account
from library.bf1_server import init_server
from library.bf1_rsp import init_rsp
from library.misc import init_misc

bot = Bot(token=token)
logging.basicConfig(level='INFO')
conn = sqlite3.connect('bot.db')

def close_db():
    conn.close()

@bot.on_startup
async def bot_init(bot: Bot):
    init_stat(bot, conn)
    #logging.info("BF1 stat module launched")
    init_account(bot, conn, super_admin)
    #logging.info("BF1 account binding module launched")
    init_server(bot, conn, super_admin)
    #logging.info("BF1 server group management module launched")
    init_rsp(bot, conn, super_admin)
    #logging.info("BF1 server management(RSP) module launched")
    init_misc(bot)
    #logging.info("Miscellaneous module launched")


atexit.register(close_db)
bot.run()