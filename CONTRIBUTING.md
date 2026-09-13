# Contributing

Corrections, counterexamples, and reports of use on real systems are the most valuable contributions at this stage.

- Found a class of silent protection failure the verification points do not cover? Open an issue with a description of the chain and where the break sits. Do not include confidential or customer data.
- Applied CoCV to a real product? Open an issue titled "Adoption" with the product category and what the method found, at whatever level of detail you can share. Listed adopters appear on the methodology page with permission.
- Code changes: run `pytest` before opening a pull request. Keep the reconciler deterministic; anything that needs a model belongs in `cocv/ai/`.

By contributing you agree that code contributions are licensed under MIT and documentation contributions under CC BY 4.0.
