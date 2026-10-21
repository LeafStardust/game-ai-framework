# Trained Sanma reference audit

Checked 2026-10-21. No trained reference was integrated, no inference was run, and no live policy or launcher changed. This audit does not establish that public Sanma weights do not exist elsewhere.

## Candidate findings

| Candidate | Source revision | Artifact finding | Decision |
| --- | --- | --- | --- |
| [Meowjong](https://github.com/VictorZXY/Meowjong) | `d32612a8eeb3df760eba58ae545b141f8910815a` | No checkpoint files found in the complete Git tree and no release assets returned. README documents training five models, without a pretrained download link. | Research/training reference; cannot run the published policy from these artifacts. |
| [Mortal Sanma](https://github.com/Lawrencelea/Mortal_Sanma) | `5575c139e3ed5c41d281b1260b9c58b13c077558` | No checkpoint files found in the complete Git tree and no release assets returned. README explicitly says model weights are untracked and created by training. | Plausible Sanma interface, unavailable trained reference. |
| [mahjong-ai-sanma](https://github.com/Mateces/mahjong-ai-sanma) | `ed9ed8388a1c0c205e31e3ecc47863c54257a442` | README links upstream c3 weights, but identifies their training data, rank heads and evaluation as four-player East/South. | Those linked weights are not a verified Sanma checkpoint. Do not substitute them. |

Method: GitHub repository metadata, recursive Git trees (all returned untruncated), release assets and README model/download references. File-name checks covered `.pth`, `.pt`, `.onnx`, `.h5`, `.hdf5`, `.keras`, `.ckpt`, `.safetensors`, saved-model and checkpoint paths. This cannot rule out unadvertised or externally hosted weights. No foreign training code was executed and no model libraries were installed.

## Compatibility boundary

Mortal Sanma documents 774 observation channels and 44 actions for its v5 encoder. Our simulator adapter currently handles native RiichiEnv actions, not that encoded tensor or action vector. Matching action counts would not establish equivalence. Meowjong uses separate Discard, Pon, Kan, Kita and Riichi models, so a discard model alone would not reproduce the full published policy.

A usable reference needs the exact checkpoint, architecture and observation encoder revisions together. Before benchmarking, verify:

- Sanma tile set, red fives, North extraction, no Chi, legal Kan and Riichi handling.
- Mahjong Soul scoring rules, especially Tsumo loss, and East versus South training/evaluation objectives.
- Exact action-to-native mapping, red/normal tile identity, legal-action masking and the two-stage Riichi action.
- Public-information-only features, including history accumulated across observations. No simulator hidden hands or wall may enter inference.
- Deterministic inference and actual completed matches on development seeds, followed by frozen held-out evaluation. Record checkpoint SHA-256 and encoder revision with results.

These are acceptance requirements, not completed compatibility tests. No candidate above passed an inference test because no appropriate checkpoint was obtained.

## Next implementation

Continue improving the existing East Speed policy using complete-game outcomes. Audit call opportunities and legal winning progress on recorded boards before adding another shape-only tie-break: the previous lookahead experiments did not demonstrate a win-rate gain. Keep trained-model integration pending a verifiable Sanma checkpoint; do not start a large training run implicitly or replace live decisions with random weights.
