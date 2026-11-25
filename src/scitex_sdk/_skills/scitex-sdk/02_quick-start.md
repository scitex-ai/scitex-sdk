---
description: [user outcome, capability discovery and validation boundaries] See SKILL.md and the intent-based workflow before selecting implementation tools.
tags: [scitex-sdk]
---

# Start with what the user wants to build

1. Follow [Build from intent](05_build-from-intent.md): identify inputs,
   outputs, project scope and a concrete acceptance example. Reuse supplied
   context rather than making the user select a starter first.
2. Inspect existing leaf capabilities and the app being extended. Use
   `scitex-sdk list-python-apis --json` and `scitex-sdk skills list --json`
   for discovery, then read the owning App/UI skills.
3. Implement one useful interaction using shared SDK contracts. For a new
   app, `scitex-sdk app init ./sample_app --name sample_app --dry-run`
   previews boilerplate creation without writing. Scaffolding is optional
   tooling, not an implementation of the user's requested feature.
4. Exercise the behavioral acceptance example and refusal cases on owned
   fixtures. `scitex-sdk app validate ./sample_app` checks a created app's
   readiness; it does not prove feature correctness or visual acceptance.
5. Verify installed artifacts and the intended host separately before
   adoption, submission or release.

The creator at `scitex-sdk gui serve` starts from the user's description and
creates a plain workspace with that implementation brief. Feature development
comes next. Older installed/hosted versions may still show starter cards.
Detailed creation and validation mechanics belong to the scitex-app component
skill; UI mounting and shared shell behavior belong to the scitex-ui skill.
