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
    
    # Automated login
    try:
        # Wait for email field and login
        email_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, "email"))
        )
        email_field.send_keys(DISCORD_EMAIL)
        
        # Find and fill password
        password_field = driver.find_element(By.NAME, "password")
        password_field.send_keys(DISCORD_PASSWORD)
        password_field.send_keys(Keys.RETURN)
        
        print("Automated login completed")
        time.sleep(5)  # Wait for login to complete
    except Exception as e:
        print(f"Login error: {e}")
        print("Please log in manually")
        input("Press Enter after logging in...")

@bot.event
async def on_ready():
    print(f'Bot is logged in as {bot.user}')
    setup_selenium()
    print("Setup complete - bot is ready!")

@bot.event
async def on_message(message):
    # Ignore messages from the bot itself
    if message.author == bot.user:
        return

    # Only process DM messages
    if isinstance(message.channel, discord.DMChannel):
        print(f"DM received: {message.content}")
        if message.content.startswith('imagine '):
            prompt = message.content[8:]  # Remove 'imagine ' from the start
            try:
                # Navigate to DM
                dm_url = "https://discord.com/channels/@me/1122240897984245850"
                print(f"Processing prompt: {prompt}")
                driver.get(dm_url)
                time.sleep(5)
                
                # Find and click message box
                message_box = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, 'div[role="textbox"]'))
                )
                message_box.click()
                time.sleep(1)
                
                # Send command - modified to just send the prompt
                message_box.send_keys("/imagine")
                time.sleep(1)
                message_box.send_keys(Keys.TAB)
                message_box.send_keys(prompt)  # Just send the prompt without "prompt:"
                time.sleep(1)
                message_box.send_keys(Keys.ENTER)
                
                print("Command sent successfully")
                await message.channel.send(f"Sent to Midjourney: {prompt}")
                
            except Exception as e:
                print(f"Error: {str(e)}")
                await message.channel.send(f"Error sending prompt: {str(e)}")


bot.run(DISCORD_BOT_TOKEN)