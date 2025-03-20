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

    def __init__(self, module_id: str):

        super().__init__(module_id)

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



    p = PrinterModule(
        module_id="printer"
    )
    i = InputModule(
        module_id="input"
    )

    mm = {
        "printer": p,
        "input": i
    }

    p.update_module_map(mm)
    i.update_module_map(mm)

    print(p)
    print(i)

    try:
        i.start()
        p.start()



        print(p)
        print(i)

    except KeyboardInterrupt:

        p.stop()
        i.stop()