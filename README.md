# IntensifierResearch

![Tests](https://github.com/WilliamMorales1/IntensifierResearch/actions/workflows/tests.yml/badge.svg)

This is the code I used to analyze a number of Spanish transcripts for sociolinguistic research. It extracts intensifier + adjective/adverb tokens (*muy bueno*, *riquísimo*, *archiconocido*, *muy muy lejos*) from POS-tagged interviews, classifies them as predicative or attributive, and merges in speaker metadata. Results are published in [*Proceedings of the LSA* 11(1)](https://doi.org/10.3765/plsa.v11i1.6091).

Stuff you'll need: [Miniforge](https://github.com/conda-forge/miniforge) (conda; it installs Python and the dependencies for you), [LibreOffice](https://www.libreoffice.org/) if your transcripts are old `.doc` files, and [TagAnt](https://www.laurenceanthony.net/software/tagant/).

1. Clone the repo (or Code -> Download ZIP) and run `conda env create -f environment.yml` inside it, then `conda activate intensifier-research`.
2. Put the original .docx transcript files in a folder called "original".
3. Create an Excel sheet called "speaker_data_CART_YYYY-MM-DD.xlsx" (with the exact same caps, punct, etc.) that you'll use to write out the information for each speaker you have. Go through each transcript and get that information (their gender, education level, age, etc.) with each row being a separate speaker.
4. Then, go through each transcript and remove everything up until the first line of actual dialogue.
5. Run `python step_5_clean_raw_data.py`.
6. Place the text folder into TagAnt to create a tagged version of all the files (make sure that you use the Spanish model, not the English one). For the Display Information, select "word+pos_tag+lemma".
7. Run `python step_7_tagged_to_csv.py`.
8. Now you have an excel sheet with all the data, plus a `.sqlite` copy of the same data. You can try making some graphs of the data using [Language Variation Suite](https://languagevariationsuite.shinyapps.io/Pages/) or anything else.

The SQLite file is about half the size of the CSV and stores each speaker, phrase and word once. To get the full table back in pandas:

```python
import sqlite3
import pandas as pd

df = pd.read_sql("SELECT * FROM intensifier_data", sqlite3.connect("intensifier_data_YYYY-MM-DD.sqlite"))
```

### Using Stanza instead of TagAnt

You can skip TagAnt (steps 6 and 7) and let [Stanza](https://stanfordnlp.github.io/stanza/) tag the text instead:

```
python step_7_stanza_to_csv.py
```

It reads the raw transcripts in `text`, saves the Stanza tags to `stanza_tagged` (so a rerun only tags new files), fixes a closed list of known Stanza errors (discourse *bueno*/*claro*, *muy poco*, *San*/*Santa*, participle lemmas, ...) into a copy in `stanza_corrected` (change it with `--corrected`), dependency-parses that copy into `stanza_parsed` (`--parsed`, also resumable; about 2 hours for all files on a laptop) and writes `intensifier_data_stanza_YYYY-MM-DD.xlsx`/`.sqlite` with the same columns as step 7. The raw tags in `stanza_tagged` are never edited.

Unlike the TagAnt pipeline, which guesses from word order (the noun right next to the adjective, the verb closest in characters), the Stanza pipeline reads Adj_type, Noun, Verb and Inf_Verb from the parse: an adjective is attributive when it modifies a noun (`amod`), predicative when it has a copula or is a secondary predicate (*se puso feo*, *lo veo bonito*), and Noun is then the subject (or object) it describes, if that is a noun and appears in Phr. Verb is the verb or copula heading the host's clause, for adverb rows too, if it appears in Phr. The intensifier itself is still the word right before the host, as in the TagAnt pipeline. See `tagger_comparison.md` for why each correction exists. The first run downloads the Spanish models (~130 MB). If you only have TagAnt output, `python step_6_untag.py` turns `tagged` back into raw text in `text` first.

If you get errors or are confused you can email me (though I might be busy) or you could try to just copypaste the error and code into ChatGPT.

## Tests

```
conda activate intensifier-research
pytest
```

The tests cover apocope and gender/number normalization, *-ísimo* and *archi-* handling, double intensifiers, negation, and predicative vs. attributive classification.

## Changes

October 2026: fixed three extraction bugs. Spreadsheets made before this (including the data behind the *Proc. LSA* paper) used the old behavior.

- ADV-tagged intensifiers (*bastante*, *mucho*, *casi*, ...) and *no* were emitted as their own adverb tokens.
- Copula detection was a substring match, so *es* inside *desde* marked the next adjective predicative. It now matches whole words or the *estar*/*ser*/*parecer* lemma.
- Turn labels left inside transcripts (*J: -pues*, *E: ¿cómo?*) and the labeled turns of the interviewer, relatives and third voices are removed in step 5 and ignored by step 7. Unlabeled interviewer questions are detected by `interviewer.py` (questions addressed to the participant, with their run and lead-in); the participant echoing a question is kept.
- Later in October 2026: fixed expressions (*bien hecho*, *mucho más/menos/mejor/peor/mayor/menor*), non-gradable adverb hosts (*casi siempre*, *mucho también*, *mucho donde*) and disfluency fragments (*muy bue muy bueno*) are dropped; *más bien* no longer counts *bien* as an intensifier; *acogedora* no longer becomes *acogedoro*.
- Noun detection checked for intensifiers by substring, so *re* inside *padre* made *padre rico* "ambiguous" instead of attributive.
