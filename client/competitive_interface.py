import curses
from client.player_interface import PlayerInterface
from common.logger import Logger

class CompetitiveInterface(PlayerInterface):
    """Interface for competitive game mode"""
    
    def __init__(self, debug=False):
        """Initialize competitive interface
        
        Args:
            debug (bool): Enable debug logging
        """
        super().__init__(debug=debug)
        self.messages = []
        self.scores = {}
        self.round = 0
        self.time_left = 0
        self.running = False
        self.logger = Logger.get("CompetitiveInterface", debug)
    
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
        
        # Set up colors
        curses.start_color()
        curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)  # Success
        curses.init_pair(2, curses.COLOR_RED, curses.COLOR_BLACK)    # Failure
        curses.init_pair(3, curses.COLOR_YELLOW, curses.COLOR_BLACK) # Highlight
        
        max_y, max_x = stdscr.getmaxyx()
        
        # Create windows
        message_win = curses.newwin(max_y - 10, max_x // 2, 0, 0)
        score_win = curses.newwin(max_y - 10, max_x // 2, 0, max_x // 2)
        puzzle_win = curses.newwin(4, max_x, max_y - 10, 0)
        input_win = curses.newwin(3, max_x, max_y - 3, 0)
        stats_win = curses.newwin(3, max_x, max_y - 6, 0)
        
        # Main loop
        while self.running and self.player:
            # Update windows
            self._draw_message_window(message_win)
            self._draw_score_window(score_win)
            self._draw_puzzle_window(puzzle_win)
            self._draw_stats_window(stats_win)
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
        win.border()
        win.addstr(0, 2, " Messages ")
        max_y, max_x = win.getmaxyx()
        recent_messages = self.messages[-(max_y-2):]
        for i, msg in enumerate(recent_messages):
            if i < max_y - 2:
                win.addstr(i + 1, 1, msg[:max_x-3])
        win.refresh()
        
    def _draw_score_window(self, win):
        """Draw the score window with player scores"""
        win.clear()
        win.border()
        win.addstr(0, 2, " Scores ")
        
        max_y, max_x = win.getmaxyx()
        sorted_scores = sorted(self.scores.items(), key=lambda x: x[1], reverse=True)
        
        # Highlight current player
        for i, (name, score) in enumerate(sorted_scores):
            if i < max_y - 2:
                if name == self.player.username:
                    win.addstr(i + 1, 1, f"{name}: {score}", curses.color_pair(3))
                else:
                    win.addstr(i + 1, 1, f"{name}: {score}")
        
        win.refresh()
        
    def _draw_puzzle_window(self, win):
        """Draw the puzzle window with round info"""
        win.clear()
        win.border()
        win.addstr(0, 2, f" Round {self.round} ")
        
        if self.player and self.player.current_puzzle:
            win.addstr(1, 1, f"Current Puzzle: {self.player.current_puzzle}")
            win.addstr(2, 1, f"Time left: {self.time_left} seconds")
        else:
            win.addstr(1, 1, "Waiting for puzzle...")
            
        win.refresh()
        
    def _draw_stats_window(self, win):
        """Draw stats window with game statistics"""
        win.clear()
        win.border()
        win.addstr(0, 2, " Game Stats ")
        win.addstr(1, 1, f"Your current score: {self.scores.get(self.player.username if self.player else '', 0)}")
        
        # Get the leader if there's at least one score
        if self.scores:
            leader = max(self.scores.items(), key=lambda x: x[1])
            win.addstr(1, 40, f"Leader: {leader[0]} ({leader[1]} points)")
            
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
        """Show a puzzle with competitive info"""
        self.add_message(f"Received puzzle: {puzzle}")
        
        # Check for round and time info
        if len(args) >= 2:
            try:
                self.round = int(args[0])
                self.time_left = int(args[1])
            except ValueError:
                pass
        
    def show_new_puzzle(self, puzzle, *args):
        """Show a new puzzle with round information"""
        self.add_message(f"New puzzle for round {args[0] if args else 'unknown'}")
        
        # Check for round and time info
        if len(args) >= 2:
            try:
                self.round = int(args[0])
                self.time_left = int(args[1])
            except ValueError:
                pass
        
    def show_solution_result(self, is_correct, *args):
        """Show solution result with points earned"""
        if is_correct:
            points = int(args[0]) if args and args[0].isdigit() else 1
            total = int(args[1]) if len(args) > 1 and args[1].isdigit() else 0
            
            self.add_message(f"CORRECT! +{points} points (Total: {total})")
            # Update own score
            self.scores[self.player.username if self.player else ''] = total
        else:
            self.add_message("INCORRECT! Try again.")
        
    def show_message(self, message):
        """Show a general message"""
        self.add_message(message)
        
    def show_score_update(self, player_name, score, *args):
        """Update and display player scores"""
        try:
            self.scores[player_name] = int(score)
            if self.player and player_name == self.player.username:
                self.add_message(f"Your score updated: {score}")
            else:
                self.add_message(f"Player {player_name}'s score: {score}")
        except ValueError:
            self.add_message(f"Score update for {player_name}: {score}")

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
