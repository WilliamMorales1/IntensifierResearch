# tags the cleaned transcripts with stanza, corrects and parses the tags, then extracts host rows with extract

import argparse
import os
import re
from collections import namedtuple
from datetime import date
from multiprocessing import get_context

import dialects as dialect_rules
from extract import (
    analyze,
    intensifier_list,
    negators,
    speaker_data,
    write_outputs,
)

# stanza's default_accurate: transformer (BERTIN RoBERTa) pos and depparse; tokenize and lemma have no
# transformer model for Spanish. Needs a GPU (Colab); on this laptop's CPU it takes days
processors = {
    "tokenize": "combined_charlm",
    "mwt": "combined",
    "pos": "combined_bertin-roberta",
    "lemma": "combined_charlm",
}
# the parse reruns the tagger on stanza_corrected words only for xpos/feats
parse_tagger = {"tokenize": "combined_charlm", "pos": "combined_bertin-roberta"}
parse_processors = {"depparse": "combined_bertin-roberta"}
# what the bertin-roberta pos and depparse models load from the HF hub
bert_model = "bertin-project/bertin-roberta-base-spanish"

# plural -es stripped one letter too far (chéveres -> chéver)
lemma_fixes = {"chéver": "chévere", "chever": "chévere", "chevere": "chévere", "gritono": "gritón"}

_nlp = None
_init_error = None


def clean_field(text):
    # spaces and underscores would break the word_POS_lemma format extract parses
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
# -ísimo forms that are adverbs (lejísimos, muchísimo); the tagger calls jugosísimo, jartísimo ADV too
isimo_adverbs = re.compile(r"(much|ch|tant|h?art|lej|tard|cerqu|rapid|tempran|pront|poquit)ísim[oa]s?")
# real -ono adjectives; other -ono lemmas of -ona words are -ón ones the lemmatizer misread (mamona, cansonas)
ono_adjs = {"mono", "nono", "monótono", "autóctono"}
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
    ("ciclo", "vía"): "NOUN",
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


def _place_name(tokens, i):
    # "barrio Villa Nueva", "el Nuevo Bosque", "nueva york"; all-caps words are shouted, not names
    text = tokens[i][0]
    if text.lower() == "nueva" and _around(tokens, i)[1][0].lower() == "york":
        return True
    return text[:1].isupper() and not text.isupper() and i > 0 and tokens[i - 1][1] != "PUNCT"


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


def _interjection(tokens, i, upos, after_int):
    low = tokens[i][0].lower()
    # laughter "jajaja", "jejeje", which the transformer tagger calls ADV
    if re.fullmatch(r"(j[aeiu])+j?", low):
        return True
    # the transformer tagger calls discourse bueno/claro ADV; only claro is also a real adverb ("habla claro")
    if upos not in ("ADJ", "ADV") or low not in discourse_adjs:
        return False
    if upos == "ADV" and low != "claro":
        return True
    return (
        (not after_int and _discourse_slot(tokens, i))
        or _tag_question(tokens, i)
        or (low in ("claro", "cierto") and _discourse_tail(tokens, i))
    )


def _focus_quantifier(tokens, i):
    # "puro barro", "solo pescado frito" (nothing but, only) vs "aire puro", "una sola casa", "muy solo"
    prev, nxt, _ = _around(tokens, i)
    return nxt[1] == "NOUN" and prev[1] not in ("DET", "ADJ", "NUM") and prev[0].lower() not in intensifier_list


def _quantified_noun(tokens, i):
    # "hay mucho venezolano", "pasa mucho vicioso", ", mucho corrupto": mucho is a quantifier, so the ADJ is a noun;
    # "era mucho chusco", "se han puesto mucho malos" keep the dialectal intensifier after a copula
    if i == 0 or tokens[i - 1][0].lower() != "mucho" or tokens[i][0].lower() in comparatives:
        return False
    if tokens[i - 1][1] == "DET" or (i > 1 and tokens[i - 2][2] == "haber"):
        return True
    before = tokens[i - 2] if i > 1 else _edge
    return (
        re.search(r"[^as]$", tokens[i][0].lower()) is not None
        and before[1] != "AUX"
        and before[2] not in copular_verbs | {"poner", "volver", "seguir"}
        and before[0].lower() != "mucho"
    )


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


def correct_tokens(tokens, dialects=()):
    """correct_tokens fixes Stanza's closed list of systematic errors, each found and checked by hand; dialects adds the rules of those dialect modules."""
    out = []
    for i, (text, upos, lemma) in enumerate(tokens):
        low = text.lower()
        after_int = i > 0 and tokens[i - 1][0].lower() in intensifier_list
        fixed = next((f for d in dialects if (f := d.correct(tokens, i, upos, lemma))), None)
        if fixed:
            upos, lemma = fixed
        elif after_int and low == "poco" and upos == "PRON":
            upos = "ADV"
        # "mucho solo" is quantifier + "only", not intensified "lonely"
        elif after_int and low == "solo" and upos == "ADV" and tokens[i - 1][0].lower() != "mucho":
            upos, lemma = "ADJ", "solo"
        elif upos == "ADJ" and (
            low == "san" or re.fullmatch(r"sant[oa]s?", low) and _holy_name(tokens, i) or _place_name(tokens, i)
        ):
            upos = "PROPN"
        # "digámoslo", "respétala", "tómenlo": imperatives with enclitic pronouns
        elif upos == "ADJ" and re.fullmatch(
            r"[a-zñü]+[áéíóú][a-zñü]*(n|mos|[ae])(me|te|se|nos)?(lo|la|los|las|le|les)", low
        ):
            upos = "VERB"
        elif upos == "ADJ" and low == "menudo" and i > 0 and tokens[i - 1][0].lower() == "a":
            upos = "ADV"
        elif upos == "ADJ" and low == "entendido" and i > 0 and tokens[i - 1][2] == "tener":
            upos, lemma = "VERB", "entender"
        # vocative "el avión hermano, con problemas" (bro)
        elif upos == "ADJ" and re.fullmatch(r"herman[oa]s?", low):
            upos = "NOUN"
        elif (
            upos == "ADJ"
            and low == "regular"
            and i > 1
            and tokens[i - 1][0].lower() == "lo"
            and tokens[i - 2][0].lower() == "por"
        ):
            upos = "ADV"
        # "yo saludo a mi novia"
        elif upos == "ADJ" and low == "saludo":
            upos, lemma = "VERB", "saludar"
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
        elif _interjection(tokens, i, upos, after_int):
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
        # muy only modifies a noun used as an adjective: "muy amigo", "muy niña", "muy trabajadores"
        elif upos == "NOUN" and i > 0 and tokens[i - 1][0].lower() == "muy" and len(low) > 3 and low not in muy_nouns:
            upos = "ADJ"
        elif upos == "ADJ" and re.search(r"(d|t|ch|s)[oa]s?$", low) and re.search(r"[aeií]r$", lemma):
            # participles get the verb as lemma (dado -> dar), but Lex_Adj wants the adjective
            lemma = re.sub(r"[oa]s?$", "o", low)
        elif upos == "ADV" and re.fullmatch(r".+ísim[oa]s?", low) and not isimo_adverbs.fullmatch(low):
            upos, lemma = "ADJ", re.sub(r"[oa]s?$", "o", low)
        elif (
            upos == "ADJ"
            and re.fullmatch(r".+onas?", low)
            and not low.endswith(("ciona", "cionas"))
            and re.fullmatch(r".+on[o]?", lemma)
            and lemma not in ono_adjs
        ):
            lemma = re.sub(r"ono?$", "ón", lemma)
        lemma = lemma_fixes.get(lemma, lemma)
        for d in dialects:
            lemma = d.fix_lemma(upos, lemma)
        out.append((text, upos, lemma))
    return out


def correct_line(line, dialects=()):
    tokens = []
    for t in line.split():
        text, upos, lemma = t.split("_", 2)
        tokens.append((text, upos, lemma))
    return " ".join("_".join(t) for t in correct_tokens(tokens, dialects))


def correct_folder(input_folder, output_folder, dialects=()):
    # raw tagger output stays untouched so rules can be rechecked against it
    os.makedirs(output_folder, exist_ok=True)
    for name in sorted(os.listdir(input_folder)):
        if not name.endswith(".txt"):
            continue
        with open(os.path.join(input_folder, name), encoding="utf-8") as f:
            lines = [correct_line(line, dialects) for line in f.read().splitlines()]
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


def _fetch_models(stanza_processors):
    import stanza
    from transformers import AutoModel, AutoTokenizer

    stanza.download("es", package=None, processors=stanza_processors, verbose=False)
    # a failed hub fetch inside a spawn worker kills the initializer, and the Pool respawns it forever
    AutoTokenizer.from_pretrained(bert_model)
    AutoModel.from_pretrained(bert_model)


def _start_pool(workers, initializer):
    # spawned workers inherit the env; torch and BLAS read it at import, before set_num_threads runs
    os.environ.setdefault("OMP_NUM_THREADS", "1")
    # spawn, since forking after the parent touched CUDA (stanza import on a GPU box) fails
    return get_context("spawn").Pool(workers, initializer=_guarded_init, initargs=(initializer,))


def _guarded_init(load):
    # an initializer that raises makes the Pool respawn the worker forever; the first task re-raises instead
    global _init_error
    try:
        load()
    except Exception as e:  # noqa: BLE001 - any load failure must reach the parent
        _init_error = e


def _check_init():
    if _init_error is not None:
        raise RuntimeError("stanza worker failed to load") from _init_error


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


def parse_stale(src, dst):
    """parse_stale tells whether dst is missing or no longer matches the words, upos and lemmas of src."""
    if not os.path.exists(dst):
        return True
    tags = [t for s in read_corrected(src) for t in s]
    parsed = [(w.text, w.upos, w.lemma) for s in read_conllu(dst) for w in s]
    return tags != parsed


def _parse_file(paths):
    _check_init()
    src, dst = paths
    chunks = [c for s in read_corrected(src) for c in chunk_sentence(s)]
    # an interview shorter than the skipped opening has no text left, and Stanza returns a bare list for no input
    if not chunks:
        open(dst, "w", encoding="utf-8").close()
        return os.path.basename(src)
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
    os.makedirs(output_folder, exist_ok=True)
    for name in os.listdir(output_folder):
        if name.endswith(".part"):
            os.remove(os.path.join(output_folder, name))

    # a parse made from older corrected tags is redone, so changing correct_tokens needs no manual cleanup
    pairs = [
        (os.path.join(input_folder, name), os.path.join(output_folder, name[:-4] + ".conllu"))
        for name in sorted(os.listdir(input_folder))
        if name.endswith(".txt")
    ]
    jobs = [(src, dst) for src, dst in pairs if parse_stale(src, dst)]
    stale = sum(os.path.exists(dst) for _, dst in jobs)
    print(f"Parsing {len(jobs)} files with stanza ({stale} outdated, {workers} workers)")
    if not jobs:
        return
    _fetch_models({**parse_tagger, **parse_processors})
    with _start_pool(workers, _init_parser) as pool:
        for i, name in enumerate(pool.imap_unordered(_parse_file, jobs), 1):
            print(f"[{i}/{len(jobs)}] Parsed: {name}")


Dep = namedtuple("Dep", "id text upos lemma head deprel")
Relations = namedtuple("Relations", "adj_type noun verb inf_verb negation verbal_int")


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


def _clause(sent, w):
    # no muy bueno: the parser can hang the negator on the intensifier
    ids = {c.id for c in _children(sent, w, "advmod")}
    x = w
    while x is not None:
        ids.add(x.id)
        # the first verb or predicate up the chain closes the clause
        if (x is not w and x.upos in ("VERB", "AUX")) or _children(sent, x, "cop"):
            break
        x = _head(sent, x)
    return ids


def _infinitive(sent, w):
    return any(x.text.lower() == x.lemma for x in [w, *_children(sent, w, "cop")] if x.upos in ("VERB", "AUX"))


def _negates(sent, neg, clause):
    # preverbal no sits right before its verb, clitics, copula or intensifier; discourse no
    # (no , muy buena ; no la gente es muy buena ; no sé ellos fueron bien abiertos) does not
    k = neg.id
    while k < len(sent) and sent[k].text.lower() in clitics:
        k += 1
    if k >= len(sent):
        return False
    t = sent[k]
    # no una casa tan grande, no en ese nivel tan extremo: constituent negation of the host's phrase
    if t.head in clause and t.deprel.split(":")[0] in ("cop", "aux", "advmod", "det", "case"):
        return True
    # no se tenga que desplazar tan lejos, no tiene que estar tan preocupada: t governs the clause's infinitive
    if t.upos in ("VERB", "AUX") and any(sent[c - 1].head == t.id and _infinitive(sent, sent[c - 1]) for c in clause):
        return True
    # ni tan aficionado: the parser fixes tan to ni
    return t.id in clause or (t.head == neg.id and t.deprel == "fixed")


def negation(sent, w):
    """negation returns the negator before w in its clause (no es tan bueno, no me parece muy bonito), or "/"."""
    clause = _clause(sent, w)
    for c in reversed(sent[: w.id - 1]):
        if c.head in clause and c.text.lower() in negators and _negates(sent, c, clause):
            return c.text.lower()
    return "/"


def verbal_intensifier(sent, w):
    """verbal_intensifier tells whether the word before w hangs on a verb, not on w (se cansara mucho acostada)."""
    if w.id < 2:
        return False
    head = _head(sent, sent[w.id - 2])
    if head is None or head is w or head.upos not in ("VERB", "AUX"):
        return False
    # quede bien limpiecita: before a predicative adjective the adverb grades the adjective
    return not (w.upos == "ADJ" and head.lemma in copular_verbs)


def sentence_relations(sent):
    out = []
    for w in sent:
        # correct_tokens can turn a parsed NOUN or VERB into an ADJ after the parse was made
        if w.upos not in ("ADJ", "ADV", "NOUN", "PROPN", "VERB"):
            out.append(None)
            continue
        # ADV too, since correct_tokens can make a parsed ADV an ADJ ("muy chevre", "jugosísimo")
        adj_type, noun = adjective_relation(sent, w)
        verb = governing_verb(sent, w)
        out.append(
            Relations(
                adj_type,
                noun,
                verb.text if verb else "/",
                verb.lemma if verb else "/",
                negation(sent, w),
                verbal_intensifier(sent, w),
            )
        )
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
    _check_init()
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
    # the pool initializer loads the models even with nothing to do
    if not jobs:
        return
    _fetch_models(processors)
    with _start_pool(workers, _init_worker) as pool:
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
        "--output",
        default="output/intensifier_data_stanza_" + date.today().isoformat(),
        help="output path without extension",
    )
    parser.add_argument(
        "--drop-invariant", action="store_true", help="drop every row of a host that is never intensified"
    )
    parser.add_argument("--xlsx", action="store_true", help="also write the table as xlsx")
    parser.add_argument("--csv", action="store_true", help="also write the table as csv")
    parser.add_argument(
        "--dialect",
        action="append",
        default=[],
        choices=sorted(dialect_rules.available),
        help="also apply this dialect's tag corrections (repeatable; the corpus needs pr and co)",
    )
    parser.add_argument("--workers", type=int, default=min(4, os.cpu_count() or 1))
    args = parser.parse_args()

    tag_folder(args.input, args.tagged, args.workers)
    correct_folder(args.tagged, args.corrected, dialect_rules.load(args.dialect))
    parse_folder(args.corrected, args.parsed, args.workers)

    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    # Adj_type, Noun and Verb come from the dependency parse instead of word order
    df = analyze(args.corrected, None, parse_relations(args.parsed), drop_invariant=args.drop_invariant)
    write_outputs(df, args.output, args.speakers, xlsx=args.xlsx, csv=args.csv)

    print("Make sure to manually check the -ísimo cases!")
