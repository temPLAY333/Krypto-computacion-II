import logging
import re
import socket
import os

from common.social import UserMainMessages as UM
from common.social import InterfaceMessages as IM
from client.player import Player
from client.user_interface import UserInterface

# Configure logging to write to a file instead of stdout to avoid interfering with curses
log_dir = os.path.dirname(os.path.abspath(__file__))
logging.basicConfig(
    filename=os.path.join(log_dir, 'client.log'),
    level=logging.DEBUG, 
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class User:
    def __init__(self, server_host='localhost', server_port=5000, test_mode=False):
        self.server_host = server_host
        self.server_port = server_port
        self.username = None
        self.sock = None
        self.use_ipv6 = False
        self.ui = UserInterface(self)
        logging.info(f"User initialized with server_host={server_host}, server_port={server_port}, test_mode={test_mode}")

        self.test_mode = test_mode
        self.last_message = ""
        self.UM = UM  # Make UM accessible to UserInterface

    def ask_for_ip_version(self):
        """Pregunta al usuario si desea utilizar IPv4 o IPv6."""
        while True:
            ip_version = self.ui.get_input("¿Desea utilizar IPv4 o IPv6? (4/6): ").strip()
            if ip_version == "4":
                logging.info("User selected IPv4")
                self.use_ipv6 = False
                break
            elif ip_version == "6":
                logging.info("User selected IPv6")
                self.use_ipv6 = True
                break
            else:
                self.ui.display_message("Opción inválida. Por favor, ingrese '4' para IPv4 o '6' para IPv6.")
                logging.warning("Invalid IP version selected")

    def create_socket(self):
        """Crea un socket para la conexión."""
        if self.use_ipv6:
            self.sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
            logging.info("Created IPv6 socket")
        else:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            logging.info("Created IPv4 socket")

    def connect_to_server(self):
        """Establece la conexión con el servidor principal."""
        if self.test_mode:
            self.ui.display_message(IM.GREETING)
            logging.info("Test mode enabled, skipping server connection")
            return True
        try:
            self.ask_for_ip_version()
            self.create_socket()
            self.sock.settimeout(2)
            logging.info(f"Attempting to connect to {self.server_host}:{self.server_port}")
            self.sock.connect((self.server_host, self.server_port))
            self.send_message(UM.TEST)
            response = self.receive_message()
            if response == UM.TEST:
                self.ui.display_message(IM.GREETING)
                logging.info("Test message received successfully")
            else:
                logging.error("Test message not received correctly")
                return False
        except socket.timeout:
            self.ui.display_message("Connection timed out.")
            logging.error("Connection timed out")
            return False
        except Exception as e:
            self.ui.display_message(f"Connection error: {e}")
            logging.error(f"Connection error: {e}")
            return False
        return True

    def send_message(self, message):
        """Envía un mensaje al servidor."""
        if self.test_mode:
            self.last_message = message
            logging.info(f"Test mode enabled, message stored: {message}")
            return
        try:
            logging.info(f"Sending message: {message}")
            self.sock.sendall(message.encode())
        except Exception as e:
            self.ui.display_message(f"Error sending message: {e}")
            logging.error(f"Error sending message: {e}")

    def receive_message(self, buffer_size=1024):
        """Recibe un mensaje del servidor."""
        if self.test_mode:
            if "1" in self.last_message:
                return "Server List:\n1. Server 1\n2. Server 2"
            elif "2" in self.last_message:
                return "Success|Server 1|5001"
            elif "3" in self.last_message:
                return "Server created successfully."
            else:
                return "Simulated server response"
        try:
            self.sock.settimeout(10)  # Establecer un tiempo máximo de espera de 10 segundos
            response = self.sock.recv(buffer_size)
            logging.info(f"Received message: {response.decode()}")
            return response.decode()
        except socket.timeout:
            self.ui.display_message("Receiving message timed out.")
            logging.error("Receiving message timed out")
            return None
        except Exception as e:
            self.ui.display_message(f"Error receiving message: {e}")
            logging.error(f"Error receiving message: {e}")
            return None

    def login(self):
        """Realiza el proceso de login del jugador."""
        try:
            username = self.ui.get_input(IM.ASK_USERNAME)
            if not re.match("^[a-zA-Z0-9]{8,20}$", username):
                self.ui.display_message(IM.INVALID_USERNAME)
                logging.warning("Invalid username format")
                return False
            
            # Confirmacion con el Servidor
            self.send_message(UM.LOGIN + f"|{username}")
            response = self.receive_message()

            if response == IM.LOGIN_SUCCESS or self.test_mode:
                self.username = username
                self.ui.display_message(IM.LOGIN_SUCCESS)
                logging.info(f"User {username} logged in successfully")
                return True
            else:
                self.ui.display_message(IM.LOGIN_ERROR)
                logging.error("Login failed")
                return False
        except Exception as e:
            self.ui.display_message(f"Error during login: {e}")
            logging.error(f"Error during login: {e}")
            return False

    def main_menu(self):
        """Muestra el menú principal y maneja las opciones del jugador."""
        self.ui.main_menu()

    def view_server_list(self):
        """This method is now handled directly by UserInterface"""
        pass

    def join_server(self):
        """This method is now handled directly by UserInterface"""
        pass

    def create_server(self):
        """This method is now handled directly by UserInterface"""
        pass

    def connect_to_game_server(self, server_name, server_port):
        """Connect to a game server after selecting it"""
        try:
            if not self.test_mode:
                game_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                game_socket.connect(('localhost', int(server_port)))
                
                message = game_socket.recv(1024).decode()
                if message == IM.SERVER_FULL:
                    self.ui.display_message(IM.SERVER_FULL)
                    return
                
                self.ui.display_message(IM.SERVER_JOIN_SUCCESS)
                
                player = Player(self.username, game_socket)
                player.play()
                
            else:
                # Test mode logic
                self.ui.display_message(IM.SERVER_JOIN_SUCCESS)
                self.ui.display_message(f"Simulated joining of server {server_name}")
                
        except Exception as e:
            self.ui.display_message(f"Connection error: {e}")
            logging.error(f"Connection error: {e}")

    def exit_game(self):
        """Cierra la conexión con el servidor."""
        if not self.test_mode:
            self.sock.close()
            logging.info("Connection closed")

# Ejecución del cliente
if __name__ == "__main__":
    user = User(test_mode=False)
    user.ui.start()
    if user.connect_to_server():
        while not user.username:
            user.login()
        user.main_menu()