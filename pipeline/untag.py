# strips TagAnt word_POS_lemma tags so stanza gets the raw transcript text

import os
import re

upos = "ADJ|ADP|ADV|AUX|CCONJ|DET|INTJ|NOUN|NUM|PART|PRON|PROPN|PUNCT|SCONJ|SYM|VERB|X|SPACE"
tag_re = re.compile(rf"_(?:{upos})_.*$")


def untag_word(token):
    return tag_re.sub("", token)


def untag_line(line):
    words = [untag_word(t) for t in line.split()]
    text = " ".join(w for w in words if w)
    # TagAnt split punctuation into its own tokens; glue it back like the transcript had it
    text = re.sub(r" +([,.;:!?)\]])", r"\1", text)
    text = re.sub(r"([¿¡(\[]) +", r"\1", text)
    return text


def untag(input_folder, output_folder):
    os.makedirs(output_folder, exist_ok=True)
    for filename in os.listdir(input_folder):
        if not filename.endswith(".txt"):
            continue
        with open(os.path.join(input_folder, filename), encoding="utf-8") as f:
            lines = [untag_line(line) for line in f]
        with open(os.path.join(output_folder, filename), "w", encoding="utf-8") as f:
            f.write("\n".join(line for line in lines if line) + "\n")
    print(f"Untagged {input_folder} into {output_folder}")


if __name__ == "__main__":
    untag("data/tagged", "data/text")
