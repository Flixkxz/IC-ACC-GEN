import discord
from discord.ext import commands
from discord import option
import random
import os
import datetime

# Import the generator class from your other file
from generator import InstacartGenerator

# --- CONFIGURATION ---
# It's better to load these from a secure file or environment variables
# For now, put your bot token here.
BOT_TOKEN = "MTM4NDI2MTQ4MzQ3ODc4MjAyMg.GVB4JW.Tqi2R6azVMhMHHNgRPMtrydoVj7I0boRF8zwEc"


if os.path.exists("proxies.txt"):
    with open("proxies.txt", "r") as f:
        proxies = [line.strip() for line in f if line.strip()]
else:
    proxies = []

WORD_LIST = [
    'sky', 'blue', 'cat', 'dog', 'sun', 'moon', 'star', 'leaf', 'tree', 'rock',
    'river', 'lake', 'fire', 'ice', 'wind', 'rain', 'snow', 'bird', 'fish', 'wolf'
]

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    print('Ready to generate.')
    print('-------------------')

@bot.slash_command(
    name="generate",
    description="Generates a verified Instacart account using a catchall domain."
)
# IMAP server option is now removed
@option("catchall_domain", description="Your catchall domain (e.g., @example.com)", required=True)
@option("password", description="The password for the new account.", required=True)
@option("imap_user", description="Your Gmail login for IMAP.", required=True)
@option("imap_password", description="Your Gmail APP password for IMAP.", required=True)
async def generate(
    ctx: discord.ApplicationContext,
    catchall_domain: str,
    password: str,
    imap_user: str,
    imap_password: str
):
    await ctx.defer(ephemeral=True)
    proxy = random.choice(proxies) if proxies else None
    
    embed = discord.Embed(
        title="Instacart Account Generation",
        description="Starting the process...",
        color=discord.Color.orange()
    )
    
    random_words = "".join(random.choices(WORD_LIST, k=3))
    now = datetime.datetime.now()
    date_str = f"{now.month}{now.day:02d}{now.year}"
    clean_domain = catchall_domain.lstrip('@')
    generated_email = f"{random_words}{date_str}@{clean_domain}"

    embed.add_field(name="Generated Email", value=generated_email, inline=False)
    await ctx.respond(embed=embed, ephemeral=True)

    try:
        # IMAP server is now hard-coded here
        imap_details = {
            "server": "imap.gmail.com",
            "user": imap_user,
            "pass": imap_password
        }

        generator = InstacartGenerator(proxy)
        result = await generator.run(generated_email, password, imap_details)

        if "SUCCESS" in result:
            embed.description = "Account generation successful!"
            embed.color = discord.Color.green()
            embed.add_field(name="Credentials", value=f"```{generated_email}:{password}```", inline=False)
        else:
            embed.description = "Account generation failed."
            embed.color = discord.Color.red()
            embed.add_field(name="Error", value=f"```{result}```", inline=False)

        await ctx.edit(embed=embed)
    except Exception as e:
        error_embed = discord.Embed(
            title="A Critical Error Occurred",
            description=f"The bot ran into an unhandled exception.\n```py\n{e}\n```",
            color=discord.Color.dark_red()
        )
        await ctx.edit(embed=error_embed)

bot.run(BOT_TOKEN)