import os
from datetime import datetime, timedelta
import disnake
import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.schedulers.base import STATE_STOPPED
from elevenlabs import save
from dota import team_announce
from dota.dataHandler import DataHandler


class Dota2View(disnake.ui.View):
    def __init__(self, user_id, loop, ctx, bot):
        super().__init__(timeout=18000)
        self.bot = bot
        self.ctx = ctx
        self.loop = loop
        self.message = None
        self.data = DataHandler()
        self.user_id = user_id
        self.scheduler = BackgroundScheduler()
        self.buttons = None

        if self.scheduler.state == STATE_STOPPED:
            self.scheduler.start()

    def create_buttons(self):
        if self.buttons is None:
            self.buttons = {}

        for timeslot in self.data.get_timeslots():
            if timeslot in self.buttons:
                self.remove_item(self.buttons[timeslot])
            split_time = timeslot.split("h")
            timeslot_str = f"{split_time[0]}h"
            if split_time[1] != "00":
                timeslot_str += f"{split_time[1]}"
            button = TimeSlotButton(label=timeslot_str, time=timeslot_str)
            self.add_item(button)
            self.buttons[timeslot] = button

    async def new(self):
        self.create_buttons()
        embed = self.create_embed()

        try:
            role_id = int(os.getenv("ROLE_ID"))
        except:
            role_id = 0

        role = self.ctx.guild.get_role(role_id)
        if role:
            await self.ctx.send(f'{role.mention}!')
        else:
            print("role not found")

        self.message = await self.ctx.send(view=self, embed=embed)

        await self.wait()
        await self.disable_all_items()

    def create_embed(self):
        embed = disnake.Embed(title="Xinela Ready Checker", description="Escolha a hora do show!")

        embed.set_thumbnail(
            url="https://cdn.discordapp.com/app-icons/1103071608005984360/a5ee3bf0eb26fd1629a99771d37c2780.png?size=256")

        for timeslot in self.data.get_timeslots():
            if self.data.dict['times'].get(timeslot):
                split_time = timeslot.split("h")
                timeslot_str = f"{split_time[0]}h"
                if split_time[1] != "00":
                    timeslot_str += f"{split_time[1]}"
                unix_timestamp = self.data.time_to_unix_timestamp(timeslot)
                embed.add_field(inline=False, name=f"{timeslot_str} - <t:{unix_timestamp}:t>",
                                value=self.data.get_users_at_time(timeslot))

            button = self.buttons.get(timeslot)
            if button is not None:
                button.update_state(timeslot, self.data.get_users_list_at_time(timeslot))

        return embed

    async def disable_all_items(self):
        for item in self.children:
            item.disabled = True
        await self.message.edit(view=self)

    async def update_message(self):
        embed = self.create_embed()
        await self.message.edit(view=self, embed=embed)

    async def on_timeout(self) -> None:
        await self.disable_all_items()

    async def add_timeslot(self, timeslot):
        timeslot_formatted = self.format_time(timeslot)
        self.data.dict['times'][timeslot_formatted] = []
        self.data.save_to_json()
        self.create_buttons()
        await self.update_message()

    def format_time(self, time_str):
        split_time = time_str.split("h")
        hour = int(split_time[0]) if split_time[0] else 0
        minute = int(split_time[1]) if len(split_time) > 1 and split_time[1] else 0
        time_formatted = f"{hour:02d}h{minute:02d}"
        return time_formatted

    async def on_button(self, interaction, time_str):
        time_formatted = self.format_time(time_str)
        count = self.data.add(time_formatted, interaction.user.id)
        job_id = f'reminder_{time_formatted}'
        existing_jobs = [job for job in self.data.dict['jobs'] if job['job_id'] == job_id]

        for job in existing_jobs:
            if self.scheduler.get_job(job['job_id']):
                self.scheduler.remove_job(job['job_id'])
                self.data.remove_job(job['job_id'])

        if count >= 5:
            split_time = time_str.split("h")
            hour = int(split_time[0])
            minute = int(split_time[1]) if len(split_time) > 1 and split_time[1] else 0
            run_date = datetime.now(pytz.timezone('America/Sao_Paulo'))
            run_date = run_date.replace(hour=hour - 1, minute=minute, second=0, microsecond=0)

            if run_date < datetime.now(pytz.timezone('America/Sao_Paulo')):
                run_date += timedelta(days=1)

            self.scheduler.add_job(self.sync_send_reminder, 'date', run_date=run_date, args=[time_formatted], id=job_id)
            self.data.add_job(run_date, interaction.channel.id, interaction.user.id, job_id)

        await interaction.response.edit_message(view=self, embed=self.create_embed())

    def sync_send_reminder(self, selected_time):
        self.loop.create_task(self.send_reminder(selected_time))

    async def send_reminder(self, selected_time):
        member_ids = self.data.get_users_list_at_time(selected_time)
        if len(member_ids) < 5:
            naodeu_frase = self.bot.content.get_random("naodeu_frases")
            naodeu_imagens = self.bot.content.get_random("naodeu_imagens")
            await self.ctx.send(f"{naodeu_frase}")
            await self.ctx.send(f"{naodeu_imagens}")

            return

        unix_timestamp = self.data.time_to_unix_timestamp(selected_time)

        await team_announce.create_team_photo(self.ctx, self.bot.content.get("anuncio"), member_ids)

        ids_str = ' '.join([f'<@{mid}>' for mid in member_ids])
        await self.ctx.send(f"Eis os escolhidos das <t:{unix_timestamp}:t>! <t:{unix_timestamp}:R>! \n {ids_str}")
        await self.ctx.send(file=disnake.File("group_photo.gif"))

        frase = self.bot.content.get_random("frases")
        imagem = self.bot.content.get_random("imagens")
        await self.ctx.send(frase)
        await self.ctx.send(imagem)

        save("content", self.bot.content)

    async def remove(self):
        await self.message.delete()

class TimeSlotButton(disnake.ui.Button):
    def __init__(self, time, label, **kwargs):
        super().__init__(label=label, **kwargs)
        self.time = time

    async def callback(self, interaction: disnake.MessageInteraction):
        await self.view.on_button(interaction, self.time)

    def update_state(self, timeslot, users):
        def get_button_style(time):
            if len(users) >= 4:
                return disnake.ButtonStyle.green
            else:
                return disnake.ButtonStyle.gray

        self.style = get_button_style(timeslot)

        if len(users) == 4:
            self.emoji = "<:eyes_freaking:906257799711973497>"
        elif len(users) >= 5:
            self.emoji = "<a:pugdance:924016472941023312>"
        else:
            self.emoji = None

