"""
Augment prepare.json by combining examples
"""

# INTERNAL DEPENDENCIES
from src.utils.path_utils import path, Path


# DEPENDENCIES
from datasets import load_dataset, Dataset, load_from_disk, concatenate_datasets
import json
import re


# CONSTANTS
FUNCTION_SYSTEM_MESSAGE = "You are a helpful assistant with access to the following function(s), which you may use if required:\n"
NO_FUNCTION_SYSTEM_MESSAGE = "You are a helpful assistant with no access to functions."

# FUNCTIONS
def strip_system_message(example):
    example["conversation"] = example["conversation"][1:]
    return example

def combine_examples(batch):

    # If functions provided
    funcs = []
    if len(batch["functions"]) > 0:
        funcs = json.dumps([json.loads(func) for func_batch in batch["functions"] for func in func_batch], indent=4)
        system_message = FUNCTION_SYSTEM_MESSAGE + funcs
        messages = [{
            "content": system_message,
            "role": "system"
        }]
    else:
        messages = [{
            "content": NO_FUNCTION_SYSTEM_MESSAGE,
            "role": "system"
        }]
    messages += [message for message_batch in batch["conversation"] for message in message_batch]

    return {"conversation": [messages], "functions": [funcs]}


# MAIN
if __name__ == "__main__":

    orig_dataset = load_from_disk(path("data/glaive_function_calling/data"))

    orig_dataset = orig_dataset.map(strip_system_message, batched=False)

    augmented_datasets = []

    for i in range(1, 4):
        augmented_datasets.append(orig_dataset.map(combine_examples, batched=True, batch_size=i))

    dataset = concatenate_datasets(augmented_datasets)
    dataset = dataset.shuffle()
    print(dataset)
    dataset.to_json(path("data/glaive_function_calling/augmented.json"), indent=4)
    dataset.save_to_disk(path("data/glaive_function_calling/augmented"))