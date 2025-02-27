"""
Module to log to file
"""


# INTERNAL DEPENDENCIES
from src.modules.module import *
from src.utils.config_utils import *

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
            log_file_path: str = config.get("log_file_location"),
            log_file_save_interval = config.get("log_file_save_interval")
    ):
        """
        Constructor
        :param log_file_path: path to log file
        :param log_file_save_interval: save interval
        """

        super().__init__(module_id="logger")

        self._log_queue = PriorityQueue()  # Queue of log messages
        self._log_file_save_interval = log_file_save_interval

        if "$PROJECTDIR" in log_file_path:
            self._log_file_path = path(log_file_path.replace("$PROJECTDIR/", ""))  # Log file path
        else:
            self._log_file_path = Path(log_file_path)

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

        if instruction.get("instruction_type") == "log":
            priority = int(instruction.get("timestamp"))
            self._log_queue.put((priority, instruction.get("message")))

    def stop(
            self
    ):
        """
        Save and stop module
        :return: self
        """

        log_string = ""
        while not self._log_queue.empty():
            message = f"{self._log_queue.get_nowait()}\n"
            log_string += message

        # Save to file
        with open(self._log_file_path, "a") as file:
            file.write(log_string)

        return super().stop()

    def log(
            self,
            log_type,
            message
    ) -> None:
        current_time = datetime.now()
        self._log_queue.put((current_time.timestamp(), f"{current_time} - {self._module_id} - {log_type.upper()} - {message}"))