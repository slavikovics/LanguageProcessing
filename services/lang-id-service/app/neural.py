"""LR2's neural language-identification method: a single nn.Linear(D, C) +
softmax classifier trained on already-computed document embeddings (see
services/api's LanguageIdentificationService, which fetches embeddings from
nlp-service before calling this service — this module never touches
OpenRouter or any embedding model itself, keeping this service stateless
like nlp-service).

Deliberately linear (no hidden layer): a few hundred documents per language
can't statistically support the extra parameters a hidden layer would add
without overfitting. This is architecturally a real neural network (a real
training loop, a real loss curve for the report) while being mathematically
equivalent to L2-regularized multinomial logistic regression — the right
model for this data regime.

Training is chunked/resumable (train_step) rather than one long call: each
call runs a handful more epochs from a given weight state and returns the
updated state. That's what lets api's background task report live progress
(epoch N/total, current loss/accuracy) without this service needing to be
stateful or expose a streaming endpoint — every call here is a pure function
of its inputs.
"""

from __future__ import annotations

import time

import torch
from torch import nn


class LinearSoftmaxClassifier(nn.Module):
    def __init__(self, input_dim: int, num_classes: int) -> None:
        super().__init__()
        self.linear = nn.Linear(input_dim, num_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Raw logits. train_step feeds these to nn.CrossEntropyLoss
        (which expects logits, not probabilities); predict() below applies
        softmax itself to get the actual probability output."""
        return self.linear(x)


def _build_dataset(
    vectors_by_language: dict[str, list[list[float]]], classes: list[str]
) -> tuple[torch.Tensor, torch.Tensor]:
    class_index = {language: i for i, language in enumerate(classes)}
    xs: list[list[float]] = []
    ys: list[int] = []
    for language, vectors in vectors_by_language.items():
        for vector in vectors:
            xs.append(vector)
            ys.append(class_index[language])
    return torch.tensor(xs, dtype=torch.float32), torch.tensor(ys, dtype=torch.long)


def train_step(
    vectors_by_language: dict[str, list[list[float]]],
    *,
    weights: list[list[float]] | None = None,
    bias: list[float] | None = None,
    classes: list[str] | None = None,
    epochs: int = 10,
    learning_rate: float = 0.01,
    weight_decay: float = 1e-3,
) -> dict:
    """Runs `epochs` more steps of gradient descent, continuing from
    (weights, bias, classes) if given, or initializing fresh otherwise.
    Class order is fixed on the first call (sorted language keys) and must
    be passed back unchanged on every later chunk of the same training run.
    """
    if classes is None:
        classes = sorted(vectors_by_language.keys())
    if len(classes) < 2:
        raise ValueError("neural training needs at least 2 languages with training documents")

    x, y = _build_dataset(vectors_by_language, classes)
    input_dim = x.shape[1]
    model = LinearSoftmaxClassifier(input_dim, len(classes))
    if weights is not None and bias is not None:
        with torch.no_grad():
            model.linear.weight.copy_(torch.tensor(weights, dtype=torch.float32))
            model.linear.bias.copy_(torch.tensor(bias, dtype=torch.float32))

    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate, weight_decay=weight_decay)
    loss_fn = nn.CrossEntropyLoss()

    loss_curve_chunk: list[float] = []
    for _ in range(epochs):
        optimizer.zero_grad()
        logits = model(x)
        loss = loss_fn(logits, y)
        loss.backward()
        optimizer.step()
        loss_curve_chunk.append(float(loss.item()))

    with torch.no_grad():
        predicted = model(x).argmax(dim=1)
        train_accuracy = float((predicted == y).float().mean().item())

    return {
        "weights": model.linear.weight.detach().tolist(),
        "bias": model.linear.bias.detach().tolist(),
        "classes": classes,
        "loss_curve_chunk": loss_curve_chunk,
        "train_accuracy": train_accuracy,
    }


def _predict_proba(
    weights: list[list[float]], bias: list[float], classes: list[str], vector: list[float]
) -> dict[str, float]:
    """One forward pass -> {language: probability}. No GPU needed."""
    model = LinearSoftmaxClassifier(len(vector), len(classes))
    with torch.no_grad():
        model.linear.weight.copy_(torch.tensor(weights, dtype=torch.float32))
        model.linear.bias.copy_(torch.tensor(bias, dtype=torch.float32))
        logits = model(torch.tensor([vector], dtype=torch.float32))
        probabilities = torch.softmax(logits, dim=1)[0]
    return {language: float(p) for language, p in zip(classes, probabilities)}


def identify(
    weights: list[list[float]], bias: list[float], classes: list[str], vector: list[float]
) -> dict:
    """Same {distances, predicted_language, elapsed_ms} shape as the
    frequent-words/alphabetic endpoints: distance = 1 - probability, so
    "lower is closer" is the one argmin rule shared by every method (see
    api's app.domain.lang_id)."""
    started = time.perf_counter()
    probabilities = _predict_proba(weights, bias, classes, vector)
    elapsed_ms = (time.perf_counter() - started) * 1000
    distances = {language: 1.0 - p for language, p in probabilities.items()}
    return {
        "distances": distances,
        "probabilities": probabilities,
        "predicted_language": max(probabilities, key=probabilities.get),
        "elapsed_ms": elapsed_ms,
    }
