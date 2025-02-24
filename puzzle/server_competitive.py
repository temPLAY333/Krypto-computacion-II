import time
from puzzle.logic import KryptoLogic

class ServerCompetitive:
    def __init__(self, pipe_puzzle, pipe_message, max_players=2):
        self.pipe_puzzle = pipe_puzzle  # Pipe para recibir nuevos puzzles del servidor principal
        self.pipe_message = pipe_message  # Pipe para enviar mensajes al servidor principal
        self.max_players = max_players
        self.players = []
        self.completed = [0] * max_players  # Lista para los completados por jugador
        self.quit_players = [0] * max_players  # Lista para los rendidos por jugador
        self.puzzles = []
        self.game_running = False

    def add_player(self, player_id):
        """Agregar un jugador al servidor"""
        if len(self.players) < self.max_players:
            self.players.append(player_id)
            print(f"Jugador {player_id} agregado al servidor {self.server_id}")
        else:
            print(f"Servidor {self.server_id} está lleno.")

    def remove_player(self, player_id):
        """Remover un jugador y verificar si el juego termina"""
        if player_id in self.players:
            self.players.remove(player_id)
            print(f"Jugador {player_id} removido del servidor {self.server_id}")
            self.check_game_status()

    def complete_puzzle(self, player_id):
        """Cuando un jugador completa el puzzle"""
        index = self.players.index(player_id)
        self.completed[index] += 1
        self.check_game_status()

    def quit_game(self, player_id):
        """Cuando un jugador se rinde"""
        index = self.players.index(player_id)
        self.quit_players[index] += 1
        self.check_game_status()

    def check_game_status(self):
        """Verifica si todos los jugadores completaron o se rindieron"""
        if sum(self.completed) + sum(self.quit_players) == len(self.players):
            self.notify_server_main()  # Notifica al servidor principal
            self.reset_game()

    def reset_game(self):
        """Resetea el estado del servidor para un nuevo puzzle"""
        self.completed = [0] * len(self.players)
        self.quit_players = [0] * len(self.players)
        self.players.clear()
        self.puzzles.clear()
        self.game_running = False

    def notify_server_main(self):
        """Notifica al servidor principal sobre el estado actual del servidor"""
        self.pipe_message.send(('server_status', self.server_id, self.completed, self.quit_players))

    def send_message_to_player(self, player_id, message):
        """Envía un mensaje a un jugador específico"""
        print(f"Enviando mensaje a jugador {player_id}: {message}")
        # Aquí se podría realizar una implementación más compleja con sockets, etc.

    def handle_player_message(self, player_id, message):
        """Maneja los mensajes de los jugadores"""
        if message == "complete":
            self.complete_puzzle(player_id)
            self.send_message_to_player(player_id, "correct")
        elif message == "quit":
            self.quit_game(player_id)
            self.send_message_to_player(player_id, "incorrect")
        else:
            self.send_message_to_player(player_id, "wait")

    def receive_new_puzzle(self, new_puzzle):
        """Recibe un nuevo puzzle del servidor principal"""
        self.puzzles.append(new_puzzle)
        self.game_running = True
        print(f"Servidor {self.server_id}: Nuevos puzzles recibidos.")
        self.pipe_message.send(('new_puzzle_received', self.server_id, self.puzzles))

    def handle_messages(self):
        """Maneja los mensajes recibidos de los jugadores"""
        while self.game_running:
            for player_id in self.players:
                message = self.listen_to_player(player_id)
                self.handle_player_message(player_id, message)

    def listen_to_player(self, player_id):
        """Simula escuchar a un jugador. Aquí puedes usar sockets u otro sistema de comunicación"""
        time.sleep(2)  # Simula la espera entre mensajes
        return "complete"  # Mensaje simulado para ejemplo

# Función para crear un servidor
def create_server(pipe_puzzle, pipe_message, server_id):
    server = ServerCompetitive(server_id, pipe_puzzle, pipe_message)
    print(f"Servidor {server_id} creado en modo competitivo.")
    return server
