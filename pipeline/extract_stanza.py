# tags the raw transcripts with stanza instead of TagAnt, then runs the same extraction as extract_tagant

import argparse
import os
import re
from collections import namedtuple
from datetime import date
from multiprocessing import get_context

from extract_tagant import (
    analyze,
    intensifier_list,
    speaker_data,
    write_outputs,
)

# the charlm pos model is ~25x slower on CPU
processors = {
    "tokenize": "combined_nocharlm",
    "mwt": "combined",
    "pos": "combined_nocharlm",
    "lemma": "combined_nocharlm",
}
# the parse reruns the tagger on stanza_corrected words only for xpos/feats;
# depparse combined_nocharlm fails to load in torch 2.6, and ancora_nocharlm parsed worse by hand
parse_tagger = {"tokenize": "combined_nocharlm", "pos": "combined_nocharlm"}
parse_processors = {"depparse": "combined_charlm"}

# plural -es stripped one letter too far (chéveres -> chéver)
lemma_fixes = {"chéver": "chévere", "chever": "chévere", "chevere": "chévere", "gritono": "gritón"}
lemma_fixes |= {"chéere": "chévere", "chevre": "chévere", "primelo": "primero"}
# Puerto Rican /r/ lateralized to /l/ in adjective lemmas
lemma_fixes |= {
    w: re.sub(r"l(?=[^aeiouáéíóú]|$)", "r", w)
    for w in (
        "cielto", "impoltante", "superiol", "mejol", "fuelte", "milital", "avelgonzado", "muelto", "menol",
        "univelsitario", "olganizado", "celcano", "populal", "unifolme", "nelvioso", "coltado", "similal", "colto",
        "pueltorriqueño", "familial", "regulal", "celulal", "pelfecto", "abielto", "insopoltable", "peol",
        "pelfeccionista", "lalgo", "pelsonal",
    )
}  # fmt: skip
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
}
lateral_words |= {
    w: ("VERB", re.sub(r"l(?=[^aeiouáéíóú]|$)", "r", w))
    for w in (
        "cocinal", "limpial", "llamal", "celebral", "gastal", "destacal", "explotal", "manejal", "hablal", "gualdal",
        "preocupal", "lleval", "adoptal", "pical", "bañal", "laval", "llenal", "regresal", "folmal", "logral",
        "disfrutal", "comental", "tratal", "llegal", "jugal", "dural", "salil", "comel", "sobresalil", "asistil",
        "lucil", "recogel", "correl", "leel", "bebel", "tenel",
    )
}  # fmt: skip

_nlp = None


def clean_field(text):
    # spaces and underscores would break the word_POS_lemma format extract_tagant parses
    return (text or "").replace(" ", "").replace("_", "-")


def tag_word(word):
    return f"{clean_field(word.text)}_{word.upos}_{clean_field(word.lemma)}"


def tag_doc(doc, skip_chars=()):
    return "\n".join(
        " ".join(tag_word(w) for t in s.tokens if t.start_char not in skip_chars for w in t.words)
        for s in doc.sentences
    )


def join_paragraphs(paragraphs):
    # without final punctuation the tokenizer splits turn-final words (casero -> caser + o),
    # so a period is added and its offset returned for tag_doc to drop
    parts, added, pos = [], set(), 0
    for p in paragraphs:
        if p[-1] not in ".,;:!?¡¿…)]\"'":
            added.add(pos + len(p) + 1)
            p += " ."
        parts.append(p)
        pos += len(p) + 2
    return "\n\n".join(parts), added


# verbs that take a predicative adjective, so "se puso peor" / "sigue igual" stay ADJ
predicative_lemmas = {
    "ser",
    "estar",
    "parecer",
    "poner",
    "sentir",
    "ver",
    "quedar",
    "volver",
    "encontrar",
    "dejar",
    "hallar",
    "seguir",
}
clitics = {"me", "te", "se", "nos", "le", "les", "lo", "la", "los", "las"}
possessives = {p + e for p in ("mí", "tuy", "suy", "nuestr", "vuestr") for e in ("o", "a", "os", "as")}
comparatives = {"mejor", "mejores", "peor", "peores", "mayor", "mayores", "menor", "menores"}
_edge = ("", "PUNCT", "")
fillers = {
    "mhm",
    "mjum",
    "ajá",
    "aja",
    "eh",
    "eeh",
    "ehh",
    "mm",
    "mmm",
    "hum",
    "humm",
    "jum",
    "ah",
    "aah",
    "umm",
    "ehm",
}
discourse_adjs = ("bueno", "claro", "exacto", "listo", "cierto")
# hues that "claro" can modify ("moreno claro") even when the tagger calls them NOUN
colors = ["moreno", "morena", "azul", "verde", "rojo", "rosado", "café", "gris", "amarillo", "marrón", "morado"]
# Colombian adjectives the tagger, trained on standard Spanish, often calls NOUN or VERB
dialect_adjs = {"chéere": "chévere", "chevre": "chévere", "chevere": "chévere", "conchudo": "conchudo"}
# nouns after muy that are not used as adjectives ("muy falta de", "muy toma trago"), or are cut-off words
muy_nouns = {"gente", "cosas", "parte", "falta", "toma", "pulpa", "maleza", "masa", "carga", "calma", "dema", "ente"}
# second halves of compound nouns the tagger reads as noun + adjective
compound_nouns = {
    ("medio", "ambiente"): "NOUN",
    ("sala", "comedor"): "NOUN",
    ("salón", "comedor"): "NOUN",
    ("hora", "pico"): "NOUN",
    ("horas", "pico"): "NOUN",
    ("estados", "unidos"): "PROPN",
    ("ave", "maría"): "PROPN",
}

# "semana santa", "espíritu santo", "santa rita": holy days and saint names, not "todo el santo día"
holy_before = {"semana", "semanas", "espíritu", "lunes", "martes", "miércoles", "jueves", "viernes", "sábado"}
saint_names = {"domingo", "rita", "marta", "maría", "isabel", "rosa", "ana", "lucía", "fe", "bárbara", "catalina",
               "teresa", "clara", "cruz", "helena", "elena", "inés", "mónica", "sofía", "tomás"}  # fmt: skip
# "ahí mismo", "ahora mismo" (right there, right now) vs "yo mismo", "lo mismo"
mismo_advs = {"ahí", "aquí", "acá", "allí", "allá", "así", "ahora", "ahorita", "hoy", "ya", "ayer", "mañana"}


def _around(tokens, i):
    prev = tokens[i - 1] if i > 0 else _edge
    nxt = tokens[i + 1] if i + 1 < len(tokens) else _edge
    nxt2 = tokens[i + 2] if i + 2 < len(tokens) else _edge
    return prev, nxt, nxt2


def _before_verb(nxt, nxt2):
    return nxt[1] in ("VERB", "AUX") or (nxt[0].lower() in clitics and nxt2[1] in ("VERB", "AUX"))


def _holy_name(tokens, i):
    prev, nxt, _ = _around(tokens, i)
    return tokens[i][0][0].isupper() or prev[0].lower() in holy_before or nxt[0].lower() in saint_names


def _adverbial_comparative(tokens, i):
    # "mejor dicho", "a lo mejor", "mejor me voy", "vive mejor" vs "el mejor", "es mejor", "futuro mejor"
    prev, nxt, nxt2 = _around(tokens, i)
    if nxt[0].lower() == "dicho" or (prev[0].lower() == "lo" and i > 1 and tokens[i - 2][0].lower() == "a"):
        return True
    if (
        prev[1] in ("DET", "NOUN", "PROPN", "AUX")
        or prev[2] in predicative_lemmas
        or prev[0].lower() in ("lo", "mucho", "muchísimo", "tanto", "como", "algo", "nada")
    ):
        return False
    return _before_verb(nxt, nxt2) or (prev[1] == "VERB" and nxt[1] not in ("NOUN", "PROPN"))


def _adverbial_igual(tokens, i):
    # "pero igual se fue" (anyway) vs "es igual", "igual a", "igual forma"
    prev, nxt, nxt2 = _around(tokens, i)
    if nxt[1] in ("NOUN", "PROPN") or nxt[0].lower() in ("a", "al", "de", "en"):
        return False
    if prev[1] in ("NOUN", "PROPN") and _before_verb(nxt, nxt2):
        return True
    return not (
        prev[1] in ("DET", "NOUN", "PROPN", "AUX", "ADP")
        or prev[2] in predicative_lemmas
        or prev[0].lower() in intensifier_list + ["lo", "tan", "más", "todo"]
    )


def _discourse_slot(tokens, i):
    # clause-initial and not before a noun: "bueno, ...", "y bueno eso fue", "claro que sí", "mjum exacto", "claro claro"
    prev, nxt, _ = _around(tokens, i)
    return (nxt[1] not in ("NOUN", "PROPN") or nxt[0].lower() in fillers) and (
        prev[1] in ("PUNCT", "CCONJ", "INTJ")
        # "si claro": transcripts often drop the accent on sí
        or prev[0].lower()
        in ("sí", "si", "entonces", "pues", "porque", "no", "ay", "y", "o", "pero", *fillers, *discourse_adjs)
    )


def _tag_question(tokens, i):
    # "¿cierto?", "¿no cierto?", "¿claro?"; "es cierto?" stays ADJ
    prev, nxt, _ = _around(tokens, i)
    if nxt[0] != "?":
        return False
    return prev[0] == "¿" or (prev[0].lower() == "no" and i > 1 and tokens[i - 2][0] == "¿")


def _discourse_tail(tokens, i):
    # "se lo comen claro", "tú la conoces cierto ?", "estudiar claro que" vs "es cierto", "tengo claro", "moreno claro"
    prev, nxt, _ = _around(tokens, i)
    if nxt[1] != "PUNCT" and nxt[0].lower() not in ("que", "está", "pues"):
        return False
    low = prev[0].lower()
    return not (
        prev[1] in ("AUX", "ADJ", "DET", "ADP", "PUNCT")
        or prev[2] in predicative_lemmas | {"tener", "hablar"}
        or low in intensifier_list + ["lo", "tan", "más", "mas", "por", "poco"] + colors
        or low.endswith("mente")
        # "un cambio claro ?"
        or (prev[1] == "NOUN" and i > 1 and tokens[i - 2][0].lower() in ("un", "una"))
    )


def _focus_quantifier(tokens, i):
    # "puro barro", "solo pescado frito" (nothing but, only) vs "aire puro", "una sola casa", "muy solo"
    prev, nxt, _ = _around(tokens, i)
    return nxt[1] == "NOUN" and prev[1] not in ("DET", "ADJ", "NUM") and prev[0].lower() not in intensifier_list


def _quantified_noun(tokens, i):
    # "hay mucho venezolano", "mucho extranjero": mucho is a quantifier, so the ADJ is a noun
    if i == 0 or tokens[i - 1][0].lower() != "mucho" or tokens[i][0].lower() in comparatives:
        return False
    return tokens[i - 1][1] == "DET" or (i > 1 and tokens[i - 2][2] == "haber")


def _adverbial_primero(tokens, i):
    # "pues primero se enferma", "primero, ..." (first) vs "el primero", "lo primero que", "en primero" (grade)
    prev, nxt, nxt2 = _around(tokens, i)
    if prev[1] in ("DET", "ADP", "AUX", "NOUN", "PROPN") or prev[2] in predicative_lemmas or prev[0].lower() == "lo":
        return False
    # "primero y segundo de bachillerato"
    if nxt[0].lower() in ("y", "o") and nxt2[0].lower().startswith("segund"):
        return False
    return nxt[1] not in ("NOUN", "PROPN", "ADJ")


def _time_media(tokens, i):
    # "medio día", "media noche" (midday, midnight), "dos y media" (half past)
    prev, nxt, _ = _around(tokens, i)
    if nxt[0].lower() in ("día", "noche"):
        return True
    return (
        prev[0].lower() == "y"
        and i > 1
        and (tokens[i - 2][1] == "NUM" or tokens[i - 2][0].lower() in ("hora", "horas"))
    )


def _adverbial_total(tokens, i):
    # "total que volvimos", ", total es que", "bueno total" (anyway) vs "cambio total", "en total", "total caos"
    prev, nxt, _ = _around(tokens, i)
    return (prev[1] == "PUNCT" or prev[0].lower() in ("bueno", "que", "pues")) and (
        nxt[0].lower() in ("que", "es", "porque", "pero") or nxt[1] == "PUNCT"
    )


def _adverbial_seguro(tokens, i):
    # "seguro que sí", "pero seguro que" (surely) vs "estoy seguro que", "más seguro que este"
    prev, nxt, _ = _around(tokens, i)
    return nxt[0].lower() == "que" and not (
        prev[1] in ("AUX", "DET", "NOUN", "PROPN")
        or prev[2] in predicative_lemmas
        or prev[0].lower() in intensifier_list + ["tan", "más", "mas", "lo"]
    )


def _verb_vivo(tokens, i):
    # "yo vivo en", "no vivo", "vivo feliz" (I live) vs "está vivo", "muy vivo", "en vivo", "animal vivo", "llegó vivo"
    prev, nxt, _ = _around(tokens, i)
    if (
        prev[1] in ("DET", "AUX", "VERB")
        or prev[2] in predicative_lemmas
        or prev[0].lower() in intensifier_list + ["lo", "tan", "más", "en"]
    ):
        return False
    if prev[1] in ("NOUN", "PROPN", "NUM"):
        # "en mi trabajo vivo feliz"
        return nxt[1] in ("ADV", "ADJ") or nxt[0].lower() in ("en", "con", "de")
    return True


def correct_tokens(tokens):
    """correct_tokens fixes Stanza's closed list of systematic errors found by hand against TagAnt."""
    out = []
    for i, (text, upos, lemma) in enumerate(tokens):
        low = text.lower()
        after_int = i > 0 and tokens[i - 1][0].lower() in intensifier_list
        if after_int and low == "poco" and upos == "PRON":
            upos = "ADV"
        # "mucho solo" is quantifier + "only", not intensified "lonely"
        elif after_int and low == "solo" and upos == "ADV" and tokens[i - 1][0].lower() != "mucho":
            upos, lemma = "ADJ", "solo"
        elif upos == "ADJ" and (low == "san" or re.fullmatch(r"sant[oa]s?", low) and _holy_name(tokens, i)):
            upos = "PROPN"
        elif low in lateral_words and (low == "celca" or upos == "ADJ"):
            upos, lemma = lateral_words[low]
        elif upos == "ADJ" and low == "mismo" and i > 0 and tokens[i - 1][0].lower() in mismo_advs:
            upos = "ADV"
        elif upos == "ADJ" and i > 0 and (tokens[i - 1][0].lower(), low) in compound_nouns:
            upos = compound_nouns[(tokens[i - 1][0].lower(), low)]
        # "mi cuarto", "menos cuarto" (room, quarter hour) vs "cuarto piso"
        elif upos == "ADJ" and (
            low == "estrato" or low == "cuarto" and _around(tokens, i)[1][1] not in ("NOUN", "PROPN")
        ):
            upos = "NOUN"
        elif upos == "ADJ" and low == "primero" and _adverbial_primero(tokens, i):
            upos = "ADV"
        elif upos == "ADJ" and (
            (low in discourse_adjs and not after_int and _discourse_slot(tokens, i))
            or (low in discourse_adjs and _tag_question(tokens, i))
            or (low in ("claro", "cierto") and _discourse_tail(tokens, i))
        ):
            upos = "INTJ"
        elif upos == "ADJ" and low in ("mejor", "peor") and _adverbial_comparative(tokens, i):
            upos = "ADV"
        elif low == "dicho" and i > 0 and tokens[i - 1][0].lower() == "mejor":
            upos, lemma = "VERB", "decir"
        elif upos == "ADJ" and low == "igual" and _adverbial_igual(tokens, i):
            upos = "ADV"
        elif upos == "ADJ" and re.fullmatch(r"(pur|sol)[oa]s?", low) and _focus_quantifier(tokens, i):
            upos = "DET" if low.startswith("pur") else "ADV"
        elif upos == "ADJ" and low in possessives:
            upos = "DET"
        elif upos == "ADJ" and _quantified_noun(tokens, i):
            upos = "NOUN"
        elif upos == "ADJ" and low == "vivo" and _verb_vivo(tokens, i):
            upos, lemma = "VERB", "vivir"
        # "se le hecha", "le hechas una cucharada": misspelled echar
        elif (
            upos == "ADJ"
            and re.fullmatch(r"hech[oa]s?|hechan", low)
            and i > 0
            and tokens[i - 1][0].lower() in ("se", "le", "les", "me", "te", "nos")
        ):
            upos, lemma = "VERB", "echar"
        elif upos == "ADJ" and low == "debido" and _around(tokens, i)[1][0].lower() in ("a", "al"):
            upos = "ADP"
        elif upos == "ADJ" and low == "junto" and _around(tokens, i)[1][0].lower() in ("a", "al", "con", "de", "e"):
            upos = "ADV"
        elif upos == "ADJ" and low in ("medio", "media") and _time_media(tokens, i):
            upos = "NUM" if tokens[i - 1][0].lower() == "y" else "NOUN"
        elif upos == "ADJ" and (
            low == "total" and _adverbial_total(tokens, i) or low == "seguro" and _adverbial_seguro(tokens, i)
        ):
            upos = "ADV"
        elif upos in ("NOUN", "PROPN", "VERB") and low in dialect_adjs:
            upos, lemma = "ADJ", dialect_adjs[low]
        # muy only modifies a noun used as an adjective: "muy amigo", "muy niña", "muy trabajadores"
        elif upos == "NOUN" and i > 0 and tokens[i - 1][0].lower() == "muy" and len(low) > 3 and low not in muy_nouns:
            upos = "ADJ"
        elif upos == "ADJ" and re.search(r"(d|t|ch|s)[oa]s?$", low) and re.search(r"[aeií]r$", lemma):
            # participles get the verb as lemma (dado -> dar), but Lex_Adj wants the adjective
            lemma = re.sub(r"[oa]s?$", "o", low)
        elif upos == "ADJ" and re.search(r".{3}ao$", lemma):
            # dropped intervocalic d: "complicao", "pesao", "calmao"
            lemma = lemma[:-2] + "ado"
        out.append((text, upos, lemma_fixes.get(lemma, lemma)))
    return out


def correct_line(line):
    tokens = []
    for t in line.split():
        text, upos, lemma = t.split("_", 2)
        tokens.append((text, upos, lemma))
    return " ".join("_".join(t) for t in correct_tokens(tokens))


def correct_folder(input_folder, output_folder):
    # raw tagger output stays untouched so it can still be compared against TagAnt
    os.makedirs(output_folder, exist_ok=True)
    for name in sorted(os.listdir(input_folder)):
        if not name.endswith(".txt"):
            continue
        with open(os.path.join(input_folder, name), encoding="utf-8") as f:
            lines = [correct_line(line) for line in f.read().splitlines()]
        with open(os.path.join(output_folder, name), "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")


def chunk_sentence(tokens, size=80):
    # transcripts run on for thousands of tokens, and the parser is quadratic in sentence length
    clauses, current = [], []
    for t in tokens:
        current.append(t)
        if t[1] == "PUNCT":
            clauses.append(current)
            current = []
    if current:
        clauses.append(current)
    chunks, current = [], []
    for clause in clauses:
        if current and len(current) + len(clause) > size:
            chunks.append(current)
            current = []
        current += clause
        while len(current) > size:
            chunks.append(current[:size])
            current = current[size:]
    if current:
        chunks.append(current)
    return chunks


def read_corrected(path):
    with open(path, encoding="utf-8") as f:
        return [[tuple(t.split("_", 2)) for t in line.split()] for line in f if line.split()]


def to_conllu(doc):
    return "\n".join(
        "\n".join(
            "\t".join(
                [str(w.id), w.text, w.lemma, w.upos, w.xpos or "_", w.feats or "_", str(w.head), w.deprel, "_", "_"]
            )
            for w in s.words
        )
        + "\n"
        for s in doc.sentences
    )


def _init_parser():
    global _nlp
    import stanza
    import torch

    torch.set_num_threads(1)
    options = {"package": None, "download_method": None, "verbose": False}
    _nlp = (
        stanza.Pipeline("es", processors=parse_tagger, tokenize_pretokenized=True, **options),
        stanza.Pipeline("es", processors=parse_processors, depparse_pretagged=True, **options),
    )


def _parse_file(paths):
    src, dst = paths
    chunks = [c for s in read_corrected(src) for c in chunk_sentence(s)]
    tagger, parser = _nlp  # type: ignore
    doc = tagger([[t[0] for t in c] for c in chunks])
    for sent, chunk in zip(doc.sentences, chunks):
        assert [w.text for w in sent.words] == [t[0] for t in chunk], src
        # the parser needs xpos/feats from the tagger, but upos/lemma keep the correct_tokens fixes
        for w, (_, upos, lemma) in zip(sent.words, chunk):
            w.upos, w.lemma = upos, lemma
    doc = parser(doc)
    with open(dst + ".part", "w", encoding="utf-8") as f:
        f.write(to_conllu(doc))
    os.replace(dst + ".part", dst)
    return os.path.basename(src)


def parse_folder(input_folder, output_folder, workers):
    import stanza

    stanza.download("es", package=None, processors={**parse_tagger, **parse_processors}, verbose=False)
    os.makedirs(output_folder, exist_ok=True)
    for name in os.listdir(output_folder):
        if name.endswith(".part"):
            os.remove(os.path.join(output_folder, name))

    jobs = [
        (os.path.join(input_folder, name), os.path.join(output_folder, name[:-4] + ".conllu"))
        for name in sorted(os.listdir(input_folder))
        if name.endswith(".txt") and not os.path.exists(os.path.join(output_folder, name[:-4] + ".conllu"))
    ]
    print(f"Parsing {len(jobs)} files with stanza ({workers} workers)")
    with get_context("spawn").Pool(workers, initializer=_init_parser) as pool:
        for i, name in enumerate(pool.imap_unordered(_parse_file, jobs), 1):
            print(f"[{i}/{len(jobs)}] Parsed: {name}")


Dep = namedtuple("Dep", "id text upos lemma head deprel")
Relations = namedtuple("Relations", "adj_type noun verb inf_verb")


def read_conllu(path):
    sents, current = [], []
    with open(path, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                if current:
                    sents.append(current)
                current = []
                continue
            c = line.rstrip("\n").split("\t")
            current.append(Dep(int(c[0]), c[1], c[3], c[2], int(c[6]), c[7]))
    if current:
        sents.append(current)
    return sents


def _head(sent, w):
    return sent[w.head - 1] if w.head else None


def _children(sent, w, rel):
    return [c for c in sent if c.head == w.id and c.deprel.split(":")[0] == rel]


def _noun(words, near):
    # run-on chunks can give several subjects; the nearest one is the adjective's, even if a pronoun
    if not words:
        return "/"
    w = min(words, key=lambda w: abs(w.id - near.id))
    return w.text if w.upos in ("NOUN", "PROPN") else "/"


def governing_verb(sent, w):
    # nominal predicates head their clause in UD, so "es muy bonita" yields the copula
    x = w
    while x is not None:
        # w itself can be a parsed VERB that correct_tokens made an ADJ ("muy chéere")
        if x.upos == "VERB" and x is not w:
            return x
        cop = _children(sent, x, "cop")
        if cop:
            return cop[0]
        if x.upos == "AUX" and x is not w:
            return x
        x = _head(sent, x)
    return None


copular_verbs = {"ser", "estar", "parecer", "quedar", "sentir"}


def adjective_relation(sent, w):
    # "bonita y grande": the second conjunct shares the first one's relation; so do lists and
    # repeats the parser hangs as amod on the first adjective ("muy organizado muy bonito")
    while w.deprel in ("conj", "amod") and w.head and _head(sent, w).upos == "ADJ":
        w = _head(sent, w)
    head = _head(sent, w)
    rel = w.deprel.split(":")[0]
    # "mhm, muy joven": the parser takes a filler for the noun
    if head is not None and head.text.lower() in fillers:
        return "ambiguous", "/"
    if rel == "amod" and head is not None:
        return "attributive", _noun([head], w)
    if _children(sent, w, "cop"):
        return "predicative", _noun(_children(sent, w, "nsubj"), w)
    # "una cabuya atravesada en la calle": participle phrases after a noun
    if rel == "acl" and head is not None and head.upos in ("NOUN", "PROPN"):
        return "attributive", _noun([head], w)
    if rel == "xcomp" and head is not None:
        # "lo veo bonito" describes the object, "se puso feo" the subject
        return "predicative", _noun(_children(sent, head, "obj") or _children(sent, head, "nsubj"), w)
    # "es como difícil", "queda delicioso": the parse hangs the adjective off a copular verb instead of using cop
    if (
        head is not None
        and head.lemma in copular_verbs
        and rel in ("obj", "advcl", "advmod", "ccomp", "parataxis")
        and not _children(sent, w, "case")
    ):
        return "predicative", _noun(_children(sent, head, "nsubj"), w)
    return "ambiguous", "/"


def sentence_relations(sent):
    out = []
    for w in sent:
        # correct_tokens can turn a parsed NOUN or VERB into an ADJ after the parse was made
        if w.upos not in ("ADJ", "ADV", "NOUN", "PROPN", "VERB"):
            out.append(None)
            continue
        adj_type, noun = adjective_relation(sent, w) if w.upos != "ADV" else ("/", "/")
        verb = governing_verb(sent, w)
        out.append(Relations(adj_type, noun, verb.text if verb else "/", verb.lemma if verb else "/"))
    return out


def parse_relations(parsed_folder):
    def relations(filename):
        sents = read_conllu(os.path.join(parsed_folder, filename[:-4] + ".conllu"))
        return [r for s in sents for r in sentence_relations(s)]

    return relations


def _init_worker():
    global _nlp
    import stanza
    import torch

    # one thread per process; extra threads per process made pos 25x slower here
    torch.set_num_threads(1)
    _nlp = stanza.Pipeline("es", package=None, processors=processors, download_method=None, verbose=False)


def _tag_file(paths):
    src, dst = paths
    with open(src, encoding="utf-8") as f:
        paragraphs = [line.strip() for line in f if line.strip()]
    # blank-line paragraphs keep the tokenizer's input short, which is 10x faster than one blob
    text, added = join_paragraphs(paragraphs)
    doc = _nlp(text)  # type: ignore
    with open(dst + ".part", "w", encoding="utf-8") as f:
        f.write(tag_doc(doc, added) + "\n")
    os.replace(dst + ".part", dst)
    return os.path.basename(src)


def tag_folder(input_folder, output_folder, workers):
    import stanza

    stanza.download("es", package=None, processors=processors, verbose=False)
    os.makedirs(output_folder, exist_ok=True)
    for name in os.listdir(output_folder):
        if name.endswith(".part"):
            os.remove(os.path.join(output_folder, name))

    # files tagged by an earlier run are reused so an interrupted run picks up where it stopped
    jobs = [
        (os.path.join(input_folder, name), os.path.join(output_folder, name))
        for name in sorted(os.listdir(input_folder))
        if name.endswith(".txt") and not os.path.exists(os.path.join(output_folder, name))
    ]
    print(f"Tagging {len(jobs)} files with stanza ({workers} workers)")
    # spawn, since forking after the parent touched CUDA (stanza import on a GPU box) fails
    with get_context("spawn").Pool(workers, initializer=_init_worker) as pool:
        for i, name in enumerate(pool.imap_unordered(_tag_file, jobs), 1):
            print(f"[{i}/{len(jobs)}] Tagged: {name}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/text", help="folder of raw .txt transcripts")
    parser.add_argument("--tagged", default="data/stanza_tagged", help="where stanza output goes")
    parser.add_argument("--corrected", default="data/stanza_corrected", help="tags after correct_tokens")
    parser.add_argument("--parsed", default="data/stanza_parsed", help="dependency parse of the corrected tags")
    parser.add_argument("--speakers", default=speaker_data, help="speaker metadata sheet, one row per Speaker")
    parser.add_argument(
        "--drop-invariant", action="store_true", help="drop every row of a host that is never intensified"
    )
    parser.add_argument("--workers", type=int, default=min(4, os.cpu_count() or 1))
    args = parser.parse_args()

    tag_folder(args.input, args.tagged, args.workers)
    correct_folder(args.tagged, args.corrected)
    parse_folder(args.corrected, args.parsed, args.workers)

    os.makedirs("output", exist_ok=True)
    output = "output/intensifier_data_stanza_" + date.today().isoformat() + ".csv"
    # Adj_type, Noun and Verb come from the dependency parse instead of word order
    # stanza tags come from clean_transcripts' cleaned text, and their lines are sentences, not transcript turns
    df = analyze(
        args.corrected, output, parse_relations(args.parsed), clean_turns=False, drop_invariant=args.drop_invariant
    )
    write_outputs(df, output, args.speakers)

    print("Make sure to manually check the -ísimo cases!")
