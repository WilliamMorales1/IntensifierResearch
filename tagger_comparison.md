# TagAnt vs Stanza accuracy

Data: 314 transcripts, same text, tagged once by TagAnt (`tagged/`) and once by Stanza (`stanza_tagged/`). Neither tagger is treated as gold. Disagreements were hand-judged.

Reproduce the token comparison with `python compare_taggers.py --stanza stanza_corrected` (writes `tagger_disagreements.tsv`).

## Stanza bug found and fixed

Stanza split turn-final words that had no closing punctuation: *casero* -> *caser* + *o* (CCONJ), *sabroso* -> *sabros* + *o*, *peligroso* -> *peligros* (NOUN) + *o*. 340 sentence-final tokens hit (118 adjectives), which put garbage like *muy caser*, *muy chéver*, *muy sabros* into the extraction.

Fix in `step_7_stanza_to_csv.py`: `join_paragraphs` adds a temporary period to every paragraph without final punctuation, and `tag_doc` drops that period from the output so segments still match the TagAnt pipeline. The period also changes nearby tags (e.g. *muy peligroso* NOUN -> ADJ).

Retagged all 314 files with the fix into `stanza_tagged/` (old buggy tags deleted 2026-10-30). Split garbage (*caser*, *chéver*, *sabros*, *peligros* as ADJ) gone from the extraction (15 rows -> 0). Remaining *peligros* tokens are the real plural noun.

## Rule corrections

`correct_tokens` in `step_7_stanza_to_csv.py` fixes Stanza's closed error list after tagging. Raw tags stay in the tagged folder; corrected copies go to `stanza_corrected/`, which the extraction reads.

| rule | why |
|---|---|
| intensifier + *poco* PRON -> ADV | *muy poco* is adverbial (TagAnt was right) |
| intensifier + *solo* ADV -> ADJ, except after *mucho* | *es muy solo* = lonely; *mucho solo el saludo* = only |
| capitalized *San/Santa/Santo* ADJ -> PROPN | place names (*Santa Rita*, *Santo Domingo*) |
| *bueno/claro* ADJ, clause-initial before a pause or *que* -> INTJ | discourse markers (*bueno, ...*, *claro que sí*) |
| participle ADJ with verb lemma -> adjective lemma | *dado* -> *dar* was wrong for Lex_Adj |
| lemma *chéver* -> *chévere* | plural *chéveres* over-stripped |
| *bueno/claro* ADJ after PUNCT/CCONJ/INTJ/*sí/pues/porque/no/y/o/pero* -> INTJ, unless before a noun or after an intensifier | *pero bueno eso*, *. Bueno ahora* are discourse markers |
| *mejor/peor* ADJ -> ADV, kept ADJ after DET/NOUN/AUX/predicative verb/*lo*; *dicho* after *mejor* -> VERB *decir* | *mejor dicho*, *a lo mejor*, *mejor me voy*, *vive mejor* |
| *igual* ADJ -> ADV, kept ADJ before a noun or *a/de/en*, after DET/AUX/predicative verb/intensifier | *pero igual se fue* = anyway |
| possessive *mío/mía/tuyo/suyo/nuestro* ADJ -> DET | not gradable adjectives |
| *mucho* + noun tagged ADJ -> NOUN when *mucho* is DET or follows *haber*; comparatives excluded | *hay mucho venezolano*, *mucho extranjero* |

Checked against TagAnt by hand on samples: the *mejor/peor* rule flips 247 tokens TagAnt also calls ADV and 41 TagAnt calls ADJ (mostly TagAnt wrong); *igual* flips 257 + 256 (TagAnt ADJ ones are mostly *pero igual* = anyway); *bueno/claro* flips ~830, nearly all discourse.

*mucho donde* is handled in the extraction (both taggers), not here: Stanza's ADV is the right POS.

Still wrong, no rule: *mucho* + ADJ after a copula (*es mucho frío*, *era mucho chusco*), left alone since it may be dialectal intensifier *mucho*. *pocos/pocas/poca* PRON/DET after an intensifier are verified correct quantifiers (*muy pocos amigos*); TagAnt's 6 ADJ there are wrong.

## After fix and rules

Host decision after an intensifier, Stanza vs TagAnt:

| | before fix | fix only | fix + first 6 rules | fix + all rules |
|---|---|---|---|---|
| tokens after an intensifier | 22,230 | 22,309 | 22,309 | 22,309 |
| host decision differs | 616 | 617 | 478 | 476 |
| same UPOS (all tokens) | 94.5% | 94.5% | 94.6% | 94.5% |

The later rules barely move agreement: they mostly retag tokens TagAnt also gets wrong (*mejor*, *igual*, *bueno* as ADJ), so Stanza moves away from TagAnt as often as toward it. Remaining host disagreements (all rules): TagAnt none / Stanza ADJ 266, none / ADV 62, ADJ / none 88, ADJ / ADV 16, ADV / none 19, ADV / ADJ 25.

Spot-check of the new disagreements: the *poco* rule flips 24 tokens where TagAnt says PRON; all sampled are adverbial (*lo vemos muy poco*, *se bañan muy poco*). The 10 *poco* left (TagAnt ADV, Stanza DET) are *muy poco trabajo/tránsito/tiempo*, where Stanza is right.

Extraction before the split fix (`intensifier_data_stanza_2026-10-29`) vs after fix, `correct_tokens` and the extraction rules below (`intensifier_data_stanza_2026-10-30`), with final TagAnt for reference. Word counts use Lex_Adj on adjective rows.

| | Stanza before | Stanza after | TagAnt after |
|---|---|---|---|
| rows | 124,715 | 120,431 | 120,574 |
| intensified rows | 9,940 | 9,358 | 9,162 |
| adjective rows | 59,725 | 55,010 | 58,835 |
| adjective rows intensified | 15.13% | 16.11% | 14.75% |
| *muy poco* Adv rows | 6 | 162 | 148 |
| *solo* intensified Adj rows | 14 | 32 | 27 |
| *bueno* / *claro* Adj rows | 5,892 / 1,153 | 4,013 / 331 | 5,526 / 423 |
| *san/santa/santo* Adj rows | 860 | 123 | 66 |
| *igual* Adj rows | 888 | 372 | 602 |
| possessive Adj rows (*mío*, *suyo*, ...) | 257 | 0 | 155 |
| Lex_Adj ending in -ar/-er/-ir | 1,344 | 668 | 770 |
| *mucho más/menos/mejor/...* rows | 303 | 0 | 0 |
| *casi siempre/nunca* rows | 143 | 0 | 0 |

Intensified rows fall because the extraction rules drop fixed expressions, non-gradable Adv hosts and disfluency fragments. The adjective rate still rises 1 pp, because false bare adjectives (*bueno*, *claro*, *Santa*, *igual*, possessives) left the denominator.

## Extraction rules (both taggers)

`step_7_tagged_to_csv.py`, shared by both pipelines (2026-10-30):

| problem | fix |
|---|---|
| fixed expressions: *bien hecho*, *mucho más/mas/menos/mejor/peor/mayor/menor* | row dropped |
| non-gradable Adv hosts: *casi siempre/nunca*, *mucho también/ya/entonces/antes*, *bien ya*, *mucho/bastante donde*, sentence adverbs | intensified row dropped, bare row kept |
| *más bien* + host | host kept, Int `/` |
| disfluency fragments (*muy bue muy bueno*, *muy d muy rápido*) | host <= 2 chars (except *ya/sí/ni*), or <= 4 chars and a prefix of a word in the next 4 tokens; row dropped |
| -a -> -o on feminine lemma (*acogedora* -> *acogedoro*) | lemmas in -dora/-tora/-sora drop the -a |
| *muchísima/os* ADJ (TagAnt), *muchísimo* ADV | row dropped |

Comparatives are still kept as bare hosts. Known residue: 4 Stanza *muy bue* rows with no restart to match; 30 TagAnt *acogedoro* rows where TagAnt's own lemma is *acogedoro*.

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

Share of adjective rows intensified, by group, from `intensifier_data_2026-10-30` (TagAnt) and `intensifier_data_stanza_2026-10-30` (Stanza), both with all fixes. Last column is the gap before any fix.

| group | TagAnt | Stanza | diff (pp) | diff before fix |
|---|---|---|---|---|
| hombre | 13.68 | 14.99 | +1.31 | +0.17 |
| mujer | 16.00 | 17.42 | +1.42 | +0.01 |
| Edu alto | 14.89 | 16.04 | +1.15 | +0.07 |
| Edu bajo | 14.34 | 15.93 | +1.58 | +0.04 |
| Edu medio | 14.87 | 16.30 | +1.43 | +0.16 |
| Cali | 14.57 | 15.87 | +1.30 | +0.11 |
| Cartagena | 7.59 | 8.38 | +0.80 | -0.30 |
| LA Puerto Ricans | 11.05 | 12.55 | +1.49 | +1.25 |
| Medellín | 18.63 | 20.03 | +1.40 | +0.20 |
| Tunja | 14.61 | 16.27 | +1.66 | +0.32 |
| all | 14.75 | 16.11 | +1.36 | |

Stanza is now ~1.4 pp higher everywhere: its rules removed false bare adjectives (*bueno*, *claro*, *igual*, possessives) that TagAnt still counts. The shift is near uniform, so group gaps barely change (largest: Cartagena, 0.56 pp below the mean shift). Only order flip: Edu alto vs medio, 0.02 pp apart in TagAnt.

Per-speaker rate correlation 0.989 (before 0.987), mean absolute gap 1.35 pp (before 0.83, the uniform shift), worst speaker 5.44 pp (LAPR_M05_1991m_2013; before 6.7). Int shares move under 0.2 pp (*muy* 82.6% both). Adj_type split moves more: ambiguous 43.6% TagAnt vs 38.8% Stanza, attributive 35.7 vs 39.0, predicative 20.7 vs 22.3.

Before the rules, the one real gap was LA Puerto Ricans (+1.25 pp vs ~0.1 elsewhere). After them it is in line with the uniform shift. TagAnt reads lateralized /r/ verbs as adjectives (*estal* 32, *hacel* 18, *impolta* 15, *recueldo* 9, *estudial* 8, *quedal*, *contal*), padding the bare-adjective count and pushing the PR rate down. Stanza handles *fuelte*, *celca*, *polque* better. That is a dialect-correlated error, the kind that biases a variationist comparison, and it favors Stanza for that corpus.

## Shared pipeline problems (both taggers)

Found during the comparison, all fixed by the extraction rules above (2026-10-30):

- Non-gradable Adv hosts: *mucho más* 221, *casi siempre* 120, *casi nunca* 37, *también*, *ya*, *entonces*, *más bien* (*bien* is not an intensifier there).
- Disfluency fragments after an intensifier (*muy d muy rápido*, *muy bue*, *muy ca era muy calmado*) became rows in whichever tagger made them ADJ/ADV.
- *-ísimo* on quantifiers: TagAnt made *muchísima/muchísimos* ADJ, giving 41 `-ísimo` + *mucho* rows; Stanza calls them DET/PRON.

Still open: *-ísimo* on ADV hosts (*lejísimos*, *cerquísima*) counts as unintensified. The adverb envelope is mostly non-gradable bare adverbs (*ya*, *más*, *entonces*).

## Verdict

Overall accuracy is a draw; neither is clearly better. Group-level results barely move except for the Puerto Rican corpus, where TagAnt is biased. Stanza's remaining errors are concentrated and rule-fixable (*poco*, *solo*, *donde*, *claro*, *san/santa*, participle lemmas); TagAnt's are scattered and include dialectal adjectives it does not know. Recommendation: use Stanza (with the split fix) plus small rules for its closed error list, and keep spot-checking. With all rules applied, Stanza's adjective rate sits ~1.4 pp above TagAnt in every group because TagAnt's false bare adjectives stay in its denominator; group comparisons are unaffected.
