"""
Base module class.
"""

# INTERNAL DEPENDENCIES
from src.utils.config_utils import config

# DEPENDENCIES
from abc import ABC, abstractmethod
import socket
import threading
from queue import PriorityQueue, Empty
import json
import time
from json import JSONDecodeError
from datetime import datetime

# CONSTANTS
LOCALHOST = "127.0.0.1"

# ASYNC MODULE CLASS
class AsyncModule(ABC):
    """
    Template module class
    """

    def __init__(
            self,
            module_id: str,
            module_id_to_port_map: dict[str: int] = config.get("module_id_to_port_map"),
            instruction_priorities: dict[str: int] = config.get("instruction_priorities")
    ):
        """
        Constructor
        :param module_id: own module id
        :param module_id_to_port_map: map of module IDs to localhost ports
        :param instruction_priorities: map of instruction names to priorities
        """

        # Instance variables
        self._module_threads = {}  # Internal threads
        self._module_id_to_port_map = module_id_to_port_map  # Port numbers of each module
        self._module_id = module_id  # Own module id
        self._port = module_id_to_port_map.get(module_id)  # Own port
        self._connections = {}  # Outgoing sockets
        self._running = True  # Whether module is running
        self._instruction_queue = PriorityQueue()  # Queue of instructions
        self._instruction_priorities = instruction_priorities  # Priority of each instruction

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
    ) -> object:
        """
        Add a thread
        :param thread_id: thread id
        :param target: target function
        :param args: args to target function
        :return: self
        """

        # Error if thread already exists
        if thread_id in self._module_threads.keys():
            raise KeyError(f"Thread with ID {thread_id} already exists")

        # Create thread
        new_thread = threading.Thread(
            target=target,
            args=args
        )

        # Register thread
        self._module_threads.update({
            thread_id: new_thread
        })

        # Chaining
        return self

    def start(
            self,
            thread_id: str = None
    ) -> object:
        """
        Start specific thread, or all threads
        :param thread_id: id of thread; None if start all threads
        :return: self
        """

        # Start specific thread
        if thread_id:
            self._module_threads.get(thread_id).start()

        # Start all inactive threads
        else:
            self._running = True

            for module_thread in self._module_threads.values():
                if not module_thread.is_alive():
                    module_thread.start()

        # Chaining
        return self

    def stop(
            self
    ) -> object:
        """
        Stop all threads
        :return: self
        """

        # Stop
        self._running = False

        # Disconnect all
        self.disconnect()

        # Wait for all threads to end
        for module_id, module_thread in self._module_threads.items():
            try:
                module_thread.join()

            # If thread is already stopped
            except RuntimeError:
                pass

        # Chaining
        return self

    @abstractmethod
    def process_instruction(
            self,
            instruction
    ) -> None:
        """
        Process single instruction; override in derived classes
        :param instruction: instruction dict
        :return: None
        """

        return

    def _handle_instructions(self) -> None:
        """
        Loop over handling instruction
        :return: None
        """

        # While running
        while self._running:

            # Wait for instruction
            try:
                instruction = self._instruction_queue.get(block=True, timeout=config.get("loop_timeout"))[1]

                # Process instruction
                self.process_instruction(instruction)

            # Ignore empty
            except Empty:
                pass


    def _handle_client(
            self,
            client_sock
    ) -> None:
        """
        Handle client module (incoming connection)
        :param client_sock: client socket
        :return: None
        """

        # While running
        while self._running:

            try:
                # Get message
                try:
                    message = json.loads(client_sock.recv(4096).decode())

                    # Get priority
                    if message.get("instruction_type") in self._instruction_priorities.keys():
                        priority = self._instruction_priorities.get(message.get("instruction_type"))
                    else:
                        priority = config.get("default_instruction_priority")

                    # Add to queue
                    self._instruction_queue.put((priority, message))
                except JSONDecodeError:
                    pass

            # Ignore timeout
            except socket.timeout:
                pass


    def _handle_incoming_connections(self) -> None:
        """
        Receive connections from authorized modules
        :return: None
        """

        # Instantiate server obj
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.settimeout(config.get("loop_timeout"))
        server.bind((LOCALHOST, self._port))
        server.listen()

        # Receive connections while running
        while self._running:

            try:

                # Accept connection
                client_sock, client_addr = server.accept()
                client_sock.settimeout(config.get("loop_timeout"))
                client_ip, client_port = client_addr

                # Add and start thread
                thread_id = f"_client_handler_{client_port}"
                self.add_thread(
                    thread_id=thread_id,
                    target=self._handle_client,
                    args=(client_sock,)
                )
                self.start(thread_id)

            # Ignore timeout
            except socket.timeout:
                pass


    def connect(
            self,
            module_id: str
    ) -> object:
        """
        Connect to other module
        :param module_id: other module ID
        :return: self
        """

        # If module id provided
        if module_id:

            # If invalid module id, exception
            if not module_id in self._module_id_to_port_map.keys():
                raise KeyError(f"Module with ID {module_id} not found in port map")

        # Start connection attempt loop
        thread_id = f"_connection_attempt_loop_{module_id}"
        self.add_thread(
            thread_id,
            self._connection_attempt_loop,
            (module_id,)
        )
        self.start(thread_id)

        # Chaining
        return self

    def _connection_attempt_loop(
            self,
            module_id
    ):
        """
        Attempt to connect to a module until connected
        :param module_id: other module id
        :return: None
        """

        # Temp
        connected = False
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Attempt to connect until connected
        while not connected and self._running:

            try:
                # Connect
                client.connect((LOCALHOST, self._module_id_to_port_map.get(module_id)))

                # Store
                self._connections.update({
                    module_id: client
                })

                connected = True

            # If timed out, sleep
            except ConnectionRefusedError:
                time.sleep(config.get("loop_timeout"))


    def send(
            self,
            module_id: str,
            instruction: dict
    ) -> object:
        """
        Send message to other module
        :param module_id: id of module to send to
        :param instruction: instruction dict to send
        :return: self
        """

        # Change to string
        str_instruction = json.dumps(instruction)

        # If invalid module id, exception
        if not module_id in self._module_id_to_port_map.keys():
            raise KeyError(f"Module with ID {module_id} not found in port map")

        # Send
        self._connections.get(module_id).sendall(str_instruction.encode())

        # Chaining
        return self

    def disconnect(
            self,
            module_id: str = None
    ) -> object:
        """
        Disconnect from module, or all modules
        :param module_id: other module id
        :return: self
        """

        # Disconnect specific module
        if module_id:

            # If invalid module id, exception
            if not module_id in self._module_id_to_port_map.keys():
                raise KeyError(f"Module with ID {module_id} not found in port map")

            # Close socket
            self._connections.pop(module_id).close()

        # Disconnect all modules
        else:
            for module_id, sock in self._connections.items():
                sock.close()

        # Chaining
        return self

    def log(
            self,
            log_type: str,
            message: str
    ) -> None:
        """
        Register log message
        :param log_type: type of log
        :param message: log message
        :return:
        """

        # Get current time
        current_time = datetime.now()

        # Send formatted log
        self.send(
            "logger",
            {
                "instruction_type": "log",
                "message": f"{current_time} - {self._module_id} - {log_type.upper()} - {message}",
                "timestamp": str(int(current_time.timestamp()))
            }
        )

    def __str__(self):
        """
        To string method
        :return: str
        """

        # Literally just return the string
        return f"""=== MODULE {self._module_id} ({'not ' if not self._running else ''}running) ===

--- Threads ---:
{'\n'.join([f'{thread_id} ({'not ' if not self._module_threads.get(thread_id).is_alive() else ''}running)' for thread_id in self._module_threads.keys()])}

--- Outbound sockets ---:
{'\n'.join([f'{socket_id}' for socket_id in self._connections.keys()])}
=== END ===\n\n\n
"""