from src.modules.builtin.llm_module import LLMAsyncModule
from src.modules.builtin.extension_manager_module import ExtensionManagerAsyncModule
import time
if __name__ == "__main__":

    e = ExtensionManagerAsyncModule()
    e.start()

    funcs = e.get_extension_descriptions()

    print(funcs)

    l = LLMAsyncModule(function_call_function=e.function_call)
    l.set_system_message("You are a helpful assistant with access to the following function(s), which you must use if required:\n" + funcs)
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