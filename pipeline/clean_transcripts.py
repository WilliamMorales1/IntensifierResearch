# cleans the raw docx transcripts into participant-only text: labeled interviewer and third-voice turns and labels removed

import argparse
import os
import re
import subprocess
from collections import Counter

from docx import Document

# "E.", "E..", "E:", "e:" and "E ¿" open an interviewer line; lowercase "e ¿" and "e." are the filler "eh"
label_line = re.compile(r"^\s*(E\.+:?|E:|e:|E(?=\s*¿))")
# the participant's own line labels ("I..", "i:", "i.:", "B.") are dropped, the words kept
informant_label = re.compile(r"^\s*([A-DF-Z]\.+:?|i\.?:|I:)\s*")


def interviewer_spans(text):
    """interviewer_spans returns the character spans of labeled interviewer lines and participant line labels."""
    # only a speaker label marks the interviewer; unlabeled questions can be the participant's own
    if text.count("\n") < 10:
        return []
    spans, pos = [], 0
    for line in text.split("\n"):
        end = pos + len(line)
        if label_line.match(line):
            spans.append((pos, end))
        elif m := informant_label.match(line):
            spans.append((pos, pos + m.end()))
        pos = end + 1
    return spans


def remove_interviewer(text):
    out, pos = [], 0
    for start, end in interviewer_spans(text):
        out.append(text[pos:start])
        pos = end
    out.append(text[pos:])
    return "".join(out)


# turn labels left inside a turn ("J: -pues", "E: ¿cómo?", "LMP: -si", "G.: hasta luego")
speaker_label = re.compile(r"(?<!\w)[A-ZÁÉÍÓÚÑ]{1,3}\.?\s?:\s*-?\s*")
turn_label = re.compile(r"(?<!\w)([A-ZÁÉÍÓÚÑ]{1,3})\.?\s?:")
turn_question = re.compile(r"[^?\n]*?\?(?:[\s,.]{0,3}¿[^?\n]*\?)*")
# transcribers also mark a third voice inside the participant's turn: "F: -(tercera voz) sigue"
third_voice = re.compile(r"\s*\S*?tercera voz")


def remove_other_turns(text):
    """remove_other_turns drops every labeled turn not spoken by the participant (interviewer, third voices)."""
    matches = list(turn_label.finditer(text))
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
        q = turn_question.match(text, m.end(), end) if inline else None
        if q:
            end = min(end, q.end())
        out.append(text[pos : m.start()])
        pos = end
    out.append(text[pos:])
    return "".join(out)


def strip_speaker_labels(text):
    return speaker_label.sub("", text)


def clean_turns(text):
    """clean_turns drops labeled interviewer and third-voice turns, then the participant's own labels."""
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


def drop_asides(text):
    return re.sub(
        r"\(.*?\)\s*"  # parentheses + space
        r"|[•·]",  # stray punctuation
        "",
        text,
        flags=re.DOTALL,
    )


def read_docx(path):
    """read_docx returns the paragraphs of a docx plus its table cells, skipping line-number columns."""
    doc = Document(path)
    paragraphs = [paragraph.text for paragraph in doc.paragraphs]
    # Tunja generation 2 and 3 put the whole dialogue in a table next to a column of line numbers
    for table in doc.tables:
        for row in table.rows:
            paragraphs += [cell.text for cell in row.cells if not re.fullmatch(r"[\d\s]*", cell.text)]
    return "\n".join(paragraphs)


section_start = re.compile(r"^(?:Hombre|Mujer) de \d+ años", re.MULTILINE)
informant_number = re.compile(r"informante N[º°o]\.?\s*(\d+)", re.IGNORECASE)


def informant_section(text, filename):
    """informant_section keeps only the interview whose informant number is in filename when a docx compiles several."""
    starts = [m.start() for m in section_start.finditer(text)]
    if len(starts) < 2 or not (m := re.search(r"\d+", filename)):
        return text
    for start, end in zip(starts, starts[1:] + [len(text)]):
        if (n := informant_number.search(text, start, end)) and int(n[1]) == int(m[0]):
            return text[start:end]
    return text


def cartagena_turns(content):
    """cartagena_turns returns the turns of whichever of A and B speaks more, the informant."""
    turns = {label: re.findall(label + r":\s*(.*?)\s*[A-Z]:", content, flags=re.DOTALL) for label in "AB"}
    return max(turns.values(), key=lambda t: sum(len(turn.split()) for turn in t))


# PRESEEA transcripts (Medellín, Cali, Tunja) open with an XML header giving each speaker's label
speaker_code = re.compile(r"c[oó]digo_hab\s*=\s*[\"“”]?\s*([A-Z]\w{0,2})")
legend_line = re.compile(
    r"^\s*[A-Z]\d?\s*:\s*(?:Entrevistador|Informante|Audiencia)\w*\s*$", re.MULTILINE | re.IGNORECASE
)


def preseea_turns(text):
    """preseea_turns returns the informant's ("I") turns of a PRESEEA transcript, markup removed."""
    codes = set(speaker_code.findall(text)) | {"E", "I"}
    header_end = text.find("\n", max(m.end() for m in speaker_code.finditer(text)))
    text = legend_line.sub("", text[header_end:])
    alt = "|".join(sorted(codes, key=len, reverse=True))
    # "E:", "I.:", "e:" and Tunja's colon-less "E." open a line; mid-line turns always have the colon
    label = re.compile(rf"^[ \t]*(?:(?i:{alt})\.*[ \t]*:|(?:{alt})\.+(?=\s))|(?<=\s)(?:{alt})\.?:")
    turns, speaker, asked = [], None, False
    for line in text.split("\n"):
        labels = list(label.finditer(line))
        # an unlabeled line right after the interviewer's question is the informant's answer with its label missing
        if not labels and speaker == "E" and asked and line.strip():
            speaker = "I"
            turns.append("")
        pos = 0
        for m in labels:
            if speaker == "I":
                turns[-1] += " " + line[pos : m.start()]
            speaker, pos = re.match(r"\s*([A-Za-z]\w?)", m[0])[1].upper(), m.end()
            if speaker == "I":
                turns.append("")
        if speaker == "I":
            turns[-1] += " " + line[pos:]
        if line.strip():
            asked = re.sub(r"<[^>]*>", "", line).rstrip().endswith("?")
    # unclosed "<" marks and "====" rules are left over once the tags are gone
    turns = [" ".join(re.sub(r"[<>]|={2,}", "", re.sub(r"<[^>]*>", "", t)).split()) for t in turns]
    # "/" is a short pause and "//" a long one
    turns = [re.sub(r"\s*/\s*", ", ", re.sub(r"\s*//+\s*", ". ", t)).strip(" ,") for t in turns]
    return [t for t in turns if t]


def clean_data(input_folder, output_folder):
    # Ensure the output folder exists
    os.makedirs(output_folder, exist_ok=True)

    written = []
    for filename in os.listdir(input_folder):
        if filename.endswith(".docx"):
            docx_path = os.path.join(input_folder, filename)
            txt_path = os.path.join(output_folder, os.path.splitext(filename)[0] + ".txt")

            content = informant_section(read_docx(docx_path), filename)
            if speaker_code.search(content):
                turns = [drop_asides(t).strip() for t in preseea_turns(content)]
            else:
                turns = cartagena_turns(drop_asides(content.replace("/", ",").replace(",,", ",")))

            modified_content = clean_turns("\n".join(turns))
            modified_content = modified_content.replace(":", "")

            with open(txt_path, "w", encoding="utf-8") as outfile:
                outfile.write(modified_content)
            written.append(os.path.basename(txt_path))

    print("Successfully cleaned data")
    return written


# median informant words before the 5:00 and 10:00 stamps in the time-stamped MEDE/TCali files (512, 1,122), used for
# every file since Tunja and Cartagena have no stamps; PRESEEA guides start at minute 5 or 10
start_words = {5: 510, 10: 1120}


def remove_text(input_folder, num_words_to_remove, filenames=None):

    # Ensure the input folder exists
    os.makedirs(input_folder, exist_ok=True)

    # texts without an original (LAPR) were trimmed when first cleaned; trimming again would cut more
    for filename in filenames if filenames is not None else os.listdir(input_folder):
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
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/original", help="folder of .docx transcripts")
    parser.add_argument("--output", default="data/text", help="where the cleaned .txt files go")
    parser.add_argument(
        "--start-minute",
        type=int,
        choices=sorted(start_words),
        default=10,
        help="interview minute analysis starts at, as informant words dropped (5: 510, 10: 1,120)",
    )
    parser.add_argument("--skip-words", type=int, help="leading informant words dropped; overrides --start-minute")
    args = parser.parse_args()
    written = clean_data(args.input, args.output)
    skip = start_words[args.start_minute] if args.skip_words is None else args.skip_words
    if skip:
        remove_text(args.output, skip, written)
