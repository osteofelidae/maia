"""
Module to manage LLM
"""
"""
LLM module
"""

# INTERNAL DEPENDENCIES
from src.modules.module import AsyncModule
from src.utils.config_utils import *
from src.utils.path_utils import path, Path
from abc import ABC
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, GenerationConfig


# LLM MODULE
class LLMAsyncModule(AsyncModule, ABC):

    def __init__(
            self,
            module_id: str = "llm",
            model_path: str = config.get("llm_path"),
            **kwargs
    ):
        # TODO docstring

        # Formulate project dir
        if "$PROJECTDIR" in model_path:
            self.model_path = path(model_path.replace("$PROJECTDIR/", ""))  # Log file path
        else:
            self.model_path = Path(model_path)

        # Initialize message history
        self.message_history = []

        # Init
        super().__init__(
            module_id,
            **kwargs
        )

    def process_instruction(
            self,
            instruction
    ) -> None:
        """
        Process single instruction
        :param instruction:
        :return:
        """

        # Generate
        if instruction.get("instruction_type") == "add_message":

            # Formulate input
            message = {
                "role": instruction.get("role") if instruction.get("role") else "user",
                "content": instruction.get("content")
            }

            # Add to message history
            self.message_history.append(message)
            # TODO trim message history


    def _load_model(
            self
    ):
        # TODO docstring


        # Model, tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_path)
        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_path,
            torch_dtype=torch.float16,
            device_map="auto"
        )
        self.model = torch.compile(self.model)
        self.model.generation_config = GenerationConfig.from_pretrained(self.model_path)
        self.model.generation_config.pad_token_id = self.model.generation_config.eos_token_id

    def generate(
            self,
            max_new_tokens = config.get("llm_max_new_tokens"),
            add_message = config.get("llm_add_generated_messages")
    ):

        # Tokenize
        input_tensor = self.tokenizer.apply_chat_template(
            self.message_history,
            add_generation_prompt=True,
            return_tensors="pt"
        )

        # Generate
        outputs = self.model.generate(
            input_tensor.to(self.model.device),
            max_new_tokens=max_new_tokens,
            pad_token_id=self.tokenizer.pad_token_type_id,
            eos_token_id=self.tokenizer.eos_token_id
        )

        # Decode
        result = self.tokenizer.decode(
            outputs[0][input_tensor.shape[1]:],
            skip_special_tokens=True
        )

        # Add to message history if set
        if add_message:
            self.message_history.append({
                "role": "assistant",
                "content": result
            })

        return result


    # TODO:
    # * Load/unload model, on command and automatically
    # * Message history
    # * Dump message history, on command and automatically