import re
import socket

from common.social import InterfaceMessages as IM
from client.player import Player
from client.user_interface import UserInterface

class User:
    def __init__(self, server_host='localhost', server_port=5000, test_mode=False):
        self.server_host = server_host
        self.server_port = server_port
        self.username = None
        self.sock = None
        self.ui = UserInterface(self)
        self.last_message = ""
        self.test_mode = test_mode

    def ask_for_ip_version(self):
        """Pregunta al usuario si desea utilizar IPv4 o IPv6."""
        while True:
            ip_version = self.ui.get_input("¿Desea utilizar IPv4 o IPv6? (4/6): ").strip()
            if ip_version == "4":
                return False
            elif ip_version == "6":
                return True
            else:
                self.ui.display_message("Opción inválida. Por favor, ingrese '4' para IPv4 o '6' para IPv6.")

    def create_socket(self, use_ipv6):
        """Crea un socket para la conexión."""
        if use_ipv6:
            self.sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        else:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def connect_to_server(self):
        """Establece la conexión con el servidor principal."""
        if self.test_mode:
            self.ui.display_message(IM.GREETING)
            return True
        try:
            use_ipv6 = self.ask_for_ip_version()
            self.create_socket(use_ipv6)
            self.sock.connect((self.server_host, self.server_port))
            self.ui.display_message(IM.GREETING)
        except Exception as e:
            self.ui.display_message(f"Connection error: {e}")
            return False
        return True

    def send_message(self, message):
        """Envía un mensaje al servidor."""
        if self.test_mode:
            self.last_message = message
            return
        try:
            self.sock.sendall(message.encode())
        except Exception as e:
            self.ui.display_message(f"Error sending message: {e}")

    def receive_message(self, buffer_size=1024):
        """Recibe un mensaje del servidor."""
        if self.test_mode:
            if "LOGIN" in self.last_message:
                return IM.LOGIN_SUCCESS
            elif "1" in self.last_message:
                return "Server List:\n1. Server 1\n2. Server 2"
            elif "2" in self.last_message:
                return "Success|Server 1|5001"
            elif "3" in self.last_message:
                return "Server created successfully."
            else:
                return "Simulated server response"
        try:
            response = self.sock.recv(buffer_size)
            return response.decode()
        except Exception as e:
            self.ui.display_message(f"Error receiving message: {e}")
            return None

    def login(self):
        """Realiza el proceso de login del jugador."""
        try:
            username = self.ui.get_input(IM.ASK_USERNAME)
            if not re.match("^[a-zA-Z0-9]{8,20}$", username):
                self.ui.display_message(IM.INVALID_USERNAME)
                return False
            self.send_message(username)
            response = self.receive_message()

            if response == IM.LOGIN_SUCCESS or self.test_mode:
                self.username = username
                self.ui.display_message(IM.LOGIN_SUCCESS)
                return True
            else:
                self.ui.display_message(IM.LOGIN_ERROR)
                return False
        except Exception as e:
            self.ui.display_message(f"Error during login: {e}")
            return False

    def main_menu(self):
        """Muestra el menú principal y maneja las opciones del jugador."""
        self.ui.main_menu()

    def view_server_list(self):
        """Solicita y muestra la lista de servidores al jugador."""
        self.send_message("1")
        response = self.receive_message(4096)
        self.ui.display_message(response)

    def join_server(self):
        """Permite al jugador unirse a un servidor existente."""
        server_id = self.ui.get_input(IM.ASK_SERVER_ID)
        self.send_message(f"2|{server_id}")
        response = self.receive_message()

        if response.startswith("Success"):
            _, name, classic_port = response.split("|")
            try:
                if not self.test_mode:
                    self.create_socket(self.use_ipv6)
                    self.sock.connect(('localhost', int(classic_port)))

                message = self.receive_message()
                if message == IM.SERVER_FULL:
                    raise Exception()

                self.ui.display_message(IM.SERVER_JOIN_SUCCESS)
                self.ui.display_message(f"Joining Server {name} ...")

                if not self.test_mode:
                    player = Player(self.username, self.sock)
                    self.ui.display_message(message)
                    player.play()

            except Exception as e:
                self.ui.display_message(f"Connection error: {e}")
        else:
            self.ui.display_message(IM.SERVER_JOIN_FAIL)

    def create_server(self):
        """Permite al jugador crear un servidor nuevo."""
        name = self.ui.get_input(IM.CREATE_SERVER_NAME)
        mode = self.ui.get_input(IM.CREATE_SERVER_MODE).lower()

        if mode not in ["classic", "competitive"]:
            self.ui.display_message(IM.CREATE_SERVER_ERROR)
            return

        self.send_message(f"3|{name}|{mode}")
        response = self.receive_message()
        self.ui.display_message(response)

    def exit_game(self):
        """Cierra la conexión con el servidor."""
        if not self.test_mode:
            self.sock.close()

# Ejecución del cliente
if __name__ == "__main__":
    user = User(test_mode=False)
    user.ui.start()
    if user.connect_to_server():
        while not user.username:
            user.login()
        user.main_menu()