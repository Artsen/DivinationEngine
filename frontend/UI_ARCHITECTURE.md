# Reading workspace UI

The reading route is a single document flow: question anchor, persisted cast timeline, explicit
add-cast interaction, then notes. It deliberately has no permanent utility sidebar.

`AddCastFlow` owns only temporary form state. No cast occurs until its system-specific form is
submitted. Successful mutations invalidate the stored reading, close and reset the flow, and
return focus to its trigger. Existing deck or rune-bag sessions are an advanced option and are
described by cast order rather than exposed identifiers.

`CastTimeline` determines system presentation and marks the latest persisted cast. Tarot,
I Ching, and rune components expose reading identity and the source text most relevant to the
mechanical result first. Commentary, related traditions, source witnesses, cast mechanics, and
provenance remain in native `details` disclosures. These layers must never merge text from
different sources or traditions, and disclosure choices are presentation state only.
