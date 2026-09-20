from __future__ import annotations

import os
import threading

_MODEL_NAME = os.environ.get("MT_MODEL_NAME", "Helsinki-NLP/opus-mt-en-fr")
_MAX_INPUT_TOKENS = 512
_MAX_OUTPUT_TOKENS = 256
_NUM_BEAMS = int(os.environ.get("MT_NUM_BEAMS", "1"))
_BATCH_SIZE = int(os.environ.get("MT_BATCH_SIZE", "32"))
_TORCH_THREADS = int(os.environ.get("MT_TORCH_THREADS", "4"))
_QUANTIZE = os.environ.get("MT_QUANTIZE", "1") == "1"

_tokenizer = None
_model = None
_lock = threading.Lock()


def _load():
    import torch
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

    torch.set_num_threads(_TORCH_THREADS)

    cache_dir = os.environ.get("MT_MODELS_DIR")
    tokenizer = AutoTokenizer.from_pretrained(_MODEL_NAME, cache_dir=cache_dir)
    model = AutoModelForSeq2SeqLM.from_pretrained(_MODEL_NAME, cache_dir=cache_dir)
    model.eval()
    if _QUANTIZE:
        model = torch.quantization.quantize_dynamic(model, {torch.nn.Linear}, dtype=torch.qint8)
    return tokenizer, model


def _get():
    global _tokenizer, _model
    if _model is None:
        with _lock:
            if _model is None:
                _tokenizer, _model = _load()
    return _tokenizer, _model


def warmup() -> None:
    _get()


def _translate_chunk(sentences: list[str]) -> list[str]:
    import torch

    tokenizer, model = _get()
    inputs = tokenizer(
        sentences,
        return_tensors="pt",
        padding=True,
        truncation=True,
        max_length=_MAX_INPUT_TOKENS,
    )
    with torch.no_grad():
        generated = model.generate(
            **inputs, max_new_tokens=_MAX_OUTPUT_TOKENS, num_beams=_NUM_BEAMS
        )
    return tokenizer.batch_decode(generated, skip_special_tokens=True)


def translate_batch(sentences: list[str]) -> list[str]:
    if not sentences:
        return []

    translations: list[str] = []
    for start in range(0, len(sentences), _BATCH_SIZE):
        translations.extend(_translate_chunk(sentences[start : start + _BATCH_SIZE]))
    return translations
