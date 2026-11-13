# ConvoAI — User Acceptance Test checklist

Manual end-to-end checks in the browser (Chromium, desktop 1366–1440 px and phone 375 px, light and dark theme), run during development on the RTX 3060 laptop with the Nimbus sample documents loaded. **Result** records what was observed. "Not tested" means the check still needs a person to do it.

| ID | Area | Steps | Expected | Result |
|---|---|---|---|---|
| UAT-01 | Start-up | Run `python app.py` and open the app | Chat opens directly (no sign-in); Overview shows Database, Ollama, chat and embedding models as green | Pass |
| UAT-02 | Theme | Click the theme button (system → light → dark), reload, change page | Theme switches instantly and is remembered across pages and reloads | Pass |
| UAT-03 | Small talk | Type "hi", then "thanks!" | Instant reply (≈10 ms) with the "Quick reply" badge, no sources | Pass |
| UAT-04 | Document question | Click the suggestion "How many casual leaves do I get per year?" | Streams "12 days of casual leave" with citation chips to the Employee Handbook p.4; "From documents" badge | Pass |
| UAT-05 | Follow-up | In the same chat, ask "what about sick leave? and can I carry it forward?" | Status shows "Understanding your follow-up…"; answer gives 10 days and the 20-day carry-forward limit, cited | Pass |
| UAT-06 | Out of scope | Ask "What is the capital of France?" | Polite "couldn't find" reply, "Not found in documents" badge, no invented answer | Pass |
| UAT-07 | Sources panel | Click a citation number or source chip | Panel opens at the cited passage with the question's words highlighted (side column on desktop, bottom sheet on phone) | Pass |
| UAT-08 | Feedback | Click 👍 on an answer, reload the conversation | Thumb stays filled; the rating appears on the Analytics page | Pass |
| UAT-09 | Stop | Ask a long question and press ■ while it streams | Streaming stops, "Stopped." is shown, the partial answer is saved in history | Pass |
| UAT-10 | History | Rename a chat, delete a chat, use the browser Back button, open `/c/<id>` directly | All work; deleted chat disappears; links and Back restore the right conversation | Pass |
| UAT-11 | Collections filter | Select the "IT Support" chip and ask an HR question | Answer is limited to IT documents (says it couldn't find it, or cites only IT sources) | Pass |
| UAT-12 | Voice input | Tap 🎤, ask "My VPN keeps disconnecting…", stay silent | Recording stops ~1.5 s after speech; text transcribed on this computer; answer read aloud with an installed voice | Pass with a recorded voice fed in as the microphone. **Live microphone: not tested** (no microphone in the test browser) |
| UAT-13 | Voice cancel | Tap 🎤 then press Esc; tap 🎤 and say nothing | Esc cancels without sending; silence gives up after 8 s with a hint | Pass |
| UAT-14 | Read aloud | Turn on 🔊 in the message box and ask a question | Answer is read aloud without the citation numbers, using a voice installed on this PC | Pass |
| UAT-15 | Upload | Admin → Documents: drag in a 41-page PDF | Status goes Queued → Processing % → Ready (~6 s); chunks viewable with page numbers | Pass |
| UAT-16 | Duplicate upload | Upload the same file again to the same collection | Skipped with "Already in …" | Pass (automated test) |
| UAT-17 | Test retrieval | Documents → Test retrieval: "who approves discounts above 20 percent" | Vector and keyword results both show the Discounts section first | Pass |
| UAT-18 | Move document | Rename/move a document to another collection | Moves immediately; citations show the new title | Pass (automated test, plus UI dialog opened) |
| UAT-19 | Collections | Create "Test Finance" with an icon and colour, then delete it | Card appears; delete asks for confirmation and removes it | Pass |
| UAT-20 | Intents | Open `doc_query` in Admin → Intents | Tag, Active switch and Responses are locked; Delete is hidden | Pass |
| UAT-21 | Retrain | Edit an intent, then Retrain | "Retrain needed" banner appears after the edit and clears after training | Pass (automated test) |
| UAT-22 | Settings | Change "Sources per answer" to 6 and save; then try 50 | 6 saves with "Saved 1 setting"; 50 is rejected with the field highlighted | Pass |
| UAT-23 | Analytics | Open Admin → Analytics, switch time ranges, toggle a chart to its table view | Figures match the chat history; table view shows full names | Pass |
| UAT-24 | Metrics | Admin → Metrics → Re-run evaluation | Finishes in ~10 s; hybrid MRR 0.935; every question plotted against the 0.618 line | Pass |
| UAT-25 | Phone layout | Repeat UAT-03/04/07 at 375 px | No sideways scrolling; history is a slide-out drawer; message box above the bottom navigation | Pass |
| UAT-26 | Access control (sign-in on) | Set `LOGIN_REQUIRED=1`; user with HR access only asks about the VPN | IT documents are never retrieved or cited; admin pages return 403 | Pass (automated tests) |

**Recommended before the viva:** repeat UAT-12 with a real microphone in Chrome or Edge, and allow microphone access when the browser asks.
