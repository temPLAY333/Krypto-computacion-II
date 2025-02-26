import curses
import time
import logging
from client.player_interface import PlayerInterface
from common.social import PlayerServerMessages as SM

class CompetitivePlayerInterface(PlayerInterface):
    """Interface for competitive game mode"""
    
    def __init__(self):
        super().__init__()
        self.current_puzzle = "Waiting for puzzle..."
        self.result = None
        self.game_state = {
            "solved": 0,
            "abandoned": 0,
            "players": 0
        }
        self.puzzle_count = 0
        self.current_puzzle_num = 0
        self.start_time = None
        self.scores = {}
        self.game_completed = False
    
    def run_interface(self, stdscr):
        """Run the competitive mode interface"""
        # Set up curses
        curses.curs_set(1)
        curses.use_default_colors()
        for i in range(1, 8):
            curses.init_pair(i, i, -1)
        stdscr.clear()
        stdscr.refresh()
        
        # Create windows
        max_y, max_x = stdscr.getmaxyx()
        header_win = curses.newwin(3, max_x, 0, 0)
        status_win = curses.newwin(3, max_x, 3, 0)
        puzzle_win = curses.newwin(5, max_x, 6, 0)
        message_win = curses.newwin(max_y - 14, max_x, 11, 0)
        input_win = curses.newwin(3, max_x, max_y - 3, 0)
        
        # Main interface loop
        while self.running:
            # Update header
            header_win.clear()
            header_win.border()
            header_win.addstr(1, 2, f"Player: {self.player.username} | "
                             f"Competitive Mode | Players: {self.game_state['players']}")
            header_win.refresh()
            
            # Update status window
            status_win.clear()
            status_win.border()
            if self.puzzle_count > 0:
                progress = f"Puzzle {self.current_puzzle_num}/{self.puzzle_count}"
                status_win.addstr(1, 2, progress, curses.color_pair(2))
                
                # Show elapsed time if game has started
                if self.start_time:
                    elapsed = time.time() - self.start_time
                    status_win.addstr(1, len(progress) + 4, 
                                      f"Time: {int(elapsed // 60)}:{int(elapsed % 60):02d}", 
                                      curses.color_pair(3))
            else:
                status_win.addstr(1, 2, "Waiting for game to start...", curses.color_pair(1))
            status_win.refresh()
            
            # Update puzzle display
            puzzle_win.clear()
            puzzle_win.border()
            puzzle_win.addstr(1, 2, "Current Puzzle:", curses.A_BOLD)
            puzzle_win.addstr(2, 2, self.current_puzzle)
            if self.result:
                if "Correcto" in self.result:
                    puzzle_win.addstr(3, 2, f"Result: {self.result}", curses.color_pair(2))
                else:
                    puzzle_win.addstr(3, 2, f"Result: {self.result}", curses.color_pair(1))
            puzzle_win.refresh()
            
            # Update message display
            message_win.clear()
            message_win.border()
            message_win.addstr(1, 2, "Messages:", curses.A_BOLD)
            for i, msg in enumerate(self.messages[-20:], 1):
                if i >= message_win.getmaxyx()[0] - 3:
                    break
                message_win.addstr(i + 1, 2, msg[:max_x - 4])
            message_win.refresh()
            
            # Update input window
            input_win.clear()
            input_win.border()
            
            # In competitive mode, no surrender option
            input_win.addstr(1, 2, "Enter solution (or '/exit' to leave): ")
            input_win.refresh()
            
            # Get user input
            curses.echo()
            user_input = input_win.getstr(1, 40, max_x - 42).decode('utf-8').strip()
            curses.noecho()
            
            # Process input
            if not self.running:
                break
                
            if user_input.lower() == '/exit':
                self.display_message("Exiting game...")
                self.player.exit_game()
                break
            elif user_input:
                self.display_message(f"Submitting solution: {user_input}")
                self.player.submit_solution(user_input)
    
    def update_puzzle(self, puzzle):
        """Update the current puzzle"""
        self.current_puzzle = puzzle
        self.current_puzzle_num += 1
        self.result = None  # Clear previous result
        self.display_message(f"New puzzle received: {puzzle}")
    
    def display_result(self, result):
        """Display a puzzle result"""
        self.result = result
        self.display_message(f"Puzzle result: {result}")
    
    def update_game_state(self, state):
        """Update the game state display"""
        old_state = self.game_state.copy()
        self.game_state = state
        
        # Only display a message if something changed
        if old_state != state:
            self.display_message(
                f"Game state updated: {state['players']} players in game"
            )
    
    def handle_game_start(self, puzzle_count):
        """Handle game start message"""
        self.puzzle_count = int(puzzle_count)
        self.current_puzzle_num = 1
        self.start_time = time.time()
        self.display_message(f"Game started with {puzzle_count} puzzles!")
    
    def handle_game_completed(self, score):
        """Handle game completion message"""
        self.game_completed = True
        self.display_message(f"You completed all puzzles! Your score: {score}")
    
    def handle_game_results(self, duration, *player_scores):
        """Handle game results message"""
        self.display_message(f"Game finished! Duration: {duration} seconds")
        
        for player_data in player_scores:
            player_id, score = player_data.split(",")
            self.display_message(f"Player {player_id}: {score} puzzles solved")
