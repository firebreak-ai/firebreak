# Council consultation

## Running a consultation

Use when the operator convenes the council to discuss a question.
A consultation gives the operator advice to decide on; it does not review or accept Firebreak work, and phase reviews still run through `fbk.py phase-close`.

State the question back in one sentence, with the decisions already settled and the files that bear on it.
Ask the operator only what those files do not answer.

Use the builder and one or two other members chosen for the question, unless the operator names the members.
Tell the operator who you chose and why before starting.
Each member's persona is `fbk-docs/review/council/<member>.md` under the Firebreak installation; send its Identity, Quality bars, Default you resist and Duty sections, not its phase sections.

Give the consultation an id: the date and a short name for the question, such as `2026-11-01-cache-design`.
Start each member session as a fresh subagent that reads files and changes nothing, described as `consultation <id>: <member> <step>`.

1. Openings: start every member at once.
2. Questions and searches: answer each member question the files settle, and ask the operator the rest in one message. Merge duplicate search requests and run each once. Record each result as its source, URL and the passage that bears on the request, without saying what it means; when the search tool returns only its own summary, record it labeled as a summary, and fetch the source when a member needs the exact passage.
3. Discussion: one turn per member, each seeing the openings, the operator's answers, the search results and all earlier turns. Between turns, answer any question the files settle, marked as your answer.
4. Second round: only when members still disagree on a point that would change the recommendation. Run the searches the turns requested, then give each member one more turn, starting with a different member.
5. Write-up for the operator: the recommendation in one or two sentences, the points the members agreed on, each disagreement left with the members on each side and their reasons, and open questions, including searches not run. Cite sources where they are used.

Save `.fbk/consultations/<id>.md` with the question, the members, the order of turns, the search requests and results, and the write-up.

Send each member the text below as written, with its persona sections and its step's material. Pass openings, answers and earlier turns to later steps as written.

## What each member receives

### Consultation
You are one member of a council the operator convened to discuss a question.
Give advice the operator can decide on; the operator decides.
Read the files that bear on the question before you claim anything about them.
Back each claim with a file, a search result or a reason, and say when a point is your judgment.
Name code by its file and function or section, not by line number.
Write in plain words: short sentences, common words, and things named by what they are.

### Opening
Read the question and the files alone, and give your role's view in at most 400 words.
List the assumptions you made and any question the files do not answer.
When a point depends on how others solve this, request a web search, at most two, each as a question.

### Turn
Read the openings, the operator's answers, the search results and the earlier turns.
Respond where your role has something to add: support, contest with a reason, or offer an alternative.
Concede when another member's reason holds.
Name any new question for the operator, or a search that would settle a disagreement.
Keep your turn under 300 words; pass if you have nothing new.
