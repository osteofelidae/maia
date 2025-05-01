"""
Module to manage LLM
"""

# INTERNAL DEPENDENCIES
from src.modules.module import AsyncModule
from src.utils.config_utils import *
from src.utils.path_utils import path, Path


# DEPENDENCIES
import torch
from unsloth import FastLanguageModel
import os


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
class LLMAsyncModule(AsyncModule):

    def __init__(
            self,
            module_id: str = "llm",
            model_path: str = config.get("llm_path"),
            message_history_length: int = config.get("llm_message_history_length"),
            rag_length: int = config.get("llm_rag_length"),
            hyde_length: int = config.get("llm_hyde_length"),
            function_call_function = None,
            **kwargs
    ):
        """

        :param module_id: it's in the name.
        :param model_path: path to model
        :param message_history_length: max length of message history before punting to archive
        :param rag_length: number of messages retrieved for RAG
        :param hyde_length: ditto for HyDE
        :param function_call_function: function to call on functioncall
        :param kwargs: kwargs
        """

        # Formulate project dir
        if "$PROJECTDIR" in model_path:
            self.model_path = path(model_path.replace("$PROJECTDIR/", ""))  # Log file path
        else:
            self.model_path = Path(model_path)

        # Instance variables
        self.message_history_length = message_history_length
        self.rag_length = rag_length
        self.hyde_length = hyde_length
        self.function_call_function = function_call_function

        # Initialize message history & backlog
        self.message_history = []
        self.message_history_backlog = []
        self.system_message = ""

        # Load model
        self._load_model(self.model_path)

        # Init
        super().__init__(
            module_id,
            **kwargs
        )

    def set_system_message(
            self,
            system_message
    ):
        """
        Set system message
        :param system_message: what do you think
        :return: self
        """

        self.system_message = system_message

        return self


    def add_message(
            self,
            role: str = "user",
            content: str = ""
    ):
        """
        Add message to history
        :param role: role (user|system|assistant)
        :param content: message content
        :return: self
        """
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

        return self


    def process_instruction(
            self,
            instruction
    ) -> None:
        """
        Process single instruction
        :param instruction: instruction dict
        :return: None
        """

        # Add message
        if instruction.get("instruction_type") == "add_message":

            # Add message
            self.add_message(
                role=instruction.get("role", "user"),
                content=instruction.get("content")
            )


    def _load_model(
            self,
            model_path
    ):
        """
        Load model
        :return:
        """

        # Set env for unsloth
        os.environ["TOKENIZERS_PARALLELISM"] = "true"

        # Model, tokenizer
        self.model, self.tokenizer = FastLanguageModel.from_pretrained(
            model_name=str(model_path),
            #max_seq_length=max_seq_length,
            dtype=None,
            load_in_4bit=True
        )

        FastLanguageModel.for_inference(self.model)

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
        """
        Generate with no frills
        :param message_history: message history list of dicts
        :param max_new_tokens: max new tokens
        :return: response str
        """

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
        """
        Generate with bells and whistles
        :param add_message: whether to add message to history
        :param kwargs: kwargs
        :return: response
        """

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
            rag_score_indices = sorted(sorted(range(len(rag_scores)), key=lambda j: rag_scores[j], reverse=True)[:self.rag_length])

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
            hyde_score_indices = sorted(range(len(rag_scores)), key=lambda j: hyde_scores[j], reverse=True)[:self.rag_length]

            # Join max indices
            all_indices = sorted(list(set(rag_score_indices+hyde_score_indices)))

            # Get messages
            rag_hyde_messages = [self.message_history_backlog[i] for i in all_indices]
            temp_message_history = rag_hyde_messages + self.message_history

        # Add system message if set
        if self.system_message:
            temp_message_history = [{
                "role": "system",
                "content": self.system_message
            }] + temp_message_history


        # Generate
        response_message = self._generate(
            temp_message_history,
            **kwargs
        )

        # Functioncall
        if response_message.startswith("function call: "):

            # Functioncall if able
            if self.function_call_function:

                print("functioncall")

                print(response_message)

                # Data
                function_call_data = json.loads(response_message.removeprefix("function call: ").strip())  # TODO error handling

                # Do function call
                function_response = self.function_call_function(
                    function_call_data.get("name", "default_function"),
                    function_call_data.get("arguments", {})
                )

                print(f"function response: {function_response}")

                # Add to temporary message history
                temp_message_history.append({
                    "role": "system",
                    "content": "function response: " + str(function_response)
                })

                # Regenerate
                response_message = self._generate(
                    temp_message_history,
                    **kwargs
                )

            # Else, error
            else:
                pass  # TODO error


        # Add to history if set
        if add_message:
            self.add_message(
                role="assistant",
                content=response_message
            )

        return response_message




    # TODO:
    # * Dump message history, on command and automatically
    # * generate at intervals