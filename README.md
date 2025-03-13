# CDR2Discord

## Overview
This software monitors recent call detail records (CDRs) from an Asterisk database, logs call details to a Discord webhook, and uploads call recordings if available. Additionally, it deletes processed call records from the database.

## Features
- Fetches recent call details from the Asterisk CDR database.
- Sends call logs to a specified Discord webhook.
- Uploads call recordings if they exist and are of a valid size.
- Deletes processed CDRs to maintain database cleanliness.
- Continuously monitors for new calls.

## Requirements
- Python 3.x
- MySQL Server with Asterisk CDR database
- A valid Discord Webhook URL

## Installation
1. Clone the repository or copy the script files to your system.
2. Install dependencies using:
   ```sh
   pip install -r requirements.txt
   ```
3. Update the `db_config` dictionary in the script to match your database credentials.
4. Set the `discord_webhook_url` variable to your Discord webhook URL.
5. Ensure your Asterisk call recordings are stored in the directory specified in `recording_base_directory`.

## Usage
Run the script using:
```sh
python script.py
```
The script will continuously monitor for new calls, log details, upload recordings, and remove processed records.

## Configuration
- **Database Settings**: Modify the `db_config` dictionary to reflect your MySQL database credentials.
- **Recording Directory**: Ensure `recording_base_directory` is correctly set to where Asterisk stores call recordings.
- **Discord Webhook**: Replace `discord_webhook_url` with your actual Discord webhook endpoint.

## Notes
- Ensure the MySQL user has the necessary permissions to read from and delete records in the `cdr` table.
- The script runs indefinitely, checking for new calls every few seconds. To stop it, use `CTRL + C`.

## License
This project is licensed under the GNU V3 License.


