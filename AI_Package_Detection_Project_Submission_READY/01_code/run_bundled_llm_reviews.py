"""Review the bundled requests and lodash evidence reports with one local LLM load.

This is intended for the all-in-one Google Colab bundle. It reads only existing
evidence JSON files and writes reviewer outputs. It never installs, downloads,
or executes either target package.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.llm_review import build_review_messages, load_evidence_report, make_review_record


DEFAULT_MODEL = "Qwen/Qwen2.5-1.5B-Instruct"


def _load_model(model_name: str):
    try:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
    except ImportError as error:
        raise SystemExit("Install requirements-colab-llm.txt before running this program.") from error

    tokenizer = AutoTokenizer.from_pretrained(model_name)
    use_gpu = torch.cuda.is_available()
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        torch_dtype=torch.float16 if use_gpu else torch.float32,
        device_map="auto" if use_gpu else None,
    )
    if not use_gpu:
        model = model.to("cpu")
    return model, tokenizer, torch


def _generate(model, tokenizer, torch_module, messages: list[dict[str, str]], max_new_tokens: int) -> str:
    prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer([prompt], return_tensors="pt")
    inputs = {key: value.to(model.device) for key, value in inputs.items()}
    with torch_module.no_grad():
        generated = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            pad_token_id=tokenizer.eos_token_id,
        )
    new_tokens = generated[0][inputs["input_ids"].shape[1] :]
    return tokenizer.decode(new_tokens, skip_special_tokens=True).strip()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run local LLM reviews for bundled package evidence reports.")
    parser.add_argument("--requests-evidence", required=True)
    parser.add_argument("--lodash-evidence", required=True)
    parser.add_argument("--output-dir", default="outputs/llm_reviews")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--max-new-tokens", type=int, default=350)
    args = parser.parse_args()

    reports = {
        "requests": load_evidence_report(args.requests_evidence),
        "lodash": load_evidence_report(args.lodash_evidence),
    }
    expected_packages = {"requests": "requests-2.32.3", "lodash": "lodash-4.17.21"}
    for label, expected in expected_packages.items():
        observed = reports[label]["package"].get("package_name")
        if observed != expected:
            raise ValueError(f"Expected {expected} in {label} report, found {observed!r}")

    model, tokenizer, torch_module = _load_model(args.model)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    for label, report in reports.items():
        response = _generate(model, tokenizer, torch_module, build_review_messages(report), args.max_new_tokens)
        review = make_review_record(report, args.model, response)
        review_path = output_dir / f"{label}_llm_review.json"
        review_path.write_text(json.dumps(review, indent=2, ensure_ascii=True), encoding="utf-8")
        print(f"Wrote {label} review for {report['package']['package_name']}: {review_path.resolve()}")


if __name__ == "__main__":
    main()
