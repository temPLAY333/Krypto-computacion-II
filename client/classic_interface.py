import curses
from client.player_interface import PlayerInterface
from common.logger import Logger
import threading
import time

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
        self.stats = {
            "total_players": 0,
            "correct_answers": 0,
            "surrendered": 0
        }
        self.input_buffer = ""
        self.input_lock = threading.Lock()
        self.refresh_needed = False  # Add this flag

    def request_refresh(self):
        """Request an immediate UI refresh"""
        self.refresh_needed = True

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
        
        # Create windows - adjusted layout to include stats window
        message_height = max_y - 6
        message_win = curses.newwin(message_height, max_x, 0, 0)
        stats_win = curses.newwin(1, max_x, message_height, 0)
        puzzle_win = curses.newwin(2, max_x, message_height + 1, 0)
        input_win = curses.newwin(3, max_x, message_height + 3, 0)
        
        # Start input thread to prevent interruptions
        input_thread = threading.Thread(target=self._input_handler, args=(input_win,))
        input_thread.daemon = True
        input_thread.start()
        
        # Main display loop
        last_refresh = time.time()
        while self.running and self.player:
            current_time = time.time()

            # Update immediately if:
            # 1. Refresh is explicitly requested (from message handler)
            # 2. Regular refresh interval has passed (50ms)
            if self.refresh_needed or (current_time - last_refresh) >= 0.05:
                # Update windows
                self._draw_message_window(message_win)
                self._draw_stats_window(stats_win)
                self._draw_puzzle_window(puzzle_win)
                self._draw_input_window(input_win)
                
                self.refresh_needed = False
                last_refresh = current_time
                
            # Process any completed input
            with self.input_lock:
                if self.input_buffer:
                    user_input = self.input_buffer
                    self.input_buffer = ""
                    self._process_input(user_input)
                    self.refresh_needed = True  # Force refresh after input
            
            # Small sleep to prevent CPU hogging
            time.sleep(0.01)  # Reduced from 0.05 for more responsive updates
                
    def _input_handler(self, win):
        """Handle input in a separate thread to avoid interruptions"""
        while self.running:
            win.clear()
            win.border()
            win.addstr(0, 2, " Enter your solution ")
            win.addstr(1, 1, "Enter solution (or 'exit'/'quit'): ")
            win.refresh()
            
            curses.echo()
            try:
                user_input = win.getstr(1, 40, 50).decode('utf-8').strip()
                with self.input_lock:
                    self.input_buffer = user_input
            except:
                # Handle interrupts
                continue
            finally:
                curses.noecho()
                
    def disable_input_until_new_puzzle(self):
        """Disable input until a new puzzle is received"""
        self.input_disabled = True
        self.add_message("Input disabled until next puzzle")

    # And update _process_input to check this flag
    def _process_input(self, user_input):
        """Process input from the user"""
        # Always allow exit, even when input is disabled
        if user_input.lower() == 'exit':
            self.running = False
            self.player.exit_game()
            return
            
        # Block other commands if input is disabled
        if hasattr(self, 'input_disabled') and self.input_disabled:
            self.add_message("You surrendered. Waiting for next puzzle...")
            return
        
        if user_input.lower() == 'quit':
            self.player.surrender()
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
        
    def _draw_stats_window(self, win):
        """Draw the stats window with player counts"""
        win.clear()
        stats_text = f"Players: {self.stats['total_players']} | Correct: {self.stats['correct_answers']} | Surrendered: {self.stats['surrendered']}"
        win.addstr(0, 0, stats_text)
        win.refresh()
        
    def _draw_puzzle_window(self, win):
        """Draw the puzzle window"""
        win.clear()
        win.border()
        if self.player and self.player.current_puzzle:
            win.addstr(0, 2, " Current Puzzle ")
            try:
                # Handle different possible puzzle formats and ensure it's clean
                puzzle_str = ""
                if isinstance(self.player.current_puzzle, list):
                    puzzle_str = ", ".join(map(str, self.player.current_puzzle))
                else:
                    # Clean up any potential message contamination
                    puzzle_text = str(self.player.current_puzzle)
                    # Remove any non-puzzle content (messages that got appended)
                    if "GAME_STATUS" in puzzle_text:
                        puzzle_text = puzzle_text.split("GAME_STATUS")[0]
                    puzzle_str = puzzle_text.strip()
                    
                win.addstr(1, 1, puzzle_str)
            except Exception as e:
                win.addstr(1, 1, f"Error displaying puzzle: {e}")
                self.logger.error(f"Error displaying puzzle: {e}")
        else:
            win.addstr(0, 2, " Waiting for puzzle... ")
        win.refresh()
        
    def _draw_input_window(self, win):
        """Draw the input window border only, content handled by input thread"""
        win.border()
        win.refresh()
        
    def add_message(self, message):
        """Add a message to the list"""
        self.messages.append(message)
        if self.debug:
            self.logger.debug(f"Added message: {message}")
        
    def update_stats(self, total_players, correct_answers, surrendered):
        """Update game statistics"""
        self.stats["total_players"] = total_players
        self.stats["correct_answers"] = correct_answers 
        self.stats["surrendered"] = surrendered
        self.logger.debug(f"Stats updated: Players={total_players}, Correct={correct_answers}, Surrendered={surrendered}")
        self.refresh_needed = True  # Request refresh

    def show_puzzle(self, puzzle, *args):
        """Show the current puzzle to user
        
        Args:
            puzzle: The puzzle to display
        """
        try:                
            # Display in message area
            self.add_message(f"Current puzzle: {puzzle}")
            self.refresh_needed = True  # Request refresh
        except Exception as e:
            self.logger.error(f"Error showing puzzle: {e}")

    def show_new_puzzle(self, puzzle, *args):
        """Show a new puzzle to the user"""
        self.add_message(f"New puzzle: {puzzle}")
        # Reset input disabled flag when new puzzle arrives
        if hasattr(self, 'input_disabled') and self.input_disabled:
            self.input_disabled = False
            self.add_message("Input enabled for new puzzle")
        self.refresh_needed = True  # Request refresh
    
    def show_solution_result(self, is_correct, *args):
        if is_correct:
            self.add_message("Your solution was CORRECT!")
        else:
            self.add_message("Your solution was INCORRECT. Try again.")
        
    def show_message(self, message):
        self.add_message(message)
        
    def show_score_update(self, player_name, score, *args):
        self.add_message(f"Score update: {player_name} - {score}")
        
    def show_game_stats(self, total_players, correct_answers, surrendered):
        """Show updated game statistics
        
        Args:
            total_players (int): Number of players in game
            correct_answers (int): Number of correct answers
            surrendered (int): Number of surrendered players
        """
        self.logger.debug(f"Updating stats: Players={total_players}, Correct={correct_answers}, Surrendered={surrendered}")
        self.update_stats(total_players, correct_answers, surrendered)
        
        # Log the updated state
        self.add_message(f"Game stats updated: Players={total_players}, Correct={correct_answers}, Surrendered={surrendered}")      
    
    def get_user_input(self, prompt="Enter your solution: "):
        """Get input from user - compatibility method"""
        if not self.running:
            try:
                return input(prompt)
            except (EOFError, KeyboardInterrupt):
                return None
        return None