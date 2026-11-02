# Output

`output/intensifier_data_stanza_<date>.sqlite` holds the full table. `--xlsx` and `--csv` write the same table as `.xlsx` and `.csv`. One row per adjective or adverb token, intensified or not, except comparatives, superlatives, *tan* X *como/que* and other contexts outside the envelope of variation; `--drop-invariant` keeps only hosts intensified at least once in the corpus.

| Column | Meaning |
| --- | --- |
| `Speaker` | transcript file name |
| `Phr_tagged`, `Phr` | the segment the token came from, tagged and plain |
| `Int` | intensifier (*muy*, *tan*, *súper*, *-ísimo*, *re-*, *archi-*, *más o menos*, ...) or `/` |
| `Int_type` | `maximizer`, `booster`, `approximator`, `compromiser` or `emphasizer` (Quirk et al. 1985 via Stratton & Sundquist 2022; see [rules](rules.md#intensifier-types-and-the-envelope-of-variation)), or `/`. Emphasizers count as unintensified in Stratton's method |
| `Double` | second intensifier (*muy muy*) or `/` |
| `Adj`, `Lex_Adj` | adjective host as written, and its masculine singular lemma |
| `Adv` | adverb host |
| `Adj_type` | `predicative`, `attributive` or `ambiguous` |
| `Noun` | noun the adjective modifies or describes |
| `Negation` | negator scoping over the host (*no*, *nunca*, *ni*, *tampoco*, *jamás*) or `/`; Stratton & Sundquist (2022) drop these rows, so filter `Negation = '/'` to match them |
| `Verb`, `Inf_Verb` | verb or copula tied to the host, as written and as its infinitive lemma |
| `Number` | token id within the speaker (`<Speaker>_01`, ...) |
| `Syllable` | syllables in the host |

Next to it, `<output>_re-words.txt` (only when there are any) lists hosts starting with *re-* for a hand check of the *re-* intensifier.

`/` means not applicable or not found. The SQLite file is about half the size of the csv: speakers, phrases and short words are stored once, and the `intensifier_data` view rebuilds the table.

```python
import sqlite3
import pandas as pd

df = pd.read_sql("SELECT * FROM intensifier_data", sqlite3.connect("output/intensifier_data_stanza_YYYY-MM-DD.sqlite"))
```

`Adj_type`, `Noun` and `Verb` come from the parse: `amod` is attributive with the head noun; a `cop` child or an `xcomp` (*se puso feo*, *lo veo bonito*) is predicative with the subject (or object) as Noun; Verb is the first verb, copula or auxiliary up the head chain, for adverb rows too. Noun and Verb must appear in `Phr`, else `/`.
