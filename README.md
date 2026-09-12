# KunoWorld

Private, verifiable AI video generation on a Bittensor subnet. Customers generate
video with **MiniMax H3** and **LTX-2.5** on GPUs that run inside hardware enclaves
(Intel TDX + NVIDIA confidential computing). Prompts, reference media and the finished
video are encrypted end to end between the customer and an attested enclave; the
platform and the GPU operator only ever handle ciphertext. Every video comes back with
an enclave-signed certificate that anyone can verify.

Website: **kunoworld.com**. The research and plan behind this repo are in [research/](research/).

## Layout

The folders map to three future repositories.

| Folder | Repo | Visibility | What it is |
|---|---|---|---|
| [subnet/protocol](subnet/protocol) | `kunoworld/subnet` | public | Wire protocol: HPKE job envelope, blob format, model profiles, the H3/LTX switch, attestation, receipts |
| [subnet/worker](subnet/worker) | `kunoworld/subnet` | public | Miner worker: the whole enclave application (attest, pull, decrypt, generate, seal, sign) |
| [subnet/validator](subnet/validator) | `kunoworld/subnet` | public | Validator: attestation challenges, canary jobs, scoring, weight setting |
| [sdk/python](sdk/python), [sdk/js](sdk/js) | `kunoworld/sdk` | public | Client SDKs that encrypt on the customer's device |
| [platform/gateway](platform/gateway) | `kunoworld/platform` | private | API gateway: accounts, pricing, routing, ciphertext job queue, blob store, provenance lookup |
| [platform/web](platform/web) | `kunoworld/platform` | private | Website and creation studio |

The enclave code, validator and SDKs are public on purpose: customers (and MiniMax,
when reviewing our license application) must be able to audit that the enclave cannot
leak content and reproduce the image that attestation measures, and third-party
validators must be able to run the validator.

## How a request flows

```
browser / SDK ──seal(prompt, params as AAD)──► gateway ──queue──► worker in TDX CVM ──► model runtime (H3 / LTX)
     ▲   encrypt inputs with HPKE-exported key       │                 │ decrypt, safety check, generate
     │                                               │                 │ encrypt video with HPKE-exported output key
     └──── download ciphertext, verify receipt, decrypt locally ◄──────┘ sign receipt with attested key
```

1. The SDK asks `/v1/route` which model serves the request (owner switch + license region
   rules + capacity) and gets attested enclaves. It verifies the attestation itself.
2. It opens an HPKE session to the enclave key, uploads inputs encrypted with the exported
   input key, and seals the private payload with the public params, job id, enclave id and
   blob ids as AAD.
3. The gateway prices and queues ciphertext. Changing any public parameter makes
   decryption fail inside the enclave.
4. The worker decrypts, runs the in-enclave safety gate, generates, encrypts the MP4 with
   the output key, uploads it, and signs a receipt (digests only, no content).
5. The SDK checks the receipt signature and digests, then decrypts on the device.

## Quickstart (local, mock GPUs, real encryption)

Requires `uv`, `ffmpeg` (or the bundled imageio-ffmpeg), Node 20+ for the JS SDK.

```bash
uv sync
scripts/dev.sh            # gateway on :8080 + a mock-TEE worker serving every profile
```

Then generate a video with the Python SDK:

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

Run a validator round (challenges every enclave, sends a canary, prints weights):

```bash
KUNO_DATA_DIR=data uv run kuno-validator once --canary ltx-2.5-fast
```

## Tests

```bash
uv run pytest                                  # protocol, end-to-end, JS↔Python interop
cd sdk/js && npm install && npm run build && npm test
```

The end-to-end suite runs a real gateway and mock-TEE workers per test and checks, among
other things, that no plaintext prompt, input or output ever lands in the gateway's
database or blob store, that a relay tampering with public parameters makes the job fail
inside the enclave, that the owner switch and H3 region rule reroute to LTX, and that the
validator attests and scores miners.

## Status

**Built and tested**
- End-to-end encryption (HPKE + chunked blobs), byte-compatible in Python and TypeScript.
- Gateway: routing, owner-signed model switch, H3 territory rule with LTX fallback, price
  holds with automatic refunds on failure, ciphertext-only uploads, enclave registration
  with nonce-bound attestation, re-attestation challenges, receipt checks, public provenance.
- Worker loop with a mock TEE and an ffmpeg mock renderer covering every mode.
- Validator: nonce challenges it verifies itself, canary jobs, VCU scoring split by the
  switch, reliability and attestation gates.
- Model profiles for all H3 and LTX-2.5 modes, per the official inference code.

**Written, not yet run on GPUs**
- H3 backend (official SGLang server; LightX2V Turbo script) and LTX-2.5 backend
  (official `ltx_pipelines` modules). Both need Phase 0 validation, and both currently
  cold-start per job; serving needs resident runtimes.
- Bittensor weight setting (`kuno-validator ... --netuid`), unverified against the live chain.

**Not built yet**
- Real TDX quote verification (dcap-qvl / Intel QVL) and NVIDIA GPU evidence (NVAT);
  the TDX quote parser and binding checks are in place.
- The confidential VM image (dstack-based, reproducible, dm-verity weights) and golden
  manifest publishing.
- Hardware-ID registry and collateral, deterministic "verified mode" with step-replay
  audits, the Turbo-track mechanism.
- Accounts, payments, webhooks, C2PA manifests, content classifiers (the safety gate is a
  placeholder), Postgres/S3, rate limiting.

## License notes

MiniMax H3 is used under the MiniMax H3 Community License, which excludes the EU, UK,
South Korea and the US unless MiniMax grants written authorization; the gateway enforces
this with `kuno_protocol.regions` and the switch's `h3_authorized_everywhere` flag. LTX-2.5
is used under the LTX-2 Community License.
