# Driving a Windows application: the executive view

What happens when an agent is asked to operate a real Windows application through BRYES. The
agent is the decider; BRYES supplies eyes and hands only. No step here depends on a command,
a coordinate or an endpoint, so a reader can follow the shape without the technical detail.
The full procedure is [drive-the-desktop.md](../procedures/drive-the-desktop.md).

```mermaid
flowchart TD
    A["A job needs a real Windows application"] --> B{"Can the application do it<br/>through its own API or command line?"}
    B -->|Yes| C["Use that route instead<br/>the visual route is the fallback"]
    C --> Z["Done"]
    B -->|No| D["Confirm the task is authorised<br/>this is the user's own desktop"]
    D --> E{"Is the eyes-and-hands tool<br/>already running?"}
    E -->|No| E1["Start it, allowing it to act"]
    E -->|Yes| E2["Check that it answers<br/>an answer is not proof it can act"]
    E1 --> E2
    E2 --> E3{"Can it both see the screen<br/>and act on it?"}
    E3 -->|See only| E4["Only looking is allowed<br/>so the job cannot be finished"]
    E3 -->|Both| E5{"Is it local to this machine,<br/>with no other driver?"}
    E5 -->|No| E6["Another driver has the desktop<br/>so this task cannot take it"]
    E4 --> M["Stop and report<br/>what happened and what remains"]
    E6 --> M
    E5 -->|Yes| F["Choose the target window<br/>prefer one you launched"]
    F --> G["Look at the current screen"]
    G --> H["Decide the next single action"]
    H --> I["Act"]
    I --> J["Look again and compare<br/>with what was expected"]
    J --> K{"Did the screen show<br/>the expected change?"}
    K -->|No| L["Re-check the basics<br/>right window, fresh picture, focus, partial failure"]
    L -->|Recoverable| H
    L -->|Not recoverable| M
    K -->|Yes| N{"Is the job finished?"}
    N -->|No| H
    N -->|Yes| O["Check that the result really persisted<br/>then report what was seen and what was saved"]
    O --> Z
    M --> Z
```

## Two abilities, not one

Connecting is not a single switch. The tool has to be running, and it has to be allowed to act
as well as see. A healthy answer only proves it is talking. When only seeing is possible, the
job cannot be finished, and the gap is reported rather than worked around.

## The rules that hold at every step

- **One authorised task.** Act only inside the task that was agreed, and never touch unrelated
  work on the same desktop.
- **One driver at a time.** The desktop is shared with the person using it. Do not compete for
  the mouse or keyboard, and leave shared processes running.
- **Look before you act, and look again after.** Every picture is a moment; a window that moved,
  a layout that changed or a stale image makes the next action wrong.
- **"It answered" is not "it worked".** A completed call, a visible change and a saved result are
  three separate claims. Report each one for what it is.
- **A half-finished sequence is not rolled back.** When a sequence stops partway, look at the
  desktop before deciding what remains, and never replay it blindly.
- **Stop rather than improvise.** If the result cannot be confirmed, or the task would reach
  beyond what was authorised, stop and say so.

## A note on the alternative

There is a second entry point where the whole goal is handed to BRYES and it decides every step
itself. That is a different way in, not a different set of rules: the same authorisation,
targeting and verification apply.
