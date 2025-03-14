import re
import os
import socket

from common.social import UserMainMessages as UM
from common.social import InterfaceMessages as IM
from common.communication import Communication
from common.network import NetworkManager
from client.player_factory import create_player
from client.user_interface import UserInterface

# Use the centralized logger
from common.logger import Logger

class User:
    """User class that handles communication with the main server"""
    
    def __init__(self, server_host=None, server_port=5000, test_mode=False):
        # Si no se especifica server_host, intentamos detectar una IP razonable
        if server_host is None:
            # Intentar obtener la IP del servidor del entorno si está disponible
            server_host = os.environ.get('KRYPTO_SERVER', '')
            if not server_host:
                # Usar una dirección IP genérica
                server_host = '127.0.0.1'  # IPv4 genérica en lugar de 'localhost'
   
        self.server_host = server_host
        self.server_port = server_port
        self.username = None
        self.sock = None
        self.use_ipv6 = False
        self.test_mode = test_mode
        self.last_message = ""
        self.server_list = []
        self.login_result = None
        self.command_results = {}  # To store results of command executions
        
        # Configure logging using the centralized logger
        Logger.configure(test_mode)
        self.logger = Logger.get("User", test_mode)
        
        self.communication = Communication(self.logger)
        
        # Register command handlers
        self.register_command_handlers()
        
        # UI will be set later
        self.ui = UserInterface(self)
        
        self.logger.info(f"User initialized with server_host={server_host}, server_port={server_port}, test_mode={test_mode}")
    
    def register_command_handlers(self):
        """Register all command handlers with the Communication object"""
        handlers = {
            UM.OK: self.handle_ok_response,
            UM.ERROR: self.handle_error_response,
            UM.LOGIN_SUCCESS: self.handle_login_success,
            UM.LOGIN_FAIL: self.handle_login_failure,
            UM.SERVER_LIST: self.handle_server_list,
            UM.JOIN_SUCCESS: self.handle_join_success,
            UM.JOIN_FAIL: self.handle_join_failure,
            UM.CREATE_SUCCESS: self.handle_create_success,
            UM.CREATE_FAIL: self.handle_create_failure,
        }
        
        # Register all handlers at once
        self.communication.define_all_commands(handlers)
    
    def handle_ok_response(self, *args):
        """Handle OK response from server"""
        self.logger.info("Received OK response from server")
        self.command_results["last_status"] = "ok"
    
    def handle_error_response(self, *args):
        """Handle error response from server"""
        error_msg = args[0] if args else "Unknown error"
        self.logger.error(f"Server error: {error_msg}")
        self.ui.display_message(f"Server error: {error_msg}", self.ui.COLOR_ERROR)
        self.command_results["last_status"] = "error"
        self.command_results["error_message"] = error_msg
    
    def handle_login_success(self, *args):
        """Handle successful login response"""
        self.logger.info("Login successful")
        self.ui.display_message(IM.LOGIN_SUCCESS, self.ui.COLOR_SUCCESS)
        self.login_result = True
        self.command_results["login"] = True
    
    def handle_login_failure(self, *args):
        """Handle login failure response"""
        reason = args[0] if args else "Unknown reason"
        self.logger.warning(f"Login failed: {reason}")
        self.ui.display_message(f"Login failed: {reason}", self.ui.COLOR_ERROR)
        self.login_result = False
        self.command_results["login"] = False
        self.command_results["login_error"] = reason
    
    def handle_server_list(self, *args):
        """Handle server list response"""
        server_list_str = args[0] if args else ""
        
        # Special case for "No servers available" message
        if server_list_str == "No servers available":
            self.server_list = []
            self.logger.info("No servers are currently available")
        else:
            self.server_list = []
            
            # Process regular server list - IMPORTANTE: Procesar solo aquí, no tratar como comandos
            servers = server_list_str.split('\n') if server_list_str else []
            
            # Filter out empty strings and add to server list
            for server in servers:
                if server.strip():
                    self.server_list.append(server.strip())
                    # Solo loggear, no ejecutar como comando
                    self.logger.debug(f"Added server to list: {server}")
            
            self.logger.info(f"Received server list with {len(self.server_list)} servers")
        
        self.command_results["server_list"] = self.server_list
        
        # IMPORTANTE: Procesar cualquier mensaje adicional en el buffer
        # para evitar interpretar líneas de servidores como comandos
        self._process_remaining_buffer()
    
    def handle_join_success(self, *args):
        """Handle successful join response"""
        if len(args) >= 3:
            server_name = args[0]
            server_host = args[1]  # La IP del servidor
            server_port = args[2]
            game_type = args[3] if len(args) >= 4 else "classic"
            
            self.logger.info(f"Successfully joined server {server_name} on {server_host}:{server_port}")
            self.ui.display_message(f"Successfully joined server {server_name}", self.ui.COLOR_SUCCESS)
            
            self.command_results["join"] = True
            self.command_results["server_name"] = server_name
            self.command_results["server_host"] = server_host  # Guardar el host
            self.command_results["server_port"] = server_port
            self.command_results["game_type"] = game_type
        else:
            self.logger.error("Join response missing required data")
            self.ui.display_message("Join response missing required data", self.ui.COLOR_ERROR)
            self.command_results["join"] = False
    
    def handle_join_failure(self, *args):
        """Handle join failure response"""
        reason = args[0] if args else "Unknown reason"
        self.logger.warning(f"Failed to join server: {reason}")
        self.ui.display_message(f"Failed to join server: {reason}", self.ui.COLOR_ERROR)
        self.command_results["join"] = False
        self.command_results["join_error"] = reason
    
    def handle_create_success(self, *args):
        """Handle successful server creation response"""
        server_id = args[0] if args else "Unknown"
        self.logger.info(f"Server created successfully with ID: {server_id}")
        self.ui.display_message(f"Server created successfully with ID: {server_id}", self.ui.COLOR_SUCCESS)
        self.command_results["create"] = True
        self.command_results["server_id"] = server_id
    
    def handle_create_failure(self, *args):
        """Handle server creation failure response"""
        reason = args[0] if args else "Unknown reason"
        self.logger.warning(f"Failed to create server: {reason}")
        self.ui.display_message(f"Failed to create server: {reason}", self.ui.COLOR_ERROR)
        self.command_results["create"] = False
        self.command_results["create_error"] = reason
    
    def _process_remaining_buffer(self):
        """Process any remaining data in the communication buffer"""
        try:
            # Verificar si hay más datos en el buffer de comunicación
            if hasattr(self.communication, 'buffer') and self.communication.buffer:
                # Si estos datos contienen información de servidores, no son comandos
                if self.communication.buffer.startswith("ID:"):
                    self.logger.debug("Found server entries in buffer, clearing to prevent misinterpretation")
                    # Si empieza con "ID:", es parte de la lista de servidores
                    while self.communication.buffer.startswith("ID:"):
                        if '\n' in self.communication.buffer:
                            # Extraer esta entrada y añadirla a server_list
                            entry, self.communication.buffer = self.communication.buffer.split('\n', 1)
                            if entry.strip():
                                self.server_list.append(entry.strip())
                                self.logger.debug(f"Added remaining server from buffer: {entry}")
                        else:
                            # No hay más saltos de línea, añadir el resto y limpiar
                            if self.communication.buffer.strip():
                                self.server_list.append(self.communication.buffer.strip())
                                self.logger.debug(f"Added final server from buffer: {self.communication.buffer}")
                            self.communication.buffer = ""
                            
                    # Actualizar command_results con la lista completa
                    self.command_results["server_list"] = self.server_list
        except Exception as e:
            self.logger.error(f"Error processing remaining buffer: {e}")
    
    def create_socket(self):
        """Crea un socket para la conexión."""
        try:
            if self.use_ipv6:
                self.sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
                self.logger.info("Created IPv6 socket")
            else:
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.logger.info("Created IPv4 socket")
            
            # Set default timeout
            self.sock.settimeout(5)
            return True
        except Exception as e:
            self.logger.error(f"Error creating socket: {e}")
            self.ui.display_message(f"Error creating socket: {e}")
            return False
    
    def connect_to_server(self):
        """Establece la conexión con el servidor principal."""
        try:
            self.ui.display_message(f"Connecting to server at {self.server_host}:{self.server_port}")
            self.logger.info(f"Connecting to server at {self.server_host}:{self.server_port}")
            
            # Primero verificar si el cliente soporta IPv6
            local_ipv6 = NetworkManager.is_ipv6_available()
            self.logger.info(f"Local IPv6 support: {local_ipv6}")
            
            # Variable para controlar qué versión IP usar
            use_ipv6 = False
            server_ipv6 = False
            
            # Si tenemos soporte local para IPv6, verificar si el servidor también lo soporta
            if local_ipv6:
                try:
                    # Intentar una conexión temporal para verificar si el servidor soporta IPv6
                    temp_sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
                    temp_sock.settimeout(2)  # Timeout corto para verificación
                    temp_sock.connect((self.server_host, self.server_port, 0, 0))  # Formato IPv6
                    server_ipv6 = True
                    temp_sock.close()
                    self.logger.info("Server supports IPv6")
                except Exception as e:
                    server_ipv6 = False
                    self.logger.info(f"Server does not support IPv6 or hostname not resolved: {e}")
            
            # Si ambos soportan IPv6, preguntar al usuario qué prefiere
            if local_ipv6 and server_ipv6:
                use_ipv6 = self.ask_for_ip_version()
            
            # Conectar usando la versión IP elegida o disponible
            if use_ipv6:
                # Conectar explícitamente con IPv6
                self.sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
                self.sock.connect((self.server_host, self.server_port, 0, 0))
                self.using_ipv6 = True
                self.logger.info("Connected using IPv6")
            else:
                # Usar IPv4
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.sock.connect((self.server_host, self.server_port))
                self.using_ipv6 = False
                self.logger.info("Connected using IPv4")
            
            self.ui.display_message("Connected successfully" + (" using IPv6" if self.using_ipv6 else " using IPv4"))
            return True
                
        except Exception as e:
            self.ui.display_message(f"Failed to connect: {e}")
            self.logger.error(f"Failed to connect: {e}")
            return False
    
    def ask_for_ip_version(self):
        """Pregunta al usuario qué versión de IP prefiere usar."""
        self.logger.info("Asking user for IP version preference")
        choice = self.ui.get_input("Both IPv4 and IPv6 are available. Enter '6' for IPv6 or '4' for IPv4: ")
        use_ipv6 = (choice.strip() == '6')
        self.logger.info(f"User selected {'IPv6' if use_ipv6 else 'IPv4'}")
        return use_ipv6
    
    def login(self):
        """Realiza el proceso de login del jugador."""
        try:
            username = self.ui.get_input(IM.ASK_USERNAME)
            if not re.match("^[a-zA-Z0-9]{3,20}$", username):
                self.ui.display_message(IM.INVALID_USERNAME)
                self.logger.warning(f"Invalid username format: {username}")
                return False
            
            # Confirmation with the server
            if self.test_mode:
                self.username = username
                self.ui.display_message(IM.LOGIN_SUCCESS)
                self.logger.info(f"Test mode: User {username} logged in")
                return True
            
            # Send login request
            self.communication.send_message(self.sock, f"{UM.LOGIN}|{username}")
            
            # Wait for login response
            success, data = self.communication.receive_message(self.sock)
            if not success:
                self.ui.display_message("Login failed, no response from server.")
                self.logger.error("Login failed, no server response")
                return False
            
            # Process the response using the communication handler
            self.communication.execute_command(data)
            
            # Check if login was successful
            if self.command_results.get("login"):
                self.username = username
                return True
            else:
                return False
                
        except Exception as e:
            self.ui.display_message(f"Error during login: {e}")
            self.logger.error(f"Error during login: {e}")
            return False
    
    def get_server_list(self):
        """Get the list of available servers from the main server"""
        try:
            if self.test_mode:
                self.logger.info("Test mode: Returning simulated server list")
                return ["Server 1", "Server 2", "Server 3"]
            
            # Request server list
            self.communication.send_message(self.sock, UM.LIST_SERVERS)
            
            # Receive server list
            success, data = self.communication.receive_message(self.sock)
            if not success:
                self.logger.warning("Failed to retrieve server list: no response")
                return []
            
            # Process the response
            self.communication.execute_command(data)
            
            # Return the server list from the command results
            return self.command_results.get("server_list", [])
            
        except Exception as e:
            self.ui.display_message(f"Error getting server list: {e}")
            self.logger.error(f"Error getting server list: {e}")
            return []

    def join_server(self, server_id):
        """Join a specific game server"""
        try:
            if self.test_mode:
                self.logger.info(f"Test mode: Simulating joining server with ID {server_id}")
                # In test mode, just simulate joining a server
                return self.connect_to_game_server(server_id, "5001", "classic")
            
            # Request to join server
            self.communication.send_message(self.sock, f"{UM.CHOOSE_SERVER}|{server_id}")
            
            # Get response
            success, data = self.communication.receive_message(self.sock)
            if not success:
                self.ui.display_message("Failed to join server: no response from server.")
                self.logger.error("Failed to join server: no response")
                return False
            
            # Process the response
            self.communication.execute_command(data)
            
            # Check if join was successful
            if self.command_results.get("join"):
                # Connect to the game server
                return self.connect_to_game_server(
                    self.command_results.get("server_name"),
                    self.command_results.get("server_port"),
                    self.command_results.get("game_type", "classic")
                )
            else:
                return False
                
        except Exception as e:
            self.ui.display_message(f"Error joining server: {e}")
            self.logger.error(f"Error joining server: {e}")
            return False
    
    def create_server(self, server_name, server_type, number):
        """Create a new game server"""
        try:
            if self.test_mode:
                self.logger.info(f"Test mode: Simulating creating {server_type} server")
                self.ui.display_message("Server created successfully in test mode.")
                return True
            
            # Send server creation request
            self.communication.send_message(self.sock, f"{UM.CREATE_SERVER}|{server_name}|{server_type}|{number}")
            
            # Get response
            success, data = self.communication.receive_message(self.sock)
            if not success:
                self.ui.display_message("Failed to create server: no response from server.")
                self.logger.error("Failed to create server: no response")
                return False
            
            # Process the response
            self.communication.execute_command(data)
            
            # Check if creation was successful
            return self.command_results.get("create", False)
            
        except Exception as e:
            self.ui.display_message(f"Error creating server: {e}")
            self.logger.error(f"Error creating server: {e}")
            return False
    
    def connect_to_game_server(self, server_name, server_port, game_type):
        """Connect to a game server using the PlayerFactory"""
        try:
            self.ui.display_message(f"Connecting to {server_name} ({game_type} mode)...")
            
            # Obtener el servidor correcto (puede ser localhost u otro servidor)
            server_host = self.command_results.get("server_host", self.server_host)
            
            # Use PlayerFactory to create the appropriate player and interface
            player = create_player(
                self.username, 
                server_host, 
                int(server_port), 
                game_type,
                self.test_mode  # Pass debug mode
            )
            
            if player:
                self.logger.info(f"Connected to game server: {server_name} at {server_host}:{server_port}")
                
                # Hide the user User interface
                self.ui.pause()
                
                # Start the Player interface in a separate thread
                player.play()
                
                # Resume the User interface when done
                self.ui.resume()
                return True
            else:
                self.ui.display_message(f"Failed to connect to {server_name}.")
                self.logger.error(f"Failed to create player for {server_name}")
                return False
        except Exception as e:
            self.ui.display_message(f"Error connecting to game server: {e}")
            self.logger.error(f"Error connecting to game server: {e}")
            return False
    
    def exit_game(self):
        """Close the connection with the server and exit"""
        try:
            if not self.test_mode and self.sock:
                try:
                    self.communication.send_message(self.sock, UM.LOGOUT)
                except:
                    pass  # Ignore errors during logout
                self.sock.close()
            
            self.logger.info("User session ended")
            return True
        except Exception as e:
            self.logger.error(f"Error during exit: {e}")
            return False

# Ejecución del cliente
if __name__ == "__main__":
    user = User(test_mode=False)
    
    try:
        # Conectar al servidor dentro de la UI
        # No intentar conectarse antes de inicializar la UI
        user.ui.start()
    except KeyboardInterrupt:
        # Manejar cierre con Ctrl+C
        print("Programa interrumpido por el usuario")
    except Exception as e:
        print(f"Error en la aplicación: {e}")
    finally:
        # Asegurarse de cerrar las conexiones
        if hasattr(user, 'sock') and user.sock:
            try:
                user.sock.close()
            except:
                pass