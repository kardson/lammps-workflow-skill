# Records, recovery and delivery

Use a private workspace with plan, literature, models, runs, analysis, review and administration areas. `tools/init_workspace.py` creates this layout without overwriting files. Existing project layouts remain valid; don't migrate raw evidence just for naming consistency.

Plans and model cards distinguish proposed, confirmed and unverified fields. Reference the actual user decision in `confirmation`; leave it null in drafts. Separate scientific confirmation, installation/build permission, MD execution, performance testing, remote transfer and monitoring scopes. Do not fabricate approval records.

For each execution attempt retain plan and input-audit references, actual inputs and potential identity, exact executable/interface, command/resource settings, host/directory, start observation, job/process/session identity, termination evidence, required outputs and missing items. A restart gets a separate attempt linked to its actual parent restart and compatibility audit; do not reuse stale process IDs as live identity.

On a progress question, obtain a bounded read-only snapshot of the selected attempt if the host is available and that check is authorized. Prefer direct status/log/process evidence; distinguish no connection, process absent, partial log, running and terminal. Do not relaunch, signal processes, change sessions or start polling based on missing evidence. A historical `running` stage is never enough to resume execution.

Deliver actual observations and their timestamps, not a directory-derived scientific state. Raw log inspection can support failure diagnosis even without a preparation audit; label that limitation. Accepted numerical/scientific claims require the relevant plan, actual-input audit, outputs and agreed criteria. Keep failed/partial/unknown states visible, preserve original output requirements and report parser failures without treating them as successful analysis.

For numerical results retain selected frames/time windows, analysis script/version, parameters and units, numerical tables, figures and limitations. File hashes establish specific model/input/transfer identity, not perpetual determinism or scientific validity. Never include private host/configuration data or results in a public skill update.
