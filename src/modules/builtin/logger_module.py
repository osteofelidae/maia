"""
Module to log to file
"""

# INTERNAL DEPENDENCIES
from src.modules.module import AsyncModule
from src.utils.config_utils import config
from src.utils.path_utils import path, Path

# DEPENDENCIES
from queue import PriorityQueue
import time
from datetime import datetime

# LOGGER ASYNC MODULE CLASS
class LoggerAsyncModule(AsyncModule):
    """
    Logs to file
    """

    def __init__(
            self,
            module_id = "logger",
            log_file_path: str = config.get("log_file_location"),
            log_file_save_interval = config.get("log_file_save_interval"),
            **kwargs
    ):
        """
        Constructor
        :param log_file_path: path to log file
        :param log_file_save_interval: save interval
        """
         # init super
        super().__init__(module_id=module_id, **kwargs)

        # Instance variables
        self._log_queue = PriorityQueue()  # Queue of log messages
        self._log_file_save_interval = log_file_save_interval

        # Formulate project dir
        if "$PROJECTDIR" in log_file_path:
            self._log_file_path = path(log_file_path.replace("$PROJECTDIR/", ""))  # Log file path
        else:
            self._log_file_path = Path(log_file_path)

        # Add save loop thread
        self.add_thread(
            thread_id="_save_log_loop",
            target=self._save_log_loop
        )

    def _save_log_loop(self):
        """
        Loop and save log
        :return: None
        """

        # While running
        while self._running:

            # Add everything to string
            log_string = ""
            while not self._log_queue.empty():

                message = f"{self._log_queue.get_nowait()[1]}\n"
                log_string += message

            # Save to file
            with open(self._log_file_path, "a") as file:
                file.write(log_string)

            # Sleep
            time.sleep(self._log_file_save_interval)

    def process_instruction(
            self,
            instruction
    ):
        """
        Overridden process_instruction method
        :param instruction: instruction to process
        :return: None
        """

        # If log instruction
        if instruction.get("instruction_type") == "log":
            priority = int(instruction.get("timestamp"))
            self._log_queue.put((priority, instruction.get("message")))
            print(instruction.get("message"))


    def stop(
            self
    ):
        """
        Save and stop module
        :return: self
        """

        # Get log string
        log_string = ""
        while not self._log_queue.empty():
            message = f"{self._log_queue.get_nowait()}\n"
            log_string += message

        # Save to file
        with open(self._log_file_path, "a") as file:
            file.write(log_string)

        # Stop and return self
        return super().stop()

    def log(
            self,
            log_type,
            message
    ) -> None:
        """
        Override log function since it is stupid for logger to connect to itself
        :param log_type: see overriden
        :param message: see overridden
        :return: see overriden
        """

        # Add to log queue
        current_time = datetime.now()
        self._log_queue.put((current_time.timestamp(), f"{current_time} - {self._module_id} - {log_type.upper()} - {message}"))