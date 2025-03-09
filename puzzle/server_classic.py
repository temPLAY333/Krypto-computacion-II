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
        
         # Estructura unificada de tracking de jugadores
        self.players = {}  # {client_id: {"username": name, "state": None|"correct"|"surrendered"}}
        self.max_players = max_players
        
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
        
        # Inicializar datos del jugador si no existen
        if client_id not in self.players:
            self.players[client_id] = {"username": client_id, "state": None}
        
        # Actualizar username si se proporcionó
        if len(args) > 1:
            self.players[client_id]["username"] = args[1]
        
        username = self.players[client_id]["username"]
        
        # Verificar si el jugador ya ha contribuido al puzzle actual
        if self.players[client_id]["state"] is not None:
            self.logger.warning(f"Player {username} already submitted for this puzzle: {self.players[client_id]['state']}")
            await self.comm.send_message_async(writer, f"{SCM.SOLUTION_INCORRECT}|You already submitted for this puzzle\n")
            return
                
        # Validar solución
        if self.validate_solution(solution):
            # Enviar respuesta de correcto
            await self.comm.send_message_async(writer, f"{SCM.SOLUTION_CORRECT}\n")
            self.logger.info(f"Player {username} answered correctly")
            
            # Actualizar estado del jugador
            self.players[client_id]["state"] = "correct"
            
            # Verificar estado del juego
            await asyncio.sleep(0.5)
            if not await self.check_puzzle_completion_status():
                await self.broadcast_game_stats()
        else:
            await self.comm.send_message_async(writer, f"{SCM.SOLUTION_INCORRECT}\n")

    async def handle_player_surrender(self, writer, *args):
        """Handle PLAYER_SURRENDER command"""
        client_id = self.get_client_id_from_writer(writer)
        
        # Inicializar datos del jugador si no existen
        if client_id not in self.players:
            self.players[client_id] = {"username": client_id, "state": None}
        
        # Actualizar username si se proporcionó
        if args:
            self.players[client_id]["username"] = args[0]
        
        username = self.players[client_id]["username"]
        
        # Verificar si el jugador ya ha contribuido al puzzle actual
        if self.players[client_id]["state"] is not None:
            self.logger.warning(f"Player {username} already submitted for this puzzle: {self.players[client_id]['state']}")
            await self.comm.send_message_async(writer, f"{SCM.SURRENDER_STATUS}|You already submitted for this puzzle\n")
            return
        
        self.logger.info(f"Player {username} surrendered")
        
        # Actualizar estado del jugador
        self.players[client_id]["state"] = "surrendered"
        
        # Enviar confirmación de rendición
        await self.comm.send_message_async(writer, f"{SCM.SURRENDER_STATUS}|disable_input\n")
        
        # Verificar estado del juego
        await asyncio.sleep(0.5)
        if not await self.check_puzzle_completion_status():
            await self.broadcast_game_stats()
        

    async def handle_player_exit(self, writer, *args):
        """Handle PLAYER_EXIT command"""
        client_id = self.get_client_id_from_writer(writer)
        
        # Obtener username
        username = client_id
        if client_id in self.players:
            if args:  # Si se proporciona username en el mensaje
                self.players[client_id]["username"] = args[0]
            username = self.players[client_id]["username"]
        
        state = "none"
        if client_id in self.players:
            state = self.players[client_id].get("state", "none")
        
        self.logger.info(f"Player {username} exited with state: {state}")
        
        if client_id in self.clients:
            self.clients[client_id]["disconnected"] = True
            
            active_clients = {cid: data for cid, data in self.clients.items() 
                             if cid != client_id and not data.get("disconnected", False)}
                             
            del self.clients[client_id]
            
            if active_clients:
                self.message_queue.put(f"{SM.PLAYER_EXIT}|{os.getpid()}")
                await self.broadcast_game_stats()
                await asyncio.sleep(0.5)
                await self.check_puzzle_completion_status()
            else:
                self.logger.info("All players have disconnected")
                self.message_queue.put(f"{SM.KILL_SERVER}|{os.getpid()}")
    
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
    
    async def check_puzzle_completion_status(self):
        """Check if all players have completed the current puzzle and send new if needed"""
        # Contar sólo clientes activos
        active_clients = {cid: data for cid, data in self.clients.items() 
                         if not data.get("disconnected", False)}
        total_players = len(active_clients)
        
        # Calcular estadísticas a partir de los estados
        correct_answers = sum(1 for cid in active_clients if cid in self.players and self.players[cid]["state"] == "correct")
        surrendered = sum(1 for cid in active_clients if cid in self.players and self.players[cid]["state"] == "surrendered")
        
        # Verificar si todos los jugadores han completado el puzzle
        if total_players > 0 and total_players <= correct_answers + surrendered:
            # Obtener nuevo puzzle
            new_puzzle = self.get_next_puzzle()
            if new_puzzle:
                self.logger.info(f"All players completed the puzzle. Sending new puzzle: {new_puzzle}")
                self.current_puzzle = new_puzzle
                
                # Resetear estados para el nuevo puzzle
                for client_id in self.players:
                    if client_id in active_clients:  # Solo para clientes conectados
                        self.players[client_id]["state"] = None
                
                # Enviar nuevo puzzle a todos los clientes
                await self.broadcast_message(f"{SCM.NEW_PUZZLE}|{new_puzzle}\n")
                
                return True  # Puzzle actualizado
        
        return False  # No necesita nuevo puzzle
            
    async def handle_client_connection(self, reader, writer):
        """Handle a client connection"""
        addr = writer.get_extra_info('peername')
        client_id = f"{addr[0]}:{addr[1]}"
        
        self.logger.info(f"New client connected: {client_id}")

        # Cancelar el temporizador de inactividad si es el primer cliente
        if self.idle_timer_active and len(self.clients) == 0:
            self.logger.info("First player joined. Canceling idle timer.")
            self.idle_timer_active = False
        
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
            # Contar sólo clientes activos
            active_clients = {cid: data for cid, data in self.clients.items() 
                             if not data.get("disconnected", False)}
            
            total_players = len(active_clients)
            
            # Calcular estadísticas a partir de los estados
            correct_answers = sum(1 for cid in active_clients if cid in self.players and self.players[cid]["state"] == "correct")
            surrendered = sum(1 for cid in active_clients if cid in self.players and self.players[cid]["state"] == "surrendered")
            
            # Formatear mensaje de estado
            message = f"{SCM.GAME_STATUS}|{total_players}|{correct_answers}|{surrendered}\n"
            
            self.logger.debug(f"Broadcasting stats: Players={total_players}, Correct={correct_answers}, Surrendered={surrendered}")
            
            # Broadcast a todos los clientes
            await self.broadcast_message(message)
            
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
