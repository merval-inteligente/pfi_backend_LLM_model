import os
import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

lista_noticias = [{
    "nivel_usuario": 1,
    "texto_original": (
        "La reciente baja del dólar en Argentina responde a un entramado de factores que combinaron ajustes de mercado, intervenciones oficiales y un endurecimiento de la política monetaria. Expertos relevados por iProfesional comentaron que la dinámica cambiaria se apoyó en la credibilidad de corto plazo, en la aparición de oferta de divisas cada vez que la cotización se acercaba al techo, y en las señales del Gobierno que reforzaron la idea de un control firme sobre el tipo de cambio. En paralelo, los analistas señalaron que el viraje en la política monetaria resultó determinante. La suba de encajes y el retiro de liquidez impactaron de lleno en el sistema financiero, llevando a un salto abrupto de tasas de interés que duplicaron sus niveles en cuestión de días. Esto generó un freno inmediato en la expansión del crédito privado, al mismo tiempo que aumentó la carga de intereses del Tesoro y acortó peligrosamente los plazos de la deuda. \
Asimismo, indicaron que la eliminación de instrumentos como las Lefis y el esquema de remonetización modificaron la forma en que el Tesoro y el Banco Central administraron los pesos disponibles. El financiamiento interno se volvió más costoso y complejo, mientras que el dólar oficial pasó a ser la principal variable de ajuste tras el levantamiento parcial del cepo. En ese escenario, el riesgo país se mantuvo elevado y el acceso al crédito externo continuó cerrado, lo que reforzó la dependencia de medidas locales. Para los especialistas, el resultado es un dólar contenido a costa de un programa económico mucho más contractivo. La estrategia estabilizó la divisa en el corto plazo, pero al precio de enfriar la actividad y deteriorar el crédito. Con vencimientos de deuda exigentes por delante y en vísperas de un proceso electoral clave, la gran incógnita quedó en torno a la sostenibilidad: hasta qué punto se podía sostener un esquema basado en tasas altas, encajes crecientes y un ajuste monetario que replicó la lógica de los programas con el FMI de años anteriores.")
}]

def _resolve_model_path():
    """
    Devuelve la ruta absoluta a la carpeta del modelo local: <directorio_de_este_py>/modelo_noticias_financieras
    """
    here = os.path.dirname(os.path.abspath(__file__))
    model_dir = os.path.join(here, "modelo_noticias_financieras")
    if not os.path.isdir(model_dir):
        raise FileNotFoundError(
            f"No se encontró la carpeta del modelo en: {model_dir}\n"
            "Verificá que exista y que contenga config.json, tokenizer.json y model.safetensors/pytorch_model.bin."
        )
    return model_dir

def load_model_tokenizer_device():
    # === Selección de dispositivo (ROCm reporta como 'cuda' si el torch es ROCm-enabled) ===
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    # === Ruta local del modelo ===
    model_path = _resolve_model_path()

    # === Carga de tokenizer y modelo ===
    tokenizer = AutoTokenizer.from_pretrained(model_path)
    model = AutoModelForSeq2SeqLM.from_pretrained(model_path)

    # Asegura pad_token si falta (algunos tokenizers no lo setean)
    if tokenizer.pad_token_id is None and tokenizer.eos_token_id is not None:
        tokenizer.pad_token = tokenizer.eos_token

    model.to(device)
    model.eval()

    return tokenizer, model, device

def adapt_news(tokenizer, model, device, level, text):
    # Prompt simple y consistente (ajustá si tu modelo espera otro formato)
    prompt = f"Explicá el siguiente texto financiero para un público general. Nivel {level}: {text}"

    inputs = tokenizer(
        prompt,
        return_tensors="pt",
        padding=True,
        truncation=True,
        max_length=2048  # subí a 1024 por textos largos
    ).to(device)

    # Generación. Ajustá parámetros a tu gusto/entrenamiento
    with torch.inference_mode():
        outputs = model.generate(
            **inputs,
            max_length=1024,
            num_beams=4,          # más determinista que sampling puro
            early_stopping=True,
            no_repeat_ngram_size=3
        )

    adapted = tokenizer.decode(outputs[0], skip_special_tokens=True)

    # Limpia prefijos duros si tu modelo a veces los agrega
    for to_strip in [
        "NOTICIA ADAPTADA AL NIVEL 1 :", "NOTICIA ADAPTADA AL NIVEL 2 :",
        "NOTICIA ADAPTADA AL NIVEL 3 :", "NOTICIA ADAPTADA AL NIVEL 4 :",
        "NOTICIA ADAPTADA AL NIVEL 5 :", "NOTICIA ADAPTADA AL NIVEL 1:",
        "NOTICIA ADAPTADA AL NIVEL 2:", "NOTICIA ADAPTADA AL NIVEL 3:",
        "NOTICIA ADAPTADA AL NIVEL 4:", "NOTICIA ADAPTADA AL NIVEL 5:"
    ]:
        if adapted.startswith(to_strip):
            adapted = adapted[len(to_strip):].strip()
            break

    return adapted

def get_adaptations_news(news_list):
    tokenizer, model, device = load_model_tokenizer_device()

    for item in news_list:
        nivel = item.get("nivel_usuario", 1)
        texto = item["texto_original"]
        item["texto_adaptado"] = adapt_news(tokenizer, model, device, nivel, texto)
        print("\n=== TEXTO ADAPTADO (Nivel", nivel, ") ===\n")
        print(item["texto_adaptado"])

if __name__ == "__main__":
    get_adaptations_news(lista_noticias)
