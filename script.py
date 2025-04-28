import os
import time
import logging
import requests
import mysql.connector
import subprocess
from typing import Optional, Dict
from datetime import datetime
from requests import Session

# --- Config ---
from dotenv import load_dotenv
load_dotenv()

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
RECORDING_BASE_DIR = "/var/spool/asterisk/monitor/"
MAX_FILE_SIZE_MB = 10
FFMPEG_OPTS = ["-b:a", "64k", "-ar", "8000", "-ac", "1"]
DB_CONFIG = {
    "host": "localhost",
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASS"),
    "database": "asteriskcdrdb"
}

# --- Logging ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("cdr_monitor.log")]
)

# --- HTTP Session ---
session = Session()

# --- Functions ---
def compress_audio(input_path: str, output_path: str) -> Optional[str]:
    command = ["ffmpeg", "-y", "-i", input_path] + FFMPEG_OPTS + ["-fs", f"{MAX_FILE_SIZE_MB}M", output_path]
    try:
        subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if os.path.exists(output_path) and os.path.getsize(output_path) <= MAX_FILE_SIZE_MB * 1024 * 1024:
            return output_path
    except subprocess.CalledProcessError as e:
        logging.warning(f"FFmpeg failed: {e}")
    return None

def fetch_recent_cdr() -> Optional[Dict]:
    try:
        with mysql.connector.connect(**DB_CONFIG) as conn:
            with conn.cursor(dictionary=True) as cursor:
                cursor.execute("""
                    SELECT * FROM cdr 
                    WHERE calldate > NOW() - INTERVAL 3 MINUTE
                    ORDER BY calldate DESC LIMIT 1
                """)
                return cursor.fetchone()
    except Exception as e:
        logging.error(f"Failed to fetch CDR: {e}")
    return None

def delete_cdr(cdr_id: str):
    try:
        with mysql.connector.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM cdr WHERE uniqueid = %s", (cdr_id,))
                conn.commit()
    except Exception as e:
        logging.error(f"Failed to delete CDR {cdr_id}: {e}")

def send_cdr_log(cdr: Dict):
    embed = {
        "title": "📞 Call Ended",
        "color": 0xFFA07A,
        "fields": [
            {"name": "Caller", "value": cdr["src"], "inline": True},
            {"name": "Callee", "value": cdr["dst"], "inline": True},
            {"name": "Start Time", "value": str(cdr["calldate"]), "inline": True},
            {"name": "Duration", "value": f"{cdr['duration']}s", "inline": True},
            {"name": "Answered", "value": f"{cdr.get('billsec', 'N/A')}s", "inline": True},
            {"name": "Disposition", "value": cdr.get("disposition", "N/A"), "inline": True},
            {"name": "Cause", "value": str(cdr.get("hangupcause", "N/A")), "inline": True},
            {"name": "Channel", "value": cdr.get("channel", "N/A"), "inline": False},
            {"name": "Dst Channel", "value": cdr.get("dstchannel", "N/A"), "inline": False},
            {"name": "App", "value": cdr.get("lastapp", "N/A"), "inline": False},
            {"name": "Unique ID", "value": str(cdr["uniqueid"]), "inline": False},
        ],
        "footer": {"text": "(c) 2025 MelodyRocks"}
    }
    try:
        response = session.post(DISCORD_WEBHOOK_URL, json={"embeds": [embed]})
        response.raise_for_status()
    except Exception as e:
        logging.error(f"Failed to send webhook: {e}")

def send_call_recording(recording_path: str):
    if not recording_path or not os.path.exists(recording_path):
        logging.warning("Recording path invalid or missing.")
        return
    compressed_path = recording_path.replace(".wav", "_compressed.mp3")
    compressed_path = compress_audio(recording_path, compressed_path)
    if not compressed_path:
        logging.warning("Compression failed or file too large.")
        return
    try:
        with open(compressed_path, "rb") as f:
            response = session.post(DISCORD_WEBHOOK_URL, files={"file": f})
            response.raise_for_status()
        os.remove(compressed_path)
    except Exception as e:
        logging.error(f"Failed to upload recording: {e}")

def monitor_calls():
    logging.info("Starting Asterisk CDR monitor loop...")
    try:
        while True:
            cdr = fetch_recent_cdr()
            if cdr:
                send_cdr_log(cdr)
                rec_file = cdr.get("recordingfile")
                if rec_file:
                    rec_path = os.path.join(
                        RECORDING_BASE_DIR,
                        cdr["calldate"].strftime("%Y/%m/%d"),
                        rec_file
                    )
                    time.sleep(5)  # Give Asterisk time to flush the recording
                    send_call_recording(rec_path)
                delete_cdr(cdr["uniqueid"])
                time.sleep(2)  # Shorter sleep after work
            else:
                time.sleep(10)  # Longer sleep if idle
    except KeyboardInterrupt:
        logging.info("Shutting down monitor...")

# --- Main ---
if __name__ == "__main__":
    print("(c) 2025 MelodyRocks - You were warned")
    monitor_calls()
