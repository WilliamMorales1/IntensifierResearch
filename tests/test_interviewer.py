import pytest

from interviewer import remove_interviewer, remove_interviewer_tagged

pad = "".join(f"relleno {i}\n" for i in range(10))


@pytest.mark.parametrize(
    ("lines", "kept"),
    [
        (["¿y por qué le gustaría ir a vivir allá?", "sí, mucho también"], ["", "sí, mucho también"]),
        (["E. ¿en qué barrio vive?", "en Antonio Nariño"], ["", "en Antonio Nariño"]),
        (["e: ¿y cómo es?", "bonito"], ["", "bonito"]),
        (["I.. ¿el peor susto de mi vida? un día"], ["¿el peor susto de mi vida? un día"]),
        # the participant echoing the question stays; the short question it echoes goes
        (["¿pero cercano?", "¿cercano?, sí una vez"], ["", "¿cercano?, sí una vez"]),
        (["¿mi casa?", "es grande"], ["¿mi casa?", "es grande"]),
        (["¿en qué sentido?", "más planita"], ["¿en qué sentido?", "más planita"]),
        (["¿cierto?", "ya"], ["¿cierto?", "ya"]),
        (["“ ¿Ustedes dos nada más? ”", "veinticinco"], ["“ ¿Ustedes dos nada más? ”", "veinticinco"]),
        (["¿cuentos de historias?", "Sí, también."], ["", "Sí, también."]),
        (["tú no puedes, ¿quién eres tú para eso?", "nadie"], ["tú no puedes, ¿quién eres tú para eso?", "nadie"]),
    ],
)
def test_line_based(lines, kept):
    assert remove_interviewer(pad + "\n".join(lines)).split("\n")[10:] == kept


@pytest.mark.parametrize(
    ("text", "kept"),
    [
        (
            "amiga? bueno ahora vamos a la parte de tu profesión ¿a que te dedicas? ¿en que te gustaría trabajar? en un banco",
            "amiga? en un banco",
        ),
        (
            "¿tienes amigos? ¿como eran tus amigos de infancia? ¿qué diferencia hay entre esos amigos y los de ahora? pues muchos",
            "pues muchos",
        ),
        ("muy imperativos. si ¿qué más te puedo decir? de mis dos hijos", None),
        ("me dice el profe ¿y usted cultiva papa? le dije claro", None),
        ("le decía ven acá, ven acá ¿tú quieres comprar esta casa? pero no", None),
        ("nos dio tiempo ¿no le parece? es como uno le advierte a sus hijos de los peligros.", None),
    ],
)
def test_inline(text, kept):
    assert remove_interviewer(text).split() == (kept or text).split()


def test_tagged_tokens_follow_word_spans():
    lines = ["x_NOUN_x"] * 10 + [
        "¿_PUNCT_¿ y_CCONJ_y por_ADP_por qué_PRON_qué le_PRON_él gustaría_VERB_gustar ir_VERB_ir ?_PUNCT_?",
        "sí_INTJ_sí ,_PUNCT_, mucho_ADV_mucho",
    ]
    assert remove_interviewer_tagged("\n".join(lines)).split("\n")[10:] == ["", "sí_INTJ_sí ,_PUNCT_, mucho_ADV_mucho"]


def test_inline_keeps_quote_after_finished_sentence_and_long_generic_tu():
    text = "mi abuelo los paró y les dijo. ¿usted quiere que coman? me preguntó"
    assert remove_interviewer(text).split() == text.split()
    text = (
        "¿qué comida preparas? mmm y luego procedes pues a amarrarlos si tu no los amarras bien se les entra el agua "
        "y pues se van a dañar todos los tamales que uno hace con tanto cuidado en la casa."
    )
    assert "amarrarlos" in remove_interviewer(text)
