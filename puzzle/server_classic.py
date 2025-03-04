import asyncio
import logging
import os
import time
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
        
        # Add game stats tracking
        self.stats = {
            "correct_answers": 0,
            "surrendered": 0
        }
        
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
            await self.comm.send_message_async(writer, f"{SCM.PUZZLE}|{self.current_puzzle}")
        else:
            await self.comm.send_message_async(writer, f"{SCM.ERROR}|No puzzle available")
    
    async def handle_submit_solution(self, writer, *args):
        """Handle SUBMIT_SOLUTION command"""
        client_id = self.get_client_id_from_writer(writer)
        
        if not args:
            await self.comm.send_message_async(writer, f"{SCM.ERROR}|Invalid solution format\n")
            return
            
        solution = str(args[0])
        
        # Store username if provided
        if len(args) > 1:
            self.player_usernames[client_id] = args[1]
            
        # Validate solution
        if self.validate_solution(solution):
            # First send the correct solution response
            await self.comm.send_message_async(writer, f"{SCM.SOLUTION_CORRECT}\n")
            self.logger.info(f"Player {self.player_usernames.get(client_id, client_id)} answered correctly")
            
            # Update stats
            self.stats["correct_answers"] += 1
            
            # Send updated stats
            await self.broadcast_game_stats()
            
            # Check if we need a new puzzle
            total_players = len(self.clients)
            if total_players > 0 and total_players <= self.stats["correct_answers"] + self.stats["surrendered"]:
                # Get new puzzle
                new_puzzle = self.get_next_puzzle()
                if new_puzzle:
                    self.logger.info(f"All players completed the puzzle. Sending new puzzle: {new_puzzle}")
                    self.current_puzzle = new_puzzle
                    # Reset stats for new puzzle
                    self.stats["correct_answers"] = 0
                    self.stats["surrendered"] = 0
                    
                    # THIS LINE WAS MISSING - It gets the puzzle but doesn't send it
                    await self.broadcast_message(f"{SCM.NEW_PUZZLE}|{new_puzzle}\n")
                    
                    # Send updated stats again
                    await asyncio.sleep(0.1)  # Small delay for message separation
                    await self.broadcast_game_stats()
        else:
            await self.comm.send_message_async(writer, f"{SCM.SOLUTION_INCORRECT}\n")

    async def handle_player_surrender(self, writer, *args):
        """Handle PLAYER_SURRENDER command"""
        client_id = self.get_client_id_from_writer(writer)
        
        if args:
            username = args[0]
            self.player_usernames[client_id] = username
            self.logger.info(f"Player {username} surrendered")
        else:
            self.logger.info(f"Player {client_id} surrendered")
        
        # Update stats for surrender
        self.stats["surrendered"] += 1
        
        # Send surrender acknowledgment
        await self.comm.send_message_async(writer, f"{SCM.SURRENDER_STATUS}|disable_input\n")
        
        # Broadcast updated stats
        await self.broadcast_game_stats()
        
        # Check if we need a new puzzle - THIS WAS MISSING!
        total_players = len(self.clients)
        if total_players > 0 and total_players <= self.stats["correct_answers"] + self.stats["surrendered"]:
            # Add a small delay for message separation
            await asyncio.sleep(0.1)
            
            # Get and send new puzzle
            new_puzzle = self.get_next_puzzle()
            if new_puzzle:
                self.logger.info(f"All players surrendered or completed. New puzzle: {new_puzzle}")
                self.current_puzzle = new_puzzle
                # Reset stats for new puzzle
                self.stats["correct_answers"] = 0
                self.stats["surrendered"] = 0
                
                # Send new puzzle to all clients
                await self.broadcast_message(f"{SCM.NEW_PUZZLE}|{new_puzzle}")
                
                # Wait a moment then send updated stats again
                await asyncio.sleep(0.1)
                await self.broadcast_game_stats()

    async def handle_player_exit(self, writer, *args):
        """Handle PLAYER_EXIT command"""
        client_id = self.get_client_id_from_writer(writer)
        
        if args:
            username = args[0]
            self.player_usernames[client_id] = username
        
        self.logger.info(f"Player {self.player_usernames.get(client_id, client_id)} exited")
        
        # Clean up client immediately to prevent "forced disconnection" errors
        if client_id in self.clients:
            del self.clients[client_id]
            # Update stats after player exit
            await self.broadcast_game_stats()
    
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
        
        # Add client to tracking
        self.clients[client_id] = {
            "reader": reader,
            "writer": writer,
            "last_activity": asyncio.get_event_loop().time()
        }
        
        try:
            # Send welcome message
            await self.comm.send_message_async(writer, f"{PSM.GREETING}|{self.name}")
            
            # Send current puzzle immediately
            if self.current_puzzle:
                await self.comm.send_message_async(writer, f"{SCM.PUZZLE}|{self.current_puzzle}")
            
            # Broadcast updated game stats after new client connects
            await self.broadcast_game_stats()
            
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
                # Broadcast updated stats after client disconnects
                await self.broadcast_game_stats()
    
    async def broadcast_game_stats(self):
        """Broadcast current game statistics to all connected clients"""
        try:
            # Count only clients that are still connected
            active_clients = {cid: data for cid, data in self.clients.items() 
                            if not data.get("disconnected", False)}
            
            total_players = len(active_clients)
            correct_answers = self.stats["correct_answers"]
            surrendered = self.stats["surrendered"]
            
            # Format the game status message
            message = f"{SCM.GAME_STATUS}|{total_players}|{correct_answers}|{surrendered}"
            
            self.logger.debug(f"Broadcasting stats: Players={total_players}, Correct={correct_answers}, Surrendered={surrendered}")
            
            # Broadcast to all clients
            await self.broadcast_message(message)
            
            # Log if puzzles should reset but aren't
            if total_players > 0 and total_players <= correct_answers + surrendered:
                self.logger.warning(f"All players ({total_players}) have completed the puzzle "
                                f"({correct_answers} correct, {surrendered} surrendered). "
                                f"A new puzzle should be sent.")
                
        except Exception as e:
            self.logger.error(f"Failed to broadcast game stats: {e}")
            
    async def broadcast_message(self, message):
        """Send a message to all connected clients"""
        try:
            self.logger.debug(f"Broadcasting: {message}")
            
            for client_id, client_data in list(self.clients.items()):
                writer = client_data["writer"]
                try:
                    writer.write(message.encode())
                    await writer.drain()
                except Exception as e:
                    self.logger.error(f"Failed to send to client {client_id}: {e}")
                    # Mark client for removal
                    del self.clients[client_id]
                    
            self.logger.debug(f"Broadcast complete to {len(self.clients)} clients")
        except Exception as e:
            self.logger.error(f"Broadcast error: {e}")
            
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
