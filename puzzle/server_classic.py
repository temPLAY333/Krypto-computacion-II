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
    
    def __init__(self, name, port, puzzle_queue, message_queue, max_players=8, debug=False):
        super().__init__(name, port, puzzle_queue, message_queue, debug)
        self.mode = "classic"
        self.logger = logging.getLogger(f"ClassicServer-{name}")
        self.logger.setLevel(logging.DEBUG if debug else logging.INFO)
        
        # Player tracking
        self.player_usernames = {}  # Map client_id to username
        self.solved_count = 0
        self.total_players = 0
        self.max_players = max_players
        
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
            await self.comm.send_message_async(writer, f"{SCM.PUZZLE}|{self.current_puzzle}\n")
        else:
            await self.comm.send_message_async(writer, f"{SCM.ERROR}|No puzzle available\n")
    
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
            
            await asyncio.sleep(0.5)
            if not await self.check_puzzle_completion_status():
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
        await asyncio.sleep(0.5)
        if not await self.check_puzzle_completion_status():
            await self.broadcast_game_stats()
        

    async def handle_player_exit(self, writer, *args):
        """Handle PLAYER_EXIT command"""
        client_id = self.get_client_id_from_writer(writer)
        
        if args:
            username = args[0]
            self.player_usernames[client_id] = username
        
        self.logger.info(f"Player {self.player_usernames.get(client_id, client_id)} exited")
        
        # Mark client as disconnected to prevent further communication attempts
        if client_id in self.clients:
            self.clients[client_id]["disconnected"] = True
            
            # Update stats after player exit but don't try to send to the exiting client
            disconnected_client = client_id
            active_clients = {cid: data for cid, data in self.clients.items() 
                            if cid != disconnected_client and not data.get("disconnected", False)}
                            
            # Remove client from tracking
            del self.clients[client_id]
            
            # Broadcast updated stats to remaining clients only
            if len(active_clients) > 0:
                await self.broadcast_game_stats()
                await asyncio.sleep(0.5)

                await self.check_puzzle_completion_status()
            else:
                self.logger.info("All players have disconnected")
                self.message_queue.put(f"{SM.KILL_SERVER}|{os.getpid()}")
        return
    
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
            
    def check_after_solution(self, client_id, solution): # Borrar a la brevedad
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
    
    async def check_puzzle_completion_status(self):
        """Check if all players have completed the current puzzle and send new if needed"""
        # Count only active clients
        active_clients = {cid: data for cid, data in self.clients.items() 
                        if not data.get("disconnected", False)}
        total_players = len(active_clients)
        
        # Check if all players completed the puzzle
        if total_players > 0 and total_players <= self.stats["correct_answers"] + self.stats["surrendered"]:
            # Get new puzzle
            new_puzzle = self.get_next_puzzle()
            if new_puzzle:
                self.logger.info(f"All players completed the puzzle. Sending new puzzle: {new_puzzle}")
                self.current_puzzle = new_puzzle
                
                # Reset stats for new puzzle
                self.stats["correct_answers"] = 0
                self.stats["surrendered"] = 0
                
                # Send new puzzle to all clients
                await self.broadcast_message(f"{SCM.NEW_PUZZLE}|{new_puzzle}\n")
                
                return True  # Puzzle was updated
        
        return False  # No need for a new puzzle
            
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
            await self.comm.send_message_async(writer, f"{PSM.GREETING}|{self.name}\n")
            
            # Send current puzzle immediately
            if self.current_puzzle:
                await self.comm.send_message_async(writer, f"{SCM.PUZZLE}|{self.current_puzzle}\n")
            
            # Broadcast updated game stats after new client connects
            await self.broadcast_game_stats()
            
            # Handle client messages
            while client_id in self.clients and not self.clients[client_id].get("disconnected", False):
                try:
                    data = await reader.read(1024)
                    if not data:
                        # Client disconnected
                        break
                        
                    message = data.decode()
                    self.logger.debug(f"Received from {client_id}: {message}")
                    
                    # Process message using Communication
                    await self.comm.handle_async_command(message, writer)
                except ConnectionError:
                    # Explicit handling for connection errors
                    self.logger.debug(f"Connection lost with {client_id}")
                
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
            message = f"{SCM.GAME_STATUS}|{total_players}|{correct_answers}|{surrendered}\n"
            
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
