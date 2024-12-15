import curses
import asyncio
from typing import List, Callable
from telethon.tl.custom import Dialog

class ChatNavigator:
    def __init__(self, stdscr, dialogs: List[Dialog]):
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
    
    def handle_key(self, key) -> Dialog | str | None:
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

async def navigate_chats(dialogs: List[Dialog]) -> Dialog | str | None:
    def _navigate(stdscr) -> Dialog | str | None:
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