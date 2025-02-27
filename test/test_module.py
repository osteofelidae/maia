"""
Test base module class.
"""

from src.modules.module import AsyncModule
from src.utils.config_utils import *

class PrinterModule(AsyncModule):

    def process_instruction(
            self,
            instruction
    ):
        if instruction.get("instruction_type") == "print":
            print(instruction.get("message"))
        elif instruction.get("instruction_type") == "halt":
            self.stop()

class InputModule(AsyncModule):

    def __init__(self, module_id_to_port_map: dict[str: int] = config.get("module_id_to_port_map")):
        super().__init__("input", module_id_to_port_map)

        self.add_thread("input_action", self.input_action)

    def process_instruction(
            self,
            instruction
    ) -> None:
        return

    def input_action(self):

        while self._running:
            x = input(">>>")

            if x == "stop":
                self.send(
                    "printer",
                    {
                        "instruction_type": "halt"
                    }
                )
                self.stop()

            else:
                self.send(
                    "printer",
                    {
                        "instruction_type": "print",
                        "message": x
                    }
                )

if __name__ == "__main__":

    id_to_port_map = {
        "printer": 3010,
        "input": 3011
    }

    p = PrinterModule(
        module_id="printer",
        module_id_to_port_map=id_to_port_map
    )
    i = InputModule(
        module_id_to_port_map=id_to_port_map
    )

    print(p)
    print(i)

    try:
        i.connect("printer").start()
        p.start()



        print(p)
        print(i)

    except KeyboardInterrupt:

        p.stop()
        i.stop()