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
from transformers import AutoTokenizer, AutoModelForCausalLM


# FUNCTIONS
def compare_embeddings(
        embedding_1,
        embedding_2
):
    """
    Compare two embeddings
    :param embedding_1: First embedding
    :param embedding_2: Second embedding
    :return: Similarity score
    """

    # Return compared embedding
    return torch.nn.functional.cosine_similarity(embedding_1, embedding_2, dim=1).item()


# LLM MODULE
class LLMAsyncModule(AsyncModule, ABC):

    def __init__(
            self,
            module_id: str = "llm",
            model_path: str = config.get("llm_path"),
            message_history_length: int = config.get("llm_message_history_length"),
            rag_length: int = config.get("llm_rag_length"),
            hyde_length: int = config.get("llm_hyde_length"),
            **kwargs
    ):
        # TODO docstring

        # Formulate project dir
        if "$PROJECTDIR" in model_path:
            self.model_path = path(model_path.replace("$PROJECTDIR/", ""))  # Log file path
        else:
            self.model_path = Path(model_path)

        # Instance variables
        self.message_history_length = message_history_length
        self.rag_length = rag_length
        self.hyde_length = hyde_length

        # Initialize message history & backlog
        self.message_history = []
        self.message_history_backlog = []

        # Init
        super().__init__(
            module_id,
            **kwargs
        )

    def add_message(
            self,
            role: str = "user",
            content: str = ""
    ):
        # TODO docstring
        # Formulate input
        message = {
            "role": role,
            "content": content
        }

        # Add to message history
        self.message_history.append(message)

        # Trim message history
        self.message_history_backlog += self.message_history[:-self.message_history_length]
        self.message_history = self.message_history[-self.message_history_length:]


    def process_instruction(
            self,
            instruction
    ) -> None:
        """
        Process single instruction
        :param instruction:
        :return:
        """

        # Add message
        if instruction.get("instruction_type") == "add_message":

            # Add message
            self.add_message(
                role=instruction.get("role", "user"),
                content=instruction.get("content")
            )


    def _load_model(
            self
    ):
        # TODO docstring

        # Model, tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_path)
        self.tokenizer.pad_token = self.tokenizer.eos_token
        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_path,
            torch_dtype=torch.float16,
            device_map="auto"
        )

    def _get_embedding(
            self,
            text: str
    ):
        """
        Generate embedding from text
        :param text: Text to embed
        :return: Embedding
        """
        # Tokenize inputs
        inputs = self.tokenizer(text, return_tensors="pt", padding=True, truncation=True).to(self.model.device)

        # Get embeddings
        with torch.no_grad():
            outputs = self.model(**inputs)
        embedding = outputs.logits.mean(dim=1).to("cpu")

        # Return
        return embedding


    def _generate(
            self,
            message_history: list,
            max_new_tokens: int = config.get("llm_max_new_tokens"),
    ):

        # Tokenize input
        input_tokens = self.tokenizer.apply_chat_template(
            message_history,
            return_tensors="pt"
        ).to(self.model.device)

        # Generate output
        with torch.no_grad():
            output_tokens = self.model.generate(
                input_tokens,
                max_new_tokens=max_new_tokens,
                temperature=0.7,
                top_p=0.95,
                do_sample=True,
                eos_token_id=self.tokenizer.eos_token_id,
            )

        # Decode
        response_tokens = output_tokens[0][input_tokens.shape[-1]:]
        response_message = self.tokenizer.decode(
            response_tokens,
            skip_special_tokens=True
        ).removeprefix("assistant").strip()



        # Return
        return response_message


    def generate(
            self,
            add_message: bool = config.get("llm_add_generated_messages"),
            **kwargs
    ):
        # TODO docstring

        # Message history
        temp_message_history = self.message_history

        # If hyde or rag enabled
        if self.hyde_length or self.rag_length:

            # Get embeddings for all backlog
            for i in range(len(self.message_history_backlog)):

                # If not already calculated, calculate embedding
                if self.message_history_backlog[i].get("embedding") is None:
                    self.message_history_backlog[i]["embedding"] = self._get_embedding(
                        self.message_history_backlog[i]["content"]
                    )

            # Do rag if set
            rag_scores = []
            target = self._get_embedding(self.message_history[-1]["content"]).to("cpu")
            for message in self.message_history_backlog:
                rag_scores.append(compare_embeddings(target, message.get("embedding")))
            rag_score_indices = sorted(sorted(range(len(rag_scores)), key=lambda i: rag_scores[i], reverse=True)[:self.rag_length])

            # Add messages
            rag_messages = [self.message_history_backlog[i] for i in rag_score_indices]
            temp_message_history = rag_messages + self.message_history

            # Do HyDE if set
            hyde_response = self._generate(
                temp_message_history,
                **kwargs
            )
            hyde_scores = []
            target = self._get_embedding(hyde_response).to("cpu")
            for message in self.message_history_backlog:
                hyde_scores.append(compare_embeddings(target, message.get("embedding")))
            hyde_score_indices = sorted(range(len(rag_scores)), key=lambda i: hyde_scores[i], reverse=True)[:self.rag_length]

            # Join max indices
            all_indices = sorted(list(set(rag_score_indices+hyde_score_indices)))

            # Get messages
            rag_hyde_messages = [self.message_history_backlog[i] for i in all_indices]
            temp_message_history = rag_hyde_messages + self.message_history


        # Generate
        response_message = self._generate(
            temp_message_history,
            **kwargs
        )

        # Add to history if set
        if add_message:
            self.add_message(
                role="assistant",
                content=response_message
            )

        return response_message




    # TODO:
    # * Dump message history, on command and automatically