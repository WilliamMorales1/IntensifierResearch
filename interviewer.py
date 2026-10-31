# finds the interviewer's speech left unlabeled in the transcripts, so steps 5 and 7 can drop it

import re

question = re.compile(r"¿[^?¿\n]*\?")
# addressing the interviewee: usted/tú forms, possessives and second-person verbs
second_person = re.compile(
    r"\b(usted|ustedes|sumercé|su|sus|tú|tu|tus|te|ti|contigo|vos|"
    r"le (?:parece|parecen|gusta|gustan|gustaría|ha|han|queda|cae|pasó|toca)|"
    r"tienes|tenés|eres|sos|estás|vives|vivís|haces|hacés|piensas|pensás|crees|creés|opinas|recuerdas|"
    r"consideras|sientes|dedicas|trabajas|estudias|visualizas|"
    r"\w+(?:aste|iste|abas|ías))\b",
    re.I,
)
not_second = re.compile(r"\b(triste|tristes|chiste|chistes|existe|consiste|insiste|resiste|asiste|desiste|viste|días|tías|frías|vías)\b", re.I)
first_person = re.compile(r"\b(yo|me|mi|mis|mí|conmigo|nosotros|nosotras|nos|nuestro|nuestra|nuestros|nuestras)\b", re.I)
# the participant's own address to the interviewer, not questions put to the participant
fillers = re.compile(
    r"\b(tú sabes|tu sabes|usted sabe|sabe usted|sabes|sabe|me entiendes|me entiende|"
    r"te digo|le digo|te dijera|le dijera|te cuento|le cuento|te explico|le explico|te aclaro|le aclaro|"
    r"(?:te|le) puedo (?:decir|contar)|(?:te|le) (?:voy a|iba a) (?:decir|contar)|"
    r"mira|mire|fíjate|fíjese|imagínate|imagínese|vea|oiga|oye|ve)\b",
    re.I,
)
tags = re.compile(
    r"¿\s*(no|sí|si|cierto|verdad|ya|ve|vio|viste|oyó|oíste|sabe|sabes|ah|eh|ajá|qué|cómo|perdón|"
    r"me entiende|me entiendes|entiende|entiendes|me explico|sí o no|no le parece|no te parece|no cree|no crees|"
    r"cómo (?:le|te) (?:digo|dijera|explico)|cómo se llama|cómo es que se llama)\s*\?",
    re.I,
)
# "me dice ¿usted qué es de él?" quotes someone else to the participant
reported = re.compile(
    r"\b(dice|dijo|dije|decía|decían|digo|dicen|decir|pregunta|pregunto|preguntó|pregunté|preguntaba|preguntan|"
    r"preguntaron|contestó|izque|pensé|pensaba)\b|[\"“”«'\-–—:]\s*$",
    re.I,
)
# "les dijo. ¿usted quiere que coman?": the quote follows a finished sentence
said_before = re.compile(r"\b(dijo|dije|dice|decía|preguntó|pregunto|pregunta|preguntaba|contestó)\s*[.:,]\s*$", re.I)
cues = re.compile(r"\b(hablemos|vamos a|pasemos|cuéntame|cuénteme|háblame|hábleme|dime|dígame|describe|describa|descríbame|ahora)\b", re.I)
boundary = re.compile(r"[.?!¡¿\n]")
# "E.", "E..", "E:", "e:" and "E ¿" open an interviewer line; lowercase "e ¿" and "e." are the filler "eh"
yes_no = re.compile(r"(sí|si|no|claro|exacto|ajá|aja|tampoco|también|nunca|jamás)\b[\s,.!]*", re.I)
label_line = re.compile(r"^\s*(E\.+:?|E:|e:|E(?=\s*¿))")
# the participant's own line labels ("I..", "i:", "i.:", "B.") are dropped, the words kept
informant_label = re.compile(r"^\s*([A-DF-Z]\.+:?|i\.?:|I:)\s*")


def addresses_interviewee(text, in_question=True):
    text = fillers.sub(" ", not_second.sub(" ", text))
    if not in_question:
        # outside a question su/sus is mostly "his/her/their"
        text = re.sub(r"\b(su|sus)\b", " ", text, flags=re.I)
    return bool(second_person.search(text)) and not first_person.search(text)


def interviewer_question(text, m):
    """interviewer_question reports whether question m is put to the participant rather than echoed, quoted or a tag."""
    q = m.group(0)
    if tags.fullmatch(q) or len(q.split()) < 2 and not second_person.search(q):
        return False
    # the quote can start anywhere in the sentence: "le decía ven acá, ven acá ¿tú quieres comprar?"
    prev = max((b.end() for b in boundary.finditer(text, max(0, m.start() - 80), m.start())), default=max(0, m.start() - 80))
    if (
        reported.search(text[prev : m.start()])
        or said_before.search(text[max(0, m.start() - 40) : m.start()])
        or re.match(r"\s*[”\"»]", text[m.end() : m.end() + 3])
    ):
        return False
    return addresses_interviewee(q)


def _content(words):
    return {w for w in re.findall(r"\w+", words.lower()) if len(w) >= 3}


def _line_spans(text):
    spans, pos = [], 0
    lines = text.split("\n")
    for i, line in enumerate(lines):
        end = pos + len(line)
        if label_line.match(line):
            spans.append((pos, end))
        elif m := informant_label.match(line):
            spans.append((pos, pos + m.end()))
        else:
            qs = list(question.finditer(line))
            rest = question.sub(" ", line)
            # a line that is only a question; anything else on it is the participant answering
            if qs and len(re.findall(r"\w+", rest)) <= 2:
                nxt = lines[i + 1].lstrip() if i + 1 < len(lines) else ""
                echo = question.match(nxt)
                echoed = echo and _content(echo.group(0)) and _content(echo.group(0)) <= _content(line)
                # an echo only marks short clarifications ("¿pero cercano?" -> "¿cercano?"), not rhetorical runs
                short = sum(len(m.group(0).split()) for m in qs) <= 3
                asked = any(interviewer_question(line, m) for m in qs)
                # a yes/no question answered on the next line: "¿cuentos de historias?" -> "Sí, también."
                answered = (
                    bool(yes_no.match(nxt))
                    and len(re.findall(r"\w+", nxt)) <= 2
                    and len(qs[0].group(0).split()) >= 2
                    and not tags.fullmatch(qs[0].group(0).strip())
                    and not first_person.search(line)
                )
                if echoed and (short or asked) or asked or answered:
                    spans.append((pos, end))
        pos = end + 1
    return spans


def _inline_spans(text):
    qs = list(question.finditer(text))
    marked = [interviewer_question(text, m) for m in qs]
    # questions run together with an interviewer question are the interviewer's too: "¿tienes amigos? ¿cómo eran?"
    changed = True
    while changed:
        changed = False
        for k, m in enumerate(qs):
            if marked[k] or tags.fullmatch(m.group(0)) or first_person.search(m.group(0)):
                continue
            for j in (k - 1, k + 1):
                if 0 <= j < len(qs) and marked[j]:
                    a, b = sorted((qs[j], m), key=lambda x: x.start())
                    if not re.search(r"\w", text[a.end() : b.start()]):
                        marked[k] = changed = True
    spans = []
    for k, m in enumerate(qs):
        if not marked[k]:
            continue
        start = m.start()
        # lead-in back to the previous sentence boundary: "ahora vamos a la parte de tu profesión ¿a qué te dedicas?"
        prev = max((b.end() for b in boundary.finditer(text, 0, m.start())), default=0)
        # without punctuation the boundary can sit a whole answer back; a lead-in is a few words
        words = list(re.finditer(r"\S+", text[prev : m.start()]))
        if len(words) > 12:
            prev += words[-12].start()
        lead = text[prev : m.start()]
        if lead.strip() and (addresses_interviewee(lead, False) or cues.search(lead)) and not first_person.search(lead):
            start = prev
        spans.append((start, m.end()))
    # a whole sentence addressed to the participant next to an interviewer question
    for s in re.finditer(r"[^.?!¿¡\n]+[.!]", text):
        near = any(abs(s.start() - e) <= 2 or abs(s.end() - b) <= 2 for b, e in spans)
        # interviewer asides are short; a long one is the participant using generic "tú"
        if near and len(s.group(0).split()) <= 20 and addresses_interviewee(s.group(0), False):
            spans.append((s.start(), s.end()))
    return sorted(spans)


def interviewer_spans(text):
    """interviewer_spans returns the character spans of text spoken by the interviewer."""
    return _line_spans(text) if text.count("\n") >= 10 else _inline_spans(text)


def remove_interviewer(text):
    out, pos = [], 0
    for start, end in interviewer_spans(text):
        if start >= pos:
            out.append(text[pos:start])
            pos = end
    out.append(text[pos:])
    return "".join(out)


def remove_interviewer_tagged(content):
    """remove_interviewer_tagged drops the tokens of word_UPOS_lemma lines that fall in interviewer speech."""
    lines = [line.split() for line in content.split("\n")]
    text = "\n".join(" ".join(t.split("_")[0] for t in tokens) for tokens in lines)
    spans = interviewer_spans(text)
    if not spans:
        return content
    out, pos = [], 0
    for tokens in lines:
        kept = []
        for t in tokens:
            word = t.split("_")[0]
            if not any(a <= pos < b for a, b in spans):
                kept.append(t)
            pos += len(word) + 1
        if not tokens:
            pos += 1
        out.append(" ".join(kept))
    return "\n".join(out)
