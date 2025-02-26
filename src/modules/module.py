"""
Base module class.
"""

# INTERNAL DEPENDENCIES
from src.utils.path_utils import *

# DEPENDENCIES
import socket
import threading
from queue import PriorityQueue, Empty
import json
import traceback

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
            id_to_port_map: dict[str: int],  # TODO autodetect from 'custom'
            instruction_priority = {}
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
        self._running = True  # Whether module is running
        self._instruction_queue = PriorityQueue()
        self._instruction_priority = instruction_priority

        # Add threads
        self.add_thread(
            "_instruction_handler",
            self._handle_instructions
        )
        self.add_thread(
            "_incoming_connection_handler",
            self._handle_incoming_connections
        )

    def add_thread(
            self,
            thread_id: str,
            target,
            args: tuple = ()
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
            target=self._thread_target_wrapper,
            args=(target, args)
        )

        # Register thread
        self.module_threads.update({
            thread_id: new_thread
        })

        # Chaining
        return self

    def _thread_target_wrapper(
            self,
            target,
            args
    ):
        """
        Wrapper for thread function
        :param target: target function
        :param args: args to target function
        :return: None
        """
        try:
            target(*args)
        except:
            if self._running:
                traceback.print_exc()

            else:
                pass


    def start(
            self,
            thread_id: str = None
    ):
        """
        Start specific thread, or all threads
        :param thread_id: id of thread; None if start all threads
        :return: self
        """

        # Start specific thread
        if thread_id:
            self.module_threads.get(thread_id).start()

        # Start all threads
        else:
            self._running = True

            for module_thread in self.module_threads.values():
                module_thread.start()

        # Chaining
        return self

    def stop(
            self
    ):
        """
        Stop all threads
        :return: self
        """

        # Stop
        self._running = False

        # Disconnect all
        self.disconnect()

        # Wait for all threads to end
        for module_id, module_thread in self.module_threads.items():
            try:
                module_thread.join()
            except:
                pass

        # Chaining
        return self

    def process_instruction(
            self,
            instruction
    ):
        """
        Process single instruction; override in derived classes
        :param instruction: instruction dict
        :return: None
        """

        pass

    def _handle_instructions(self):
        """
        Loop over handling instruction
        :return: None
        """

        # While running
        while self._running:

            # Wait for instruction
            try:
                instruction = self._instruction_queue.get(block=True, timeout=0.5)[1]

                # Process instruction
                self.process_instruction(instruction)

            except Empty:
                pass




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

        # While running
        while self._running:

            try:
                # Get message
                try:
                    message = json.loads(client_sock.recv(4096).decode())

                    # Get priority
                    if message.get("instruction_type") in self._instruction_priority.keys():  # TODO change to config
                        priority = self._instruction_priority.get(message.get("instruction_type"))
                    else:
                        priority = 100  # TODO change to config

                    # Add to queue
                    self._instruction_queue.put((priority, message))
                except:
                    pass

            except socket.timeout:
                pass


    def _handle_incoming_connections(self):
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
            client_sock.settimeout(0.5)
            client_ip, client_port = client_addr

            # Add and start thread
            thread_id = f"_client_handler_{client_port}"
            self.add_thread(
                thread_id=thread_id,
                target=self._handle_client,
                args=(client_sock, client_addr)
            )
            self.start(thread_id)


    def connect(
            self,
            module_id: str = None
    ):
        """
        Connect to other module
        :param module_id: other module ID
        :return: self
        """

        # If module id provided
        if module_id:

            # Connect
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.connect((LOCALHOST, self._id_to_port_map.get(module_id)))

            # Store
            self._connections.update({
                module_id: client
            })

        # Chaining
        return self

    def send(
            self,
            module_id: str,
            instruction: dict
    ):
        """
        Send message to other module
        :param module_id: id of module to send to
        :param instruction: instruction dict to send
        :return: self
        """

        # Change to string
        str_instruction = json.dumps(instruction)

        # Send
        self._connections.get(module_id).sendall(str_instruction.encode())

        # Chaining
        return self

    def disconnect(
            self,
            module_id: str = None
    ):
        """
        Disconnect from module, or all modules
        :param module_id: other module id
        :return: self
        """

        # Disconnect specific module
        if module_id:
            self._connections.pop(module_id).close()

        # Disconnect all modules
        else:
            for module_id, sock in self._connections.items():
                sock.close()

        # Chaining
        return self