"""Fine-tuning LoRA de Qwen3.5-0.8B sur sft/train.jsonl (TRL + PEFT).
Sortie : sft/out_qwen35/lora et sft/out_qwen35/merged.
Usage : .venv/bin/python sft/train_qwen35.py [--smoke]"""
import json
import sys
from pathlib import Path

import torch
from datasets import Dataset
from peft import LoraConfig
from transformers import AutoModelForCausalLM, AutoTokenizer
from trl import SFTConfig, SFTTrainer

D = Path(__file__).resolve().parent
OUT = D / "out_qwen35"
MODEL_ID = "Qwen/Qwen3.5-0.8B"
SMOKE = "--smoke" in sys.argv
device = "mps" if torch.backends.mps.is_available() else "cuda" if torch.cuda.is_available() else "cpu"


def load(name: str) -> Dataset:
    """Format TRL « prompt / completion » : perte uniquement sur la réponse, thinking désactivé."""
    rows = [json.loads(l) for l in open(D / f"{name}.jsonl", encoding="utf-8")]
    rows = [
        {
            "prompt": r["messages"][:-1],
            "completion": r["messages"][-1:],
            "chat_template_kwargs": {"enable_thinking": False},
        }
        for r in rows
    ]
    return Dataset.from_list(rows[:4] if SMOKE else rows)


tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, trust_remote_code=True)
model = AutoModelForCausalLM.from_pretrained(
    MODEL_ID, dtype=torch.bfloat16, trust_remote_code=True
).to(device)

peft_config = LoraConfig(
    r=16,
    lora_alpha=32,
    lora_dropout=0.05,
    task_type="CAUSAL_LM",
    target_modules="all-linear",
)

args = SFTConfig(
    output_dir=str(OUT / "checkpoints"),
    num_train_epochs=2,
    per_device_train_batch_size=1,
    gradient_accumulation_steps=8,
    learning_rate=2e-4,
    lr_scheduler_type="cosine",
    warmup_steps=0.05,
    max_length=4096,
    eval_strategy="epoch",
    per_device_eval_batch_size=1,
    logging_steps=5,
    save_strategy="no",
    report_to="none",
    bf16=False,
    max_steps=2 if SMOKE else -1,
)

trainer = SFTTrainer(
    model=model,
    args=args,
    train_dataset=load("train"),
    eval_dataset=load("dev"),
    processing_class=tokenizer,
    peft_config=peft_config,
)
trainer.model.print_trainable_parameters()
print(f"Appareil : {device}")
trainer.train()
print("Perte sur dev :", trainer.evaluate()["eval_loss"])

q = load("dev")[0]
prompt = tokenizer.apply_chat_template(
    q["prompt"], add_generation_prompt=True, tokenize=False, enable_thinking=False
)
inputs = tokenizer(prompt, return_tensors="pt", add_special_tokens=False).to(device)
trainer.model.eval()
with torch.no_grad():
    out = trainer.model.generate(**inputs, max_new_tokens=200, do_sample=False, repetition_penalty=1.1)
print(
    "\nQ :", q["prompt"][-1]["content"],
    "\nAttendu :", q["completion"][0]["content"],
    "\nObtenu  :", tokenizer.decode(out[0, inputs["input_ids"].shape[1]:], skip_special_tokens=True),
)

trainer.save_model(str(OUT / "lora"))
merged = trainer.model.merge_and_unload()
merged.save_pretrained(OUT / "merged")
tokenizer.save_pretrained(OUT / "merged")
print("Modèle fusionné :", OUT / "merged")
