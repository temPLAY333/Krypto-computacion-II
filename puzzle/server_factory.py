import multiprocessing
from puzzle.server_classic import ServerClassic
from puzzle.server_competitive import ServerCompetitive

class ServerFactory:
    def __init__(self, puzzle_queue, message_queue):
        self.puzzle_queue = puzzle_queue
        self.message_queue = message_queue
        self.processes = {}
        self.next_port = 5001

    def create_server(self, name, mode):
        if mode == "classic":
            return self._create_classic_server(name)
        elif mode == "competitive":
            return self._create_competitive_server(name)
        else:
            raise ValueError("Invalid game mode")

    def _create_classic_server(self, name):
        port = self.next_port
        self.next_port += 1

        process = multiprocessing.Process(
            target=self._start_classic_server,
            args=(port, self.puzzle_queue, self.message_queue)
        )
        process.start()

        self.processes[process.pid] = process
        return process.pid

    def _start_classic_server(self, port, puzzle_queue, message_queue):
        server = ServerClassic(puzzle_queue, message_queue)
        server.start(port)

    def _create_competitive_server(self, name):
        port = self.next_port
        self.next_port += 1

        process = multiprocessing.Process(
            target=self._start_competitive_server,
            args=(port, self.puzzle_queue, self.message_queue)
        )
        process.start()

        self.processes[process.pid] = process
        return process.pid

    def _start_competitive_server(self, port, puzzle_queue, message_queue):
        server = ServerCompetitive(puzzle_queue, message_queue)
        server.start(port)