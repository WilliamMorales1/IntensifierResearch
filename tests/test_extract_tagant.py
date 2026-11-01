import sqlite3

import pandas as pd
import pytest

from extract_tagant import (
    closest_verb_infinitive,
    closest_verb_non_infinitive,
    count_syllables,
    get_adj,
    get_int,
    numero,
    process_segment,
    remove_other_turns,
    strip_speaker_labels,
    to_sqlite,
)


@pytest.fixture(autouse=True)
def _isolate_cwd(tmp_path, monkeypatch):
    # get_adj appends re- words to output/re-words.txt under the working directory.
    monkeypatch.chdir(tmp_path)


def token(segment):
    rows = process_segment(segment, "S01")
    assert len(rows) == 1, rows
    return rows[0]


@pytest.mark.parametrize(
    ("tagged", "lex"),
    [
        ("buen_ADJ_buen", "bueno"),
        ("gran_ADJ_gran", "grande"),
        ("bonitas_ADJ_bonita", "bonito"),
        ("altos_ADJ_altos", "alto"),
        ("lejos_ADJ_lejos", "lejos"),
    ],
)
def test_get_adj_normalizes_apocope_gender_and_number(tagged, lex):
    assert get_adj(tagged)[1] == lex


@pytest.mark.parametrize("spelling", ["super", "supel", "súper"])
def test_get_int_merges_super_spellings(spelling):
    assert get_int(f"{spelling}_ADV_{spelling}") == "súper"


def test_predicative_with_intensifier():
    row = token("es_AUX_ser muy_ADV_muy bueno_ADJ_bueno")
    assert (row["Int"], row["Lex_Adj"], row["Adj_type"], row["Double"]) == ("muy", "bueno", "predicative", "/")


def test_attributive_records_noun():
    row = token("casa_NOUN_casa bonita_ADJ_bonito")
    assert (row["Int"], row["Adj_type"], row["Noun"]) == ("/", "attributive", "casa")


def test_apocopated_adjective_before_noun():
    row = token("buen_ADJ_buen hombre_NOUN_hombre")
    assert (row["Adj"], row["Lex_Adj"], row["Noun"]) == ("buen", "bueno", "hombre")


def test_double_intensifier():
    row = token("muy_ADV_muy muy_ADV_muy bueno_ADJ_bueno")
    assert (row["Int"], row["Double"]) == ("muy", "muy")


@pytest.mark.parametrize(
    ("segment", "adj", "lex"),
    [
        ("está_AUX_estar riquísima_ADJ_riquísimo", "rica", "rico"),
        ("es_AUX_ser larguísimo_ADJ_larguísimo", "largo", "largo"),
        ("es_AUX_ser buenísimo_ADJ_buenísimo", "bueno", "bueno"),
    ],
)
def test_isimo_superlative_restores_base(segment, adj, lex):
    row = token(segment)
    assert (row["Int"], row["Adj"], row["Lex_Adj"]) == ("-ísimo", adj, lex)


def test_archi_prefix():
    row = token("archiconocido_ADJ_archiconocido")
    assert (row["Int"], row["Lex_Adj"]) == ("archi-", "conocido")


def test_negated_intensifier_skips_adjective_token():
    rows = process_segment("no_ADV_no muy_ADV_muy bueno_ADJ_bueno", "S01")
    assert all(row["Adj"] == "/" for row in rows)


def test_adverb_host():
    rows = process_segment("muy_ADV_muy lejos_ADV_lejos", "S01")
    assert [(r["Int"], r["Adv"]) for r in rows] == [("muy", "lejos")]


def test_intensifier_is_not_counted_as_adverb_host():
    rows = process_segment("bastante_ADV_bastante lejos_ADV_lejos", "S01")
    assert [(r["Int"], r["Adv"]) for r in rows] == [("bastante", "lejos")]


def test_negation_is_not_counted_as_adverb_host():
    assert process_segment("no_ADV_no muy_ADV_muy bueno_ADJ_bueno", "S01") == []


def test_noun_match_ignores_intensifier_substrings():
    # "re" is an intensifier and used to match inside "padre".
    row = token("padre_NOUN_padre rico_ADJ_rico")
    assert (row["Adj_type"], row["Noun"]) == ("attributive", "padre")


def test_noun_intensifier_adjective():
    row = token("tarde_NOUN_tarde re_ADV_re linda_ADJ_lindo")
    assert (row["Int"], row["Adj_type"], row["Noun"]) == ("re", "attributive", "tarde")


def test_copula_by_lemma():
    row = token("estuvieron_AUX_estar contentos_ADJ_contento")
    assert row["Adj_type"] == "predicative"


def test_copula_match_is_whole_word():
    row = token("desde_ADP_desde interesante_ADJ_interesante")
    assert row["Adj_type"] == "ambiguous"


@pytest.mark.parametrize(("word", "n"), [("queso", 2), ("guitarra", 3), ("pingüino", 3), ("muy", 1)])
def test_count_syllables(word, n):
    assert count_syllables(word) == n


def test_closest_verb():
    row = {"Phr_tagged": "ella_PRON_ella era_AUX_ser muy_ADV_muy alta_ADJ_alto", "Adj": "alta"}
    assert closest_verb_non_infinitive(row) == "era"
    assert closest_verb_infinitive(row) == "ser"


def test_numero_counts_each_speaker_separately():
    counts = {}
    rows = [{"Speaker": "S01"}, {"Speaker": "S01"}, {"Speaker": "S02"}]

    assert [numero(row, counts) for row in rows] == ["S01_01", "S01_02", "S02_01"]


def test_to_sqlite_round_trips(tmp_path):
    df = pd.DataFrame({
        "Corpus": ["Medellín", "Medellín", "Quijote"],
        "Speaker": ["S01", "S01", None],
        "Phr_tagged": ["es_AUX_ser muy_ADV_muy bueno_ADJ_bueno"] * 2 + ["casa_NOUN_casa bonita_ADJ_bonito"],
        "Phr": ["es muy bueno"] * 2 + ["casa bonita"],
        "Double": ["/", "/", None],
        "Int": ["muy", "muy", "/"],
        "Adj": ["bueno", "bueno", "bonito"],
        "Adj_type": ["predicative", "predicative", "attributive"],
        "Number": ["S01_01", "S01_02", "Quijote_01"],
        "Syllable": [2, 2, 3],
        "Age": [34.0, 34.0, None],
        "Gender": ["mujer", "mujer", None],
    })
    path = tmp_path / "out.sqlite"
    to_sqlite(df, path)
    with sqlite3.connect(path) as con:
        back = pd.read_sql("SELECT * FROM intensifier_data", con)
        counts = {t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in ("source", "phrase", "token")}
    pd.testing.assert_frame_equal(back, df, check_dtype=False)
    assert counts == {"source": 2, "phrase": 2, "token": 3}


@pytest.mark.parametrize(
    ("tagged", "lex"),
    [
        ("acogedora_ADJ_acogedora", "acogedor"),
        ("colaboradoras_ADJ_colaboradora", "colaborador"),
        ("conservadora_ADJ_conservador", "conservador"),
        ("sonora_ADJ_sonora", "sonoro"),
    ],
)
def test_get_adj_feminine_or_lemma(tagged, lex):
    assert get_adj(tagged)[1] == lex


@pytest.mark.parametrize(
    "segment",
    [
        "está_AUX_estar bien_ADV_bien hecho_ADJ_hecho",
        "es_AUX_ser mucho_ADV_mucho mejor_ADJ_mejor",
        "mucho_ADV_mucho mayores_ADJ_mayor",
        "mucho_PRON_mucho más_ADV_más",
        "mucho_PRON_mucho menos_ADV_menos",
    ],
)
def test_fixed_expressions_dropped(segment):
    assert process_segment(segment, "S01") == []


def test_fixed_expression_only_with_its_intensifier():
    row = token("está_AUX_estar muy_ADV_muy hecho_ADJ_hecho")
    assert (row["Int"], row["Lex_Adj"]) == ("muy", "hecho")


@pytest.mark.parametrize(
    "segment",
    [
        "casi_ADV_casi siempre_ADV_siempre",
        "casi_ADV_casi nunca_ADV_nunca",
        "mucho_PRON_mucho también_ADV_también",
        "hay_VERB_haber mucho_PRON_mucho donde_ADV_donde divertirse_VERB_divertir",
        "bastante_PRON_bastante donde_ADV_donde",
        "bien_ADV_bien ya_ADV_ya",
        "mucho_ADV_mucho antes_ADV_antes",
    ],
)
def test_non_gradable_adverb_hosts_dropped(segment):
    assert [r for r in process_segment(segment, "S01") if r["Int"] != "/"] == []


def test_non_gradable_adverb_kept_bare():
    assert [(r["Int"], r["Adv"]) for r in process_segment("siempre_ADV_siempre", "S01")] == [("/", "siempre")]


def test_mas_bien_is_not_intensified():
    rows = process_segment("es_AUX_ser más_ADV_más bien_ADV_bien pequeño_ADJ_pequeño", "S01")
    assert [(r["Int"], r["Double"], r["Adj"]) for r in rows if r["Adj"] != "/"] == [("/", "/", "pequeño")]


@pytest.mark.parametrize(
    ("segment", "hosts"),
    [
        ("muy_ADV_muy bue_ADJ_bue muy_ADV_muy bueno_ADJ_bueno", ["bueno"]),
        ("muy_ADV_muy d_ADJ_d muy_ADV_muy rápido_ADJ_rápido", ["rápido"]),
        ("muy_ADV_muy ca_ADJ_ca era_AUX_ser muy_ADV_muy calmado_ADJ_calmado", ["calmado"]),
        ("muy_ADV_muy cer_ADV_cer cerca_ADV_cerca", ["cerca"]),
        ("muy_ADV_muy poco_ADV_poco ,_PUNCT_, muy_ADV_muy pocos_DET_poco", ["poco"]),
        ("muy_ADV_muy mal_ADV_mal lo_PRON_él único_ADJ_único maluco_ADJ_maluco", ["mal", "único", "maluco"]),
        ("muy_ADV_muy rico_ADJ_rico ,_PUNCT_, muy_ADV_muy rico_ADJ_rico", ["rico", "rico"]),
    ],
)
def test_disfluency_fragments_dropped(segment, hosts):
    rows = process_segment(segment, "S01")
    assert [r["Adj"] if r["Adj"] != "/" else r["Adv"] for r in rows] == hosts


def test_isimo_quantifier_dropped():
    assert process_segment("muchísimas_ADJ_muchísimo cosas_NOUN_cosa", "S01") == []
    assert process_segment("me_PRON_yo gusta_VERB_gustar muchísimo_ADV_muchísimo", "S01") == []


@pytest.mark.parametrize(
    ("content", "clean"),
    [
        ("vida_NOUN_vida J_PROPN_J :_PUNCT_: -pues_ADV_-pues fue_AUX_ser", "vida_NOUN_vida pues_ADV_pues fue_AUX_ser"),
        ("LMP_PROPN_LMP :_PUNCT_: -_PUNCT_- si_INTJ_si", "si_INTJ_si"),
        ("E_NOUN_e :_PUNCT_: ¿_PUNCT_¿ cómo_PRON_cómo", "¿_PUNCT_¿ cómo_PRON_cómo"),
        ("hora_NOUN_hora :_PUNCT_: las_DET_el", "hora_NOUN_hora :_PUNCT_: las_DET_el"),
    ],
)
def test_strip_speaker_labels(content, clean):
    assert strip_speaker_labels(content).split() == clean.split()


def test_remove_other_turns_on_tagged_lines():
    lines = ["x_NOUN_x"] * 10 + [
        "E_CCONJ_e :_PUNCT_: ¿_PUNCT_¿ y_CCONJ_y cómo_PRON_cómo ?_PUNCT_?",
        "era_AUX_ser muy_ADV_mucho tranquilo_ADJ_tranquilo",
    ]
    assert remove_other_turns("\n".join(lines)).split("\n")[10:] == ["", "era_AUX_ser muy_ADV_mucho tranquilo_ADJ_tranquilo"]


def test_remove_other_turns_on_tagged_inline_question():
    line = "comento_VERB_comentar E_CCONJ_e :_PUNCT_: ¿_PUNCT_¿ cómo_PRON_cómo ?_PUNCT_? difícil_ADJ_difícil"
    assert remove_other_turns(line).split() == ["comento_VERB_comentar", "difícil_ADJ_difícil"]


def test_remove_other_turns_drops_tagged_third_voice():
    line = " ".join(["F_PROPN_F :_PUNCT_: -sí_INTJ_-sí"] * 20) + " F_PROPN_F :_PUNCT_: -(tercera_NOUN_-(tercera voz_NOUN_voz )_PUNCT_) sigue_VERB_seguir F_PROPN_F :_PUNCT_: -yo_PRON_-yo"
    assert "sigue_VERB_seguir" not in remove_other_turns(line)
    assert remove_other_turns(line).endswith("-yo_PRON_-yo")
