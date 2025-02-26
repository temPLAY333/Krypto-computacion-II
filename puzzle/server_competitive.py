import time
import logging

from puzzle.logic import KryptoLogic
from puzzle.game_server import GameServer
from common.social import PlayerServerMessages as PM
from common.social import MainServerMessages as SM

class CompetitiveServer(GameServer):
    """Competitive game server with additional rules
    
    Features:
    - Supports exactly 2 players
    - Set number of puzzles agreed by both players
    - Players cannot surrender (but can abandon)
    - Gets all puzzles at once from the queue
    """
    
    def __init__(self, name, puzzle_queue, message_queue, port=5001, puzzle_count=5):
        # Override max_players to be exactly 2 for competitive mode
        super().__init__(name, puzzle_queue, message_queue, port, max_players=2)
        
        # Competitive specific settings
        self.puzzle_count = puzzle_count
        self.puzzles = []
        self.current_puzzle_index = 0
        self.player_scores = {}  # Track scores per player
        self.player_status = {}  # Track completion status per player
        self.start_time = None
        self.game_completed = False
    
    def get_initial_puzzles(self):
        """Get all puzzles at once for competitive mode"""
        try:
            # Get all puzzles upfront
            self.puzzles = []
            for _ in range(self.puzzle_count):
                puzzle = self.puzzle_queue.get(timeout=5)
                self.puzzles.append(puzzle)
            
            # Set the first puzzle as current
            self.puzzle = self.puzzles[self.current_puzzle_index]
            self.message_queue.put(f"{SM.OK}|{self.name}")
            self.logger.info(f"Got {len(self.puzzles)} puzzles for competitive mode")
        except Exception as e:
            self.logger.error(f"Error getting competitive puzzles: {e}")
            raise
    
    def handle_new_connection(self, client_socket, client_address):
        """Override to track player scores and status"""
        # Use parent implementation first
        super().handle_new_connection(client_socket, client_address)
        
        # Initialize player tracking (using socket as player identifier)
        player_id = str(id(client_socket))
        self.player_scores[player_id] = 0
        self.player_status[player_id] = {"current_puzzle": 0, "completed": False}
        
        # Start the game if we have two players
        if self.players == 2 and not self.start_time:
            self.start_time = time.time()
            self.broadcast(f"{PM.GAME_START}|{self.puzzle_count}")
    
    def check_after_solution(self, client_socket):
        """Check if player has completed all puzzles"""
        player_id = str(id(client_socket))
        
        # Update player's score and status
        self.player_scores[player_id] += 1
        current_score = self.player_scores[player_id]
        
        # Check if this player has completed all puzzles
        if current_score >= self.puzzle_count:
            self.player_status[player_id]["completed"] = True
            self.communication.send_message(client_socket, f"{PM.GAME_COMPLETED}|{current_score}")
            
            # Check if game is over
            if self.check_game_completed():
                self.end_game()
        else:
            # Move this player to their next puzzle
            next_puzzle_index = current_score
            if next_puzzle_index < len(self.puzzles):
                next_puzzle = self.puzzles[next_puzzle_index]
                self.communication.send_message(client_socket, f"{PM.NEW_PUZZLE}|{next_puzzle}")
    
    def check_game_completed(self):
        """Check if the competitive game is completed"""
        # Game is completed when any player finishes all puzzles or all players have left
        if self.players == 0:
            return True
            
        for status in self.player_status.values():
            if status["completed"]:
                return True
                
        return False
    
    def end_game(self):
        """End the competitive game and announce results"""
        if self.game_completed:
            return
            
        self.game_completed = True
        game_duration = time.time() - self.start_time if self.start_time else 0
        
        # Find winner
        winner_id = None
        highest_score = -1
        
        for player_id, score in self.player_scores.items():
            if score > highest_score:
                highest_score = score
                winner_id = player_id
        
        # Announce results
        results = f"{PM.GAME_RESULTS}|{game_duration:.2f}"
        for player_id, score in self.player_scores.items():
            results += f"|{player_id},{score}"
            
        self.broadcast(results)
        self.message_queue.put(f"{SM.GAME_COMPLETED}|{self.name}|{game_duration:.2f}")
    
    def cleanup_client(self, client_socket):
        """Override to handle player leaving competitive game"""
        player_id = str(id(client_socket))
        
        # Mark this player's puzzles as abandoned
        self.abandoned += 1
        
        # Call parent implementation
        super().cleanup_client(client_socket)
        
        # Check if game should end
        if self.check_game_completed():
            self.end_game()
