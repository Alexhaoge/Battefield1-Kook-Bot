from khl import Bot, Message
from secret import token
from random import choice

bot = Bot(token=token)

hello_messages = ['你好！', 'Hello!', 'Bonjour!', 'Hola!', 'Ciao!', 'Hallo!', 'こんにちは']

@bot.command(name='hello')
async def world(msg: Message):
    await msg.reply(choice(hello_messages))


bot.run()