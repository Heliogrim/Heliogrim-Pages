# Report a Bug

<a class="hg-btn primary" href="https://github.com/Heliogrim/Heliogrim-Engine/issues/new?template=1-bug_report.yml">Open a bug report</a>
<a class="hg-btn" href="https://github.com/Heliogrim/Heliogrim-Engine/issues?q=is%3Aissue+label%3Abug">Search existing bugs</a>

The button opens the engine repository's bug report form.

## What makes a report actionable

- **One bug per issue.** Two symptoms with one cause can be linked later.
- **Exact steps.** Start from a clean checkout or an empty level if you can.
- **Commit hash**, not "latest". Say whether the editor or a packaged runtime failed.
- **Hardware and driver** for anything rendering, audio or storage related. The engine targets Windows first.
- **The first error**, not the last. Paste the log from the first warning on.
- **A crash dump or call stack** for crashes.

## Security issues

Do not open a public issue for a vulnerability. Use the *Report a vulnerability* option under the Security tab of the engine repository if it is enabled, or contact the maintainers privately.

## What happens next

A maintainer triages the issue, sets labels, and adds it to the [project board](project-links.md). A bug that exposes a design problem may lead to an [exploration](../guides/writing-explorations.md).
