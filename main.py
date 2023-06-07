import logging
import requests

from khl import Bot, Message, MessageTypes
from secret import token
from random import choice

from library.utils import request_API, bftracker_recent
from library.cardTemplate import (
    render_stat_card, render_find_server_card, render_recent_card
)

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
    if isinstance(result, requests.Response):
        if result.status_code == 404:
            logging.warning(f'BF1 User {origin_id} not found')
        await msg.reply(f'玩家{origin_id}不存在')
        return
    await msg.reply(render_stat_card(result))

@bot.command(name='f')
async def bf1_find_server(msg: Message, server_name: str):
    result = request_API('bf1', 'servers', {'name': server_name, 'lang':'zh-tw'})
    if isinstance(result, requests.Response):
        if result.status_code == 404:
            logging.warning(f'error getting server info')
        await msg.reply(f'找不到任何相关服务器')
        return
    await msg.reply(render_find_server_card(result))

@bot.command(name='r')
async def bf1_recent(msg: Message, origin_id: str):
    result = bftracker_recent(origin_id)
    if isinstance(result, str):
        logging.warning(result)
        await msg.reply(result)
        return
    await msg.reply(render_recent_card(result))
    #await msg.reply(cm)

logging.basicConfig(level='INFO')
bot.run()