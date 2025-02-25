import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from puzzle.main_server import MainServer
from common.social import Messages

@pytest.fixture(scope="function")
def main_server():
    return MainServer()

@pytest.fixture
def mock_writer():
    writer = Mock()
    writer.write = Mock()
    writer.drain = AsyncMock()
    return writer

@pytest.mark.asyncio
async def test_01_start_main_server(main_server):
    with patch.object(asyncio, 'start_server', new_callable=AsyncMock) as mock_start_server, \
         patch.object(main_server, 'initialize_puzzles', new_callable=AsyncMock) as mock_initialize_puzzles, \
         patch.object(main_server, 'listen_to_servers', new_callable=AsyncMock) as mock_listen_to_servers, \
         patch.object(main_server, 'run_server', new_callable=AsyncMock) as mock_run_server:
        
        # Simulate the server is listening
        mock_server = AsyncMock()
        mock_start_server.return_value = mock_server

        # Start the server
        await main_server.start_main_server()

        # Verify that the async functions were called
        mock_initialize_puzzles.assert_called_once()
        mock_listen_to_servers.assert_called_once()
        mock_run_server.assert_called_once()
        mock_start_server.assert_called_once_with(main_server.handle_new_player, main_server.host, main_server.port)

@pytest.mark.asyncio
async def test_02_initialize_puzzles(main_server):
    with patch('puzzle.logic.KryptoLogic.generar_puzzle', return_value='test_puzzle') as mock_generar_puzzle:
        await main_server.initialize_puzzles()
        assert not main_server.puzzle_queue.empty()
        assert main_server.puzzle_queue.qsize() == main_server.max_servers

@pytest.mark.asyncio
async def test_03_listen_to_servers_ok(main_server):
    mock_pipe = Mock()
    mock_pipe.poll.return_value = True
    mock_pipe.recv.return_value = Messages.OK
    main_server.process_pipes = {1: mock_pipe}

    mock_queue = Mock()
    mock_queue.put.return_value = None
    main_server.puzzle_queue = mock_queue

    with patch('puzzle.logic.KryptoLogic.generar_puzzle', return_value='test_puzzle') as mock_generar_puzzle:
        await main_server.listen_to_servers(test=True)

        mock_generar_puzzle.assert_called_once()
        mock_pipe.poll.assert_called_once()
        mock_pipe.recv.assert_called_once()
        mock_queue.put.assert_called_once_with('test_puzzle')

@pytest.mark.asyncio
async def test_04_listen_to_servers_kill(main_server):
    mock_pipe = Mock()
    mock_pipe.poll.return_value = True
    mock_pipe.recv.return_value = Messages.KILL
    mock_pipe.close.return_value = None
    main_server.process_pipes = {1: mock_pipe}

    mock_process = Mock()
    mock_process.terminate.return_value = None
    main_server.processes = {1: mock_process}

    await main_server.listen_to_servers(test=True)

    mock_pipe.poll.assert_called_once()
    mock_pipe.recv.assert_called_once()
    mock_pipe.close.assert_called_once()
    mock_process.terminate.assert_called_once()
    assert 1 not in main_server.process_pipes
    assert 1 not in main_server.processes

@pytest.mark.asyncio
async def test_05_listen_to_servers_error(main_server):
    mock_pipe = Mock()
    mock_pipe.poll.return_value = True
    mock_pipe.recv.return_value = Messages.ERROR
    main_server.process_pipes = {1: mock_pipe}

    await main_server.listen_to_servers(test=True)

    mock_pipe.poll.assert_called_once()
    mock_pipe.recv.assert_called_once()

@pytest.mark.asyncio
async def test_06_listen_to_servers_else(main_server):
    mock_pipe = Mock()
    mock_pipe.poll.return_value = True
    mock_pipe.recv.return_value = "test_message"
    main_server.process_pipes = {1: mock_pipe}

    main_server.processes = {1: Mock()}

    await main_server.listen_to_servers(test=True)

    mock_pipe.poll.assert_called_once()
    mock_pipe.recv.assert_called_once()

@pytest.mark.asyncio
async def test_07_handle_new_player_success(main_server, mock_writer):
    reader = AsyncMock()
    reader.read.return_value = b'test_user'

    with patch.object(main_server, 'handle_main_menu', new_callable=AsyncMock) as mock_handle_main_menu:
        await main_server.handle_new_player(reader, mock_writer)

        mock_writer.write.assert_called_with(Messages.LOGIN_SUCCESS.encode())
        await mock_writer.drain()
        mock_handle_main_menu.assert_called_once()

@pytest.mark.asyncio
async def test_08_handle_new_player_error(main_server, mock_writer):
    reader = AsyncMock()
    reader.read.side_effect = Exception

    with patch.object(main_server, 'handle_main_menu', new_callable=AsyncMock) as mock_handle_main_menu:
        await main_server.handle_new_player(reader, mock_writer)

        mock_writer.write.assert_called_with(Messages.LOGIN_ERROR.encode())
        await mock_writer.drain()
        mock_handle_main_menu.assert_called_once()

@pytest.mark.asyncio
async def test_09_handle_main_menu_1(main_server, mock_writer):
    reader = AsyncMock()
    reader.read.return_value = b'1|'

    with patch.object(main_server, 'send_server_list', new_callable=AsyncMock) as mock_send_server_list:
        await main_server.handle_main_menu(reader, mock_writer, test=True)

        mock_send_server_list.assert_called_once()

@pytest.mark.asyncio
async def test_10_handle_main_menu_2(main_server, mock_writer):
    reader = AsyncMock()
    reader.read.return_value = b'2|1234'

    with patch.object(main_server, 'handle_server_choice', new_callable=AsyncMock) as mock_handle_server_choice:
        await main_server.handle_main_menu(reader, mock_writer, test=True)

        mock_handle_server_choice.assert_called_once_with('1234', mock_writer)

@pytest.mark.asyncio
async def test_11_handle_main_menu_3(main_server, mock_writer):
    reader = AsyncMock()
    reader.read.return_value = b'3|Test Server|classic'

    with patch.object(main_server, 'create_new_server', new_callable=AsyncMock) as mock_create_new_server:
        await main_server.handle_main_menu(reader, mock_writer, test=True)

        mock_create_new_server.assert_called_once_with('Test Server', 'classic', mock_writer)

@pytest.mark.asyncio
async def test_12_handle_main_menu_exit(main_server, mock_writer):
    reader = AsyncMock()
    reader.read.return_value = b'exit'

    await main_server.handle_main_menu(reader, mock_writer, test=True)

    mock_writer.write.assert_called_with(b"Goodbye!")
    await mock_writer.drain()

@pytest.mark.asyncio
async def test_13_handle_main_menu_else(main_server, mock_writer):
    reader = AsyncMock()
    reader.read.return_value = b'message'

    await main_server.handle_main_menu(reader, mock_writer, test=True)

    mock_writer.write.assert_called_with(b"Invalid option. Please try again.\n")
    await mock_writer.drain()

@pytest.mark.asyncio
async def test_send_server_list(main_server, mock_writer):
    main_server.servers = {'1234': {'port': 5001, 'name': 'Test Server', 'mode': 'classic'}}
    await main_server.send_server_list(mock_writer)
    mock_writer.write.assert_called()
    await mock_writer.drain()

@pytest.mark.asyncio
async def test_handle_server_choice(main_server, mock_writer):
    main_server.servers = {'1234': {'port': 5001, 'name': 'Test Server', 'mode': 'classic'}}
    await main_server.handle_server_choice('1234', mock_writer)
    mock_writer.write.assert_called_with(b"Success|'Test Server'|5001.\n")
    await mock_writer.drain()

@pytest.mark.asyncio
async def test_create_new_server(main_server, mock_writer):
    await main_server.create_new_server('Test Server', 'classic', mock_writer)
    mock_writer.write.assert_called()
    await mock_writer.drain()
    assert 'Test Server' in [server['name'] for server in main_server.servers.values()]

if __name__ == '__main__':
    pytest.main(['-v', __file__])