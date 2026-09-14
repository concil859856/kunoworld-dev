# KunoWorld

Private, verifiable AI video generation on a Bittensor subnet. Customers generate video with
**MiniMax H3** and **LTX-2.5**, and choose per job how private it is. In **Private** mode the job
runs on GPUs inside hardware enclaves (Intel TDX + NVIDIA confidential computing), and prompts,
reference media and the finished video are encrypted end to end between the customer and an
attested enclave. In **Standard** mode the platform handles the job in readable form, so it can
run on any miner. Every video comes back with an enclave-signed certificate anyone can verify.
The encryption and certificates work today against a simulated enclave. Real hardware
attestation and GPU serving are not built yet — see [Status](#status).

Website: **kunoworld.com**. The research behind the design is in [research/](research/).

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
  reported as illegal (child sexual abuse material) and content under a legal preservation hold. Every such view
  is logged. In Private mode, KunoWorld can't open a video at all unless whoever reports it supplies its key.
- **No NSFW.** Sexual and NSFW content is not allowed in either mode. Prompts are checked inside the enclave in both
  modes (and at the gateway for Standard jobs), and every finished video's frames are checked before it is signed.
  Blocked jobs count as strikes against the account.
- **Enforcement never needs to look.** Private content is policed by those in-enclave checks, account strikes and
  restrictions, reports, and signed provenance that traces a surfaced copy back to its job.
- **Sign-in.** Customers and operators sign in by email; the website keeps the session in an HttpOnly cookie and
  never gives the browser a token. API keys exist only for developers using the API.

Prices are placeholders until they are set. The legal entity and its jurisdiction are not decided yet, so the
terms and privacy policy remain drafts. Details: [subnet/PRIVACY_MODES.md](subnet/PRIVACY_MODES.md),
[subnet/SECURITY.md](subnet/SECURITY.md), and the gateway's `STANDARD_MODE.md` and `MODERATION.md`.

## Layout

Four private repositories, cloned side by side. `subnet/` and `sdk/` are written to be
made public later: the enclave code must be auditable for the privacy claim to mean
anything, and third-party validators need to run the validator.

| Folder | Repository | What it is |
|---|---|---|
| [subnet/](subnet/) | [kunoworld-subnet](https://github.com/concil859856/kunoworld-subnet) | wire protocol, miner worker (runs inside the confidential VM), validator |
| [sdk/](sdk/) | [kunoworld-sdk](https://github.com/concil859856/kunoworld-sdk) | Python and JavaScript clients that encrypt on the customer's device |
| [platform/](platform/) | [kunoworld-platform](https://github.com/concil859856/kunoworld-platform) | gateway API, and the website and studio |
| this directory | [kunoworld-dev](https://github.com/concil859856/kunoworld-dev) | workspace, dev scripts, integration tests, research |

Subnet documentation lives with the code it describes: [PROTOCOL.md](subnet/PROTOCOL.md)
(byte-level wire spec), [MINING.md](subnet/MINING.md), [VALIDATING.md](subnet/VALIDATING.md)
and [SECURITY.md](subnet/SECURITY.md) (what the enclave protects and what it does not).

## How a request flows

```
browser / SDK ──seal(prompt, params as AAD)──► gateway ──queue──► worker in TDX CVM ──► model runtime (H3 / LTX)
     ▲   encrypt inputs with HPKE-exported key       │                 │ decrypt, safety check, generate
     │                                               │                 │ encrypt video with HPKE-exported output key
     └──── download ciphertext, verify receipt, decrypt locally ◄──────┘ sign receipt with attested key
```

1. The SDK asks `/v1/route` which model serves the request (owner switch + licence region
   rules + capacity) and gets attested enclaves. It verifies the attestation itself.
2. It opens an HPKE session to the enclave key, uploads inputs encrypted with the exported
   input key, and seals the private payload with the public params, job id, enclave id and
   blob ids as associated data.
3. The gateway prices and queues ciphertext. Changing any public parameter makes decryption
   fail inside the enclave.
4. The worker decrypts, runs the in-enclave safety gate, generates, encrypts the MP4 with
   the output key, uploads it, and signs a receipt (digests only, no content).
5. The SDK checks the receipt signature and digests, then decrypts on the device.

## Quickstart (local, mock GPUs, real encryption)

Requires `uv`, `ffmpeg`, and Node 20+ for the JavaScript SDK.

```bash
uv sync
scripts/dev.sh            # gateway on :8080 + a mock-TEE worker serving every profile
```

Generate a video with the Python SDK:

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

Other entry points:

```bash
cd platform/web && npm run dev              # the studio at localhost:3000
kuno-validator once --canary ltx-2.5-fast   # one validator round: attest, canary, score
kuno-preflight --no-tee                     # can this machine mine? what is missing?
kuno-plan h3-reference reference_to_video   # exactly what we would send to the model runtime
```

## Tests

```bash
scripts/check.sh          # python, JavaScript SDK, web typecheck/lint/build
scripts/check.sh --web    # also the Playwright browser suite (starts the backend itself)
```

145 Python tests, 8 JavaScript tests and the browser suite currently pass. Between them
they cover: the encrypted round trip end to end; that no plaintext prompt, input or output
reaches the gateway's database or blob store; that a relay tampering with public parameters
makes the job fail inside the enclave; that a crashing model never leaks the prompt into
logs or failure messages; the owner switch and the H3 territory rule; attestation binding,
replay and forged-quote rejection; scoring, gates and weight mapping; what each backend
would send to the real H3 and LTX runtimes, exercised against fake runtimes; and shared
protocol vectors verified identically in Python and TypeScript.

Both public repositories have CI that runs their own tests standalone.

## Status

**Built and tested**
- End-to-end encryption (HPKE + chunked blobs), byte-compatible in Python and TypeScript.
- Gateway: routing, owner-signed model switch, H3 territory rule with LTX fallback, price
  holds with automatic refunds, ciphertext-only uploads, enclave registration and
  re-attestation challenges, receipt checks, public provenance lookup.
- Worker: the full enclave job loop against a simulated TEE, with a placeholder renderer
  covering every mode.
- Validator: nonce challenges it verifies itself, canary jobs, scoring split by the switch,
  reliability and attestation gates, chain weight mapping with a dry run.
- Website and studio: browser-side encryption, all generation modes, certificates, verify
  page, developer docs.
- Tools: `kuno-preflight` (can this machine mine?) and `kuno-plan` (what exactly we send).

- Accounts: email sign-in links, web sessions, API keys, an integer ledger, the account page.
- Top-ups: Stripe card payments, USDT through NOWPayments, TAO and subnet alpha sent to a
  treasury coldkey from a linked wallet (tested against fakes of each provider; the chain
  reader was checked read-only against finney). See `platform/gateway/PAYMENTS.md`.
- Signed webhooks with retries, per-account rate limits, body limits, Postgres row locking,
  an S3-compatible blob store, JSON logs, metrics, Sentry, container images, a compose stack.
- Validator: receipts re-verified against attested enclave keys, canary scoring, replay
  detection, signed switches that can't be rolled back.
- Miner identity: a hotkey proof bound to the attested enclave, required in production.
- Sybil resistance: verified hardware identities (TDX PPID, GPU UEID) bound to one hotkey's
  live enclave at the gateway, deduplicated again by validators, and per-GPU registration
  collateral read from the chain (the storage read was checked against finney).
- Verified mode: per-step latent commitments signed into receipts, retained openings, a gateway
  audit relay limited to a validator's own canaries, and validators replaying a random step
  bitwise (end to end with a deterministic dev denoiser). See `subnet/VERIFIED_MODE.md`.
- Turbo track: owner-signed competitions, hotkey-signed submissions committed on chain,
  attested benchmark jobs pinned to a candidate image, mechanism-1 weights, adoption tooling.
  See `subnet/TURBO.md`.
- Safety gate: normalizing blocklist, an optional Qwen3Guard prompt classifier and frame
  classifiers over the rendered video (all fail closed).
- C2PA: a manifest embedded before sealing, under short-lived certificates the gateway's CA
  issues only to freshly attested enclaves, trusted against the KunoWorld root.

**Written, not yet run on real hardware or live services**
- The H3 backend (official SGLang server; LightX2V Turbo script) and the LTX-2.5 backend, both
  as per-job cold starts (`KUNO_BACKEND=cold`) and as resident runtimes that keep each profile
  loaded (`KUNO_BACKEND=real`).
- TDX quote verification (dcap-qvl, tested on real Phala quotes and Intel collateral) and
  NVIDIA GPU evidence (`nvattest` collection, NRAS or local verification); the production
  attestation policy (`KUNO_ATTESTATION=production`); the worker image and dm-verity weights
  script (`subnet/image/CVM.md` lists the on-host checks).
- Bittensor weight setting, unverified against the live chain.
- Real Stripe, NOWPayments and on-chain payments; the CI workflows; load and stress testing.
- Verified-mode determinism and step replay on GPUs (the LTX-2.5 and H3 hooks and executors
  are written; `subnet/VERIFIED_MODE.md` lists the Phase 0 checks before penalties go live).
- Collateral and Turbo extrinsics on the live chain (storage and call names were read from
  finney metadata; nothing was submitted), and the collateral amount per GPU.
- The safety classifiers with real weights inside an image, and any accuracy evaluation.

**Not built yet**
- C2PA Trust List membership for the KunoWorld root (HSM custody, OCSP, conformance).
- A timestamp authority for production C2PA signing.
- The confidential VM image's measured boot chain and published golden measurements.

## Licence notes

MiniMax H3 is used under the MiniMax H3 Community License, which excludes the EU, UK, South
Korea and the US unless MiniMax grants written authorization; the gateway enforces this with
`kuno_protocol.regions` and the switch's `h3_authorized_everywhere` flag. LTX-2.5 is used
under the LTX-2 Community License.
