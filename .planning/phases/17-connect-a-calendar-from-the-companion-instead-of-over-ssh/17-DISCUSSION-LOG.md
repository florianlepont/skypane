# Phase 17: Connect a calendar from the companion instead of over SSH - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-09-08
**Phase:** 17-connect-a-calendar-from-the-companion-instead-of-over-ssh
**Areas discussed:** secret location on disk, fate of the environment variable, disconnecting, what happens on save

---

## Framing correction made before the areas were presented

The discussion opened by withdrawing a claim made while Phase 16 was being scoped — that the
environment variable made it "structurally impossible" for the companion to leak the URL. A
codebase scout showed all three systemd units load the same `EnvironmentFile` and run as the
same user, so the companion process already carried the variable. What protected the secret was
its code calling `calendar_is_configured()` rather than `configured_calendar_url()` — a code
discipline, not a process boundary. A second, stronger correction surfaced later (see the "What
happens on save" area below).

The same scout produced the finding that shaped the first area: no code in this project ever
sets a file mode, `STATE_DIR` is setgid, and `caddy` is in the `skypane` group — so copying the
house write idiom would have deposited the calendar URL group-readable by the internet-facing
reverse proxy.

---

## Where the secret lives on disk

| Option | Description | Selected |
|--------|-------------|----------|
| State directory, file at 0600 | Alongside the other state files but created explicitly at 0600 instead of the default umask. Caddy has +x on the directory but the file mode blocks it outright. No systemd unit touched, no daemon-reload to ask for. Real cost: it means breaking with the write idiom copied everywhere else, and the plan must make that break impossible to overlook. | ✓ |
| Dedicated directory, out of caddy's reach | A separate directory, no setgid, caddy not in the group — isolation rests on the directory and no longer depends on one file's mode. More robust if someone later copies the idiom by reflex. In exchange: both systemd units gain a ReadWritePaths, provision.sh gains a directory, and the developer runs the daemon-reload themselves at deploy. | |
| Inside device_config.json at 0600 | One more field in the existing settings file, whose mode would become 0600. Least new code. But that file is meant to be inspectable, several pages read and rewrite it, and it already travels through whole-dict equality comparisons in tests — a secret there is one carelessness away from leaking. | |

**User's choice:** State directory, file at 0600.
**Notes:** The dedicated-directory option was genuinely stronger on isolation and was rejected on
deployment cost, not on merit — `state_dir` is the only entry in `ReadWritePaths=` in both units,
so any other location requires editing them plus a `daemon-reload` on the VPS that the developer
would have to run themselves (`sudo systemctl` over SSH is blocked for Claude in this project).
The trade is recorded in CONTEXT.md D-01 so the planner compensates with explicitness rather than
inheriting the weaker guarantee silently.

---

## What the reader does if the file's mode has drifted

Asked as a follow-up in the same area, because D-01 makes the whole protection rest on one mode
bit surviving backups, clumsy `cp`s and different umasks.

| Option | Description | Selected |
|--------|-------------|----------|
| Refuse it and say so | The read checks the mode and, if too open, returns "not configured" without ever reading the value — what ssh does with an over-permissive private key. The interface then shows a distinct state naming the problem and the remedy. The feature stops, visibly, rather than continuing on an exposed secret. | ✓ |
| Re-tighten it silently and continue | The read detects the open mode, resets it to 0600 and carries on. Nothing breaks and the problem fixes itself. But the secret may already have been read, and the silent repair removes the evidence that it was. | |
| Use it anyway | The mode is set at write time and never re-checked. Least code, one fewer path to test. In exchange the only protection is a file written correctly once, with nothing re-verifying it afterwards. | |

**User's choice:** Refuse it and say so.
**Notes:** Recorded as D-02. Adds a fourth Settings status state beyond configured / not
configured / connected.

---

## Fate of the environment variable

First attempt at this question was answered with a question — *"pourquoi tu parles de fichier
alors que pour moi dans le companion on indique une url ??"*. The options had been written in
implementation terms (which storage source wins) without ever saying that the file is invisible
to the operator. The mechanism was explained — the web page and the poll service are two separate
programs sharing no memory, so the pasted URL has to be written down for the second to find it —
and the question was reframed as "should the old SSH way keep working?". That reframing is the
one the table below records.

| Option | Description | Selected |
|--------|-------------|----------|
| It disappears, the field is enough | One way to connect a calendar: the field. The line comes out of skypane.env.example and the code stops reading it. It is what "connect your calendar" means, and it removes the "but which of the two wins?" question before it can be asked. Since the variable was never actually set on the VPS, nobody loses anything. | ✓ |
| It stays and takes precedence | If someone sets the variable on the server it wins, and the field shows that the calendar comes from there. Lets an installation keep a secret that never touches disk. In exchange the interface has to explain a precedence, and there is a state where the field refuses what is typed into it. | |
| It stays, but the field wins | Both coexist, what is saved in the interface always wins. Already the behaviour of the wake interval. But the variable becomes an overridable default, which makes it misleading for anyone who sets it deliberately. | |

**User's choice:** It disappears, the field is enough.
**Notes:** Recorded as D-03. The lesson from the misfire is recorded in CONTEXT.md's `<specifics>`:
the file is never named in the interface, with D-02's permission state the single exception,
because that is the one case where the operator must act on the server.

---

## Disconnecting, and what remains

| Option | Description | Selected |
|--------|-------------|----------|
| Emptying the field disconnects and erases | Clear the field, save: the calendar is unplugged and the flights already fetched are deleted from disk in the same action. One gesture, and "disconnected" means what it sounds like — nothing of someone's schedule is left on the server. The form must distinguish "left empty because I did not touch it" from "emptied on purpose", which the project already knows how to do elsewhere. | ✓ |
| Emptying disconnects, flights age out | Same gesture, but the flights already fetched stay on disk and vanish on their own once outside the retention window. Less code. But for two days someone's schedule survives an explicit disconnection, which is not what the word promises. | |
| A separate Disconnect button | The field only ever connects; a distinct button unplugs and erases. The intent is impossible to confuse and an empty field keeps a single meaning. But it adds a control to an already-long settings page, and an action outside the save bar every other setting shares. | |

**User's choice:** Emptying the field disconnects and erases.
**Notes:** Recorded as D-04. One consequence was recorded rather than re-asked (D-05): replacing
the URL with a different one also clears the previous calendar's entries, since otherwise
"disconnected" would mean two different things depending on the gesture. The sentinel precedent
named for the form problem is `device_config.CLEAR_THEME_ARRIVING`, from Phase 15.

---

## What happens on save

Before this question was asked, a scout of the existing cross-process trigger produced the
discussion's most consequential finding, reported to the developer at the time: `POST /poll-now`
runs `poll_loop.run_once()` **inside the companion process**, and `run_once()` refreshes the
calendar, which reads the URL. The companion therefore already reads the secret's value today,
every time "Poll now" is pressed — contradicting the comment at `companion/app.py:1018` and
Phase 16's T-16-SECRET, and unnoticed by that phase's security audit. Nothing leaks, but the
property that had justified recommending the environment variable did not exist. It also means
the machinery for an immediate sync was already there.

| Option | Description | Selected |
|--------|-------------|----------|
| Immediate sync, outcome shown | Saving triggers the fetch at once, by the same path the "Poll now" button already uses, and the page comes back saying what happened: connected with N flights retained, or the failure and its reason. You know straight away whether the URL is right. It is the only moment an invalid URL can be reported usefully. | ✓ |
| Nothing, the next sync handles it | The URL is saved and the service picks it up on its next pass, up to thirty minutes later. No new code, no wait in the page. But a wrong URL is indistinguishable from a correct one for half an hour, which is exactly when you doubt you copied it properly. | |
| Nothing, but a Sync button | Saving triggers nothing; a button alongside runs the sync on demand. Saving stays fast and predictable. But it asks for a second gesture at the one moment you expected none, and adds another control to the page. | |

**User's choice:** Immediate sync, outcome shown.
**Notes:** Recorded as D-06, with two constraints noted rather than re-asked: the immediate sync
must bypass the 1800s fetch throttle (scoped to this path only), and the failure message must be
built from Phase 16's five `FETCH_*` outcome constants rather than from an exception string,
since network and DNS errors routinely embed the full request URL.

---

## Claude's Discretion

- The rendered wording of the field, its status states and the failure message, within Phase 16's
  locked copy discipline.
- Whether the field validates the URL's shape before storing, or lets `_url_is_safe()` and the
  fetch remain the single arbiter — with the constraint that an earlier check must not become a
  second, drifting definition.
- Whether repeated saves need a cooldown beyond the existing `/poll-now` one.
- Task and wave decomposition.

## Deferred Ideas

- Showing which upcoming flights the connected calendar holds — deliberately absent in Phase 16
  so the frame does not look like it tracks a person; a browsable list would be its own phase.
- More than one connected calendar — the registry, match key and single theme all assume one.
- Connecting a calendar from the device itself, without a browser — not raised, noted only because
  the phase name invites the question.
