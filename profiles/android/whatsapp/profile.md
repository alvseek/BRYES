# WhatsApp (Android)

Profile for the WhatsApp app on an Android phone. Inherits `profiles/android/profile.md`.

## Terms & Vocab
- Search bar — the field at the TOP of the chat list; placeholder "Ask Meta AI or Search".
- Chat list — the scrollable list of conversations; each row = contact name, last-message preview, time.
- Compose box — the text input field at the BOTTOM of an open chat (placeholder "Message").
- Send button — a GREEN CIRCLE with a white paper-plane/arrow, at the bottom-RIGHT, just right of
  the Compose box. It appears once the Compose box contains text.
- Sent bubble — a message YOU sent: a bubble on the RIGHT side of the conversation, with a
  timestamp and grey/blue check ticks (a single check, or double check for delivered/read).

## Visual
- You are looking at the WhatsApp app — a green-accented chat app. It is NOT a generic search
  tool, an assistant, or "Meta AI".
- The main screen is the Chat list. An OPEN CHAT shows the conversation (message bubbles) with the
  Compose box + Send button at the very bottom.
- A message counts as SENT only when it appears as a Sent bubble (RIGHT side, with check ticks) in
  the conversation. Text sitting in the Compose box is NOT sent yet — do not report it as sent.

## Operating
- To open a conversation: tap the Search bar, type the contact name (type_into the Search bar),
  then tap the matching result in the Chat list.
- To SEND a message: first type_into the Compose box, THEN TAP the Send button. CRITICAL: pressing
  Enter does NOT send in WhatsApp — it only inserts a newline. Do NOT use press_enter_after to send;
  you MUST click the Send button as a separate action.
- To send TWO messages: send the first (type into Compose box, tap Send), confirm it appears as a
  Sent bubble, then repeat for the second. Send them as separate messages, not combined into one.
- VERIFY a send by checking the message now appears as a Sent bubble (RIGHT side, with check ticks)
  in the conversation — NOT by seeing the text in the Compose box.
