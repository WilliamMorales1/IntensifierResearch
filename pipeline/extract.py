# host extraction from Stanza's corrected word_UPOS_lemma tags: intensifier + adjective/adverb rows

import bisect
import os
import re
import sqlite3
from collections import Counter

import pandas as pd

from dialects.pr import delateralize

speaker_data = "data/speaker_data_ALL_2026-3-12.xlsx"
re_words = "output/re-words.txt"

intensifier_list = [
    "absolutamente",
    "bastante",
    "casi",
    "completamente",
    "demasiado",
    "estrictamente",
    "especialmente",
    "extremadamente",
    "harto",
    "increíblemente",
    "mucho",
    "muy",
    "plenamente",
    "realmente",
    "sumamente",
    "súper",
    "totalmente",
    "verdaderamente",
    "bien",
    "super",
    "supel",
    "re",
    "archi",
]

# Quirk et al. (1985:589-590) scale as operationalized by Stratton & Sundquist (2022:388-389): amplifiers are
# maximizers or boosters, downtoners approximators, compromisers, diminishers or minimizers; emphasizers are not
# scalar and do not count as intensification (Stratton & Sundquist 2022:395)
int_types = {
    "absolutamente": "maximizer",
    "completamente": "maximizer",
    "totalmente": "maximizer",
    "plenamente": "maximizer",
    "extremadamente": "maximizer",
    "sumamente": "maximizer",
    "muy": "booster",
    "bien": "booster",
    "mucho": "booster",
    "harto": "booster",
    "bastante": "booster",
    "demasiado": "booster",
    "súper": "booster",
    "re": "booster",
    "realmente": "booster",
    "verdaderamente": "booster",
    "increíblemente": "booster",
    "tan": "booster",
    "más": "booster",
    "-ísimo": "booster",
    "archi-": "booster",
    "casi": "approximator",
    "más o menos": "compromiser",
    "especialmente": "emphasizer",
    "estrictamente": "emphasizer",
}

# degree words that only intensify in some constructions (see degree_types); never hosts themselves
degree_words = {"tan", "más", "mas", "menos"}

# comparative hosts (Stratton & Sundquist 2022:395); muy mayor (= elderly) is a positive degree, so mayor/menor stay when intensified
comparatives = {"mejor", "peor"}
comparatives_bare = {"mayor", "menor"}

apocope_dict = {
    "gran": "grande",
    "buen": "bueno",
    "cien": "ciento",
    "cualquier": "cualquiero",
    "cualesquier": "cualesquiero",
    "algún": "alguno",
    "mal": "malo",
    "ningún": "ninguno",
    "primer": "primero",
    "tercer": "tercero",
    "un": "uno",
}

# adjectives in -a with no -o form; -ista/-ísta and -crata are caught by suffix
invariant_a = {
    "agrícola", "azteca", "belga", "cosmopolita", "déspota", "extra", "hincha", "hipócrita", "homicida", "idiota",
    "indígena", "inca", "israelita", "lila", "maya", "naranja", "paisa", "patriota", "persa", "pirata", "plaga", "rosa",
    "suicida", "violeta",
}  # fmt: skip

# fixed expressions without variation (*muy mejor is impossible, so mucho there is a quantifier)
fixed_expressions = {
    ("bien", "hecho"),
    ("mucho", "más"),
    ("mucho", "mas"),
    ("mucho", "menos"),
    ("mucho", "mejor"),
    ("mucho", "peor"),
    ("mucho", "mayor"),
    ("mucho", "menor"),
}

# adverbs that can't be graded, so a preceding "intensifier" is a quantifier, approximator or another adverb
non_gradable = {
    "más",
    "mas",
    "menos",
    "antes",
    "después",
    "siempre",
    "nunca",
    "jamás",
    "también",
    "tampoco",
    "ya",
    "entonces",
    "entoes",
    "donde",
    "dónde",
    "adonde",
    "todavía",
    "aún",
    "ahora",
    "ahorita",
    "luego",
    "anoche",
    "acerca",
    "primero",
    "solo",
    "sólo",
    "solamente",
    "además",
    "tan",
    "obviamente",
    "afortunadamente",
    "desafortunadamente",
    "probablemente",
    "posiblemente",
    "seguramente",
    "últimamente",
    "actualmente",
    "anteriormente",
    "prácticamente",
    "simplemente",
    "económicamente",
    # discourse and function words the taggers call ADV ("muy digamos", "bien hasta con", "casi toos los días")
    "digamos",
    "hasta",
    "tanto",
    "igual",
    "como",
    "cuando",
    "sino",
    "toos",
}

# endings that turn a host into a fuller form of the same word rather than completing a cut-off one
inflection = re.compile(r"(e?s|[oa]s?|mente|(uc|it|ic|ísim)[oa]s?)")


def is_well_formed(word):
    return bool(any(word.endswith(c) for c in "oaeslndr") and re.match(r"^[a-zA-Z_áéíóúüñÁÉÍÓÚÜÑí]+$", word))


def is_adj(word):
    adj_match = re.search(r"^(.*)_ADJ_", word)
    lex_adj_match = re.search(r"_ADJ_(.+)", word)
    return bool(adj_match and lex_adj_match and is_well_formed(word) and not word.endswith("mente"))


def log_re_word(word):
    os.makedirs(os.path.dirname(re_words), exist_ok=True)
    with open(re_words, "a", encoding="utf-8") as f:
        f.write(word + "\n")


def deaccent(word):
    return word.translate(str.maketrans("áéíóú", "aeiou"))


def get_adj(word):
    adj_match = re.search(r"^(.*)_ADJ_", word)
    adv_match = re.search(r"_ADJ_(.+)", word)

    adjective = adj_match.group(1)  # type: ignore
    lex_adjective = adv_match.group(1)  # type: ignore

    lex_adjective = lex_adjective.lower()
    # apocope corrections
    if lex_adjective in apocope_dict:
        lex_adjective = apocope_dict[lex_adjective]
    # only plural endings lose the -s; gris, gratis, francés are singular
    if re.search(r"[aeo]s$", lex_adjective) and lex_adjective != "lejos":
        lex_adjective = lex_adjective[:-1]
    # the lemmatizer sometimes keeps the feminine (soltera, pequeñita), and -dora/-tora/-sora come from masculine -or
    if re.search(r"[dts]ora$", lex_adjective):
        lex_adjective = lex_adjective[:-1]
    elif lex_adjective.endswith("a") and not (
        lex_adjective in invariant_a or re.search(r"([ií]sta|crata)$", lex_adjective)
    ):
        lex_adjective = lex_adjective[:-1] + "o"

    # write re adjectives that could be with the re- intensifier
    if adjective.startswith("re"):
        log_re_word(adjective)

    return adjective.lower(), lex_adjective.lower()


def is_adv(word):
    adv_match = re.search(r"^(.*)_ADV_", word)
    if adv_match and is_well_formed(word):
        adverb = adv_match.group(1).lower()
        return adverb not in intensifier_list and adverb not in degree_words and adverb != "no"
    return False


def get_adv(word):
    adv_match = re.search(r"^(.*)_ADV_(.*)", word)
    adverb, lemma = adv_match.group(1), adv_match.group(2)  # type: ignore
    if adverb.startswith("re"):
        log_re_word(adverb)
    # lemma set by the pr dialect rules (celca -> cerca, talde -> tarde)
    if lemma.lower() != adverb.lower() and delateralize(adverb.lower()) == lemma.lower():
        return lemma.lower()
    return adverb.lower()


# adverbs whose base does not end in -o
isimo_adv_base = {"lej": "lejos", "tard": "tarde", "cerc": "cerca"}


def strip_isimo_adv(adverb):
    """strip_isimo_adv returns the base of an -ísimo adverb (lejísimos -> lejos), or None."""
    match = re.fullmatch(r"(.+?)(qu|gu)?ísim[oa]s?", adverb)
    if not match:
        return None
    stem = match.group(1) + {"qu": "c", "gu": "g"}.get(match.group(2) or "", "")
    return isimo_adv_base.get(stem, stem + "o")


def is_fragment(words, i):
    """is_fragment reports whether words[i] is a cut-off word the speaker restarts, like "bue" in "muy bue muy bueno"."""
    host = words[i].split("_")[0].lower()
    if len(host) <= 2:
        return host not in ("ya", "sí", "ni")
    # cut-off bueno, bien, todo, nunca, often with the restart outside the segment
    if host in ("bue", "bie", "tod", "nun"):
        return True
    if len(host) > 6:
        return False
    for j in range(i + 1, min(i + 5, len(words))):
        later = words[j].split("_")[0].lower()
        if later.startswith(host) and not inflection.fullmatch(later[len(host) :]):
            # longer hosts are often real words ("cerca ... cercanías"), so need a restarted intensifier
            return later != host and (len(host) <= 4 or is_int(words[j - 1]))
    return False


def is_int(word):
    int_match = re.search(r"^(.*?)_", word)
    return bool(int_match and int_match.group(1) in intensifier_list)


def get_int(word):
    int_match = re.search(r"^(.*?)_", word)
    intensifier = int_match.group(1)  # type: ignore
    if intensifier == "super" or intensifier == "supel":
        intensifier = "súper"
    if intensifier.lower() == "mas":
        intensifier = "más"
    return intensifier.lower()


def _text(word):
    return word.split("_")[0].lower()


def _upos(word):
    parts = word.split("_")
    return parts[1] if len(parts) == 3 else ""


def _degree_type(words, i):
    # i is tan/más/menos; words[i + 1] the host
    word = _text(words[i])
    host = _text(words[i + 1])
    j = i
    while j > 0 and _text(words[j - 1]) == word:  # tan tan bonito
        j -= 1
    prev = _text(words[j - 1]) if j > 0 else ""

    if word == "tan":
        if host in ("solo", "sólo", "pronto", "siquiera"):
            return "fixed"
        # no sé qué tan grande (= how big), like Norwegian hvor gammel (Stratton & Sundquist 2022:395);
        # clause-initial ¡ay, qué tan lindo! is exclamative
        if prev in ("qué", "que", "cuán", "cuan") and j > 1 and _upos(words[j - 2]) not in ("PUNCT", "INTJ"):
            return "interrogative"
        k = i + 2
        while k < len(words) and _upos(words[k]) == "PUNCT" and k < i + 4:
            k += 1
        nxt = _text(words[k]) if k < len(words) else ""
        after = _text(words[k + 1]) if k + 1 < len(words) else ""
        if nxt == "como" and after == "para":
            return "result"
        # como que is a filler (tan bonito como que ...)
        if nxt == "como" and after != "que":
            return "equality"
        # relative que is PRON (el dolor tan grande que uno tiene); ¡qué profesor tan malo!, que ... is no result
        exclamative = any(_text(w) == "qué" for w in words[max(0, j - 3) : j])
        if nxt == "que" and _upos(words[k]) == "SCONJ" and not exclamative:
            return "result"
        return "intensifier"

    # más o menos bueno: a compromiser, like Norwegian mer eller mindre (Stratton & Sundquist 2022:391)
    if word == "menos" and j > 1 and prev == "o" and _text(words[j - 2]) in ("más", "mas"):
        return "intensifier"
    # por lo menos, a lo menos (= at least) focus the host without grading it
    if word == "menos" and prev == "lo" and j > 1 and _text(words[j - 2]) in ("por", "a", "al"):
        return "focus"
    # ¡qué casa más bonita!: the only intensifying más; everything else compares
    if word in ("más", "mas") and _upos(words[i + 1]) == "ADJ":
        k = j - 1
        while k >= 0 and _upos(words[k]) in ("NOUN", "ADJ", "DET") and _text(words[k]) != "qué":
            k -= 1
        noun = any(_upos(words[m]) == "NOUN" for m in range(k + 1, j))
        if noun and k >= 0 and _text(words[k]) == "qué":
            return "intensifier"
    if prev in definite or (j > 1 and _upos(words[j - 1]) == "NOUN" and _text(words[j - 2]) in definite):
        return "superlative"
    return "comparative"


# el más bonito, la casa más bonita, mi hijo más chiquito; una vida más ordenada compares
definite = {
    "el",
    "la",
    "los",
    "las",
    "lo",
    "del",
    "al",
    "mi",
    "mis",
    "tu",
    "tus",
    "su",
    "sus",
    "nuestro",
    "nuestra",
    "nuestros",
    "nuestras",
}


def degree_types(words):
    """degree_types labels each tan/más/menos before a host: intensifier, focus, comparative, superlative, equality, result, interrogative or fixed."""
    out = [None] * len(words)
    for i in range(len(words) - 1):
        if _text(words[i]) in degree_words and _upos(words[i + 1]) in ("ADJ", "ADV"):
            out[i] = _degree_type(words, i)
    return out


def _is_degree_int(words, k, degree):
    return k >= 0 and _text(words[k]) in degree_words and degree[k] == "intensifier"


def is_mas_bien(words, i):
    # "más bien" means "rather", so bien there is not an intensifier
    return (
        i > 1 and words[i - 1].split("_")[0].lower() == "bien" and words[i - 2].split("_")[0].lower() in ("más", "mas")
    )


# negators marked in Negation instead of dropped, unlike Stratton & Sundquist (2022:395)
negators = {"no", "nunca", "jamás", "tampoco", "ni"}


def get_negation(words, i, relations):
    """get_negation returns the negator scoping over the host at i (no es tan bueno, no muy bueno), or "/"."""
    before = [_text(w) for w in words[:i]]
    if relations is not None:
        # the parse can reach past the segment, so the negator must come before the host in Phr
        return relations.negation if relations.negation in before else "/"
    # no parse (tests): any negator earlier in the segment
    found = [w for w in before if w in negators]
    return found[-1] if found else "/"


def add_verb(row_data, relations, words):
    # like Noun, the verb must be visible in Phr; the parse can reach past the segment
    visible = relations is not None and relations.verb.lower() in (w.split("_")[0].lower() for w in words)
    row_data["Verb"] = relations.verb if visible else "/"
    row_data["Inf_Verb"] = relations.inf_verb if visible else "/"


# words the tagger calls ADJ, NOUN, VERB or PRON that are always adverbs ("queda súper cerquita")
always_adverbs = {"ahorita", "ahoritica", "cerquita"}
# the tagger calls lejísimos ADJ
isimo_adverb = re.compile(r"(lej|tard|cerqu)ísim[oa]s?")


def retag(words):
    """retag fixes host tags the tagger gets wrong: ahorita/lejísimos ADV, poquito ADV or DET."""
    out = []
    for i, word in enumerate(words):
        parts = word.split("_")
        if len(parts) == 3:
            text, pos, lemma = parts
            low = text.lower()
            if (low in always_adverbs or isimo_adverb.fullmatch(low)) and pos != "ADV":
                pos = "ADV"
            elif re.fullmatch(r"poquit[oa]s?", low) and pos in ("ADJ", "NOUN"):
                before = words[i - 1].split("_") if i > 0 else []
                after = words[i + 1].split("_") if i + 1 < len(words) else []
                # muy poquito, como poquito: like muy poco; un poquito de stays NOUN;
                # muy poquitas veces, muy poquito tiempo are quantifiers like muy pocas veces
                quantifier = low != "poquito" or (len(after) == 3 and after[1] in ("NOUN", "PROPN"))
                if before and (is_int(words[i - 1]) or before[1] in ("VERB", "AUX")) and not quantifier:
                    pos = "ADV"
                elif pos == "ADJ":
                    pos = "DET"
            word = f"{text}_{pos}_{lemma}"
        out.append(word)
    return out


def _modifier(words, i, degree):
    # (Int, Double) for the host at i, or None when the row leaves the envelope of variation
    k = i - 1
    if k < 0:
        return "/", "/"
    if _text(words[k]) in degree_words and degree[k] is not None:
        if degree[k] == "focus":
            return "/", "/"
        if degree[k] != "intensifier":
            return None
        if _text(words[k]) == "menos":
            return "más o menos", "/"
    elif not is_int(words[k]) or is_mas_bien(words, i):
        return "/", "/"
    double = "/"
    if k > 0 and (is_int(words[k - 1]) or _is_degree_int(words, k - 1, degree)):
        double = get_int(words[k - 1])
    return get_int(words[k]), double


def process_segment(segment, speaker, parse=None, degree=None):
    """process_segment extracts host rows; parse and degree, when given, hold a Relations and a degree_types label per word."""
    rows = []

    intensifier = None
    adjective = None
    lex_adjective = None
    attributive = None
    noun = None
    double = None

    words = retag(segment.split())
    if degree is None:
        degree = degree_types(words)

    # Process each word in the segment
    for i, word in enumerate(words):
        # bueno
        if is_adj(word) and not is_fragment(words, i):
            adjective, lex_adjective = get_adj(word)

            attributive, noun = "ambiguous", "/"
            if parse and parse[i]:
                attributive, noun = parse[i].adj_type, parse[i].noun
                # the parse spans past the segment, but the noun must be visible in Phr
                if noun != "/" and noun.lower() not in (w.split("_")[0].lower() for w in words):
                    noun = "/"
                    if attributive == "attributive":
                        attributive = "ambiguous"
            if not re.match(r"^[a-zA-Z_áéíóúüñÁÉÍÓÚÜÑ/]+$", noun):
                attributive = "ambiguous"
                noun = "/"

            # muy bueno, muy muy bueno; None for no muy bueno, más bueno que
            modifier = _modifier(words, i, degree)
            if modifier is None:
                continue
            intensifier, double = modifier
            if (intensifier, lex_adjective) in fixed_expressions or lex_adjective in comparatives:
                continue
            if lex_adjective in comparatives_bare and intensifier == "/":
                continue

            if lex_adjective.endswith("ísimo"):
                intensifier = "-ísimo"
                adjective = adjective.replace("quísim", "c")
                lex_adjective = lex_adjective.replace("quísim", "c")
                adjective = adjective.replace("guísim", "g")
                lex_adjective = lex_adjective.replace("guísim", "g")
                adjective = adjective.replace("ísim", "")
                lex_adjective = lex_adjective.replace("ísim", "")

            if lex_adjective.startswith("archi"):
                intensifier = "archi-"
                adjective = adjective.replace("archi", "")
                lex_adjective = lex_adjective.replace("archi", "")

            # FRASE
            phrase_tagged = " ".join(words)
            phrase = " ".join(re.sub(r"_.*", "", word) for word in words)

            row_data = {
                "Speaker": speaker,
                "Phr_tagged": phrase_tagged,
                "Phr": phrase,
                "Double": double,
                "Int": intensifier,
                "Int_type": int_types.get(intensifier, "/"),
                "Adv": "/",
                "Adj": adjective,
                "Lex_Adj": lex_adjective,
                "Adj_type": attributive,
                "Noun": noun.lower(),
                "Negation": get_negation(words, i, parse[i] if parse else None),
            }
            add_verb(row_data, parse[i] if parse else None, words)
            rows.append(row_data)

        # IF NON-INT ADV
        if is_adv(word) and not is_fragment(words, i):
            adverb = get_adv(word)
            # muchísimo is the intensifier mucho itself, not a host
            if adverb.startswith(("muchísim", "tantísim")):
                continue
            isimo_base = strip_isimo_adv(adverb)

            # muy lejos
            modifier = _modifier(words, i, degree)
            if modifier is None or adverb in comparatives:
                continue
            intensifier, double = modifier
            if intensifier != "/" and (adverb in non_gradable or (intensifier, adverb) in fixed_expressions):
                continue
            if isimo_base:
                intensifier, adverb = "-ísimo", isimo_base

            # FRASE REAL
            phrase_tagged = " ".join(words)
            phrase = " ".join(re.sub(r"_.*", "", word) for word in words)

            row_data = {
                "Speaker": speaker,
                "Phr_tagged": phrase_tagged,
                "Phr": phrase,
                "Double": double,
                "Int": intensifier,
                "Int_type": int_types.get(intensifier, "/"),
                "Adv": adverb,
                "Adj": "/",
                "Lex_Adj": "/",
                "Adj_type": "/",
                "Noun": "/",
                "Negation": get_negation(words, i, parse[i] if parse else None),
            }
            add_verb(row_data, parse[i] if parse else None, words)
            rows.append(row_data)
    return rows


def drop_invariant_hosts(df):
    """drop_invariant_hosts removes every row of an adjective lemma or adverb that is never intensified in df."""
    if df.empty:
        return df
    host = df["Lex_Adj"].where(df["Adv"] == "/", df["Adv"].str.lower())
    varies = (df["Int"] != "/").groupby(host).transform("any")
    print(f"Dropped {(~varies).sum()} rows of {host[~varies].nunique()} hosts never intensified")
    return df[varies].reset_index(drop=True)


def isimo_base(stem, lexicon):
    """isimo_base picks the host an -ísimo stem comes from (grand -> grande, facil -> fácil) using lexicon."""
    if stem in isimo_adv_base:
        return isimo_adv_base[stem]
    candidates = [stem + "o", stem + "e", stem, stem + "os"]
    if stem.endswith("bil"):
        candidates.append(stem[:-3] + "ble")
    # felicísimo, antiquísimo (qu was already turned into c)
    if stem.endswith("c"):
        candidates += [stem[:-1] + "z", stem[:-1] + "guo"]
    for candidate in candidates:
        if deaccent(candidate) in lexicon:
            return lexicon[deaccent(candidate)]
    if re.search(r"n[dt]$|rav$", stem):
        return stem + "e"
    return stem + "o"


def _host_lexicon(hosts):
    # accentless key, since -ísimo drops the base's accent (rápido -> rapidísimo)
    lexicon = {}
    for host, _ in Counter(hosts).most_common():
        lexicon.setdefault(deaccent(host), host)
    return lexicon


def _rebase_surface(surface, stem, base):
    # granda -> grande, grandas -> grandes, rapida -> rápida
    if not surface.startswith(stem):
        return surface
    ending = surface[len(stem) :]
    if base.endswith("o"):
        return base[:-1] + ending
    if ending.endswith("s") and not base.endswith("s"):
        return base + ("s" if base[-1] in "aeiouáéíóú" else "es")
    return base


def fix_isimo_hosts(df):
    """fix_isimo_hosts replaces the default -o base of -ísimo hosts (grando, importanto) with the corpus form."""
    if df.empty:
        return df
    df = df.copy()
    isimo = df["Int"] == "-ísimo"
    adj_rows = df["Adj"] != "/"
    adj_lexicon = _host_lexicon(df.loc[~isimo & adj_rows, "Lex_Adj"])
    adv_lexicon = _host_lexicon(list(df.loc[~isimo & ~adj_rows, "Adv"].str.lower()) + list(adj_lexicon.values()))
    for i in df.index[isimo & adj_rows]:
        lex = df.at[i, "Lex_Adj"]
        if not lex.endswith("o"):
            continue
        stem = lex[:-1]
        base = isimo_base(stem, adj_lexicon)
        df.at[i, "Lex_Adj"] = base
        df.at[i, "Adj"] = _rebase_surface(df.at[i, "Adj"], stem, base)
    for i in df.index[isimo & ~adj_rows]:
        adv = df.at[i, "Adv"]
        if adv.endswith("o"):
            df.at[i, "Adv"] = isimo_base(adv[:-1], adv_lexicon)
    return df


def analyze(input_path, output_filename=None, parses=None, drop_invariant=False):
    """analyze extracts every file in input_path; parses maps a filename to one Relations or None per token."""
    # Create a list to store data frames
    data_frames = []

    if os.path.exists(re_words):
        os.remove(re_words)

    # Iterate over marked files in the input folder
    for filename in sorted(f for f in os.listdir(input_path) if f.endswith(".txt")):
        # SPEAKER
        speaker = filename[:-4]
        print("Started analyzing:", speaker)

        # Construct the absolute path to the marked file
        marked_file_path = os.path.join(input_path, filename)

        # Initialize a list to store row data
        rows = []

        # Read the marked text from the file
        with open(marked_file_path, "r", encoding="utf-8") as file:
            # Read entire file and replace all newlines
            content = file.read()
            content = content.replace("\n", " ")

            # Split the content into segments based on custom sentence-ending punctuation
            segments = re.split(r"(?<=[,.!?]_PUNCT_[,.!?])", content)

            parse = parses(filename) if parses else None
            starts = [m.start() for m in re.finditer(r"\S+", content)]
            if parse is not None and len(parse) != len(starts):
                raise ValueError(f"{filename}: parse has {len(parse)} tokens, tags have {len(starts)}")

            # tan cansada , que no sé: the result clause can lie past the segment's comma
            degree = degree_types(retag(content.split()))

            # Process each segment
            offset = 0
            for segment in segments:
                # the split can fall inside a token ("..._PUNCT_..."), so map by character offset
                index = [bisect.bisect_right(starts, offset + m.start()) - 1 for m in re.finditer(r"\S+", segment)]
                seg_parse = [parse[k] for k in index] if parse is not None else None
                offset += len(segment)
                seg_rows = process_segment(segment, speaker, seg_parse, [degree[k] for k in index])
                rows.extend(seg_rows)

        # Check if rows list is not empty
        if rows:
            # Create a DataFrame for the current file and append it to the list
            df = pd.DataFrame(rows)
            data_frames.append(df)
            print(f"Appended DataFrame for file: {filename}")
        else:
            print(f"No valid rows found in file: {filename}")

    data = pd.concat(data_frames, ignore_index=True) if data_frames else pd.DataFrame()
    data = fix_isimo_hosts(data)
    # hosts with no variation tell nothing about the choice to intensify
    if drop_invariant:
        data = drop_invariant_hosts(data)

    print("Successfully created data")
    print(f"re- words saved to {re_words}")

    if output_filename:
        data.to_csv(output_filename, index=False)
    return data


def numero(row, count_dict=None):
    # Split the original label to get the speaker number
    if count_dict is None:
        count_dict = {}
    speaker_number = row["Speaker"]

    # Update the count for this speaker number
    count_dict[speaker_number] = count_dict.get(speaker_number, 0) + 1

    # Generate the new label
    new_label = f"{speaker_number}_{count_dict[speaker_number]:02d}"
    return new_label


# add syl col
def count_syllables(word):
    # Remove silent 'u' in gue/gui/que/qui unless it has a diaeresis (ü)
    word = re.sub(r"gue|gui|que|qui", lambda m: m.group(0).replace("u", ""), word)

    # Count vowel groups (as a simple approximation of syllables)
    syllables = re.findall(r"[aeiouáéíóúü]+", word)

    return len(syllables)


def merge_speaker_data(id_df, int_df):
    transformed_data = []

    # Iterate through each row in df
    for _, row in int_df.iterrows():
        Speaker = row["Speaker"]
        id_row = id_df[id_df["Speaker"] == Speaker]

        if not id_row.empty:
            # Convert id_row to a dict, excluding the Speaker column
            row_data = row.to_dict()
            id_data = id_row.iloc[0].to_dict()
            id_data.pop("Speaker", None)

            # Combine row data with id_data
            merged_row = {**row_data}
            for key, value in id_data.items():
                if pd.notna(value):  # Only use id_data value if it's not null/NaN
                    merged_row[key] = value

            transformed_data.append(merged_row)

    transformed_df = pd.DataFrame(transformed_data)
    print("Speaker data merged into intensifier data")
    return transformed_df


# columns with few distinct words, stored once in a shared term table
term_cols = [
    "Double",
    "Int",
    "Int_type",
    "Adv",
    "Adj",
    "Lex_Adj",
    "Adj_type",
    "Noun",
    "Negation",
    "Verb",
    "Inf_Verb",
]
phrase_cols = ["Phr_tagged", "Phr"]
token_cols = ["Number", "Syllable"]


def _quote(name):
    return '"' + str(name).replace('"', '""') + '"'


def _sql_values(df):
    # sqlite3 can't bind numpy scalars or NaN
    return [
        tuple(None if pd.isna(v) else v.item() if hasattr(v, "item") else v for v in row)
        for row in df.itertuples(index=False)
    ]


def to_sqlite(df, output_filename):
    """to_sqlite writes df as a normalized SQLite database whose intensifier_data view rebuilds df."""
    terms = [c for c in term_cols if c in df]
    phrases = [c for c in phrase_cols if c in df]
    tokens = [c for c in token_cols if c in df]
    # whatever is left is speaker metadata, which repeats on every row of a speaker
    sources = [c for c in df if c not in terms + phrases + tokens]

    source_id = df.groupby(sources, dropna=False, sort=False).ngroup() + 1
    phrase_id = df.groupby(phrases, dropna=False, sort=False).ngroup() + 1
    term_codes, term_text = pd.factorize(pd.concat([df[c] for c in terms]), use_na_sentinel=False)
    term_ids = pd.DataFrame(term_codes.reshape(len(terms), len(df)).T + 1, columns=terms, index=df.index)

    if os.path.exists(output_filename):
        os.remove(output_filename)
    con = sqlite3.connect(output_filename)

    # untyped columns so ints, floats and text all come back as they went in
    def create(table, cols, data):
        con.execute(f"CREATE TABLE {table} (id INTEGER PRIMARY KEY, {', '.join(_quote(c) for c in cols)})")
        con.executemany(
            f"INSERT INTO {table} VALUES ({', '.join('?' * (len(cols) + 1))})",
            _sql_values(data),
        )

    create(
        "source",
        sources,
        df[sources].assign(id=source_id)[["id"] + sources].drop_duplicates("id"),
    )
    create(
        "phrase",
        phrases,
        df[phrases].assign(id=phrase_id)[["id"] + phrases].drop_duplicates("id"),
    )
    create(
        "term",
        ["text"],
        pd.DataFrame({"id": range(1, len(term_text) + 1), "text": term_text}),
    )
    token = pd.concat(
        [
            pd.Series(range(1, len(df) + 1), index=df.index, name="id"),
            source_id.rename("source_id"),
            phrase_id.rename("phrase_id"),
            term_ids.add_suffix("_id"),
            df[tokens],
        ],
        axis=1,
    )
    create("token", list(token.columns[1:]), token)

    select, joins = [], []
    for c in df:
        if c in terms:
            alias = _quote("t_" + c)
            joins.append(f"JOIN term {alias} ON {alias}.id = k.{_quote(c + '_id')}")
            select.append(f"{alias}.text AS {_quote(c)}")
        else:
            table = "s" if c in sources else "p" if c in phrases else "k"
            select.append(f"{table}.{_quote(c)} AS {_quote(c)}")
    con.execute(f"""CREATE VIEW intensifier_data AS
        SELECT {", ".join(select)}
        FROM token k
        JOIN source s ON s.id = k.source_id
        JOIN phrase p ON p.id = k.phrase_id
        {" ".join(joins)}
        ORDER BY k.id""")

    con.execute("CREATE INDEX token_source ON token(source_id)")
    for c in ("Int", "Adj_type"):
        if c in terms:
            con.execute(f"CREATE INDEX {_quote('token_' + c)} ON token({_quote(c + '_id')})")
    con.commit()
    con.execute("VACUUM")
    con.close()
    print(f"Saved SQLite database to {output_filename}")


def write_outputs(df, output, speaker_path, xlsx=False, csv=False):
    """write_outputs adds Number and Syllable, merges speaker metadata if present, and saves output.sqlite plus optional xlsx and csv."""
    number_counts = {}
    df["Number"] = df.apply(numero, axis=1, count_dict=number_counts)
    df["Syllable"] = df["Adj"].apply(count_syllables)
    if os.path.exists(speaker_path):
        df = merge_speaker_data(pd.read_excel(speaker_path), df)
    else:
        print(f"No {speaker_path}, skipping speaker metadata")

    for col in df.select_dtypes(include=["object", "string"]).columns:
        # commas would split cells in tools that re-read the csv naively
        df[col] = df[col].str.replace(",", "", regex=False)

    to_sqlite(df, output + ".sqlite")
    if xlsx:
        df.to_excel(output + ".xlsx", index=False)
        print(f"Saved {output}.xlsx")
    if csv:
        df.to_csv(output + ".csv", index=False)
        print(f"Saved {output}.csv")
    return df
