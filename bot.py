import os
from functools import reduce
import discord
from dotenv import load_dotenv
from discord.ext import commands
from datetime import datetime
from pytz import timezone, utc

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

bot = commands.Bot(command_prefix='pin ')

@bot.event
async def on_ready():
    print(f'Bot {bot.user} has connected to Discord!')


PIN_CHANNEL_PREFIX = 'pins'

@bot.group()
async def transfer(ctx):
	if ctx.invoked_subcommand is None:
		pass
	pass
	
@bot.group()
async def untransfer(ctx):
	if ctx.invoked_subcommand is None:
		pass
	pass

@transfer.command()
async def all(ctx):
	guild = ctx.guild
	channel = ctx.channel
	native_pins = await channel.pins()
	count = 0
	for message in native_pins:
		success = await pin_to_category(guild, message)
		count += int(success)

	pins_channel = await safe_create_channel(guild, None, 1)
	await ctx.send(f'Transfered {count} native pins in {channel.name} to {pins_channel.name}')


@untransfer.command()
async def all(ctx):
	guild = ctx.guild
	channel = ctx.channel
	
	count = 0
	native_pins = await channel.pins()
	for message in native_pins:
		pins_channel = await safe_create_channel(guild, None, 1)
		matched_pin = await find_pin(pins_channel, message)
		print(message, matched_pin)
		if matched_pin:
			await matched_pin.delete()
			count += 1
	await ctx.send(f'Untransfered {count} native pins in {channel.name} from {pins_channel.name}')

async def pin_to_category(guild, message, category_name=''):
	# category = await safe_create_category(guild, category_name)
	category = discord.utils.get(guild.categories, name=category_name)
	# category = None

	async def pin_to_channel(index):
		channel = await safe_create_channel(guild, category, index)
		# await message.pin()

		# dont pin if message is already pinned to this channel (determine by hash on date?)
		description = create_description(message)
		matched_pin = await find_pin(channel, message)

		if matched_pin:
			print('matched pin ', matched_pin)
			return False
		
		attachments = reduce(lambda urls, attachment: f'{urls}\n{attachment.url}', message.attachments, '')
		author_tag = f'<@{message.author.id}>'
		author_profile = f'https://discordapp.com/users/{message.author.id}'
		pfp = message.author.avatar_url
		# https://leovoel.github.io/embed-visualizer/
		# https://stackoverflow.com/questions/51423859/get-profile-picture-from-set-user
		# https://www.programcreek.com/python/example/107400/discord.Embed
		embed = discord.Embed(title=message.content, description=description, color=0x00ff00)
		embed.set_author(name=message.author, icon_url=pfp)
		for url in attachments.split():
			embed.set_image(url=url)
		await channel.send(embed=embed)
		return True

	return await pin_to_channel(1)

async def safe_create_category(guild, category_name):
	print(guild, guild.categories)
	category = discord.utils.get(guild.categories, name=category_name)
	if not category:
		print(f'Creating a new category: {category_name}')
		category = await guild.create_category(category_name)
	return category

async def safe_create_channel(guild, category, index):
	channel_name = f'{PIN_CHANNEL_PREFIX}-{index}'
	if category is None:
		# search all channels
		channel = discord.utils.get(guild.channels, name=channel_name)
		if not channel:
			print(f'Creating a new channel: {channel_name}')
			channel = await guild.create_text_channel(channel_name)
	else:
		# only search channels within the given category
		channel = discord.utils.get(category.channels, name=channel_name)
		if not channel:
			print(f'Creating a new channel: {channel_name}')
			channel = await guild.create_text_channel(channel_name, category=category)
	return channel


# https://gist.github.com/yhay81/31d1402e29d4f635d1c878909b30f82a
@bot.event
async def on_raw_reaction_add(payload):
	guild = bot.get_guild(payload.guild_id)
	channel = discord.utils.get(bot.get_all_channels(), id=payload.channel_id)
	message = await channel.fetch_message(payload.message_id)
	if str(payload.emoji) == "📌":
		await pin_to_category(guild, message)

@bot.event
async def on_raw_reaction_remove(payload):
	guild = bot.get_guild(payload.guild_id)
	channel = discord.utils.get(bot.get_all_channels(), id=payload.channel_id)
	message = await channel.fetch_message(payload.message_id)
	if str(payload.emoji) == "📌":
		channel = await safe_create_channel(guild, None, 1)
		if channel:
			matched_pin = await find_pin(channel, message)
			if matched_pin:
				await matched_pin.delete()

def get_message_link(message):
	return f'https://discord.com/channels/{message.guild.id}/{message.channel.id}/{message.id}'

def create_description(message):
	message_link = get_message_link(message)
	timestamp = message.created_at.replace(tzinfo=utc)
	# date = datetime.now(tz=utc)
	target_tz = timezone('US/Pacific')
	
	timestamp = timestamp.astimezone(target_tz)
	formatted_time = timestamp.strftime('On %b %d %Y at %I:%M %p')

	description = '\n'.join([
		formatted_time,
		f'[Jump]({message_link})'
	])
	return description

async def find_pin(channel, message):

	history = await channel.history().flatten()
	description = create_description(message)

	def match_message(x):
		embeds = x.embeds
		for embed in embeds:
			if embed.description == description:
				return True
		return False

	matched_pin = discord.utils.find(match_message, history)
	return matched_pin

# https://stackoverflow.com/questions/52241051/i-want-to-let-my-discord-bot-send-images-gifs
# good example bot: https://github.com/HaiderZaidiDev/Discord-Pin-Archiver-Bot/blob/public-release-dev/main.py

bot.run(TOKEN)

