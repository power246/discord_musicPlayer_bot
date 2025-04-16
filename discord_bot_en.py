#by Paul Liao
import os
import discord
from discord.ext import commands
import yt_dlp
import asyncio
import random

token = os.getenv("DISCORD_BOT_TOKEN")
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix = "!", intents = intents)

ytdl_format_options = {
    'format': 'bestaudio/best',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }],
    'noplaylist': True,
    'extractaudio': True,  # Force audio extraction only
    'audioquality': 1,  # High quality audio
    'prefer_ffmpeg': True,  # Extract audio using FFmpeg
    'keepvideo': False,  # Do not save the video
}
ffmpeg_options = {'options': '-vn',}
ytdl = yt_dlp.YoutubeDL(ytdl_format_options)

playlist = []
playdic = {}
current_play = -1
listnum = 0
random_flag = 0
self_flag = 0
sequential_flag = 0
single_flag = 1

@bot.command()
@commands.has_permissions(administrator = True)
async def synccommands(ctx):
    await bot.tree.sync()
    await ctx.send("sync done!")


@bot.hybrid_command()
async def ping(ctx):
    """test"""
    await ctx.send("pong")

@bot.hybrid_command()
async def join(ctx):
    """Join the channel"""
    if not ctx.author.voice:
        await ctx.send("You join the voice channel first, then call me, OK?")
        return
    if ctx.voice_client and ctx.voice_client.is_connected():
        await ctx.send(f"The robot has connected to the channel:{ctx.voice_client.channel.name}")
    else:
        channel = ctx.author.voice.channel
        await channel.connect()
        await ctx.send("The Khala connects us!")

@bot.hybrid_command()
async def leave(ctx):
    """Leave the channel"""
    if ctx.voice_client:
        if ctx.voice_client and ctx.voice_client.is_playing():
            ctx.voice_client.pause()
        await ctx.voice_client.disconnect()
        await ctx.send("Got it!")
    else:
        await ctx.send("Oops, your mistake! You haven’t joined yet, so no need to leave.")

@bot.hybrid_command()
async def reset_playlist(ctx):
    """Reset the playlist"""
    global playlist, playdic, current_play, listnum
    playlist = []
    playdic = {}
    current_play = -1
    listnum = 0
    ctx.voice_client.pause()
    await ctx.invoke(show_playlist)

@bot.hybrid_command()
async def show_playlist(ctx):
    """Show the playlist."""
    message = "Current playlist: \n"
    i = 0
    for key, value in playdic.items():
        message += '--------------------------------\n'
        message += f"Song {i+1}: {key}; {value}\n"
        i += 1
    message += '===============================\n'
    message += f"The total number of songs is {listnum}\n"
    if listnum > 0:
        message += '===============================\n'
        message += f"The current song is the {current_play+1} one : {playlist[current_play]}; {playdic[playlist[current_play]]}\n"
    message += '===============================\n'
    await ctx.send(message)

@bot.hybrid_command()
async def random_loop(ctx):
    """Shuffle the music in the playlist"""
    global random_flag, sequential_flag, self_flag, single_flag
    random_flag = 1
    sequential_flag = 0
    self_flag = 0
    single_flag = 0
    await ctx.send(f"Set to shuffle play")

@bot.hybrid_command()
async def sequential_loop(ctx):
    """Play the music in the playlist sequentially"""
    global random_flag, sequential_flag, self_flag, single_flag
    random_flag = 0
    sequential_flag = 1
    self_flag = 0
    single_flag = 0
    await ctx.send(f"Set to playlist mode")

@bot.hybrid_command()
async def self_loop(ctx):
    """Repeat the single track"""
    global random_flag, sequential_flag, self_flag, single_flag
    random_flag = 0
    sequential_flag = 0
    self_flag = 1
    single_flag = 0
    await ctx.send(f"Set to single track loop")

@bot.hybrid_command()
async def single_play(ctx):
    """Play a single track"""
    global random_flag, sequential_flag, self_flag, single_flag
    random_flag = 0
    sequential_flag = 0
    self_flag = 0
    single_flag = 1
    await ctx.send(f"Set to single track playback")

@bot.hybrid_command()
async def play_num(ctx, *, num):
    """Which song in the playlist"""
    global current_play
    try:
        num = int(num)
    except Exception as e:
        await ctx.send(f"Please enter an Arabic numeral")
        return
    if not ctx.voice_client:
        await ctx.invoke(join)
    num -= 1
    if listnum == 0 or num >= listnum or num < 0:
        await ctx.send(f"There is no such song")
        return
    async with ctx.typing():
        title, flag = await play_music(ctx, url=playdic[playlist[num]])
        if flag:
            current_play = num

@bot.hybrid_command()
async def add_playlist(ctx, *, url):
    """Add the music to the playlist"""
    global playlist, playdic, listnum
    try:
        async with ctx.typing():
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=False))
        if 'entries' in data:
            # If it's a playlist, select the first video
            data = data['entries'][0]
        title = data.get('title', 'Unknown')
        if url in playdic.values():
            await ctx.send(f"The song is already in the playlist")
        else:
            listnum += 1
            playlist.append(title)
            playdic[playlist[listnum-1]] = url
            await ctx.send(f"Song added: {title}")
    except Exception as e:
        await ctx.send(f"It cannot be added: {e}")

@bot.hybrid_command()
async def delet(ctx, *, num):
    """Remove the music from the playlist"""
    global playlist, playdic, listnum, current_play
    try:
        num = int(num)
    except:
        await ctx.send("Please enter a number")
        return
    if 0 < num and num <= listnum:
        num -= 1
        if num == current_play:
            await pause(ctx)
            current_play = -1
        music = playdic.pop(playlist[num])
        del playlist[num]
        listnum -= 1
        await ctx.send(f"Deleted song {num+1}: {music}")
    else:
        await ctx.send("Please enter a valid number")

@bot.hybrid_command()
async def play_next(ctx):
    "Play the next song"
    global current_play
    former_cp = current_play
    if not ctx.voice_client:
        await ctx.invoke(join)
    if listnum == 0:
        return
    if random_flag:
        current_play = random.randint(0, listnum-1)
    elif sequential_flag:
        current_play = (current_play + 1) % listnum
    elif self_flag:
        current_play = current_play
    print(f'playlist[current_play]: {playlist[current_play]}')
    print(f'playdic[playlist[current_play]]: {playdic[playlist[current_play]]}')
    title, flag = await play_music(ctx, url=playdic[playlist[current_play]])
    if flag:
        current_play = former_cp

@bot.hybrid_command()
async def play(ctx, *, url):
    """Play the music and add it to the playlist, which will interrupt the current song"""
    global playlist, playdic, current_play, listnum
    if not ctx.voice_client:
        await ctx.invoke(join)
    title, flag = await play_music(ctx, url=url)
    if flag:
        if title in playdic.keys():
            current_play = playlist.index(title)
            await ctx.send(f"The song is already in the playlist")
        else:
            listnum += 1
            current_play = listnum - 1
            playlist.append(title)
            playdic[playlist[listnum-1]] = url

async def play_music(ctx, *, url):
    """Play the music"""
    if not ctx.voice_client:
        await ctx.invoke(join)
    try:
        try:
            async with ctx.typing():
                loop = asyncio.get_event_loop()
                data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=False))
        except:
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=False))
        if 'entries' in data:
            # If it's a playlist, select the first video
            data = data['entries'][0]
        song = data['url']
        title = data.get('title', 'Unknown')
        player = discord.FFmpegPCMAudio(song, **ffmpeg_options)
        if ctx.voice_client.is_playing():
            ctx.voice_client.pause()
        await ctx.send(f'Now playing: {title} ({url})')
        print(f'title: {title}')
        print(f'url: {url}')
        if single_flag:
            ctx.voice_client.play(player)
        else:
            ctx.voice_client.play(player, after=lambda e: loop.create_task(play_next(ctx)))
        return title, True
    except Exception as e:
        await ctx.send(f"It cannot be played: {e}")
        return None, False

@bot.hybrid_command()
async def pause(ctx):
    """Pause the playback"""
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.pause()
        await ctx.send("The music has been paused")
    else:
        await ctx.send("There is no music currently playing")

@bot.hybrid_command()
async def resume(ctx):
    """Resume playback"""
    if ctx.voice_client and ctx.voice_client.is_paused():
        ctx.voice_client.resume()
        await ctx.send("The music has resumed playing")
    else:
        await ctx.send("There is no paused music")

@bot.hybrid_command()
async def volume(ctx, volume: int):
    """Set the volume"""
    if ctx.voice_client:
        ctx.voice_client.source.volume = volume / 100
        await ctx.send(f"The volume has been set to: {volume}%")
    else:
        await ctx.send("The robot is not playing anything")

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.response.send_message("The command is missing parameters, please enter it again")
    elif isinstance(error, commands.CommandInvokeError):
        await ctx.response.send_message("The command execution failed. Please check your input or try again later")
    else:
        await ctx.send(f"An error occurred: {error}")


bot.run(token)
