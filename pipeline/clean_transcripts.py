# cleans the raw docx transcripts into participant-only text: labeled turns, unlabeled interviewer speech and labels removed

import os
import re
import subprocess
from collections import Counter

from docx import Document

question = re.compile(r"¿[^?¿\n]*\?")
# addressing the interviewee: usted/tú forms, possessives and second-person verbs
second_person = re.compile(
    r"\b(usted|ustedes|sumercé|su|sus|tú|tu|tus|te|ti|contigo|vos|"
    r"le (?:parece|parecen|gusta|gustan|gustaría|ha|han|queda|cae|pasó|toca)|"
    r"tienes|tenés|eres|sos|estás|vives|vivís|haces|hacés|piensas|pensás|crees|creés|opinas|recuerdas|"
    r"consideras|sientes|dedicas|trabajas|estudias|visualizas|"
    r"\w+(?:aste|iste|abas|ías))\b",
    re.IGNORECASE,
)
not_second = re.compile(
    r"\b(triste|tristes|chiste|chistes|existe|consiste|insiste|resiste|asiste|desiste|viste|días|tías|frías|vías)\b",
    re.IGNORECASE,
)
first_person = re.compile(
    r"\b(yo|me|mi|mis|mí|conmigo|nosotros|nosotras|nos|nuestro|nuestra|nuestros|nuestras)\b", re.IGNORECASE
)
# the participant's own address to the interviewer, not questions put to the participant
fillers = re.compile(
    r"\b(tú sabes|tu sabes|usted sabe|sabe usted|sabes|sabe|me entiendes|me entiende|"
    r"te digo|le digo|te dijera|le dijera|te cuento|le cuento|te explico|le explico|te aclaro|le aclaro|"
    r"(?:te|le) puedo (?:decir|contar)|(?:te|le) (?:voy a|iba a) (?:decir|contar)|"
    r"mira|mire|fíjate|fíjese|imagínate|imagínese|vea|oiga|oye|ve)\b",
    re.IGNORECASE,
)
tags = re.compile(
    r"¿\s*(no|sí|si|cierto|verdad|ya|ve|vio|viste|oyó|oíste|sabe|sabes|ah|eh|ajá|qué|cómo|perdón|"
    r"me entiende|me entiendes|entiende|entiendes|me explico|sí o no|no le parece|no te parece|no cree|no crees|"
    r"cómo (?:le|te) (?:digo|dijera|explico)|cómo se llama|cómo es que se llama)\s*\?",
    re.IGNORECASE,
)
# "me dice ¿usted qué es de él?" quotes someone else to the participant
reported = re.compile(
    r"\b(dice|dijo|dije|decía|decían|digo|dicen|decir|pregunta|pregunto|preguntó|pregunté|preguntaba|preguntan|"
    r"preguntaron|contestó|izque|pensé|pensaba)\b|[\"“”«'\-–—:]\s*$",
    re.IGNORECASE,
)
# "les dijo. ¿usted quiere que coman?": the quote follows a finished sentence
said_before = re.compile(
    r"\b(dijo|dije|dice|decía|preguntó|pregunto|pregunta|preguntaba|contestó)\s*[.:,]\s*$", re.IGNORECASE
)
cues = re.compile(
    r"\b(hablemos|vamos a|pasemos|cuéntame|cuénteme|háblame|hábleme|dime|dígame|describe|describa|descríbame|ahora)\b",
    re.IGNORECASE,
)
boundary = re.compile(r"[.?!¡¿\n]")
# "E.", "E..", "E:", "e:" and "E ¿" open an interviewer line; lowercase "e ¿" and "e." are the filler "eh"
yes_no = re.compile(r"(sí|si|no|claro|exacto|ajá|aja|tampoco|también|nunca|jamás)\b[\s,.!]*", re.IGNORECASE)
label_line = re.compile(r"^\s*(E\.+:?|E:|e:|E(?=\s*¿))")
# the participant's own line labels ("I..", "i:", "i.:", "B.") are dropped, the words kept
informant_label = re.compile(r"^\s*([A-DF-Z]\.+:?|i\.?:|I:)\s*")


def addresses_interviewee(text, in_question=True):
    text = fillers.sub(" ", not_second.sub(" ", text))
    if not in_question:
        # outside a question su/sus is mostly "his/her/their"
        text = re.sub(r"\b(su|sus)\b", " ", text, flags=re.IGNORECASE)
    return bool(second_person.search(text)) and not first_person.search(text)


def interviewer_question(text, m):
    """interviewer_question reports whether question m is put to the participant rather than echoed, quoted or a tag."""
    q = m.group(0)
    if tags.fullmatch(q) or len(q.split()) < 2 and not second_person.search(q):
        return False
    # the quote can start anywhere in the sentence: "le decía ven acá, ven acá ¿tú quieres comprar?"
    prev = max(
        (b.end() for b in boundary.finditer(text, max(0, m.start() - 80), m.start())), default=max(0, m.start() - 80)
    )
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


# turn labels left inside a turn ("J: -pues", "E: ¿cómo?", "LMP: -si", "G.: hasta luego")
speaker_label = re.compile(r"(?<!\w)[A-ZÁÉÍÓÚÑ]{1,3}\.?\s?:\s*-?\s*")
turn_label = re.compile(r"(?<!\w)([A-ZÁÉÍÓÚÑ]{1,3})\.?\s?:")
turn_question = re.compile(r"[^?\n]*?\?(?:[\s,.]{0,3}¿[^?\n]*\?)*")
# transcribers also mark a third voice inside the participant's turn: "F: -(tercera voz) sigue"
third_voice = re.compile(r"\s*\S*?tercera voz")


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


def strip_speaker_labels(text):
    return speaker_label.sub("", text)


def clean_turns(text):
    """clean_turns drops labeled interviewer and third-voice turns, unlabeled interviewer speech, then the participant's own labels."""
    return strip_speaker_labels(remove_interviewer(remove_other_turns(text)))


def convert_doc_docx(input_folder, output_folder):
    # Create the output folder if it doesn't exist
    os.makedirs(output_folder, exist_ok=True)

    # Loop through all files in the input folder
    for filename in os.listdir(input_folder):
        if filename.endswith(".doc"):
            doc_path = os.path.join(input_folder, filename)
            # Use LibreOffice to convert .doc to .docx
            subprocess.run(
                ["libreoffice", "--headless", "--convert-to", "docx", doc_path, "--outdir", output_folder], check=True
            )


def clean_data(input_folder, output_folder):
    # Ensure the output folder exists
    os.makedirs(output_folder, exist_ok=True)

    # Step 1: Convert DOCX files to TXT and process them
    for filename in os.listdir(input_folder):
        if filename.endswith(".docx"):
            docx_path = os.path.join(input_folder, filename)
            txt_file = os.path.splitext(filename)[0] + ".txt"
            txt_path = os.path.join(output_folder, txt_file)

            # Convert DOCX to TXT
            doc = Document(docx_path)
            # Extract text from paragraphs
            text_content = [paragraph.text for paragraph in doc.paragraphs]
            # Combine paragraphs into a single string with formatted punctuation
            full_text = "\n".join(text_content).replace("/", ",").replace(",,", ",")
            # Write the text to a TXT file
            with open(txt_path, "w", encoding="utf-8") as txt_file:
                txt_file.write(full_text)

            # Step 2: Clean the content of the newly created TXT file
            with open(txt_path, "r", encoding="utf-8") as infile:
                content = infile.read()

            # Remove text based on conditions
            content = re.sub(
                r"\(.*?\)\s*"  # parentheses + space
                r"|[•·]",  # stray punctuation
                "",
                content,
                flags=re.DOTALL,
            )

            BXlist = ["21"]

            if any(filename.startswith(num) for num in BXlist):
                # Extract all sequences that start with A: and end with X:
                filtered_sequences = re.findall(r"B:\s*(.*?)\s*[A-Z]:", content, flags=re.DOTALL)
            else:
                # Extract all sequences that start with B: and end with X:
                filtered_sequences = re.findall(r"A:\s*(.*?)\s*[A-Z]:", content, flags=re.DOTALL)

            # Join into one string (not line-based anymore, unless you want separators)
            modified_content = clean_turns("\n".join(filtered_sequences))
            modified_content = modified_content.replace(":", "")
            modified_content = re.sub(r"\bA\s+", "", modified_content)

            # Write the cleaned content back to the output file
            with open(txt_path, "w", encoding="utf-8") as outfile:
                outfile.write(modified_content)

    print("Successfully cleaned data")


# NOTE: COMMENT FOR IF YOU DONT WANT TO REMOVE FIRST 350 WORDS
def remove_text(input_folder, num_words_to_remove):

    # Ensure the input folder exists
    os.makedirs(input_folder, exist_ok=True)

    for filename in os.listdir(input_folder):
        if filename.endswith(".txt"):
            txt_path = os.path.join(input_folder, filename)

            with open(txt_path, "r", encoding="utf-8") as infile:
                content = infile.read()

            word_count = 0
            result_lines = []

            for line in content.splitlines(keepends=True):  # keep \n at end
                words = line.split()

                if word_count < num_words_to_remove:
                    # skip words until we’ve removed enough
                    remaining = []
                    for w in words:
                        if word_count < num_words_to_remove:
                            word_count += 1
                            continue
                        remaining.append(w)
                    if remaining:
                        result_lines.append(" ".join(remaining) + ("\n" if line.endswith("\n") else ""))
                else:
                    result_lines.append(line)

            final_content = "".join(result_lines)

            with open(txt_path, "w", encoding="utf-8") as outfile:
                outfile.write(final_content)

    print(f"Successfully deleted {num_words_to_remove} words from each file")


if __name__ == "__main__":
    clean_data("data/original", "data/text")
    remove_text("data/text", 350)
