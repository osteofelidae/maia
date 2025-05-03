"""
Train LLM
"""


# CONSTANTS
BASE_MODEL_PATH = "models/llama-3.2-1b-instruct"
DATASETS = [
    "data/glaive_function_calling/augmented"
]
OUTPUT_DIR = "models/maia-llm"


# INTERNAL DEPENDENCIES
from src.utils.path_utils import path, Path
from src.utils.config_utils import *


# DEPENDENCIES
import unsloth
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, Trainer, TrainingArguments, DataCollatorForLanguageModeling
from datasets import load_dataset, concatenate_datasets, load_from_disk, Dataset
from peft import PeftModel
from unsloth import FastLanguageModel
from trl import SFTTrainer



# MAIN
if __name__ == "__main__":

    # Load model
    model_path = path(BASE_MODEL_PATH)
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=str(model_path),
        max_seq_length=config.get("llm_max_new_tokens"),
        dtype=None,
        load_in_4bit=True
    )

    # Get peft model
    model = FastLanguageModel.get_peft_model(
        model,
        r=16,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj", ],
        lora_alpha=16,
        lora_dropout=0,  # Don't change - 0 is optimized
        bias="none",  # Don't change = 'none' is optimized
        use_gradient_checkpointing="unsloth",  # Don't change obviously
        random_state=3407,
        use_rslora=False,
        loftq_config=None
    )

    # Load datasets
    dataset_paths = [path(raw_path) for raw_path in DATASETS]
    datasets = [load_from_disk(str(dataset_path)) for dataset_path in dataset_paths]
    dataset = concatenate_datasets(datasets, axis=1)
    #dataset = Dataset.from_dict(dataset)

    # Format dataset
    def format_as_prompt(examples):
        # Get  conversations
        conversations = examples["conversation"]
        # Apply chat template and mappings
        text = [tokenizer.apply_chat_template(conversation,
                                                   tokenize=False,
                                                   add_generation_prompt=False)
                for conversation in conversations]
        # Return result
        return {"text": text}
    dataset = dataset.map(
        format_as_prompt,
        batched=True
    )

    # Train
    output_path = str(path(OUTPUT_DIR))
    data_collator = DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False)
    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=dataset,
        dataset_text_field="text",
        max_seq_length=config.get("llm_max_new_tokens"),
        dataset_num_proc=2,
        packing=False,  # TODO check - Can make training 5x faster for short sequences.
        data_collator=data_collator,
        args=TrainingArguments(
            per_device_train_batch_size=4,
            gradient_accumulation_steps=4,
            warmup_steps=5,
            max_steps=5000,
            learning_rate=2e-4,
            fp16=not unsloth.is_bfloat16_supported(),
            bf16=unsloth.is_bfloat16_supported(),
            logging_steps=1,
            optim="adamw_8bit",
            weight_decay=0.01,
            lr_scheduler_type="linear",
            seed=3407,
            output_dir=output_path,
        )
    )
    trainer.train()

    # Save
    model.save_pretrained(output_path)
    tokenizer.save_pretrained(output_path)