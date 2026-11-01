from types import SimpleNamespace

import pytest

from extract_stanza import (
    chunk_sentence,
    correct_folder,
    correct_line,
    join_paragraphs,
    parse_relations,
    read_conllu,
    sentence_relations,
    tag_doc,
    tag_word,
)
from extract_tagant import analyze
from untag import untag, untag_line


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
def test_tag_word_keeps_tagged_format(w, tagged):
    assert tag_word(w) == tagged


def token(start, *words):
    return SimpleNamespace(start_char=start, words=list(words))


def test_tag_doc_one_line_per_sentence():
    doc = SimpleNamespace(
        sentences=[
            SimpleNamespace(
                tokens=[
                    token(0, word("es", "AUX", "ser")),
                    token(3, word("muy", "ADV", "mucho")),
                    token(7, word("bueno", "ADJ", "bueno")),
                ]
            ),
            SimpleNamespace(tokens=[token(12, word(".", "PUNCT", "."))]),
        ]
    )
    assert tag_doc(doc) == "es_AUX_ser muy_ADV_mucho bueno_ADJ_bueno\n._PUNCT_."


def test_tag_doc_drops_added_periods():
    doc = SimpleNamespace(
        sentences=[
            SimpleNamespace(tokens=[token(0, word("casero", "ADJ", "casero")), token(7, word(".", "PUNCT", "."))]),
        ]
    )
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
        (
            "pero_CCONJ_pero igual_ADJ_igual se_PRON_él fue_VERB_ir",
            "pero_CCONJ_pero igual_ADV_igual se_PRON_él fue_VERB_ir",
        ),
        (
            "la_DET_el bebé_NOUN_bebé igual_ADJ_igual lo_PRON_él extraña_VERB_extrañar",
            "la_DET_el bebé_NOUN_bebé igual_ADV_igual lo_PRON_él extraña_VERB_extrañar",
        ),
        ("es_AUX_ser igual_ADJ_igual ._PUNCT_.", "es_AUX_ser igual_ADJ_igual ._PUNCT_."),
        ("igual_ADJ_igual a_ADP_a su_DET_su mamá_NOUN_mamá", "igual_ADJ_igual a_ADP_a su_DET_su mamá_NOUN_mamá"),
        ("la_DET_el casa_NOUN_casa mía_ADJ_mío", "la_DET_el casa_NOUN_casa mía_DET_mío"),
        (
            "hay_VERB_haber mucho_PRON_mucho venezolano_ADJ_venezolano",
            "hay_VERB_haber mucho_PRON_mucho venezolano_NOUN_venezolano",
        ),
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


def test_chunk_sentence_cuts_at_punctuation():
    tokens = [("a", "NOUN", "a")] * 3 + [(",", "PUNCT", ",")] + [("b", "NOUN", "b")] * 3 + [(",", "PUNCT", ",")]
    assert [len(c) for c in chunk_sentence(tokens, size=5)] == [4, 4]
    assert [len(c) for c in chunk_sentence(tokens, size=8)] == [8]


def test_chunk_sentence_cuts_long_clause_hard():
    tokens = [("a", "NOUN", "a")] * 12
    assert [len(c) for c in chunk_sentence(tokens, size=5)] == [5, 5, 2]


def conllu(*rows):
    return (
        "\n".join(
            "\t".join([str(i), t, l, u, "_", "_", str(h), d, "_", "_"]) for i, (t, u, l, h, d) in enumerate(rows, 1)
        )
        + "\n\n"
    )


# la casa es muy bonita y grande , lo veo muy feo
parsed = (
    conllu(
        ("la", "DET", "el", 2, "det"),
        ("casa", "NOUN", "casa", 5, "nsubj"),
        ("es", "AUX", "ser", 5, "cop"),
        ("muy", "ADV", "mucho", 5, "advmod"),
        ("bonita", "ADJ", "bonito", 0, "root"),
        ("y", "CCONJ", "y", 7, "cc"),
        ("grande", "ADJ", "grande", 5, "conj"),
        (",", "PUNCT", ",", 5, "punct"),
    )
    + conllu(
        ("lo", "PRON", "él", 2, "obj"),
        ("veo", "VERB", "ver", 0, "root"),
        ("muy", "ADV", "mucho", 4, "advmod"),
        ("feo", "ADJ", "feo", 2, "xcomp"),
    )
    + conllu(
        ("vivo", "VERB", "vivir", 0, "root"),
        ("en", "ADP", "en", 3, "case"),
        ("casas", "NOUN", "casa", 1, "obl"),
        ("muy", "ADV", "mucho", 5, "advmod"),
        ("viejas", "ADJ", "viejo", 3, "amod"),
        ("bien", "ADV", "bien", 7, "advmod"),
        ("lejos", "ADV", "lejos", 1, "advmod"),
    )
)


def test_sentence_relations(tmp_path):
    (tmp_path / "S01.conllu").write_text(parsed, encoding="utf-8")
    first, second, third = (sentence_relations(s) for s in read_conllu(tmp_path / "S01.conllu"))
    assert first[4] == ("predicative", "casa", "es", "ser")
    assert first[6] == ("predicative", "casa", "es", "ser")
    assert first[3] == ("/", "/", "es", "ser")
    assert first[1] is None
    # object is a pronoun, so no noun
    assert second[3] == ("predicative", "/", "veo", "ver")
    assert third[4] == ("attributive", "casas", "vivo", "vivir")
    assert third[6] == ("/", "/", "vivo", "vivir")


def test_predicative_subject_is_nearest(tmp_path):
    # yo fui peleonera , medallas: the parser also hangs a later noun on the adjective
    (tmp_path / "S01.conllu").write_text(
        conllu(
            ("yo", "PRON", "yo", 3, "nsubj"),
            ("fui", "AUX", "ser", 3, "cop"),
            ("peleonera", "ADJ", "peleonero", 0, "root"),
            (",", "PUNCT", ",", 5, "punct"),
            ("medallas", "NOUN", "medalla", 3, "nsubj"),
        ),
        encoding="utf-8",
    )
    (sent,) = read_conllu(tmp_path / "S01.conllu")
    assert sentence_relations(sent)[2] == ("predicative", "/", "fui", "ser")


def test_analyze_reads_relations_from_parse(tmp_path):
    tagged, out = tmp_path / "tagged", tmp_path / "parsed"
    tagged.mkdir()
    out.mkdir()
    (out / "S01.conllu").write_text(parsed, encoding="utf-8")
    words = [(t, u, l) for s in read_conllu(out / "S01.conllu") for _, t, u, l, _, _ in s]
    # attributive casas viejas is not adjacent in word order to the verb "vivo"
    (tagged / "S01.txt").write_text(" ".join("_".join(w) for w in words) + "\n", encoding="utf-8")

    df = analyze(str(tagged), str(tmp_path / "out.csv"), parse_relations(str(out)), drop_invariant=False)

    rows = df.set_index(df.Adj.where(df.Adj != "/", df.Adv))
    assert rows.loc["bonita", ["Int", "Adj_type", "Noun", "Verb", "Inf_Verb"]].tolist() == [
        "muy",
        "predicative",
        "casa",
        "es",
        "ser",
    ]
    assert rows.loc["grande", ["Int", "Adj_type", "Noun", "Verb"]].tolist() == ["/", "predicative", "casa", "es"]
    assert rows.loc["feo", ["Adj_type", "Verb"]].tolist() == ["predicative", "veo"]
    assert rows.loc["viejas", ["Int", "Adj_type", "Noun", "Verb"]].tolist() == ["muy", "attributive", "casas", "vivo"]
    assert rows.loc["lejos", ["Int", "Verb", "Inf_Verb"]].tolist() == ["bien", "vivo", "vivir"]


def test_analyze_maps_parse_across_split_inside_token(tmp_path):
    tagged, out = tmp_path / "tagged", tmp_path / "parsed"
    tagged.mkdir()
    out.mkdir()
    (out / "S01.conllu").write_text(
        conllu(
            ("...", "PUNCT", "...", 3, "punct"),
            ("muy", "ADV", "mucho", 3, "advmod"),
            ("bonito", "ADJ", "bonito", 0, "root"),
            ("es", "AUX", "ser", 3, "cop"),
        ),
        encoding="utf-8",
    )
    (tagged / "S01.txt").write_text("..._PUNCT_... muy_ADV_mucho bonito_ADJ_bonito es_AUX_ser\n", encoding="utf-8")

    df = analyze(str(tagged), str(tmp_path / "out.csv"), parse_relations(str(out)))

    assert df[["Adj", "Adj_type", "Verb"]].values.tolist() == [["bonito", "predicative", "es"]]


def test_analyze_rejects_misaligned_parse(tmp_path):
    tagged, out = tmp_path / "tagged", tmp_path / "parsed"
    tagged.mkdir()
    out.mkdir()
    (out / "S01.conllu").write_text(conllu(("bonito", "ADJ", "bonito", 0, "root")), encoding="utf-8")
    (tagged / "S01.txt").write_text("muy_ADV_mucho bonito_ADJ_bonito\n", encoding="utf-8")

    with pytest.raises(ValueError):
        analyze(str(tagged), str(tmp_path / "out.csv"), parse_relations(str(out)))


def test_noun_outside_phrase_is_dropped(tmp_path):
    # "gracias , muy agradable ,": the head noun sits in the previous segment
    tagged, out = tmp_path / "tagged", tmp_path / "parsed"
    tagged.mkdir()
    out.mkdir()
    (out / "S01.conllu").write_text(
        conllu(
            ("gracias", "NOUN", "gracia", 0, "root"),
            (",", "PUNCT", ",", 1, "punct"),
            ("muy", "ADV", "mucho", 4, "advmod"),
            ("agradable", "ADJ", "agradable", 1, "amod"),
            (",", "PUNCT", ",", 4, "punct"),
            ("la", "DET", "el", 2, "det"),
            ("gente", "NOUN", "gente", 9, "nsubj"),
            ("es", "AUX", "ser", 9, "cop"),
            ("amable", "ADJ", "amable", 0, "root"),
        ),
        encoding="utf-8",
    )
    words = [(t, u, l) for s in read_conllu(out / "S01.conllu") for _, t, u, l, _, _ in s]
    (tagged / "S01.txt").write_text(" ".join("_".join(w) for w in words) + "\n", encoding="utf-8")

    df = analyze(str(tagged), str(tmp_path / "out.csv"), parse_relations(str(out)), drop_invariant=False)

    assert df[["Adj", "Adj_type", "Noun"]].values.tolist() == [
        ["agradable", "ambiguous", "/"],
        ["amable", "predicative", "gente"],
    ]


def test_verb_outside_phrase_is_dropped(tmp_path):
    # "lo conocí , muy buen amigo ,": the verb sits in the previous segment
    tagged, out = tmp_path / "tagged", tmp_path / "parsed"
    tagged.mkdir()
    out.mkdir()
    (out / "S01.conllu").write_text(
        conllu(
            ("lo", "PRON", "él", 2, "obj"),
            ("conocí", "VERB", "conocer", 0, "root"),
            (",", "PUNCT", ",", 2, "punct"),
            ("muy", "ADV", "mucho", 5, "advmod"),
            ("buen", "ADJ", "bueno", 6, "amod"),
            ("amigo", "NOUN", "amigo", 2, "obj"),
            (",", "PUNCT", ",", 6, "punct"),
        ),
        encoding="utf-8",
    )
    words = [(t, u, l) for s in read_conllu(out / "S01.conllu") for _, t, u, l, _, _ in s]
    (tagged / "S01.txt").write_text(" ".join("_".join(w) for w in words) + "\n", encoding="utf-8")

    df = analyze(str(tagged), str(tmp_path / "out.csv"), parse_relations(str(out)))

    assert df[["Adj", "Adj_type", "Noun", "Verb", "Inf_Verb"]].values.tolist() == [
        ["buen", "attributive", "amigo", "/", "/"]
    ]
