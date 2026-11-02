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


@pytest.mark.parametrize(
    ("tagged", "expected"),
    [
        ("archiconocido_ADJ_archiconocido", ("archi-", "conocido", "conocido")),
        ("superbonito_ADJ_superbonito", ("súper", "bonito", "bonito")),
        ("súperdeliciosos_ADJ_súperdelicioso", ("súper", "deliciosos", "delicioso")),
        ("supelbonita_ADJ_supelbonito", ("súper", "bonita", "bonito")),
        ("requetebueno_ADJ_requetebueno", ("requete-", "bueno", "bueno")),
        ("recontrabuena_ADJ_recontrabueno", ("recontra-", "buena", "bueno")),
        ("retemprano_ADJ_retemprano", ("re", "temprano", "temprano")),
        ("paupérrimas_ADJ_paupérrimo", ("-érrimo", "pobres", "pobre")),
        ("celebérrimo_ADJ_celebérrimo", ("-érrimo", "célebre", "célebre")),
        ("libérrima_ADJ_libérrimo", ("-érrimo", "libre", "libre")),
        ("integérrimo_ADJ_integérrimo", ("-érrimo", "íntegro", "íntegro")),
    ],
)
def test_bound_intensifier_strips_to_base(tagged, expected):
    row = token("es_AUX_ser " + tagged)
    assert (row["Int"], row["Adj"], row["Lex_Adj"]) == expected
    assert row["Int_type"] == "booster"


@pytest.mark.parametrize(
    "tagged",
    [
        "archivado_ADJ_archivado",
        "superior_ADJ_superior",
        "superiol_ADJ_superior",
        "superficial_ADJ_superficial",
        "supersticiosa_ADJ_supersticioso",
        "superable_ADJ_superable",
        "reunido_ADJ_reunido",
        "relleno_ADJ_relleno",
        "retirado_ADJ_retirado",
        "retebueno_ADJ_retebueno",
        "hiperactivo_ADJ_hiperactivo",
        "ultraconservadora_ADJ_ultraconservador",
        "extraordinario_ADJ_extraordinario",
        "sobrenatural_ADJ_sobrenatural",
    ],
)
def test_lexical_prefix_lookalikes_stay_bare(tagged):
    row = token("es_AUX_ser " + tagged)
    assert row["Int"] == "/"
    assert row["Lex_Adj"] == tagged.split("_")[2]


def test_super_prefix_on_adverb():
    (row,) = process_segment("está_AUX_estar súperbien_ADV_súperbien", "S01")
    assert (row["Int"], row["Adv"]) == ("súper", "bien")


@pytest.mark.parametrize("word", ["requete", "recontra"])
def test_free_requete_recontra_intensify(word):
    row = token(f"es_AUX_ser {word}_ADV_{word} bonito_ADJ_bonito")
    assert (row["Int"], row["Int_type"], row["Lex_Adj"]) == (word, "booster", "bonito")


def test_isimo_bil_base_without_lexicon():
    assert isimo_base("amabil", {}) == "amable"


@pytest.mark.parametrize(
    ("segment", "row"),
    [
        ("no_ADV_no muy_ADV_muy bueno_ADJ_bueno", ("muy", "bueno", "no")),
        ("no_ADV_no tan_ADV_tan bueno_ADJ_bueno", ("tan", "bueno", "no")),
        ("no_ADV_no es_AUX_ser tan_ADV_tan bueno_ADJ_bueno", ("tan", "bueno", "no")),
        ("nunca_ADV_nunca fue_AUX_ser muy_ADV_mucho bueno_ADJ_bueno", ("muy", "bueno", "nunca")),
        ("ni_CCONJ_ni tan_ADV_tan pobres_ADJ_pobre", ("tan", "pobre", "ni")),
        ("es_AUX_ser muy_ADV_mucho bueno_ADJ_bueno", ("muy", "bueno", "/")),
        ("no_ADV_no es_AUX_ser bueno_ADJ_bueno", ("/", "bueno", "no")),
    ],
)
def test_negation_marked_not_dropped(segment, row):
    rows = [r for r in process_segment(segment, "S01") if r["Adj"] != "/"]
    assert [(r["Int"], r["Lex_Adj"], r["Negation"]) for r in rows] == [row]


def test_adverb_host():
    rows = process_segment("muy_ADV_muy lejos_ADV_lejos", "S01")
    assert [(r["Int"], r["Adv"]) for r in rows] == [("muy", "lejos")]


def test_intensifier_is_not_counted_as_adverb_host():
    rows = process_segment("bastante_ADV_bastante lejos_ADV_lejos", "S01")
    assert [(r["Int"], r["Adv"]) for r in rows] == [("bastante", "lejos")]


def test_negation_is_not_counted_as_adverb_host():
    assert [r["Adv"] for r in process_segment("no_ADV_no muy_ADV_muy bueno_ADJ_bueno", "S01")] == ["/"]


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


def hosts(segment):
    return [
        (r["Int"], r["Int_type"], r["Lex_Adj"] if r["Adj"] != "/" else r["Adv"])
        for r in process_segment(segment, "S01")
    ]


@pytest.mark.parametrize(
    ("segment", "row"),
    [
        ("es_AUX_ser muy_ADV_mucho bonito_ADJ_bonito", ("muy", "booster", "bonito")),
        ("es_AUX_ser totalmente_ADV_totalmente distinto_ADJ_distinto", ("totalmente", "maximizer", "distinto")),
        ("es_AUX_ser casi_ADV_casi imposible_ADJ_imposible", ("casi", "approximator", "imposible")),
        ("es_AUX_ser especialmente_ADV_especialmente bonito_ADJ_bonito", ("especialmente", "emphasizer", "bonito")),
        ("es_AUX_ser bonitísimo_ADJ_bonitísimo", ("-ísimo", "booster", "bonito")),
        ("es_AUX_ser bonito_ADJ_bonito", ("/", "/", "bonito")),
    ],
)
def test_int_type_follows_quirk_scale(segment, row):
    assert hosts(segment) == [row]


@pytest.mark.parametrize(
    "segment",
    [
        "es_AUX_ser tan_ADV_tan bonita_ADJ_bonito",
        "una_DET_uno casa_NOUN_casa tan_ADV_tan bonita_ADJ_bonito",
        "qué_DET_qué muchacho_NOUN_muchacho tan_ADV_tan simpático_ADJ_simpático",
        "¡_PUNCT_¡ ay_INTJ_ay qué_PRON_qué tan_ADV_tan lindo_ADJ_lindo",
        "el_DET_el dolor_NOUN_dolor tan_ADV_tan grande_ADJ_grande que_PRON_que uno_PRON_uno tiene_VERB_tener",
        "¡_PUNCT_¡ qué_DET_qué profesor_NOUN_profesor tan_ADV_tan malo_ADJ_malo !_PUNCT_! ,_PUNCT_, que_SCONJ_que sí_ADV_sí",
    ],
)
def test_tan_intensifier(segment):
    assert [h for h in hosts(segment) if h[0] != "/"] == [
        ("tan", "booster", h[2]) for h in hosts(segment) if h[0] != "/"
    ]
    assert len([h for h in hosts(segment) if h[0] == "tan"]) == 1


@pytest.mark.parametrize(
    "segment",
    [
        # equality, result (Bulgin et al. 2008), interrogative, fixed
        "no_ADV_no es_AUX_ser tan_ADV_tan grande_ADJ_grande como_ADP_como este_PRON_este",
        "es_AUX_ser tan_ADV_tan bueno_ADJ_bueno ,_PUNCT_, como_SCONJ_como lo_PRON_él era_AUX_ser",
        "son_AUX_ser tan_ADV_tan atrevidos_ADJ_atrevido que_SCONJ_que me_PRON_yo fui_VERB_ir",
        "es_AUX_ser tan_ADV_tan descarado_ADJ_descarado ,_PUNCT_, que_SCONJ_que hasta_ADV_hasta",
        "no_ADV_no sé_VERB_saber qué_PRON_qué tan_ADV_tan buenos_ADJ_bueno",
        "me_PRON_yo voy_VERB_ir tan_ADV_tan pronto_ADV_pronto",
    ],
)
def test_tan_outside_envelope_dropped(segment):
    assert [h for h in hosts(segment) if h[2] in ("grande", "bueno", "atrevido", "descarado", "pronto")] == []


@pytest.mark.parametrize(
    "segment",
    [
        "es_AUX_ser más_ADV_más grande_ADJ_grande que_SCONJ_que yo_PRON_yo",
        "es_AUX_ser más_ADV_más grande_ADJ_grande",
        "es_AUX_ser mucho_ADV_mucho más_ADV_más grande_ADJ_grande",
        "lo_PRON_él más_ADV_más grande_ADJ_grande",
        "la_DET_el casa_NOUN_casa más_ADV_más grande_ADJ_grande",
        "es_AUX_ser menos_ADV_menos grande_ADJ_grande",
        "es_AUX_ser mejor_ADJ_mejor",
        "vive_VERB_vivir mejor_ADV_mejor",
        "mi_DET_mi hermano_NOUN_hermano mayor_ADJ_mayor",
        "quiero_VERB_querer más_ADV_más",
    ],
)
def test_comparatives_and_superlatives_dropped(segment):
    assert [h for h in hosts(segment) if h[2] in ("grande", "mejor", "mayor", "más")] == []


def test_muy_mayor_kept():
    assert hosts("es_AUX_ser muy_ADV_mucho mayor_ADJ_mayor") == [("muy", "booster", "mayor")]


def test_exclamative_mas_is_booster():
    assert hosts("¡_PUNCT_¡ qué_DET_qué casa_NOUN_casa más_ADV_más bonita_ADJ_bonito") == [("más", "booster", "bonito")]


def test_mas_o_menos_is_compromiser():
    assert hosts("es_AUX_ser más_ADV_más o_CCONJ_o menos_ADV_menos bueno_ADJ_bueno") == [
        ("más o menos", "compromiser", "bueno")
    ]


def test_por_lo_menos_keeps_host_bare():
    assert hosts("por_ADP_por lo_PRON_él menos_ADV_menos tranquilo_ADJ_tranquilo") == [("/", "/", "tranquilo")]


def test_result_clause_past_segment_comma(tmp_path):
    (tmp_path / "S01.txt").write_text(
        "es_AUX_ser tan_ADV_tan descarado_ADJ_descarado ,_PUNCT_, que_SCONJ_que hasta_ADV_hasta se_PRON_él fue_VERB_ir\n",
        encoding="utf-8",
    )
    df = analyze(str(tmp_path))
    assert "descarado" not in set(df.get("Lex_Adj", []))


@pytest.mark.parametrize(
    "segment",
    [
        "compartimos_VERB_compartir mucho_ADV_mucho juntos_ADJ_junto",
        "he_AUX_haber estado_AUX_estar mucho_ADV_mucho hospitalizada_ADJ_hospitalizado",
    ],
)
def test_mucho_on_verb_leaves_adjective_bare(segment):
    assert token(segment)["Int"] == "/"


def test_dialectal_mucho_after_ser_intensifies():
    assert token("era_AUX_ser mucho_ADV_mucho chusco_ADJ_chusco")["Int"] == "mucho"


@pytest.mark.parametrize(
    ("tagged", "int_", "host"),
    [
        ("es_AUX_ser muy_ADV_mucho distin_ADJ_distin to_X_to", "muy", ("Lex_Adj", "distinto")),
        ("no_ADV_no es_AUX_ser tan_ADV_tan lejo_ADV_lejo s_X_s", "tan", ("Adv", "lejos")),
        ("está_AUX_estar muy_ADV_mucho calma_ADJ_calma do_ADV_do", "muy", ("Lex_Adj", "calmado")),
        ("es_AUX_ser muy_ADV_mucho bue_ADV_bue no_ADV_no", "muy", ("Lex_Adj", "bueno")),
    ],
)
def test_analyze_rejoins_split_words(tmp_path, tagged, int_, host):
    (tmp_path / "S01.txt").write_text(tagged + "\n", encoding="utf-8")
    rows = analyze(str(tmp_path), parses=lambda f: [None] * len(tagged.split()))
    assert len(rows) == 1
    assert (rows.iloc[0]["Int"], rows.iloc[0][host[0]]) == (int_, host[1])


def test_split_bue_no_restart_stays_fragment():
    from extract import join_splits

    words = ["son_AUX_ser", "bue_ADV_bue", "no_ADV_no", "son_AUX_ser"]
    assert join_splits(words)[0] == words


def test_split_noun_cuidado_keeps_noun_and_others_take_word_tag():
    from extract import join_splits

    words, _ = join_splits(["mucho_DET_mucho", "cuida_NOUN_cuidar", "do_NOUN_do", "horri_NOUN_horri", "bles_ADJ_bles"])
    assert words == ["mucho_DET_mucho", "cuidado_NOUN_cuidado", "horribles_ADJ_horrible"]


def test_write_outputs_without_speakers_adds_no_metadata(tmp_path):
    corrected = tmp_path / "corrected"
    corrected.mkdir()
    (corrected / "S01.txt").write_text("es_AUX_ser muy_ADV_mucho rebonita_ADJ_rebonito ._PUNCT_.\n", encoding="utf-8")
    output = str(tmp_path / "out")

    df = write_outputs(analyze(str(corrected)), output)

    assert "Gender" not in df.columns
    assert (tmp_path / "out.sqlite").exists()
    assert not (tmp_path / "out_re-words.txt").exists()


@pytest.mark.parametrize(
    ("tagged", "expected"),
    [
        ("es_AUX_ser muy_ADV_mucho feliz_ADJ_feliz", ("muy", "feliz", "feliz")),
        ("son_AUX_ser muy_ADV_mucho felices_ADJ_feliz", ("muy", "felices", "feliz")),
        ("es_AUX_ser capaz_ADJ_capaz", ("/", "capaz", "capaz")),
        ("fue_AUX_ser tenaz_ADJ_tenaz", ("/", "tenaz", "tenaz")),
        ("palabras_NOUN_palabra soeces_ADJ_soez", ("/", "soeces", "soez")),
    ],
)
def test_z_adjectives_are_hosts(tagged, expected):
    row = token(tagged)
    assert (row["Int"], row["Adj"], row["Lex_Adj"]) == expected


@pytest.mark.parametrize(
    "tagged",
    [
        "cebolla_NOUN_cebolla cabezona_ADJ_cabez",
        "una_DET_uno diz_ADJ_diz cosa_NOUN_cosa",
        "la_DET_el mano_NOUN_mano iz_ADJ_iz",
    ],
)
def test_cut_z_lemmas_are_not_hosts(tagged):
    assert process_segment(tagged, "S01") == []
