import sqlite3

import pandas as pd
import pytest

from extract import (
    analyze,
    count_syllables,
    drop_invariant_hosts,
    fix_isimo_hosts,
    get_adj,
    get_int,
    isimo_base,
    numero,
    process_segment,
    to_sqlite,
    write_outputs,
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
        ("gritona_ADJ_gritón", "gritón"),
        ("sonoro_ADJ_sonoro", "sonoro"),
        ("grises_ADJ_gris", "gris"),
        ("gratis_ADJ_gratis", "gratis"),
        ("francesa_ADJ_francés", "francés"),
        ("soltera_ADJ_soltera", "soltero"),
        ("pequeñitas_ADJ_pequeñitas", "pequeñito"),
        ("egoístas_ADJ_egoísta", "egoísta"),
        ("adventista_ADJ_adventista", "adventista"),
        ("paisas_ADJ_paisa", "paisa"),
        ("demócrata_ADJ_demócrata", "demócrata"),
    ],
)
def test_get_adj_normalizes_apocope_gender_and_number(tagged, lex):
    assert get_adj(tagged)[1] == lex


@pytest.mark.parametrize("spelling", ["super", "supel", "súper"])
def test_get_int_merges_super_spellings(spelling):
    assert get_int(f"{spelling}_ADV_{spelling}") == "súper"


def test_intensified_adjective_without_parse():
    row = token("es_AUX_ser muy_ADV_muy bueno_ADJ_bueno")
    assert (row["Int"], row["Lex_Adj"], row["Double"]) == ("muy", "bueno", "/")
    # Adj_type, Noun and Verb only come from the parse
    assert (row["Adj_type"], row["Noun"], row["Verb"], row["Inf_Verb"]) == ("ambiguous", "/", "/", "/")


def test_apocopated_adjective():
    row = token("buen_ADJ_buen hombre_NOUN_hombre")
    assert (row["Adj"], row["Lex_Adj"]) == ("buen", "bueno")


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


@pytest.mark.parametrize(("word", "n"), [("queso", 2), ("guitarra", 3), ("pingüino", 3), ("muy", 1)])
def test_count_syllables(word, n):
    assert count_syllables(word) == n


def test_numero_counts_each_speaker_separately():
    counts = {}
    rows = [{"Speaker": "S01"}, {"Speaker": "S01"}, {"Speaker": "S02"}]

    assert [numero(row, counts) for row in rows] == ["S01_01", "S01_02", "S02_01"]


def test_to_sqlite_round_trips(tmp_path):
    df = pd.DataFrame(
        {
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
        }
    )
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
        ("luchadora_ADJ_luchadora", "luchador"),
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
        "mucho_PRON_mucho anoche_ADV_anoche",
        "bastante_PRON_bastante acerca_ADV_acerca de_ADP_de",
        "bien_ADV_bien primero_ADV_primero",
        "pasó_VERB_pasar muy_ADV_mucho digamos_ADV_decir",
        "va_VERB_ir bien_ADV_bien hasta_ADV_hasta con_ADP_con",
        "hablaba_VERB_hablar mucho_ADV_mucho tanto_ADV_tanto de_ADP_de",
        "casi_ADV_casi toos_ADV_too los_DET_el días_NOUN_día",
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
        ("es_AUX_ser muy_ADV_muy comple_ADJ_comple es_AUX_ser muy_ADV_muy complejo_ADJ_complejo", ["complejo"]),
        ("muy_ADV_muy cerca_ADV_cerca en_ADP_en cercanías_NOUN_cercanía", ["cerca"]),
        ("muy_ADV_muy poco_ADV_poco ,_PUNCT_, muy_ADV_muy pocos_DET_poco", ["poco"]),
        ("muy_ADV_muy mal_ADV_mal lo_PRON_él único_ADJ_único maluco_ADJ_maluco", ["mal", "único", "maluco"]),
        ("muy_ADV_muy rico_ADJ_rico ,_PUNCT_, muy_ADV_muy rico_ADJ_rico", ["rico", "rico"]),
    ],
)
def test_disfluency_fragments_dropped(segment, hosts):
    rows = process_segment(segment, "S01")
    assert [r["Adj"] if r["Adj"] != "/" else r["Adv"] for r in rows] == hosts


def test_isimo_quantifier_dropped():
    assert process_segment("me_PRON_yo gusta_VERB_gustar muchísimo_ADV_muchísimo", "S01") == []


@pytest.mark.parametrize(
    ("segment", "adv"),
    [
        ("vive_VERB_vivir lejísimos_ADV_lejísimos", "lejos"),
        ("está_AUX_estar cerquísima_ADV_cerquísima", "cerca"),
        ("llegó_VERB_llegar tardísimo_ADV_tardísimo", "tarde"),
        ("habla_VERB_hablar altísimo_ADV_altísimo", "alto"),
        ("salió_VERB_salir tempranísimo_ADV_tempranísimo", "temprano"),
    ],
)
def test_isimo_adverb_restores_base(segment, adv):
    (row,) = process_segment(segment, "S01")
    assert (row["Int"], row["Adv"]) == ("-ísimo", adv)


@pytest.mark.parametrize(
    ("stem", "base"),
    [
        ("grand", "grande"),
        ("facil", "fácil"),
        ("rapid", "rápido"),
        ("chever", "chévere"),
        ("amabil", "amable"),
        ("antic", "antiguo"),
        ("buen", "bueno"),
        ("lej", "lejos"),
        # not in the lexicon: rules
        ("important", "importante"),
        ("grav", "grave"),
        ("hermos", "hermoso"),
    ],
)
def test_isimo_base(stem, base):
    lexicon = {"grande": "grande", "facil": "fácil", "rapido": "rápido", "chevere": "chévere"}
    lexicon |= {"amable": "amable", "antiguo": "antiguo", "bueno": "bueno"}
    assert isimo_base(stem, lexicon) == base


def test_fix_isimo_hosts_uses_corpus_forms():
    def row(int_, adj, lex, adv="/"):
        return {"Int": int_, "Adj": adj, "Lex_Adj": lex, "Adv": adv}

    df = pd.DataFrame(
        [
            row("/", "grandes", "grande"),
            row("/", "fáciles", "fácil"),
            row("/", "/", "/", "rápido"),
            row("-ísimo", "grandas", "grando"),
            row("-ísimo", "granda", "grando"),
            row("-ísimo", "facilos", "facilo"),
            row("-ísimo", "buena", "bueno"),
            row("-ísimo", "lejos", "lejo"),
            row("-ísimo", "/", "/", "rapido"),
        ]
    )
    out = fix_isimo_hosts(df).iloc[3:]
    assert list(out["Adj"]) == ["grandes", "grande", "fáciles", "buena", "lejos", "/"]
    assert list(out["Lex_Adj"]) == ["grande", "grande", "fácil", "bueno", "lejos", "/"]
    assert out["Adv"].iloc[-1] == "rápido"


def test_analyze_and_write_outputs_end_to_end(tmp_path):
    corrected = tmp_path / "corrected"
    corrected.mkdir()
    (corrected / "S01.txt").write_text(
        "la_DET_el casa_NOUN_casa es_AUX_ser muy_ADV_mucho bonita_ADJ_bonito ._PUNCT_.\n", encoding="utf-8"
    )
    (corrected / "notes.md").write_text("ignored", encoding="utf-8")
    speakers = tmp_path / "speakers.xlsx"
    pd.DataFrame({"Speaker": ["S01"], "Gender": ["mujer"]}).to_excel(speakers, index=False)
    output = str(tmp_path / "out")

    df = write_outputs(analyze(str(corrected)), output, str(speakers), xlsx=True, csv=True)

    with sqlite3.connect(tmp_path / "out.sqlite") as con:
        back = pd.read_sql("SELECT * FROM intensifier_data", con)
    pd.testing.assert_frame_equal(back, df, check_dtype=False)
    assert (tmp_path / "out.xlsx").exists()
    pd.testing.assert_frame_equal(pd.read_csv(tmp_path / "out.csv", dtype=str), df.astype(str), check_dtype=False)
    assert len(df) == 1
    assert df.iloc[0][["Int", "Adj", "Lex_Adj", "Gender", "Number"]].tolist() == [
        "muy",
        "bonita",
        "bonito",
        "mujer",
        "S01_01",
    ]


def test_analyze_with_no_files(tmp_path):
    assert analyze(str(tmp_path), str(tmp_path / "out.csv")).empty


def test_drop_invariant_hosts_keeps_only_varying_hosts():
    df = pd.DataFrame(
        {
            "Int": ["muy", "/", "/", "/", "muy", "/"],
            "Adv": ["/", "/", "/", "ya", "Bien", "bien"],
            "Lex_Adj": ["bonito", "bonito", "feo", "/", "/", "/"],
        }
    )
    assert drop_invariant_hosts(df)[["Lex_Adj", "Adv"]].values.tolist() == [
        ["bonito", "/"],
        ["bonito", "/"],
        ["/", "Bien"],
        ["/", "bien"],
    ]


def test_analyze_drops_hosts_never_intensified(tmp_path):
    (tmp_path / "S01.txt").write_text(
        "es_AUX_ser muy_ADV_muy lindo_ADJ_lindo ._PUNCT_. fue_AUX_ser lindo_ADJ_lindo ._PUNCT_. "
        "es_AUX_ser alto_ADJ_alto ._PUNCT_.\n",
        encoding="utf-8",
    )
    assert len(analyze(str(tmp_path), str(tmp_path / "all.csv"))) == 3
    df = analyze(str(tmp_path), str(tmp_path / "out.csv"), drop_invariant=True)
    assert df[["Int", "Lex_Adj"]].values.tolist() == [["muy", "lindo"], ["/", "lindo"]]
    assert len(pd.read_csv(tmp_path / "out.csv")) == 2


@pytest.mark.parametrize(
    ("segment", "host"),
    [
        ("entoes_ADJ_entoes fuimos_VERB_ir", "entoes"),
        ("ahorita_PRON_ahorita no_ADV_no", "ahorita"),
        ("queda_VERB_quedar súper_ADV_súper cerquita_ADJ_cerquita", "cerquita"),
        ("hago_VERB_hacer muy_ADV_mucho poquito_ADJ_poquito", "poquito"),
        ("estábamos_AUX_estar lejísimos_ADJ_lejísimo", "lejos"),
        ("es_AUX_ser muy_ADV_mucho celca_ADV_cerca", "cerca"),
    ],
)
def test_retag_always_adverbs(segment, host):
    (row,) = process_segment(segment, "S01")
    assert (row["Adv"], row["Adj"]) == (host, "/")


@pytest.mark.parametrize(
    "segment",
    [
        "un_DET_uno poquito_ADJ_poquito duro_NOUN_duro",
        "muy_ADV_mucho poquitas_ADJ_poquito veces_NOUN_vez",
        "muy_ADV_mucho poquito_ADJ_poquito tiempo_NOUN_tiempo",
        "son_AUX_ser muy_ADV_mucho poquitos_ADJ_poquito ,_PUNCT_,",
    ],
)
def test_retag_quantifiers_are_not_hosts(segment):
    assert process_segment(segment, "S01") == []


@pytest.mark.parametrize("host", ["bue", "bie", "tod", "nun"])
def test_cut_off_without_restart_is_fragment(host):
    assert process_segment(f"sería_AUX_ser muy_ADV_mucho {host}_ADV_{host} podría_AUX_poder", "S01") == []
