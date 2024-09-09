# main.py
import asyncio

import discord
import requests
import random
import youtube_dl
from discord.ext import commands

disc_token = "<Insert Discord bot token here>"
tenor = "<Insert Tenor API key here>"
c_key = "<Insert client key here>"
lmt = 50

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)

youtube_dl.utils.bug_reports_message = lambda: ''


ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
}

ffmpeg_options = {
    'options': '-vn'
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)
player = None


# Class for acquiring songs based on user input
class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)

        self.data = data

        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

        if 'entries' in data:
            # take first item from a playlist
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)


# Plays a song based on user input
@bot.command()
async def play(ctx, *, url):
    if ctx.message.author.voice is None:
        await send_message(ctx.message, "Error: You are not in a voice channel.")
        return

    channel = ctx.message.author.voice.channel
    voice = discord.utils.get(ctx.message.guild.voice_channels, name=channel.name)
    voice_client = discord.utils.get(bot.voice_clients, guild=ctx.message.guild)

    if voice_client is None:
        await voice.connect()
        await send_message(ctx.message, f"Connected to {channel}")
    else:
        await send_message(ctx.message, f"Moved from {voice_client.channel} to {channel}")
        await ctx.message.guild.voice_client.move_to(voice)
    async with ctx.typing():
        global player
        player = await YTDLSource.from_url(url, loop=bot.loop)
        ctx.voice_client.play(player, after=lambda e: print(f'Player error: {e}') if e else None)
    await send_message(ctx, f"Now playing: {player.title}")

# Prints the name of the current song playing in the voice channel
@bot.command()
async def cs(ctx):
    if player is None:
        await send_message(ctx, "No song is currently playing.")
        return
    await send_message(ctx, f"Current song in the bot: {player.title}")


# Helper function to send direct message to user
async def send_dm(user, phrase):
    await user.send(phrase)


# Helper function to send message in a text channel
async def send_message(message, phrase):
    await message.channel.send(phrase)


# Helper function to send a phrase into a text channel based on
# the location of the message that triggers the function
async def send_gif(message, phrase):
    r = requests.get(f"https://tenor.googleapis.com/v2/search?q={phrase}&key={tenor}&client_key={c_key}&limit={1}")
    data = r.json()
    await send_message(message, data["results"][0]["media_formats"]["gif"]["url"])


# Helper function to send a GIF image from Tenor to a user
async def get_random_gif(message):
    r = requests.get(f"https://tenor.googleapis.com/v2/search?q={message}&key={tenor}&client_key={c_key}&limit={lmt}")
    data = r.json()
    chosen = random.choice(data["results"])
    return chosen["media_formats"]["gif"]["url"]


# A 'guild' is a server in Discord
@bot.event
async def on_ready():
    for guild in bot.guilds:
        print(f"{bot.user} joined {guild}")

    game = discord.Game("<Input desired bot's Discord status here>")
    await bot.change_presence(status=discord.Status.online, activity=game)


# Reads in messages in servers/direct messages to formulate response.
@bot.listen('on_message')
async def funny_stuff(message):
    if message.author == bot.user:
        return

    if isinstance(message.channel, discord.DMChannel):
        print(f"{message.author} said {message.content}")
        if int(message.author.id) == 165524480851050496 and message.content == "shutdown":
            await bot.change_presence(status=discord.Status.offline)
            await bot.close()
        else:
            chosen = await get_random_gif(message.content)
            await send_dm(message.author, chosen)
    else:
        if message.content.lower() == "hi bot":
            await send_message(message, f"Hi {message.author}")
        print(f"{message.channel}: {message.author.name} said {message.content}")


# Example command to send a fun GIF image
@bot.command()
async def pog(message):
    chosen = await get_random_gif("pog")
    await send_message(message, chosen)


# Command to allow bot to enter voice channel
@bot.command()
async def join(message):
    if message.author.voice is None:
        await send_message(message, "Error: You are not in a voice channel.")
        return

    channel = message.author.voice.channel
    voice = discord.utils.get(message.guild.voice_channels, name=channel.name)
    voice_client = discord.utils.get(bot.voice_clients, guild=message.guild)

    if voice_client is None:
        await voice.connect()
        await send_message(message, f"Connected to {channel}")
    elif voice_client.channel is not channel:
        await send_message(message, f"Moved from {voice_client.channel} to {channel}")
        await message.guild.voice_client.move_to(voice)


# Command to force bot to leave voice channel
@bot.command()
async def leave(message):
    if message.author.voice is None:
        await send_message(message, "Error: You are not in a voice channel.")
        return

    channel = message.author.voice.channel
    voice_client = discord.utils.get(bot.voice_clients, guild=message.guild)

    if voice_client is None:
        await send_message(message, "Error: I am not in a voice channel.")
        return

    if voice_client.channel is channel:
        await message.guild.voice_client.disconnect()
        await send_message(message, f"Disconnected from {channel}")
    else:
        await send_message(message, "Error: You are not in the same voice channel as me.")


# Example Help function for users to see commands
@bot.command()
async def commands(message):
    await send_message(message, "# 𝕭𝖔𝖙 𝕮𝖔𝖒𝖒𝖆𝖓𝖉𝖘 𝕷𝖎𝖘𝖙:\n"
                                "```\njoin: Connects the bot to the voice channel the user is in."
                                "\nleave: Disconnects the bot from the voice channel."
                                "\npog: Try it for yourself.```")

bot.run(disc_token)