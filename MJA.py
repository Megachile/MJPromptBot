import discord
from discord.ext import commands
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from dotenv import load_dotenv
import os
import time

# Load environment variables
load_dotenv()
DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
DISCORD_EMAIL = os.getenv('DISCORD_EMAIL')
DISCORD_PASSWORD = os.getenv('DISCORD_PASSWORD')

# Read profile IDs
def load_profiles():
    try:
        with open('profiles.txt', 'r') as file:
            # Remove any empty lines or whitespace
            profiles = [line.strip() for line in file.readlines() if line.strip()]
        print(f"Loaded {len(profiles)} profiles")
        return profiles
    except FileNotFoundError:
        print("Warning: profiles.txt not found!")
        return []

PROFILES = load_profiles()

# Set up intents
intents = discord.Intents.default()
intents.message_content = True
intents.dm_messages = True

bot = commands.Bot(command_prefix='!', intents=intents)
driver = None

def setup_selenium():
    global driver
    print("Setting up Chrome...")
    chrome_options = Options()
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.get("https://discord.com/login")
    
    try:
        email_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, "email"))
        )
        email_field.send_keys(DISCORD_EMAIL)
        
        password_field = driver.find_element(By.NAME, "password")
        password_field.send_keys(DISCORD_PASSWORD)
        password_field.send_keys(Keys.RETURN)
        
        print("Automated login completed")
        time.sleep(5)
    except Exception as e:
        print(f"Login error: {e}")
        print("Please log in manually")
        input("Press Enter after logging in...")

@bot.event
async def on_ready():
    print(f'Bot is logged in as {bot.user}')
    setup_selenium()
    print("Setup complete - bot is ready!")
    print(f"Loaded profiles: {PROFILES}")

async def send_prompt_with_profile(message, base_prompt, profile_id):
    try:
        dm_url = "https://discord.com/channels/@me/1122240897984245850"
        driver.get(dm_url)
        time.sleep(5)
        
        message_box = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 'div[role="textbox"]'))
        )
        message_box.click()
        time.sleep(1)
        
        # Construct full prompt with profile
        full_prompt = f"{base_prompt} --c 15 --profile {profile_id}"
        
        message_box.send_keys("/imagine")
        time.sleep(1)
        message_box.send_keys(Keys.TAB)
        message_box.send_keys(full_prompt)
        time.sleep(1)
        message_box.send_keys(Keys.ENTER)
        
        print(f"Sent prompt with profile {profile_id}")
        await message.channel.send(f"Sent: {full_prompt}")
        
        # Wait between prompts to avoid rate limiting
        time.sleep(3)
        
    except Exception as e:
        print(f"Error with profile {profile_id}: {str(e)}")
        await message.channel.send(f"Error with profile {profile_id}: {str(e)}")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if isinstance(message.channel, discord.DMChannel):
        if message.content.startswith('imagine '):
            base_prompt = message.content[8:].strip()
            
            if not PROFILES:
                await message.channel.send("No profiles loaded! Check profiles.txt")
                return
                
            await message.channel.send(f"Processing prompt: {base_prompt}\nUsing {len(PROFILES)} profiles...")
            
            for profile_id in PROFILES:
                await send_prompt_with_profile(message, base_prompt, profile_id)
            
            await message.channel.send("Completed all profiles!")
        
        elif message.content == 'profiles':
            if PROFILES:
                profile_list = '\n'.join(PROFILES)
                await message.channel.send(f"Loaded profiles:\n{profile_list}")
            else:
                await message.channel.send("No profiles loaded!")

bot.run(DISCORD_BOT_TOKEN)