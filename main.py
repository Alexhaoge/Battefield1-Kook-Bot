import logging

from khl import Bot, Message, MessageTypes
from secret import token
from random import choice
from nonebot_plugin_htmlrender import md_to_pic, html_to_pic

from .library.utils import request_API
from .library.cardTemplate import render_card

bot = Bot(token=token)

hello_messages = ['你好！', 'Hello!', 'Bonjour!', 'Hola!', 'Ciao!', 'Hallo!', 'こんにちは']

@bot.command(name='hello')
async def world(msg: Message):
    await msg.reply(choice(hello_messages))

@bot.command(name='stat')
async def bf1_player_stat(msg: Message, origin_id: str):
    result = request_API('bf1','all',{'name':origin_id, 'lang':'zh-tw'})
    # result['__update_time'] = time()
    # html = apply_template(result,'bf1', '/')
    # pic = await html_to_pic(html, viewport={"width": 700,"height":10})
    await msg.reply(render_card(result), type=MessageTypes.CARD)

logging.basicConfig(level='INFO')
bot.run()