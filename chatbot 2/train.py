import platform

import torch
from datasets import load_dataset
from transformers import TrainingArguments
from trl import SFTTrainer

try:
    from unsloth import FastLanguageModel
except ModuleNotFoundError as exc:
    raise SystemExit(
        "Unsloth installed nahi hai.\n"
        "Install command: pip install unsloth\n"
        "Note: Unsloth usually Linux + NVIDIA CUDA setup par best kaam karta hai."
    ) from exc

if platform.system() == "Darwin":
    raise SystemExit(
        "Aap macOS use kar rahe ho. Unsloth training zyadatar Linux + NVIDIA GPU par supported hoti hai.\n"
        "Train karne ke liye Linux GPU machine (local/Colab/cloud) use karo, fir model folder yahan copy karo."
    )

if not torch.cuda.is_available():
    raise SystemExit("CUDA GPU detect nahi hua. Is script ke liye NVIDIA CUDA GPU chahiye.")

# 1. Load Model & Tokenizer
model, tokenizer = FastLanguageModel.from_pretrained(
    model_name = "unsloth/llama-3-8b-bnb-4bit",
    max_seq_length = 2048,
    load_in_4bit = True,
)

# 2. Add LoRA Adapters
model = FastLanguageModel.get_peft_model(
    model,
    r = 16,
    target_modules = ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    lora_alpha = 16,
    lora_dropout = 0,
    bias = "none",
)

# 3. Formatting Logic (Ye model ko sikhayega ki prompt kaise read kare)
prompt_style = """Below is an instruction that describes a task, paired with an input that provides further context. Write a response that appropriately completes the request.

### Instruction:
{}

### Input:
{}

### Response:
{}"""

def formatting_prompter(examples):
    instructions = examples["instruction"]
    inputs       = examples["input"]
    outputs      = examples["output"]
    texts = []
    for instruction, input, output in zip(instructions, inputs, outputs):
        text = prompt_style.format(instruction, input, output)
        texts.append(text)
    return { "text" : texts, }

# 4. Load your train.json file
dataset = load_dataset("json", data_files="train.jsonl", split="train")
dataset = dataset.map(formatting_prompter, batched = True,)

# 5. Trainer Logic
trainer = SFTTrainer(
    model = model,
    tokenizer = tokenizer,
    train_dataset = dataset,
    dataset_text_field = "text",
    max_seq_length = 2048,
    dataset_num_proc = 2,
    args = TrainingArguments(
        per_device_train_batch_size = 2,
        gradient_accumulation_steps = 4,
        warmup_steps = 5,
        max_steps = 60, # Small dataset ke liye kaafi hai
        learning_rate = 2e-4,
        fp16 = not torch.cuda.is_bf16_supported(),
        bf16 = torch.cuda.is_bf16_supported(),
        logging_steps = 1,
        optim = "adamw_8bit",
        weight_decay = 0.01,
        lr_scheduler_type = "linear",
        seed = 3407,
        output_dir = "outputs",
    ),
)

# 6. Start Training
trainer_stats = trainer.train()

# 7. Save the Model
# Is folder ka path tum .env mein LOCAL_MODEL_PATH mein daal dena
model.save_pretrained("vernacular_fd_model") 
tokenizer.save_pretrained("vernacular_fd_model")

print("✅ Model trained and saved as 'vernacular_fd_model'")