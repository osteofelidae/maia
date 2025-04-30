"""
Base module class.
"""

# INTERNAL DEPENDENCIES
from src.utils.config_utils import config

# DEPENDENCIES
from abc import ABC, abstractmethod
import threading
from queue import PriorityQueue, Empty
from datetime import datetime


# ASYNC MODULE CLASS
class AsyncModule(ABC):
    """
    Template module class
    """

    def __init__(
            self,
            module_id: str,
            module_map: dict[str: object] = None,
            instruction_priorities: dict[str: int] = config.get("instruction_priorities")
    ):
        """
        Constructor
        :param module_id: own module id
        :param module_map: map of module objects
        :param instruction_priorities: map of instruction names to priorities
        """

        # Instance variables
        self._module_threads = {}  # Internal threads
        self._module_id = module_id  # Own module id
        self._module_map = module_map if module_map else {}
        self._running = True  # Whether module is running
        self._instruction_queue = PriorityQueue()  # Queue of instructions
        self._instruction_priorities = instruction_priorities  # Priority of each instruction

        # Add threads
        self.add_thread(
            "_instruction_handler",
            self._handle_instructions
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
    ):
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

    def update_module_map(
            self,
            update_dict: dict
    ):
        """
        Update module map
        :param update_dict: dict to update with
        :return: self
        """

        # Update module map
        self._module_map.update(update_dict)

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

    def instruct(
            self,
            instruction: dict
    ):
        """
        Called externally to instruct this module
        :param instruction: instruction
        :return: self
        """

        # If not running, exception
        if not self._running:
            raise RuntimeError(f"Module '{self._module_id}' not running")

        # Get priority
        if instruction.get("instruction_type") in self._instruction_priorities.keys():
            priority = self._instruction_priorities.get(instruction.get("instruction_type"))
        else:
            priority = config.get("default_instruction_priority")

        # Add to queue
        self._instruction_queue.put((priority, instruction))

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

        # Get module object
        module = self._module_map.get(module_id)

        # Send if found
        if module:
            module.instruct(instruction)

        # Exception if not found
        else:
            raise KeyError(f"Module '{module_id}' not found")

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