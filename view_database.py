from pymongo import MongoClient
import os
import csv
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get credentials from environment variables
mongobd_uri = os.getenv("MONGODB_URI")

if not mongobd_uri:
    raise ValueError("MONGODB_URI environment variable not set. Please check your .env file.")

try:
    client = MongoClient(mongobd_uri)
    Twilio = client["TwilioDB"]
    Messages = Twilio["Messages"]
    
    # Get all messages from the database
    messages = list(Messages.find())
    
    csv_file = 'messages.csv'
    existing_sids = set()
    
    if os.path.exists(csv_file):
        with open(csv_file, 'r', newline='') as f:
            reader = csv.reader(f)
            next(reader, None)  # skip header
            for row in reader:
                if row:
                    existing_sids.add(row[0])
    
    new_messages_count = 0
    with open(csv_file, 'a', newline='') as f:
        writer = csv.writer(f)
        if not existing_sids:  # if file didn't exist, write header
            writer.writerow(['SID', 'Body', 'From', 'To', 'Status', 'Date Created', 'Date Sent', 'Date Updated', 'Error'])
        for msg in messages:
            sid = msg.get('sid', 'N/A')
            if sid not in existing_sids:
                row = [
                    sid,
                    msg.get('body', 'N/A'),
                    msg.get('from_', 'N/A'),
                    msg.get('to', 'N/A'),
                    msg.get('status', 'N/A'),
                    str(msg.get('date_created', 'N/A')),
                    str(msg.get('date_sent', 'N/A')),
                    str(msg.get('date_updated', 'N/A')),
                    msg.get('error', 'None')
                ]
                writer.writerow(row)
                existing_sids.add(sid)
                new_messages_count += 1
    
    print(f"CSV file '{csv_file}' updated with {new_messages_count} new messages.")
    print(f"Total messages in database: {len(messages)}")
    
except Exception as e:
    print(f"Error connecting to database: {e}")