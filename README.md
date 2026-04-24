# RemixDataBase

A Python project that integrates Twilio messaging and phone number lookup with MongoDB (CosmosDB) for managing messages and phone number information.

## Features

- **Twilio Phone Lookup API**: Fetch carrier and caller-name information for phone numbers
- **Twilio Messaging**: Send SMS messages through Twilio
- **MongoDB Integration**: Store message history and phone lookup data in MongoDB/CosmosDB
- **Environment Configuration**: Secure credential management via `.env` file

## Prerequisites

- Python 3.14 or higher
- [MongoDB Atlas](https://www.mongodb.com/cloud/atlas) or [Azure CosmosDB](https://azure.microsoft.com/en-us/products/cosmos-db/) account
- [Twilio Account](https://www.twilio.com/) with active phone number and API credentials

## Environment Setup

Create a `.env` file in the project root with the following variables:

```env
MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/dbname
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_FROM_NUMBER=+1234567890  # Your Twilio phone number
TWILIO_TO_NUMBER=+0987654321    # Recipient phone number
```

> **Note**: Replace the `TWILIO_FROM_NUMBER` with a phone number from your Twilio account, not a random number.

## Installation

Choose one of the following approaches:

### Option 1: Using uv (Recommended)

[uv](https://github.com/astral-sh/uv) is a fast Python package installer and resolver.

```bash
# Install uv if you haven't already
# See https://github.com/astral-sh/uv#installation

# Sync dependencies
uv sync

# Run the application
uv run python -m src.twilio_client
```

### Option 2: Using standard pip

```bash
# Create a virtual environment
python -m venv .venv

# Activate the virtual environment
# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the application
python -m src.twilio_client
```

## Project Structure

```
RemixDataBase/
├── src/                     # Source code
│   ├── __init__.py         # Package initialization
│   ├── twilio_client.py    # Twilio messaging and phone lookup
│   ├── database.py         # MongoDB database operations
│   └── main.py             # Main entry point
├── data/                    # Data files and outputs
│   ├── .gitkeep
│   ├── messages.csv        # Exported messages (generated)
│   └── phone_lookups.csv   # Exported phone lookups (generated)
├── tests/                   # Test files
│   └── .gitkeep
├── docs/                    # Documentation
│   └── .gitkeep
├── .env                     # Environment variables (not in version control)
├── .python-version          # Python version specification for uv
├── .venv/                   # Virtual environment (created by uv sync)
├── .gitignore              # Git ignore rules
├── README.md               # This file
├── pyproject.toml          # Project metadata and dependencies
├── requirements.txt        # Pinned dependencies for pip
└── uv.lock                 # Dependency lock file (uv)
```

## Usage

### Running the Twilio client

The main application sends SMS messages and looks up phone numbers using Twilio:

```bash
# With uv
uv run python -m src.twilio_client

# With pip (after activating venv)
python -m src.twilio_client
```

### Running the database utility

Export messages and phone lookups from MongoDB to CSV:

```bash
# With uv
uv run python -m src.database

# With pip (after activating venv)
python -m src.database
```

This creates two CSV files:
- `data/messages.csv` - All SMS message data
- `data/phone_lookups.csv` - All phone number lookup data

### How the application works

1. **Phone Number Lookup**: Uses Twilio Lookup API to fetch carrier and caller-name information
2. **Phone Lookup Storage**: Stores lookup results in MongoDB `PhoneLookups` collection
3. **SMS Sending**: Sends test messages using Twilio
4. **Message Storage**: Stores all message metadata in MongoDB `Messages` collection
5. **CSV Export**: Exports stored messages to `data/messages.csv` for analysis

### What gets stored in MongoDB

**PhoneLookups collection:**
- Phone number details
- Carrier information (name, type, MCC/MNC)
- Caller-name information
- Country code and national format
- Lookup timestamp and API URL

**Messages collection:**
- Message SID
- Message body and metadata
- Message status
- Timestamps (created, sent, updated)
- Error information if failed

## Dependencies

### Core Dependencies
- **pymongo** (4.16.0+): MongoDB Python driver
- **twilio** (9.10.4+): Twilio SDK
- **python-dotenv** (1.2.2+): Environment variable management

### Transitive Dependencies
All transitive dependencies are automatically installed and pinned in `requirements.txt` for reproducibility.

## Troubleshooting

### "Python was not found" error
If you see "Python was not found; run without arguments to install from the Microsoft Store":
- Disable the Windows App Execution Alias for python.exe in Settings
- Or ensure your python PATH is set correctly
- Use uv which manages its own Python installation

### "No module named 'src'" error
Make sure you're running from the project root directory:
```bash
cd c:\Users\zacwr\OneDrive\XD\Projects\RemixDataBase
```

Then use the correct command:
```bash
uv run python -m src.twilio_client
```

### Module not found errors
Ensure dependencies are installed:
```bash
uv sync      # for uv
# OR
pip install -r requirements.txt  # for pip
```

### "From phone number is not a valid Twilio number"
Ensure `TWILIO_FROM_NUMBER` in your `.env` is a phone number purchased in your Twilio account, not a random number.

### CSV file not created or exported
The `data/` directory will be created automatically on first run. Verify:
```bash
# List data directory contents
ls data/       # macOS/Linux
dir data       # Windows
```

The CSV file is created at `data/messages.csv` when you run the database export utility.


## Development

### Updating dependencies

With uv:
```bash
uv add package_name
uv export > requirements.txt
```

With pip:
```bash
pip install --upgrade package_name
pip freeze > requirements.txt
```

### Regenerating requirements.txt

If dependencies change, regenerate `requirements.txt` to keep pip users in sync:

```bash
uv export > requirements.txt
```

## License

Add your license information here.

## Contributing

Guidelines for contributing to this project.
