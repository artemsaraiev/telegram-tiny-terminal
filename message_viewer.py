import curses
import locale
from telethon.tl.types import User, Chat, Channel
import asyncio

locale.setlocale(locale.LC_ALL, '')

KEY_UP = curses.KEY_UP
KEY_DOWN = curses.KEY_DOWN

class MessageViewer:
    def __init__(self, stdscr, messages, entity, client, loop, current_offset):
        self.stdscr = stdscr
        self.messages = list(sorted(messages, key=lambda m: m['id'], reverse=False))
        # self.messages = list(reversed(messages))
        self.entity = entity
        self.client = client
        self.loop = loop
        self.entity_name = self.get_entity_name(entity)
        self.current_pos = len(self.messages) - 1
        self.height, self.width = stdscr.getmaxyx()
        self.max_visible = self.height - 4
        if current_offset == -1:
            self.offset = max(0, self.current_pos - self.max_visible + 1)
        else:
            self.offset = current_offset
        self.command_mode = False
        self.command_buffer = ""
        self.oldest_message_id = min(msg['id'] for msg in messages) if messages else None
        # self.oldest_message_id = self.messages[0]['id'] if self.messages else None  # track oldest loaded message ID
    
        
    def get_entity_name(self, entity):
        if isinstance(entity, User):
            return entity.first_name or entity.username or "User"
        elif isinstance(entity, (Chat, Channel)):
            return entity.title
        return str(entity)

    def draw(self, last_y=None):
        if last_y is None:
            self.stdscr.clear()
            header = f"Messages (↑/↓ to scroll, / for commands, q to exit) - {self.entity_name}"
            self.safe_addstr(0, 0, header, curses.A_BOLD)
            self.safe_addstr(1, 0, "=" * (self.width-1))
            current_y = self.height - 2
        else:
            current_y = last_y

        visible_messages = self.messages[self.offset:self.offset + self.max_visible]

        for msg in reversed(visible_messages):
            date_str = msg['date'].strftime('%H:%M:%S')
            line = f"[{date_str}] {msg['sender']}: {msg['text']}"

            remaining = line
            while remaining and current_y > 1:
                space_left = self.width - 1
                if len(remaining) > space_left:
                    split_point = remaining[:space_left].rfind(' ')
                    if split_point == -1:
                        split_point = space_left
                    self.safe_addstr(current_y, 0, remaining[:split_point])
                    remaining = remaining[split_point:].strip()
                else:
                    self.safe_addstr(current_y, 0, remaining)
                    remaining = ''
                current_y -= 1

        if self.command_mode:
            self.safe_addstr(self.height-1, 0, self.command_buffer)
            curses.curs_set(1)
        else:
            curses.curs_set(0)

        self.stdscr.refresh()
        return current_y



    def safe_addstr(self, y, x, text, attr=0):
        try:
            if y < self.height and x < self.width:
                remaining_width = self.width - x
                safe_text = text[:remaining_width]
                if isinstance(safe_text, str):
                    safe_text = safe_text.encode('utf-8', errors='replace').decode('utf-8')
                self.stdscr.addstr(y, x, safe_text, attr)
        except curses.error:
            pass

    def handle_key(self, key):
        if self.command_mode:
            if key == 27:  # ESC
                self.command_mode = False
                self.command_buffer = ""
            elif key == ord('\n'):
                cmd = self.command_buffer
                self.command_mode = False
                self.command_buffer = ""
                return cmd
            elif key == curses.KEY_BACKSPACE or key == 127:
                self.command_buffer = self.command_buffer[:-1]
            elif 32 <= key <= 126:
                self.command_buffer += chr(key)
            elif key == curses.KEY_UP or key == curses.KEY_DOWN:
                self.command_buffer = ""
                self.command_mode = False
            return None
            

        if key == ord('/'):
            self.command_mode = True
            self.command_buffer = "/"
        elif key == curses.KEY_UP:
            if self.offset > 0:
                self.offset -= 1
            else:
                # Instead of trying to load older messages here,
                # return a special command to signal that we need older messages.
                return '/load_older'
        elif key == curses.KEY_DOWN:
            if self.offset < len(self.messages) - self.max_visible:
                self.offset += 1
        elif key == ord('o'):  # go bottom (newest messages)
            self.offset = 0
        elif key == ord('n'):  # go top (oldest messages)
            self.offset = max(0, len(self.messages) - self.max_visible)
        elif key == ord('q'):  
            return 'quit'
            
        return None
    
    
    def load_older_messages(self):
        print(f'In load_older_messages, {self.oldest_message_id=}')
        # Synchronously load older messages by running async code
        if self.oldest_message_id:
            older_messages = self.loop.run_until_complete(self.fetch_older_messages())
            print(f'loaded {len(older_messages)} older messages')
            if older_messages:
                # Prepend older_messages to self.messages
                self.messages = older_messages + self.messages
                # Adjust offset to account for newly added messages
                self.offset += len(older_messages)
                # Update oldest_message_id
                self.oldest_message_id = self.messages[0]['id']
                print(f'new offset is {self.offset}')
                return True
        return False

    async def fetch_older_messages(self, batch_size=10):
        # Use oldest_message_id to load messages before that
        older_msgs_raw = []
        async for m in self.client.iter_messages(self.entity, limit=batch_size, max_id=self.oldest_message_id - 1):
            if m.text:
                sender = await m.get_sender()
                sender_name = sender.username if sender and sender.username else (sender.first_name if sender else "Unknown")
                older_msgs_raw.append({
                    'id': m.id,
                    'text': m.text,
                    'sender': sender_name,
                    'date': m.date
                })
        
        # oldest first so reverse if needed
        return list(reversed(older_msgs_raw))

async def load_messages(client, entity, limit=10):
    messages = []
    async for message in client.iter_messages(entity, limit=limit):
        if message.text:  # Only include text messages
            sender = await message.get_sender()
            sender_name = sender.username if sender and sender.username else (sender.first_name if sender else "Unknown")
            messages.append({
                'id': message.id,
                'text': message.text,
                'sender': sender_name,
                'date': message.date
            })
    return messages



async def view_messages(client, entity):
    current_offset = -1
    messages = await load_messages(client, entity, limit=10)  # Initial batch
    loop = asyncio.get_event_loop()
    viewer = None
    async def fetch_older_messages(oldest_message_id, batch_size=100):
        older_msgs = []
        async for m in client.iter_messages(entity, limit=batch_size, max_id=oldest_message_id - 1):
            if m.text:
                sender = await m.get_sender()
                sender_name = sender.username if sender and sender.username else (sender.first_name if sender else "Unknown")
                older_msgs.append({
                    'id': m.id,
                    'text': m.text,
                    'sender': sender_name,
                    'date': m.date
                })
        return list(reversed(older_msgs))

    def _view(stdscr, msgs):
        nonlocal viewer
        curses.use_default_colors()
        viewer = MessageViewer(stdscr, msgs, entity, client, loop, current_offset)  # Pass client and loop here
        while True:
            viewer.draw()
            try:
                key = stdscr.getch()
                if key == -1:  # No key pressed
                        continue
                result = viewer.handle_key(key)
                
                if result == 'quit':
                    return 'quit'
                elif result == '/load_older':
                    return '/load_older'  # Signal we need more messages
                elif result and result.startswith('/'):
                    return result
            except curses.error:
                continue
            # else continue looping

    while True:
        command = curses.wrapper(lambda stdscr: _view(stdscr, messages))
        

        if command == 'quit':
            return
        elif command == '/load_older':
            # Fetch older messages async here
            current_offset = viewer.offset
            if messages:
                oldest_message_id = min(msg['id'] for msg in messages)
                older = await fetch_older_messages(oldest_message_id)
                if older:
                    messages =  older + messages
                else:
                    # No older messages found, maybe show a message or just continue
                    # so user remains in the curses view
                    print("No older messages found")
            # After attempting to load older messages (whether found or not), go back to the view
            continue
        elif command and command.startswith('/'):
            # Handle other commands
            return command
        else:
            # No command returned (None), just continue to show UI again
            continue