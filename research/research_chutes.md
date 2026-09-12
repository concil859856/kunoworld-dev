# Chutes (Bittensor SN64, Rayon Labs / chutes.ai): Technical and Economic Teardown

Research date: 2026-09-11. Method: cloned `chutesai/{chutes, chutes-miner, chutes-api, graval, sek8s, chutes-audit}` at HEAD (chutes-api HEAD 3b5609f, 2026-09-03; sek8s HEAD 168804d, 2026-09-03; chutes-miner HEAD e32943e, 2026-08-05), GitHub commit history via the API, live public API (`api.chutes.ai/chutes/`), chutes.ai docs, and secondary sources.

Legend: **[CODE]** = read in source at HEAD. **[DOC]** = official Chutes docs/README. **[2nd]** = secondary/third-party source. **[UNVERIFIED]** = claim I could not confirm from a primary source.

> **Important caveat: the public docs are stale.** The docs page https://chutes.ai/docs/miner-resources/scoring still describes a 7-day window with weights of 55/25/15/5. https://chutes.ai/docs/miner-resources/overview still describes GraVal. Neither matches the code at HEAD. The code is the source of truth below.

---

## 1. Architecture

### 1.1 How a chute is defined (SDK: `chutesai/chutes`)
- **Image DSL** [CODE] `chutes/image`: `Image(username, name, tag).from_base(...).run_command(...).apt_install(...).set_user(...)`. Example: https://github.com/chutesai/chutes/blob/main/examples/wan21.py
- **Chute** [CODE] `chutes/chute/base.py`: `Chute(username, name, image, node_selector, concurrency, readme, ...)`. It has `@chute.on_startup()` hooks (model load) and `@chute.cord(...)` endpoints.
- **Cord** [CODE] `chutes/chute/cord.py`, which takes these arguments:
  - `public_api_path`, `method`, `stream`
  - `input_schema` / `minimal_input_schema` (pydantic)
  - `output_content_type` (e.g. `video/mp4`)
  - `passthrough`, `passthrough_path`, `passthrough_port`: proxy to an inner server such as vLLM/SGLang
  - `sglang_passthrough`
- **NodeSelector** [CODE] `chutes/chute/node_selector.py`: `gpu_count` 1–8, `min_vram_gb_per_gpu` 16–140, `include` / `exclude` GPU short names. The server resolves it to `supported_gpus` and a `compute_multiplier`.
- **Templates** [CODE] `chutes/chute/template/`: `vllm.py`, `sglang.py`, `diffusion.py`, `embedding.py`. At HEAD the live catalog is overwhelmingly `vllm` (476 of 491 chutes) [live API].
- **Jobs** [CODE] `chutes/chute/job.py`: non-API workloads (training, server rental). They take `ports`, `timeout` (None or 30 s–24 h), `upload`, and `ssh` (port 2202).
- **Workflow**: `chutes build` sends the image to the validator's **forge**. `chutes deploy` registers the chute with the validator.

### 1.2 Validator / API side (`chutesai/chutes-api`)
- **One dominant validator.** It runs everything: FastAPI, socket.io/websocket to miners, Postgres, Redis, the forge (image builds), a private docker registry, GraVal GPU workers, `chute_autoscaler.py`, `watchtower.py`, `metasync/` (weight setting), `audit_exporter.py`, `nv-attest`, and server/TEE attestation endpoints. [CODE] https://github.com/chutesai/chutes-api
- **Validators are told to use a child hotkey rather than run their own.** README: "we strongly suggest making use of the child hotkey feature instead, with hotkey `5Dt7HZ7Zpw4DppPxFM7Ke3Cm7sDAWhsZXmM5ZAmE7dSVJbcQ`… The chutes validator hotkey take is set to 0%." Running a full validator needs "at least 8x h200s" for GraVal work, Postgres, k8s, and so on. [DOC] https://github.com/chutesai/chutes-api/blob/main/README.md
- **Forge** (`api/image/forge.py`): controlled multi-stage builds. It generates filesystem and bytecode baselines, runs vulnerability scans, and **cosign-signs** every image. [DOC] https://chutes.ai/docs/core-concepts/security-architecture
- **Registry**: miners never pull from Docker Hub. Each GPU node sees images as `[validator-hotkey].localregistry.chutes.ai:30500/...`, which resolves to 127.0.0.1. A miner-side nginx proxy injects hotkey signatures, and the validator swaps them for registry basic auth. [DOC] chutes-miner README.
- **Lite validators: `chutesai/chutes-audit`** [DOC]:
  - The validator commits hourly audit exports on-chain via `set_commitment`.
  - The auditor downloads them (instance_audit + compute_history), recomputes incentives, and can set weights itself.
  - Reported delta versus the metagraph is <0.2%.
  - https://github.com/chutesai/chutes-audit

### 1.3 Request routing
- **`LeastConnManager`** [CODE] `api/instance/util.py`:
  - Least-connections, with random choice among ties.
  - Connection counts are held in a sharded Redis (`cc:{chute}:{instance}`).
  - **Prefix-aware routing** for LLM KV cache: `pfx:{prefix_hash}:{instance}` keys. Instances likely to hold the cached prefix are preferred when within 7 connections of the minimum. "Always use prefix aware routing" commit: 2026-01-12.
- **Instance disablement** [CODE] `api/constants.py`:
  - On consecutive errors an instance is disabled for 90 s, increasing linearly.
  - More than 5 disables in a sliding hour means the instance is deleted.
  - "Cascade failure" guard: if more than 50 instances are pending deletion within 45 s, deletions are skipped (assumed network outage).
- **Request timeouts** [CODE] `api/chute/util.py` ~L802:
  - Default read timeout is **1800 s** for current chutes versions (600 s for <0.3.59, 900 s for <0.4.2).
  - Streaming vLLM calls have **no read timeout**; dead connections are caught by TCP keepalive instead.
- **All validator-to-miner traffic is encrypted and signed** with the validator hotkey. Legacy: AES keyed by GraVal. Current: TEE instance keys plus optional client E2E.

### 1.4 Miner side (`chutesai/chutes-miner` + `chutesai/sek8s`)
- **Two node roles** [DOC] https://github.com/chutesai/chutes-miner/blob/main/README.md:
  - **Control plane**: one non-GPU server with k3s, the miner API, **gepetto**, Postgres, Redis, the registry proxy and Grafana. Provisioned with ansible.
  - **Workers**: each GPU server runs an **Intel TDX confidential VM** with k3s, provisioned with `sek8s/host-tools`. "The chutes network is now TEE-exclusive… a node without the `chutes/tee=true` label will be rejected during `add-node`."
- **Hardware rules**: bare metal or VM only (no Runpod/Vast). Static unique IPs with 1:1 port mapping. The k8s NodePort range 30000–32767 must be public. RAM should be at least total VRAM.
- **What the miner controls:**
  - **Gepetto strategy**, "the main thing to optimize". Gepetto decides which chutes to deploy, on which servers (it takes `--hourly-cost` per GPU into account), when to scale up or down, whether to chase bounties (`bounty_changed` → `scale_chute(..., preempt=True)`), and when to preempt.
  - Preemption rules [CODE] `gepetto.py preempting_deploy`: never preempt private deployments; never preempt the only global instance of a chute; never preempt an instance whose multiplier is ≥ the new chute's effective multiplier; otherwise preempt the lowest-multiplier instances first.
  - Hardware inventory, cache sizes, and which validators to serve.
- **What the validator controls:**
  - The chute catalog, images and code, node selectors, and pricing.
  - Autoscaler targets. The validator decides how many instances each chute should have, and miners compete to fill them.
  - Bounty creation, request routing, all verification, and scoring.
  - It can purge any instance.
- **Launch flow** [CODE] `api/instance/router.py`, `api/instance/util.py`:
  1. The miner gets a JWT launch config.
  2. The pod starts and claims the launch config.
  3. The validator verifies the instance: TEE path `verify_tee_chute`, or legacy GraVal PoVW.
  4. The instance is activated, then routable.
- **The autoscaler owns demand.** Constants [CODE] `api/constants.py`:

| Constant | Value |
|---|---|
| `UTILIZATION_SCALE_UP` | 0.5 |
| `UTILIZATION_SCALE_DOWN` | 0.2 |
| `RATE_LIMIT_SCALE_UP` | 0.03 (3% of requests rate-limited) |
| `UNDERUTILIZED_CAP` | 2 instances |
| Scale-down lookback / max drop vs 90-min moving average | 90 min / 0.6 |
| `BOUNTY_COOLDOWN_SECONDS` | 600 |
| Bounty lifetime (public / private / affine) | 86400 s / 3600 s / 7200 s |

---

## 2. Verification and anti-cheat, and how it evolved

### 2.1 Era 1 (Nov 2024 to ~mid-2026): GraVal plus software integrity
- **GraVal** ("Graphics card validation") https://github.com/chutesai/graval.
  - The repo ships **only compiled `.so` binaries** (`libgraval-validator.so`, `libgraval-miner.so`) plus a thin Python wrapper. The README says "More details to come…". The last commit was 2025-07-25.
  - The mechanism is closed source. Per docs: matmuls seeded by device info. Traffic is "encrypted with keys that can only be decrypted by the GPU advertised". GPUs are verified once at node add, and keys are re-derived per deployment. It verifies that about 95% of VRAM is available. [DOC] https://chutes.ai/docs/miner-resources/overview
- **graval-priv / PoVW** ("Proof of Consecutive VRAM Work"): OpenCL + clBLAS consecutive matmuls with diagonal slices. This produces a speed and VRAM signature and derives an AES-256 key from the GPU UUID plus a validator seed. [DOC] https://chutes.ai/docs/core-concepts/security-architecture
  - Per-GPU timing budgets live in `api/gpu.py`, e.g. `b200: graval iterations 2, estimate 75 s`, `b300: 1 iteration, 430 s` [CODE].
  - Operational pain: issue #126 (2026-04-12). On RTX Pro 6000, PoVW took about 101 s, but the validator deleted pending instances after 60–90 s, so proofs always hit a 404. https://github.com/chutesai/chutes-miner/issues/126
- **cfsv** (`chutes/cfsv`, `cfsv_v2..v4` binaries): builds a filesystem index and digests seeded by a validator challenge, compared with forge baselines.
- **inspecto** (`chutes-inspecto.so`): hashes the Python bytecode of loaded modules to detect stdlib overrides and logic bombs.
- **envdump**: snapshot of env vars, filesystem, kernel and loaded modules.
- **chutes-net-nanny**: egress allowlist, DNS protection, and encryption of the main chute source. It "intentionally causes a segfault if any attempt is made to exec into the pod, run a sidecar container, or connect to a local service not in the process tree." [DOC]
- **cllmv**: per-token verification hashes in SGLang/vLLM, "HF model name and exact revision hash cryptographically bound into the per-token proofs" [DOC]. Enabled for vLLM 2026-01-11, with many edge-case fixes in January 2026 [commits]. Session HMAC via `cllmv_session_init` [CODE `chutes/entrypoint/run.py`].
- **watchtower.py** [CODE], which runs random continuous checks:
  - `check_weight_files`: SHA256 of a random weight file at a random offset, compared with Hugging Face.
  - `check_live_code`: `/proc/1/cmdline` must equal the expected command, and `/app/{chute.filename}` must byte-equal the registered code.
  - `verify_fs_hash` (cfsv) and `check_runint` (runtime integrity challenge, AES-GCM, chutes ≥0.5.0).
  - `verify_bytecode_integrity`: manifest v2, chutes ≥0.5.5. The docstring says it is "NOT wired into automation".
  - `check_instance_connections`: parses `/proc/net/tcp` for suspicious outbound connections.
  - `check_sglang`.
  - Failing a check or not responding means immediate removal.
- **Aegis** (`chutes-aegis.so`, LD_PRELOAD; added 2026-03-02 in chutes-api PR #100 and chutes PR #56) [CODE `chutes/entrypoint/run.py`, `cfsv_wrapper.py`]: CFSV is compiled into Aegis. It also handles challenge/response (`generate_challenge_response`, `verify_challenge_response`) and egress blocking.
- **Pattern across all of these:** security-critical components ship as obfuscated binaries (`chutes-aegis.so`, `chutes-inspecto.so`, `chutes-bcm.so`, graval `.so`).

### 2.2 Known exploits, incidents and hardening events (from the commit and issue record)
- **2025-11-03, chutes-api PR #61 "Fix affine exploit"** https://github.com/chutesai/chutes-api/pull/61. Default `allow_external_egress` changed to False. Affine and turbovision (SN44) chutes are forced to no egress. A minimum cllmv-capable SGLang image is required. This implies the exploit used external network egress and/or unverifiable inference on integrated-subnet chutes; the details are not public. **[UNVERIFIED specifics]**
- **2025-12-02, chutes issue #36 / PR #37 "7 Critical Security Vulnerabilities"** https://github.com/chutesai/chutes/issues/36, https://github.com/chutesai/chutes/pull/37. Findings in the chute runtime:
  - 540 s nonce replay window.
  - Path traversal: the validator can read any file on the miner.
  - JWT signature not verified.
  - Env-var injection (LD_PRELOAD / PYTHONPATH).
  - **"Predictable filesystem hash — anti-cheat bypass via precompute."**
  - Concurrency bypass after purge.
  - Both issue and PR were closed on 2025-12-03. I did not verify whether the PR was merged or the fixes landed separately.
- **2026-02-03 "Reduce opportunities to game boosts" (#97); 2026-02-10 "prevent demand boosts on free models to avoid manipulation" (#99); 2026-03-01 "Cap max boosts".** Together these show miners (or chute owners) were **manufacturing demand on free models** to raise the autoscaler urgency boost, and hence their compute multiplier.
- **2026-04-24 "Remove multi-hotkey restriction"** [CODE diff]. Coldkey-level de-dup, where only the best hotkey per coldkey was paid, was removed. Presumably it was pointless under TEE plus instance-based scoring, and easy to evade anyway.
- **2025-06-01**: after a Bittensor chain pause, Rayon Labs paid about 1.25k TAO to miners across SN64/56/19 out of owner emissions. https://x.com/rayon_labs/status/1929264732202012714
- **Operational friction**: miners needed the owner to delete orphan GPUs from the validator DB "multiple times per day", which led to a community tool. https://github.com/minersunion/sn64-tools
- I found **no public post-mortem** of a GPU-spoofing or GraVal bypass. The move to TEE, and blocking of the GraVal path, is the de facto answer. **[UNVERIFIED: whether GraVal was actually broken]**

### 2.3 Era 2 (Dec 2025 onward): TEE-exclusive
- GraVal is **deprecated and blocked**. `add-node` errors for any non-TEE node, and the `graval-bootstrap` package was removed [DOC chutes-miner README].
- The validator refuses GraVal launch configs for TEE chutes: "Can not claim a graval launch config for a TEE chute" [CODE `api/instance/router.py`].
- Software checks (Aegis/cfsv/cllmv/watchtower) still run inside the TEE, as defence in depth against a malicious *chute* image and for runtime continuity.

---

## 3. TEE (sek8s)

### 3.1 Timeline (commit dates plus posts)

| Date | Event |
|---|---|
| 2025-09-29 | `k3s-tee` branch merged in chutes-miner |
| 2025-11-14 / 11-15 | "Tee (#68)" in chutes-api; "K3s tee (#69)" in miner |
| 2025-12-09 | X post "Chutes TEE is live" https://x.com/chutes_ai/status/1998411097783570552 |
| Dec 2025 – Jan 2026 | Popular models progressively rerouted to "-TEE" chute variants: GLM-4.6 (12-12), DeepSeek V3-0324 (12-16), R1-0528 (12-26), InternVL3 (01-01), Devstral (01-09); TEE cache encryption (01-09) |
| 2026-03-02 | "increase incentive for cold start times (since they are quite bad on TEE nodes)" |
| 2026-03-03 | switched to `hf_transfer` "vs XET (massive slowdowns on TEE?)" |
| 2026-03-09 | "reject launch configs for legacy TEE infra" |
| 2026-03-11 | E2E public key bound into attestation (#116) |
| 2026-03-18 | TEE attestation docs published (#105) |
| 2026-04-23 | integrated-subnet chutes must be TEE (#136) |
| 2026-04-27 | "Prevent tee downgrade"; "Lock node_selector for TEE chutes" |
| 2026-05-12 | "tee only for new chutes" |
| 2026-05-28 | sek8s B200 host support done (spec `sek8s/docs/specs/b200-support.md`) |
| ~June 2026 | "moved to fully Trusted Execution Environments in June" [2nd, Tao.media] |
| 2026-07-01 | X post from tao.com: GLM 5.2 in TEE "alongside more than a dozen open models" https://x.com/taodotcom/status/2072384125781082224 |
| 2026-07-31 | chutes-miner README states the network is TEE-exclusive (#144) |
| **2026-09-11 (today)** | **Live API: 491 of 491 chutes have `tee: true`.** GPU selectors: 483 pro_6000-only, 6 h200, 1 b200, 1 b300. Most are private "Affine" miner-model chutes; 31 are public |

### 3.2 Hardware requirements [DOC] https://github.com/chutesai/sek8s/blob/main/host-tools/README.md
- An Intel TDX-capable CPU. Host OS Ubuntu **25.10 or 26.04**. Intel PCCS plus an API key for PCK certs (DCAP).
- **Validated topologies**:
  - 8×H200: NVSwitch required.
  - 8×B200: host-side Fabric Manager, with CX7 NVSwitch bridge PFs kept on the host. NVLink is encrypted in MPT CC mode.
  - 8×RTX Pro 6000: no NVSwitch.
  - B300 has a host profile but is **not validated**.
- NVIDIA confidential computing with **PPCIe** (Protected PCIe). The `nvidia-open` driver is required for Blackwell.
- No SSH into production TEE VMs. Management is via `chutes-miner-cli` plus a read-only system-status API. A debug image with SSH and no encryption exists for development [DOC `sek8s/docs/debug-mode.md`].

### 3.3 Attestation flow [DOC + CODE]
1. **Boot gate**: the guest root disk is **LUKS-encrypted**. The key is released by the Chutes attestation/key service only after a TDX quote whose MRTD/RTMRs match "golden" measurements. Endpoints [CODE `api/server/router.py`]:
   - `POST /servers/boot/attestation`
   - `POST /servers/{vm}/luks/attest`, `/luks/confirm`
   - `/provision`, `/provision/confirm`
   - quote type "runtime, RTMR3 extended"

   "Building the VM image yourself is insufficient unless you also control the policy + key server." [DOC `sek8s/docs/end-to-end-miner.md`]
2. **Measurement registry**:
   - `GET /servers/tee/measurements` is public: MRTD, boot RTMRs and runtime RTMRs per accepted configuration.
   - `/servers/tdx/host_profiles` fingerprints the host class. RTMR0 depends on the QEMU build, the `-cpu` string, CPU topology and passthrough inventory, so each hardware class needs its own measurement set.
   - `/servers/tdx/preflight`.
3. **Image admission**: the sek8s k8s API server has an admission controller that allows only images **cosign-signed** by the Chutes forge. SGLang binds to 127.0.0.1 with a password [DOC].
4. **Per-instance attestation** (`verify_tee_chute`, [CODE] `api/instance/util.py`):
   - The validator fetches evidence from the node's attestation proxy (NodePort 30443): TDX quote, NVIDIA GPU evidence, and a TLS cert.
   - Report data must equal `sha256(nonce + e2e_pubkey)` for chutes ≥0.6.0.
   - The cert hash is bound to the quote.
   - The validator verifies the quote (Intel DCAP / Intel Trust Authority), the GPU evidence (NVIDIA attestation SDK, `nv-attest` service), and `_require_rc_chute_owner` against the measurement.
5. **Third-party verification** [DOC] https://github.com/chutesai/chutes-api/blob/main/docs/tee-verification.md:
   - `GET /chutes/{id}/evidence?nonce=` and `GET /instances/{id}/evidence?nonce=` return quote, gpu_evidence, certificate, and an RSA `signature` over `attested_body` (attestation proxy ≥0.2.0).
   - Callers must re-verify when new instances appear, because instances scale dynamically.

### 3.4 End-to-end encryption of prompts
- Each instance generates an **ML-KEM-768** keypair inside the TEE at startup, and the public key is bound into the quote.
- The client flow:
  1. Call `GET /e2e/instances/{chute_id}`. It returns up to 5 instances, each with 10 single-use nonces, valid for 60 s. Rate limit is 10/min.
  2. Encapsulate with **ML-KEM-768 + HKDF-SHA256 + ChaCha20-Poly1305**.
  3. `POST /e2e/invoke`.
- Streaming uses an `e2e_init` event followed by encrypted `e2e` chunks.
- Usage (token counts) chunks are passed back for billing; commit 2026-06-24 "Optionally pass raw usage data chunks back to client in e2ee mode".
- Client libraries: `pip install chutes-e2ee` (httpx transport for the OpenAI SDK) https://github.com/chutesai/chutes-e2ee-transport, and `parachutes/e2ee-proxy` (OpenResty local proxy speaking the OpenAI, Anthropic and Responses APIs) https://github.com/chutesai/e2ee-proxy.
- **Without the E2E client, the Chutes API terminates TLS and sees plaintext.** In that case it re-encrypts to the instance. The docs call this "all communication between the user, the validator, and the miner is encrypted", but the validator is then in the trust boundary. [inference from CODE `api/e2e/router.py` vs normal invocation path]

### 3.5 Published or known limitations
- **Golden measurements and a circular root of trust.** Issue chutes-e2ee-transport #6 (2026-04-24, still open): "we cannot independently verify the software because the expected sek8s golden measurements (MRTD/RTMRs) aren't public… we must trust the central api.chutes.ai endpoint… security theater." https://github.com/chutesai/chutes-e2ee-transport/issues/6. The `/servers/tee/measurements` endpoint now exists in code, so this may be partially addressed; the open issue suggests it was not yet satisfying.
- **Centralized key release.** Only the Chutes key service can unlock miner VMs, which is a single point of failure and control. DR requires access to that service.
- **A TEE does not protect against malicious chute code.** The privacy policy notes that a chute which logs prompts would still leak them. Jon Durbin (2026-05-28): "TEE only matters if the code/workload is attested…" https://x.com/jon_durbin/status/2060043578051596331
- **Cold starts and model download are slow on TEE nodes** (commits 2026-03-02 and 03-03).
- Hardware is narrow: 8-GPU TDX servers with specific SKUs, plus Ubuntu 25.10/26.04 hosts.
- Side channels, TDX/NVIDIA CC firmware CVEs and PPCIe performance overhead are not discussed in Chutes docs. **[not addressed]**
- Some chute source code is not public. The live API returned empty `code` for `turbowani2v` and `LTX-25-Video`; `INTEGRATED_SUBNETS["chronoseek"].source_public=False`.

---

## 4. Incentive mechanism

### 4.1 Current formula (HEAD, since 2026-01-08, window changed 2026-04-20) [CODE]
Files: `metasync/constants.py`, `metasync/shared.py`, `metasync/set_weights_on_metagraph.py`, `api/chute/util.py::calculate_effective_compute_multiplier`, `api/bounty/util.py`, `chute_autoscaler.py`.

```
score(miner) = Σ_instances ∫_{window} compute_multiplier_instance(t) dt      # seconds × multiplier
weight(miner) = score / Σ score   → quantized to u16, set on-chain every hour at :00 UTC
window = last 1 day (SCORING_INTERVAL = "1 day")
```

**Instance eligibility** (`INSTANCES_QUERY`). An instance counts if `activated_at` is not null and at least one of these holds:
- it is still alive;
- it was deleted after living ≥1 h;
- `valid_termination`;
- the deletion reason is user balance, private-chute idle shutdown, or old version.

Consequences: instances killed in under 1 h earn **nothing**. That is the anti-churn and anti-spam rule. The startup period (`created_at` → `activated_at`) is paid at **0.3×**.

**Effective multiplier** (`calculate_effective_compute_multiplier`):
```
m = base
  × private_bonus      (2.0 private; 3.0 integrated-subnet chute; 1.3 private TEE)   # PRIVATE_INSTANCE_BONUS etc.
  × urgency_boost      (autoscaler 'chute.boost', public non-sponsored only, 0 < boost ≤ 20)
  × manual_boost       (admin knob, capped 20)
  × bounty_boost       (1.1 → 1.5 linear over 180 min of bounty age; BOUNTY_BOOST_MIN/MAX/RAMP)
  × TEE_BONUS          (2.25 if chute.tee)
base = (hourly_rate of cheapest supported GPU / max hourly_rate) × gpu_count
```
- `base` comes from `api/gpu.py normalize_scores`. The per-GPU figures are hourly_rate / 4.5 (B200/B300 = $4.5):

| GPU | Multiplier |
|---|---|
| B200 / B300 | 1.0 |
| MI300X | 0.667 |
| H200 | 0.611 |
| H100 SXM | 0.522 |
| H100 | 0.398 |
| RTX Pro 6000 | 0.40 |
| A100 80 GB | 0.267 |
| L40S | 0.189 |
| 4090 | 0.089 |

- The live API confirms `compute_multiplier: 0.4` for 1× pro_6000.
- The "× gpu_count" factor is inferred from the docstring "(GPU type * count)"; I did not read `NodeSelector.compute_multiplier` line by line.

**Urgency / revenue boost** (`chute_autoscaler.py` ~L2172):
```
boost = 1.0 + urgency_bonus × revenue_weight + revenue_bonus
```
- `urgency_bonus` ≤ 0.2, derived from smoothed urgency (rate-limit score up to 500, plus utilization score up to 100, times capacity pressure; saturates at 300).
- `revenue_weight` = clamp(revenue_per_instance / median, 0.1, 3.0).
- `revenue_bonus`:
  - active demand tier: min(0.25 × ratio, 1.0);
  - retention tier: min(0.25 × ratio, 0.75).
- In effect, **chutes that earn real USD pay miners more per GPU-second.** Commit 2026-03-23: "make rev more relevant in scoring".

**Multiplier drift after activation.** The instance's multiplier blends toward the current (bounty-free) target:
- hold for 0–2 h;
- ease in over 2–8 h;
- clamp after 8 h.

This is from the autoscaler docstring. `constants.BOUNTY_BOOST_DECAY_HOURS = 5` conflicts with it, and one docstring also claims bounty boost of "1.5x–4x"; the constants say 1.1–1.5. The code has stale comments. **[internal inconsistency]**

**Bounties** (`api/bounty/util.py`):
- Created by the autoscaler when a chute needs capacity, and broadcast to miners over Redis pubsub.
- Claimed atomically by the first instance launched for that chute.
- Nominal `amount = min(3·age_s + 100, 86400)`.
- In the current scoring, bounties matter **only through the multiplier boost**. `bounty_score` is computed but not used in `final_scores`.

**Weight setting** [CODE]:
- Hourly at the top of the UTC hour, with a 150-block `LastUpdate` guard and a 15-minute retry budget.
- `VERSION_KEY = 69420`.
- The Chutes validator, and auditors running `chutes-audit`, compute the same thing from the same exported data.

**Penalties** [CODE/spec]:
- There is no negative scoring; the penalty is lost time.
- Instance disable/delete on errors, blacklist (`metagraph_nodes.blacklist_reason`), and watchtower removal.
- "Thrash penalties" were removed on 2026-05-17.
- With a 1-day window, one hour of outage costs about 4.2% of score (about 0.6% under the old 7-day window) [spec `docs/specs/scoring-window.md`].
- **Invocations are no longer scored at all.** The spec says "scoring is now based entirely on instance compute units (not invocations)".

**Jobs**: the job multiplier equals the node-selector multiplier. H200-only jobs get ×16 (2025-07-08 hack) "so jobs have equal priority to normal chutes" [CODE `api/job/router.py`].

### 4.2 History of the mechanism [CODE git history]

| Period | Mechanism |
|---|---|
| ~Mar–May 2025 | 7-day window; features compute_units / invocation_count / unique_chute_count / bounty_count. Docs version: 55/25/15/5. Unique chute normalization: above median (count/max)^1.3, below median ^2.2 (2025-05-07 "Exponential on unique chute score"). Multi-UID punishment: only the best hotkey per coldkey paid |
| Jul 2025 | compute units normalized by moving-average seconds per step/token (2-day medians) |
| ~Oct 2025 snapshot (sha 256aa1b) | `FEATURE_WEIGHTS = {compute_units 0.52, invocation_count 0.20, unique_chute_count 0.20, bounty_count 0.08}`, 7 days |
| 2025-11-09 "Incentives overhaul" (#63) | base = instance lifetime × compute_multiplier; bonuses demand 0.35 / bounty 0.35 / breadth 0.30, `BONUS_WEIGHT 0.1`, `BONUS_EXP 1.4` |
| 2025-11-14 | TEE added to scoring |
| 2026-01-08 (#80) | "Dynamic instance incentives… remove bonus categories": everything folded into the per-instance compute_multiplier (urgency, bounty, TEE, private) |
| 2026-02/03 | anti-gaming of boosts; boost caps |
| 2026-04-20 (#132) | 1-day window, hourly clock-aligned weights; invocation CSVs dropped from audits |
| 2026-04-24 | multi-hotkey restriction removed |
| 2026-05-17 | thrash penalties removed |

---

## 5. Revenue and tokenomics

### 5.1 Pricing [CODE `api/constants.py`, `api/gpu.py`, live API]
- `COMPUTE_UNIT_PRICE_BASIS` = max hourly_rate = **$4.50/hr**. Per-chute price = basis × compute_multiplier. For example 1× RTX Pro 6000 = **$1.80/hr = $0.0005/s**; this is the live price for image, video and music chutes.
- **LLM per-token pricing** = hourly × gpu_count × 0.01358695 per 1M input, and × 0.05434782 per 1M output.
  - There is a concurrency surcharge ×16/c when concurrency is under 16.
  - Minimum $0.01. Cached prompt tokens 90% off.
  - Code comment example: 8×H200 at $2.3 gives $0.25 in / $1.00 out per 1M.
- **Diffusion**: per step = hourly × 0.002.
- Payments in TAO or fiat. Each user gets a unique bittensor coldkey for payments, with mnemonics double-encrypted in Postgres [DOC chutes-api README].

### 5.2 Subscriptions
- **2025-08-04**: Base $3/mo (300 req/day), Plus $10 (2,000/day), Pro $20 (5,000/day), Enterprise custom. The old free tier ($5 one-time deposit giving 200/day) was eliminated for new users. https://rpwithai.com/chutes-new-subscription-plans/
- Plus gets a 6% and Pro a 10% PAYG discount beyond quota [2nd] https://chutes.ai/llms.txt
- **Feb 2026**: a model tier was removed from Base because "heavy users were extracting 56x to 324x their subscription value" [2nd] https://ownyourmind.ai/tokenomics/chutes-bittensor-revenue-machine/
- **May 2026**: Base tier closed to new subscribers, and 7 models were removed on 2026-05-15 [2nd] https://simplytao.ai/blog/chutes-sn64-last-week-7-models-cut-294k-trillion-tokens

### 5.3 Reported revenue (conflicting figures)

| Source | Figure |
|---|---|
| Unsupervised Capital (≈ late 2025) [2nd] | **$4.3M ARR**, about 3 months after monetization; >120B tokens/day. https://www.unsupervised.capital/writing/bittensors-ai-compute-subnets-collectively-reach-20m-arr |
| Pine Analytics (Mar 2026), cited by Own Your Mind [2nd] | **$1.3–2.4M verified external ARR**; subsidy ratio 22–40:1 versus about 518 TAO/day of emissions (14.39% of network) |
| 0xSammy (2026-03-26) [2nd, single source] | "$22K/day, approaching $10M ARR". https://www.0xsammy.com/p/the-agentic-future-033126-intel-validates |
| Chutes "From Volume to Value" (Mar 2026) [2nd summary; page is client-rendered, could not fetch] | 45% fewer tokens over 6 weeks, revenue down about 25%, revenue per 1M tokens +37.7% since Feb 1, organic PAYG +20% in the last 10 days. https://chutes.ai/news/from-volume-to-value-building-a-sustainable-ai-inference-platform-2 |
| SimplyTao (~May 2026) [2nd] | trailing-90-day revenue **$1.41M** (about $5.7M annualized); latest day $16,451; $294K per trillion tokens |
| Tao.media [2nd] | "$43M in Q1 2026 real AI revenue". **Treat as UNVERIFIED/likely wrong**; inconsistent with every other source. https://www.tao.media/the-ultimate-guide-to-bittensor-2026/ |
| OpenRouter volume [2nd] | peak about 42B tokens/day (2026-02-07), about 6.8B/day in late March. Chutes self-reported 160B/day. OpenRouter currently lists only 6 Chutes models. https://openrouter.ai/provider/chutes |

### 5.4 Emissions and buyback
- dTAO split: 18% owner / 41% miners / 41% validators+stakers [2nd].
- SN64 held 14.39% of TAO emissions (Mar 2026), then **6.55%** (2026-08-15) [2nd].
- Rayon Labs' three subnets (SN64/56/19) held about 23.7% of emissions at the peak.
- **Revenue is used to "auto-stake" into SN64 alpha, i.e. buybacks** [2nd]. OAK Research: "All revenues generated on Chutes are used in an auto-staking mechanism, consisting of buying back the subnet's native token." https://oakresearch.io/en/analyses/innovations/rayon-labs-subnet-leader-bittensor-tao, CoinGecko https://www.coingecko.com/learn/top-bittensor-subnets-dtao. **[UNVERIFIED from a primary Chutes source; amounts and cadence not found]**
- **Owner emissions**: I found no published owner-take or burn policy **[UNVERIFIED]**. Validator take is 0% [DOC].

---

## 6. Image and video generation on Chutes

- **Yes, supported.** The SDK has a `diffusion` template, and there are SDK examples `wan21.py`, `flux_dev.py`, `flux_schnell.py`, `chroma.py`, `omnigen.py`, `infiniteyou.py`.
- **`wan21.py` example** [CODE]:
  - Wan2.1-T2V-14B plus I2V-14B-480P, pinned HF revisions.
  - `NodeSelector(gpu_count=8, include=[h100, h800, h100_nvl, h100_sxm, h200])`.
  - torch.distributed / xfuser across 8 ranks with a multiprocessing task queue.
  - Inputs: `steps` 10–30, `fps` 16–60, `frames` 81–241, resolutions up to 1280×720.
- **Live (2026-09-11) video/image chutes, all TEE, all 1× RTX Pro 6000 (min 80 GB), priced $0.0005/s** [live API]:

| Chute | Created | Concurrency | Cord / output |
|---|---|---|---|
| `turbowani2v` (TurboWan2.2 I2V A14B) | 2026-05-29 | 2 | `POST /generate`, `stream: False`, `output_content_type: video/mp4` |
| `LTX-25-Video` | 2026-08-13 | 3 | `/generate` (text/plain), `/health`, `/models` |

  Also live: `z-image-turbo`, `Qwen-Image-2512`, `Qwen-Image-Edit-2511`, `ACE-Step-15-Music-Generator`. llms.txt additionally mentions LTX 2.3 Video and Wan2.1.
- **How long jobs are handled:**
  - Video requests are **plain synchronous HTTP requests**: no streaming progress, no job queue.
  - They rely on the 1800 s read timeout; streaming LLMs have no read timeout.
  - Billing is per-second of compute (or per diffusion step), not per token.
  - There is a separate **Jobs** API for truly long work (timeout up to 24 h, ports, SSH, file upload, daily per-user job quotas) [CODE `chutes/chute/job.py`, `api/job/router.py`].
  - Max VLM asset (image/video input) is 100 MB [CODE `VLM_MAX_SIZE`].
  - Scoring is time-based (GPU-seconds × multiplier), so long video jobs are rewarded no differently from LLM serving. That is a nice property.

---

## 7. Lessons, criticisms, and recommendations for a TEE video-generation subnet

### Criticisms / weaknesses observed
1. **Extreme centralization.** One validator runs the product, builds and signs images, holds the LUKS key service, controls autoscaling, sets pricing, and effectively sets weights. Others are told to child-hotkey. chutes-audit mitigates this only by re-deriving weights from data the same validator exports.
2. **Emissions subsidy far exceeds revenue**: 22–40:1 by Pine's estimate. Self-reported volume and revenue were contradicted by independent data (160B vs about 7–12B tokens/day on OpenRouter).
3. **Security through obscurity.** GraVal, Aegis, inspecto and cfsv ship as closed `.so` binaries. Independent TEE verification depended on golden measurements not being public (issue #6).
4. **Constant mechanism churn**: at least 6 major scoring redesigns in about 18 months, plus stale docs (7-day, 55/25/15/5, GraVal still documented). That churn makes miner ROI hard to model.
5. **Gaming pressure moved to boosts.** Once scoring became "time × multiplier", fake demand to inflate boosts appeared (Feb 2026 fixes).
6. **TEE operational costs**: slow cold starts and model pulls, narrow hardware support, PoVW or attestation timeouts killing pending instances (#126), and dependence on the owner's key service.

### What to copy
- **Scoring on attested GPU-time × a validator-computed multiplier.** It covers GPU price class, TEE bonus, demand/revenue boost and first-responder bounty, and has no user-visible benchmark to game. Only count instances that live ≥1 h; pay startup at a reduced rate (0.3×); use a short rolling window (1 day); set weights on clock-aligned hours.
- **Validator-owned autoscaler plus bounties** to solve cold start. A bounty's boost grows with age (1.1→1.5 over 3 h), then decays into the steady-state multiplier. Tie the boost to *paid revenue per instance* (clamp 0.1–3× median), not raw request counts, and never boost free or sponsored endpoints.
- **The TEE stack pattern**:
  - TDX CVM plus NVIDIA CC (PPCIe), with a LUKS root unlocked only after quote verification.
  - A cosign admission controller in k3s.
  - Per-instance quote with `report_data = H(nonce || e2e_pubkey)`, plus GPU evidence and TLS-cert binding.
  - Public evidence endpoints for third-party verification.
  - ML-KEM-768 + HKDF + ChaCha20-Poly1305 client E2E with single-use nonces and streaming chunk encryption. For video, encrypt the output mp4 too.
- **Auditable weights**: hourly on-chain commitment of audit exports, plus an open auditor that reproduces weights.
- **Least-connection routing with a per-instance disable/backoff ladder** and a cascade-failure guard.

### What to avoid or do better
- **Publish golden measurements and a reproducible guest-image build from day one.** Use a transparency log so clients never have to trust the owner API. Consider threshold or multi-validator key release rather than one owner-run LUKS KMS.
- **Don't rely on closed binaries for anti-cheat.** In a TEE world, measured boot plus signed images should be the root; keep in-container checks for defence in depth, but open-source them.
- **For video, don't reuse the synchronous 30-minute HTTP call.** Use an async job API (submit → job_id → poll or webhook). Add per-step heartbeats and progress so the validator can detect stalls, and write encrypted results to object storage. Price per output second and resolution, or per diffusion step × resolution × frames, like Chutes' `hourly × 0.002 per step`.
- **Budget for TEE cold-start pain.** Video models are 14B+ plus VAE/T5. Pre-stage encrypted model caches, pin HF revisions, and verify weight hashes at random offsets (watchtower-style). Pay bounties large enough to cover multi-minute TDX boots and model loads.
- **Keep the mechanism stable and documented**, and version it. Chutes' repeated overhauls plus stale docs were a recurring source of miner confusion.
- **Watch the revenue-to-emissions ratio and verify revenue on-chain** (e.g. publish buyback transactions). Chutes' buyback claims are widely repeated but hard to verify from primary sources.
- **Hardware reality**: Chutes' live fleet is almost entirely **8× RTX Pro 6000 TDX boxes**, plus a few H200/B200/B300. For video generation, 1× Pro 6000 (96 GB) runs Wan2.2 I2V A14B and LTX; that is a cheap, CC-capable SKU worth targeting.

---

## Source index
- Code: https://github.com/chutesai/chutes-api (metasync/constants.py, metasync/shared.py, metasync/set_weights_on_metagraph.py, api/constants.py, api/gpu.py, api/chute/util.py, api/bounty/util.py, api/instance/util.py, api/instance/router.py, api/server/router.py, api/e2e/router.py, api/job/router.py, chute_autoscaler.py, watchtower.py, docs/tee-verification.md, docs/specs/scoring-window.md)
- https://github.com/chutesai/chutes-miner (README, gepetto.py)
- https://github.com/chutesai/sek8s (README, host-tools/README.md, docs/end-to-end-miner.md, docs/specs/b200-support.md, docs/debug-mode.md)
- https://github.com/chutesai/chutes (examples/wan21.py, chutes/chute/*.py, entrypoint/run.py)
- https://github.com/chutesai/graval, https://github.com/chutesai/chutes-audit, https://github.com/chutesai/chutes-e2ee-transport, https://github.com/chutesai/e2ee-proxy
- Issues/PRs: chutes#36, chutes#37, chutes-api#61, chutes-miner#126, chutes-e2ee-transport#6
- Docs: https://chutes.ai/docs/core-concepts/security-architecture, https://chutes.ai/docs/miner-resources/scoring, https://chutes.ai/docs/miner-resources/overview, https://chutes.ai/llms.txt
- Live API: https://api.chutes.ai/chutes/?include_public=true&limit=1000, https://api.chutes.ai/chutes/turbowani2v, https://api.chutes.ai/chutes/LTX-25-Video
- Secondary: ownyourmind.ai (two pages), simplytao.ai, unsupervised.capital, oakresearch.io, coingecko.com/learn, rpwithai.com, 0xsammy.com, tao.media, openrouter.ai/provider/chutes, x.com posts cited inline
