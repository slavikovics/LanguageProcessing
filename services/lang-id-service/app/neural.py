
from __future__ import annotations

import time

import torch
from torch import nn


class LinearSoftmaxClassifier(nn.Module):
    def __init__(self, input_dim: int, num_classes: int) -> None:
        super().__init__()
        self.linear = nn.Linear(input_dim, num_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
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
