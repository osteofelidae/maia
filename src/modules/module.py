"""
Base module class.
"""
from symtable import Function

# INTERNAL DEPENDENCIES
from src.utils.path_utils import *

# DEPENDENCIES
import socket
import threading

# CONSTANTS
LOCALHOST = "127.0.0.1"

class AsyncModule:
    """
    Template module class
    """

    def __init__(
            self,
            port: int,
            allowed_incoming_connections: list[str],
            id_to_port_map: map[str: int]  # TODO autodetect from 'custom'
    ):
        """
        Constructor
        :param port: own localhost port
        :param allowed_incoming_connections: list of IDs of allowed incoming connections
        :param id_to_port_map: map of module IDs to localhost ports
        """

        # Instance variables
        self.module_threads = {}  # Internal threads
        self._allowed_incoming_connections = allowed_incoming_connections  # Allowed incoming connection IDs
        self._id_to_port_map = id_to_port_map
        self.port = port
        self._connections = {}  # Outgoing sockets
        self._running = False  # Whether module is running

    def add_thread(
            self,
            thread_id: str,
            target,
            args: tuple
    ):
        """
        Add a thread
        :param thread_id: thread id
        :param target: target function
        :param args: args to target function
        :return: self
        """

        # Error if thread already exists
        if thread_id in self.module_threads.keys():
            return  # TODO exception

        # Create thread
        new_thread = threading.Thread(
            target=target,
            args=args
        )

        # Register thread
        self.module_threads.update({
            thread_id: new_thread
        })

        # Chaining
        return self

    def start(
            self,
            thread_id: str = None
    ):
        # TODO docstring

        # Start specific thread
        if thread_id:
            self.module_threads.get(thread_id).start()

        # Start all threads
        else:
            pass  # TODO start all threads


        # Chaining
        return self

    def stop(
            self,
            thread_id: str
    ):
        # TODO all

        # Chaining
        return self

    def _handle_client(
            self,
            client_sock,
            client_addr
    ):
        """
        Handle client module (incoming connection)
        :param client_sock: client socket
        :param client_addr: client address
        :return: None
        """

        # TODO handle message
        while True:
            try:
                message = client_sock.recv(1024).decode()
                if not message:
                    break  # If empty message, client disconnected
                print(f"Received from {client_addr}: {message}")
            except ConnectionResetError:
                break  # Handle unexpected disconnection

    def _recv_connections(self):
        """
        Receive connections from authorized modules
        :return: None
        """

        # Instantiate server obj
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind((LOCALHOST, self.port))
        server.listen()

        # TODO check valid socket

        # Receive connections while running
        while self._running:

            # Accept connection
            client_sock, client_addr = server.accept()
            client_ip, client_port = client_addr

            # Add and start thread
            module_id = [k for k, v in self._id_to_port_map.items() if v == client_port][0]
            thread_id = f"_client_handler_{module_id}"
            self.add_thread(
                thread_id=thread_id,
                target=self._handle_client,
                args=(client_sock, client_addr)
            )
            self.start_thread(thread_id)


    def _connect(
            self,
            module_id: str
    ):
        """
        Connect to other module
        :param module_id: other module ID
        :return: None
        """

        # Connect
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect((LOCALHOST, self._id_to_port_map.get(module_id)))

        # Store
        self._connections.update({
            module_id: client
        })


        return

    def _disconnect(
            self,
            module_id: str = None
    ):
        # TODO docstring

        # Disconnect specific module
        if module_id:
            self._connections.pop(module_id).close()

        # Disconnect all modules
        else:
            pass # TODO