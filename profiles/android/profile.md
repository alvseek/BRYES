# Android (base)

Base profile for any app running on an Android phone body. Inherited by every
`profiles/android/<app>/profile.md`.

## Terms & Vocab
- Status bar — the thin strip at the very TOP (clock, battery, wifi, signal).
- Navigation bar — the row at the very BOTTOM: Back, Home, Recents.
- Keyboard — the on-screen keyboard shown at the bottom when a text field is focused.
- Suggestion bar — the single row of words directly ABOVE the keyboard (autocorrect / word suggestions).

## Visual
- You are looking at an Android phone screen (portrait).
- CRITICAL: the Suggestion bar — the row of words directly above the keyboard — is AUTOCORRECT
  SUGGESTIONS, NOT typed text. The text that was actually typed is in the INPUT FIELD higher up
  (where the cursor is). Never report a suggestion-bar word as the field's content.
- The Navigation bar at the very bottom (Back / Home / Recents) belongs to the OS, not the app.

## Operating
- To go back one screen, use action "key" with key "Back". For the home screen, key "Home".
- The only pointer action is a tap (mapped to "click"); there is no right-click or hover.
