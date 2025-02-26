import curses
import logging
from client.player_interface import PlayerInterface

class ClassicPlayerInterface(PlayerInterface):
    """Interface for classic game mode"""
    
    def __init__(self):
        super().__init__()
        self.current_puzzle = "Waiting for puzzle..."
        self.result = None
        self.game_state = {
            "solved": 0,
            "abandoned": 0,
            "players": 0
        }
    
    def run_interface(self, stdscr):
        """Run the classic mode interface"""
        # Set up curses
        curses.curs_set(1)
        curses.use_default_colors()
        stdscr.clear()
        stdscr.refresh()
        
        # Create windows
        max_y, max_x = stdscr.getmaxyx()
        header_win = curses.newwin(3, max_x, 0, 0)
        puzzle_win = curses.newwin(5, max_x, 3, 0)
        message_win = curses.newwin(max_y - 11, max_x, 8, 0)
        input_win = curses.newwin(3, max_x, max_y - 3, 0)
        
        # Main interface loop
        while self.running:
            # Update header
            header_win.clear()
            header_win.border()
            header_win.addstr(1, 2, f"Player: {self.player.username} | "
                             f"Players: {self.game_state['players']} | "
                             f"Solved: {self.game_state['solved']} | "
                             f"Abandoned: {self.game_state['abandoned']}")
            header_win.refresh()
            
            # Update puzzle display
            puzzle_win.clear()
            puzzle_win.border()
            puzzle_win.addstr(1, 2, "Current Puzzle:")
            puzzle_win.addstr(2, 2, self.current_puzzle)
            if self.result:
                puzzle_win.addstr(3, 2, f"Result: {self.result}")
            puzzle_win.refresh()
            
            # Update message display
            message_win.clear()
            message_win.border()
            message_win.addstr(1, 2, "Messages:")
            for i, msg in enumerate(self.messages[-20:], 1):
                if i >= message_win.getmaxyx()[0] - 3:
                    break
                message_win.addstr(i + 1, 2, msg[:max_x - 4])
            message_win.refresh()
            
            # Update input window
            input_win.clear()
            input_win.border()
            input_win.addstr(1, 2, "Enter solution (or '/quit' to surrender, '/exit' to leave): ")
            input_win.refresh()
            
            # Get user input
            curses.echo()
            user_input = input_win.getstr(1, 60, max_x - 62).decode('utf-8').strip()
            curses.noecho()
            
            # Process input
            if not self.running:
                break
                
            if user_input.lower() == '/exit':
                self.display_message("Exiting game...")
                self.player.exit_game()
                break
            elif user_input.lower() == '/quit':
                self.display_message("Surrendering current puzzle...")
                self.player.surrender()
            elif user_input:
                self.display_message(f"Submitting solution: {user_input}")
                self.player.submit_solution(user_input)
    
    def update_puzzle(self, puzzle):
        """Update the current puzzle"""
        self.current_puzzle = puzzle
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
        
        # Only display a message if something significant changed
        if (old_state["players"] != state["players"] or 
            old_state["solved"] != state["solved"] or
            old_state["abandoned"] != state["abandoned"]):
            self.display_message(
                f"Game state updated: "
                f"{state['solved']}/{state['players']} solved, "
                f"{state['abandoned']}/{state['players']} abandoned"
            )
