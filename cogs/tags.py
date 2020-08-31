import json

import discord
from discord.ext import commands

from ext.command import group
from ext.utils import apply_vars


class Tags(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @group(6, invoke_without_command=True)
    async def tag(self, ctx):
        """Configure tags in your server."""
        await ctx.invoke(self.bot.get_command('help'), command_or_cog='tag')

    @tag.command(6)
    async def create(self, ctx, name, *, value: commands.clean_content=None, aliases=['add', 'make', '+']):
        """Create tags for your server.

        Example: tag create hello Hi! I am the bot responding!
        Complex usage for variables: https://github.com/fourjr/rainbot/wiki/Tags
        """
        if value.startswith('http'):
            if value.startswith('https://hasteb.in') and 'raw' not in value:
                value = 'https://hasteb.in/raw/' + value[18:]

            async with self.bot.session.get(value) as resp:
                value = await resp.text()

        if name in [i.qualified_name for i in self.bot.commands]:
            await ctx.send('That name is already a pre-existing tag/command.')
        else:
            await self.bot.db.update_guild_config(ctx.guild.id, {'$push': {'tags': {'name': name, 'value': value}}})
            await ctx.send(self.bot.accept)

    @tag.command(6)
    async def remove(self, ctx, name, aliases=['delete', 'del', '-']):
        """Removes a tag from the server."""
        await self.bot.db.update_guild_config(ctx.guild.id, {'$pull': {'tags': {'name': name}}})

        await ctx.send(self.bot.accept)

    @tag.command(6, name='list')
    async def list_(self, ctx, aliases=['tags', 'dump', 'all']):
        """Lists all tags."""
        guild_config = await self.bot.db.get_guild_config(ctx.guild.id)
        tags = [i.name for i in guild_config.tags]

        if tags:
            await ctx.send('Tags: ' + ', '.join(tags))
        else:
            await ctx.send('No tags saved.')

    @commands.Cog.listener()
    async def on_message(self, message):
        if not message.author.bot and message.guild:
            ctx = await self.bot.get_context(message)
            guild_config = await self.bot.db.get_guild_config(ctx.guild.id)
            tags = [i.name for i in guild_config.tags]

            if ctx.invoked_with in tags:
                tag = guild_config.tags.get_kv('name', ctx.invoked_with)
                await ctx.send(**self.format_message(tag.value, message))

    def apply_vars_dict(self, tag, message):
        for k, v in tag.items():
            if isinstance(v, dict):
                tag[k] = self.apply_vars_dict(v, message)
            elif isinstance(v, str):
                tag[k] = apply_vars(self, v, message)
            elif isinstance(v, list):
                tag[k] = [self.apply_vars_dict(_v, message) for _v in v]
            if k == 'timestamp':
                tag[k] = v[:-1]
        return tag

    def format_message(self, tag, message):
        try:
            tag = json.loads(tag)
        except json.JSONDecodeError:
            # message is not embed
            tag = apply_vars(self, tag, message)
            tag = {'content': tag}
        else:
            # message is embed
            tag = self.apply_vars_dict(tag, message)

            if any(i in message for i in ('embed', 'content')):
                tag['embed'] = discord.Embed.from_dict(tag['embed'])
            else:
                tag = None
        return tag


def setup(bot):
    bot.add_cog(Tags(bot))
