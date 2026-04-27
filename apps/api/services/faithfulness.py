from __future__ import annotations

import re


STOPWORDS = {
    "a", "al", "ante", "antes", "bajo", "con", "contra", "de", "del", "desde", "durante", "el", "en",
    "entre", "es", "esta", "este", "hay", "la", "las", "lo", "los", "mes", "meses", "para", "pero",
    "por", "que", "se", "sin", "su", "sus", "un", "una", "uno", "unos", "unas", "y",
}


def _tokens(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9áéíóúñ]{3,}", text.lower())
        if token not in STOPWORDS
    }


def _matches_token(answer_token: str, chunk_token: str) -> bool:
    if answer_token == chunk_token:
        return True
    if len(answer_token) >= 5 and len(chunk_token) >= 5:
        return answer_token.startswith(chunk_token[:5]) or chunk_token.startswith(answer_token[:5])
    return False


def _overlap_score(answer_tokens: set[str], chunk_tokens: set[str]) -> float:
    if not answer_tokens or not chunk_tokens:
        return 0.0

    matched = 0
    for answer_token in answer_tokens:
        if any(_matches_token(answer_token, chunk_token) for chunk_token in chunk_tokens):
            matched += 1
    return matched / len(answer_tokens)


def compute_faithfulness(answer: str, chunks: list[dict]) -> float:
    if not chunks or not answer or not answer.strip():
        return 0.0

    answer_without_citations = re.sub(r"\[[^\]]+\]", " ", answer)
    answer_tokens = _tokens(answer_without_citations)
    if not answer_tokens:
        return 0.0

    chunk_map = {}
    all_chunk_tokens: set[str] = set()
    for chunk in chunks:
        chunk_id = str(chunk.get("chunk_id") or "")
        chunk_text = chunk.get("text") or chunk.get("fragmento_exacto") or chunk.get("excerpt") or ""
        chunk_tokens = _tokens(chunk_text)
        if not chunk_tokens:
            continue
        if chunk_id:
            chunk_map[chunk_id] = chunk_tokens
        all_chunk_tokens.update(chunk_tokens)

    cited_chunk_ids = re.findall(r"\[([^\]]+)\]", answer)
    if cited_chunk_ids:
        cited_tokens: set[str] = set()
        for chunk_id in cited_chunk_ids:
            cited_tokens.update(chunk_map.get(chunk_id, set()))
        if cited_tokens:
            return round(_overlap_score(answer_tokens, cited_tokens), 4)

    best_overlap = 0.0
    for chunk_tokens in chunk_map.values():
        overlap = _overlap_score(answer_tokens, chunk_tokens)
        if overlap > best_overlap:
            best_overlap = overlap

    if all_chunk_tokens:
        best_overlap = max(best_overlap, _overlap_score(answer_tokens, all_chunk_tokens))

    return round(best_overlap, 4)
