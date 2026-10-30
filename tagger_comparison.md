# TagAnt vs Stanza accuracy

Data: 314 transcripts, same text, tagged once by TagAnt (`tagged/`) and once by Stanza (`stanza_tagged/`). Neither tagger is treated as gold. Disagreements were hand-judged.

Reproduce the token comparison with `python compare_taggers.py` (writes `tagger_disagreements.tsv`).

## Stanza bug found and fixed

Stanza split turn-final words that had no closing punctuation: *casero* -> *caser* + *o* (CCONJ), *sabroso* -> *sabros* + *o*, *peligroso* -> *peligros* (NOUN) + *o*. 340 sentence-final tokens hit (118 adjectives), which put garbage like *muy caser*, *muy chéver*, *muy sabros* into the extraction.

Fix in `step_7_stanza_to_csv.py`: `join_paragraphs` adds a temporary period to every paragraph without final punctuation, and `tag_doc` drops that period from the output so segments still match the TagAnt pipeline. The period also changes nearby tags (e.g. *muy peligroso* NOUN -> ADJ).

POST_FIX_SECTION

## Token-level agreement (before fix)

| | |
|---|---|
| TagAnt tokens | 1,714,334 |
| aligned to Stanza (same word) | 1,694,693 (98.9%) |
| same UPOS | 94.5% |
| same UPOS right after an intensifier | 95.6% |

Biggest confusions (TagAnt -> Stanza): AUX->VERB 15k, ADV->PRON 5.5k, PROPN->NOUN 5.4k, DET->PRON 5.2k, ADJ->NOUN 4.1k, NOUN->ADJ 2.4k. Most are label-convention differences (UD vs TagAnt's model) that the extraction never reads.

## Extraction totals (before fix)

| | TagAnt | Stanza |
|---|---|---|
| rows | 121,528 | 124,715 |
| intensified rows | 9,894 | 9,940 |
| intensified rows found by both | 9,464 | 9,464 |
| only this tagger | 430 | 476 |

## Hand judgment: host after an intensifier

All 652 tokens where an intensifier is followed by a word one tagger makes a host (ADJ/ADV) and the other does not, or ADJ vs ADV differ. Judged by type (324 types). Question asked: should this be extracted, and with what POS?

| right | tokens |
|---|---|
| TagAnt | 311 |
| Stanza | 312 |
| ambiguous | 29 |

Tie in count, very different shape:

- TagAnt wins are a few systematic words. *muy poco* (153 tokens, Stanza PRON; ~27/30 sampled are adverbial, so TagAnt right). *mucho donde* (25, "hay mucho donde divertirse": Stanza's ADV is correct POS but yields a bogus *mucho + donde* row). *muy solo* (13, "es muy solo" = lonely, Stanza ADV). *mucho* + noun (*mucho costeño*, *mucho venezolano*, *mucho frío*), where Stanza calls the noun ADJ.
- Stanza wins are spread over ~150 adjective types TagAnt calls NOUN/VERB/PROPN, mostly dialectal and participial: *maluco*, *amiguera*, *aburridor*, *rumbero*, *berraco*, *chévere/chevere*, *viejito*, *contaminado*, *amañado*, *complicao*, *contenta*, *celca*, *fuelte*. These are exactly the lexical variety a sociolinguistic study cares about.
- TagAnt-style errors are open-ended; Stanza's are mostly a closed list (*poco/poca*, *solo*, *donde/dónde*) that a rule could fix.

## Hand judgment: bare adjectives (the envelope)

12,775 non-intensified tokens where only one tagger says ADJ. Random sample of 100 (seed 42), judged: is it really an adjective?

| right | of 100 |
|---|---|
| TagAnt | 49 |
| Stanza | 46 |
| ambiguous | 5 |

When a tagger is the only one calling something ADJ it is usually wrong: TagAnt-only ADJ correct 8/53, Stanza-only ADJ correct 6/47. Both inflate the denominator about equally.

Stanza's false ADJs concentrate: top 15 words are 48% of its ADJ-only tokens (*claro* 725, *san* 362, *bueno* 353 as discourse marker, *santa* 327, *mejor* 313, *igual* 289, *mía* 209). TagAnt's scatter: top 15 are 30% (*poquito* 380, *solo* 247, *entoes* 177, *mismo* 169, *ahorita* 152), with 2,038 types overall.

## Lemmas (Lex_Adj)

Of 52,559 tokens both tag ADJ, Lex_Adj differs on 892 (1.7%).

- 539: Stanza lemmatizes participles to the verb (*dado* -> *dar*, *sentados* -> *sentar*). Wrong for Lex_Adj.
- 88: TagAnt lemma garbage (*deliciosa* -> *delició*, *juiciosa* -> *juició*, *morena* -> *morén*, *amigables* -> *amigabl*).
- 90: the pipeline's own -a -> -o step turns *acogedor/colaborador* into *acogedoro/colaboradoro* (TagAnt lemma is feminine). Pipeline bug, affects TagAnt only.

## Does it change results?

Share of adjective tokens intensified, by group (before fix):

| group | TagAnt | Stanza | diff (pp) |
|---|---|---|---|
| hombre | 13.92 | 14.09 | +0.17 |
| mujer | 16.32 | 16.33 | +0.01 |
| Edu alto | 15.11 | 15.18 | +0.07 |
| Edu bajo | 14.68 | 14.72 | +0.04 |
| Edu medio | 15.17 | 15.33 | +0.16 |
| Cali | 14.81 | 14.92 | +0.11 |
| Cartagena | 7.68 | 7.38 | -0.30 |
| LA Puerto Ricans | 11.18 | 12.43 | +1.25 |
| Medellín | 19.08 | 19.28 | +0.20 |
| Tunja | 14.80 | 15.12 | +0.32 |

Per-speaker rate correlation 0.987, mean absolute gap 0.83 pp, worst speaker 6.7 pp. Int shares and predicative/attributive split move under 0.5 pp.

The one real gap is LA Puerto Ricans. TagAnt reads lateralized /r/ verbs as adjectives (*estal* 32, *hacel* 18, *impolta* 15, *recueldo* 9, *estudial* 8, *quedal*, *contal*), padding the bare-adjective count and pushing the PR rate down. Stanza handles *fuelte*, *celca*, *polque* better. That is a dialect-correlated error, the kind that biases a variationist comparison, and it favors Stanza for that corpus.

## Shared pipeline problems (both taggers)

Not tagger accuracy, but they show up in every comparison:

- Non-gradable Adv hosts: *mucho más* 221, *casi siempre* 120, *casi nunca* 37, *también*, *ya*, *entonces*, *más bien* (*bien* is not an intensifier there).
- Disfluency fragments after an intensifier (*muy d muy rápido*, *muy bue*, *muy ca era muy calmado*) become rows in whichever tagger makes them ADJ/ADV.
- *-ísimo* on quantifiers: TagAnt makes *muchísima/muchísimos* ADJ, giving 41 `-ísimo` + *mucho* rows; Stanza calls them DET/PRON.

## Verdict

Overall accuracy is a draw; neither is clearly better. Group-level results barely move except for the Puerto Rican corpus, where TagAnt is biased. Stanza's remaining errors are concentrated and rule-fixable (*poco*, *solo*, *donde*, *claro*, *san/santa*, participle lemmas); TagAnt's are scattered and include dialectal adjectives it does not know. Recommendation: use Stanza (with the split fix) plus small rules for its closed error list, and keep spot-checking.
