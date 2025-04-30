"""
Process glaive-function-calling-v2.json
"""

# INTERNAL DEPENDENCIES
from src.utils.path_utils import path, Path

# DEPENDENCIES
from datasets import load_dataset, Dataset
import json
import re

# CONSTANTS
FUNCTION_PROMPT_START = "SYSTEM: You are a helpful assistant with access to the following functions. Use them if required -"
NO_FUNCTION_PROMPT_START = "SYSTEM: You are a helpful assistant, with no access to external functions."

USER = "USER: "
ASSISTANT = "ASSISTANT: "
FUNCTION_RESPONSE = "FUNCTION RESPONSE: "

# FUNCTIONS
def minify(json_string):
    """
    Minify a json string
    :param json_string: The json string
    :return: Minified json string
    """

    return json.dumps(json.loads(json_string))


# MAIN
if __name__ == "__main__":

    # Open file
    with open(path("data/glaive_function_calling/glaive-function-calling-v2.json"), "r") as file:
        text = file.read()

    # Convert all lines to json
    raw_data = json.loads(text)

    # Format conversations
    def map_conversation(conversation):

        # Get new system message
        system_message = conversation.get("system")
        funcs_list = []
        if system_message.startswith(FUNCTION_PROMPT_START):
            funcs_raw = "[" + system_message.replace(FUNCTION_PROMPT_START, "").replace("}\n\n{", "},{") + "]"
            system_message = "You are a helpful assistant with access to the following function(s), which you may use if required:\n"

            # Get functions
            func_signatures = json.loads(funcs_raw)
            funcs = []

            for func_signature in func_signatures:
                func_name = func_signature.get("name")
                func_description = func_signature.get("description")

                func_params = {}

                if func_signature.get("parameters") is not None and func_signature["parameters"].get("properties") is not None:
                    raw_func_params = func_signature.get("parameters").get("properties") or {}
                    required_params = (func_signature.get("parameters").get("required")
                                       or func_signature.get("parameters").get("properties").get("required")
                                       or [])


                    for param_name, param_obj in raw_func_params.items():
                        if param_name != "required":
                            param_type = param_obj.get("type")
                            param_description = param_obj.get("description")
                            if type(required_params) is list:
                                param_required = "true" if param_name in required_params else "false"
                            else:
                                param_required = "true" if required_params else "false"

                            func_params.update({
                                param_name: {
                                    "type": param_type,
                                    "description": param_description,
                                    "required": param_required
                                }
                            })

                func_dict = {
                    "name": func_name,
                    "description": func_description,
                    "parameters": func_params
                }
                funcs.append(func_dict)

            funcs = [json.dumps(func, indent=4) for func in funcs]
            funcs_list = funcs
            funcs = ",\n".join(funcs)
            system_message += funcs


        elif system_message.startswith(NO_FUNCTION_PROMPT_START):
            system_message = "You are a helpful assistant with no access to functions."
        else:
            print("Invalid system message")

        # Result list with system message
        result = [{
            "content": system_message,
            "role": "system"
        }]

        # Split messages
        messages = []
        messages_raw = re.split(rf"(?={USER}|{ASSISTANT}|{FUNCTION_RESPONSE})", conversation.get("chat"))
        messages_raw = [message for message in messages_raw if message.strip() != ""]
        for message_raw in messages_raw:
            message = {}
            message_raw = message_raw.strip()
            if message_raw.startswith(USER):
                message["role"] = "user"
                message["content"] = message_raw.replace(USER, "")

            elif message_raw.startswith(ASSISTANT):
                message["role"] = "assistant"
                message["content"] = message_raw.replace(ASSISTANT, "").strip()
                if message["content"].startswith("<functioncall>"):
                    message["content"] = message["content"].replace("<functioncall>", "function call:").replace("'", "")

            elif message_raw.startswith(FUNCTION_RESPONSE):
                message["role"] = "system"
                message["content"] = message_raw.replace(FUNCTION_RESPONSE, "function response: ")
            else:
                return

            message["content"] = message["content"].replace("<|endoftext|>", "").strip()

            messages.append(message)

        result += messages

        return {"conversation": result, "functions": funcs_list}


    data = list(map(map_conversation, raw_data))
    data = [x for x in data if x]

    data = Dataset.from_list(data)
    data.to_json(path("data/glaive_function_calling/prepared.json"), indent=4)
    data.save_to_disk(path("data/glaive_function_calling/data"))

