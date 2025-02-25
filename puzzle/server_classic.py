import time
import socket
import threading
import multiprocessing

from multiprocessing import Queue
from multiprocessing.connection import PipeConnection

from puzzle.logic import KryptoLogic
from common.social import PlayerServerMessages as PM

class ServerClassic:
    def __init__(self, pipe_puzzle: Queue, pipe_message: PipeConnection):
        # Puntos de comunicación (puentes) con el servidor principal
        self.pipe_puzzle = pipe_puzzle
        self.pipe_message = pipe_message

        # Comandos que el servidor puede recibir de los jugadores
        self.commands = {
                PM.SUBMIT_ANSWER: self.handle_posible_solution,
                PM.PLAYER_SURRENDER: self.handle_player_rend,
                PM.PLAYER_EXIT: self.handle_player_disconnect,
            }
        
        # Configuración del servidor
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind(('localhost', 5001))  # Dirección y puerto
        self.server_socket.listen(10)
        
        # Estado del servidor
        self.players = 0
        self.solved = 0
        self.abandoned = 0
        self.puzzle = 0
        self.client_sockets = []
        print("Servidor Clásico iniciado y esperando conexiones...")

    def broadcast(self, message):
        """Envía un mensaje a todos los jugadores."""
        for player in self.client_sockets:
            try:
                player.sendall(message.encode())
            except Exception as e:
                print(f"Error broadcasting message: {e}")

    def starting(self, test=False):
        """Inicia el servidor clásico y espera las conexiones de los jugadores"""
        self.puzzle = self.pipe_puzzle.get()
        self.pipe_message.sendall("ok")

        while True:
            client_socket, client_direccion = self.server_socket.accept()
            if self.players >= 8:
                client_socket.sendall(PM.SERVER_FULL.encode())
                client_socket.close()
            else:
                print(f"Conexión aceptada de {client_direccion}")
                client_socket.sendall(PM.GREETING.encode())
                self.players += 1
                self.check_game_status()

                client_socket.sendall((PM.NEW_PUZZLE + "|" + self.puzzle).encode())

                # Crear un hilo para manejar el cliente
                threading.Thread(target=self.handle_client_messages, args=(client_socket,)).start()
                
            time.sleep(1)
            if test:
                break

    def handle_client_messages(self, client_socket, test=False):
        """Maneja los mensajes recibidos del cliente y la conexión del jugador."""
        self.client_sockets.append(client_socket)
        client_socket.sendall(f"Nuevo puzzle: {self.puzzle}".encode())

        while True:
            try:
                data = client_socket.recv(1024).decode()
                if not data:
                    break
                command, *args = data.split("|")
                if command in self.commands:
                    self.commands[command](client_socket, *args)
                else:
                    print(f"Unknown command from client: {command}")
            except Exception as e:
                print(f"Error with player: {e}")
                break
            if test:
                break

        client_socket.close()
        self.client_sockets.remove(client_socket)
        self.handle_player_disconnect()

    def handle_posible_solution(self, client_socket, solution):
        """Maneja la posible solución enviada por el jugador"""
        if KryptoLogic.verify_solution(solution, self.puzzle[-1]):
            self.solved += 1
            client_socket.sendall((PM.PUZZLE_RESULT + "|Correcto").encode())
            self.check_game_status()
        else:
            client_socket.sendall((PM.PUZZLE_RESULT + "|Incorrecto").encode())

    def handle_player_rend(self, client_socket):
        """Maneja el abandono de un jugador"""
        self.abandoned += 1
        client_socket.sendall(("You gave up").encode())
        self.check_game_status()

    def handle_player_disconnect(self):
        """Maneja la desconexión de un jugador"""
        self.players -= 1
        if self.players == 0:
            self.pipe_message.sendall("vacio")  # Avisar al servidor principal que no hay jugadores
        self.check_game_status()

    def check_game_status(self):
        """Verifica el estado del juego (todos los jugadores terminaron o se rindieron)"""
        if self.solved + self.abandoned == self.players:
            self.puzzle = self.pipe_puzzle.get() # Recibir un nuevo puzzle del servidor principal
            self.pipe_message.sendall("ok")  # Avisar al servidor principal que el puzzle fue resuelto

            # Limpiar estado y esperar nuevo puzzle
            self.solved = 0
            self.abandoned = 0
            self.broadcast(PM.NEW_PUZZLE + "|" + self.puzzle)  # Enviar nuevo puzzle a todos los jugadores
        
        self.broadcast(PM.GAME_STATE + f"|{self.solved}|{self.abandoned}|{self.players}")


# Ejemplo de uso del servidor clásico
if __name__ == "__main__":
    pipe_puzzle, pipe_message = multiprocessing.Pipe()
    
    # Crear la instancia del servidor clásico
    server = ServerClassic(pipe_puzzle, pipe_message)
    server.starting()
