import curses
from client.player_interface import PlayerInterface
from common.logger import Logger

class ClassicInterface(PlayerInterface):
    """Interface for classic game mode"""
    
    def __init__(self, debug=False):
        """Initialize classic interface
        
        Args:
            debug (bool): Enable debug logging
        """
        super().__init__(debug=debug)
        self.messages = []
        self.running = False
        self.logger = Logger.get("ClassicInterface", debug)
    
    def run(self):
        """Run the interface"""
        if not self.player:
            self.logger.error("Cannot run: No player attached")
            return
            
        self.running = True
        try:
            curses.wrapper(self._main_loop)
        except Exception as e:
            self.logger.error(f"Interface error: {e}")
        finally:
            self.running = False
            
    def _main_loop(self, stdscr):
        """Main loop for the curses interface"""
        # Configure curses
        curses.curs_set(1)  # Show cursor
        stdscr.clear()
        stdscr.refresh()
        
        max_y, max_x = stdscr.getmaxyx()
        
        # Create windows
        message_win = curses.newwin(max_y - 4, max_x, 0, 0)
        puzzle_win = curses.newwin(1, max_x, max_y - 4, 0)
        input_win = curses.newwin(3, max_x, max_y - 3, 0)
        
        # Initial display
        self._draw_message_window(message_win)
        self._draw_puzzle_window(puzzle_win)
        self._draw_input_window(input_win)
        
        # Main loop
        while self.running and self.player:
            # Update windows
            self._draw_message_window(message_win)
            self._draw_puzzle_window(puzzle_win)
            self._draw_input_window(input_win)
            
            # Get input
            input_win.clear()
            input_win.border()
            input_win.addstr(1, 1, "Enter solution (or 'exit'/'quit'): ")
            input_win.refresh()
            
            curses.echo()
            try:
                user_input = input_win.getstr(1, 40, 50).decode('utf-8').strip()
            except:
                # Handle interrupts (like window resize)
                continue
                
            curses.noecho()
            
            # Process input
            if user_input.lower() == 'exit':
                self.running = False
                self.player.exit_game()
                break
            elif user_input.lower() == 'quit':
                self.player.surrender()
                self.add_message("You surrendered this puzzle")
            else:
                self.player.submit_solution(user_input)
                
    def _draw_message_window(self, win):
        """Draw the message window"""
        win.clear()
        max_y, max_x = win.getmaxyx()
        recent_messages = self.messages[-(max_y):]
        for i, msg in enumerate(recent_messages):
            if i < max_y:
                win.addstr(i, 0, msg[:max_x-1])
        win.refresh()
        
    def _draw_puzzle_window(self, win):
        """Draw the puzzle window"""
        win.clear()
        if self.player and self.player.current_puzzle:
            win.addstr(0, 0, f"Current Puzzle: {self.player.current_puzzle}")
        else:
            win.addstr(0, 0, "Waiting for puzzle...")
        win.refresh()
        
    def _draw_input_window(self, win):
        """Draw the input window"""
        win.clear()
        win.border()
        win.addstr(0, 2, " Enter your solution ")
        win.refresh()
        
    def add_message(self, message):
        """Add a message to the list"""
        self.messages.append(message)
        if self.debug:
            self.logger.debug(f"Added message: {message}")
        
    # Interface implementation methods
    def show_puzzle(self, puzzle, *args):
        self.add_message(f"Received puzzle: {puzzle}")
        
    def show_new_puzzle(self, puzzle, *args):
        self.add_message(f"New puzzle: {puzzle}")
        
    def show_solution_result(self, is_correct, *args):
        if is_correct:
            self.add_message("Your solution was CORRECT!")
        else:
            self.add_message("Your solution was INCORRECT. Try again.")
        
    def show_message(self, message):
        self.add_message(message)
        
    def show_score_update(self, player_name, score, *args):
        # Not used in classic mode, but implemented for compatibility
        pass

    def get_user_input(self, prompt="Enter your solution: "):
        """Get input from user
        
        This is mainly used by PlayerInterface for compatibility,
        but the actual input handling is done in _main_loop.
        
        Args:
            prompt (str): Prompt to display
            
        Returns:
            str: User input or None if not available
        """
        # This is a simplified version for compatibility
        # In practice, input is handled by curses in _main_loop
        if not self.running:
            try:
                return input(prompt)
            except (EOFError, KeyboardInterrupt):
                return None
        return None
