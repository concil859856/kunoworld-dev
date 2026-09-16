# The safety gate on benign content: false positives and margins, 2026-09-16

First measurement of the safety gate's classifiers on real content. The run used `kuno-safety-eval` (subnet
`worker/src/kuno_worker/safety_eval.py`) inside the worker image `kuno-worker:ltx` (subnet `da0af19`), with the
classifiers and thresholds it ships:
- Qwen3Guard-Gen-0.6B for prompts;
- Freepik's nsfw_image_detector and CLIP ViT-L/14 zero-shot for frames;
- 10 frames per video, on CPU.

**Everything tested is benign.** This measures how often the gate blocks what it shouldn't, and how close benign
content comes to being blocked. It says nothing about whether the gate catches violating content. That needs a vetted
evaluation set handled under the owner's legal process (the harness takes one; see SECURITY.md).

The full reports, with ids and numbers only, are beside this note: `benign-prompts-report_2026-09-16.json` and
`benign-videos-report_2026-09-16.json`.

## Prompts: 42 of our own

The prompts: the 8 canary prompts, the 3 benchmark prompts, and the 31 website showcase and footage prompts, with
duplicates removed.

| Stage | Blocked | False-positive rate |
|---|---|---|
| Content policy (word lists) | 0 of 42 | 0% |
| Qwen3Guard classifier | 1 of 42 | 2.4% |
| Gate | 1 of 42 | 2.4% |

**The false block.** It was the colour-powder dancer shot on the homepage reel ("A dancer in white spins and flings
her arms out, launching huge bursts of vivid pink, yellow and blue powder…"). Qwen3Guard answered *Controversial:
Sexual Content*, which scores 0.5. The gate blocks controversial sexual content at 0.5 by design (`DEFAULT_THRESHOLDS`,
over-blocking preferred), so this is the designed trade-off showing up on an ordinary prompt, not a bug.

- Median latency: 0.72 s per prompt on CPU.
- **Owner decision:** keep blocking "Controversial" sexual content, and accept that some dance and fashion prompts are
  refused, or require "Unsafe" and rely on the frame check for borderline cases.

## Videos: 80 we generated

The clips: 6 from the network's own LTX-2.5 GPU runs; 44 showcase round-2 takes (Wan 3.0, Seedance 2.0, MiniMax H3),
including the take excluded from the site for looking undressed at a glance; 10 round-3 site takes; and 20 round-1
candidates (mostly Veo 3.1).

- **Blocked:** 0 of 80.
- **Median latency:** 5.1 s per video on CPU (p95 5.7 s).

Scores are each clip's maximum over its sampled frames. `ratio` is how far the clip got toward its nearest blocking
rule: 1.0 blocks.

| Clip | minor | sexual | suggestive | ratio | Rule it came closest to |
|---|---|---|---|---|---|
| showcase-v2/12-comic-hero-seedance | 0.23 | 0.25 | 0.26 | 0.77 | minor ≥ 0.3 and sexual ≥ 0.15 |
| showcase-v2/t3-fpv-canyon-seedance | 0.47 | 0.11 | 0.15 | 0.72 | the same |
| showcase-v2/t2-anime-rooftops-seedance | 0.41 | 0.08 | 0.08 | 0.54 | the same |
| showcase-v2/12-comic-hero-wan | 0.21 | 0.08 | 0.08 | 0.52 | the same |
| showcase-v2/16-color-powder-dancer-seedance-silent | 0.51 | 0.07 | 0.15 | 0.45 | the same |

**Findings.**
1. **The zero-shot minor detector fires on benign content.** 33 of 80 clips (41%) scored `minor` ≥ 0.3, including an
   FPV flight through a canyon with no people in it (0.47) and a claymation kitchen (0.63). For those clips the
   minor-with-sexual rule becomes simply `sexual` ≥ 0.15.
2. **Benign stylised clips already exceed 0.15 `sexual`.** The Seedance comic-hero take scored 0.25. It passed only
   because its `minor` score, 0.23, was under 0.3. A little more of a youthful look in the same clip would have
   blocked it.
3. **The take excluded from the site for looking undressed passed comfortably.** It isn't in the top five.
4. **The earlier synthetic benchmark was too optimistic.** SECURITY.md recorded benign peaks of 0.012 `sexual` and
   0.22 `minor` on synthetic clips; real generated video is an order of magnitude closer to the thresholds.

**What this means.**
- **False blocks.** Expect them on stylised and animated content once traffic grows, concentrated in the
  minor-with-sexual rule.
- **Possible remedies (owner decision):**
  - a better age signal than zero-shot CLIP;
  - scoring minor and sexual per frame rather than taking each one's maximum across all frames (the maximums can come
    from different frames);
  - a second look before blocking borderline clips.
- **Accuracy is still unmeasured.** None of this measures whether violating content is caught.
