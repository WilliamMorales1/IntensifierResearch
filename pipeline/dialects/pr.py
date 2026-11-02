# Puerto Rican Spanish: /r/ lateralized to /l/ before a consonant or word end (cielto, fuelte, celca, estudial)

import re


def delateralize(word):
    """delateralize turns each syllable-final l back into r (cielto -> cierto)."""
    return re.sub(r"l(?=[^aeiouáéíóú]|$)", "r", word)


# adjective lemmas the tagger leaves lateralized
lemma_fixes = {
    w: delateralize(w)
    for w in (
        "cielto", "impoltante", "superiol", "mejol", "fuelte", "milital", "avelgonzado", "muelto", "menol", "celcano",
        "populal", "unifolme", "nelvioso", "coltado", "pueltorriqueño", "familial", "regulal", "celulal", "pelfecto",
        "abielto", "insopoltable", "peol", "pelfeccionista", "lalgo", "pelsonal", "mayol", "velde", "diveltido",
        "solal", "particulal", "cualto",
    )
}  # fmt: skip
# lateralized non-adjectives the tagger calls ADJ
lateral_words = {
    "celca": ("ADV", "cerca"),
    "alrededol": ("ADV", "alrededor"),
    "talde": ("ADV", "tarde"),
    "vel": ("VERB", "ver"),
    "polque": ("SCONJ", "porque"),
    "pol": ("ADP", "por"),
    "helmano": ("NOUN", "hermano"),
    "impolta": ("VERB", "importar"),
}
lateral_words |= {
    w: ("VERB", delateralize(w))
    for w in (
        "cocinal", "limpial", "celebral", "explotal", "manejal", "adoptal", "pical", "llenal", "regresal", "folmal",
        "logral", "tratal", "llegal", "jugal", "dural", "salil", "sobresalil", "asistil", "lucil", "estudial", "vivil",
        "consideral", "competil", "pronuncial", "imaginal", "paral",
    )
}  # fmt: skip


def correct(tokens, i, upos, lemma):
    """correct returns the fixed (upos, lemma) of token i, or None to leave it to the general rules."""
    low = tokens[i][0].lower()
    if low in lateral_words and (low == "celca" or upos in ("ADJ", "ADV")):
        return lateral_words[low]
    return None


def fix_lemma(upos, lemma):
    return lemma_fixes.get(lemma, lemma)
