from types import SimpleNamespace

import pytest

from step_6_untag import untag, untag_line
from step_7_stanza_to_csv import join_paragraphs, tag_doc, tag_word


def test_untag_line_restores_raw_text():
    line = "¿_PUNCT_¿ cómo_PRON_cómo se_PRON_él llama_VERB_llamar ?_PUNCT_? ,_PUNCT_, es_AUX_ser muy_ADV_mucho pequeña_ADJ_pequeño ._PUNCT_."
    assert untag_line(line) == "¿cómo se llama?, es muy pequeña."


def test_untag_line_drops_space_tokens():
    assert untag_line("para_ADP_para _SPACE_ tener_VERB_tener") == "para tener"


def test_untag_keeps_transcript_underscores(tmp_path):
    src, out = tmp_path / "tagged", tmp_path / "text"
    src.mkdir()
    (src / "S01.txt").write_text("ruido_fondo_NOUN_ruido_fondo bueno_ADJ_bueno\n\n", encoding="utf-8")

    untag(str(src), str(out))

    assert (out / "S01.txt").read_text(encoding="utf-8") == "ruido_fondo bueno\n"


def word(text, upos, lemma):
    return SimpleNamespace(text=text, upos=upos, lemma=lemma)


@pytest.mark.parametrize(
    ("w", "tagged"),
    [
        (word("bueno", "ADJ", "bueno"), "bueno_ADJ_bueno"),
        (word("ruido_fondo", "NOUN", "ruido_fondo"), "ruido-fondo_NOUN_ruido-fondo"),
        (word("1 000", "NUM", None), "1000_NUM_"),
    ],
)
def test_tag_word_keeps_step_7_format(w, tagged):
    assert tag_word(w) == tagged


def token(start, *words):
    return SimpleNamespace(start_char=start, words=list(words))


def test_tag_doc_one_line_per_sentence():
    doc = SimpleNamespace(sentences=[
        SimpleNamespace(tokens=[
            token(0, word("es", "AUX", "ser")),
            token(3, word("muy", "ADV", "mucho")),
            token(7, word("bueno", "ADJ", "bueno")),
        ]),
        SimpleNamespace(tokens=[token(12, word(".", "PUNCT", "."))]),
    ])
    assert tag_doc(doc) == "es_AUX_ser muy_ADV_mucho bueno_ADJ_bueno\n._PUNCT_."


def test_tag_doc_drops_added_periods():
    doc = SimpleNamespace(sentences=[
        SimpleNamespace(tokens=[token(0, word("casero", "ADJ", "casero")), token(7, word(".", "PUNCT", "."))]),
    ])
    assert tag_doc(doc, {7}) == "casero_ADJ_casero"


def test_join_paragraphs_ends_turns_with_period():
    text, added = join_paragraphs(["soy muy casero", "sí.", "bueno"])
    assert text == "soy muy casero .\n\nsí.\n\nbueno ."
    assert {text[i] for i in added} == {"."}
    assert added == {15, 29}
