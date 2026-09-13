# KunoWorld

Private, verifiable AI video generation on a Bittensor subnet. The design: customers generate
video with **MiniMax H3** and **LTX-2.5** on GPUs inside hardware enclaves (Intel TDX + NVIDIA
confidential computing); prompts, reference media and the finished video are encrypted end to
end between the customer and an attested enclave, so the platform and the GPU operator only
ever handle ciphertext; and every video comes back with an enclave-signed certificate anyone
can verify. The encryption and certificates work today against a simulated enclave. Real
hardware attestation and GPU serving are not built yet — see [Status](#status).

Website: **kunoworld.com**. The research behind the design is in [research/](research/).

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

**Written, not yet run on GPUs**
- The H3 backend (official SGLang server; LightX2V Turbo script) and the LTX-2.5 backend, both
  as per-job cold starts (`KUNO_BACKEND=cold`) and as resident runtimes that keep each profile
  loaded (`KUNO_BACKEND=real`).
- Bittensor weight setting, unverified against the live chain.

**Not built yet**
- Real TDX quote verification (dcap-qvl / Intel QVL) and NVIDIA GPU evidence (NVAT).
- The confidential VM image (reproducible, dm-verity weights) and golden manifest publishing.
- Hardware-identity registry and collateral, deterministic verified mode with step-replay
  audits, the Turbo-track mechanism.
- Accounts, payments, webhooks (the API stores `webhook_url` but never calls it), C2PA manifests, real content classifiers (the safety gate
  is a placeholder), Postgres/S3, rate limiting.

## Licence notes

MiniMax H3 is used under the MiniMax H3 Community License, which excludes the EU, UK, South
Korea and the US unless MiniMax grants written authorization; the gateway enforces this with
`kuno_protocol.regions` and the switch's `h3_authorized_everywhere` flag. LTX-2.5 is used
under the LTX-2 Community License.
