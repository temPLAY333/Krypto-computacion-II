import unittest
import asyncio
import tracemalloc

from unittest.mock import patch, MagicMock, AsyncMock
from puzzle.main import MainServer
from test.async_test_case import AsyncTestCase


tracemalloc.start()
class TestMainServer(AsyncTestCase):

    async def asyncSetUp(self):
        patcher = patch('builtins.print')
        self.mock_print = patcher.start()
        self.addCleanup(patcher.stop)

    @patch('puzzle.logic.KryptoLogic.generar_puzzle')
    @patch('multiprocessing.Queue')
    def test_01_initialize_puzzles(self, mock_queue, mock_generar_puzzle):
        mock_generar_puzzle.return_value = "puzzle"
        mock_queue_instance = mock_queue.return_value

        server = MainServer()
        server.initialize_puzzles()

        self.assertEqual(mock_queue_instance.put.call_count, server.max_servers)
        mock_generar_puzzle.assert_called()

    @patch('asyncio.start_server', new_callable=AsyncMock)
    @patch('threading.Thread')
    async def test_02_start_main_server(self, mock_thread, mock_start_server):
        server = MainServer()
        mock_server_instance = AsyncMock()
        mock_start_server.return_value = mock_server_instance

        await server.start_main_server()

        mock_thread.assert_called()
        mock_start_server.assert_called_with(server.handle_new_player, server.host, server.port)
        mock_server_instance.serve_forever.assert_called()
        
    
    @patch('puzzle.logic.KryptoLogic.generar_puzzle')
    def test_03_listen_to_servers_messages_ok(self, mock_generar_puzzle):
        mock_pipe = MagicMock()
        mock_pipe.poll.return_value = True
        mock_pipe.recv.return_value = "ok"

        server = MainServer()
        server.processes = {1: MagicMock()}
        server.puzzle_queue = MagicMock()
        server.process_pipes = {1: mock_pipe}
        mock_generar_puzzle.return_value = "new_puzzle"

        with patch.object(server, 'listen_to_servers', wraps=server.listen_to_servers) as mock_listen:
            server.listen_to_servers(True)
            mock_listen.assert_called_once()

        server.puzzle_queue.put.assert_called_with("new_puzzle")
        mock_pipe.close.assert_not_called()
        server.processes[1].terminate.assert_not_called()

    def test_04_listen_to_servers_messages_vacio(self):
        mock_pipe = MagicMock()
        mock_pipe.poll.return_value = True
        mock_pipe.recv.return_value = "vacio"

        server = MainServer()
        server.processes = {1: MagicMock()}
        server.puzzle_queue = MagicMock()
        server.process_pipes = {1: mock_pipe}

        with patch.object(server, 'listen_to_servers', wraps=server.listen_to_servers) as mock_listen:
            server.listen_to_servers(True)
            mock_listen.assert_called_once()

        mock_pipe.close.assert_called()
        # server.processes[1].terminate.assert_called()
        server.puzzle_queue.put.assert_not_called()
        self.assertNotIn(1, server.process_pipes)
        self.assertNotIn(1, server.processes)

    def test_05_listen_to_servers_messages_error(self):
        mock_pipe = MagicMock()
        mock_pipe.poll.return_value = True
        mock_pipe.recv.return_value = "error"

        server = MainServer()
        server.processes = {1: MagicMock()}
        server.puzzle_queue = MagicMock()
        server.process_pipes = {1: mock_pipe}

        with patch.object(server, 'listen_to_servers', wraps=server.listen_to_servers) as mock_listen:
            server.listen_to_servers(True)
            mock_listen.assert_called_once()

        mock_pipe.close.assert_not_called()
        server.processes[1].terminate.assert_not_called()
        self.assertIn(1, server.process_pipes)
        self.assertIn(1, server.processes)

    @patch('asyncio.StreamReader.read', return_value=b'test-username')
    @patch('asyncio.StreamWriter.write')
    @patch('asyncio.StreamWriter.drain', return_value=None)
    async def test_06_handle_new_player(self, mock_drain, mock_write, mock_read):
        server = MainServer()
        reader = MagicMock()
        writer = MagicMock()

        with patch.object(server, 'handle_new_player', wraps=server.handle_new_player) as mock_handle:
            await server.handle_new_player(reader, writer)
            mock_handle.assert_called_once()

        mock_read.assert_called()
        mock_write.assert_called_with(b'Login successful!')
        mock_drain.assert_called()

    @patch('asyncio.StreamReader.read', return_value=b'1')
    @patch('asyncio.StreamWriter.write')
    @patch('asyncio.StreamWriter.drain', return_value=None)
    @patch('main.MainServer.send_server_list')
    async def test_07_handle_new_player_option_1(self, mock_send_server_list, mock_drain, mock_write, mock_read):
        server = MainServer()
        reader = MagicMock()
        writer = MagicMock()

        with patch.object(server, 'handle_new_player', wraps=server.handle_new_player) as mock_handle:
            await server.handle_new_player(reader, writer)
            mock_handle.assert_called_once()

        mock_send_server_list.assert_called_with(writer)
        mock_drain.assert_called()

    @patch('asyncio.StreamReader.read', return_value=b'2|server1')
    @patch('asyncio.StreamWriter.write')
    @patch('asyncio.StreamWriter.drain', return_value=None)
    @patch('main.MainServer.handle_server_choice')
    async def test_08_handle_new_player_option_2(self, mock_handle_server_choice, mock_drain, mock_write, mock_read):
        server = MainServer()
        reader = MagicMock()
        writer = MagicMock()

        with patch.object(server, 'handle_new_player', wraps=server.handle_new_player) as mock_handle:
            await server.handle_new_player(reader, writer)
            mock_handle.assert_called_once()

        mock_handle_server_choice.assert_called_with('server1', writer)
        mock_drain.assert_called()

    @patch('asyncio.StreamReader.read', return_value=b'3|Test Server|classic')
    @patch('asyncio.StreamWriter.write')
    @patch('asyncio.StreamWriter.drain', return_value=None)
    @patch('main.MainServer.create_new_server')
    async def test_09_handle_new_player_option_3(self, mock_create_new_server, mock_drain, mock_write, mock_read):
        server = MainServer()
        reader = MagicMock()
        writer = MagicMock()

        with patch.object(server, 'handle_new_player', wraps=server.handle_new_player) as mock_handle:
            await server.handle_new_player(reader, writer)
            mock_handle.assert_called_once()

        mock_create_new_server.assert_called_with('Test Server', 'classic', writer)
        mock_drain.assert_called()


    @patch('common.social.Messages.NO_SERVERS', 'No servers available')
    @patch('asyncio.StreamWriter.write')
    @patch('asyncio.StreamWriter.drain', return_value=None)
    async def test_10_send_server_list_no_servers(self, mock_drain, mock_write, mock_no_servers):
        server = MainServer()
        writer = MagicMock()

        await server.send_server_list(writer)

        mock_write.assert_called_with(b'No servers available')
        mock_drain.assert_called()

    @patch('asyncio.StreamWriter.write')
    @patch('asyncio.StreamWriter.drain', return_value=None)
    async def test_11_send_server_list_with_servers(self, mock_drain, mock_write):
        server = MainServer()
        server.servers = {
            '1': {'port': 5001, 'name': 'Server 1', 'mode': 'classic'},
            '2': {'port': 5002, 'name': 'Server 2', 'mode': 'competitive'}
        }
        writer = MagicMock()

        await server.send_server_list(writer)

        expected_output = (
            b'\nAvailable servers:\n'
            b'ID: 1, Name: Server 1, Mode: classic\n'
            b'ID: 2, Name: Server 2, Mode: competitive\n'
        )
        mock_write.assert_called_with(expected_output)
        mock_drain.assert_called()

    @patch('asyncio.StreamWriter.write')
    @patch('asyncio.StreamWriter.drain', return_value=None)
    async def test_12_handle_server_choice_valid(self, mock_drain, mock_write):
        server = MainServer()
        server.servers = {
            '1': {'port': 5001, 'name': 'Server 1', 'mode': 'classic'}
        }
        writer = MagicMock()

        await server.handle_server_choice('1', writer)

        mock_write.assert_called_with(b"Success|'Server 1'|5001.\n")
        mock_drain.assert_called()

    @patch('asyncio.StreamWriter.write')
    @patch('asyncio.StreamWriter.drain', return_value=None)
    async def test_13_handle_server_choice_invalid(self, mock_drain, mock_write):
        server = MainServer()
        writer = MagicMock()

        await server.handle_server_choice('invalid_server', writer)

        mock_write.assert_called_with(b'Invalid server ID. Please try again.\n')
        mock_drain.assert_called()

    @patch('uuid.uuid4', return_value='test-server-id')
    @patch('main.MainServer.create_classic_server', return_value=5001)
    @patch('asyncio.StreamWriter.write')
    @patch('asyncio.StreamWriter.drain', return_value=None)
    async def test_14_create_new_server_classic(self, mock_drain, mock_write, mock_create_classic, mock_uuid):
        server = MainServer()
        writer = MagicMock()

        await server.create_new_server('Test Server', 'classic', writer)

        mock_create_classic.assert_called_with('Test Server')
        mock_write.assert_called_with(b'Server created successfully with ID: test-server-id. Share this ID with others.\n')
        mock_drain.assert_called()
        self.assertIn('test-server-id', server.servers)
        self.assertEqual(server.servers['test-server-id']['port'], 5001)

    @patch('uuid.uuid4', return_value='test-server-id')
    @patch('main.MainServer.create_competitive_server', return_value=5002)
    @patch('asyncio.StreamWriter.write')
    @patch('asyncio.StreamWriter.drain', return_value=None)
    async def test_15_create_new_server_competitive(self, mock_drain, mock_write, mock_create_competitive, mock_uuid):
        server = MainServer()
        writer = MagicMock()

        await server.create_new_server('Test Server', 'competitive', writer)

        mock_create_competitive.assert_called_with('Test Server')
        mock_write.assert_called_with(b'Server created successfully with ID: test-server-id. Share this ID with others.\n')
        mock_drain.assert_called()
        self.assertIn('test-server-id', server.servers)
        self.assertEqual(server.servers['test-server-id']['port'], 5002)

    @patch('asyncio.StreamWriter.write')
    @patch('asyncio.StreamWriter.drain', return_value=None)
    @patch('uuid.uuid4', return_value='test-server-id')
    async def test_16_create_new_server_wrong_mode(self, mock_uuid, mock_drain, mock_write):
        server = MainServer()
        writer = MagicMock()

        await server.create_new_server('Test Server', 'wrong_mode', writer)

        writer.write.assert_called_with(b'Invalid game mode. Try again. \n')
        writer.drain.assert_called()

if __name__ == '__main__':
    # Ejecutar los tests de manera personalizada
    suite = unittest.TestLoader().loadTestsFromTestCase(TestMainServer)
    for test in suite:
        if asyncio.iscoroutinefunction(test._testMethodName):
            asyncio.run(test)
        else:
            test()