from telethon import TelegramClient
import asyncio
from dotenv import load_dotenv
import os
import curses
from telegram_utils import get_last_messages, format_message, print_help, stream_print
from llm_utils import (
    show_global_context, process_prompt_with_context, add_messages_to_context,
    clear_global_context, get_llm_summary
)
from message_viewer import view_messages

load_dotenv()

api_id = os.getenv('API_ID')    
api_hash = os.getenv('API_HASH')
session_name = os.getenv('SESSION_NAME')

class ChatNavigator:
    def __init__(self, stdscr, dialogs):
        self.stdscr = stdscr
        self.dialogs = dialogs
        self.current_pos = 0
        self.offset = 0
        self.height, self.width = stdscr.getmaxyx()
        self.max_visible = self.height - 4  # Leave space for header/footer
        
    def draw(self):
        self.stdscr.clear()
        
        # Draw header
        header = "Telegram Chats (↑/↓ to navigate, Enter to select, [ to go back, q to quit)"
        self.stdscr.addstr(0, 0, header, curses.A_BOLD)
        self.stdscr.addstr(1, 0, "=" * min(len(header), self.width))
        
        # Draw chats
        for i in range(min(self.max_visible, len(self.dialogs))):
            idx = i + self.offset
            if idx >= len(self.dialogs):
                break
                
            dialog = self.dialogs[idx]
            line = f"{idx + 1}. {dialog.name}"
            if dialog.unread_count > 0:
                line += f" [{dialog.unread_count}]"
                
            y = i + 2  # Start after header
            if idx == self.current_pos:
                self.stdscr.attron(curses.A_REVERSE)
                self.stdscr.addstr(y, 0, line[:self.width])
                self.stdscr.attroff(curses.A_REVERSE)
            else:
                self.stdscr.addstr(y, 0, line[:self.width])
        
        # Draw scrollbar if needed
        if len(self.dialogs) > self.max_visible:
            scrollbar_height = int((self.max_visible / len(self.dialogs)) * self.max_visible)
            scrollbar_pos = int((self.offset / len(self.dialogs)) * self.max_visible) + 2
            for i in range(self.max_visible):
                y = i + 2
                if scrollbar_pos <= y < scrollbar_pos + scrollbar_height:
                    self.stdscr.addstr(y, self.width - 1, "█")
                else:
                    self.stdscr.addstr(y, self.width - 1, "│")
        
        self.stdscr.refresh()
    
    def handle_key(self, key):
        if key == curses.KEY_UP and self.current_pos > 0:
            self.current_pos -= 1
            if self.current_pos < self.offset:
                self.offset = self.current_pos
        
        elif key == curses.KEY_DOWN and self.current_pos < len(self.dialogs) - 1:
            self.current_pos += 1
            if self.current_pos >= self.offset + self.max_visible:
                self.offset = self.current_pos - self.max_visible + 1
        
        elif key == ord('\n'):  # Enter key
            return self.dialogs[self.current_pos]
        
        elif key == ord('['):  # [ key
            return 'back'
        
        elif key == ord('q'):  # q key
            return 'quit'
        
        return None

async def navigate_chats(dialogs):
    def _navigate(stdscr):
        # Setup curses
        curses.curs_set(0)  # Hide cursor
        stdscr.nodelay(0)   # Make getch() blocking
        
        navigator = ChatNavigator(stdscr, dialogs)
        result = None
        
        while True:
            navigator.draw()
            key = stdscr.getch()
            result = navigator.handle_key(key)
            
            if result is not None:
                break
        
        return result
    
    # Run the curses application
    return curses.wrapper(_navigate)

async def summarize_messages(messages):
    """Summarize messages using LLM"""
    try:
        formatted_msgs = []
        for msg in messages:
            if not msg.text:
                continue
            sender = (await msg.get_sender()) if msg.sender_id else None
            sender_name = sender.username if sender and sender.username else (sender.first_name if sender else "Unknown")
            formatted_msgs.append(f"{sender_name}: {msg.text}")
        
        if not formatted_msgs:
            return "No text messages to summarize."
            
        messages_text = "\n".join(formatted_msgs)
        summary = await get_llm_summary(messages_text)
        return summary
        
    except Exception as e:
        return f"Error creating summary: {str(e)}"

async def handle_chat_commands(cmd, client, entity, chosen_dialog):
    """Handle chat-level commands"""
    if cmd == "/view":
        cmd = await view_messages(client, entity)
        if cmd:
            return await handle_chat_commands(cmd, client, entity, chosen_dialog)
        return True

    elif cmd.startswith("/read "):
        parts = cmd.split()
        if len(parts) == 2 and parts[1].isdigit():
            x = int(parts[1])
            msgs = await get_last_messages(client, entity, limit=x)
            for m in msgs:
                sender = (await m.get_sender()) if m.sender_id else None
                sender_name = sender.username if sender and sender.username else (sender.first_name if sender else "Unknown")
                print(f"[{m.date.strftime('%Y-%m-%d %H:%M:%S')}] {sender_name}: {m.text or '(non-text message)'}")
        else:
            print("Usage: /read x (where x is a number)")
            
    elif cmd == "/send":
        text = input("Enter the message to send:\n").strip()
        confirm = input("Send this message? (y/n): ").strip().lower()
        if confirm == 'y':
            await client.send_message(entity, text)
            print("Message sent!")
        else:
            print("Message not sent.")
    
    elif cmd.startswith("/summarize "):
        try:
            parts = cmd.split()
            if len(parts) == 2 and parts[1].isdigit():
                x = int(parts[1])
                print(f"\nFetching and summarizing last {x} messages...")
                msgs = await get_last_messages(client, entity, limit=x)
                if msgs:
                    summary = await summarize_messages(msgs)
                    print("\nSummary of conversation:")
                    print("-" * 40)
                    stream_print(summary)
                    print("-" * 40)
                else:
                    print("No messages found to summarize.")
            else:
                print("Usage: /summarize x (where x is a number)")
        except Exception as e:
            print(f"Error during summarization: {str(e)}")
    
    elif cmd.startswith("/add "):
        parts = cmd.split()
        if len(parts) == 2 and parts[1].isdigit():
            x = int(parts[1])
            print(f"\nFetching last {x} messages to add to context...")
            msgs = await get_last_messages(client, entity, limit=x)
            if msgs:
                formatted_msgs = [await format_message(msg) for msg in msgs]
                result = await add_messages_to_context(formatted_msgs)
                print(result)
            else:
                print("No messages found to add to context.")
        else:
            print("Usage: /add x (where x is a number)")
    
    elif cmd == "/prompt":
        prompt = input("Enter your prompt:\n").strip()
        print("\nProcessing prompt with context...")
        print("-" * 40)
        await process_prompt_with_context(prompt)
        print("-" * 40)
    
    elif cmd == "/clear":
        result = clear_global_context()
        print(result)
    
    elif cmd == "/show":
        context_display = show_global_context()
        print(context_display)
    
    elif cmd == "/help":
        print_help()
        
    else:
        return False
        
    return True

async def list_chats(client):
    """List all available Telegram chats"""
    dialogs = []
    async for dialog in client.iter_dialogs():
        dialogs.append(dialog)
    return dialogs

async def main():
    async with TelegramClient(session_name, api_id, api_hash) as client:
        print("Telegram client connected.")
        
        while True:
            # Get the list of dialogs
            dialogs = await list_chats(client)
            
            # Enter the chat navigation interface
            result = await navigate_chats(dialogs)
            
            if result == 'quit':
                print("Exiting...")
                break
                
            elif result == 'back':
                continue
                
            elif result:  # Dialog selected
                chosen_dialog = result
                entity = chosen_dialog.entity
                # Clear screen after exiting curses
                print("\033[H\033[J")  # ANSI escape sequence to clear screen
                print(f"\nYou are now in chat mode with: {chosen_dialog.name}")
                print_help()
                
                while True:
                    cmd = input(f"{chosen_dialog.name}> ").strip()
                    
                    if cmd == "/back":
                        print("Returning to chat selection...")
                        break
                        
                    # Handle all other commands
                    handled = await handle_chat_commands(cmd, client, entity, chosen_dialog)
                    if not handled:
                        print("Unknown command. Type /help for a list of commands.")

if __name__ == "__main__":
    asyncio.run(main())