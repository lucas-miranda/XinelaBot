import asyncio
import random
import discord
from discord.ext import commands
from elevenlabs import generate, save
from elevenlabs import set_api_key
import utils.env as env
from dota.dota2View import Dota2View
from dota import team_announce

set_api_key(env.ELEVENLABS_API)


def async_to_sync(async_func):
    def wrapper(*args, **kwargs):
        return asyncio.create_task(async_func(*args, **kwargs))

    return wrapper


class Poll(commands.Cog):
    def __init__(self, xinelabot):
        self._bot = xinelabot
        self.view = None

    @commands.command()
    async def readycheck(self, ctx: commands.Context):
        self.view = Dota2View(user_id=ctx.author.id, loop=self._bot.loop, ctx=ctx, bot=self._bot)
        await self.view.new()

    @commands.command()
    async def anunciar(self, ctx):
        if self.view is None:
            print("[Anunciar] View is none")
            return

        voted_time, unix_timestamp = self.view.data.most_votes()
        member_ids = self.view.data.get_users_list_at_time(voted_time)
        #  member_ids.extend([89437921286819840, 89437921286819840, 89437921286819840, 89437921286819840])

        await team_announce.create_team_photo(ctx, self._bot.content.get("anuncio"), member_ids)

        ids_str = ' '.join([f'<@{mid}>' for mid in member_ids])
        await ctx.send(f"<t:{unix_timestamp}:R>! Eis os escolhidos de hoje!\n {ids_str}")
        await ctx.send(file=discord.File("group_photo.gif"))

        frase = self._bot.content.get_random("abertura_frases")
        audio = generate(
            text=frase.replace("*", ""),
            voice=random.choice(["RpvoK8WoHsA3IVJ5sZRq"]),
            model="eleven_multilingual_v1"
        )

        save(audio, "frase_do_dia.wav")
        with open("frase_do_dia.wav", "rb") as f:
            await ctx.send(file=discord.File(f, "frase_do_dia.wav"))

    @commands.command()
    async def reset(self, ctx: commands.Context):
        view = Dota2View(user_id=ctx.author.id, loop=self._bot.loop, ctx=ctx, bot=self._bot)
        view.data.reset()
        view.scheduler.remove_all_jobs()


async def setup(bot):
    await bot.add_cog(Poll(bot))
