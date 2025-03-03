import asyncio
import logging
import os
from common.social import ServerClientMessages as SCM
from common.social import PlayerServerMessages as PSM
from common.social import MainServerMessages as SM
from common.communication import Communication
from puzzle.abstract_game_server import AbstractGameServer
from puzzle.logic import KryptoLogic

class ClassicServer(AbstractGameServer):
    """Implementation of a classic game server"""
    
    def __init__(self, name, port, puzzle_queue, message_queue, debug=False):
        super().__init__(name, port, puzzle_queue, message_queue, debug)
        self.mode = "classic"
        self.logger = logging.getLogger(f"ClassicServer-{name}")
        self.logger.setLevel(logging.DEBUG if debug else logging.INFO)
        
        # Player tracking
        self.player_usernames = {}  # Map client_id to username
        self.solved_count = 0
        self.total_players = 0
        
        # Initialize Communication
        self.comm = Communication(logger=self.logger)
        
        # Register command handlers
        self.register_command_handlers()
        
        self.logger.info(f"Classic server '{name}' initialized on port {port}")
    
    def register_command_handlers(self):
        """Register all command handlers with Communication"""
        handlers = {
            SCM.GET_PUZZLE: self.handle_get_puzzle,
            SCM.SUBMIT_SOLUTION: self.handle_submit_solution,
            PSM.PLAYER_SURRENDER: self.handle_player_surrender,
            PSM.PLAYER_EXIT: self.handle_player_exit
        }
        self.comm.define_all_commands(handlers)
    
    # Command handlers
    async def handle_get_puzzle(self, writer, *args):
        """Handle GET_PUZZLE command"""
        client_id = self.get_client_id_from_writer(writer)
        if self.current_puzzle:
            await self.send_message_to_client(client_id, f"{SCM.PUZZLE}|{self.current_puzzle}")
        else:
            await self.send_message_to_client(client_id, f"{SCM.ERROR}|No puzzle available")
    
    async def handle_submit_solution(self, writer, *args):
        """Handle SUBMIT_SOLUTION command"""
        client_id = self.get_client_id_from_writer(writer)
        
        if not args:
            await self.send_message_to_client(client_id, f"{SCM.ERROR}|Invalid solution format")
            return
            
        solution = str(args[0])
        
        # Store username if provided
        if len(args) > 1:
            self.player_usernames[client_id] = args[1]
            
        # Validate solution
        if self.validate_solution(solution):
            await self.send_message_to_client(client_id, f"{SCM.SOLUTION_CORRECT}")
            
            # Get next puzzle if solution is correct
            new_puzzle = self.check_after_solution(client_id, solution)
            if new_puzzle:
                # Broadcast new puzzle to all clients
                await self.broadcast_message(f"{SCM.NEW_PUZZLE}|{new_puzzle}")
        else:
            await self.send_message_to_client(client_id, f"{SCM.SOLUTION_INCORRECT}")
    
    async def handle_player_surrender(self, writer, *args):
        """Handle PLAYER_SURRENDER command"""
        client_id = self.get_client_id_from_writer(writer)
        
        if args:
            username = args[0]
            self.player_usernames[client_id] = username
            self.logger.info(f"Player {username} surrendered")
        else:
            self.logger.info(f"Player {client_id} surrendered")
        
        await self.send_message_to_client(client_id, f"{SCM.ERROR}|Puzzle surrendered")
    
    async def handle_player_exit(self, writer, *args):
        """Handle PLAYER_EXIT command"""
        client_id = self.get_client_id_from_writer(writer)
        
        if args:
            username = args[0]
            self.player_usernames[client_id] = username
        self.logger.info(f"Player {self.player_usernames.get(client_id, client_id)} exited")
        # No response needed as client is disconnecting
    
    def get_client_id_from_writer(self, writer):
        """Get client ID from writer object"""
        addr = writer.get_extra_info('peername')
        return f"{addr[0]}:{addr[1]}"
    
    def get_initial_puzzles(self):
        """Get initial puzzles for the classic mode - just one is enough"""
        try:
            if not self.puzzle_queue.empty():
                return [self.puzzle_queue.get()]
            return None
        except Exception as e:
            self.logger.error(f"Error getting initial puzzles: {e}")
            return None
            
    def check_after_solution(self, client_id, solution):
        """Check what happens after a solution is submitted in classic mode
        
        In classic mode, when a solution is correct, we get a new puzzle for everyone
        """
        self.solved_count += 1
        self.logger.info(f"Player {self.player_usernames.get(client_id, 'unknown')} solved the puzzle")
        
        # Get new puzzle
        new_puzzle = self.get_next_puzzle()
        if new_puzzle:
            self.logger.info(f"New puzzle set: {new_puzzle}")
            # Reset solved count for new puzzle
            self.solved_count = 0
            # Broadcast to all clients
            return new_puzzle
        else:
            self.logger.error("Failed to get next puzzle")
            return None
            
    async def handle_client_connection(self, reader, writer):
        """Handle a client connection"""
        addr = writer.get_extra_info('peername')
        client_id = f"{addr[0]}:{addr[1]}"
        
        self.logger.info(f"New client connected: {client_id}")
        self.total_players += 1
        
        # Add client to tracking
        self.clients[client_id] = {
            "reader": reader,
            "writer": writer,
            "last_activity": asyncio.get_event_loop().time()
        }
        
        try:
            # Send welcome message
            await self.send_message_to_client(client_id, f"{PSM.GREETING}|{self.name}")
            
            # Send current puzzle immediately
            if self.current_puzzle:
                await self.send_message_to_client(client_id, f"{SCM.PUZZLE}|{self.current_puzzle}")
            
            # Handle client messages
            while True:
                data = await reader.read(1024)
                if not data:
                    break
                    
                message = data.decode()
                self.logger.debug(f"Received from {client_id}: {message}")
                
                # Process message using Communication
                await self.comm.handle_async_command(message, writer)
                
        except Exception as e:
            self.logger.error(f"Error handling client {client_id}: {e}")
        finally:
            # Clean up
            writer.close()
            try:
                await writer.wait_closed()
            except:
                pass
                
            if client_id in self.clients:
                del self.clients[client_id]
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
        self.logger.debug(f"Broadcast to {len(self.clients)} clients: {message}")
            
    def validate_solution(self, solution:str):
        """Validate a solution against the current puzzle
        
        In a complete implementation, this would verify the solution against the puzzle.
        For now we'll check basic formatting and validity.
        """
        try:
            if not self.current_puzzle:
                return False
            
            # Validate solution using logic module
            return KryptoLogic.verify_solution(solution, self.current_puzzle[-1])
            
        except Exception as e:
            self.logger.error(f"Error validating solution: {e}")
            return False
