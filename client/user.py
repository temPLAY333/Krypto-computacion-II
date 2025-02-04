
import socket

from common.social import Messages
from client.player import Player
import re

class User:
    def __init__(self, host='localhost', port=5000):
        self.host = host
        self.port = port
        self.username = None
        self.socket = None

    def connect_to_server(self):
        """Establece la conexión con el servidor principal."""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            print(Messages.GREETING)
        except Exception as e:
            print(f"Connection error: {e}")
            return False
        return True

    def login(self):
        """Realiza el proceso de login del jugador."""
        try:
            username = input(Messages.ASK_USERNAME)
            if not re.match("^[a-zA-Z0-9]{8,20}$", username):
                print(Messages.INVALID_USERNAME)
                return False
            self.socket.sendall(username.encode())
            response = self.socket.recv(1024).decode()

            if response == Messages.LOGIN_SUCCESS:
                self.username = username
                print(Messages.LOGIN_SUCCESS)
                return True
            else:
                print(Messages.LOGIN_ERROR)
                return False
        except Exception as e:
            print(f"Error during login: {e}")
            return False

    def main_menu(self):
        """Muestra el menú principal y maneja las opciones del jugador."""
        while True:
            print(Messages.MAIN_MENU)
            option = input().strip()

            if option == "1":
                self.view_server_list()
            elif option == "2":
                self.join_server()
            elif option == "3":
                self.create_server()
            elif option == "exit":
                self.exit_game()
                break
            else:
                print(Messages.INVALID_OPTION)

    def view_server_list(self):
        """Solicita y muestra la lista de servidores al jugador."""
        self.socket.sendall(b"1")
        response = self.socket.recv(4096).decode()
        print(response)

    def join_server(self):
        """Permite al jugador unirse a un servidor existente."""
        server_id = input(Messages.ASK_SERVER_ID)
        self.socket.sendall(f"2|{server_id}".encode())
        response = self.socket.recv(1024).decode()

        if response.startswith("Success"):
            _, name, classic_port = response.split("|")
            try:
                classic_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                classic_socket.connect(('localhost', classic_port))

                message = classic_socket.recv(1024).decode()
                if message == Messages.SERVER_FULL:
                    raise Exception()

                print(Messages.SERVER_JOIN_SUCCESS)
                print(f"Joining Server {name} ...")

                player = Player(self.username, classic_socket)
                print(message)
                player.play()

            except Exception as e:
                print(f"Connection error: {e}")
        else:
            print(Messages.SERVER_JOIN_FAIL)

    def create_server(self):
        """Permite al jugador crear un servidor nuevo."""
        name = input(Messages.CREATE_SERVER_NAME)
        mode = input(Messages.CREATE_SERVER_MODE).lower()

        if mode not in ["classic", "competitive"]:
            print(Messages.CREATE_SERVER_ERROR)
            return

        self.socket.sendall(f"3|{name}|{mode}".encode())
        response = self.socket.recv(1024).decode()
        print(response)

# Ejecución del cliente
if __name__ == "__main__":
    player = User()
    if player.connect_to_server():
        if player.login():
            player.main_menu()
