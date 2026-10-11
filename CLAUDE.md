Always read docs/spec.md before starting any work.

## 17. Working rules for you

### Build feature by feature, never all at once
For every feature, follow this loop and stop at each checkpoint for my approval:
1. **Design note**: what the feature does, the options you considered, the trade-offs, and your recommendation.
2. **Devil's advocate**: argue against your own recommendation. List the strongest reasons it could fail, what it costs, and what a simpler option would give up. Then say whether you still recommend it.
3. **I approve or change the design.**
4. **Implement only that feature**, with its tests.
5. **Demo**: show me it working (test output, and a fixture or live page run where relevant).
6. **Feature summary**: a short plain-English summary, then a few succinct bullets covering what the feature added and how it works. No jargon I would need to look up.
7. **I approve**, then commit. Only then start the next feature.

Never implement more than one feature in a single step. Never start a feature I have not approved.

### General

- Verify any API, selector, browser behaviour or library detail against current documentation or a live page before relying on it. If something in this prompt is wrong, tell me what you found.
- When unsure about a design choice, ask me instead of guessing.
- Keep a `README.md` with setup, how to load the extension in each browser, how to run each test suite, and how to run the backend.