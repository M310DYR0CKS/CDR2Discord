import os
import time
import requests
import mysql.connector

discord_webhook_url = "https://dummywebhookurl.net"

db_config = {
    "host": "localhost",
    "user": "asterisk",
    "password": "asterisk",
    "database": "asteriskcdrdb"
}

recording_base_directory = "/var/spool/asterisk/monitor/"

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
    """Formats and sends the CDR data to Discord via webhook."""
    embed = {
        "title": "ðŸ“ž Call Ended",
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
            "text": "Made with <3 MelodyRocks"
        }
    }

    payload = {"embeds": [embed]}
    requests.post(discord_webhook_url, json=payload)

def send_call_recording(recording_path):
    """Sends the call recording to Discord."""
    if recording_path and os.path.exists(recording_path):
        try:
            file_size = os.path.getsize(recording_path)
            if file_size <= 44:
                print(f"Recording is too small ({file_size} bytes). Skipping upload.")
                return

            with open(recording_path, "rb") as recording_file:
                files = {"file": recording_file}
                response = requests.post(discord_webhook_url, files=files)
                response.raise_for_status()
        except Exception as e:
            print(f"Error uploading file: {e}")
    else:
        print(f"Recording not found at {recording_path}. Skipping file upload.")

def monitor_channel_creation():
    print("Monitoring Asterisk SIP channels...")
    while True:
        cdr_data = fetch_recent_cdr()
        print(f"Fetched CDR: {cdr_data}")
        
        if cdr_data:
            calldate = cdr_data["calldate"]
            year = calldate.strftime("%Y")
            month = calldate.strftime("%m")
            day = calldate.strftime("%d")
            
            recording_filename = cdr_data.get('recordingfile')
            if recording_filename:
                recording_path = os.path.join(recording_base_directory, year, month, day, recording_filename)
                print(f"Recording Path: {recording_path}")
            else:
                recording_path = None
                print("No recording found in CDR data.")
            
            send_cdr_log(cdr_data)
            print(f"Logged call end with Unique ID: {cdr_data['uniqueid']}")

            time.sleep(5)
            send_call_recording(recording_path)
            delete_cdr(cdr_data["uniqueid"])
            print(f"Deleted call with Unique ID: {cdr_data['uniqueid']}")
        else:
            print("No recent calls.")
        time.sleep(5)

if __name__ == "__main__":
    monitor_channel_creation()


