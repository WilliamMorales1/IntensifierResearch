import argparse
import bisect
import os
import re
import sqlite3
from collections import Counter
from datetime import date

import pandas as pd

from interviewer import remove_interviewer_tagged

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
# -esa adjectives whose lemma is -eso, not gentilic -és (francesa -> francés)
eso_adjs = {"travieso", "obeso", "ileso", "espeso", "grueso", "tieso", "preso"}

# Puerto Rican lateralized /r/ verbs and other words (estal = estar, polque = porque) that taggers call ADJ
lateralized_verbs = {
    "acostal", "acueldas", "agarral", "buscal", "cambial", "competil", "conseguil", "consideral", "contal", "creel",
    "dirigil", "entral", "estal", "estudial", "hacel", "ilme", "imaginal", "impactal", "impolta", "levantal",
    "metelnos", "molestal", "paral", "pelial", "pescal", "ponel", "preparal", "prestal", "pronuncial", "quedal",
    "recueldo", "regalal", "respetal", "respiral", "saltal", "solicital", "sulgido", "telmina", "visital", "vivil",
    "cocinal", "limpial", "celebral", "tratal", "logral", "disfrutal", "telmino", "polque", "helmano", "puelto",
}  # fmt: skip

forms_of_estar = [
    "estar",
    "estal",
    "estoy",
    "estás",
    "está",
    "estamos",
    "estáis",
    "están",
    "estaba",
    "estabas",
    "estábamos",
    "estabais",
    "estaban",
    "estuve",
    "estuviste",
    "estuvo",
    "estuvimos",
    "estuvisteis",
    "estuvieron",
    "estaré",
    "estarás",
    "estará",
    "estaremos",
    "estaréis",
    "estarán",
    "estaría",
    "estarías",
    "estaría",
    "estaríamos",
    "estaríais",
    "estarían",
    "esté",
    "estés",
    "estemos",
    "estéis",
    "estén",
    "estuviera",
    "estuvieras",
    "estuviéramos",
    "estuvierais",
    "estuvieran",
    "estuviese",
    "estuvieses",
    "estuviésemos",
    "estuvieseis",
    "estuviesen",
    "estuviere",
    "estuvieres",
    "estuviéremos",
    "estuviereis",
    "estuvieren",
    "estad",
]

forms_of_ser = [
    "ser",
    "sel",
    "soy",
    "eres",
    "es",
    "somos",
    "sois",
    "son",
    "era",
    "eras",
    "éramos",
    "erais",
    "eran",
    "fui",
    "fuiste",
    "fue",
    "fuimos",
    "fuisteis",
    "fueron",
    "seré",
    "serás",
    "será",
    "seremos",
    "seréis",
    "serán",
    "sería",
    "serías",
    "sería",
    "seríamos",
    "seríais",
    "serían",
    "sea",
    "seas",
    "seás",
    "seamos",
    "seáis",
    "sean",
    "fuera",
    "fueras",
    "fuéramos",
    "fuerais",
    "fueran",
    "fuese",
    "fueses",
    "fuésemos",
    "fueseis",
    "fuesen",
    "fuere",
    "fueres",
    "fuéremos",
    "fuereis",
    "fueren",
    "sé",
    "sed",
]

forms_of_parecer = [
    "parecer",
    "parecel",
    "parezco",
    "pareces",
    "parecés",
    "parece",
    "parecemos",
    "parecéis",
    "parecen",
    "parecía",
    "parecías",
    "parecíamos",
    "parecíais",
    "parecían",
    "parecí",
    "pareciste",
    "pareció",
    "parecimos",
    "parecisteis",
    "parecieron",
    "pareceré",
    "parecerás",
    "parecerá",
    "pareceremos",
    "pareceréis",
    "parecerán",
    "parecería",
    "parecerías",
    "parecería",
    "pareceríamos",
    "pareceríais",
    "parecerían",
    "parezca",
    "parezcas",
    "parezcás",
    "parezcamos",
    "parezcáis",
    "parezcan",
    "pareciera",
    "parecieras",
    "pareciéramos",
    "parecierais",
    "parecieran",
    "pareciese",
    "parecieses",
    "pareciésemos",
    "parecieseis",
    "pareciesen",
    "pareciere",
    "parecieres",
    "pareciéremos",
    "pareciereis",
    "parecieren",
    "paracé",
    "pareced",
]

copulas = forms_of_estar + forms_of_ser + forms_of_parecer
copula_lemmas = ["estar", "ser", "parecer"]

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
}

# endings that turn a host into a fuller form of the same word rather than completing a cut-off one
inflection = re.compile(r"(e?s|[oa]s?|mente|(uc|it|ic|ísim)[oa]s?)")
# transcript speaker labels ("J: -pues") that clean_transcripts missed; TagAnt glues the dash onto the next word
speaker_label = re.compile(
    r"(?<!\S)[A-ZÁÉÍÓÚÑ]{1,3}\.?_[A-Z]+_\S* :_PUNCT_:(?: -_PUNCT_-)?(?: -(\S+?)_([A-Z]+)_-?(\S*))?"
)
turn_label = re.compile(r"(?<!\S)([A-ZÁÉÍÓÚÑ]{1,3})\.?_[A-Z]+_\S* :_PUNCT_:")
turn_question = re.compile(r".*?\?_PUNCT_\?(?:\s+(?:[,.]_PUNCT_[,.]\s+)?¿_PUNCT_¿.*?\?_PUNCT_\?)*")
# transcribers also mark a third voice inside the participant's turn: "F: -(tercera voz) sigue"
third_voice = re.compile(r"\s*\S*?tercera voz")


def remove_SPACE(input_path):
    # Check if the directory exists
    if os.path.isdir(input_path):
        # List all files in the directory
        files = os.listdir(input_path)

        # Loop through each file
        for file_name in files:
            if file_name.endswith(".txt"):
                file_path = os.path.join(input_path, file_name)

                # Read the content of the file with the detected encoding
                with open(file_path, "r", encoding="utf-8") as file:
                    content = file.read()

                # Replace _SPACE_ with an empty string
                modified_content = content.replace("_SPACE_", "")

                # Write the modified content back to the file
                with open(file_path, "w", encoding="utf-8") as file:
                    file.write(modified_content)


def remove_other_turns(text, label=turn_label, question=turn_question):
    """remove_other_turns drops every labeled turn not spoken by the participant (interviewer, third voices)."""
    matches = list(label.finditer(text))
    names = Counter(m[1] for m in matches)
    # one-line transcripts run the participant's answer on after the question ("E: ¿cómo? difícil, ...");
    # in line-based ones every labeled line is someone else (interviewer, relative, radio)
    inline = text.count("\n") < 10
    keep = None
    if inline:
        # "I:" is the informant; otherwise a label used throughout marks the participant's own turns
        keep = "I" if "I" in names else next((n for n, c in names.most_common(1) if c >= 20), None)
    out, pos = [], 0
    for k, m in enumerate(matches):
        if (m[1] == keep and not third_voice.match(text, m.end())) or m.start() < pos:
            continue
        end = matches[k + 1].start() if k + 1 < len(matches) else len(text)
        eol = text.find("\n", m.end())
        if eol != -1:
            end = min(end, eol)
        # the interviewer's turn ends with its question(s): "E.: a, se nota ¿no? ¿cuántos años llevan juntos?, me decía ..."
        q = question.match(text, m.end(), end) if inline else None
        if q:
            end = min(end, q.end())
        out.append(text[pos : m.start()])
        pos = end
    out.append(text[pos:])
    return "".join(out)


def strip_speaker_labels(content):
    return speaker_label.sub(lambda m: f"{m[1]}_{m[2]}_{m[3]}" if m[1] else "", content)


def is_well_formed(word):
    return bool(any(word.endswith(c) for c in "oaeslndr") and re.match(r"^[a-zA-Z_áéíóúüñÁÉÍÓÚÜÑí]+$", word))


def is_adj(word):
    adj_match = re.search(r"^(.*)_ADJ_", word)
    lex_adj_match = re.search(r"_ADJ_(.+)", word)
    return bool(
        adj_match
        and lex_adj_match
        and is_well_formed(word)
        and not word.endswith("mente")
        and adj_match.group(1).lower() not in lateralized_verbs
    )


def log_re_word(word):
    os.makedirs(os.path.dirname(re_words), exist_ok=True)
    with open(re_words, "a", encoding="utf-8") as f:
        f.write(word + "\n")


def deaccent(word):
    return word.translate(str.maketrans("áéíóú", "aeiou"))


def repair_lemma(word, lemma):
    """repair_lemma undoes TagAnt lemmas cut from a feminine or plural form (acogedoro, morén, amigabl)."""
    feminine = re.fullmatch(r"(.+)as?", word)
    if feminine and re.search(r"[dts]oro$", lemma):
        return lemma[:-1]
    # -ón/-ona is a real pair (gritón); -én/-ín/-ún from -ena/-ina/-una is not
    if feminine and re.search(r"[éíú]n$", lemma) and deaccent(lemma) == feminine.group(1):
        return feminine.group(1) + "o"
    if feminine and lemma.endswith("és") and deaccent(lemma) + "o" in eso_adjs:
        return deaccent(lemma) + "o"
    # Spanish words don't end in two consonants, so TagAnt dropped the -e
    if re.search(r"[^aeiouáéíóú]{2}$", lemma) and word.startswith(lemma + "e"):
        return lemma + "e"
    return lemma


def get_adj(word):
    adj_match = re.search(r"^(.*)_ADJ_", word)
    adv_match = re.search(r"_ADJ_(.+)", word)

    adjective = adj_match.group(1)  # type: ignore
    lex_adjective = adv_match.group(1)  # type: ignore

    lex_adjective = repair_lemma(adjective.lower(), lex_adjective.lower())
    # apocope corrections
    if lex_adjective in apocope_dict:
        lex_adjective = apocope_dict[lex_adjective]
    # only plural endings lose the -s; gris, gratis, francés are singular
    if re.search(r"[aeo]s$", lex_adjective) and lex_adjective != "lejos":
        lex_adjective = lex_adjective[:-1]
    # TagAnt sometimes keeps the feminine lemma, and -dora/-tora/-sora come from masculine -or
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
        return adverb not in intensifier_list and adverb != "no"
    return False


def get_adv(word):
    adv_match = re.search(r"^(.*)_ADV_", word)
    adverb = adv_match.group(1)  # type: ignore
    if adverb.startswith("re"):
        log_re_word(adverb)
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
    # cut-off bueno, bien, todo, often with the restart outside the segment
    if host in ("bue", "bie", "tod"):
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
    return intensifier.lower()


def is_mas_bien(words, i):
    # "más bien" means "rather", so bien there is not an intensifier
    return (
        i > 1 and words[i - 1].split("_")[0].lower() == "bien" and words[i - 2].split("_")[0].lower() in ("más", "mas")
    )


def is_copula(word):
    parts = word.split("_")
    return parts[0].lower() in copulas or (len(parts) >= 3 and parts[-1].lower() in copula_lemmas)


def add_verb(row_data, relations, words):
    # like Noun, the verb must be visible in Phr; the parse can reach past the segment
    visible = relations and relations.verb.lower() in (w.split("_")[0].lower() for w in words)
    row_data["Verb"] = relations.verb if visible else "/"
    row_data["Inf_Verb"] = relations.inf_verb if visible else "/"


# words both taggers call ADJ, NOUN or VERB that are always adverbs
# the transformer tagger calls cerquita ADJ ("queda súper cerquita")
always_adverbs = {"entoes", "ahorita", "ahoritica", "cerquita"}


def is_weather_noun(words, i):
    """is_weather_noun reports whether words[i] is the noun in mucho frío or hace (bastante) frío."""
    before = [w.split("_")[0].lower() for w in words[max(0, i - 2) : i]]
    if before and before[-1] in ("mucho", "tanto", "poco"):
        return True
    hacer = ("hace", "hacía", "hacia", "hizo", "hará", "haga", "hiciera", "hacer")
    return bool(before) and (before[-1] in hacer or len(before) == 2 and before[0] in hacer and is_int(words[i - 1]))


def retag(words):
    """retag fixes host tags both taggers get wrong: entoes/ahorita ADV, poquito ADV or DET, poco DET, mucho frío NOUN."""
    out = []
    for i, word in enumerate(words):
        parts = word.split("_")
        if len(parts) == 3:
            text, pos, lemma = parts
            low = text.lower()
            if low in always_adverbs and pos != "ADV":
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
            elif re.fullmatch(r"poc[oa]s?", low) and pos == "ADJ":
                pos = "DET"
            elif low in ("frío", "frio", "calor") and pos == "ADJ" and is_weather_noun(words, i):
                pos = "NOUN"
            word = f"{text}_{pos}_{lemma}"
        out.append(word)
    return out


def process_segment(segment, speaker, parse=None):
    """process_segment extracts host rows; parse, when given, holds a Relations or None per word."""
    rows = []

    intensifier = None
    adjective = None
    lex_adjective = None
    attributive = None
    noun = None
    double = None

    words = retag(segment.split())

    # Process each word in the segment
    for i, word in enumerate(words):
        # bueno
        if is_adj(word) and not is_fragment(words, i):
            adjective, lex_adjective = get_adj(word)

            if parse and parse[i]:
                attributive, noun = parse[i].adj_type, parse[i].noun
                # the parse spans past the segment, but the noun must be visible in Phr
                if noun != "/" and noun.lower() not in (w.split("_")[0].lower() for w in words):
                    noun = "/"
                    if attributive == "attributive":
                        attributive = "ambiguous"
            # noun adj
            elif i > 0 and "_NOUN_" in words[i - 1] and not is_int(words[i - 1]):
                attributive = "attributive"
                noun = re.search(r"^(.*?)_", words[i - 1]).group(1)  # type: ignore
            # adj noun
            elif i < len(words) - 1 and "_NOUN_" in words[i + 1]:
                attributive = "attributive"
                noun = re.search(r"^(.*?)_", words[i + 1]).group(1)  # type: ignore
            # noun int adj
            elif i > 1 and "_NOUN_" in words[i - 2] and is_int(words[i - 1]):
                attributive = "attributive"
                noun = re.search(r"^(.*?)_", words[i - 2]).group(1)  # type: ignore
            # cop int adj
            elif i > 1 and is_copula(words[i - 2]) or i > 0 and is_copula(words[i - 1]):
                attributive = "predicative"
                noun = "/"
            else:
                attributive = "ambiguous"
                noun = "/"
            if not re.match(r"^[a-zA-Z_áéíóúüñÁÉÍÓÚÜÑ/]+$", noun):
                attributive = "ambiguous"
                noun = "/"

            # muy bueno
            if i > 0 and is_int(words[i - 1]) and not is_mas_bien(words, i):
                intensifier = get_int(words[i - 1])
                # no muy bueno
                if i > 1 and words[i - 2] == "no_ADV_no":
                    continue
                if (intensifier, lex_adjective) in fixed_expressions:
                    continue
                # muy muy bueno
                elif i > 1 and is_int(words[i - 2]):
                    double = get_int(words[i - 2])
                else:
                    double = "/"
            else:
                intensifier = "/"
                double = "/"

            if lex_adjective.endswith("ísimo"):
                # muchísimos, tantísimas are quantifiers TagAnt calls ADJ
                if lex_adjective.startswith(("muchísim", "tantísim")):
                    continue
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
                "Adv": "/",
                "Adj": adjective,
                "Lex_Adj": lex_adjective,
                "Adj_type": attributive,
                "Noun": noun.lower(),
            }
            if parse is not None:
                add_verb(row_data, parse[i], words)
            rows.append(row_data)

        # IF NON-INT ADV
        if is_adv(word) and not is_fragment(words, i):
            adverb = get_adv(word)
            # muchísimo is the intensifier mucho itself, not a host
            if adverb.startswith(("muchísim", "tantísim")):
                continue
            isimo_base = strip_isimo_adv(adverb)

            # muy lejos
            if i > 0 and is_int(words[i - 1]) and not is_mas_bien(words, i):
                intensifier = get_int(words[i - 1])
                # no muy lejos
                if i > 1 and words[i - 2] == "no_ADV_no":
                    continue
                if adverb in non_gradable or (intensifier, adverb) in fixed_expressions:
                    continue
                # muy muy lejos
                elif i > 1 and is_int(words[i - 2]):
                    double = get_int(words[i - 2])
                else:
                    double = "/"
            else:
                intensifier = "/"
                double = "/"
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
                "Adv": adverb,
                "Adj": "/",
                "Lex_Adj": "/",
                "Adj_type": "/",
                "Noun": "/",
            }
            if parse is not None:
                add_verb(row_data, parse[i], words)
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


def analyze(input_path, output_filename, parses=None, clean_turns=True, drop_invariant=False):
    """analyze extracts every file in input_path; parses maps a filename to one Relations or None per token."""
    # no mas, tan
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
            # tags made from uncleaned transcripts (TagAnt) still hold labels and interviewer speech
            if clean_turns:
                content = strip_speaker_labels(remove_interviewer_tagged(remove_other_turns(content)))
            content = content.replace("\n", " ")

            # Split the content into segments based on custom sentence-ending punctuation
            segments = re.split(r"(?<=[,.!?]_PUNCT_[,.!?])", content)

            parse = parses(filename) if parses else None
            starts = [m.start() for m in re.finditer(r"\S+", content)]
            if parse is not None and len(parse) != len(starts):
                raise ValueError(f"{filename}: parse has {len(parse)} tokens, tags have {len(starts)}")

            # Process each segment
            offset = 0
            for segment in segments:
                seg_parse = None
                if parse is not None:
                    # the split can fall inside a token ("..._PUNCT_..."), so map by character offset
                    seg_parse = [
                        parse[bisect.bisect_right(starts, offset + m.start()) - 1] for m in re.finditer(r"\S+", segment)
                    ]
                offset += len(segment)
                seg_rows = process_segment(segment, speaker, seg_parse)
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

    # Save the DataFrame to a CSV file
    data.to_csv(output_filename, index=False)
    return data


def closest_verb_non_infinitive(row):
    phrase = row["Phr_tagged"]
    intensifier_pos = phrase.find(row["Adj"])

    if intensifier_pos == -1:
        return "/"

    # Find the sentence containing the intensifier
    # Split by periods and track positions
    period_before = phrase.rfind(".", 0, intensifier_pos)
    sentence_start = 0 if period_before == -1 else period_before + 1  # +1 to skip the period
    sentence_end = phrase.find(".", intensifier_pos)
    if sentence_end == -1:
        sentence_end = len(phrase)

    sentence = phrase[sentence_start:sentence_end]
    # Adjust intensifier position relative to the sentence
    intensifier_pos_in_sentence = intensifier_pos - sentence_start

    # Initialize minimum distances and closest matches
    min_distance_verb = float("inf")
    min_distance_aux = float("inf")
    closest_verb = None
    closest_aux = None

    # Regular expression to find verb and auxiliary patterns
    pattern = r"\b(\w+)_(VERB|AUX)_(\w+)\b"

    for match in re.finditer(pattern, sentence):
        start_pos = match.start()
        end_pos = match.end()
        match_center = (start_pos + end_pos) // 2
        distance = abs(match_center - intensifier_pos_in_sentence)

        if "VERB" in match.group():
            if distance < min_distance_verb:
                min_distance_verb = distance
                closest_verb = match.group(1)
        elif "AUX" in match.group() and distance < min_distance_aux:
            min_distance_aux = distance
            closest_aux = match.group(1)

    # Determine which is closer
    if closest_verb and closest_aux:
        return closest_verb if min_distance_verb < min_distance_aux else closest_aux
    elif closest_verb:
        return closest_verb
    elif closest_aux:
        return closest_aux
    else:
        return "/"


def closest_verb_infinitive(row):
    phrase = row["Phr_tagged"]
    intensifier_pos = phrase.find(row["Adj"])

    if intensifier_pos == -1:
        return "/"

    # Find the sentence containing the intensifier
    period_before = phrase.rfind(".", 0, intensifier_pos)
    sentence_start = 0 if period_before == -1 else period_before + 1
    sentence_end = phrase.find(".", intensifier_pos)
    if sentence_end == -1:
        sentence_end = len(phrase)

    sentence = phrase[sentence_start:sentence_end]
    # Adjust intensifier position relative to the sentence
    intensifier_pos_in_sentence = intensifier_pos - sentence_start

    # Initialize minimum distances and closest matches
    min_distance_verb = float("inf")
    min_distance_aux = float("inf")
    closest_verb = None
    closest_aux = None

    # Regular expression to find verb and auxiliary patterns
    pattern = r"\b(\w+)_(VERB|AUX)_(\w+)\b"

    for match in re.finditer(pattern, sentence):
        start_pos = match.start()
        end_pos = match.end()
        match_center = (start_pos + end_pos) // 2
        distance = abs(match_center - intensifier_pos_in_sentence)

        if "VERB" in match.group():
            if distance < min_distance_verb:
                min_distance_verb = distance
                closest_verb = match.group(3)
        elif "AUX" in match.group() and distance < min_distance_aux:
            min_distance_aux = distance
            closest_aux = match.group(3)

    # Determine which is closer
    if closest_verb and closest_aux:
        return closest_verb if min_distance_verb < min_distance_aux else closest_aux
    elif closest_verb:
        return closest_verb
    elif closest_aux:
        return closest_aux
    else:
        return "/"


# make numbered based on speaker col
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
    print("Speaker data merged into intensifer data")
    return transformed_df


# columns with few distinct words, stored once in a shared term table
term_cols = [
    "Double",
    "Int",
    "Adv",
    "Adj",
    "Lex_Adj",
    "Adj_type",
    "Noun",
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


def write_outputs(df, output, speaker_path):
    """write_outputs adds Number and Syllable, merges speaker metadata if present, and saves xlsx and sqlite."""
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

    df.to_excel(output[:-4] + ".xlsx", index=False)
    to_sqlite(df, output[:-4] + ".sqlite")
    return df


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/tagged", help="folder of TagAnt word_POS_lemma .txt files")
    parser.add_argument("--speakers", default=speaker_data, help="speaker metadata sheet, one row per Speaker")
    parser.add_argument(
        "--drop-invariant", action="store_true", help="drop every row of a host that is never intensified"
    )
    args = parser.parse_args()

    os.makedirs("output", exist_ok=True)
    output = "output/intensifier_data_" + date.today().isoformat() + ".csv"
    remove_SPACE(args.input)  # writes without space back to files
    df = analyze(args.input, output, drop_invariant=args.drop_invariant)
    df["Verb"] = df.apply(closest_verb_non_infinitive, axis=1)
    df["Inf_Verb"] = df.apply(closest_verb_infinitive, axis=1)
    write_outputs(df, output, args.speakers)

    print("Make sure to manually check the -ísimo cases!")
