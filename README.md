# Guide_AddOwnPlaces-Telegram-Bot

A Telegram bot that allows users to add and manage their own places of interest. This bot is designed for easy deployment and customization.

## Features
- Add new places with details
- List and manage your saved places
- Simple and intuitive Telegram interface
- Modular code structure for easy extension
- Logging and error handling

## Installation

### Prerequisites
- Python 3.8+
- [pip](https://pip.pypa.io/en/stable/)
- Telegram Bot Token (from [BotFather](https://core.telegram.org/bots#botfather))

### Clone the Repository
```bash
git clone https://github.com/yourusername/Guide_AddOwnPlaces-Telegram-Bot-.git
cd Guide_AddOwnPlaces-Telegram-Bot-
```

### Install Dependencies
```bash
pip install -r requirements.txt
```

> If `requirements.txt` is missing, install dependencies manually as needed (e.g., `aiogram`, `requests`).

## Configuration
1. Create a `.env` file or set environment variables for your bot token:
   ```env
   TELEGRAM_BOT_TOKEN=your_bot_token_here
   ```
2. (Optional) Configure logging or API endpoints in `bot/utils/logger.py` or `bot/services/api_client.py` as needed.

## Running the Bot
```bash
python main.py
```

The bot will start and connect to Telegram. Interact with it via your Telegram client.

## Project Structure
```
main.py
bot/
    states.py
    handlers/
        places.py
    model/
        place.py
    services/
        api_client.py
    utils/
        logger.py
```

## Customization
- Add new handlers in `bot/handlers/` for more features.
- Extend the `Place` model in `bot/model/place.py` for additional attributes.
- Integrate with external APIs via `bot/services/api_client.py`.

## License
MIT License
