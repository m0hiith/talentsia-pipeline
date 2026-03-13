"""
Fine-tuning script for Mistral 7B using Unsloth + QLoRA.
Trains on your JSONL script dataset to learn Hook → Body → CTA style.

Requirements:
  - GPU with ≥16GB VRAM (or Google Colab free T4)
  - pip install unsloth
  - JSONL dataset in ./dataset/scripts.jsonl

Usage:
  python train.py                              # Train with defaults
  python train.py --epochs 3 --lr 2e-4        # Custom training
  python train.py --dataset ./my_scripts.jsonl  # Custom dataset
"""

import argparse
import json
from pathlib import Path


def train(
    dataset_path: str = "./dataset/scripts.jsonl",
    model_name: str = "unsloth/mistral-7b-v0.3",
    output_dir: str = "./output/mistral-ft",
    epochs: int = 3,
    lr: float = 2e-4,
    batch_size: int = 4,
    max_seq_length: int = 2048,
    lora_r: int = 16,
    lora_alpha: int = 32,
    lora_dropout: float = 0.05,
):
    """Fine-tune Mistral 7B with Unsloth + QLoRA on script dataset."""

    # ─── Step 1: Load Model ──────────────────────
    print(f"📦 Loading {model_name}...")

    try:
        from unsloth import FastLanguageModel

        model, tokenizer = FastLanguageModel.from_pretrained(
            model_name=model_name,
            max_seq_length=max_seq_length,
            load_in_4bit=True,  # QLoRA — 4-bit quantization
            dtype=None,         # Auto-detect
        )
    except ImportError:
        print("❌ Unsloth not installed. Install with: pip install unsloth")
        print("   For Google Colab: pip install 'unsloth[colab-new]'")
        print("\nAlternatively, run on Google Colab with free T4 GPU:")
        print("   https://colab.research.google.com/")
        return

    # ─── Step 2: Add LoRA Adapters ───────────────
    print(f"🔧 Adding LoRA adapters (r={lora_r}, alpha={lora_alpha})...")

    model = FastLanguageModel.get_peft_model(
        model,
        r=lora_r,
        lora_alpha=lora_alpha,
        lora_dropout=lora_dropout,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                         "gate_proj", "up_proj", "down_proj"],
        bias="none",
        use_gradient_checkpointing="unsloth",
        random_state=42,
    )

    # ─── Step 3: Load Dataset ────────────────────
    print(f"📂 Loading dataset from {dataset_path}...")

    dataset = load_jsonl_dataset(dataset_path)
    print(f"   Found {len(dataset)} training examples")

    # Format for instruction tuning
    def format_example(example):
        messages = example.get("messages", [])
        text = ""
        for msg in messages:
            if msg["role"] == "system":
                text += f"### System:\n{msg['content']}\n\n"
            elif msg["role"] == "user":
                text += f"### User:\n{msg['content']}\n\n"
            elif msg["role"] == "assistant":
                text += f"### Assistant:\n{msg['content']}\n\n"
        return {"text": text}

    from datasets import Dataset
    train_dataset = Dataset.from_list([format_example(ex) for ex in dataset])

    # ─── Step 4: Train ───────────────────────────
    print(f"🚀 Starting training: {epochs} epochs, lr={lr}, batch={batch_size}...")

    from transformers import TrainingArguments
    from trl import SFTTrainer

    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=train_dataset,
        dataset_text_field="text",
        max_seq_length=max_seq_length,
        args=TrainingArguments(
            output_dir=output_dir,
            num_train_epochs=epochs,
            per_device_train_batch_size=batch_size,
            gradient_accumulation_steps=4,
            learning_rate=lr,
            weight_decay=0.01,
            warmup_steps=10,
            logging_steps=5,
            save_strategy="epoch",
            fp16=True,
            optim="adamw_8bit",
            seed=42,
            report_to="none",
        ),
    )

    trainer.train()

    # ─── Step 5: Save Model ──────────────────────
    print(f"💾 Saving model to {output_dir}...")
    model.save_pretrained(output_dir)
    tokenizer.save_pretrained(output_dir)

    print(f"\n✅ Training complete!")
    print(f"   Model saved to: {output_dir}")
    print(f"   Next step: python export_gguf.py --model {output_dir}")


def load_jsonl_dataset(path: str) -> list[dict]:
    """Load a JSONL dataset file."""
    data = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                data.append(json.loads(line))
    return data


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fine-tune Mistral 7B for script generation")
    parser.add_argument("--dataset", default="./dataset/scripts.jsonl")
    parser.add_argument("--model", default="unsloth/mistral-7b-v0.3")
    parser.add_argument("--output", default="./output/mistral-ft")
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--lr", type=float, default=2e-4)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--lora-r", type=int, default=16)
    args = parser.parse_args()

    train(
        dataset_path=args.dataset,
        model_name=args.model,
        output_dir=args.output,
        epochs=args.epochs,
        lr=args.lr,
        batch_size=args.batch_size,
        lora_r=args.lora_r,
    )
