import logging
import asyncio
from common.social import ServerClientMessages as SCM
from puzzle.abstract_game_server import AbstractGameServer

class ClassicServer(AbstractGameServer):
    """Implementation of a classic game server"""
    
    def __init__(self, name, port, puzzle_queue, message_queue, debug=False):
        super().__init__(name, port, puzzle_queue, message_queue, debug)
        self.mode = "classic"
        self.logger = logging.getLogger(f"ClassicServer-{name}")
        self.logger.setLevel(logging.DEBUG if debug else logging.INFO)
        self.logger.info(f"Classic server '{name}' initialized on port {port}")
        
    def get_initial_puzzles(self):
        """Get initial puzzles for the classic mode - just one is enough"""
        try:
            if not self.puzzle_queue.empty():
                return [self.puzzle_queue.get()]
            return None
        except Exception as e:
            self.logger.error(f"Error getting initial puzzles: {e}")
            return None
            
    def check_after_solution(self, solution):
        """Check what happens after a solution is submitted in classic mode"""
        # In classic mode, just get a new puzzle
        return self.get_next_puzzle()
        
    async def process_client_message(self, client_id, message):
        """Process messages from clients in classic mode"""
        try:
            parts = message.split('|')
            if not parts:
                return
                
            command = parts[0]
            args = parts[1:] if len(parts) > 1 else []
            
            if command == SCM.GET_PUZZLE:
                # Send current puzzle to client
                if self.current_puzzle:
                    await self.send_message_to_client(client_id, f"{SCM.PUZZLE}|{self.current_puzzle}")
                else:
                    await self.send_message_to_client(client_id, f"{SCM.ERROR}|No puzzle available")
                    
            elif command == SCM.SUBMIT_SOLUTION:
                # Process solution submission
                if len(args) < 1:
                    await self.send_message_to_client(client_id, f"{SCM.ERROR}|Invalid solution format")
                    return
                    
                solution = args[0]
                # Validate solution (simplified)
                if self.validate_solution(solution):
                    await self.send_message_to_client(client_id, f"{SCM.SOLUTION_CORRECT}")
                    
                    # Get next puzzle
                    new_puzzle = self.check_after_solution(solution)
                    if new_puzzle:
                        # Broadcast new puzzle to all clients
                        await self.broadcast_message(f"{SCM.NEW_PUZZLE}|{new_puzzle}")
                else:
                    await self.send_message_to_client(client_id, f"{SCM.SOLUTION_INCORRECT}")
                    
            # Add more commands as needed
                
        except Exception as e:
            self.logger.error(f"Error processing message from {client_id}: {e}")
            
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
