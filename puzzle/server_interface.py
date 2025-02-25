from abc import ABC, abstractmethod

class ServerInterface(ABC):
    @abstractmethod
    def start(self, port):
        pass

    @abstractmethod
    def handle_player(self, reader, writer):
        pass
    
    @abstractmethod
    def handle_posible_solution(self, writer, solution):
        pass
    
    @abstractmethod
    def handle_player_rend(self, client_socket):
        pass
    
    @abstractmethod
    def handle_player_disconnect(self):
        pass

    @abstractmethod
    def check_game_status(self):
        pass

    @abstractmethod
    def generate_puzzle(self):
        pass