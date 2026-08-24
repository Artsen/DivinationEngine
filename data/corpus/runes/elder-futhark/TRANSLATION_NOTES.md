# Editorial rune-poem translation notes

## Scope and method

`editorial-translations.json` contains a newly written DivinationEngine modern-English
translation for each of the 61 historical stanzas in `rune-poems.json`. These translations
are machine-assisted editorial work, have `translation_type: project-editorial` and
`status: derived`, and are neither historical exact text nor divinatory interpretations.
The original-language stanza remains the exact-text evidence layer.

The translation process used the fixed historical witness cited by each stanza. Old English
word choices were checked against Joseph Bosworth and T. Northcote Toller's *An Anglo-Saxon
Dictionary* (1898). Old Norse choices were checked against Richard Cleasby and Gudbrand
Vigfusson's *An Icelandic-English Dictionary* (1874), with Geir T. Zoëga's *A Concise
Dictionary of Old Icelandic* (1910) as a second lexical aid. These dictionaries are registered
as translation sources on each applicable record. Dictionary content is public domain; the
Linguistics Research Center and Germanic Lexicon Project interfaces have their own site rights,
which are not claimed or copied by this corpus.

Bruce Dickins's English is not a translation source and is not bundled. It was consulted only
after the project translations existed, as a source-likeness sanity check. Phrase-level
similarity review is a guard against accidental imitation, not evidence for a translation.

The final 61-way comparison normalized punctuation and case and paired stanzas by poem order.
Its highest character-sequence ratio was 0.869 for the short, formulaic Norwegian Hagall
couplet; no pair reached 0.90. The highest-scoring pairs were manually reviewed against their
originals. Shared literal vocabulary was retained where the source constrains it, but no
Dickins wording was imported as a correction.

## Required philological spot checks

| Stanza | Editorial decision and remaining uncertainty |
| --- | --- |
| Old English Feoh | `frofor` is “comfort”; the obligation to distribute wealth and seek honor before the Lord is retained, rather than reduced to a modern rune keyword. |
| Old English Cen | `cen` is rendered “torch.” `blac` can be pale, shining, or bright; “pale” retains its contrast with `beorhtlic`. |
| Old English Eoh | `eoh` is “yew.” `hyrde fyres` stays relatively literal as “guardian of fire”; whether it refers to burning qualities or another association remains uncertain. |
| Old English Peorð | The referent of the rune name is unresolved, so `Peorð` remains untranslated. The bracketed words remain visibly editorial material inherited from the witness. |
| Old English Eolh-secg | Bosworth-Toller calls `eolh-secg` some kind of sedge. “Elk-sedge” preserves the compound without claiming a secure botanical identification; the blood-marking clause remains cautioned. |
| Old English Lagu | Although `lagu` can denote water broadly, the ship, waves, and “sea-horse” establish a maritime context, so the stanza uses “sea.” |
| Old English Ear | Context supports “grave.” The compressed ending is kept as the loss of fruits, joys, and covenants; the last noun admits nuance. |
| Norwegian Fé | `fé` is wealth/property, and the stanza's kin-strife and forest wolf remain concrete statements rather than occult correspondences. |
| Norwegian Kaun | `kaun` is a sore or ulcer. `bǫl` is rendered broadly as “suffering,” without inventing a specific cause of death. |
| Norwegian Ýr | `ýr` is yew. The second line can emphasize fierce burning or the danger of being scorched, so the note preserves both possibilities. |
| Icelandic Fé | The tide-beacon and serpent-path phrases are retained as poetic circumlocutions for gold rather than flattened into an abstract “meaning.” |
| Icelandic Kaun | The witness's bracketed supply remains bracketed in the historical layer. The English follows it but records that intervention. |
| Icelandic Lögr | `lögr` is water. Cleasby-Vigfusson identifies `glömmungr` as a kind of fish, supporting the final “fishes' land” kenning. |
| Icelandic Ýr | Cleasby-Vigfusson gives `fífa` both a literal cotton-grass sense and a poetic arrow sense. The poetic sense fits this stanza; the obscure `Fífu fárbauti` expression is not silently resolved into a confident mythic claim. |

The Icelandic tags are preserved separately from each stanza. Their modern English glosses
also remain separate because the historical tags combine a Latin headword with an Old Norse
ruler synonym; they are not silently inserted into the poem body.

## Editorial safeguards

Validation requires a one-to-one set of 61 originals and 61 editorial translations, requires
the historical witness plus appropriate public-domain dictionary references, requires a
separate English gloss for every Icelandic tag, and rejects Dickins as a translator or source.
Import and API models preserve original text, editorial English, mapping status, translation
notes, and their source identifiers in separate fields.
