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
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/original", help="folder of .docx transcripts")
    parser.add_argument("--output", default="data/text", help="where the cleaned .txt files go")
    parser.add_argument("--skip-words", type=int, default=350, help="leading words dropped from each transcript")
    args = parser.parse_args()
    clean_data(args.input, args.output)
    if args.skip_words:
        remove_text(args.output, args.skip_words)
