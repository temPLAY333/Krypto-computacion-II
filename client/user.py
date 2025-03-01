import re
import os
import sys
import time
import socket
import logging
import threading

from common.social import UserMainMessages as UM
from common.social import InterfaceMessages as IM
from common.communication import Communication
from client.player_factory import create_player
from client.user_interface import UserInterface

# Configure logging
log_dir = os.path.dirname(os.path.abspath(__file__))
logging.basicConfig(
    filename=os.path.join(log_dir, 'client.log'),
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Add console handler to see logs in console too
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logging.getLogger().addHandler(console_handler)

class User:
    """User class that handles communication with the main server"""
    
    def __init__(self, server_host='localhost', server_port=5000, test_mode=False):
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
        
        # Set up logging and communication
        self.logger = logging.getLogger("User")
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
        self.server_list = server_list_str.split('\n') if server_list_str else []
        self.logger.info(f"Received server list with {len(self.server_list)} servers")
        self.command_results["server_list"] = self.server_list
    
    def handle_join_success(self, *args):
        """Handle successful join response"""
        if len(args) >= 2:
            server_name = args[0]
            server_port = args[1]
            game_type = args[2] if len(args) >= 3 else "classic"
            
            self.logger.info(f"Successfully joined server {server_name} on port {server_port}")
            self.ui.display_message(f"Successfully joined server {server_name}", self.ui.COLOR_SUCCESS)
            
            self.command_results["join"] = True
            self.command_results["server_name"] = server_name
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
    
    def ask_for_ip_version(self):
        """Pregunta al usuario si desea utilizar IPv4 o IPv6."""
        while True:
            ip_version = self.ui.get_input("¿Desea utilizar IPv4 o IPv6? (4/6): ").strip()
            if ip_version == "4":
                self.logger.info("User selected IPv4")
                self.use_ipv6 = False
                return
            elif ip_version == "6":
                self.logger.info("User selected IPv6")
                self.use_ipv6 = True
                return
            else:
                self.ui.display_message("Opción inválida. Por favor, ingrese '4' para IPv4 o '6' para IPv6.")
                self.logger.warning("Invalid IP version selected")
    
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
        if self.test_mode:
            self.ui.display_message(IM.GREETING)
            self.logger.info("Test mode enabled, skipping server connection")
            return True
        
        try:
            self.ask_for_ip_version()
            if not self.create_socket():
                return False
                
            self.logger.info(f"Attempting to connect to {self.server_host}:{self.server_port}")
            self.sock.connect((self.server_host, self.server_port))
            
            # Test the connection with a test message
            self.communication.send_message(self.sock, UM.TEST)
            
            # Wait for a response to verify communication is working
            success, data = self.communication.receive_message(self.sock)
            if not success:
                self.ui.display_message("Connection test failed, server did not respond.")
                self.logger.error("Connection test failed")
                return False
                
            # Process the response using the communication handler
            self.communication.execute_command(data)
            
            # Check if the result was OK
            if self.command_results.get("last_status") != "ok":
                self.ui.display_message("Connection test failed, server response not recognized.")
                self.logger.error("Connection test failed: invalid response")
                return False
                
            self.ui.display_message(IM.GREETING)
            self.logger.info("Connected to server")
            return True
        except socket.timeout:
            self.ui.display_message("Connection timed out.")
            self.logger.error("Connection timed out")
            return False
        except Exception as e:
            self.ui.display_message(f"Connection error: {e}")
            self.logger.error(f"Connection error: {e}")
            return False
    
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
            
            # Use PlayerFactory to create the appropriate player and interface
            player, interface = create_player(
                self.username, 
                'localhost', 
                int(server_port), 
                game_type
            )
            
            if player and interface:
                self.ui.display_message(f"Connected to {server_name}. Starting game...")
                self.logger.info(f"Connected to game server: {server_name}:{server_port}")
                
                # Hide the user User interface
                self.ui.pause()
                
                # Start the Player interface in a separate thread
                interface.start()
                
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
    user.ui.start()