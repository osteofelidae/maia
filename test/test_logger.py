"""
Test src/modules/builtin/logger_module.py
"""

from abc import ABC
from src.modules.builtin.logger_module import *
from src.modules.input_module import *

class LoggerModuleTestInputModule(InputModule, ABC):

    def get_input(self) -> dict | str | None:
        x = input(">>> ")
        return x

    def process_instruction(
            self,
            instruction
    ) -> None:
        return

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
                print("send", instruction)
                self.log(
                    "test",
                    instruction
                )

m, t = None, None

mm = {
    "logger": m,
    "input": t
}

m = LoggerAsyncModule().update_module_map(mm).start()
t = LoggerModuleTestInputModule(target="logger").update_module_map(mm).start()


print(m)
print(t)