from telethon import TelegramClient
from typing import List
from datetime import datetime
import time
import sys

def stream_print(text: str, delay: float = 0.005):
    """Print text with a streaming effect"""
    for char in text:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(delay)
    sys.stdout.write('\n')

def format_chat_line(index: int, dialog) -> str:
    """Format chat line with bold unread count if any"""
    unread_text = f" \033[1m[{dialog.unread_count}]\033[0m" if dialog.unread_count > 0 else ""
    return f"{index}. {dialog.name}{unread_text}"

async def list_chats(client):
    """List all available Telegram chats"""
    dialogs = []
    async for dialog in client.iter_dialogs():
        dialogs.append(dialog)
    return dialogs

async def get_last_messages(client, entity, limit=10):
    """Fetch last X messages from a specific chat"""
    messages = []
    async for message in client.iter_messages(entity, limit=limit):
        messages.append(message)
    messages.reverse()
    return messages

async def format_message(msg):
    """Format a single message with sender information"""
    if not msg.text:
        return None
    
    sender = (await msg.get_sender()) if msg.sender_id else None
    sender_name = sender.username if sender and sender.username else (sender.first_name if sender else "Unknown")
    
    return {
        'date': msg.date.strftime('%Y-%m-%d %H:%M:%S'),
        'sender': sender_name,
        'text': msg.text
    }

def print_help():
    """Print help message for available commands"""
    print("\nChat-Level Commands:")
    print("/view         - View messages in this chat")
    print("/read x       - Read the last x messages from this chat")
    print("/summarize x  - Get an AI summary of the last x messages")
    print("/add x        - Add last x messages to global context")
    print("/show         - Show current context")
    print("/prompt       - Send a prompt to LLM with current context")
    print("/clear        - Clear all stored context")
    print("/send         - Send a message to this chat")
    print("/back         - Return to the main chat selection menu")
    print("/list x       - List 50 chats starting from index x")
    print("/help         - Show this help message\n")