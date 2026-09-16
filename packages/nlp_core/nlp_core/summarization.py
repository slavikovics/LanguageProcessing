
from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence

from .tokenization import get_pipeline, lemmatize, split_sentences
from .weighting import term_frequencies

_PARAGRAPH_RE = re.compile(r"\n\s*\n+")


@dataclass(frozen=True)
class SentenceSpan:
    text: str
    doc_start: int
    doc_end: int
    paragraph_start: int
    paragraph_length: int


@dataclass(frozen=True)
class SentenceScore:
    index: int
    text: str
    weight: float


def split_paragraphs(text: str) -> list[str]:
    paragraphs = _PARAGRAPH_RE.split(text.strip())
    return [p.strip() for p in paragraphs if p.strip()]


def _sentence_spans_in_paragraph(paragraph: str) -> list[tuple[str, int, int]]:
    doc = get_pipeline()(paragraph)
    return [
        (sent.text.strip(), sent.start_char, sent.end_char)
        for sent in doc.sents
        if sent.text.strip()
    ]


def split_sentences_with_positions(text: str) -> list[SentenceSpan]:
    spans: list[SentenceSpan] = []
    search_from = 0
    for paragraph in split_paragraphs(text):
        paragraph_offset = text.find(paragraph, search_from)
        if paragraph_offset == -1:
            paragraph_offset = search_from
        search_from = paragraph_offset + len(paragraph)
        paragraph_length = len(paragraph)
        for sentence_text, para_start, para_end in _sentence_spans_in_paragraph(paragraph):
            spans.append(
                SentenceSpan(
                    text=sentence_text,
                    doc_start=paragraph_offset + para_start,
                    doc_end=paragraph_offset + para_end,
                    paragraph_start=para_start,
                    paragraph_length=paragraph_length,
                )
            )
    return spans


def sentence_document_position_weight(doc_start: int, document_length: int) -> float:
    if document_length <= 0:
        return 1.0
    return 1 - (doc_start / document_length)


def sentence_paragraph_position_weight(paragraph_start: int, paragraph_length: int) -> float:
    if paragraph_length <= 0:
        return 1.0
    return 1 - (paragraph_start / paragraph_length)


def modified_tfidf_sentence_score(
    sentence_terms: Iterable[str], term_weights: Mapping[str, float]
) -> float:
    counts = term_frequencies(sentence_terms)
    return sum(count * term_weights.get(term, 0.0) for term, count in counts.items())


def rank_sentences_algorithm(
    text: str, term_weights: Mapping[str, float]
) -> list[SentenceScore]:
    spans = split_sentences_with_positions(text)
    document_length = len(text)
    scores: list[SentenceScore] = []
    for index, span in enumerate(spans):
        posd = sentence_document_position_weight(span.doc_start, document_length)
        posp = sentence_paragraph_position_weight(span.paragraph_start, span.paragraph_length)
        score = modified_tfidf_sentence_score(lemmatize(span.text), term_weights)
        scores.append(
            SentenceScore(index=index, text=span.text, weight=posd * posp * score)
        )
    return scores


def _textrank_sentence_similarity(words_a: set[str], words_b: set[str]) -> float:
    if not words_a or not words_b:
        return 0.0
    overlap = len(words_a & words_b)
    if overlap == 0:
        return 0.0
    denom = math.log(len(words_a) + 1) + math.log(len(words_b) + 1)
    return overlap / denom if denom > 0 else 0.0


def rank_sentences_textrank(
    text: str,
    *,
    damping: float = 0.85,
    max_iterations: int = 100,
    tolerance: float = 1e-4,
) -> list[SentenceScore]:
    sentences = split_sentences(text)
    n = len(sentences)
    if n == 0:
        return []
    if n == 1:
        return [SentenceScore(index=0, text=sentences[0], weight=1.0)]

    term_sets = [set(lemmatize(sentence)) for sentence in sentences]
    weights = [
        [_textrank_sentence_similarity(term_sets[i], term_sets[j]) if i != j else 0.0 for j in range(n)]
        for i in range(n)
    ]
    out_weight_sums = [sum(row) for row in weights]

    scores = [1.0 / n] * n
    for _ in range(max_iterations):
        new_scores = []
        for i in range(n):
            incoming = 0.0
            for j in range(n):
                if i == j or out_weight_sums[j] == 0:
                    continue
                incoming += (weights[j][i] / out_weight_sums[j]) * scores[j]
            new_scores.append((1 - damping) / n + damping * incoming)
        delta = sum(abs(a - b) for a, b in zip(new_scores, scores))
        scores = new_scores
        if delta < tolerance:
            break

    return [SentenceScore(index=i, text=sentences[i], weight=scores[i]) for i in range(n)]


def _cosine(a: Sequence[float], b: Sequence[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def rank_sentences_by_embedding_centrality(
    sentences: Sequence[str], sentence_embeddings: Sequence[Sequence[float]]
) -> list[SentenceScore]:
    if len(sentences) != len(sentence_embeddings):
        raise ValueError("sentences and sentence_embeddings must be the same length")
    n = len(sentences)
    if n == 0:
        return []
    dimension = len(sentence_embeddings[0])
    centroid = [sum(vector[d] for vector in sentence_embeddings) / n for d in range(dimension)]
    return [
        SentenceScore(
            index=i, text=sentences[i], weight=_cosine(sentence_embeddings[i], centroid)
        )
        for i in range(n)
    ]


def rank_sentences_by_query_similarity(
    sentences: Sequence[str],
    sentence_embeddings: Sequence[Sequence[float]],
    query_embedding: Sequence[float],
) -> list[SentenceScore]:
    if len(sentences) != len(sentence_embeddings):
        raise ValueError("sentences and sentence_embeddings must be the same length")
    return [
        SentenceScore(
            index=i, text=sentences[i], weight=_cosine(sentence_embeddings[i], query_embedding)
        )
        for i in range(len(sentences))
    ]


def select_summary_sentences(
    scores: Sequence[SentenceScore], target_count: int
) -> list[SentenceScore]:
    top = sorted(scores, key=lambda s: s.weight, reverse=True)[:target_count]
    return sorted(top, key=lambda s: s.index)


def extract_keywords_from_weights(
    term_weights: Mapping[str, float], top_n: int | None = None
) -> list[str]:
    ranked = sorted(term_weights.items(), key=lambda pair: pair[1], reverse=True)
    return [term for term, _ in ranked[:top_n]]


@dataclass(frozen=True)
class KeywordGroup:
    term: str
    children: list[str]


_PHRASE_POS = {"NOUN", "PROPN", "ADJ"}


def _extract_candidate_phrases(text: str) -> list[list[str]]:
    doc = get_pipeline()(text)
    phrases: list[list[str]] = []
    current: list[str] = []
    for tok in doc:
        if tok.is_alpha and not tok.is_stop and tok.pos_ in _PHRASE_POS:
            current.append(tok.lemma_.lower())
        else:
            if len(current) >= 2:
                phrases.append(current)
            current = []
    if len(current) >= 2:
        phrases.append(current)
    return phrases


def extract_keyword_hierarchy(
    term_weights: Mapping[str, float],
    text: str,
    *,
    top_n: int | None = None,
    max_children: int = 5,
) -> list[KeywordGroup]:
    roots = extract_keywords_from_weights(term_weights, top_n)
    if not roots:
        return []

    phrase_words: dict[str, list[str]] = {}
    phrase_scores: dict[str, float] = {}
    for words in _extract_candidate_phrases(text):
        score = sum(term_weights.get(word, 0.0) for word in words)
        if score <= 0:
            continue
        phrase = " ".join(words)
        if phrase not in phrase_scores or score > phrase_scores[phrase]:
            phrase_scores[phrase] = score
            phrase_words[phrase] = words

    assigned: set[str] = set()
    groups: list[KeywordGroup] = []
    for root in roots:
        candidates = sorted(
            (
                (phrase, score)
                for phrase, score in phrase_scores.items()
                if phrase not in assigned and root in phrase_words[phrase]
            ),
            key=lambda pair: pair[1],
            reverse=True,
        )
        children = [phrase for phrase, _ in candidates[:max_children]]
        assigned.update(children)
        groups.append(KeywordGroup(term=root, children=children))
    return groups
