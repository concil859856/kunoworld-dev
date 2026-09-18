# KunoWorld

Private, verifiable AI video generation on a Bittensor subnet. Customers make videos with **LTX-2.5** and
**MiniMax H3**, and choose for each job how private it is:

- **Private:** the job runs only on GPUs inside hardware enclaves (Intel TDX with NVIDIA confidential computing). The
  prompt, the reference media and the finished video are encrypted end to end between the customer's device and an
  enclave whose attestation the customer's own client has checked.
- **Standard:** KunoWorld can read the job, so any miner can run it, including GPUs without an enclave.

Every video comes back with an enclave-signed receipt and a C2PA manifest that anyone can verify.

This is the development workspace: it ties the other repositories together and holds the integration tests, the dev
and GPU-test scripts, and the research behind the design. Website: **kunoworld.com**.

> **Where things stand (2026-09-18).** The whole system works end to end against a simulated enclave, with real
> encryption. Both model families have rendered on rented GPUs through a real gateway, without confidential computing.
> Real enclave attestation, live payments and the live chain have not run yet. Details in [Status](#status).

## The repositories

Five private repositories, cloned side by side in this directory. `subnet/` and `sdk/` are written to be made public
later: the enclave code must be auditable for the privacy claim to mean anything, and third parties need to run the
validator.

| Folder | Repository | What it holds |
|---|---|---|
| [subnet/](subnet/) | [kunoworld-subnet](https://github.com/concil859856/kunoworld-subnet) | The wire protocol, the miner worker (runs inside the confidential VM), the validator, the worker images |
| [sdk/](sdk/) | [kunoworld-sdk](https://github.com/concil859856/kunoworld-sdk) | Python and JavaScript clients that encrypt on the customer's device, and an MCP server for AI assistants |
| [platform/](platform/) | [kunoworld-platform](https://github.com/concil859856/kunoworld-platform) | The gateway API, the website and studio, deployment |
| [papers/](papers/) | [kunoworld-papers](https://github.com/concil859856/kunoworld-papers) | The development record, `agent.md` |
| this directory | [kunoworld-dev](https://github.com/concil859856/kunoworld-dev) | The uv workspace, integration tests, dev and GPU-test scripts, research |

This directory's `.gitignore` excludes the other four, so run git inside each one (`git -C subnet …`). From here, git
works on kunoworld-dev.

**Where to read further**

| Question | Document |
|---|---|
| What is on the wire, byte for byte | [subnet/PROTOCOL.md](subnet/PROTOCOL.md) |
| Running a miner or a validator | [subnet/MINING.md](subnet/MINING.md), [subnet/VALIDATING.md](subnet/VALIDATING.md) |
| What the enclave protects, and what it does not | [subnet/SECURITY.md](subnet/SECURITY.md), [subnet/PRIVACY_MODES.md](subnet/PRIVACY_MODES.md) |
| What a second of video costs and what customers pay | [subnet/PRICING.md](subnet/PRICING.md) |
| Using the API from code | [sdk/python/README.md](sdk/python/README.md), [sdk/js/README.md](sdk/js/README.md) |
| Operating the platform | [platform/README.md](platform/README.md), [platform/deploy/README.md](platform/deploy/README.md) |
| The full status, the owner's decisions, and what's next | [papers/agent.md](papers/agent.md) |
| Why the design is the way it is | [research/](research/) |

## How privacy works

| | Private | Standard |
|---|---|---|
| Who can read your prompt, inputs and video | only you, and the attested enclave that renders it | you, KunoWorld, and the GPU provider that renders it |
| Which miners may run it | confidential (TEE) miners only | any miner, including open-tier miners without a TEE |
| Where the video is kept | on Cloudflare R2, as ciphertext only you can decrypt | on Cloudflare R2, encrypted at rest |
| How long it is kept | until you delete it | until you delete it |
| If you lose access | a lost key means a lost video: back up your keys | sign in again |

The same rules apply in both modes:

- **Only you can open your video.** Nobody at KunoWorld opens a customer's video, with two exceptions: content
  reported as child sexual abuse material, and content under a legal preservation hold. Every such view is logged. In
  Private mode KunoWorld can't open a video at all unless whoever reports it supplies its key.
- **No sexual content.** It is not allowed in either mode. Prompts are checked inside the enclave in both modes (and at
  the gateway for Standard jobs), and every finished video's frames are checked before it is signed. A blocked prompt
  counts as a strike against the account. The exception is text a model wrote inside the enclave (the prompt enhancer's
  rewrite or a Director plan): that job is refused and refunded without a strike.
- **Enforcement never needs to look.** Private content is policed by the in-enclave checks, account strikes and
  restrictions, reports, and signed provenance that traces a surfaced copy back to its job.
- **Sign-in.** Customers and operators sign in by email; the website keeps the session in an HttpOnly cookie and never
  gives the browser a token. API keys are only for developers calling the API.

**Prices.** Standard matches fal's list price for the same model; Private may cost more, because confidential GPUs
cost more. Full MiniMax H3 is Private-only: at fal's price, a Standard second would sell for a fraction of what it
costs to render. The prices in `subnet/protocol/src/kuno_protocol/profiles.json` are launch estimates until they are
benchmarked on confidential hardware, and the API marks them `pricing_placeholder`. The legal entity and its
jurisdiction are not decided yet, so the terms and privacy policy remain drafts.

## How a request flows

```
browser / SDK ──seal(prompt, params as AAD)──► gateway ──queue──► worker in TDX CVM ──► model runtime (H3 / LTX)
     ▲   encrypt inputs with HPKE-exported key       │                 │ decrypt, safety check, generate
     │                                               │                 │ encrypt video with HPKE-exported output key
     └──── download ciphertext, verify receipt, decrypt locally ◄──────┘ sign receipt with attested key
```

1. The SDK asks `/v1/route` which model serves the request (the owner's switch, the H3 licence's regions, capacity)
   and gets the attested enclaves. It verifies their attestation itself.
2. It opens an HPKE session to the enclave's key, uploads inputs encrypted with the exported input key, and seals the
   private payload with the public params, job id, enclave id and blob ids as associated data.
3. The gateway prices and queues ciphertext. Changing any public parameter makes decryption fail inside the enclave.
4. The worker decrypts, runs the in-enclave safety gate, generates, encrypts the MP4 with the output key, uploads it,
   and signs a receipt (digests only, no content).
5. The SDK checks the receipt's signature and digests, then decrypts on the device.

## Quickstart: a local network with real encryption and mock GPUs

Needs `uv` and `ffmpeg`; Node 22.13+ for the website, Node 20+ for the JavaScript SDK alone.

```bash
uv sync
scripts/dev.sh            # gateway on :8080 and a mock-TEE worker serving every profile; prints the dev API key
```

The mock worker encrypts, signs and delivers real MP4s, but their pictures are placeholders. Make one with the Python
SDK:

```bash
source data/dev.env
uv run python - <<'EOF'
import os
from kunoworld import KunoClient
from kuno_protocol.attestation import GoldenManifest

manifest = GoldenManifest.model_validate_json(open(os.environ["KUNO_MANIFEST"]).read())
client = KunoClient(os.environ["KUNO_DEV_API_KEY"], "http://127.0.0.1:8080", manifest=manifest, country="JP")
result = client.generate("A lighthouse keeper lights the lamp at dusk", model="h3-turbo", duration_s=5)
print(result.save("lighthouse.mp4"), result.receipt.body.content_digest)
EOF
```

`country="JP"` matters: MiniMax H3 is only served outside the regions its licence excludes.

Other entry points:

```bash
cd platform/web && npm ci && npm run dev    # the website and studio at localhost:3000
kuno-validator once --canary ltx-2.5-fast   # one validator round: attest, canary, score
kuno-preflight --no-tee                     # can this machine mine? what is missing?
kuno-plan h3-reference reference_to_video   # exactly what the worker would send to the model runtime
```

`scripts/localnet/` runs the subnet against a local Bittensor chain, and `scripts/gpu-test/` runs real models on a
rented GPU server (see each folder's README).

## Tests

```bash
scripts/check.sh          # every check without GPUs: Python, the JavaScript SDK, the website's typecheck, lint and build
scripts/check.sh --web    # also the Playwright browser suite (it starts the backend itself)
uv run pytest -q          # the Python suite alone, including the integration tests in tests/
```

Run `pytest` from this directory, not inside a repository: `pytest subnet` misses the integration tests in `tests/`.
On 2026-09-18 the Python suite was 2,427 tests, all passing.

The suite covers, among other things:
- the encrypted round trip end to end, and that no plaintext prompt, input or output reaches the gateway's database
  or blob store;
- that a relay tampering with public parameters makes the job fail inside the enclave;
- that a crashing model never leaks the prompt into logs or failure messages;
- the owner's switch and the H3 territory rule;
- attestation binding, and the rejection of replayed and forged quotes;
- scoring, gates and weight mapping;
- what each backend would send to the real H3 and LTX runtimes, against fake runtimes;
- shared protocol vectors, verified identically in Python and TypeScript.

The subnet and SDK repositories each have CI that runs their own tests standalone. The platform's CI also needs a
`SUBNET_REPO_TOKEN` secret to check out the other two, and that secret isn't set yet.

## Status

### Built and tested without GPUs

- **Encryption:** HPKE and chunked blobs, byte-compatible in Python and TypeScript.
- **Gateway:**
  - routing, the owner-signed model switch, and the H3 territory rule with an LTX fallback;
  - price holds with automatic refunds, ciphertext-only uploads, and exact quotes;
  - enclave registration and re-attestation challenges, receipt checks, and public provenance lookup.
- **Worker:** the full enclave job loop against a simulated TEE, with a placeholder renderer covering every mode.
- **Validator:**
  - nonce challenges it verifies itself, canary jobs, and step audits;
  - scoring split by the switch, reliability and attestation gates, and chain weight mapping with a dry run;
  - a main validator and auditors: auditors apply its signed findings and flag weights that diverge.
- **Website and studio:** encryption in the browser, every generation mode, storyboards, plans, Elements, share links,
  certificates, a verify page, the admin console and the developer docs.
- **Generation features:**
  - text, image, first and last frame, and reference modes;
  - edits (retake and audio-to-video);
  - long videos as storyboards of chained shots;
  - plans written by the Director from a brief;
  - Elements (encrypted reusable characters, products, places, styles and voices).
- **Accounts and payments:**
  - email sign-in, web sessions, API keys, and an integer ledger;
  - top-ups by Stripe card payments, USDT through NOWPayments, and TAO or subnet alpha sent from a linked wallet;
  - payments tested against fakes of each provider (`platform/gateway/PAYMENTS.md`).
- **Operations:**
  - signed webhooks with retries, per-account rate limits, and body limits;
  - Postgres row locking and an S3-compatible blob store;
  - JSON logs, metrics and Sentry;
  - container images and a Compose stack.
- **Moderation:** strikes and restrictions, reports, legal holds, and CyberTipline reporting.
- **Miner identity and Sybil resistance:**
  - a hotkey proof bound to the attested enclave;
  - verified hardware identities (TDX PPID, GPU UEID) bound to one hotkey's live enclave;
  - per-GPU registration collateral read from the chain.
- **Verified mode:** per-step latent commitments signed into receipts, and validators replaying a random step
  bitwise. The replay ran end to end with a deterministic dev denoiser. See `subnet/VERIFIED_MODE.md`.
- **Turbo track:** owner-signed competitions for faster model variants. See `subnet/TURBO.md`.
- **Safety gate:** a normalizing blocklist, a Qwen3Guard prompt classifier and frame classifiers, all failing closed.
- **C2PA:** a manifest embedded before sealing, under short-lived certificates that the gateway's CA issues only to
  freshly attested enclaves.
- **Tools:** `kuno-preflight` (can this machine mine?) and `kuno-plan` (what exactly would be sent to the model).

### Run on rented GPUs, without confidential computing

These GPU tests ran on Shadeform rentals, and `scripts/gpu-test/` repeats them. Results are in `research/` and
`papers/agent.md`.

- **LTX-2.5 on one RTX PRO 6000 Blackwell:**
  - Fast and Pro clips through a real gateway;
  - storyboards, and plans in both privacy modes;
  - retakes up to 18 s, and audio-to-video.
- **LTX-2.5 4K:** 1440p and 2160p on an RTX PRO 6000 and on an H200.
- **MiniMax H3 and H3 Director (`h3-reference`) on 4× H200.** On 2026-09-17, full H3 and H3 Turbo also ran through the
  worker and a real gateway, including two GPU groups on one 8-GPU server.
- **H3 Turbo on one H200 (2026-09-18):** a 10 s clip through the worker and a real gateway, with a peak of 134,935 MiB
  of 143,771.
- **SageAttention for H3 Turbo:**
  - Measured at 6.5% faster. The owner compared the clips by eye and made it Turbo's default on H200s.
  - The first image built with it fell back to FlashAttention on a GPU. The fix is in the subnet (`afab6c1`) but has
    not yet run on a GPU.
- **The safety classifiers:** run on benign clips only, which shows the path works, not what it catches.
- **Measured cost per second of video:** `research/pricing/` and `subnet/PRICING.md`.

### Written, not yet run on real hardware or live services

- **Attestation:** TDX quote verification (tested on real sample quotes and Intel collateral) and NVIDIA GPU evidence.
  No confidential VM with NVIDIA confidential computing has run the worker yet, and the golden measurements aren't
  published.
- **Verified mode on GPUs:** determinism, step replay and tolerance calibration (`subnet/VERIFIED_MODE.md`).
- **The live chain:** Bittensor weight setting, collateral and Turbo extrinsics. The local chain ran; testnet needs
  test TAO.
- **Live money:** real Stripe, NOWPayments and on-chain payments.
- **Accuracy and load:** the safety classifiers' accuracy, and load testing.

### Not built yet

- C2PA Trust List membership for the KunoWorld root (HSM custody, OCSP, conformance), and a production timestamp
  authority.
- The confidential VM image's measured boot chain, as run on real hardware.
- The enterprise tier (routing only to hardware in verified data centres).

## Licence notes

- **MiniMax H3** is used under the MiniMax H3 Community License. It excludes the EU, UK, South Korea and the US unless
  MiniMax grants written authorization, and that applies to testing too. The gateway enforces it with
  `kuno_protocol.regions` and the switch's `h3_authorized_everywhere` flag.
- **LTX-2.5** is used under the LTX-2 Community License.
