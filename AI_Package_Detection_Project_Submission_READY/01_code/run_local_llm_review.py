"""Run a free local Hugging Face LLM review over an existing evidence JSON report.

Designed for Google Colab with a GPU. This program loads a public model locally
in the runtime; no API key is required. It never executes package code.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.llm_review import build_review_messages, load_evidence_report, make_review_record


DEFAULT_MODEL = "Qwen/Qwen2.5-1.5B-Instruct"


def generate_local_review(messages: list[dict[str, str]], model_name: str, max_new_tokens: int) -> str:
    try:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
    except ImportError as error:
        raise SystemExit(
            "Missing local-LLM packages. Install requirements-colab-llm.txt first, preferably in Google Colab."
        ) from error

    tokenizer = AutoTokenizer.from_pretrained(model_name)
    dtype = torch.float16 if torch.cuda.is_available() else torch.float32
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        torch_dtype=dtype,
        device_map="auto" if torch.cuda.is_available() else None,
    )
    prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer([prompt], return_tensors="pt")
    if not torch.cuda.is_available():
        model = model.to("cpu")
    inputs = {key: value.to(model.device) for key, value in inputs.items()}
    with torch.no_grad():
        generated = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            pad_token_id=tokenizer.eos_token_id,
        )
    new_tokens = generated[0][inputs["input_ids"].shape[1] :]
    return tokenizer.decode(new_tokens, skip_special_tokens=True).strip()


def main() -> None:
    parser = argparse.ArgumentParser(description="Review an existing package-evidence report with a local LLM.")
    parser.add_argument("--evidence", required=True, help="JSON created by fuse_source_trace.py")
    parser.add_argument("--output", required=True, help="Destination JSON for the LLM review record")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--max-new-tokens", type=int, default=350)
    args = parser.parse_args()

    if args.max_new_tokens < 64 or args.max_new_tokens > 1_024:
        raise ValueError("--max-new-tokens must be between 64 and 1024")
    report = load_evidence_report(args.evidence)
    response = generate_local_review(build_review_messages(report), args.model, args.max_new_tokens)
    review = make_review_record(report, args.model, response)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(review, indent=2, ensure_ascii=True), encoding="utf-8")
    print(json.dumps(review, indent=2, ensure_ascii=True))
    print(f"\nWrote local LLM review to: {output.resolve()}")


if __name__ == "__main__":
    main()
