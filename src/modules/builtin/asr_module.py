"""
Module to manage ASR
"""

# INTERNAL DEPENDENCIES
from src.modules.module import AsyncModule
from src.utils.config_utils import *
from src.utils.path_utils import path, Path


# DEPENDENCIES
from transformers import WhisperForConditionalGeneration, WhisperProcessor


# ASR MODULE
class ASRAsyncModule(AsyncModule):

    def __init__(
            self,
            module_id: str = "asr",
            model_path: Path = config.get("asr_path")
    ):
        # TODO docstring

        # Formulate project dir
        model_path = str(model_path)
        if "$PROJECTDIR" in model_path:
            self.model_path = path(model_path.replace("$PROJECTDIR/", ""))  # Log file path
        else:
            self.model_path = Path(model_path)

        # Load model
        self._load_model(self.model_path)

        super().__init__(module_id)  # TODO

    def _load_model(
            self,
            model_path
    ):
        # TODO docstring
        # Initialize model
        self.model = WhisperForConditionalGeneration.from_pretrained(
            model_path,
            # low_cpu_mem_usage=True,
            use_safetensors=True,
            device_map="cuda",
        )

        # Initialize processor
        self.processor = WhisperProcessor.from_pretrained(model_path)


    def process_instruction(
            self,
            instruction
    ) -> None:
        # TODO docstring

        if instruction.get("instruction_type") == "do_asr":
            self._inference(
                instruction.get("audio")  # TODO send it forward
            )

    def _inference(
            self,
            audio,
            initial_prompt: str = None,
            temperature: float = 1.0  # TODO
    ):
        """
        Do inference
        :param audio: audio data
        :param initial_prompt: initial prompt
        :param temperature: inference temperature
        :return: text transcription
        """

        # Get and send input features to device
        input_features = self.processor.feature_extractor(
            audio,
            return_tensors="pt"
        ).input_features.to(self.model.device)

        # Tokenize and send prompt
        prompt_ids = self.processor.get_prompt_ids(initial_prompt, return_tensors="pt").to(self.model.device)

        # Do inference
        predicted_ids = self.model.generate(
            input_features,
            prompt_ids=prompt_ids,
            return_timestamps=False
        )

        # Decode result
        result = self.processor.tokenizer.batch_decode(
            predicted_ids,
            skip_special_tokens=True,
            decode_with_timestamps=False,
            temperature=temperature
        )[0].strip()

        # Return result
        return result