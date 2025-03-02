import logging
import asyncio
import time
from common.social import ServerClientMessages as SCM
from puzzle.abstract_game_server import AbstractGameServer

class CompetitiveServer(AbstractGameServer):
    """Implementation of a competitive game server"""
    
    def __init__(self, name, port, puzzle_queue, message_queue):
        super().__init__(name, port, puzzle_queue, message_queue)
        self.mode = "competitive"
        self.logger = logging.getLogger(f"CompetitiveServer-{name}")
        self.logger.info(f"Competitive server '{name}' initialized on port {port}")
        
        # Competitive-specific attributes
        self.scores = {}  # Track player scores
        self.round_start_time = None
        self.round_duration = 60  # 60 seconds per round
        self.current_round = 0
        
    def get_initial_puzzles(self):
        """Get initial puzzles for competitive mode - we need several"""
        try:
            puzzles = []
            # Try to get 5 puzzles
            for _ in range(5):
                if not self.puzzle_queue.empty():
                    puzzles.append(self.puzzle_queue.get())
                    
            return puzzles if puzzles else None
        except Exception as e:
            self.logger.error(f"Error getting initial puzzles: {e}")
            return None
            
    def check_after_solution(self, solution):
        """Check what happens after a solution in competitive mode"""
        # In competitive, we might wait for round to end
        # For now, just get the next puzzle
        return self.get_next_puzzle()
        
    async def process_client_message(self, client_id, message):
        """Process messages from clients in competitive mode"""
        try:
            parts = message.split('|')
            if not parts:
                return
                
            command = parts[0]
            args = parts[1:] if len(parts) > 1 else []
            
            if command == SCM.GET_PUZZLE:
                # Send current puzzle to client with round info
                if self.current_puzzle:
                    time_left = self.get_round_time_left()
                    await self.send_message_to_client(
                        client_id, 
                        f"{SCM.PUZZLE}|{self.current_puzzle}|{self.current_round}|{time_left}"
                    )
                else:
                    await self.send_message_to_client(client_id, f"{SCM.ERROR}|No puzzle available")
                    
            elif command == SCM.SUBMIT_SOLUTION:
                # Process solution submission with scoring
                if len(args) < 2:
                    await self.send_message_to_client(client_id, f"{SCM.ERROR}|Invalid solution format")
                    return
                    
                solution = args[0]
                player_name = args[1]
                
                # Initialize player score if needed
                if player_name not in self.scores:
                    self.scores[player_name] = 0
                
                # Validate solution
                if self.validate_solution(solution):
                    # Award points based on time left
                    time_left = self.get_round_time_left()
                    points = max(1, int(time_left / 5))  # More points for faster solutions
                    self.scores[player_name] += points
                    
                    await self.send_message_to_client(
                        client_id, 
                        f"{SCM.SOLUTION_CORRECT}|{points}|{self.scores[player_name]}"
                    )
                    
                    # Broadcast updated scores
                    await self.broadcast_message(
                        f"{SCM.SCORE_UPDATE}|{player_name}|{self.scores[player_name]}"
                    )
                    
                    # Move to next puzzle if we're the first to solve
                    if self.should_advance_puzzle():
                        new_puzzle = self.check_after_solution(solution)
                        if new_puzzle:
                            self.start_new_round()
                            await self.broadcast_message(
                                f"{SCM.NEW_PUZZLE}|{new_puzzle}|{self.current_round}|{self.round_duration}"
                            )
                else:
                    # Penalty for wrong solution
                    self.scores[player_name] = max(0, self.scores[player_name] - 1)
                    await self.send_message_to_client(
                        client_id, 
                        f"{SCM.SOLUTION_INCORRECT}|{self.scores[player_name]}"
                    )
                
            # Add more commands as needed
                
        except Exception as e:
            self.logger.error(f"Error processing message from {client_id}: {e}")
    
    def start_new_round(self):
        """Start a new round"""
        self.current_round += 1
        self.round_start_time = time.time()
        self.logger.info(f"Starting round {self.current_round}")
        
    def get_round_time_left(self):
        """Get time left in current round"""
        if not self.round_start_time:
            self.round_start_time = time.time()
            
        elapsed = time.time() - self.round_start_time
        return max(0, self.round_duration - elapsed)
        
    def should_advance_puzzle(self):
        """Check if we should advance to the next puzzle"""
        # In this implementation, advance if someone solves it
        return True
            
    async def send_message_to_client(self, client_id, message):
        """Send a message to a specific client"""
        if client_id in self.clients:
            writer = self.clients[client_id]["writer"]
            writer.write(message.encode())
            await writer.drain()
            self.logger.debug(f"Sent to {client_id}: {message}")
            
    async def broadcast_message(self, message):
        """Send a message to all connected clients"""
        for client_id, client_data in self.clients.items():
            writer = client_data["writer"]
            writer.write(message.encode())
            await writer.drain()
        self.logger.debug(f"Broadcast: {message}")
            
    def validate_solution(self, solution):
        """Validate a solution (simplified implementation)"""
        # In a real implementation, this would check the solution against the puzzle
        # For now, we'll just return True for testing
        return True
