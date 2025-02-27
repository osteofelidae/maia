"""
General input module class, mostly for testing
"""

# INTERNAL DEPENDENCIES
from src.modules.module import AsyncModule
from src.utils.config_utils import *

# DEPENDENCIES
from abc import abstractmethod


# INPUT MODULE CLASS
class InputModule(AsyncModule):

    def __init__(self, target, module_id_to_port_map: dict[str: int] = config.get("module_id_to_port_map")):
        super().__init__("input_module", module_id_to_port_map)

        self.add_thread("input_action", self._input_action)
        self._target = target
        self.connect(self._target)

    @abstractmethod
    def get_input(self) -> dict | str | None:
        """
        Get instruction dict to send; override in child classes
        :return:
        """
        return None

    def _input_action(self):

        while self._running:
            instruction = self.get_input()

            if instruction == "stop":
                self.send(
                    self._target,
                    {
                        "instruction_type": "halt"
                    }
                )
                self.stop()

            else:
                self.send(
                    self._target,
                    instruction
                )