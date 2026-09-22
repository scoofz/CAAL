# Hey Zelda

Community OpenWakeWord model, supplied unchanged from
[fwartner/home-assistant-wakewords-collection](https://github.com/fwartner/home-assistant-wakewords-collection/tree/8bcd2f20bb7b76c351b2eff871fa1ce873fe9be2/en/hey_zelda).

- Source revision: `8bcd2f20bb7b76c351b2eff871fa1ce873fe9be2`
- SHA-256: `a28322c2f82dccd0b2cc227db169f18289027ca31d3a226874e574ae685bb38b`
- Repository license: MIT (see `hey_zelda.LICENSE`).
- Input: float32 embeddings `[1, 16, 96]`, compatible with CAAL's OpenWakeWord frontend.
- Checked: ONNX structural validation and CPU inference on zero embeddings.
- Not yet measured: real microphone detection, French accent recall, false activations.

This is a community pretrained detector, not a newly trained model and not a
voice clone. The Qwen3 reference WAV is independent of wake word detection.
Start at threshold 0.5 and test with your microphone before tuning it.
