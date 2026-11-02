# Colombian Spanish: chévere spellings, conchudo, entoes, and dropped intervocalic d (complicao, consentio)

import re

# adjectives the tagger, trained on standard Spanish, often calls NOUN, VERB or ADV
dialect_adjs = {"chevre": "chévere", "chevere": "chévere"}
lemma_fixes = {"chevre": "chévere"}
# dropped intervocalic d in -ido ("consentio", "conocío")
lemma_fixes |= {"consentio": "consentido", "conocío": "conocido"}


def correct(tokens, i, upos, lemma):
    """correct returns the fixed (upos, lemma) of token i, or None to leave it to the general rules."""
    low = tokens[i][0].lower()
    if upos in ("NOUN", "PROPN", "VERB", "ADV") and low in dialect_adjs:
        return "ADJ", dialect_adjs[low]
    # "entoes" (entonces) as ADJ, NOUN, VERB or PRON
    if low == "entoes" and upos != "ADV":
        return "ADV", lemma
    return None


def fix_lemma(upos, lemma):
    if upos == "ADJ" and re.search(r".{3}ao$", lemma):
        # dropped intervocalic d: "complicao", "pesao", "calmao"
        lemma = lemma[:-2] + "ado"
    return lemma_fixes.get(lemma, lemma)
