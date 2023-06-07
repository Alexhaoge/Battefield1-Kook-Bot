import logging

from khl import Bot, Message, MessageTypes
from secret import token
from random import choice

from library.utils import request_API
from library.cardTemplate import render_stat_card

bot = Bot(token=token)

hello_messages = ['你好！', 'Hello!', 'Bonjour!', 'Hola!', 'Ciao!', 'Hallo!', 'こんにちは!']

@bot.command(name='hello')
async def world(msg: Message):
    """
    /hello return welcome message
    """
    await msg.reply(choice(hello_messages))

@bot.command(name='stat')
async def bf1_player_stat(msg: Message, origin_id: str):
    """
    /stat originid
    """
    result = request_API('bf1','all',{'name':origin_id, 'lang':'zh-tw'})
    # result['__update_time'] = time()
    # html = apply_template(result,'bf1', '/')
    # pic = await html_to_pic(html, viewport={"width": 700,"height":10})
    cm = render_stat_card(result)
    await msg.reply(cm)

@bot.command(name='f')
async def bf1_find_server(msg: Message, server_name: str):
    pass

logging.basicConfig(level='INFO')
bot.run()