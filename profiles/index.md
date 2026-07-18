# BRYES Profile Catalog

The agent picks its embodiment for a task from this catalog BEFORE it starts — text-only, from
the goal, with no screen yet. Pick ONE body (a `##` section) and ZERO OR MORE profiles listed
under it. For a pure question that needs NO on-screen action, pick no body and answer directly.

Each profile line is `` `<path>` — <description> ``. A profile inherits every `profile.md` up its
path, so picking `android/whatsapp` also loads `android`.

## android — a real Android phone (body), driven over USB
- `android` — base Android conventions (status/navigation bar, on-screen keyboard, autocorrect suggestion bar)
- `android/whatsapp` — messaging on WhatsApp (chat list, search, compose box, send button)

## linux — the Linux desktop container (body): Google Chrome, a terminal, a calculator
- `linux` — base desktop conventions (windows, mouse + keyboard, a shell for command-line tasks)
- `linux/browser` — browsing the web in Google Chrome (address bar, tabs, on-page search, lazy-loading pages)
- `linux/browser/tokopedia` — shopping on Tokopedia (search box, product result grid, "Rp" price format)
