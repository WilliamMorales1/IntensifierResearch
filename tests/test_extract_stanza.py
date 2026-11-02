from pathlib import Path
from types import SimpleNamespace

import pytest

from extract import analyze, process_segment, write_outputs
from extract_stanza import (
    Dep,
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
        ("¿_PUNCT_¿ cierto_ADJ_cierto ?_PUNCT_?", "¿_PUNCT_¿ cierto_INTJ_cierto ?_PUNCT_?"),
        ("¿_PUNCT_¿ no_ADV_no cierto_ADJ_cierto ?_PUNCT_?", "¿_PUNCT_¿ no_ADV_no cierto_INTJ_cierto ?_PUNCT_?"),
        ("es_AUX_ser cierto_ADJ_cierto ?_PUNCT_?", "es_AUX_ser cierto_ADJ_cierto ?_PUNCT_?"),
        ("mjum_NOUN_mjum exacto_ADJ_exacto es_AUX_ser", "mjum_NOUN_mjum exacto_INTJ_exacto es_AUX_ser"),
        ("?_PUNCT_? claro_ADJ_claro mjum_NOUN_mjum", "?_PUNCT_? claro_INTJ_claro mjum_NOUN_mjum"),
        (
            "claro_INTJ_claro claro_ADJ_claro porque_SCONJ_porque",
            "claro_INTJ_claro claro_INTJ_claro porque_SCONJ_porque",
        ),
        ("el_DET_el momento_NOUN_momento exacto_ADJ_exacto", "el_DET_el momento_NOUN_momento exacto_ADJ_exacto"),
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
        ("es_AUX_ser muy_ADV_mucho amigo_NOUN_amigo", "es_AUX_ser muy_ADV_mucho amigo_ADJ_amigo"),
        ("son_AUX_ser muy_ADV_mucho caras_NOUN_cara", "son_AUX_ser muy_ADV_mucho caras_ADJ_cara"),
        ("muy_ADV_mucho falta_NOUN_falta de_ADP_de", "muy_ADV_mucho falta_NOUN_falta de_ADP_de"),
        ("muy_ADV_mucho val_NOUN_val", "muy_ADV_mucho val_NOUN_val"),
        ("súper_ADV_súper restaurante_NOUN_restaurante", "súper_ADV_súper restaurante_NOUN_restaurante"),
        ("muy_ADV_mucho chevere_ADJ_chevere", "muy_ADV_mucho chevere_ADJ_chévere"),
        ("yo_PRON_yo vivo_ADJ_vivo aquí_ADV_aquí", "yo_PRON_yo vivo_VERB_vivir aquí_ADV_aquí"),
        (",_PUNCT_, vivo_ADJ_vivo en_ADP_en", ",_PUNCT_, vivo_VERB_vivir en_ADP_en"),
        ("donde_PRON_donde vivo_ADJ_vivo ,_PUNCT_,", "donde_PRON_donde vivo_VERB_vivir ,_PUNCT_,"),
        ("está_AUX_estar vivo_ADJ_vivo en_ADP_en", "está_AUX_estar vivo_ADJ_vivo en_ADP_en"),
        ("muy_ADV_mucho vivo_ADJ_vivo con_ADP_con", "muy_ADV_mucho vivo_ADJ_vivo con_ADP_con"),
        ("un_DET_uno animal_NOUN_animal vivo_ADJ_vivo", "un_DET_uno animal_NOUN_animal vivo_ADJ_vivo"),
        ("trabajo_NOUN_trabajo vivo_ADJ_vivo feliz_ADJ_feliz", "trabajo_NOUN_trabajo vivo_VERB_vivir feliz_ADJ_feliz"),
        ("no_ADV_no vivo_ADJ_vivo ,_PUNCT_,", "no_ADV_no vivo_VERB_vivir ,_PUNCT_,"),
        ("llegó_VERB_llegar vivo_ADJ_vivo ,_PUNCT_,", "llegó_VERB_llegar vivo_ADJ_vivo ,_PUNCT_,"),
        ("si_SCONJ_si claro_ADJ_claro ,_PUNCT_,", "si_SCONJ_si claro_INTJ_claro ,_PUNCT_,"),
        ("tengo_VERB_tener claro_ADJ_claro que_SCONJ_que", "tengo_VERB_tener claro_ADJ_claro que_SCONJ_que"),
        ("pues_SCONJ_pues primero_ADJ_primero se_PRON_él", "pues_SCONJ_pues primero_ADV_primero se_PRON_él"),
        ("lo_PRON_él primero_ADJ_primero que_PRON_que", "lo_PRON_él primero_ADJ_primero que_PRON_que"),
        ("el_DET_el primero_ADJ_primero ,_PUNCT_,", "el_DET_el primero_ADJ_primero ,_PUNCT_,"),
        ("primero_ADJ_primero año_NOUN_año", "primero_ADJ_primero año_NOUN_año"),
        (
            "tiene_VERB_tener primero_ADJ_primero y_CCONJ_y segundo_ADJ_segundo",
            "tiene_VERB_tener primero_ADJ_primero y_CCONJ_y segundo_ADJ_segundo",
        ),
        ("medio_ADJ_medio ambiente_ADJ_ambiente", "medio_ADJ_medio ambiente_NOUN_ambiente"),
        ("estados_PROPN_estados unidos_ADJ_unido", "estados_PROPN_estados unidos_PROPN_unido"),
        ("somos_AUX_ser muy_ADV_mucho unidos_ADJ_unido", "somos_AUX_ser muy_ADV_mucho unidos_ADJ_unido"),
        ("en_ADP_en san_ADJ_san Javier_PROPN_Javier", "en_ADP_en san_PROPN_san Javier_PROPN_Javier"),
        ("mi_DET_mi cuarto_ADJ_cuarto ,_PUNCT_,", "mi_DET_mi cuarto_NOUN_cuarto ,_PUNCT_,"),
        ("cuarto_ADJ_cuarto piso_NOUN_piso", "cuarto_ADJ_cuarto piso_NOUN_piso"),
        ("barrio_NOUN_barrio estrato_ADJ_estrato", "barrio_NOUN_barrio estrato_NOUN_estrato"),
        ("se_PRON_él le_PRON_él hecha_ADJ_hecho", "se_PRON_él le_PRON_él hecha_VERB_echar"),
        ("mal_ADV_mal hecho_ADJ_hecho", "mal_ADV_mal hecho_ADJ_hecho"),
        ("debido_ADJ_debido a_ADP_a", "debido_ADP_debido a_ADP_a"),
        ("su_DET_su debido_ADJ_debido tiempo_NOUN_tiempo", "su_DET_su debido_ADJ_debido tiempo_NOUN_tiempo"),
        ("junto_ADJ_junto a_ADP_a", "junto_ADV_junto a_ADP_a"),
        ("vivir_VERB_vivir juntos_ADJ_junto a_ADP_a", "vivir_VERB_vivir juntos_ADJ_junto a_ADP_a"),
        ("el_DET_el medio_ADJ_medio día_NOUN_día", "el_DET_el medio_NOUN_medio día_NOUN_día"),
        ("dos_NUM_dos y_CCONJ_y media_ADJ_medio", "dos_NUM_dos y_CCONJ_y media_NUM_medio"),
        ("clase_NOUN_clase media_ADJ_medio", "clase_NOUN_clase media_ADJ_medio"),
        ("y_CCONJ_y listo_ADJ_listo ,_PUNCT_,", "y_CCONJ_y listo_INTJ_listo ,_PUNCT_,"),
        ("todo_PRON_todo listo_ADJ_listo ,_PUNCT_,", "todo_PRON_todo listo_ADJ_listo ,_PUNCT_,"),
        ("bueno_INTJ_bueno total_ADJ_total que_SCONJ_que", "bueno_INTJ_bueno total_ADV_total que_SCONJ_que"),
        ("cambio_NOUN_cambio total_ADJ_total ,_PUNCT_,", "cambio_NOUN_cambio total_ADJ_total ,_PUNCT_,"),
        ("pero_CCONJ_pero seguro_ADJ_seguro que_SCONJ_que", "pero_CCONJ_pero seguro_ADV_seguro que_SCONJ_que"),
        ("estoy_AUX_estar seguro_ADJ_seguro que_SCONJ_que", "estoy_AUX_estar seguro_ADJ_seguro que_SCONJ_que"),
        ("comen_VERB_comer claro_ADJ_claro ._PUNCT_.", "comen_VERB_comer claro_INTJ_claro ._PUNCT_."),
        (
            "estudiar_VERB_estudiar claro_ADJ_claro que_SCONJ_que",
            "estudiar_VERB_estudiar claro_INTJ_claro que_SCONJ_que",
        ),
        ("conoces_VERB_conocer cierto_ADJ_cierto ?_PUNCT_?", "conoces_VERB_conocer cierto_INTJ_cierto ?_PUNCT_?"),
        ("tengo_VERB_tener claro_ADJ_claro ._PUNCT_.", "tengo_VERB_tener claro_ADJ_claro ._PUNCT_."),
        (
            "relativamente_ADV_relativamente claro_ADJ_claro ._PUNCT_.",
            "relativamente_ADV_relativamente claro_ADJ_claro ._PUNCT_.",
        ),
        (
            "un_DET_uno cambio_NOUN_cambio claro_ADJ_claro ?_PUNCT_?",
            "un_DET_uno cambio_NOUN_cambio claro_ADJ_claro ?_PUNCT_?",
        ),
        ("moreno_NOUN_moreno claro_ADJ_claro ,_PUNCT_,", "moreno_NOUN_moreno claro_ADJ_claro ,_PUNCT_,"),
        (",_PUNCT_, cierto_ADJ_cierto ._PUNCT_.", ",_PUNCT_, cierto_INTJ_cierto ._PUNCT_."),
        ("era_AUX_ser puro_ADJ_puro barro_NOUN_barro", "era_AUX_ser puro_DET_puro barro_NOUN_barro"),
        ("aire_NOUN_aire puro_ADJ_puro", "aire_NOUN_aire puro_ADJ_puro"),
        (
            "comiendo_VERB_comer solo_ADJ_solo pescado_NOUN_pescado",
            "comiendo_VERB_comer solo_ADV_solo pescado_NOUN_pescado",
        ),
        ("una_DET_uno sola_ADJ_solo casa_NOUN_casa", "una_DET_uno sola_ADJ_solo casa_NOUN_casa"),
        ("muy_ADV_mucho alto_ADJ_alto", "muy_ADV_mucho alto_ADJ_alto"),
        ("muy_ADV_mucho parte_NOUN_parte de_ADP_de", "muy_ADV_mucho parte_NOUN_parte de_ADP_de"),
        ("la_DET_el semana_NOUN_semana santa_ADJ_santo", "la_DET_el semana_NOUN_semana santa_PROPN_santo"),
        ("de_ADP_de santo_ADJ_santo domingo_NOUN_domingo", "de_ADP_de santo_PROPN_santo domingo_NOUN_domingo"),
        ("el_DET_el santo_ADJ_santo día_NOUN_día", "el_DET_el santo_ADJ_santo día_NOUN_día"),
        ("ahí_ADV_ahí mismo_ADJ_mismo fue_AUX_ser", "ahí_ADV_ahí mismo_ADV_mismo fue_AUX_ser"),
        ("ahora_ADV_ahora mismo_ADJ_mismo ,_PUNCT_,", "ahora_ADV_ahora mismo_ADV_mismo ,_PUNCT_,"),
        ("uno_PRON_uno mismo_ADJ_mismo ,_PUNCT_,", "uno_PRON_uno mismo_ADJ_mismo ,_PUNCT_,"),
        (
            "pasa_VERB_pasar mucho_PRON_mucho vicioso_ADJ_vicioso",
            "pasa_VERB_pasar mucho_PRON_mucho vicioso_NOUN_vicioso",
        ),
        (",_PUNCT_, mucho_PRON_mucho corrupto_ADJ_corrupto", ",_PUNCT_, mucho_PRON_mucho corrupto_NOUN_corrupto"),
        ("puesto_VERB_poner mucho_ADV_mucho malos_ADJ_malo", "puesto_VERB_poner mucho_ADV_mucho malos_ADJ_malo"),
        (
            "estado_AUX_estar mucho_ADV_mucho hospitalizada_ADJ_hospitalizado",
            "estado_AUX_estar mucho_ADV_mucho hospitalizada_ADJ_hospitalizado",
        ),
        ("mucho_PRON_mucho mucho_PRON_mucho raro_ADJ_raro", "mucho_PRON_mucho mucho_PRON_mucho raro_ADJ_raro"),
        (
            "barrio_NOUN_barrio Villa_PROPN_Villa Nueva_ADJ_nuevo",
            "barrio_NOUN_barrio Villa_PROPN_Villa Nueva_PROPN_nuevo",
        ),
        ("en_ADP_en nueva_ADJ_nuevo york_PROPN_york", "en_ADP_en nueva_PROPN_nuevo york_PROPN_york"),
        ("._PUNCT_. Nueva_ADJ_nuevo", "._PUNCT_. Nueva_ADJ_nuevo"),
        ("ESTOY_AUX_estar PENDIENTE_ADJ_pendiente", "ESTOY_AUX_estar PENDIENTE_ADJ_pendiente"),
        ("pandillas_NOUN_pandilla digámoslo_ADJ_digámoslo", "pandillas_NOUN_pandilla digámoslo_VERB_digámoslo"),
        ("son_AUX_ser difíciles_ADJ_difícil", "son_AUX_ser difíciles_ADJ_difícil"),
        ("los_DET_el ángeles_ADJ_ángeles", "los_DET_el ángeles_ADJ_ángeles"),
        ("muy_ADV_mucho a_ADP_a menudo_ADJ_menudo", "muy_ADV_mucho a_ADP_a menudo_ADV_menudo"),
        (
            "tengo_VERB_tener entendido_ADJ_entendido que_SCONJ_que",
            "tengo_VERB_tener entendido_VERB_entender que_SCONJ_que",
        ),
        ("yo_PRON_yo saludo_ADJ_saludo", "yo_PRON_yo saludo_VERB_saludar"),
        ("avión_NOUN_avión hermano_ADJ_hermano ,_PUNCT_,", "avión_NOUN_avión hermano_NOUN_hermano ,_PUNCT_,"),
        ("por_ADP_por lo_PRON_él regular_ADJ_regular", "por_ADP_por lo_PRON_él regular_ADV_regular"),
        ("es_AUX_ser regular_ADJ_regular", "es_AUX_ser regular_ADJ_regular"),
        (
            "edificio_NOUN_edificio jajaja_ADV_jajaja pero_CCONJ_pero",
            "edificio_NOUN_edificio jajaja_INTJ_jajaja pero_CCONJ_pero",
        ),
        ("tienen_VERB_tener je_ADV_je mi_DET_mi", "tienen_VERB_tener je_INTJ_je mi_DET_mi"),
        (
            "trabajar_VERB_trabajar ,_PUNCT_, bueno_ADV_bueno mi_DET_mi",
            "trabajar_VERB_trabajar ,_PUNCT_, bueno_INTJ_bueno mi_DET_mi",
        ),
        ("y_CCONJ_y claro_ADV_claro ellos_PRON_él", "y_CCONJ_y claro_INTJ_claro ellos_PRON_él"),
        ("progresado_VERB_progresar claro_ADV_claro ,_PUNCT_,", "progresado_VERB_progresar claro_INTJ_claro ,_PUNCT_,"),
        ("habla_VERB_hablar claro_ADV_claro ,_PUNCT_,", "habla_VERB_hablar claro_ADV_claro ,_PUNCT_,"),
        ("muy_ADV_mucho claro_ADV_claro ,_PUNCT_,", "muy_ADV_mucho claro_ADV_claro ,_PUNCT_,"),
        ("la_DET_el ciclo_NOUN_ciclo vía_ADJ_vía", "la_DET_el ciclo_NOUN_ciclo vía_NOUN_vía"),
        ("contrato_NOUN_contrato jugosísimo_ADV_jugosísimo", "contrato_NOUN_contrato jugosísimo_ADJ_jugosísimo"),
        ("parece_VERB_parecer jartísimo_ADV_jartísimo", "parece_VERB_parecer jartísimo_ADJ_jartísimo"),
        ("quieren_VERB_querer hartísimo_ADV_hartísimo", "quieren_VERB_querer hartísimo_ADV_hartísimo"),
        ("divertía_VERB_divertir artísimo_ADV_artísimo", "divertía_VERB_divertir artísimo_ADV_artísimo"),
        ("a_ADP_a el_DET_el altísimo_NOUN_altísimo", "a_ADP_a el_DET_el altísimo_NOUN_altísimo"),
        ("volé_VERB_volar lejísimos_ADV_lejísimo", "volé_VERB_volar lejísimos_ADV_lejísimo"),
        ("es_AUX_ser muy_ADV_mucho mamona_ADJ_mamon", "es_AUX_ser muy_ADV_mucho mamona_ADJ_mamón"),
        ("son_AUX_ser muy_ADV_mucho cansonas_ADJ_cansono", "son_AUX_ser muy_ADV_mucho cansonas_ADJ_cansón"),
        ("muy_ADV_mucho monótona_ADJ_monótono", "muy_ADV_mucho monótona_ADJ_monótono"),
        ("muy_ADV_mucho mona_ADJ_mono", "muy_ADV_mucho mona_ADJ_mono"),
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
    assert first[4] == ("predicative", "casa", "es", "ser", "/", False)
    assert first[6] == ("predicative", "casa", "es", "ser", "/", False)
    assert first[3] == ("ambiguous", "/", "es", "ser", "/", False)
    assert first[0] is None
    # object is a pronoun, so no noun
    assert second[3] == ("predicative", "/", "veo", "ver", "/", False)
    assert third[4] == ("attributive", "casas", "vivo", "vivir", "/", False)
    assert third[6][2:4] == ("vivo", "vivir")


def test_noun_parsed_before_correction_gets_relation():
    # "él es muy amigo": correct_tokens makes amigo ADJ after the parse called it NOUN
    sent = [
        Dep(1, "él", "PRON", "él", 4, "nsubj"),
        Dep(2, "es", "AUX", "ser", 4, "cop"),
        Dep(3, "muy", "ADV", "mucho", 4, "advmod"),
        Dep(4, "amigo", "NOUN", "amigo", 0, "root"),
    ]
    assert sentence_relations(sent)[3] == ("predicative", "/", "es", "ser", "/", False)


def test_verb_parsed_before_correction_is_not_its_own_verb():
    # "fue muy chéere": the parse made chéere a VERB heading the clause
    sent = [
        Dep(1, "fue", "AUX", "ser", 3, "cop"),
        Dep(2, "muy", "ADV", "mucho", 3, "advmod"),
        Dep(3, "chéere", "VERB", "chévere", 0, "root"),
    ]
    assert sentence_relations(sent)[2] == ("predicative", "/", "fue", "ser", "/", False)


def test_adverb_parsed_before_correction_gets_relation():
    # "me parece muy chevre": the parse called chevre ADV, correct_tokens makes it ADJ
    sent = [
        Dep(1, "eso", "PRON", "ese", 3, "nsubj"),
        Dep(2, "me", "PRON", "yo", 3, "iobj"),
        Dep(3, "parece", "VERB", "parecer", 0, "root"),
        Dep(4, "muy", "ADV", "mucho", 5, "advmod"),
        Dep(5, "chevre", "ADV", "chévere", 3, "advmod"),
    ]
    assert sentence_relations(sent)[4] == ("predicative", "/", "parece", "parecer", "/", False)


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
    assert sentence_relations(sent)[2] == ("predicative", "/", "fui", "ser", "/", False)


def test_adjective_under_copular_verb_is_predicative(tmp_path):
    # la comida queda deliciosa ; está en las buenas
    (tmp_path / "S01.conllu").write_text(
        conllu(
            ("la", "DET", "el", 2, "det"),
            ("comida", "NOUN", "comida", 3, "nsubj"),
            ("queda", "VERB", "quedar", 0, "root"),
            ("deliciosa", "ADJ", "delicioso", 3, "obj"),
        )
        + conllu(
            ("está", "VERB", "estar", 0, "root"),
            ("en", "ADP", "en", 4, "case"),
            ("las", "DET", "el", 4, "det"),
            ("buenas", "ADJ", "bueno", 1, "obl"),
        ),
        encoding="utf-8",
    )
    first, second = (sentence_relations(s) for s in read_conllu(tmp_path / "S01.conllu"))
    assert first[3] == ("predicative", "comida", "queda", "quedar", "/", False)
    assert second[3].adj_type == "ambiguous"


def test_adjective_relation_lists_fillers_participles(tmp_path):
    # está muy organizado muy bonito ; mhm , muy joven ; una cabuya atravesada
    (tmp_path / "S01.conllu").write_text(
        conllu(
            ("está", "AUX", "estar", 3, "cop"),
            ("muy", "ADV", "mucho", 3, "advmod"),
            ("organizado", "ADJ", "organizado", 0, "root"),
            ("muy", "ADV", "mucho", 5, "advmod"),
            ("bonito", "ADJ", "bonito", 3, "amod"),
        )
        + conllu(
            ("mhm", "NOUN", "mhm", 0, "root"),
            (",", "PUNCT", ",", 4, "punct"),
            ("muy", "ADV", "mucho", 4, "advmod"),
            ("joven", "ADJ", "joven", 1, "amod"),
        )
        + conllu(
            ("una", "DET", "uno", 2, "det"),
            ("cabuya", "NOUN", "cabuya", 0, "root"),
            ("atravesada", "ADJ", "atravesado", 2, "acl"),
        ),
        encoding="utf-8",
    )
    first, second, third = (sentence_relations(s) for s in read_conllu(tmp_path / "S01.conllu"))
    assert first[4].adj_type == "predicative"
    assert second[3].adj_type == "ambiguous"
    assert third[2][:2] == ("attributive", "cabuya")


def test_analyze_reads_relations_from_parse(tmp_path):
    tagged, out = tmp_path / "tagged", tmp_path / "parsed"
    tagged.mkdir()
    out.mkdir()
    (out / "S01.conllu").write_text(parsed, encoding="utf-8")
    words = [(t, u, l) for s in read_conllu(out / "S01.conllu") for _, t, u, l, _, _ in s]
    # attributive casas viejas is not adjacent in word order to the verb "vivo"
    (tagged / "S01.txt").write_text(" ".join("_".join(w) for w in words) + "\n", encoding="utf-8")

    df = analyze(str(tagged), str(tmp_path / "out.csv"), parse_relations(str(out)))

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

    df = analyze(str(tagged), str(tmp_path / "out.csv"), parse_relations(str(out)))

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


def test_examples_reproduce_their_output(tmp_path):
    examples = Path(__file__).parent.parent / "examples"
    corrected = tmp_path / "corrected"
    # correct_tokens must still give the corrected tags the committed parse was made from
    correct_folder(str(examples / "stanza_tagged"), str(corrected))
    assert (corrected / "DEMO_M45.txt").read_text(encoding="utf-8") == (
        examples / "stanza_corrected" / "DEMO_M45.txt"
    ).read_text(encoding="utf-8")

    df = analyze(str(corrected), None, parse_relations(str(examples / "stanza_parsed")))
    write_outputs(df, str(tmp_path / "out"), str(examples / "speakers.xlsx"), csv=True)
    assert (tmp_path / "out.csv").read_text(encoding="utf-8") == (examples / "intensifier_data.csv").read_text(
        encoding="utf-8"
    )


def test_parse_file_empty_text_writes_empty_parse(tmp_path):
    src, dst = tmp_path / "short.txt", tmp_path / "short.conllu"
    src.write_text("", encoding="utf-8")

    import extract_stanza as es

    assert es._parse_file((str(src), str(dst))) == "short.txt"
    assert dst.read_text(encoding="utf-8") == ""
    assert es.read_conllu(str(dst)) == []


def test_negation_scope():
    # no es tan bueno ; no me parece muy bonito ; no muy bueno ; ya no está , y es bonito
    sents = [
        [
            Dep(1, "no", "ADV", "no", 4, "advmod"),
            Dep(2, "es", "AUX", "ser", 4, "cop"),
            Dep(3, "tan", "ADV", "tan", 4, "advmod"),
            Dep(4, "bueno", "ADJ", "bueno", 0, "root"),
        ],
        [
            Dep(1, "no", "ADV", "no", 3, "advmod"),
            Dep(2, "me", "PRON", "yo", 3, "iobj"),
            Dep(3, "parece", "VERB", "parecer", 0, "root"),
            Dep(4, "muy", "ADV", "mucho", 5, "advmod"),
            Dep(5, "bonito", "ADJ", "bonito", 3, "xcomp"),
        ],
        [
            Dep(1, "no", "ADV", "no", 2, "advmod"),
            Dep(2, "muy", "ADV", "mucho", 3, "advmod"),
            Dep(3, "bueno", "ADJ", "bueno", 0, "root"),
        ],
        [
            Dep(1, "no", "ADV", "no", 2, "advmod"),
            Dep(2, "está", "VERB", "estar", 0, "root"),
            Dep(3, "y", "CCONJ", "y", 5, "cc"),
            Dep(4, "es", "AUX", "ser", 5, "cop"),
            Dep(5, "bonito", "ADJ", "bonito", 2, "conj"),
        ],
    ]
    assert [sentence_relations(s)[-1].negation for s in sents] == ["no", "no", "no", "/"]


def test_negation_needs_preverbal_slot():
    # no , muy buena ; no la gente es muy buena ; no una casa tan grande ; ni tan aficionado ;
    # no se tenga que desplazar tan lejos
    sents = [
        [
            Dep(1, "no", "ADV", "no", 4, "advmod"),
            Dep(2, ",", "PUNCT", ",", 4, "punct"),
            Dep(3, "muy", "ADV", "mucho", 4, "advmod"),
            Dep(4, "buena", "ADJ", "bueno", 0, "root"),
        ],
        [
            Dep(1, "no", "ADV", "no", 6, "advmod"),
            Dep(2, "la", "DET", "el", 3, "det"),
            Dep(3, "gente", "NOUN", "gente", 6, "nsubj"),
            Dep(4, "es", "AUX", "ser", 6, "cop"),
            Dep(5, "muy", "ADV", "mucho", 6, "advmod"),
            Dep(6, "buena", "ADJ", "bueno", 0, "root"),
        ],
        [
            Dep(1, "no", "ADV", "no", 3, "advmod"),
            Dep(2, "una", "DET", "uno", 3, "det"),
            Dep(3, "casa", "NOUN", "casa", 0, "root"),
            Dep(4, "tan", "ADV", "tan", 5, "advmod"),
            Dep(5, "grande", "ADJ", "grande", 3, "amod"),
        ],
        [
            Dep(1, "ni", "CCONJ", "ni", 3, "advmod"),
            Dep(2, "tan", "ADV", "tan", 1, "fixed"),
            Dep(3, "aficionado", "ADJ", "aficionado", 0, "root"),
        ],
        [
            Dep(1, "no", "ADV", "no", 5, "advmod"),
            Dep(2, "se", "PRON", "él", 5, "expl:pv"),
            Dep(3, "tenga", "VERB", "tener", 0, "root"),
            Dep(4, "que", "SCONJ", "que", 5, "mark"),
            Dep(5, "desplazar", "VERB", "desplazar", 3, "conj"),
            Dep(6, "tan", "ADV", "tan", 7, "advmod"),
            Dep(7, "lejos", "ADV", "lejos", 5, "advmod"),
        ],
    ]
    assert [sentence_relations(s)[-1].negation for s in sents] == ["/", "/", "no", "ni", "no"]


def test_verbal_intensifier():
    # se cansara mucho acostada ; quede bien limpiecita
    cansara = [
        Dep(1, "se", "PRON", "él", 2, "expl:pv"),
        Dep(2, "cansara", "VERB", "cansar", 0, "root"),
        Dep(3, "mucho", "ADV", "mucho", 2, "advmod"),
        Dep(4, "acostada", "ADJ", "acostado", 2, "xcomp"),
    ]
    quede = [
        Dep(1, "quede", "VERB", "quedar", 0, "root"),
        Dep(2, "bien", "ADV", "bien", 1, "advmod"),
        Dep(3, "limpiecita", "ADJ", "limpiecito", 1, "xcomp"),
    ]
    assert sentence_relations(cansara)[3].verbal_int
    assert not sentence_relations(quede)[2].verbal_int
    rows = process_segment(
        "se_PRON_él cansara_VERB_cansar mucho_ADV_mucho acostada_ADJ_acostado", "S01", sentence_relations(cansara)
    )
    assert [(r["Int"], r["Adj"]) for r in rows] == [("/", "acostada")]
