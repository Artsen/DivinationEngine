# Reading workspace UI

The reading route is a single document flow: question anchor, persisted cast timeline, explicit
add-cast interaction, then notes. It deliberately has no permanent utility sidebar.

`AddCastFlow` owns only temporary form state. No cast occurs until its system-specific form is
submitted. Successful mutations invalidate the stored reading, close and reset the flow, and
return focus to its trigger. Existing deck or rune-bag sessions are an advanced option and are
described by cast order rather than exposed identifiers.

Tarot and rune flows progressively reveal a spread selector. Selecting a named spread derives
the draw count from its ordered positions; choosing an unstructured draw retains the explicit
count control. The `/spreads` workspace groups immutable project-provided layouts separately from
custom layouts and provides ordinary form controls plus keyboard-accessible move up/down actions.
It intentionally avoids canvas and drag-and-drop dependencies.

`CastTimeline` determines system presentation and marks the latest persisted cast. Tarot,
I Ching, and rune components expose reading identity and the source text most relevant to the
mechanical result first. Commentary, related traditions, source witnesses, cast mechanics, and
provenance remain in native `details` disclosures. These layers must never merge text from
different sources or traditions, and disclosure choices are presentation state only.

Placed results put the snapshotted position label and purpose ahead of symbol identity. Linear
layouts use a responsive CSS grid on wide screens and sequence-order stacking on narrow screens;
unstructured results retain the original card grid/scroller. Persisted coordinates are normalized
`0..1` values for portable future layout renderers, not raw pixels. Built-in and rune layout copy
always identifies project-provided layouts as modern editorial structure rather than historical
evidence.
