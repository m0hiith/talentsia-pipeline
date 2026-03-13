"""
Export fine-tuned model to GGUF format for use with Ollama.

Steps:
  1. Convert fine-tuned model to GGUF (Q4_K_M quantization)
  2. Create Ollama Modelfile with system prompt
  3. Register with Ollama: ollama create talentsia-writer

Usage:
  python export_gguf.py                           # Export with defaults
  python export_gguf.py --model ./output/mistral-ft  # Custom model path
"""

import argparse
import shutil
from pathlib import Path


MODELFILE_TEMPLATE = '''FROM {gguf_path}

# Talentsia Writer — Fine-tuned Mistral 7B
PARAMETER temperature 0.7
PARAMETER top_p 0.9
PARAMETER num_predict 256
PARAMETER stop "### User:"
PARAMETER stop "### System:"

SYSTEM """
## IDENTITY You are the Talentsia Content Writer. You create viral Instagram Reels scripts for the @talentsia page about AI, tech and jobs.

## FORMAT (ALWAYS FOLLOW)
HOOK: 1-2 sentences. Start with shock/curiosity/fear/FOMO.
BODY: 3-5 short punchy paragraphs. No jargon. Real data points.
CTA: 1-2 lines. Direct action. Always end with #Talentsia.

## RULES
- Max 60-90 words
- Conversational, never robotic
- Every line must earn its place
- Write for SPEAKING, not reading
"""
'''


def export(
    model_path: str = "./output/mistral-ft",
    output_path: str = "./output/gguf",
    model_name: str = "talentsia-writer",
    quantization: str = "q4_k_m",
):
    """Export fine-tuned model to GGUF and create Ollama Modelfile."""

    model_dir = Path(model_path)
    output_dir = Path(output_path)
    output_dir.mkdir(parents=True, exist_ok=True)

    # ─── Step 1: Convert to GGUF ─────────────────
    print(f"📦 Converting {model_path} to GGUF ({quantization})...")

    try:
        from unsloth import FastLanguageModel

        model, tokenizer = FastLanguageModel.from_pretrained(
            model_name=str(model_dir),
            max_seq_length=2048,
            load_in_4bit=True,
        )

        gguf_path = output_dir / f"{model_name}.{quantization}.gguf"

        # Save as GGUF
        model.save_pretrained_gguf(
            str(output_dir),
            tokenizer,
            quantization_method=quantization,
        )

        print(f"✅ GGUF saved to: {gguf_path}")

    except ImportError:
        print("⚠️ Unsloth not available — using manual conversion")
        print("   Run this on a GPU machine (Colab/RunPod):")
        print(f"   python convert_hf_to_gguf.py {model_path}")
        print(f"   OR: pip install unsloth && python export_gguf.py")

        # Create placeholder GGUF path for Modelfile
        gguf_path = output_dir / f"{model_name}.{quantization}.gguf"
        gguf_path.write_text("PLACEHOLDER — run on GPU machine")

    # ─── Step 2: Create Ollama Modelfile ─────────
    modelfile_path = output_dir / "Modelfile"
    modelfile_content = MODELFILE_TEMPLATE.format(gguf_path=gguf_path.name)
    modelfile_path.write_text(modelfile_content)
    print(f"📄 Modelfile created: {modelfile_path}")

    # ─── Step 3: Print Ollama commands ───────────
    print(f"\n🚀 To register with Ollama, run:")
    print(f"   cd {output_dir}")
    print(f"   ollama create {model_name} -f Modelfile")
    print(f"\n   Then test with:")
    print(f"   ollama run {model_name} 'News: OpenAI releases GPT-5. Write a Reel script.'")
    print(f"\n   And use in pipeline:")
    print(f"   export OLLAMA_MODEL={model_name}")

    return str(gguf_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export fine-tuned model to GGUF for Ollama")
    parser.add_argument("--model", default="./output/mistral-ft")
    parser.add_argument("--output", default="./output/gguf")
    parser.add_argument("--name", default="talentsia-writer")
    parser.add_argument("--quant", default="q4_k_m", choices=["q4_k_m", "q5_k_m", "q8_0", "f16"])
    args = parser.parse_args()

    export(
        model_path=args.model,
        output_path=args.output,
        model_name=args.name,
        quantization=args.quant,
    )
