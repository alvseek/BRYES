# Make a Lesson

A lesson is a teaching document whose every step is backed by a screenshot of the
running application, taken from the learner's own machine. BRYES records; the mentor
authors; the page carries both.

This file is the canonical procedure. The `/make-lesson` skill
(`.opencode/skills/make-lesson/SKILL.md`) points here rather than repeating it.

## The one rule

**A screenshot records what the screen showed. It never says why the step exists, in what order, or what the concept is.** The teaching value comes from the mentor and from the project's own sources. Any pipeline that derives instructions from pixels produces a confident wrong tutorial, which is the worst possible artifact for a beginner.

Everything below is arranged around that rule.

## Roles

- **BRYES captures.** `capture.py` (labelled shots) and `lesson.py` (build). Neither drives the application and neither decides what a lesson says.
- **The mentor authors.** Step order, instruction, why, expected. For a domain the mentor does not own (Unreal, a database, a vendor API), the facts come from the agent or doc that owns them, and the prose says which.
- **The learner drives.** Record mode is the default. Driving the real desktop is unbuilt and out of scope for this procedure.

## Preconditions

- The application is open on the machine running the capture.
- `python capture.py --list-windows` lists it (a visible, titled, top-level window).
- The repo has its dependencies: `pip install -r requirements.txt` (Pillow is the only one this needs).

## Phase 0: FRAME

*Goal: one sentence that says what the learner can do afterwards. Write it before capturing anything.*

- **Pick the altitude.** *Anatomy* (where things are) needs only a screenshot. *Operation* (do this task) usually needs the learner to drive, one capture per state change. *Concept* (why it works this way) needs a knowledge source, not pictures.
- **Check the screen matches the intended lesson.** If it does not, either change the lesson to fit the screen or ask for the state. Never write the lesson you planned while the evidence shows something else.
- **Name the lesson** `lessons/<project>-<nn>-<slug>/`, e.g. `lsgi-02-blueprint-editor`.

## Phase 1: CAPTURE

*Goal: one shot per state the lesson claims, with provenance.*

```
python capture.py --list-windows
python capture.py --lesson lsgi-02-blueprint-editor --step 1 --phase before \
    --window "Unreal Editor" --note "what this shot is meant to show"
```

- **Look at every shot before authoring.** `--raise` brings the window forward, but anything floating over that rectangle is baked in. A stray dialog is a defect in the evidence: fix the state and re-capture.
- **One shot per state change.** If the state does not change, one shot may serve several steps, but each step must highlight a different region. Six identical images with the same box is not a lesson.
- **Capture nothing you will not use.** The folder is the lesson's evidence, not a scratch pad.
- **The log is provenance.** Every line records time, requested window, path, size. It is what lets the build refuse a step whose shot is missing.

## Phase 2: AUTHOR

*Goal: `lesson.md`, written for a person who has not read what you read.*

Front matter: `title`, `project`, `lesson`, `created`, `target`. Then an intro paragraph, then steps.

```
## Step 3: Read the asset path, not just the asset
shot: shots/step-001-before.png
callout: 0.383,0.639,0.512,0.663 | The breadcrumb: All > Content > Tests
callout: 0.019,0.890,0.140,0.920 | The same folder, highlighted in the tree
instruction:
  ...
why:
  ...
expected:
  ...
```

- **Callouts are fractions of the image**, `x1,y1,x2,y2 | label`, measured from the capture. They survive any resize.
- **`shot: none` is an explicit opt-out**, for a step whose claim needs no picture (a shortcut, a decision). It is counted and reported, so prose-only lessons are visible rather than hidden.
- **Claims:** anything visible may be asserted. Anything about behaviour, purpose or consequence needs a source, and the source is named in the prose. An asset's name is not its purpose.
- **Voice:** second person, one idea per paragraph or bullet, `why` carries reasoning, `expected` carries the check the learner can run on themselves.
- **Write the `why` for the mistake it prevents.** "Compile before Play" is a fact; "a Blueprint you edited but did not compile is not what Play runs" is the reason someone will remember.

## Phase 3: BUILD

```
python lesson.py lessons/lsgi-02-blueprint-editor
```

- The build refuses a missing shot, an undeclared shot, or an inverted callout box, and writes nothing when it refuses. Read the failure, fix the lesson, run again.
- `assets/*.callouts.png` are generated. Never hand-edit them.

## Phase 4: VERIFY

*Goal: look at the output the way the learner will. This phase has caught real defects every time it ran.*

- **Open each `assets/step-*.callouts.png`.** Check three things: the box touches the thing the label names, the badge covers no label you rely on, and the circled number is legible.
- **Read the page top to bottom.** A step that only makes sense if you already know the answer is a failed step.
- **Re-read every claim against the shot.** If the evidence is not in the image, either delete the claim or mark where it comes from.
- **Fix and rebuild.** Annotation geometry is cheap to change and embarrassing to ship.

## Phase 5: HAND OFF

- **Place the lesson where it will be read.** BRYES is the instrument; a lesson about another project belongs near that project's docs, and `--out` supports it.
- **Decide the image policy before committing.** Lessons carry PNGs, roughly 1 MB each at 1600px wide. A handful is fine in git; a series wants LFS or a separate assets repo.
- **If the project keeps an orientation map or a session log, add the lesson to it.** An artifact nobody can find is not documentation.

## File contract

```
lessons/<lesson>/
  lesson.md                  authored by the mentor
  shots/step-NNN-<phase>.png captured by capture.py, never edited
  capture-log.jsonl          one line per capture, append-only
  lesson.html                built
  assets/step-NNN.callouts.png  built
```

## Gates

Three are enforced by `lesson.py`, and one only a reader can apply:

1. **Enforced.** Every step names a shot, or says `shot: none` deliberately.
2. **Enforced.** Every shot the lesson cites exists on disk.
3. **Enforced.** Every callout lies inside the image and is not inverted.
4. **Not enforceable.** Every image was looked at after the build, and every claim beyond the visible carries a named source in the prose.

Note what is deliberately *not* checked: whether a shot is old. Capture happens before
authoring, so a shot is always older than the text that cites it, and the staleness that
matters (the application moved on since the capture) is invisible to a timestamp. That is
why step 4 exists.

## Anti-patterns

- **Letting a vision model write the instructions.** It will describe the pixels accurately and the procedure wrongly.
- **Teaching semantics from a screenshot.** "This is the battle loop" is not something a picture can support.
- **Reusing one box for several claims.** Two claims, two boxes, even on one image.
- **Capturing the desktop when the lesson is about one window.** Crop to the application.
- **A text-only step that is really the whole lesson.** The build reports the ratio; read it.

## Worked examples

- `lessons/lsgi-01-editor-anatomy/` — anatomy, one capture, four steps, eleven callouts.
- `lessons/lsgi-02-blueprint-editor/` — anatomy of an editor inside an editor, one capture, five steps, five callouts.
