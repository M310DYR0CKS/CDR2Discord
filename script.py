import os
import time
import logging
import requests
import mysql.connector
import subprocess

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

SCRIPT_PATH = os.path.abspath(__file__)

discord_webhook_url = "add your webhook here"

db_config = {
    "host": "localhost",
    "user": "asterisk",
    "password": "asterisk",
    "database": "asteriskcdrdb"
}

recording_base_directory = "/var/spool/asterisk/monitor/"

def compress_audio(input_path, output_path):
    try:
        command = ["ffmpeg", "-i", input_path, "-b:a", "64k", "-ar", "8000", "-ac", "1", "-fs", "10M", output_path]
        subprocess.run(command, check=True)
        return output_path if os.path.exists(output_path) and os.path.getsize(output_path) <= 10 * 1024 * 1024 else None
    except subprocess.CalledProcessError:
        return None

def fetch_recent_cdr():
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT * FROM cdr 
        WHERE calldate > NOW() - INTERVAL 3 MINUTE
        ORDER BY calldate DESC LIMIT 1
    """)
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    return row

def delete_cdr(cdr_id):
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM cdr WHERE uniqueid = %s", (cdr_id,))
    conn.commit()
    cursor.close()
    conn.close()

def send_cdr_log(cdr_data):
    embed = {
        "title": "Call Ended",
        "color": 16738740,
        "fields": [
            {"name": "Caller", "value": cdr_data["src"], "inline": True},
            {"name": "Callee", "value": cdr_data["dst"], "inline": True},
            {"name": "Start Time", "value": str(cdr_data["calldate"]), "inline": True},
            {"name": "Duration", "value": f"{cdr_data['duration']} seconds", "inline": True},
            {"name": "Answered Duration", "value": f"{cdr_data.get('billsec', 'N/A')} seconds", "inline": True},
            {"name": "Hangup Cause", "value": cdr_data.get("hangupcause", "N/A"), "inline": True},
            {"name": "Channel", "value": cdr_data.get("channel", "N/A"), "inline": True},
            {"name": "Destination Channel", "value": cdr_data.get("dstchannel", "N/A"), "inline": True},
            {"name": "Call Type", "value": cdr_data.get("lastapp", "N/A"), "inline": True},
            {"name": "Call Disposition", "value": cdr_data.get("disposition", "N/A"), "inline": True},
            {"name": "Unique ID", "value": str(cdr_data["uniqueid"]), "inline": False},
        ],
        "footer": {
            "text": "(c) 2025 MelodyRocks"
        }
    }
    payload = {"embeds": [embed]}
    requests.post(discord_webhook_url, json=payload)

def send_call_recording(recording_path):
    if recording_path and os.path.exists(recording_path):
        compressed_path = recording_path.replace(".wav", "_compressed.mp3")
        compressed_path = compress_audio(recording_path, compressed_path)
        
        if not compressed_path:
            return
        
        try:
            with open(compressed_path, "rb") as recording_file:
                files = {"file": recording_file}
                requests.post(discord_webhook_url, files=files)
            os.remove(compressed_path)
        except Exception as e:
            logging.error(f"Failed to send recording: {e}")

def setup_cron_job():
    cron_command_reboot = f"@reboot sleep 10 && /usr/bin/python3 {SCRIPT_PATH} &"
    cron_command_restart = f"*/5 * * * * pgrep -f 'python3 {SCRIPT_PATH}' > /dev/null || /usr/bin/python3 {SCRIPT_PATH} &"

    try:
        existing_cron = os.popen("crontab -l 2>/dev/null").read()

        if cron_command_reboot not in existing_cron:
            os.system(f"(crontab -l 2>/dev/null; echo '{cron_command_reboot}') | crontab -")
            logging.info("Added startup cron job.")

        if cron_command_restart not in existing_cron:
            os.system(f"(crontab -l 2>/dev/null; echo '{cron_command_restart}') | crontab -")
            logging.info("Added auto-restart cron job.")

    except Exception as e:
        logging.error(f"Error setting up cron jobs: {e}")

def monitor_channel_creation():
    while True:
        try:
            cdr_data = fetch_recent_cdr()
            if cdr_data:
                send_cdr_log(cdr_data)
                calldate = cdr_data["calldate"]
                year, month, day = calldate.strftime("%Y"), calldate.strftime("%m"), calldate.strftime("%d")
                recording_filename = cdr_data.get('recordingfile')
                recording_path = os.path.join(recording_base_directory, year, month, day, recording_filename) if recording_filename else None
                time.sleep(5)
                send_call_recording(recording_path)
                delete_cdr(cdr_data["uniqueid"])
            time.sleep(5)
        except Exception as e:
            logging.error(f"Unexpected error in monitoring loop: {e}")
            time.sleep(10)

if __name__ == "__main__":
    logging.info("(c) 2025 MelodyRocks - Starting Service")
    setup_cron_job()
    monitor_channel_creation()
