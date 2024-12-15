# tinyml-telegram-client

## Prerequisites 

- python 3.6 or higher
- Telegram account
- LLM API (Ollama by default, but configurable)

## Obtaining API Credentials

To use this client, you'll need to obtain your `API_ID` and `API_HASH` from Telegram:
1. Visit [my.telegram.org](https://my.telegram.org) and log in with your Telegram phone number.
2. Click on 'API development tools' and fill out the form to create a new application.
3. You will be provided with an `API_ID` and `API_HASH` for your newly created application.

You can include your `API_ID` and `API_HASH` in config files. 

**DO NOT EXPOSE THEM OR YOU MIGHT LOSE YOUR ACCOUNT**.

## Installation

Clone the repository and navigate into the project directory:

```bash
git clone https://github.com/yourusername/tinyML-Telegram-Client.git
cd tinyML-Telegram-Client
```
Create a virtual environment:
```python
python -m venv venv
```

Enter your API credentials:
```bash
echo "API_ID=your_api_id_here" >> .env
echo "API_HASH=your_api_hash_here" >> .env
echo "SESSION_NAME=your_session_name_here" >> .env
```

Install the requirements:
```bash
pip install -r requirements.txt
```

Start the client by running:
```bash
python3 main.py
```
## LLM Setup

By default, the client uses Ollama ([installation instructions](https://github.com/ollama/ollama#installation)) with the llama2 model. You can modify `llm_utils.py` to use other LLM APIs like OpenRouter or your preferred provider.


## Usage
![Demo](demo.gif)

1. Start the client:
```bash
python3 main.py
```

2. Navigate chats using:
- ↑/↓ arrows to move between chats
- enter to select a chat
- [ to go back
- q to quit

3. Available chat commands:
- `/view` - view and scroll messages in chat
- `/read x` - read last x messages
- `/summarize x` - get AI summary of last x messages
- `/add x` - add last x messages to context
- `/show` - show current context
- `/prompt` - send prompt to LLM with context
- `/clear` - clear stored context
- `/send` - send a message
- `/back` - return to chat selection
- `/help` - show command list

## Message Viewer Controls
- ↑/↓ - scroll messages
- o - jump to oldest messages
- n - jump to newest loaded messages
- q - exit viewer

## LLM Features
Requires Ollama running locally with the llama2 model installed (or any local of your choice). 

The client uses Ollama for:
- Message summarization
- Context-aware chat analysis
- Historical message understanding

Use `/summarize` and `/prompt` commands to interact with LLM features.