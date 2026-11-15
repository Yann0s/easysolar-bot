"""Fine-tuning LoRA de LFM3-1.7B sur sft/train.jsonl (TRL + PEFT), d'après la recette officielle Liquid AI
(cookbook lfm3_sft_with_trl). Tourne sur Mac Apple Silicon (MPS), sur GPU CUDA ou, très lentement, sur CPU.
Sortie : sft/out/lora (adaptateur) et sft/out/merged (modèle fusionné, prêt pour la conversion GGUF).
Usage : python sft/train.py            (entraînement complet)
        python sft/train.py --smoke    (2 pas sur 4 exemples, pour vérifier que tout s'enchaîne)"""
import json, sys
from pathlib import Path

import torch
from datasets import Dataset
from peft import LoraConfig
from transformers import AutoModelForCausalLM, AutoTokenizer
from trl import SFTConfig, SFTTrainer

D = Path(__file__).resolve().parent
MODEL_ID = "LiquidAI/LFM3-1.7B"  # poids bf16 : la fusion LoRA doit se faire sur le modèle non quantifié
SMOKE = "--smoke" in sys.argv
device = "mps" if torch.backends.mps.is_available() else "cuda" if torch.cuda.is_available() else "cpu"

def load(name):
    """Format TRL « prompt / completion » : la perte ne porte que sur la réponse, raisonnement désactivé comme en production."""
    rows = [json.loads(l) for l in open(D / f"{name}.jsonl")]
    rows = [{"prompt": r["messages"][:-1], "completion": r["messages"][-1:],
             "chat_template_kwargs": {"enable_thinking": False}} for r in rows]
    return Dataset.from_list(rows[:4] if SMOKE else rows)

tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, trust_remote_code=True)
model = AutoModelForCausalLM.from_pretrained(MODEL_ID, dtype=torch.bfloat16, device_map={"": device}, trust_remote_code=True)

peft_config = LoraConfig(  # modules visés : ceux de la recette Liquid AI (attention + convolutions + MLP)
    r=16, lora_alpha=32, lora_dropout=0.05, task_type="CAUSAL_LM",
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "in_proj", "out_proj", "w1", "w2", "w3"])

args = SFTConfig(
    output_dir=str(D / "out" / "checkpoints"),
    num_train_epochs=3,              # 168 exemples : 3 passes ~ 63 pas de 8 exemples
    per_device_train_batch_size=1,   # prompts de 1 500 à 3 500 tokens ; batch 1 évite le padding
    gradient_accumulation_steps=8,
    learning_rate=2e-4, lr_scheduler_type="cosine", warmup_steps=0.05,
    max_length=4096,
    eval_strategy="epoch", per_device_eval_batch_size=1,
    logging_steps=5, save_strategy="no", report_to="none",
    bf16=False,  # poids déjà en bf16 ; pas d'autocast (support inégal sur MPS), les adaptateurs LoRA restent en float32
    max_steps=2 if SMOKE else -1,
)

trainer = SFTTrainer(model=model, args=args, train_dataset=load("train"), eval_dataset=load("dev"),
                     processing_class=tokenizer, peft_config=peft_config)
trainer.model.print_trainable_parameters()
print(f"Appareil : {device}")
trainer.train()
print("Perte sur dev :", trainer.evaluate()["eval_loss"])

# Contrôle rapide : une question du jeu dev, avant/après adaptateur
q = load("dev")[0]
prompt = tokenizer.apply_chat_template(q["prompt"], add_generation_prompt=True, tokenize=False, enable_thinking=False)
inputs = tokenizer(prompt, return_tensors="pt", add_special_tokens=False).to(device)
trainer.model.eval()
with torch.no_grad():
    out = trainer.model.generate(**inputs, max_new_tokens=200, do_sample=False, repetition_penalty=1.1)
print("\nQ :", q["prompt"][-1]["content"], "\nAttendu :", q["completion"][0]["content"],
      "\nObtenu  :", tokenizer.decode(out[0, inputs["input_ids"].shape[1]:], skip_special_tokens=True))

trainer.save_model(str(D / "out" / "lora"))
merged = trainer.model.merge_and_unload()
merged.save_pretrained(D / "out" / "merged")
tokenizer.save_pretrained(D / "out" / "merged")
print("Modèle fusionné :", D / "out" / "merged")
