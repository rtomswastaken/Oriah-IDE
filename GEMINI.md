# Oriah IDE

## 1. Terse Communication (Caveman Ultra Mode)
Respond in Ultra-compressed communication mode for every prompt in this workspace:
- Speak like smart caveman: drop articles (a/an/the), fillers (just, really, basically, actually, simply), pleasantries (sure, happy to), and hedging.
- Abbreviate prose words (e.g. DB, auth, config, req, res, fn, impl, conn, cmd).
- Strip conjunctions. Use arrows for causality (e.g., X → Y).
- Use one word when one word is enough.
- Technical terms exact. Code blocks unchanged. Errors quoted exact.
- NEVER abbreviate code symbols, function/API names, file paths, or error strings.
- Format: `[thing] [action] [reason]. [next step].`

## 2. RTK (Rust Token Killer / rrtk) Command Execution
- ALWAYS prefix every terminal / shell command with `rtk` (e.g., `rtk git status`, `rtk ls`, `rtk cargo check`, `rtk python3 ...`).
- In command chains with `&&`, prefix EACH individual command with `rtk`:
  `rtk git add . && rtk git commit -m "msg" && rtk git push`
- If RTK has a dedicated filter, it uses it. If not, it passes through unchanged. RTK is always safe to use.

## 3. Skills Enforcement (using-superpowers & using-skills-as-needed)
- MUST follow `using-superpowers` and `using-skills-as-needed` workflows on every prompt.
- Check and invoke relevant skills BEFORE any action or response.
- Follow skill priority: process skills (`brainstorming`, `systematic-debugging`, `test-driven-development`) first, then domain/implementation skills.
- Announce "Using [skill] to [purpose]".
- Use task artifacts (`task.md`) to track multi-step progress.
