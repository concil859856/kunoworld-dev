# Where miners (and we) can get confidential GPUs — rental landscape, 2026-09-15

Research date: 2026-09-15. Three parallel web research passes (hyperscalers, GPU clouds and TEE specialists, bare
metal), plus live API reads of Shadeform, Verda, Targon and Lium. Every claim below carries a source; **UNVERIFIED**
marks what could not be checked. It supersedes the capacity table in [research_tee.md §6.1](research_tee.md) (2026-09-11).

## What we need (from our design)

- **CPU TEE:** Intel TDX. Our golden manifest pins MRTD and RTMR0–3 for a CVM booted directly under QEMU with dstack's
  OVMF, with the worker image on a dm-verity disk measured into RTMR3 ([subnet/image/CVM.md](../subnet/image/CVM.md)).
  AMD SEV-SNP or a provider paravisor measures differently and would need its own verifier path and golden values.
- **GPU:** NVIDIA confidential computing (CC) on H100/H200/B200 (or RTX PRO 6000 Server Edition for single-GPU LTX),
  with NVIDIA evidence verifiable through NRAS or the local verifier.
- **Attestation anyone can verify:** a raw TDX quote (DCAP / dcap-qvl) plus NVIDIA evidence, not a provider dashboard.
- **Shapes:** LTX-2.5 = 1 GPU ≥ 80 GB. MiniMax H3 = 4 GPUs in one worker.
- **Where:** H3 cannot run in the US, EU, UK or South Korea (licence, no testing exception). LTX-2.5 has no territory rule.

## Bottom line

1. **Nothing rentable today runs our exact design self-serve.** The closest are GCP `a3-highgpu-1g` (our own TDX
   image, but Google firmware, spot or flex-start only, US/EU zones) and Hydra Host "Confidential Metal" (bare-metal
   TDX + GPU CC, advertised; details UNVERIFIED).
2. **Two managed platforms are self-serve but differ from our design:** Phala Cloud (TDX + dstack; containers only on
   Phala's OS) and Verda (SEV-SNP with our own measured OS). Supporting either means a second attestation profile.
3. **H3 has no verified self-serve confidential option outside US/EU/UK/KR.** Every rentable 8×H200/B200 bare-metal
   server found is in the US or EU; Phala lists India for H200 but its price table says US only (UNVERIFIED).
4. **Shadeform exposes no confidential computing.** Its API (298 offers) has no CC, TDX or SEV field.
5. **Confidential miners on Bittensor own or colocate their hardware.** Targon (SN4) showed about 224 GPUs across 5
   UIDs on 2026-09-15, run on miners' own servers with TargonOS; Chutes (SN64) is TEE-only on bare-metal TDX hosts.

## Hardware facts that shape the design

| Fact | Consequence for us | Source |
|---|---|---|
| **Hopper (H100/H200): a CVM gets 1 GPU, or all 8 GPUs plus the 4 NVSwitches under Protected PCIe (PPCIe).** A 4-GPU H200 CVM is impossible. | H3 on H200 = one 8-GPU TD hosting two 4-GPU workers, as `CVM.md` "Whole-server TDs for MiniMax H3" already plans. | [Lium CVM guide](https://docs.lium.io/providers/nodes/cvm); [NVIDIA R595 TCS release notes](https://docs.nvidia.com/595trd1-trusted-computing-solutions-release-notes.pdf) |
| **Blackwell (B200/B300): 1, 2, 4 or 8 GPUs per CVM**, NVLink encrypted, Fabric Manager on the host. | A 4×B200 CVM is a valid single H3 worker. | R595 notes; [Verda CC docs](https://docs.verda.com/cpu-and-gpu-instances/confidential-computing/) |
| **RTX PRO 6000 Server Edition: single-GPU CC only.** | Fine for LTX-2.5; no multi-GPU confidential workers on it. | Verda CC docs |
| **CPU:** NVIDIA supports Emerald Rapids / Granite Rapids for TDX (Sapphire Rapids not on its CC list); Milan/Genoa/Turin for SNP. | Many rented HGX boxes (Sapphire Rapids, AMD) can't host our TDX CVM. | [NVIDIA CC deployment guide v7.1, 2026-04-06](https://docs.nvidia.com/cc-deployment-guide-tdx.pdf) |
| **Host:** Ubuntu 25.10, kernel 6.17+ (Intel); TDX module 1.5.x (EMR) / 2.0.x (GNR); BIOS TDX/TME/SEAM settings; Secure Boot off to set GPU CC mode. | Miners need BIOS control; most GPU rentals don't give it. | Guide p.7–17; [Canonical TDX](https://github.com/canonical/tdx) |
| **Driver/firmware pin:** R595 TRD 595.58.03 (CUDA 13.2) with HGX Hopper firmware 1.9.0 (B200/B300 1.4.x). A driver-610 H200 fails attestation with "RIM Not Found" (2026-09-08). | Pin R595 in the image until a newer trusted-computing release lists RIMs. | R595 notes; [NVIDIA forum 2026-09-08](https://forums.developer.nvidia.com/t/rim-bundle-not-found-on-h200-attestation/382686) |
| **CC-mode limits relevant to video:** `cudaHostRegister` unsupported (vLLM crash loop on 8×H200 TDX); Blackwell NVDEC session caps; NPP may not work; an NVENC out-of-memory issue on RTX PRO 6000 SE (title only, UNVERIFIED). | Must test inside CC mode: pinned-memory offload paths, ffmpeg/NVENC, SGLang kernels. | [vLLM #55428](https://github.com/vllm-project/vllm/issues/55428); R595 notes; [open-gpu-kernel-modules #1326](https://github.com/NVIDIA/open-gpu-kernel-modules/issues/1326) |
| PPCIe keys never rotate, so CVMs must be restarted periodically; NVLink traffic is not encrypted on Hopper PPCIe; NCCL ≥ 2.26.3. | Plan scheduled CVM restarts for H3 workers. | R595 notes |

## Options by provider

### Hyperscalers

| Provider | Offer | TEE | Self-serve | Price | Regions | Our own image | Attestation anyone can verify | Verdict |
|---|---|---|---|---|---|---|---|---|
| **GCP A3 High** `a3-highgpu-1g` | 1× H100 80 GB | TDX + CC | **Spot or Flex-start only** (Flex-start ≤ 7 days) | CC surcharge Spot $0.439/h; base VM in CC zones UNVERIFIED | europe-west4-c, us-central1-a, us-east5-a | **Yes** (TDX-capable custom image; Google firmware, endorsements in `gs://gce_tcb_integrity`) | Raw TDX quote via `tdx_guest` (on A3 specifically UNVERIFIED); NVIDIA evidence via go-nvattest-tools | Best hyperscaler fit for a 1-GPU TDX test; MRTD/RTMR0 differ from our dstack-OVMF values |
| **GCP G4** | 1× RTX PRO 6000 | AMD SEV (not SNP, "software attested") | Yes | +$0.45/h CC | 36 zones incl. Asia | Yes | No hardware-signed report | Fails the attestation requirement |
| **Azure** `Standard_NCC40ads_H100_v5` | 1× H100 NVL 94 GB (only CC size) | SEV-SNP behind Microsoft's paravisor | PAYG, quota ticket needed | $6.98/h (eastus2) – $8.90/h (westeurope); spot $1.29–1.64 | centralus, eastus2, southcentralus, westeurope | Yes (Compute Gallery CVM image) | SNP report certifies Microsoft firmware; our OS only via vTPM quote | Works for 1 GPU only with a different attestation path |
| **Alibaba** `gn8v-tee` | 1× or 8× 96 GB HBM3 (likely H20, UNVERIFIED), PPCIe on 8 | TDX + CC | **Sales only** | UNVERIFIED | Beijing; overseas via sales | **No** (Alibaba Cloud Linux 3 only) | Raw TDX quote; GPU via NVIDIA local verifier | Only hyperscaler multi-GPU CC; unusable for our image |
| AWS, Oracle, Tencent | — | No NVIDIA CC GPU instance | — | — | — | — | — | No |

Sources: [Azure GPU options](https://learn.microsoft.com/en-us/azure/confidential-computing/gpu-options),
[Azure guest attestation](https://learn.microsoft.com/en-us/azure/confidential-computing/guest-attestation-confidential-virtual-machines-design),
Azure Retail Prices API (2026-09-15),
[GCP supported configurations](https://docs.cloud.google.com/confidential-computing/confidential-vm/docs/supported-configurations),
[GCP GPU CVM](https://docs.cloud.google.com/confidential-computing/confidential-vm/docs/create-a-confidential-vm-instance-with-gpu),
[GCP CVM pricing](https://cloud.google.com/confidential-computing/confidential-vm/pricing),
[GCP custom CVM images](https://docs.cloud.google.com/confidential-computing/confidential-vm/docs/create-custom-confidential-vm-images),
[AWS EC2 attestation](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/nitrotpm-attestation.html),
[OCI confidential computing](https://docs.oracle.com/en-us/iaas/Content/Compute/References/confidential_compute.htm),
[Alibaba GPU families](https://www.alibabacloud.com/help/en/ecs/user-guide/gpu-accelerated-compute-optimized-and-vgpu-accelerated-instance-families-1).

### GPU clouds and TEE specialists

| Provider | GPUs per CVM | TEE | Self-serve | $/GPU-h | Regions | Our own image | Verifiable attestation | Notes |
|---|---|---|---|---|---|---|---|---|
| **Phala Cloud** | H200 1× or 8×; B300 1×/8× | TDX + CC | Yes, ~1 day provisioning; card, crypto, wire | H200 $4.80 on-demand (24 h min), $4.30 (30 d), $3.80 (180 d); 8×H200 $38.40/h ($28 on 180 d); B300 1× $9.00 (720 h min) | US; H200 page lists **India** (UNVERIFIED) | **Containers only** on Phala's dstack OS (reproducible from meta-dstack); compose hash in RTMR3 | Yes: raw quote + event log; dstack-verifier / dcap-qvl; NVIDIA evidence in-VM | Closest managed fit to TDX; needs a "Phala dstack OS + our compose hash" profile |
| **Verda** (ex-DataCrunch) | 1× RTX PRO 6000; **4× or 8× B200**; 4×/8× B300 | **SEV-SNP** + CC | **Yes** (console/API) | RTX PRO 6000 CC $1.879; B200 CC $6.23 (4× = $24.93/h); B300 CC $7.65 | Finland (EU) | **Yes**, own OS via direct kernel boot (launch digest covers OVMF, kernel, initrd, cmdline) | Yes: SNP report (AMD chain) + `nvattest` | Only self-serve 4-GPU CC VM found, but EU (no H3) and SNP; stock UNVERIFIED |
| VoltageGPU | 1× H200 VM (CC status conflicting) | TDX | Conflicting (email vs self-serve) | H200 $6.58–8.08 | France | No | Raw TDX quote; NRAS only on 1×H200 | Practice raw-quote collection only |
| Targon rentals (SN4) | H100–B300 | TDX + CC | Beta, stock-limited | UNVERIFIED | UNVERIFIED | No ("custom OS images not supported") | UNVERIFIED | Not usable for our image |
| Tinfoil Containers | 1 or 8 (H200/B200) | TDX/SNP + CC | GPUs by sales | Quote | Not disclosed | Containers on Tinfoil's CVM | Via Sigstore log; no raw NVIDIA evidence to clients | Not usable |
| Lium (SN51) | 1 GPU or 8× Hopper PPCIe, optional dstack TDX | TDX | Pods only | TDX-capable H100 $1.30–1.41 | US, CA, RU, JP | No | Validators only; 14 hosts claim TDX, **0 passed attestation** (2026-09-15) | Not usable today |
| SecretVM | H100/H200/GH200 | TDX | UNVERIFIED | Unpublished | Undisclosed | Compose on their image | Yes (CPU + GPU quote, nonce-bound) | Unclear GPU availability |
| io.net, Spheron, Corvex, Super Protocol | H100–B300 | TDX | Sales / reserved | Quote | Undisclosed | UNVERIFIED | UNVERIFIED | Ask for Asia/Middle East/LatAm capacity |

No public confidential-GPU offer: Crusoe, CoreWeave, Lambda, Nebius, Together, Hyperbolic, RunPod, TensorDock,
Voltage Park, Hyperstack (vague "confidential" private cloud), Genesis Cloud, Scaleway, OVHcloud (TDX on CPU-only
bare metal), Fluence, Vast.ai (2024 "experimenting" page only). API-only: NEAR AI, Privatemode. Software-only:
Fortanix, Anjuna, Opaque.

Sources: [Phala pricing](https://cloud.phala.com/about/pricing), [Phala GPU TEE](https://phala.com/gpu-tee),
[Phala deploy guide](https://docs.phala.com/phala-cloud/confidential-ai/gpu-tee-deployment-guide.md),
[Phala verify platform](https://docs.phala.com/phala-cloud/attestation/verify-the-platform.md),
[Verda instance types API](https://api.verda.com/v1/instance-types),
[VoltageGPU walkthrough 2026-09-02](https://dev.to/voltagegpu/i-let-my-tenants-generate-their-own-intel-tdx-quotes-here-is-the-exact-walkthrough-19ph),
[Targon VM guide](https://docs.targon.com/guides/virtual-machines),
[Tinfoil limits](https://docs.tinfoil.sh/containers/limits.md),
[Lium executors API](https://lium.io/api/executors),
[SecretVM docs](https://docs.scrt.network/secret-network-documentation/secretvm-confidential-virtual-machines/introduction),
[io.net CC](https://io.net/docs/guides/clouds/confidential-compute-overview).

### Bare metal (the miner runs our CVM on its own host)

| Provider | GPU | TDX usable? | GPU CC supported? | Price | Regions | Source |
|---|---|---|---|---|---|---|
| **Hydra Host "Confidential Metal"** | B200, H200, GH200 | TDX preconfigured on Dell/Lenovo/HPE/Supermicro/Aivres | **Advertised** (TDX + GPU CC + attestation); SKUs, firmware, BIOS access UNVERIFIED | H200 $2.50–3.20/GPU-h; B200 $3.50–5.00/GPU-h | 40+ DCs (Americas, APAC, Middle East, EU); which have TDX UNVERIFIED | [TDX post 2025-12-16](https://hydrahost.com/blog/news/confidential-ai-bare-metal-intel-tdx/), [Confidential Metal 2026-04-15](https://hydrahost.com/blog/blog/confidential-metal-zero-trust-gpu-infrastructure/) |
| **OpenMetal** | H200 NVL (PCIe, no NVSwitch) | Yes (Xeon 6530P, IPMI/BIOS) | **1 GPU per CVM**; attestation "in progress" | Quote, monthly | Ashburn; Singapore, Amsterdam, LA by booking | [H200 page, 2026-09-03](https://openmetal.io/resources/hardware-details/gpu-server-h200/) |
| **Corvex** | HGX B200, H200 | Yes (stated) | Yes (B200 TDX + CC deployment) | Sales | US | [PR 2026-03-03](https://www.prnewswire.com/news-releases/corvex-among-the-first-companies-to-achieve-verified-production-deployment-of-confidential-computing-for-ai-on-nvidia-hgx-b200-systems-302702992.html) |
| Latitude.sh, Vultr | H100, B200, B300, RTX PRO 6000 | No (AMD EPYC, or Sapphire Rapids) | Not advertised | $1.68–3.50/GPU-h | US, 33 Vultr sites | [Latitude](https://www.latitude.sh/pricing) |
| Excess Supply, Boost Run, Amaya, Massed Compute (Shadeform bare metal) | 8×H200 / 8×B200 | CPU model and TDX not exposed | Not mentioned | $18–36.80/h per server | US only for bare metal | Shadeform API |
| Leaseweb, Sesterce, Hostrunway, DigitalOcean, OVHcloud, Hetzner, Cherry, phoenixNAP | various | UNVERIFIED or no | Not mentioned | — | Hostrunway lists Dubai (UNVERIFIED) | see agent notes |
| Equinix Metal | — | — | — | end of life 2026-06-30 | — | [DCD](https://www.datacenterdynamics.com/en/news/equinix-to-kill-off-metal-by-june-2026/) |

**Own or colocate (8×H200):** about $370k to buy (8×B200 about $450k); colocation $2.5–5k/month (about 10.2 kW).
Over 36 months that is about $19.60/h at 24/7 use, close to renting ($18–25.60/h), so owning mostly buys BIOS and
firmware control and a free choice of jurisdiction.
[Mercatus H200](https://www.mercatus-ai.com/blog/h200-server-price), [Mercatus B200](https://www.mercatus-ai.com/blog/b200-server-price),
[QuoteColo](https://www.quotecolo.com/nvidia-dgx-ready-data-centers/).

## Bittensor miners on confidential subnets

- **SN4 Targon** (live 2026-09-15): TDX-VM-H200 13 nodes / 104 GPUs (one UID), TDX-HOPPER-H200 2 / 16,
  TDX-VM-B300 8 / 64, TDX-VM-H100 3 / 24, RTX6000B 2 / 16 — about 224 GPUs across 5 UIDs, on miners' own hardware
  with TargonOS. Targon sells an 8-GPU TDX workstation ("Tower Pro").
  [stats.targon.com/api/miners](https://stats.targon.com/api/miners), [Targon miner docs](https://docs.targon.com/providers/miner/)
- **SN64 Chutes:** "now TEE-exclusive", bare-metal TDX hosts via sek8s; sek8s validated on 8×H200, 8×B200 and
  8×RTX PRO 6000. [chutes-miner README](https://github.com/chutesai/chutes-miner/blob/main/README.md),
  [sek8s host tools](https://github.com/chutesai/sek8s/blob/main/host-tools/README.md)
- **SN90 KubeTEE:** TDX, Hopper or Blackwell, 8-GPU workers. [repo](https://github.com/KubeTEE-AI/kubetee-subnet)
- No public report of a Bittensor miner running TDX + H200 CC on *rented* bare metal with the provider named.

## Recommendations

1. **End-to-end test of our real TDX design (LTX-2.5 only, US is fine):**
   - **Hydra Host** 1× H200 (then 8× for PPCIe) — ask for Emerald/Granite Rapids, root and BIOS access, Secure Boot
     control, HGX firmware 1.9.0, Ubuntu 25.10 or reinstall rights, and whether any non-US site has TDX hardware.
   - **In parallel, GCP `a3-highgpu-1g` on Spot** — our own TDX image on Google firmware: proves RTMR1–3, the raw
     quote path and NVIDIA evidence, with Google's MRTD/RTMR0 as a separate golden entry.
2. **Lower-friction miner paths (each needs a second attestation profile):** Phala Cloud (TDX, dstack OS + our
   compose hash) first; Verda (SEV-SNP, own measured OS) later if SNP support is worth adding.
3. **H3 on the confidential tier depends on miners' own or colocated HGX servers in allowed jurisdictions**
   (e.g. UAE, Japan, Singapore, Brazil), or Phala 8×H200 in India via sales. Consider launching the confidential
   tier with LTX-2.5 and adding H3 when a compliant miner exists.
4. **Ship what professional miners need:** a host installer (sek8s host tools are a reference), a preflight that
   checks BIOS flags, TDX module, firmware, driver pin and CC mode, and a hardware compatibility list.
5. **Test inside CC mode before promising anything:** pinned-memory and offload paths, ffmpeg/NVENC, SGLang JIT
   kernels, PPCIe restarts, R595 driver pin.
