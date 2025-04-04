from src.modules.builtin.llm_module import LLMAsyncModule
import time
if __name__ == "__main__":

    l = LLMAsyncModule()
    l._load_model()
    l.start()

    while True:
        inp = input(">>> ")
        l.instruct({
            "instruction_type": "add_message",
            "role": "user",
            "content": inp
        })
        time.sleep(0.1)
        print(l.generate())