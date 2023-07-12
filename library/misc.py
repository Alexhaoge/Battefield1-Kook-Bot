# -- coding: utf-8 --
from khl import Bot, Message
from random import choice

def init_misc(bot: Bot):
    hello_messages = ['你好！', 'Hello!', 'Bonjour!', 'Hola!', 'Ciao!', 'Hallo!', 'こんにちは!']

    @bot.command(name='hello')
    async def world(msg: Message):
        """
        /hello return welcome message
        """
        await msg.reply(choice(hello_messages))

    @bot.command(regex=u".*涩图+.*")
    async def setu_zhu(msg: Message):
        await msg.add_reaction(u"🐷")

    @bot.command(name='help')
    async def get_help(msg: Message):
        pass

    @bot.command(name='about')
    async def get_about_info(msg: Message):
        pass