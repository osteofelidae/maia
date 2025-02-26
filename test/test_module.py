"""
Test base module class.
"""

from src.modules.module import AsyncModule

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

    def __init__(self, port: int, module_id_to_port_map: dict[str: int]):
        super().__init__(port, module_id_to_port_map)

        self.add_thread("input_action", self.input_action)

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
        port=id_to_port_map.get("printer"),
        module_id_to_port_map=id_to_port_map
    )
    i = InputModule(
        port=id_to_port_map.get("input"),
        module_id_to_port_map=id_to_port_map
    )

    try:

        p.start()

        i.connect("printer").start()

    except KeyboardInterrupt:

        p.stop()
        i.stop()