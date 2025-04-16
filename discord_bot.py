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
    'extractaudio': True,  # 强制只提取音频
    'audioquality': 1,  # 高音质
    'prefer_ffmpeg': True,  # 使用 ffmpeg 提取音频
    'keepvideo': False,  # 不保存视频
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
    """加入频道"""
    if not ctx.author.voice:
        await ctx.send("你先加语音再叫我OK?")
        return
    if ctx.voice_client and ctx.voice_client.is_connected():
        await ctx.send(f"机器人已连接到频道：{ctx.voice_client.channel.name}")
    else:
        channel = ctx.author.voice.channel
        await channel.connect()
        await ctx.send("圣神的卡拉连接着我们！")

@bot.hybrid_command()
async def leave(ctx):
    """退出频道"""
    if ctx.voice_client:
        if ctx.voice_client and ctx.voice_client.is_playing():
            ctx.voice_client.pause()
        await ctx.voice_client.disconnect()
        await ctx.send("收到！")
    else:
        await ctx.send("我还没进来呢你叫我走？")

@bot.hybrid_command()
async def reset_playlist(ctx):
    """重置播放列表"""
    global playlist, playdic, current_play, listnum
    playlist = []
    playdic = {}
    current_play = -1
    listnum = 0
    ctx.voice_client.pause()
    await ctx.invoke(show_playlist)

@bot.hybrid_command()
async def show_playlist(ctx):
    """展示播放列表"""
    message = "当前播放列表: \n"
    i = 0
    for key, value in playdic.items():
        message += '--------------------------------\n'
        message += f"第{i+1}首歌: {key}; {value}\n"
        i += 1
    message += '===============================\n'
    message += f"歌曲总数为{listnum}\n"
    if listnum > 0:
        message += '===============================\n'
        message += f"当前歌曲为第{current_play+1}首：{playlist[current_play]}; {playdic[playlist[current_play]]}\n"
    message += '===============================\n'
    await ctx.send(message)

@bot.hybrid_command()
async def random_loop(ctx):
    """随机播放列表中音乐"""
    global random_flag, sequential_flag, self_flag, single_flag
    random_flag = 1
    sequential_flag = 0
    self_flag = 0
    single_flag = 0
    await ctx.send(f"已设置为随机播放")

@bot.hybrid_command()
async def sequential_loop(ctx):
    """顺序播放列表中音乐"""
    global random_flag, sequential_flag, self_flag, single_flag
    random_flag = 0
    sequential_flag = 1
    self_flag = 0
    single_flag = 0
    await ctx.send(f"已设置为列表播放")

@bot.hybrid_command()
async def self_loop(ctx):
    """单曲循环"""
    global random_flag, sequential_flag, self_flag, single_flag
    random_flag = 0
    sequential_flag = 0
    self_flag = 1
    single_flag = 0
    await ctx.send(f"已设置为单曲循环")

@bot.hybrid_command()
async def single_play(ctx):
    """单曲播放"""
    global random_flag, sequential_flag, self_flag, single_flag
    random_flag = 0
    sequential_flag = 0
    self_flag = 0
    single_flag = 1
    await ctx.send(f"已设置为列表播放")

@bot.hybrid_command()
async def play_num(ctx, *, num):
    """播放列表中第几个音乐"""
    global current_play
    try:
        num = int(num)
    except Exception as e:
        await ctx.send(f"请输入阿拉伯数字")
        return
    if not ctx.voice_client:
        await ctx.invoke(join)
    num -= 1
    if listnum == 0 or num >= listnum or num < 0:
        await ctx.send(f"就没这歌")
        return
    async with ctx.typing():
        title, flag = await play_music(ctx, url=playdic[playlist[num]])
        if flag:
            current_play = num

@bot.hybrid_command()
async def add_playlist(ctx, *, url):
    """将音乐加入歌单"""
    global playlist, playdic, listnum
    try:
        async with ctx.typing():
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=False))
        if 'entries' in data:
            # 如果是播放列表，选择第一个视频
            data = data['entries'][0]
        title = data.get('title', 'Unknown')
        if url in playdic.values():
            await ctx.send(f"歌曲已在歌单中")
        else:
            listnum += 1
            playlist.append(title)
            playdic[playlist[listnum-1]] = url
            await ctx.send(f"已添加歌曲：{title}")
    except Exception as e:
        await ctx.send(f"并非可以添加：{e}")

@bot.hybrid_command()
async def delet(ctx, *, num):
    """将音乐从歌单删除"""
    global playlist, playdic, listnum, current_play
    try:
        num = int(num)
    except:
        await ctx.send("请输入数字")
        return
    if 0 < num and num <= listnum:
        num -= 1
        if num == current_play:
            await pause(ctx)
            current_play = -1
        music = playdic.pop(playlist[num])
        del playlist[num]
        listnum -= 1
        await ctx.send(f"已删除第 {num+1} 首歌: {music}")
    else:
        await ctx.send("请输入有效数字")

@bot.hybrid_command()
async def play_next(ctx):
    "播放下个音乐"
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
    """播放音乐并且将其加入歌单，会中断当前歌曲"""
    global playlist, playdic, current_play, listnum
    if not ctx.voice_client:
        await ctx.invoke(join)
    title, flag = await play_music(ctx, url=url)
    if flag:
        if title in playdic.keys():
            current_play = playlist.index(title)
            await ctx.send(f"歌曲已在歌单中")
        else:
            listnum += 1
            current_play = listnum - 1
            playlist.append(title)
            playdic[playlist[listnum-1]] = url

async def play_music(ctx, *, url, seek_time=0):
    """播放音乐"""
    global current_seek_time
    if not ctx.voice_client:
        await ctx.invoke(join)
    try:
        async with ctx.typing():
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=False))

        if 'entries' in data:
            data = data['entries'][0]

        song = data['url']
        title = data.get('title', 'Unknown')
        duration = data.get('duration', 0)

        if seek_time >= duration:
            await ctx.send(f" 这歌有这么长吗？嗯？说话？")
            return None, False

        ffmpeg_opts = {
            'before_options': f'-ss {seek_time}',
            'options': '-vn'
        }
        player = discord.FFmpegPCMAudio(song, **ffmpeg_opts)

        if ctx.voice_client.is_playing():
            ctx.voice_client.pause()

        await ctx.send(f' 正在播放：{title} ')

        if single_flag:
            ctx.voice_client.play(player)
        else:
            ctx.voice_client.play(player, after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop))

        current_seek_time = seek_time

        return title, True

    except Exception as e:
        await ctx.send(f"播放失败：{e}")
        return None, False

@bot.hybrid_command()
async def pause(ctx):
    """暂停播放"""
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.pause()
        await ctx.send("音乐已暂停。")
    else:
        await ctx.send("没有正在播放的音乐。")

@bot.hybrid_command()
async def resume(ctx):
    """继续播放"""
    if ctx.voice_client and ctx.voice_client.is_paused():
        ctx.voice_client.resume()
        await ctx.send("音乐已恢复播放。")
    else:
        await ctx.send("没有暂停的音乐。")

@bot.hybrid_command()
async def volume(ctx, volume: int):
    """设置音量"""
    if ctx.voice_client:
        ctx.voice_client.source.volume = volume / 100
        await ctx.send(f"音量已设置为：{volume}%")
    else:
        await ctx.send("机器人未在播放任何内容")

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.response.send_message("命令缺少参数，请重新输入")
    elif isinstance(error, commands.CommandInvokeError):
        await ctx.response.send_message("命令执行错误，请检查输入或稍后重试")
    else:
        await ctx.send(f"出现错误：{error}")

@bot.hybrid_command()
async def seek(ctx, seconds: int):
    """快进到指定秒数"""
    global current_play
    if listnum == 0 or current_play == -1:
        await ctx.send("还没开始放歌你快进nm")
        return
    title = playlist[current_play]
    url = playdic[title]
    await play_music(ctx, url=url, seek_time=seconds)
    await ctx.send(f"快进到{seconds}秒好了喵！")

@bot.hybrid_command()
async def forward(ctx, seconds: int):
    """快进指定秒数"""
    global current_play, current_seek_time
    if listnum == 0 or current_play == -1:
        await ctx.send("没播放你快进nm")
        return
    if seconds < 0:
        await ctx.send("秒数不能是负的")
        return
    title = playlist[current_play]
    url = playdic[title]
    new_seek = current_seek_time + seconds
    await ctx.send(f"快进 {seconds} 秒了喵")
    await play_music(ctx, url=url, seek_time=new_seek)

@bot.hybrid_command()
async def backward(ctx, seconds: int):
    """快退指定秒数"""
    global current_play, current_seek_time
    if listnum == 0 or current_play == -1:
        await ctx.send("没播放你倒放nm")
        return
    if seconds < 0:
        await ctx.send("秒数不能是负的")
        return
    title = playlist[current_play]
    url = playdic[title]
    new_seek = max(0, current_seek_time - seconds)
    await ctx.send(f"倒退 {seconds} 秒了喵")
    await play_music(ctx, url=url, seek_time=new_seek)

bot.run(token)
