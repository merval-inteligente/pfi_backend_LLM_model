import torch
import gc
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM, default_data_collator
from datasets import Dataset
from torch.utils.data import DataLoader
from tqdm import tqdm
import pandas as pd
import numpy as np
import os

# === Configuración general ===

checkpoint = "mrm8488/bert2bert_shared-spanish-finetuned-summarization"
if torch.cuda.is_available():
    device = torch.device("cuda")
    print("🟢 Usando GPU CUDA:", torch.cuda.get_device_name(0))
else:
    device = torch.device("cpu")
    print("🟡 Advertencia: No se detectó GPU CUDA. Usando CPU.")

# === Dataset ===
df = pd.read_json("pfi_backend_LLM_model\workers\machine_learning_worker\Dataset_con_temas.jsonl", lines=True)
# Si quieres entrenar con todo el dataset, comenta la siguiente línea:
# df = df.sample(50, random_state=42)
dataset = Dataset.from_pandas(df[["texto_original", "nivel", "texto_adaptado"]])

# === Tokenizador ===
tokenizer = AutoTokenizer.from_pretrained(checkpoint)

def preprocess(example):
    # dentro de preprocess(...)
    temas = example.get("temas_detectados", [])
    temas_txt = ", ".join(temas) if temas else "otros"
    prompt = (
        f"Temas: {temas_txt}. "
        f"Explicá el siguiente texto financiero para un público general. "
        f"Nivel {example['nivel']}: {example['texto_original']}"
    )
    
    inputs = tokenizer(prompt, truncation=True, padding="max_length", max_length=512)
    targets = tokenizer(example["texto_adaptado"], truncation=True, padding="max_length", max_length=512)
    inputs["labels"] = targets["input_ids"]
    return inputs

tokenized_dataset = dataset.map(preprocess, remove_columns=dataset.column_names)
tokenized_dataset.set_format(type="torch")

# === Cargar modelo ===
model = AutoModelForSeq2SeqLM.from_pretrained(checkpoint, use_safetensors=False)
model.to(device)

# === Data collator robusto ===
def safe_data_collator(features):
    for feature in features:
        if isinstance(feature.get("labels"), list):
            feature["labels"] = torch.tensor(np.array(feature["labels"]), dtype=torch.long)
    return default_data_collator(features)

dataloader = DataLoader(
    tokenized_dataset,
    batch_size=1,  # ✅ Usar 1 en CPU
    shuffle=True,
    collate_fn=safe_data_collator
)

# === Entrenamiento ===
model.train()
optimizer = torch.optim.AdamW(model.parameters(), lr=5e-5)
epochs = 2  # Recomendado para evitar sobreajuste en datasets pequeños

for epoch in range(epochs):
    print(f"\n🔁 Época {epoch+1}/{epochs}")
    loop = tqdm(dataloader, leave=True)
    total_loss = 0

    for batch in loop:
        batch = {k: v.to(device) for k, v in batch.items()}
        outputs = model(**batch)
        loss = outputs.loss
        loss.backward()
        optimizer.step()
        optimizer.zero_grad()

        gc.collect()  # 🔁 Limpiar memoria manualmente

        total_loss += loss.item()
        loop.set_description(f"Epoch {epoch+1}")
        loop.set_postfix(loss=loss.item())

    avg_loss = total_loss / len(dataloader)
    print(f"📉 Pérdida promedio: {avg_loss:.4f}")

    # 💾 Guardar checkpoint intermedio
    os.makedirs(f"./checkpoints/epoch_{epoch+1}", exist_ok=True)
    model.save_pretrained(f"./checkpoints/epoch_{epoch+1}")
    tokenizer.save_pretrained(f"./checkpoints/epoch_{epoch+1}")

# === Guardar modelo final ===
model.save_pretrained("pfi_backend_LLM_model/workers/machine_learning_worker/modelo_noticias_financieras")
tokenizer.save_pretrained("pfi_backend_LLM_model/workers/machine_learning_worker/modelo_noticias_financieras")
print("✅ Modelo guardado en pfi_backend_LLM_model/workers/machine_learning_worker/modelo_noticias_financieras")
print("🛑 Entrenamiento finalizado")