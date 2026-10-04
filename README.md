# IntensifierResearch

![Tests](https://github.com/WilliamMorales1/IntensifierResearch/actions/workflows/tests.yml/badge.svg)

This is the code I used to analyze a number of Spanish transcripts for sociolinguistic research. It extracts intensifier + adjective/adverb tokens (*muy bueno*, *riquísimo*, *archiconocido*, *muy muy lejos*) from POS-tagged interviews, classifies them as predicative or attributive, and merges in speaker metadata. Results are published in [*Proceedings of the LSA* 11(1)](https://doi.org/10.3765/plsa.v11i1.6091).

Stuff you'll need: [uv](https://docs.astral.sh/uv/getting-started/installation/) (it installs Python and the dependencies for you), [LibreOffice](https://www.libreoffice.org/) if your transcripts are old `.doc` files, and [TagAnt](https://www.laurenceanthony.net/software/tagant/).

1. Clone the repo (or Code -> Download ZIP) and run `uv sync` inside it.
2. Put the original .docx transcript files in a folder called "original".
3. Create an Excel sheet called "speaker_data_CART_YYYY-MM-DD.xlsx" (with the exact same caps, punct, etc.) that you'll use to write out the information for each speaker you have. Go through each transcript and get that information (their gender, education level, age, etc.) with each row being a separate speaker.
4. Then, go through each transcript and remove everything up until the first line of actual dialogue.
5. Run `uv run step_5_clean_raw_data.py`.
6. Place the text folder into TagAnt to create a tagged version of all the files (make sure that you use the Spanish model, not the English one). For the Display Information, select "word+pos_tag+lemma".
7. Run `uv run step_7_tagged_to_csv.py`.
8. Now you have an excel sheet with all the data. You can try making some graphs of the data using [Language Variation Suite](https://languagevariationsuite.shinyapps.io/Pages/) or anything else.

If you get errors or are confused you can email me (though I might be busy) or you could try to just copypaste the error and code into ChatGPT.

## Tests

```
uv run pytest
```

The tests cover apocope and gender/number normalization, *-ísimo* and *archi-* handling, double intensifiers, negation, and predicative vs. attributive classification. Three tests are marked `xfail` because they document known bugs that would change token counts if fixed:

- ADV-tagged intensifiers (*bastante*, *mucho*, ...) and *no* get emitted as their own adverb tokens.
- The copula check is a substring match, so *es* inside *desde* marks the next adjective predicative.
