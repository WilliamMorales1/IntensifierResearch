from types import SimpleNamespace

import pytest

from step_6_untag import untag, untag_line
from step_7_stanza_to_csv import correct_folder, correct_line, join_paragraphs, tag_doc, tag_word


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


@pytest.mark.parametrize(
    ("line", "fixed"),
    [
        ("muy_ADV_mucho poco_PRON_poco", "muy_ADV_mucho poco_ADV_poco"),
        ("hay_VERB_haber poco_PRON_poco", "hay_VERB_haber poco_PRON_poco"),
        ("es_AUX_ser muy_ADV_mucho solo_ADV_solo", "es_AUX_ser muy_ADV_mucho solo_ADJ_solo"),
        ("conozco_VERB_conocer mucho_PRON_mucho solo_ADV_solo", "conozco_VERB_conocer mucho_PRON_mucho solo_ADV_solo"),
        ("Santa_ADJ_santo Marta_PROPN_Marta", "Santa_PROPN_santo Marta_PROPN_Marta"),
        ("muy_ADV_mucho santo_ADJ_santo", "muy_ADV_mucho santo_ADJ_santo"),
        ("bueno_ADJ_bueno ,_PUNCT_, yo_PRON_yo", "bueno_INTJ_bueno ,_PUNCT_, yo_PRON_yo"),
        ("y_CCONJ_y claro_ADJ_claro que_SCONJ_que sí_INTJ_sí", "y_CCONJ_y claro_INTJ_claro que_SCONJ_que sí_INTJ_sí"),
        ("es_AUX_ser bueno_ADJ_bueno ._PUNCT_.", "es_AUX_ser bueno_ADJ_bueno ._PUNCT_."),
        ("muy_ADV_mucho claro_ADJ_claro ._PUNCT_.", "muy_ADV_mucho claro_ADJ_claro ._PUNCT_."),
        ("sentadas_ADJ_sentar", "sentadas_ADJ_sentado"),
        ("hecho_ADJ_hacer", "hecho_ADJ_hecho"),
        ("chéveres_ADJ_chéver", "chéveres_ADJ_chévere"),
        ("populares_ADJ_popular", "populares_ADJ_popular"),
        ("pero_CCONJ_pero bueno_ADJ_bueno eso_PRON_eso", "pero_CCONJ_pero bueno_INTJ_bueno eso_PRON_eso"),
        ("._PUNCT_. Bueno_ADJ_bueno ahora_ADV_ahora", "._PUNCT_. Bueno_INTJ_bueno ahora_ADV_ahora"),
        ("que_SCONJ_que bueno_ADJ_bueno", "que_SCONJ_que bueno_ADJ_bueno"),
        ("lo_PRON_él bueno_ADJ_bueno", "lo_PRON_él bueno_ADJ_bueno"),
        ("mejor_ADJ_mejor dicho_ADJ_dicho", "mejor_ADV_mejor dicho_VERB_decir"),
        ("a_ADP_a lo_PRON_él mejor_ADJ_mejor", "a_ADP_a lo_PRON_él mejor_ADV_mejor"),
        ("mejor_ADJ_mejor me_PRON_yo voy_VERB_ir", "mejor_ADV_mejor me_PRON_yo voy_VERB_ir"),
        ("vive_VERB_vivir mejor_ADJ_mejor ._PUNCT_.", "vive_VERB_vivir mejor_ADV_mejor ._PUNCT_."),
        ("se_PRON_él puso_VERB_poner peor_ADJ_peor", "se_PRON_él puso_VERB_poner peor_ADJ_peor"),
        ("el_DET_el mejor_ADJ_mejor amigo_NOUN_amigo", "el_DET_el mejor_ADJ_mejor amigo_NOUN_amigo"),
        ("es_AUX_ser mejor_ADJ_mejor preguntar_VERB_preguntar", "es_AUX_ser mejor_ADJ_mejor preguntar_VERB_preguntar"),
        ("pero_CCONJ_pero igual_ADJ_igual se_PRON_él fue_VERB_ir", "pero_CCONJ_pero igual_ADV_igual se_PRON_él fue_VERB_ir"),
        ("la_DET_el bebé_NOUN_bebé igual_ADJ_igual lo_PRON_él extraña_VERB_extrañar", "la_DET_el bebé_NOUN_bebé igual_ADV_igual lo_PRON_él extraña_VERB_extrañar"),
        ("es_AUX_ser igual_ADJ_igual ._PUNCT_.", "es_AUX_ser igual_ADJ_igual ._PUNCT_."),
        ("igual_ADJ_igual a_ADP_a su_DET_su mamá_NOUN_mamá", "igual_ADJ_igual a_ADP_a su_DET_su mamá_NOUN_mamá"),
        ("la_DET_el casa_NOUN_casa mía_ADJ_mío", "la_DET_el casa_NOUN_casa mía_DET_mío"),
        ("hay_VERB_haber mucho_PRON_mucho venezolano_ADJ_venezolano", "hay_VERB_haber mucho_PRON_mucho venezolano_NOUN_venezolano"),
        ("mucho_DET_mucho extranjero_ADJ_extranjero", "mucho_DET_mucho extranjero_NOUN_extranjero"),
        ("es_AUX_ser mucho_ADV_mucho vicioso_ADJ_vicioso", "es_AUX_ser mucho_ADV_mucho vicioso_ADJ_vicioso"),
        ("hay_VERB_haber mucho_PRON_mucho mejor_ADJ_mejor", "hay_VERB_haber mucho_PRON_mucho mejor_ADJ_mejor"),
    ],
)
def test_correct_line(line, fixed):
    assert correct_line(line) == fixed


def test_correct_line_is_idempotent():
    line = "muy_ADV_mucho poco_PRON_poco bueno_ADJ_bueno ._PUNCT_. dado_ADJ_dar mejor_ADJ_mejor dicho_ADJ_dicho pero_CCONJ_pero igual_ADJ_igual"
    assert correct_line(correct_line(line)) == correct_line(line)


def test_correct_folder_leaves_raw_tags(tmp_path):
    raw, out = tmp_path / "raw", tmp_path / "out"
    raw.mkdir()
    (raw / "S01.txt").write_text("muy_ADV_mucho poco_PRON_poco\n", encoding="utf-8")

    correct_folder(str(raw), str(out))

    assert (raw / "S01.txt").read_text(encoding="utf-8") == "muy_ADV_mucho poco_PRON_poco\n"
    assert (out / "S01.txt").read_text(encoding="utf-8") == "muy_ADV_mucho poco_ADV_poco\n"
