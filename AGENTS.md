# pstack-bob

`plugin/` is generated. Change behavior in `patches.json` (edits to upstream
text) or `overlay/` (files added beside it), then run `python3 scripts/build.py`
and commit the result with the source change.

Each `patches.json` rule names an anchor that must occur exactly once in its
upstream file, so keep anchors short and literal, and give each rule a `why`.
Prefer an `after` rule, which adds a sentence, over a `replace` rule.

Raise `VERSION` by hand for a change of ours. `scripts/build.py --ref main`
raises it when it moves the pin.
