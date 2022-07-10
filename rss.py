import os
import sys
import feedparser
from sql import db
from time import sleep, time
from dotenv import load_dotenv
from pyrogram import Client, filters
from pyrogram.errors import FloodWait
from apscheduler.schedulers.background import BackgroundScheduler


if os.path.exists("config.env"):
    load_dotenv("config.env")


try:
    api_id = int(os.environ.get("API_ID"))   # Get it from my.telegram.org
    api_hash = os.environ.get("API_HASH")   # Get it from my.telegram.org
    feed_urls = list(set(i for i in os.environ.get("FEED_URLS").split("|")))  # RSS Feed URL of the site.
    bot_token = os.environ.get("BOT_TOKEN")   # Get it by creating a bot on https://t.me/botfather
    log_channel = int(os.environ.get("LOG_CHANNEL"))   # Telegram Channel ID where the bot is added and have write permission. You can use group ID too.
    check_interval = int(os.environ.get("INTERVAL", 10))   # Check Interval in seconds.  
    max_instances = int(os.environ.get("MAX_INSTANCES", 3))   # Max parallel instance to be used.
except Exception as e:
    print(e)
    print("One or more variables missing. Exiting !")
    sys.exit(1)


for feed_url in feed_urls:
    if db.get_link(feed_url) == None:
        db.update_link(feed_url, "*")


app = Client(":memory:", api_id=api_id, api_hash=api_hash, bot_token=bot_token)

def humanbytes(size: int):
    if not size:
        return ""
    power = 2 ** 10
    raised_to_pow = 0
    dict_power_n = {0: "", 1: "Ki", 2: "Mi", 3: "Gi", 4: "Ti"}
    while size > power:
        size /= power
        raised_to_pow += 1
    return str(round(size, 2)) + " " + dict_power_n[raised_to_pow] + "B"

def create_feed_checker(feed_url):
    def check_feed():
        FEED = feedparser.parse(feed_url)
        entry = FEED.entries[0]
        if entry.id != db.get_link(feed_url).link:
            if "1337x" in entry.link:
                msg = f"<b>Title:</b> {entry.title}\n\n"
                msg += f"<b>Size:</b> {humanbytes(entry.size)}"
                msg += f" | <b>Torrent Site:</b> {entry.jackettindexer['id']}\n\n"
                if entry.link.startswith("magnet"):
                   msg += f"<b>Magnet Link:</b> <code>{entry.link}</code>\n\n"
                else:
                    msg += f"<b>Torrent Link:</b> <code>{entry.link}</code>\n\n"
                msg += f"<b>Published On:</b> {entry.published}"
      #      message = f"<b>Title:</b> {entry.title}\n"
       #     message += f"<b>Size:</b> {humanbytes(entry.size)}\n"
      #      message += f"<b>Torrent Link:</b> <code>{entry.link}</code>\n"
       #     message += f"<b>Published On:</b> {entry.pubDate}\n"
            else:
                msg = f"{entry}"
            try:
                app.send_message(log_channel, msg)
                db.update_link(feed_url, entry.id)
            except FloodWait as e:
                print(f"FloodWait: {e.x} seconds")
                sleep(e.x)
            except Exception as e:
                print(e)
        else:
            print(f"Checked RSS FEED: {entry.id}")
    return check_feed


scheduler = BackgroundScheduler()
for feed_url in feed_urls:
    feed_checker = create_feed_checker(feed_url)
    scheduler.add_job(feed_checker, "interval", seconds=check_interval, max_instances=max_instances)
scheduler.start()
app.run()
