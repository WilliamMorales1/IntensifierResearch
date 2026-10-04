import pytest

from step_7_tagged_to_csv import (
    closest_verb_infinitive,
    closest_verb_non_infinitive,
    count_syllables,
    get_adj,
    get_int,
    process_segment,
)


@pytest.fixture(autouse=True)
def _isolate_cwd(tmp_path, monkeypatch):
    # get_adj appends re- words to re-words.txt in the working directory.
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
