# Skip timing and lossless capture encoding

Reviewed retained Skip-failure groups in the October 26 batch. The longest retained groups span approximately 1.13 seconds across five failed checks. The inspected frame shows the call panel absent while the discard/turn animation is still underway. Because journaling deduplicates frames, image references are not exact captures for every failed attempt. No stable visible Skip misclassification was demonstrated. Keep recognition thresholds, two-frame stability checks and board guards unchanged.

An offline encoding comparison used six retained full-size screenshots, decoded to BGRA and re-encoded with zlib levels three and one. Median PNG encoding time fell from 126.96 ms to 114.23 ms. Aggregate encoded size increased by a factor of 1.036. Every decoded output exactly matched the source RGB pixels. This is a codec microbenchmark, not measured live input latency.

Use level one for the recorder's filter-zero RGB PNGs. The format, CRCs, resolution, channel values and decoder requirements are unchanged. Disk retention caps remain unchanged; slightly larger frames may cause earlier deletion of old images within a session. A faster RLE experiment measured approximately 61 ms but increased aggregate size by 71 percent, so it was not adopted.

Validation includes a full-frame pattern spanning all channel values and scanlines plus the existing recorder/decoder and Mahjong tests. No live screenshot capture, input or agent launch was performed; all images used for the experiment were existing local records. No raw session images were published.

Expected benefit is modest: roughly thirteen milliseconds per encoded frame in the sampled workload. It does not remove the client's call-panel animation or guarantee one-second decisions. Next validation can use the user's next normal three-game batch; no special hand or UI setup is needed.
