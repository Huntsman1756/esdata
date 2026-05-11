import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from document_decomposition import chunk_text


def test_chunk_text_preserves_all_content_order():
    text = "Primera frase. " * 200

    chunks = chunk_text(text, size=200)

    assert len(chunks) > 1
    assert chunks[0][0] == 0
    assert "".join(chunk for _, _, chunk in chunks).replace(" ", "") in text.replace(" ", "")


def test_chunk_text_skips_empty_text():
    assert chunk_text("   ") == []
