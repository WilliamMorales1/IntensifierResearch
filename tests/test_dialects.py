import pytest

import dialects
from dialects import co, pr
from extract import process_segment
from extract_stanza import correct_line

pr_cases = [
    ("muy_ADV_mucho celca_ADJ_celca", "muy_ADV_mucho celca_ADV_cerca"),
    ("bien_ADV_bien fuelte_ADJ_fuelte", "bien_ADV_bien fuelte_ADJ_fuerte"),
    ("cieltas_ADJ_cielto cosas_NOUN_cosa", "cieltas_ADJ_cierto cosas_NOUN_cosa"),
    ("dejaba_VERB_dejar vel_ADJ_vel", "dejaba_VERB_dejar vel_VERB_ver"),
    ("está_AUX_estar alrededol_ADJ_alrededol de_ADP_de", "está_AUX_estar alrededol_ADV_alrededor de_ADP_de"),
    ("desde_ADP_desde cocinal_ADJ_cocinal", "desde_ADP_desde cocinal_VERB_cocinar"),
    ("de_ADP_de gualdal_ADJ_gualdal", "de_ADP_de gualdal_VERB_guardar"),
    ("tiempo_NOUN_tiempo polque_ADJ_polque no_ADV_no", "tiempo_NOUN_tiempo polque_SCONJ_porque no_ADV_no"),
    ("el_DET_el sabol_ADJ_sabol", "el_DET_el sabol_NOUN_sabor"),
    ("mi_DET_mi primel_ADJ_primelo año_NOUN_año", "mi_DET_mi primel_ADJ_primero año_NOUN_año"),
    (",_PUNCT_, polque_ADV_polque la_DET_el", ",_PUNCT_, polque_SCONJ_porque la_DET_el"),
    ("bien_ADV_bien velde_ADJ_velde", "bien_ADV_bien velde_ADJ_verde"),
    ("pa_ADP_para estudial_ADJ_estudial", "pa_ADP_para estudial_VERB_estudiar"),
    ("no_ADV_no impolta_ADJ_impolta", "no_ADV_no impolta_VERB_importar"),
]
co_cases = [
    ("fue_AUX_ser muy_ADV_mucho chéere_VERB_cherer", "fue_AUX_ser muy_ADV_mucho chéere_ADJ_chévere"),
    ("un_DET_uno chevre_NOUN_chevre", "un_DET_uno chevre_ADJ_chévere"),
    ("muy_ADV_mucho chéere_ADJ_chéere", "muy_ADV_mucho chéere_ADJ_chévere"),
    ("parece_VERB_parecer muy_ADV_mucho chevre_ADV_chevre", "parece_VERB_parecer muy_ADV_mucho chevre_ADJ_chévere"),
    ("fue_AUX_ser muy_ADV_mucho chéer_ADJ_chéer", "fue_AUX_ser muy_ADV_mucho chéer_ADJ_chévere"),
    ("muy_ADV_mucho complicao_ADJ_complicao", "muy_ADV_mucho complicao_ADJ_complicado"),
    ("muy_ADV_mucho consentio_ADJ_consentio", "muy_ADV_mucho consentio_ADJ_consentido"),
    ("entoes_NOUN_ento fuimos_VERB_ir", "entoes_ADV_ento fuimos_VERB_ir"),
    ("y_CCONJ_y entoes_VERB_entar", "y_CCONJ_y entoes_ADV_entar"),
]


@pytest.mark.parametrize(("line", "fixed"), pr_cases)
def test_pr(line, fixed):
    assert correct_line(line, [pr]) == fixed


@pytest.mark.parametrize(("line", "fixed"), co_cases)
def test_co(line, fixed):
    assert correct_line(line, [co]) == fixed


@pytest.mark.parametrize("line", [line for line, _ in pr_cases + co_cases])
def test_dialect_rules_off_by_default(line):
    assert correct_line(line) == line


@pytest.mark.parametrize(("line", "fixed"), pr_cases + co_cases)
def test_dialects_together(line, fixed):
    assert correct_line(line, dialects.load(["pr", "co", "pr"])) == fixed


def test_pr_lemma_gives_adverb_host():
    (row,) = process_segment(correct_line("es_AUX_ser muy_ADV_mucho celca_ADJ_celca", [pr]), "S01")
    assert (row["Int"], row["Adv"]) == ("muy", "cerca")


def test_co_entoes_is_non_gradable_host():
    (row,) = process_segment(correct_line("entoes_ADJ_ento fuimos_VERB_ir", [co]), "S01")
    assert (row["Adv"], row["Adj"]) == ("entoes", "/")
