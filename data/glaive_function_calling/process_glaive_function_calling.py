"""
Process glaive-function-calling-v2.json
"""

# INTERNAL DEPENDENCIES
from src.utils.path_utils import path, Path

# DEPENDENCIES
from datasets import load_dataset, Dataset
import json

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

    # Initialize output list
    data = []

    # For each raw data point
    for raw_point in raw_data:

        # Processed data point
        point = {}

        # If functions provided
        if FUNCTION_PROMPT_START in raw_point["system"]:
            functions = json.loads("[" + raw_point["system"].replace("SYSTEM: You are a helpful assistant with access to the following functions. Use them if required -", "").strip().replace("\n\n",",") + "]")
            for function in functions:
                if function["parameters"] is not None and function["parameters"].get("properties") is not None:
                    required_params = function["parameters"].get("required")
                    function["parameters"] = function["parameters"]["properties"]
                    if isinstance(required_params, list):
                        for key in function["parameters"]:
                            function["parameters"][key]["required"] = True if key in required_params else False

            functions = ", ".join([json.dumps(function) for function in functions])
            #functions = json.dumps(functions).replace("\"", "'")

            point["system"] = f"You are a helpful assistant. You have access to the following functions, which you may use if required: {functions}".replace("<|endoftext|>", "")

        # If functions not provided
        elif NO_FUNCTION_PROMPT_START in raw_point["system"]:
            point["system"] = "You are a helpful assistant. You do not have access to any functions."

        # If not recognized
        else:
            print("ERROR: " + raw_point)

        # Split chat
        chats = [message for message in raw_point["chat"].split("\n") if message.strip() != ""]
        print(chats)

        # Initialize processed history
        point["history"] = []

        # For message in raw history
        for message in chats:
            message = message.replace("<|endoftext|>", "").strip()
            if USER in message:
                message = message.replace(USER, "").strip()
                point["history"].append({
                    "role": "user",
                    "content": message
                })
            elif ASSISTANT in message:
                message = message.replace(ASSISTANT, "").replace("<functioncall>", "function call:").strip()
                point["history"].append({
                    "role": "assistant",
                    "content": message
                })
            elif FUNCTION_RESPONSE in message:
                message = message.replace(FUNCTION_RESPONSE, "").strip()
                point["history"].append({
                    "role": "system",
                    "content": message
                })
            else:
                point["history"][-1]["content"] += message

        data.append(point)

    # Stringify data
    data_string = [minify(json.dumps(point)) for point in data]

    # Convert to dataset
    data = [{"conversation": [{"role": "system", "content": point["system"]}] + point["history"]} for point in data]
    data = Dataset.from_list(data)

    # Save dataset
    data.to_json(path("data/glaive_function_calling/prepared.json"), indent=4)
    data.save_to_disk(path("data/glaive_function_calling/data"))
