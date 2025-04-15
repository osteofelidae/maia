from src.modules.builtin.llm_module import LLMAsyncModule
import time
if __name__ == "__main__":

    l = LLMAsyncModule()
    l.set_system_message("You are a helpful assistant with access to the following function(s), which you may use if required:\n{\n    \"name\": \"get_exchange_rate\",\n    \"description\": \"Get the exchange rate between two currencies\",\n    \"parameters\": {\n        \"base_currency\": {\n            \"type\": \"string\",\n            \"description\": \"The currency to convert from\",\n            \"required\": \"true\"\n        },\n        \"target_currency\": {\n            \"type\": \"string\",\n            \"description\": \"The currency to convert to\",\n            \"required\": \"true\"\n        }\n    }\n}")
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