import os
import time
import json
import asyncio
import discord
from discord.ext import commands
from dotenv import load_dotenv

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    ElementClickInterceptedException,
    TimeoutException,
)

# === CONFIG ===
DEFAULT_PROFILE_ID = "m7273221328335798284"
RELAX_MODE_DELAY = 20

# === LOAD SECRETS ===
load_dotenv()
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
DISCORD_EMAIL     = os.getenv("DISCORD_EMAIL")
DISCORD_PASSWORD  = os.getenv("DISCORD_PASSWORD")

# === LOAD PROFILES ===
def load_profiles():
    try:
        with open("profiles.txt") as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print("Warning: profiles.txt not found!")
        return []

PROFILES = load_profiles()

# === LOAD MOODBOARD DICTIONARY ===
def load_moodboards():
    try:
        with open("moodboards.json") as f:
            return json.load(f)
    except FileNotFoundError:
        print("Warning: moodboards.json not found! Using empty dictionary.")
        return {}

MOODBOARD_NAME_TO_ID = load_moodboards()

def resolve_profile_id(name_or_id):
    return MOODBOARD_NAME_TO_ID.get(name_or_id.strip(), name_or_id.strip())

# === DISCORD BOT ===
intents = discord.Intents.default()
intents.message_content = True
intents.dm_messages     = True
bot = commands.Bot(command_prefix="!", intents=intents)

# === SELENIUM DRIVER ===
driver = None
queue  = asyncio.Queue()

def setup_selenium():
    global driver
    chrome_opts = Options()
    chrome_opts.add_argument("--disable-logging")
    chrome_opts.add_argument("--no-sandbox")
    chrome_opts.add_argument("--disable-dev-shm-usage")
    chrome_opts.add_argument("--disable-gpu")
    chrome_opts.binary_location = "/usr/bin/chromium-browser"

    # Define service with correct chromedriver path
    service = Service("/usr/lib/chromium-browser/chromedriver")
    driver = webdriver.Chrome(service=service, options=chrome_opts)

    # Open Discord login page and wait a bit for slow cloud load
    driver.get("https://discord.com/login")
    time.sleep(5)  # Give the page time to load

    # Now proceed with the normal login steps
    WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.NAME, "email"))
    ).send_keys(DISCORD_EMAIL)
    driver.find_element(By.NAME, "password").send_keys(DISCORD_PASSWORD, Keys.RETURN)

    WebDriverWait(driver, 30).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "div[aria-label='Direct Messages']"))
    )

    dm_url = "https://discord.com/channels/@me/1122240897984245850"
    driver.get(dm_url)
    WebDriverWait(driver, 20).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "div[role='textbox']"))
    )

def wait_for_overlay(timeout=15):
    try:
        WebDriverWait(driver, timeout).until_not(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-fade='true']"))
        )
    except TimeoutException:
        pass

def safe_click(el, timeout=10):
    deadline = time.time() + timeout
    driver.execute_script("arguments[0].scrollIntoView({block:'center'})", el)
    while time.time() < deadline:
        try:
            el.click()
            return
        except ElementClickInterceptedException:
            time.sleep(0.2)
    driver.execute_script("arguments[0].click()", el)

async def send_prompt_with_profile(base_prompt, profile_id, channel):
    dm_url = "https://discord.com/channels/@me/1122240897984245850"
    driver.get(dm_url)
    await asyncio.sleep(2)
    wait_for_overlay()

    try:
        box = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "div[role='textbox']"))
        )
    except TimeoutException:
        await channel.send("⚠️ Couldn't find the message box—skipping this prompt.")
        return

    safe_click(box)
    await asyncio.sleep(0.2)

    full = f"{base_prompt} --style raw --chaos 15 --profile {profile_id}"
    for chunk in ["/imagine", Keys.TAB, full, Keys.ENTER]:
        wait_for_overlay()
        box.send_keys(chunk)
        await asyncio.sleep(0.2)

    await channel.send(f"✅ Sent to `{profile_id}`: {full}")
    print(f"🕒 Waiting {RELAX_MODE_DELAY}s before next")
    await asyncio.sleep(RELAX_MODE_DELAY)

async def process_queue():
    await bot.wait_until_ready()
    while True:
        prompt, channel, forced_profile = await queue.get()
        if forced_profile:
            await channel.send(f"🔄 Processing `{prompt}` with profile `{forced_profile}`…")
            await send_prompt_with_profile(prompt, forced_profile, channel)
        else:
            if not PROFILES:
                await channel.send("No profiles loaded; cannot process.")
            else:
                await channel.send(f"🔄 Processing `{prompt}` for {len(PROFILES)} profiles…")
                for pid in PROFILES:
                    await send_prompt_with_profile(prompt, pid, channel)
        await channel.send("🏁 Done!")
        queue.task_done()

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    setup_selenium()
    bot.loop.create_task(process_queue())
    print(f"Loaded profiles: {PROFILES}")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if isinstance(message.channel, discord.DMChannel):
        txt = message.content.strip()

        if txt.lower().startswith("imagine "):
            prompt = txt[len("imagine "):].strip()
            await message.channel.send(f"🗂 Queued: `{prompt}`")
            await queue.put((prompt, message.channel, None))

        elif txt.lower().startswith("batch "):
            block = txt[len("batch "):].strip()
            if "::" in block:
                moodboard, raw_prompts = block.split("::", 1)
                profile_override = resolve_profile_id(moodboard)
            else:
                raw_prompts = block
                profile_override = DEFAULT_PROFILE_ID

            prompts = [p.strip() for p in raw_prompts.split("|") if p.strip()]
            await message.channel.send(f"🧳 Queued {len(prompts)} prompts using profile `{profile_override}`.")
            for p in prompts:
                await queue.put((p, message.channel, profile_override))

        elif txt.lower() == "profiles":
            if PROFILES:
                await message.channel.send("Loaded profiles:\n" + "\n".join(PROFILES))
            else:
                await message.channel.send("No profiles loaded!")

bot.run(DISCORD_BOT_TOKEN)
