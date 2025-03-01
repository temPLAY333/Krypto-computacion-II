import time
import logging
from queue import Queue

from puzzle.logic import KryptoLogic
from puzzle.game_server import GameServer
from common.social import PlayerServerMessages as PM
from common.social import MainServerMessages as SM

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

class ClassicServer(GameServer):
    """Classic game server implementation
    
    Features:
    - Supports 1 to 8 players
    - Provides puzzles one at a time
    - Players can surrender
    - Gets puzzles one at a time from the queue
    """
    
    def __init__(self, name:str, puzzle_queue:Queue, message_queue:Queue, port:int, max_players:int):
        super().__init__(name, puzzle_queue, message_queue, port, max_players)
        
        # Register surrender command (only available in classic mode)
        self.communication.register_command(PM.PLAYER_SURRENDER, self.handle_player_rend)
    
    def get_initial_puzzles(self):
        """Get the first puzzle from queue"""
        try:
            self.puzzle = self.puzzle_queue.get(timeout=5)
            self.message_queue.put(f"{SM.OK}|{self.name}")
            self.logger.info(f"Initial puzzle obtained: {self.puzzle}")
        except Exception as e:
            self.logger.error(f"Error getting initial puzzle: {e}")
            raise
    
    def check_after_solution(self, client_socket):
        """Check if all players have completed the puzzle"""
        if self.check_round_completed():
            self.get_new_puzzle()
    
    def check_round_completed(self):
        """Check if the current round is completed"""
        return self.solved + self.abandoned >= self.players and self.players > 0
    
    def get_new_puzzle(self):
        """Get a new puzzle from the puzzle queue"""
        try:
            self.puzzle = self.puzzle_queue.get(timeout=5)
            self.message_queue.put(f"{SM.OK}|{self.name}")
            
            # Reset round state
            self.solved = 0
            self.abandoned = 0
            
            # Send new puzzle to all clients
            self.broadcast(f"{PM.NEW_PUZZLE}|{self.puzzle}")
            self.logger.info(f"New puzzle obtained: {self.puzzle}")
        except Exception as e:
            self.logger.error(f"Error getting new puzzle: {e}")
            self.message_queue.put(f"{SM.ERROR}|{self.name}|Failed to get new puzzle")
    
    def handle_player_rend(self, client_socket):
        """Handle a player surrendering"""
        self.logger.info("Player surrendered")
        self.abandoned += 1
        self.communication.send_message(client_socket, f"{PM.PUZZLE_RESULT}|You gave up")
        
        if self.check_round_completed():
            self.get_new_puzzle()
            
        self.broadcast_game_state()
