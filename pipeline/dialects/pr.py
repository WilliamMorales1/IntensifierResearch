# Puerto Rican Spanish: /r/ lateralized to /l/ before a consonant or word end (cielto, fuelte, celca, estudial)

import re


def delateralize(word):
    """delateralize turns each syllable-final l back into r (cielto -> cierto)."""
    return re.sub(r"l(?=[^aeiouáéíóú]|$)", "r", word)


# adjective lemmas the tagger leaves lateralized
lemma_fixes = {
    w: delateralize(w)
    for w in (
        "cielto", "impoltante", "superiol", "mejol", "fuelte", "milital", "avelgonzado", "muelto", "menol",
        "univelsitario", "olganizado", "celcano", "populal", "unifolme", "nelvioso", "coltado", "similal", "colto",
        "pueltorriqueño", "familial", "regulal", "celulal", "pelfecto", "abielto", "insopoltable", "peol",
        "pelfeccionista", "lalgo", "pelsonal", "mayol", "velde", "diveltido", "solal", "particulal", "cualto",
    )
}  # fmt: skip
lemma_fixes["primelo"] = "primero"
# lateralized non-adjectives the tagger calls ADJ
lateral_words = {
    "celca": ("ADV", "cerca"),
    "alrededol": ("ADV", "alrededor"),
    "talde": ("ADV", "tarde"),
    "vel": ("VERB", "ver"),
    "calne": ("NOUN", "carne"),
    "palte": ("NOUN", "parte"),
    "hogal": ("NOUN", "hogar"),
    "polque": ("SCONJ", "porque"),
    "pol": ("ADP", "por"),
    "sel": ("AUX", "ser"),
    "sabol": ("NOUN", "sabor"),
    "helmano": ("NOUN", "hermano"),
    "helmanos": ("NOUN", "hermano"),
    "puelto": ("PROPN", "puerto"),
    "profesol": ("NOUN", "profesor"),
    "apaltamento": ("NOUN", "apartamento"),
    "telmino": ("VERB", "terminar"),
    "duelmo": ("VERB", "dormir"),
    "sentalme": ("VERB", "sentar"),
    "impolta": ("VERB", "importar"),
}
lateral_words |= {
    w: ("VERB", delateralize(w))
    for w in (
        "cocinal", "limpial", "llamal", "celebral", "gastal", "destacal", "explotal", "manejal", "hablal", "gualdal",
        "preocupal", "lleval", "adoptal", "pical", "bañal", "laval", "llenal", "regresal", "folmal", "logral",
        "disfrutal", "comental", "tratal", "llegal", "jugal", "dural", "salil", "comel", "sobresalil", "asistil",
        "lucil", "recogel", "correl", "leel", "bebel", "tenel", "estudial", "vivil", "consideral", "competil",
        "pronuncial", "imaginal", "impactal", "paral",
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
