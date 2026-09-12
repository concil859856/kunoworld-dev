# TEE Stack Research for a Confidential Video-Generation Bittensor Subnet

Research date: 2026-09-11. Every claim has a source URL inline.

**Evidence labels**
- **[C] Confirmed**: read directly in a primary source (vendor docs, release notes, paper text, or project README) during this research.
- **[R] Reported**: from secondary sources (news, blogs, provider marketing) or paper abstracts only. Likely correct, but not checked against primary text.
- **[U] Unverified or inference**: my own analysis, estimates, or items I could not verify. Treat these as hypotheses to test.

---

## 0. Executive summary

1. **What is feasible today.** The subnet can run "this exact image, and prove it" with keys bound to the enclave on an **Intel TDX CPU (Emerald Rapids or Granite Rapids) + NVIDIA H100/H200/B200/B300/RTX PRO 6000 Blackwell Server Edition in CC mode**. Three stacks already do this in production, two of them on Bittensor:
   - Chutes (SN64) with sek8s.
   - Targon (SN4), with an Intel co-authored paper.
   - Phala dstack, which serves OpenRouter and NEAR AI.

   Consumer RTX GPUs (4090/5090) have no CC mode. They cannot give confidentiality for GPU memory or PCIe traffic.
2. **Multi-GPU status.**
   - Hopper supports up to 8 GPUs only in **Protected PCIe (PPCIe)** mode on HGX 8-GPU boards. NVLink traffic is **not encrypted** in that mode, and there is no key rotation.
   - Blackwell (HGX B200/B300) supports **Multi-GPU Passthrough CC (MPT CC)** for up to 8 GPUs with **encrypted NVLink**. This went GA in the R595 release (March 2026).
   - All modes still use CPU-side encrypted **bounce buffers**. TDISP/TEE-IO inline encryption is described as a future option for Blackwell plus compatible CPUs.
3. **Performance.**
   - Encrypted host-to-device bandwidth drops from ~51.6 GB/s to ~3.5–9.6 GB/s on B200.
   - Each kernel launch costs ~12 µs extra.
   - Model loading can be ~34× slower.
   - Steady-state throughput overhead ranges from ~1–3% (well-tuned, CUDA graphs) to 13–27% (typical LLM serving on H100+TDX).
   - Video diffusion is compute-heavy with tiny inputs and outputs of tens of MB. It should sit at the favourable end **if models stay resident in VRAM and CPU offload is avoided [U]**.
   - NVIDIA's own known issues matter for video pipelines: the Blackwell CC decoder session limit, and NPP not working because pinned host memory is unsupported.
4. **Security reality in 2025–26.**
   - Physical DDR5 bus interposers (TEE.fail, under $1k) break TDX and SEV-SNP confidentiality **and attestation**. Researchers extracted Intel PCE keys and forged "UpToDate" quotes. NVIDIA GPU attestation can be "borrowed" because GPU reports are not bound to the CVM.
   - Intel, AMD and NVIDIA all consider physical attacks out of scope and ship no fix.
   - SEV-SNP also had several **software-only** breaks: RMPocalypse, Heracles, STALEUS (USENIX Security '26), and Milan VCEK-seed extraction.
   - **In a network of untrusted miners who physically own the servers, TEEs raise the cost of cheating a lot, but they cannot guarantee confidentiality against a determined, equipped miner.** Design for that: hardware-ID registries and Proof-of-Cloud tiers, economic deterrence, short-lived per-job keys, and no long-lived global secrets on miner hardware.
5. **Recommendation.**
   - Use TDX-first (Xeon 5th/6th gen) with a dstack-style or sek8s-style measured CVM.
   - Pin the container by digest and pin the weights with a dm-verity root hash.
   - Generate the enclave key inside the CVM and bind it (plus the validator nonce) into REPORTDATA.
   - Collect GPU evidence inside the CVM with a derived nonce.
   - Clients encrypt with HPKE directly to the attested key. Outputs are encrypted per job to object storage.
   - Validators run a strict policy: TCB minimums, hardware-ID dedupe, randomized re-attestation, per-response signatures, and performance challenges.
   - Offer an optional "verified data-center" tier using Proof-of-Cloud-style registries.

---

## 1. CPU TEEs: Intel TDX vs AMD SEV-SNP

### 1.1 Intel TDX

**How it works [C].**
- A TDX Trust Domain (TD) is a hardware-isolated VM. It is managed by the Intel-signed **TDX module**, which runs in SEAM (Secure Arbitration Mode). The hypervisor is outside the TCB.
- Memory is encrypted with per-TD keys through TME-MK.
- Sources: [Linux kernel TDX docs](https://docs.kernel.org/arch/x86/tdx.html), [Chutes security architecture](https://chutes.ai/docs/core-concepts/security-architecture), [Intel TDX Demystified](https://arxiv.org/pdf/2303.15540).

**Measurement registers [C].**

| Register | Contents | Notes |
|---|---|---|
| **MRTD** | 48-byte SHA-384 of the initial TD memory, i.e. the TDVF/OVMF firmware image. Computed by the TDX module at build time. | Immutable for the TD's lifetime. Comparable to PCR0. |
| **RTMR0** | TDVF configuration: CFV, TD HOB, ACPI tables, Secure Boot variables. | Comparable to PCR1/7. **Depends on VM shape (vCPUs, memory, devices), so golden values are per configuration.** |
| **RTMR1** | OS loader, kernel, boot params. In TDVF's mapping, also the initrd. | Comparable to PCR2–5. |
| **RTMR2** | OS or application measurements. | dstack puts the initrd/cmdline here. |
| **RTMR3** | "Reserved for special usage". | dstack puts app identity here: app-id, compose-hash, instance-id, key-provider. |
| **MRCONFIGID / MROWNER / MROWNERCONFIG** | 48-byte host-provided values fixed at TD creation and included in the quote. | dstack can use MRCONFIGID to carry the compose hash ([tutorial](https://phala.com/posts/mr-config-id-tutorial)). |
| **REPORTDATA** | 64 bytes chosen by the guest. | Use it to bind a nonce plus a public key. |

- Extend semantics: `RTMR[i] = SHA384(RTMR[i] || digest)`. Verifiers replay the event log (CCEL) and compare the result to the quoted RTMR.
- Sources: [kernel docs](https://docs.kernel.org/arch/x86/tdx.html), [TDVF design guide](https://cdrdv2-public.intel.com/733585/tdx-virtual-firmware-design-guide-rev-004-20231206.pdf), [dstack paper](https://arxiv.org/html/2509.11555), [iExec on dstack RTMR3](https://x.com/iEx_ec/status/2082805940198502628).

**Quote generation [C].**
1. The guest calls `TDG.MR.REPORT` and gets a TDREPORT, which is MAC'd and verifiable only on the same platform.
2. The SGX-based **Quoting Enclave** (DCAP) on the host converts it into an ECDSA-signed **TD Quote**.
3. The certification chain is PCK certificate (per platform, issued via the PCE) → Intel CA.
4. Sources: [kernel docs](https://docs.kernel.org/arch/x86/tdx.html), [enclaive DCAP explainer](https://docs.enclaive.cloud/confidential-cloud/technology-in-depth/intel-tdx/technology/fundamentals/dcap-attestation/attestation-report).
5. **Implication [U]:** the untrusted host runs the QE. That is fine, because the signature chains to Intel. The trade-off is that the platform's PCE/PCK keys are exactly what TEE.fail extracted (see §5).

**Verification infrastructure [C].**
- **Intel PCS** (Provisioning Certification Service) serves PCK certs, TCB Info, QE Identity and CRLs. **PCCS** is a local caching proxy for it.
- Verifiers: Intel's **QVL/QVS** ([QVS repo](https://github.com/intel/SGX-TDX-DCAP-QuoteVerificationService)), Phala's Rust **dcap-qvl** ([npm](https://www.npmjs.com/package/@phala/dcap-qvl)), or ZK verifiers ([zkdcap](https://github.com/datachainlab/zkdcap)).
- TCB status values: `UpToDate`, `SWHardeningNeeded`, `ConfigurationNeeded`, `ConfigurationAndSWHardeningNeeded`, `OutOfDate`, `OutOfDateConfigurationNeeded`, `Revoked`.
- DCAP v1.24 (late Q4 2025) fixed QVL omitting advisory IDs from `tdxModuleIdentities` ([Intel QVL errata](https://community.intel.com/t5/Intel-Software-Guard-Extensions/Intel-DCAP-Quote-Verification-Library-QVL-Errata/m-p/1640457), [TCB recovery](https://www.intel.com/content/www/us/en/developer/articles/technical/software-security-guidance/best-practices/trusted-computing-base-recovery.html)).
- **Intel Trust Authority (ITA)** is Intel's SaaS verifier. It can do **composite TDX + NVIDIA GPU attestation** in a single JWT (`tdx` section plus `nvgpu` section in NRAS v3 format). The nonce is shared between CPU and GPU evidence, and ITA can use NRAS or a local GPU verifier ([ITA GPU attestation](https://docs.trustauthority.intel.com/main/articles/articles/ita/concept-gpu-attestation.html)).
- Targon uses ITA plus Intel's **Key Broker Service (KBS)**. Its validators forward evidence to KBS because they hold no ITA API keys ([Manifold/Intel paper](https://arxiv.org/html/2607.21865)).
- **Platform identity [C/R]:** Intel quotes carry a **PPID** (via the PCK cert), a stable per-CPU identifier usable for hardware allowlists ([Proof of Cloud](https://proofofcloud.org/) via search summary; [Flashbots](https://writings.flashbots.net/mind-the-gap-tee-poc)).

**CPU support [C/R].**
- 4th Gen Xeon Scalable (Sapphire Rapids) introduced TDX. It was reportedly available "only to select CSPs" at first [R].
- 5th Gen (Emerald Rapids) brought broad availability.
- Xeon 6: Granite Rapids (P-cores) and Sierra Forest (E-cores).
- 3rd Gen (Ice Lake) and older cannot gain TDX ([Intel support article](https://www.intel.com/content/www/us/en/support/articles/000091103/processors/intel-xeon-processors.html)).
- NVIDIA's CC deployment guide lists **Emerald Rapids and Granite Rapids** as the Intel CPUs for GPU CC. It says to use **TDX module 1.x for Emerald Rapids (e.g. TDX_1.5.16) and 2.x for Granite Rapids (e.g. TDX_2.0.08)**. You install it by copying `TDX-SEAM.so` and its sigstruct to `/boot/efi/EFI/TDX/` ([NVIDIA CC Deployment Guide v7.1, Apr 2026](https://docs.nvidia.com/cc-deployment-guide-tdx.pdf)).
- **TDX Connect** (TEE-IO/TDISP) is supported on Xeon 6 P-core ([Intel blog](https://community.intel.com/t5/Blogs/Tech-Innovation/Data-Center/Announcing-Intel-TDX-Connect-Support-on-Intel-Xeon-6/post/1668423)). Its ecosystem readiness for GPUs is **not confirmed** [U].

**Required BIOS settings, Intel [C]** ([NVIDIA guide p.7–8](https://docs.nvidia.com/cc-deployment-guide-tdx.pdf)):
```
Processor Configuration -> Limit CPU PA to 46 Bits -> Disable
Intel TME/TME-MT/TDX:
  Total Memory Encryption (TME) -> Enable
  TME Bypass -> Auto
  TME Multi-Tenant (TME-MT) -> Enable
  Memory Integrity -> Disable
  Intel TDX -> Enable
  TDX Secure Arbitration Mode Loader (SEAM) -> Enabled
  Disable excluding Mem below 1MB in CMR -> Auto
  Intel TDX Key Split -> <non-zero>
Software Guard Extension (SGX) -> Enable   (needed for the DCAP Quoting Enclave)
```

**Host kernel and OS [C].**
- Host: Ubuntu 25.10 with kernel 6.17+ for Intel. Guest: Ubuntu 24.04 ([NVIDIA R595 release notes](https://docs.nvidia.com/595trd1-trusted-computing-solutions-release-notes.pdf)).
- Set `kvm_intel.tdx=1 nohibernate` on the kernel command line.
- Canonical's [tdx repo](https://github.com/canonical/tdx) (tag 3.3) supplies the setup scripts.
- `dmesg` should show `virt/tdx: module initialized`. A `SEAMCALL ... failed` error means the TDX module is outdated.

### 1.2 AMD SEV-SNP

**How it works [C].**
- Guest memory is encrypted by the memory controller with per-VM keys (AES-128-XEX on Milan, AES-256-XTS on Genoa and later).
- The **RMP (Reverse Map Table)** gives integrity against remapping and replay by the hypervisor.
- The **ASP/PSP** firmware manages guests and signs attestation reports.
- Source: [SEV-SNP primer, arXiv 2608.04039](https://arxiv.org/html/2608.04039v1).

**Attestation report fields [C]** ([primer](https://arxiv.org/html/2608.04039v1)):
- **MEASUREMENT**: launch digest of initial guest memory and VMSA (vCPU state). It depends on vCPU count and type, and on the OVMF/kernel/initrd/cmdline when using measured direct boot.
- **REPORT_DATA** (64 bytes, set by the guest) and **HOST_DATA** (32 bytes, set by the host at launch; CoCo uses it for the init-data hash [U, background]).
- **POLICY**: DEBUG, SMT, ciphertext-hiding requirement, PAGE_SWAP_DISABLE, and so on.
- **CHIP_ID** is present only with VCEK signing.
- **REPORTED_TCB / CURRENT_TCB / LAUNCH_TCB / COMMITTED_TCB**.
- **PLATFORM_INFO**: SMT enabled, ciphertext hiding active, **DRAM alias check completed** (a BadRAM mitigation), Trusted I/O enabled.
- ID block / ID key digest, and VMPL.

**Keys [C].**
- **VCEK**: per chip and per TCB, derived from fused secrets plus the TCB.
- **VLEK**: per cloud provider, and omits CHIP_ID.
- Certificates come from **AMD KDS** (`kdsintf.amd.com`), with the chain ARK → ASK → VCEK/VLEK and a CRL.
- **Pin the ARK locally.** Enforce a minimum REPORTED_TCB.
- TCB components on Milan/Genoa: bootloader, TEE, SNP firmware, microcode. **Turin adds FMC**, so TCB parsing is per CPU family.
- Sources: [primer](https://arxiv.org/html/2608.04039v1), [Contrast SNP docs](https://docs.edgeless.systems/contrast/1.9/architecture/snp), [AWS SNP attestation](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/snp-attestation.html).

**CPU support [C]:** Milan 7xx3, Genoa 9xx4, Turin 9xx5 ([NVIDIA guide](https://docs.nvidia.com/cc-deployment-guide-tdx.pdf)). **Ciphertext hiding** and Secure AVIC come with Genoa and later. **SEV-TIO** (TDISP) is on Turin, and Linux 6.19 has initial support ([Phoronix](https://www.phoronix.com/news/Linux-6.19-PCIe-Link-Encrypt), [LWN](https://lwn.net/Articles/1046061/)).

**BIOS, AMD [C]** ([NVIDIA guide p.7](https://docs.nvidia.com/cc-deployment-guide-tdx.pdf)):
```
CPU Configuration: SMEE -> Enabled; SEV ASID Count -> 509; SEV-ES ASID Space Limit Control -> Manual;
                   SEV-ES ASID Space Limit -> 100; SNP Memory Coverage -> Enabled
NB Configuration:  IOMMU -> Enabled; SEV-SNP support -> Enabled
```
- SEV firmware must be ≥ 1.51 (the guide's example shows 1.55).
- Host: Ubuntu 25.04 with kernel 6.14+.

### 1.3 TDX vs SNP for this subnet [U, with supporting facts]

| Criterion | TDX | SEV-SNP |
|---|---|---|
| GPU CC ecosystem (dstack, sek8s, Targon, CoCo) | Primary target everywhere | Supported (Azure, Tinfoil); dstack calls it experimental |
| DDR4 interposer (Battering RAM) | Not vulnerable ([batteringram.eu](https://batteringram.eu/)) | Attestation broken by replay (DDR4 parts) |
| DDR5 interposer (TEE.fail) | Broken, including attestation-key extraction | Broken, even with ciphertext hiding |
| Software-only breaks 2025–26 | TDXdown/TDXploit (side channels, single-stepping) | RMPocalypse (fixed by firmware), Heracles, STALEUS (Zen 4/5, CVE-2025-54509, can forge attestation-relevant state), Fabricked (Zen 4/5 Infinity Fabric), Milan VCEK root-seed extraction |
| Per-chip ID for allowlists | PPID | CHIP_ID (VCEK only) |

**Recommendation:** make TDX on Emerald or Granite Rapids the primary platform. Accept SNP only on Genoa or Turin, and only with a strict policy (current firmware, ciphertext hiding, alias check). **Reject Milan entirely**, because its root seed has been extracted.

---

## 2. GPU TEEs: NVIDIA Confidential Computing

### 2.1 Architecture [C]

Source: [NVIDIA Secure AI with Blackwell and Hopper GPUs whitepaper WP-12554 v1.3, Aug 2025](https://docs.nvidia.com/nvidia-secure-ai-with-blackwell-and-hopper-gpus-whitepaper.pdf).

**Boot and setup.**
- The GPU's on-die RoT and secure boot chain run CEC/EROT → FSP → GSP → SEC2 ([arXiv 2507.02770](https://arxiv.org/html/2507.02770v2)).
- The host enables a mode persistently with `nvidia_gpu_tools.py --set-cc-mode=on|off|devtools`, then resets the GPU.
- The GPU firmware scrubs memory and enables its firewall.
- The guest driver sets up an **SPDM** session (Diffie-Hellman) with GPU firmware. Per arXiv 2507.02770, 44+ keys are derived from that master secret.

**Data path.**
- CPU↔GPU transfers are **AES-256-GCM encrypted by the GPU's DMA/copy engines** and staged through **bounce buffers** in shared, unencrypted CVM memory.
- Rolling 96-bit IVs provide replay protection.
- UVM paging is also encrypted.

**Lockdown.**
- Performance counters are **disabled** in CC-on. `devtools` mode keeps encryption but exposes the counters, and attestation identifies devtools mode, so reject it.
- JTAG is disabled. BMC out-of-band access drops to "card health" only.

**Workload gating.** The GPU accepts no work until the CVM sets **ReadyState**, which happens after attestation (`nvidia-smi conf-compute -srs 1`) ([deployment guide p.32–33](https://docs.nvidia.com/cc-deployment-guide-tdx.pdf)).

**Threat model.**

| In scope | Out of scope / not mitigated |
|---|---|
| Software attacks | Sophisticated physical attacks |
| Basic physical attacks (PCIe/NVLink interposers) | DoS by the hypervisor |
| Rollback, crypto, replay attacks | Reading tenant data through **HBM interposers, DPA/EM physical side channels** |
| | Fault injection |
| | Hardware side channels used to extract ephemeral session keys |

**Note [U]:** some third-party blogs claim "every write to HBM is encrypted", for example [Spheron](https://www.spheron.network/blog/confidential-gpu-computing-nvidia-tee-encrypted-vram/). NVIDIA's own threat table lists HBM interposer reads as *not mitigated*. Treat HBM contents as protected by on-package integration, not by encryption.

### 2.2 Modes and supported SKUs (R595 TRD1 GA, March/April 2026) [C]

Source: [NVIDIA Trusted Computing Solutions R595 release notes](https://docs.nvidia.com/595trd1-trusted-computing-solutions-release-notes.pdf).
- Stack: CUDA 13.2 with driver 595.58.03.
- **Single GPU Passthrough (SPT CC)**: one GPU per CVM, several CVMs per node allowed. SKUs:
  - H100 PCIe, H100 NVL, H200 NVL, H800 variants.
  - HGX H100 and H200 8-GPU, HGX H20/H20A.
  - HGX B200 (AC/PC), B200-850, HGX B300.
  - **RTX PRO 6000 Blackwell Server Edition** (including LC).
- **Hopper Multi-GPU (PPCIe)**:
  - HGX H100/H200/H800/H20A 8-GPU air-cooled only, with all 8 GPUs and 4 NVSwitches in one CVM.
  - **GPU-to-GPU NVLink/NVSwitch traffic is not encrypted.**
  - Key rotation is **not** supported, which the notes say invites passive ciphertext capture. The workaround is to restart the CVM.
  - IV exhaustion can crash apps.
- **Blackwell Multi-GPU (MPT CC)**:
  - HGX B200/B200-850/B300, **up to 8 GPUs per CVM, with P2P over encrypted NVLink**.
  - Requires Fabric Manager with `PARTITION_RAIL_POLICY=symmetric` ([guide p.14](https://docs.nvidia.com/cc-deployment-guide-tdx.pdf)).
- **Firmware and software minimums**:
  - Hopper FW 1.9.0 (VBIOS 96.00.DA.00.XX).
  - B200/B300 FW 1.4.X (97.00.E4.00.XX / 97.10.64.00.XX).
  - RTX PRO 6000 FW 1.4 (98.02.AF.00.02).
  - Attestation SDK / Local GPU Verifier ≥ 2.6.0 (≥ 2.6.3 for MPT). PPCIe verifier ≥ 1.6.0.
- **NVIDIA Confidential Containers** (Kata 4.0.0, GPU Operator v26.3.1+, Ubuntu 25.10/26.04 with kernel 6.17+):
  - Same GPU list: H100/H200 single, PPCIe multi, B200/B300 single and multi, RTX PRO 6000 BSE single.
  - Constraint: **"All GPUs on the host must be configured for CC and all GPUs must be assigned to one Confidential Container virtual machine."**
  - Source: [NVIDIA CoCo supported platforms](https://docs.nvidia.com/datacenter/cloud-native/confidential-containers/latest/supported-platforms.html).
- **GB200 NVL72** is named in release-note headers [R], but the R595 SKU lists I read do not include it. **Treat GB200/NVL72 CC as unverified.**

**Known issues relevant to video [C]** ([R595 notes p.9–10](https://docs.nvidia.com/595trd1-trusted-computing-solutions-release-notes.pdf)):
- **Blackwell CC modes limit decoder sessions** (≤190 with a shared CUDA context, ≤28 with one context per session). This is a software bug with a fix "in a future release".
- **NPP (NVIDIA Performance Primitives) might not work**, because pinned host memory is not supported in CC.
- Implication [U]: GPU video pre/post-processing through NPP, and possibly NVENC/NVDEC, needs testing. A safe default is to encode inside the CVM on CPU (ffmpeg/libx264/libsvtav1). The whitepaper shows a "Video" engine inside the protected GPU, but I did not confirm that NVENC works under CC.

### 2.3 TDISP / TEE-IO status [C/U]

- The whitepaper says that as an alternative to bounce buffers, inline encryption via **TDISP/IDE** "can be used with systems that have Blackwell B100/B200 GPUs and TDISP/IDE-compatible CPUs". Diagrams show SPT and MPT "with TDISP/IDE". It is framed as a future option, and any PCIe switch in the path must support IDE flow-through ([whitepaper p.9, 13–14, 21](https://docs.nvidia.com/nvidia-secure-ai-with-blackwell-and-hopper-gpus-whitepaper.pdf)).
- Enablers on the CPU side are Intel TDX Connect (Xeon 6 P-core) and AMD SEV-TIO (Turin, Linux 6.19+).
- **Production B200 benchmarks from Aug 2026 still show bounce-buffer bandwidth**, and GPUDirect RDMA is blocked under CC ([arXiv 2608.26575](https://arxiv.org/html/2608.26575)). **Assume no TDISP in miner fleets during 2026 [U].**

### 2.4 GPU attestation [C]

- **Evidence**: the driver collects an SPDM-signed measurement report from each GPU (and NVSwitch in PPCIe) over NVML/NSCQ. It includes a verifier **nonce**, firmware/VBIOS measurements, the CC mode, and a device identity cert chaining to NVIDIA's CA.
- **Verification options**:
  - **NRAS** (cloud) compares against the **RIM** (Reference Integrity Manifest) service and checks certs through NVIDIA **OCSP**, then returns an EAT/JWT.
  - The **Local verifier** checks locally but still fetches RIMs and OCSP from NVIDIA.
  - Tools: **NVAT** (NVIDIA Attestation SDK) with the `nvattest` CLI and C and Rust bindings, where local verification is the default. Also the older nvtrust `local-gpu-verifier`.
  - Sources: [NVIDIA attestation quick start](https://docs.nvidia.com/attestation/quick-start-guide/latest/install.html), [NVAT overview](https://docs.nvidia.com/attestation/nv-attestation-sdk-cpp/latest/overview.html), [nvattest CLI](https://docs.nvidia.com/attestation/nv-attestation-cli/0.0.0/command-reference.html), [nvtrust](https://github.com/NVIDIA/nvtrust), [ITA GPU doc](https://docs.trustauthority.intel.com/main/articles/articles/ita/concept-gpu-attestation.html).
- **Binding weakness [C]**: TEE.fail notes that **NVIDIA CC attestation reports are not bound to a specific CVM**. An attacker can "borrow" evidence from a genuine GPU they don't own ([tee.fail](https://tee.fail/)).
  - Phala's own audit found "GPU attestation data was displayed without cryptographic verification of NVIDIA device certificate chain; CPU↔GPU binding not enforced". This was fixed in dstack v0.5.6 ([Phala security update](https://phala.com/posts/dstack-security-update-attestation-pipeline-hardening)).
  - **Mitigation pattern [U]**:
    1. Derive the GPU nonce from the validator nonce and the CVM's key, e.g. `gpu_nonce = SHA256("gpu"||validator_nonce||H(pubkey))`.
    2. Have the measured CVM code collect the GPU evidence itself.
    3. Put the hash of the GPU evidence (or the nonce) into TDX REPORTDATA.
    4. Deduplicate GPU device IDs across all miners.

     This binding rests on the integrity of the CVM. It fails if the CPU TEE is broken (TEE.fail).

### 2.5 Performance numbers [C unless noted]

| Source | Platform | Findings |
|---|---|---|
| [arXiv 2608.26575](https://arxiv.org/html/2608.26575) (Aug 2026) | 2× Xeon 6767P + 8× B200, driver 595.71.05 | **H2D ~3.5 GB/s under CC vs 51.6 GB/s** non-CC (15–19× slower). Bulk ≥1 MB ≈ **9.6 GB/s**, limited by AES-GCM at ~0.1 ns/B. ~3–6 µs setup per small transfer. **~12 µs extra per kernel submission** (encrypted GSP-RPC). NVLink encryption: −10–12% copy-engine bandwidth, −18% SM-based, ~−10% NCCL, ~4× P2P small-write latency. Well-configured serving: <1% (single GPU with CUDA graphs), ~1.5% (TP4 MoE), ~3% (TP8). Misconfigured: 30–40%. 8-GPU training: 10–13%. GPUDirect RDMA blocked. No diffusion/video tests. |
| [arXiv 2606.23969](https://arxiv.org/abs/2606.23969) "Serialized Bridge" | TDX + Blackwell CC | LLM serving −13–27% throughput. **Model loading 34× slower**. KV-cache restore >2× slower. Small alloc+copy 44× slower. A scheduling flag recovers 57% of the gap, and a worker-thread drain recovers up to 92%. |
| [arXiv 2607.19353](https://arxiv.org/html/2607.19353) | GCP a3-highgpu-1g, H100 + TDX | Fixed-rate TTFT +21.8% (Mistral-7B) and +27.8% (Qwen3-30B-A3B). Throughput −17.7% and −21.1%. Closed-loop −11.5–20.2%. Recommends provisioning 15–25% extra headroom. |
| [arXiv 2409.03992](https://arxiv.org/pdf/2409.03992) (Phala) | H100 | Average <7% on LLMs, near zero for 70B. Overhead is I/O-dominated (TTFT). |

**Video diffusion projection [U, reasoning only; no published measurement found]:**
- Inputs are small: a prompt plus maybe a ~1–5 MB image.
- Outputs are ~5–200 MB of video. At ~3.5–9.6 GB/s that transfer costs <100 ms.
- Denoising runs 20–50 steps of large DiT kernels. Launch overhead of ~12 µs × thousands of kernels per step can add a few percent, so use CUDA graphs or `torch.compile` with mode "reduce-overhead" where feasible.
- **Model loading** is the pain point. A 14B video DiT plus T5 text encoder plus VAE is roughly 30–60 GB, and at ~3.5–9.6 GB/s that takes ~5–20 s versus ~1 s natively. **Keep the model resident. Never use diffusers `enable_sequential_cpu_offload` or model CPU offload, since every step would cross the bounce buffer.**
- Multi-GPU sequence/context parallel (xDiT/USP) on Blackwell MPT pays the ~10–18% NVLink encryption cost on all-to-all traffic. On Hopper PPCIe it pays no encryption cost, but NVLink traffic is cleartext.
- **Expect ~2–10% end-to-end overhead for resident single-GPU video generation. Benchmark before committing.**

### 2.6 Consumer and RTX GPUs [C/U]

- CC is listed only for datacenter Hopper/Blackwell and **RTX PRO 6000 Blackwell Server Edition** ([R595 notes](https://docs.nvidia.com/595trd1-trusted-computing-solutions-release-notes.pdf)).
- GeForce RTX 4090/5090 and workstation RTX cards (non-Server Edition) have no CC mode.
- Without GPU CC, a CVM with a passthrough GPU gets no protection for VRAM or PCIe DMA. The host can read GPU memory and bus traffic, and GPU work would require the CVM to turn on shared DMA ([U] reasoning from the bounce-buffer design).
- **Implication:** a subnet that promises prompt and output confidentiality **must exclude consumer GPUs** from the confidential tier. It could run a separate non-confidential tier for them. The RTX PRO 6000 BSE (96 GB) is the cheapest CC-capable card and is available on GCP G4 (Turin + SEV-SNP) ([GCP supported configs](https://docs.cloud.google.com/confidential-computing/confidential-vm/docs/supported-configurations)).

---

## 3. Software stacks: "run this exact image and prove it"

### 3.1 Phala dstack (open source, Linux Foundation CC project)

Sources: [GitHub Dstack-TEE/dstack](https://github.com/Dstack-TEE/dstack), [paper arXiv 2509.11555](https://arxiv.org/html/2509.11555), [docs](https://docs.phala.com/dstack/overview).

**Components [C]:**
- **dstack-vmm** runs on a bare-metal TDX host and boots CVMs from reproducible OS images (meta-dstack/Yocto). It parses docker-compose directly.
- **Guest agent** (tappd/dstack-guest-agent, reached via `/var/run/dstack.sock`) generates quotes with app-chosen REPORTDATA, gets per-app keys from KMS, and encrypts local storage.
- **dstack-KMS** runs in its own TEE. It verifies quotes before releasing keys, and its **authorization policies live in on-chain smart contracts** (KmsAuth/AppAuth). It derives keys deterministically from app identity, so data stays portable across machines. Replication uses copies or Shamir shares.
- **dstack-gateway** does TLS termination with ACME, and uses RA-TLS internally. **Zero-Trust HTTPS** binds certificates to attested apps through CAA records plus Certificate Transparency monitoring.

**Measurements [C]:**
- MRTD = virtual firmware, RTMR0 = firmware config, RTMR1 = kernel, RTMR2 = initrd/cmdline.
- **RTMR3 = app-id, compose-hash, instance-id, key-provider**. Verify by replaying the RTMR3 event log.
- Tools: `dstack-verifier`, dcap-qvl, the Trust Center UI ([trust.phala.com](https://trust.phala.com/)). NEAR AI and Phala bind a signing address plus nonce into REPORTDATA and check NVIDIA NRAS evidence with a matching nonce (search summaries of [NEAR AI docs](https://docs.near.ai/cloud/verification/model/) and [Phala](https://phala.com/learn/How-TEE-Verification-Works) [R]).

**Hardware [C]:** TDX (4th/5th Gen Xeon, GCP), SEV-SNP (experimental), AWS Nitro, and NVIDIA CC (H100/H200/Blackwell). It has a zkSecurity audit and is used by OpenRouter and NEAR AI.

**Security history [C]:** in the v0.5.6 update, Phala fixed these findings ([post](https://phala.com/posts/dstack-security-update-attestation-pipeline-hardening)):
- QE identity was not validated (critical).
- TCB status was not enforced (high).
- The GPU cert chain was not verified.
- SSRF via `pccs_url`.
- TLS verification to PCCS was off by default.
- RA-TLS certs are not session-fresh (a design trade-off).

**Limitations [C]:** the paper puts physical and firmware attacks out of scope. TEE.fail shows a malicious provider can run dstack workloads in a non-confidential VM while forging all attestation data ([tee.fail](https://tee.fail/)).

**Fit for us [U]:** very good. Our workload is one or a few containers plus weights, and dstack already handles compose hashes, KMS and RA-TLS, and GPU CC. Its gateway and KMS model need adapting to Bittensor: the subnet owner or validators would run the KMS.

### 3.2 Confidential Containers (CoCo) with Kata

Sources: [NVIDIA CoCo reference architecture](https://docs.nvidia.com/datacenter/cloud-native/confidential-containers/latest/overview.html), [CoCo init-data](https://confidentialcontainers.org/docs/features/initdata/), [CoCo policies](https://confidentialcontainers.org/docs/attestation/policies/).

**How it works [C]:**
- Each pod runs in a Kata micro-CVM.
- **Trustee** (KBS plus Attestation Service plus RVPS) performs attestation-gated secret release.
- **Init-data** (the Kata agent `policy.rego`, `aa.toml`, `cdh.toml`) is hashed into hardware evidence, so KBS policy can gate on it. On TDX this goes into MRCONFIGID and on SNP into HOST_DATA [U, background].
- Images are pulled inside the guest and can be signature-verified, with the verification key injected after attestation.
- NVIDIA GPU composite attestation is integrated.

**Constraints [C]:** Kata 4.0.0, GPU Operator 26.3.1+, and "all GPUs on the host to one CVM". There is also Red Hat OpenShift sandboxed containers with GPU CC ([Red Hat](https://developers.redhat.com/articles/2026/05/22/protect-data-offloaded-gpu-accelerated-environments-openshift-sandboxed)).

**Fit [U]:** CoCo is powerful but Kubernetes-heavy, and the pod-level TCB includes the kata-agent policy. Getting a single, stable golden measurement across miner fleets is harder than with a dstack-style fixed image.

### 3.3 Edgeless Contrast (successor to Constellation)

- **Coordinator** (in a CVM) verifies pods against a **Manifest**, which lists allowed policy hashes and expected hardware report values. It acts as the CA for a service mesh.
- An **Initializer** init-container does attestation, and the CLI verifies the Coordinator.
- Contrast runs on Kata CoCo (AKS and bare-metal SNP/TDX).
- For GPUs, the docs I read said GPU attestation "must be handled at the workload layer" (older version).
- Sources: [Contrast overview](https://docs.edgeless.systems/contrast/architecture/overview), [features/limitations](https://docs.edgeless.systems/contrast/1.5/features-limitations), [Constellation → Contrast](https://www.edgeless.systems/blog/from-constellation-to-contrast).

### 3.4 Chutes sek8s (Bittensor SN64)

Sources: [sek8s repo](https://github.com/chutesai/sek8s), [security architecture](https://chutes.ai/docs/core-concepts/security-architecture), [E2EE proxy](https://github.com/chutesai/e2ee-proxy).

**Design [C]:**
- Intel TDX VM images with k3s, attestation services and NVIDIA drivers.
- The **root disk is LUKS-encrypted, and the key is released only after the Chutes attestation service verifies TDX measurements**. "Simply possessing the qcow2 image is not enough."
- **No SSH.** Management goes only through the control plane and a read-only status API.
- Images are **cosign-signed**, and an admission controller rejects unsigned pods.
- Additional integrity layers: `cfsv` (filesystem challenge-response), `inspecto` (Python bytecode hashes), a watchtower that hashes random model-weight slices, SGLang bound to 127.0.0.1 with a password, and net-nanny egress restrictions.

**Attestation [C]:** the validator nonce goes into the TD quote together with GPU evidence. RTMRs are compared to the sek8s golden values, and the host needs PCCS.

**E2EE [C/R]:**
- **ML-KEM-768 keypair generated inside the TEE at startup.** The public key and client nonce are bound into the TDX quote.
- Clients fetch `/e2e/instances/{chute}` (public keys) and `/chutes/{chute}/evidence?nonce=` (TDX quote plus GPU evidence).
- Requests use ML-KEM-768 + ChaCha20-Poly1305, and streaming SSE responses are encrypted.
- Source: [Chutes E2EE post, via search summary](https://chutes.ai/news/end-to-end-encrypted-ai-inference-with-post-quantum-cryptography), [e2ee-proxy](https://github.com/chutesai/e2ee-proxy).

**Fit [U]:** it is the closest existing Bittensor-native reference and is fully open source. It is directly reusable for the host setup, image build and attestation service.

### 3.5 Targon (Bittensor SN4, Manifold Labs + Intel)

Source: [arXiv 2607.21865 / Intel whitepaper](https://arxiv.org/html/2607.21865), [Intel blog](https://community.intel.com/t5/Blogs/Products-and-Solutions/Security/Decentralized-Compute-on-Untrusted-Hardware-Using-Intel-TDX-and/post/1741192). Details:
- **Per-provider, uniquely encrypted Ubuntu 24.04 CVM (QCOW2).** The per-VM disk key is stored in **Intel KBS** and released only after **ITA** attestation matches the expected TDX measurements.
- **The KBS binds the CVM to the provider's source IP on first successful attestation.** That stops cloning, migration and replay from other locations.
- **Re-attestation every block interval (~72 min).**
- Validators issue nonces and forward packages to KBS, which verifies the JWT, the measurements and the NVIDIA report.
- GPUs: nvtrust evidence for H100/H200 (PPCIe) and B200.
- CPUs: Emerald or Granite Rapids.
- Scale: **1,500+ H200** reported ([SimplyTao](https://simplytao.ai/blog/targon-sn4-and-intel-tdx-confidential-compute-on-bittensor) [R]).
- The paper does not deal seriously with physical attacks.

### 3.6 Google Confidential Space and Confidential VMs

- **Confidential Space on H100 (a3-highgpu-1g) went GA on 2026-04-29**, with a known driver-install glitch. **ITA integration arrived 2026-05-20.** Confidential Space on TDX (C3) went GA on 2025-03-31 ([release notes](https://docs.cloud.google.com/confidential-computing/confidential-space/docs/release-notes)) [C].
- Attestation tokens carry the **container image digest**, with custom audience and nonces ([deploy docs](https://docs.cloud.google.com/confidential-computing/confidential-space/docs/deploy-workloads)).
- Confidential VM plus GPU machine types [C] ([supported configs](https://docs.cloud.google.com/confidential-computing/confidential-vm/docs/supported-configurations), [create CVM with GPU](https://docs.cloud.google.com/confidential-computing/confidential-vm/docs/create-a-confidential-vm-instance-with-gpu)):
  - **A3 High (Sapphire Rapids TDX + H100)** only in **europe-west4-c, us-central1-a and us-east5-a**.
  - Sizes 1g/2g/4g are **Spot or Flex-start only**, with no reservations and no multi-node clusters.
  - **G4 (Turin SEV-SNP + RTX PRO 6000)** is in 32+ zones.
- Relevance [U]: Google CS gives a very high-assurance "reference validator/KMS" host, since the operator is not the miner. It is not a miner platform for a decentralized subnet, but miners *could* rent it. The Proof-of-Cloud paper also targets GCP bare-metal TDX.

### 3.7 Azure

- **NCCadsH100v5**: AMD Genoa SEV-SNP + H100 NVL (94 GB). Resize is not supported, Ubuntu 22.04 is the qualified image, and quota is required ([Azure GPU options](https://github.com/MicrosoftDocs/azure-docs/blob/main/articles/confidential-computing/gpu-options.md)) [C].
- NCC40ads_H100_v5 costs about **$8.90/h on-demand and ~$1.64/h spot** ([Vantage](https://instances.vantage.sh/azure/vm/ncc40adsh100-v5), [DevZero](https://www.devzero.io/instances/azure/Standard_NCC40ads_H100_v5)) [R].
- AKS Confidential Containers (Kata CoCo on Azure Linux and Cloud Hypervisor) is still in preview. No GPU support was found ([MS Learn](https://learn.microsoft.com/en-us/azure/aks/confidential-containers-overview)) [C/R].
- [U, background] Azure CVMs use a Microsoft paravisor/vTPM (MAA attestation). The guest TCB includes Microsoft-controlled firmware, which is fine as a trust anchor but different from bare-metal measurements.

### 3.8 Tinfoil

Sources: [Tinfoil attestation architecture](https://docs.tinfoil.sh/verification/attestation-architecture), [blog on building trust](https://tinfoil.sh/blog/2025-01-13-how-tinfoil-builds-trust), [Tinfoil Containers](https://tinfoil.sh/blog/2026-03-10-tinfoil-containers). Design [C]:
- AMD SEV-SNP bare metal plus NVIDIA CC, with multi-GPU on Hopper and Blackwell.
- Firmware, kernel and initrd are measured. **Measurements are reproducibly generated by a GitHub Action (`measure-image-action`), Sigstore-signed, and logged in a transparency log.** Clients check that the runtime measurement equals the signed build.
- **The TLS key is generated in the enclave and tied to the attestation.** Clients pin it.
- Where TLS pinning isn't possible (browsers, proxies), **EHBP** encrypts HTTP bodies with **HPKE (RFC 9180)** to the attested key.
- **Model weights are on dm-verity read-only volumes**, with root hashes committed through `modelwrap` and checked during verification.
- Rate-limit proxies see headers in clear.

**Fit [U]:** a strong template for supply-chain transparency (Sigstore plus reproducible measurements) and for weight integrity (dm-verity).

### 3.9 Secret Network SecretVM

- TDX CVM. A reproducible OVMF/kernel/initramfs/rootfs, where **the initramfs measures the rootfs and the docker-compose file**.
- NVIDIA drivers are in the rootfs. An on-chain KMS validates quotes before releasing keys for the encrypted FS.
- An attest REST server returns TDX and NVIDIA reports.
- Sources: [architecture](https://docs.scrt.network/secret-network-documentation/secretvm-confidential-virtual-machines/architecture), [attestation key fields](https://docs.scrt.network/secret-network-documentation/secretvm-confidential-virtual-machines/attestation/attestation-report-key-fields), [attest server](https://github.com/scrtlabs/secret-vm-attest-rest-server) [C].
- Note: TEE.fail extracted Secret Network's SGX consensus seed, on the older SGX-based chain ([tee.fail](https://tee.fail/)).

### 3.10 The binding chain we need [U, synthesized from all of the above]

```
Hardware root (Intel PCK / AMD VCEK / NVIDIA device cert)
  └─ TD Quote / SNP report  (signature chain + TCB status >= policy)
       ├─ MRTD/RTMR0      == golden(OVMF, VM shape)
       ├─ RTMR1/RTMR2     == golden(UKI kernel+initrd+cmdline, cmdline carries dm-verity root hash of rootfs)
       ├─ RTMR3 / MRCONFIGID / HOST_DATA  == H(app manifest) = H(container image digests, model-weight dm-verity roots, config)
       └─ REPORTDATA[0:64] == SHA512( "vgen-v1" || validator_nonce || H(enclave_pubkeys) || H(gpu_evidence) )
             ├─ enclave_pubkeys: HPKE KEM key (X25519 or X25519+ML-KEM-768 hybrid) + Ed25519 signing key + (optional) TLS cert key
             └─ gpu_evidence: NVIDIA SPDM reports collected in-CVM with gpu_nonce = H("gpu"||validator_nonce||H(pubkeys))
Client: verifies the above (or a validator-signed receipt of it) -> HPKE-encrypts request to KEM key
Enclave: signs every response/output manifest with Ed25519 key -> continuous binding between attestation and work
```

---

## 4. End-to-end privacy design

### 4.1 Client-side encryption to attested keys

- Use **HPKE (RFC 9180)** in Base mode:
  - KEM: X25519, or the X25519+ML-KEM-768 hybrid for PQ, like Chutes' ML-KEM-768 approach.
  - KDF: HKDF-SHA256. AEAD: ChaCha20-Poly1305 or AES-256-GCM.
  - Encrypt `{prompt, negative_prompt, params, input_image}` to the node's attested KEM public key.
  - HPKE's `export()` gives a per-job output key. Tinfoil's EHBP and Chutes' E2EE are prior art.
- Include in the AEAD associated data: job_id, the client's ephemeral key, the node's attestation hash, and the output bucket path. That stops cut-and-paste between jobs [U].
- **Who verifies attestation?** Browsers or SDKs can verify quotes directly (Tinfoil has a browser-native verification stack: [blog](https://tinfoil.sh/blog/2025-12-18-browser-native-verification)). Alternatively, clients trust a validator- or gateway-signed attestation receipt that states "node key K passed policy P at time T". That is weaker, but practical. Offer both [U].

### 4.2 Keys, KMS and sealed storage

- **Ephemeral node keys** are generated at CVM boot and never leave TD memory. They are lost on reboot, which is a feature, not a bug.
- **Why a KMS [U].** You need one only for (a) proprietary model weights, (b) persistent encrypted caches, and (c) stable keys across restarts. Run the KMS **outside miner control**:
  - dstack-KMS on subnet-owner-operated TDX in a verified datacenter, or Google Confidential Space, or Intel KBS as Targon does.
  - Release keys only to quotes matching the manifest and policy.
  - **Never put a network-wide root secret on miner hardware**, since TEE.fail showed Secret Network's consensus seed being extracted.
- **Sealed storage**: TDX has no native sealing. Use KMS-released keys (LUKS/dm-crypt) as sek8s, Targon and dstack do. Bind the disk key to measurement **and** hardware ID. Targon also binds it to source IP.

### 4.3 Model weights

- **Open weights** (e.g. Wan/Hunyuan/LTX-class video models): only integrity matters. Ship a read-only **dm-verity** volume whose root hash is in the measured manifest, like Tinfoil's modelwrap. Chutes-style random slice hashing is an extra check.
- **Proprietary weights**: encrypt at rest and release the key from the KMS only to attested CVMs.
  - Weights sit in plaintext in TD memory (DDR5 with deterministic encryption) and in GPU HBM (not encrypted).
  - A TEE.fail-equipped miner can extract them. **Do not ship high-value proprietary weights to untrusted-miner tiers [U].**

### 4.4 Output delivery

- The enclave encrypts the video using the HPKE-exported key, with chunked AEAD (the STREAM construction) to allow streaming and resume.
- It uploads to **object storage via presigned URLs** (S3/R2/GCS), with the gateway issuing the URLs. The host and gateway see only ciphertext.
- It returns a signed output manifest: `{job_id, sha256(ciphertext), size, attestation_ref}`.
- The client downloads and decrypts.

### 4.5 Metadata and side channels: what the host can still see [C where cited, else U]

- **Network metadata**: source and destination IPs, connection timing, ciphertext sizes. TLS/HPKE does not hide lengths.
- **Output size** reveals resolution, duration, fps and content complexity (codec bitrate). **Mitigation:** fixed resolution/duration presets, constant-bitrate encoding or padding to size buckets, and padding requests up to image-size buckets.
- **Timing**: job duration reveals the step count, resolution and frame count. **Mitigation:** fixed step counts per preset, and optional release at fixed quanta.
- **GPU and host-side signals**: power draw (BMC/PSU), fan, PCIe traffic volume (encrypted but countable), and memory-access patterns through page faults.
  - NVIDIA disables performance counters in CC-on, but **plaintext RPC metadata (read/write pointers), unencrypted semaphores, size-dependent transfer timing, and 1,042 BAR0 fields that stay accessible** were found by [arXiv 2507.02770](https://arxiv.org/html/2507.02770v2).
  - NVLink covert and side channels are shown in [NVBleed, arXiv 2503.17847](https://arxiv.org/pdf/2503.17847).
- **CPU side channels**: single-stepping and instruction counting (TDXdown/TDXploit), interrupt injection (Heckler). Keep crypto constant-time, and prefer libraries hardened for CVMs.
- **Logs**: disable application logging of prompts, errors or stack traces inside the CVM. Scrub exception messages. Allow only structured, non-content telemetry out, and make telemetry fields part of the measured config.
- **Disk I/O patterns** are visible, though encrypted.

---

## 5. Known attacks and limitations

### 5.1 Physical memory-bus attacks

| Attack | Date / venue | Target | Result | Vendor stance |
|---|---|---|---|---|
| **TEE.fail** ([site](https://tee.fail/), [Intel advisory](https://www.intel.com/content/www/us/en/security-center/announcement/intel-security-announcement-2025-10-28-001.html), [AMD-SB-3040](https://www.amd.com/en/resources/product-security/bulletin/amd-sb-3040.html)) | Oct 2025, IEEE S&P 2026 poster | DDR5: TDX (4th/5th Gen Xeon, Xeon 6), SEV-SNP including **ciphertext hiding**, NVIDIA CC on H100/H200/B100/B200 | Passive DDR5 interposer, **< $1,000**, briefcase-sized. Exploits deterministic AES-XTS. **Extracted Intel PCE attestation keys, then forged TDX quotes that DCAP QVL accepts as "UpToDate"**. Showed dstack workloads could be moved to a non-CVM with forged attestation. **NVIDIA GPU attestation can be borrowed** (not bound to a CVM). | Intel: out of scope, no patches. AMD: out of scope, no mitigation planned [C] |
| **Battering RAM** ([site](https://batteringram.eu/)) | Sep 30 2025 | DDR4: Scalable SGX (read/write/replay), **SEV-SNP (attestation broken by replay)**. TDX not vulnerable. DDR5 not supported. | $50 active interposer (analog switches plus a Pi Pico) | Out of scope [C] |
| **WireTap** ([THN](https://thehackernews.com/2025/10/new-wiretap-attack-extracts-intel-sgx.html)) | Oct 2025 | DDR4 SGX | Passive, ~$1k. Extracted the SGX ECDSA attestation key | Out of scope [R] |
| **BadRAM** | IEEE S&P 2025 | SEV-SNP | Manipulates SPD for memory aliasing | Mitigated by boot-time DRAM alias check, reported in PLATFORM_INFO [C via primer] |

**Implication [U]:** in Bittensor the adversary *is* the physical owner. A TEE therefore cannot give cryptographic confidentiality against a motivated miner with ~$1k of equipment and some expertise.
- Attestation *integrity* is also breakable. A miner can forge quotes for machine X after extracting X's keys, but only for machines they physically attacked.
- So forged quotes still carry that machine's PPID or CHIP_ID. A registry that limits one hardware ID to one UID, tracks reputation, and revokes IDs on evidence of abuse still has value.

### 5.2 Software and firmware attacks on CVMs

| Attack | Target | Notes |
|---|---|---|
| **Heckler / WeSee (Ahoi)** ([arXiv 2404.03387](https://arxiv.org/abs/2404.03387), [WeSee](https://arxiv.org/pdf/2404.03526)) | TDX and SNP | Malicious interrupt injection bypassed OpenSSH/sudo auth. Mitigated by guest kernel hardening and Secure AVIC / restricted injection [C] |
| **TDXdown** ([CCS'24](https://dl.acm.org/doi/10.1145/3658644.3690230), [Intel advisory](https://www.intel.com/content/www/us/en/security-center/announcement/intel-security-announcement-2024-10-08-001.html)) | TDX | Bypasses single-step mitigation. StumbleStepping leaks instruction counts, used against wolfSSL ECDSA. CVE-2024-27457, fixed in the TDX module [C] |
| **TDXploit** ([USENIX Sec'25](https://www.usenix.org/conference/usenixsecurity25/presentation/rauscher)) | TDX | Single-stepping and cache attacks [R] |
| **RMPocalypse** ([site](https://rmpocalypse.github.io/), CVE-2025-0033) | SNP Zen 3/4/5 | RMP init race: one 8-byte write gives full compromise. Firmware fix [R] |
| **Heracles** ([site](https://heracles-attack.github.io/), CCS'25) | SNP | Chosen-plaintext oracle via hypervisor page moves that cause deterministic re-encryption. AMD responded with a "feature update" restricting page moves [R] |
| **STALEUS** ([USENIX Sec'26](https://www.usenix.org/conference/usenixsecurity26/presentation/schlueter-2), [XCA](https://xca-attacks.github.io/staleus/)) | SNP Zen 4 (tested on EPYC 9124 Genoa) and Zen 5 (EPYC 9135 Turin) | **Software-only**, 100% success. The hypervisor sets NoSnoop on PSP transactions via the SYSHUB bridge, so the PSP reads stale DRAM. That lets it **forge the Guest Context Page (attestation report and GuestPolicy fields)**, turn on debug, and get arbitrary read/write inside a fully attested CVM. **CVE-2025-54509, [AMD-SB-3039](https://www.amd.com/en/resources/product-security/bulletin/amd-sb-3039.html)**. Disclosed Sept 2025. Fix and TCB version not confirmed here [C from the XCA page] |
| **Milan VCEK root-seed extraction** ([arXiv 2605.12990](https://arxiv.org/abs/2605.12990)) | SNP Milan | **Software-only**: ASP code exec plus fuse-controller write gap extracts the root seed, which lets an attacker **forge reports for any TCB** [R] |
| **Fabricked** ([ETH SECTRS research](https://sectrs.ethz.ch/research.html), [XCA](https://xca-attacks.github.io/staleus/), [Tom's Hardware](https://www.tomshardware.com/pc-components/researchers-attack-amds-infinity-fabric-to-bypass-hardware-security-protections-with-fabricked-flaw-lets-malicious-cloud-hosts-silently-read-confidential-vm-memory-and-forge-attestation-reports)) | AMD SNP (Infinity Fabric) | **Software-only**, in the same "XCA" class as STALEUS. The hypervisor manipulates Infinity Fabric memory routing so that PSP writes are **dropped/misrouted during initialization**, which gives arbitrary read/write in the CVM [C from ETH/XCA]. Tom's Hardware's headline also claims **attestation forging** [R]. The affected SKUs, CVE and AMD fix were not confirmed [U]. |
| **RMPocalypse (attestation forging)** | SNP | ETH says RMP corruption during init can also "forge attestations, enable debug mode, inject code" [C from the ETH page] |
| Intel TDX side-channel survey ([ScienceDirect 2026](https://www.sciencedirect.com/science/article/abs/pii/S0167404826002002)) | TDX | Hypervisor-controlled scheduling, interrupts and paging form a large side-channel surface [R] |

### 5.3 GPU CC weaknesses

- [arXiv 2507.02770](https://arxiv.org/html/2507.02770v2) found:
  - Plaintext GSP-RPC metadata, which permits reordering, repeating or omitting RPCs.
  - Size-dependent transfer timing.
  - Unencrypted UVM semaphores and GPFIFO pointers.
  - 1,042 BAR0 registers left accessible.

  All were disclosed to NVIDIA PSIRT [C].
- NVIDIA's own threat table lists HBM interposers, physical side channels, fault injection and session-key extraction through DPA as out of scope [C].
- PPCIe: NVLink in clear and no key rotation [C].
- GPU attestation is not bound to a CVM [C].

### 5.4 Protocol-level attacks relevant to a subnet

1. **Replay of old quotes.** *Mitigation:* the validator nonce in REPORTDATA and in the GPU nonce, with a short validity window.
2. **Relay / proxy / "cuckoo" attack.** The miner runs fake or non-TEE inference and forwards attestation requests to a real TEE, which might be someone else's rented CVM. *Mitigation:*
   - Bind **all job traffic** to the key in REPORTDATA. Clients encrypt to that key, and every response and output manifest is signed by it.
   - The fake machine then cannot decrypt jobs or sign outputs. Relaying the *whole* service to a real, correctly-measured TEE is "compute reselling". It keeps privacy intact but breaks accounting and Sybil resistance, so **deduplicate hardware IDs** (PPID/CHIP_ID plus GPU device IDs) across UIDs.
   - Sources: [Proof of Cloud paper](https://arxiv.org/abs/2510.12469), [Integrating RA into TLS, ATC'25](https://www.usenix.org/system/files/atc25-weinhold.pdf).
3. **GPU evidence borrowing.** A genuine CVM is paired with GPU reports from elsewhere, or with a non-CC GPU. *Mitigation:*
   - Collect GPU evidence in-CVM with the derived nonce.
   - Put the GPU evidence hash in REPORTDATA.
   - Deduplicate GPU IDs.
   - Run **performance challenges** consistent with the claimed GPUs, e.g. Chutes' GraVal-style GPU challenge. In-CVM `nvidia-smi conf-compute` state must equal CC ON with ReadyState set only after verification.
4. **TEE.fail-style forged attestation.** Undetectable cryptographically. *Mitigation:* hardware-ID registry and reputation; **Proof of Cloud** (a signed, append-only registry of PPIDs and chip IDs in verified datacenters, [proofofcloud.org](https://proofofcloud.org/), [Flashbots](https://writings.flashbots.net/mind-the-gap-tee-poc)); DCEA/TPM binding ([arXiv 2510.12469](https://arxiv.org/abs/2510.12469)); stake and slashing; data-sensitivity tiers.
5. **Rollback / downgrade** of firmware or TCB, or of the image. *Mitigation:* TCB minimums (TDX UpToDate; SNP COMMITTED_TCB ≥ minimum), NVIDIA RIM/VBIOS minimums, and revoking golden measurements for old images with a grace period.
6. **Migration / cloning** of an encrypted VM disk. *Mitigation:* per-VM keys bound to the hardware ID, and to IP as Targon does.
7. **Geolocation / IP checks.** Latency triangulation from several validators can flag relays that cross regions, but it is weak on its own [U].

---

## 6. Practical operations

### 6.1 Where to get CC-capable GPU capacity

| Provider | Offering | Price (where found) | Status |
|---|---|---|---|
| **Azure** NCCadsH100v5 | Genoa SNP + 1–2× H100 NVL | NCC40ads ≈ $8.90/h on-demand, ≈ $1.64/h spot ([Vantage](https://instances.vantage.sh/azure/vm/ncc40adsh100-v5)) | [C] offering, [R] price |
| **GCP** a3-highgpu-1g CVM | SPR TDX + 1× H100 | Spot/Flex-start only, 3 zones. Price not collected | [C] |
| **GCP** G4 CVM | Turin SNP + RTX PRO 6000 | Not collected | [C] |
| **Phala Cloud** | TDX + H100/H200/B200/B300 GPU TEE (1–8 GPUs), US-West and India | H100 $3.08/GPU-h (trial), B300 $6.50/GPU-h, "from $3.80/h", H200 by quote ([H200 page](https://phala.com/gpu-tee/h200), [pricing](https://phala.com/pricing)) | [R] |
| **OpenMetal** | Bare-metal H200 NVL, dual Xeon 6530P, TDX, 1 GPU per CVM, Ashburn ([page](https://openmetal.io/resources/hardware-details/gpu-server-h200/)) | Not collected | [R] |
| **Corvex** | HGX B200 with CC ([blog](https://www.corvex.ai/blog/confidential-computing-meets-nvidia-hgxtm-b200-secure-ai-without-the-performance-trade-off)); H200 from $2.15/h (non-CC price) | | [R] |
| **Verda** (ex-DataCrunch) | Confidential computing docs ([docs](https://docs.verda.com/cpu-and-gpu-instances/confidential-computing/)) | | [R] |
| **Vast.ai** | Article on NVIDIA CC ([article](https://vast.ai/article/Absolute-Security-with-NVIDIA-Confidential-Computing)) | Not confirmed that CC instances are sold | [U] |
| **OVHcloud** | High Grade bare metal with 5th Gen Xeon **TDX (CPU)** ([OVH](https://corporate.ovhcloud.com/en/newsroom/news/baremetal-emerald-rapids/), [UC page](https://us.ovhcloud.com/bare-metal/uc-confidential-computing/)) | GPU CC not confirmed | [R]/[U] |
| **Lambda, CoreWeave, Hetzner** | No public GPU-CC offering found in this research | — | [U] (negative finding) |
| **Chutes/Targon miners** | Production fleets (Targon: 1,500+ H200) | — | [R] |

### 6.2 What a miner must do (bare metal)

1. **Hardware**: Xeon 5th/6th Gen (TDX) or EPYC Genoa/Turin (SNP) with H100/H200 (HGX 8-GPU for PPCIe), B200/B300 HGX, or RTX PRO 6000 BSE. The motherboard must expose TDX/SNP and Secure Boot options.
2. **BIOS**: apply the settings in §1.1 or §1.2, and update the BIOS so the TDX module / SEV firmware is current.
3. **Host OS**: Ubuntu 25.10 with kernel 6.17+ (Intel) or 25.04 with 6.14+ (AMD).
   - Canonical tdx tooling, QEMU/OVMF, libvirt.
   - VFIO plus `ib_umad` autoloaded. Blacklist nvidia/nouveau on the host.
   - Fabric Manager on the host for Blackwell MPT, or in the guest for Hopper PPCIe.
4. **PCCS** (Intel) with an Intel PCS API subscription key, or reliance on a remote PCCS or ITA. AMD needs no host service, but KDS is rate-limited, so verifiers should cache.
5. **GPU mode**: run `nvidia_gpu_tools.py --set-cc-mode=on` (or `--set-ppcie-mode=on`) for every GPU and switch, then reset. The mode persists across reboots. It **cannot be set with host Secure Boot on**; either disable it temporarily or set the mode from inside the guest ([guide p.16–17](https://docs.nvidia.com/cc-deployment-guide-tdx.pdf)).
6. **Launch the subnet CVM image** with the exact VM shape (vCPUs, memory, GPU topology), because it affects RTMR0 / MEASUREMENT.
7. **Operational gotchas** [C]:
   - A guest reboot **terminates** the CVM.
   - Persistence mode is required.
   - After the driver unloads, FLR or a reboot is needed.
   - PPCIe key rotation is unsupported, so restart CVMs periodically.
   - Keep the NCCL version ≥ 2.26.3.
   - HGX Hopper FW ≥ 1.8.0 avoids GPUs dropping off the bus.

**Difficulty for typical Bittensor miners [U]:** high.
- Most GPU marketplace rentals (RunPod, Vast, most Lambda/CoreWeave products) give neither BIOS access nor bare metal. Miners need owned or colocated servers, or bare metal from providers that allow BIOS changes.
- Expect a smaller, more professional miner set, as with Targon and Chutes' TEE tier.
- Reduce friction by shipping:
  - a one-shot host installer (reuse sek8s host tools);
  - a pre-flight checker covering BIOS flags, TDX module version, SEV firmware, GPU VBIOS and CC mode;
  - a known-good hardware compatibility list.
- Allow cloud CVMs (Azure NCC, GCP a3 CVM, Phala) as a lower-effort path. Measurements differ there (paravisor or Google firmware), so maintain a separate golden set per platform.

---

## 7. Recommended reference architecture

### 7.1 Components

1. **Release pipeline (public, reproducible)**
   - Builds a **UKI** (OVMF + kernel + initrd). The cmdline carries the dm-verity root hash of a read-only rootfs (containerd/podman plus agent).
   - Builds **inference container images** pinned by digest, and **model bundles** as dm-verity images with root hashes.
   - Emits the **Golden Manifest**: expected MRTD/RTMR0–2 per (platform × VM shape), SNP MEASUREMENT per shape, app-manifest hash (RTMR3/MRCONFIGID/HOST_DATA), NVIDIA driver/VBIOS minimums, and the policy version.
   - Signs everything through **Sigstore** into the transparency log (the Tinfoil model) and commits the manifest hash on-chain (subnet commitment or a contract) so validators agree.
2. **Miner host (untrusted)**: bare metal, BIOS in TDX/SNP mode, GPUs in CC/MPT mode, runs QEMU/dstack-vmm, PCCS, networking. It holds no secrets.
3. **Guest CVM (trusted, measured)**:
   - Minimal OS with **no SSH or debug**. Egress is allowlisted to the gateway, object storage, NRAS/RIM/OCSP (or cached collateral), and the KMS.
   - The **attestation agent** makes boot-time keys (HPKE KEM, Ed25519 signing, optional TLS), runs in-CVM GPU attestation and sets ReadyState only on success, and serves `/attest?nonce=` returning {TD quote or SNP report, event log, GPU evidence, pubkeys, manifest}.
   - The **inference worker** (e.g. a diffusers/xDiT-based video pipeline) listens on localhost only. It decrypts jobs, generates, encodes, encrypts output, uploads, and signs the manifest.
   - Content logging is off.
4. **Validators**:
   - A verification library: dcap-qvl or Intel QVL with pinned Intel root, QE identity and TCB checks; AMD SNP verifier with pinned ARK and KDS cache; NVAT local verifier with cached RIM/OCSP, falling back to NRAS.
   - A policy engine, a hardware-ID registry (on-chain or a shared DB), a challenge scheduler, and a scoring loop.
   - Performance and correctness spot-checks: deterministic seeds let validators re-run a sample job on a trusted reference and compare outputs or perceptual hashes [U].
5. **Subnet KMS (optional)**: dstack-KMS or Trustee/KBS running in a TEE on subnet-owner infrastructure in a verified datacenter, or Google Confidential Space. It releases per-node wrapped keys for proprietary weights or persistent caches only on a policy match.
6. **Gateway / API (untrusted for content)**: auth, billing, routing, presigned-URL issuance, and caching and serving attestation bundles and validator receipts. It sees only ciphertext and metadata.
7. **Client SDK / web client**: verifies the attestation bundle (full or receipt-based), HPKE-encrypts to the node, decrypts streamed or uploaded output, and verifies the output manifest signature.
8. **Encrypted object store**: per-job paths, short TTLs, server-side lifecycle deletion. Only ciphertext is stored.

### 7.2 Attestation and job flow (text diagram)

```
[Release CI] --build+measure--> Golden Manifest (Sigstore + on-chain hash)
                                          |
                                          v
 Validator V                         Miner host (untrusted)                 CVM (TD/SNP + CC GPUs)
 -----------                         ----------------------                 -----------------------
 1. REGISTER: miner submits (uid, endpoint)
 2. V -> nonce N (32B, random, ttl 60s) ------------------------------------> agent
                                                                             3. gpu_nonce = H("gpu"||N||H(PK))
                                                                                GPU evidence E_gpu via NVAT (all GPUs)
                                                                             4. RD = SHA512("vgen-v1"||N||H(PK)||H(E_gpu))
                                                                                Q = TDQuote(RD)  (host QE signs)
 5. <----------------------- {Q, CCEL event log, E_gpu, PK, manifest_id} ----
 6. V verifies:
    a. Q signature chain -> Intel root (or SNP -> pinned ARK); QE identity; TCB status >= policy
    b. MRTD, RTMR0..2 == golden[platform][shape]; replay event log -> RTMR3 == H(app manifest)
    c. RD == SHA512("vgen-v1"||N||H(PK)||H(E_gpu))  (freshness + key + GPU binding)
    d. E_gpu: cert chain -> NVIDIA root, OCSP ok, RIM match, CC=ON, not devtools, nonce==gpu_nonce,
       GPU count/model == claimed; driver/VBIOS >= min
    e. Hardware IDs (PPID/CHIP_ID, GPU UEIDs/serials) not bound to another UID; not revoked; (tier: in Proof-of-Cloud registry)
    f. Perf challenge: run small fixed-seed generation, latency within bound, output hash matches, signed by PK_sig
 7. V publishes receipt R = Sign_V(uid, H(PK), platform, tier, policy_ver, t, expiry) to gateway / chain

 JOB:
 Client --(fetch R or full bundle; verify)--> HPKE.Seal(PK_kem, info=job_id||H(R), req{prompt,image,params})
        --> Gateway (ciphertext) --> CVM worker: open, generate, encode (fixed preset), pad
        CVM: out_key = HPKE.export("out"), AEAD-STREAM encrypt video -> PUT presigned URL
        CVM: M = Sign(PK_sig, {job_id, H(ct), size_bucket, t, H(R)}) --> Gateway --> Client
        Client: GET ciphertext, verify M, decrypt
```

### 7.3 Validator verification checklist

**CPU TEE (TDX)**
- [ ] Quote v4/v5 parses. The signature chains PCK → Intel SGX Root CA (pinned). CRLs checked.
- [ ] QE Identity matches Intel's collateral. (This was a critical gap in dstack before v0.5.6.)
- [ ] TCB status is **UpToDate**. Optionally allow `SWHardeningNeeded` only for an explicit list of advisory IDs. Reject `OutOfDate`, `Revoked` and `ConfigurationNeeded`, unless the policy explicitly allows a configuration flag.
- [ ] The TDX module identity/SVN is at least the minimum. Collateral is fresh (≤24 h).
- [ ] TD attributes: DEBUG=0. No unexpected features (e.g. SEPT_VE_DISABLE per policy).
- [ ] MRTD, RTMR0, RTMR1, RTMR2 equal the golden values for (CPU gen, VM shape, image version). RTMR3 replay equals the app-manifest hash. MRCONFIGID/MROWNER match the policy (zero or the expected value).
- [ ] REPORTDATA equals the expected binding hash, and the nonce is fresh and unused.

**CPU TEE (SNP, if allowed)**
- [ ] ARK pinned, then ASK, then VCEK (not VLEK, unless it's a trusted CSP). CRL checked.
- [ ] Product is Genoa or Turin (**reject Milan**). REPORTED_TCB and COMMITTED_TCB ≥ minimum per family (Turin includes FMC).
- [ ] POLICY: DEBUG=0, ciphertext hiding required, PAGE_SWAP_DISABLE, SMT per policy. PLATFORM_INFO: alias check done, ciphertext hiding active.
- [ ] MEASUREMENT equals the golden value per vCPU count/type. HOST_DATA equals the manifest hash. REPORT_DATA equals the binding. VMPL is as expected.

**GPU**
- [ ] One evidence entry per GPU, and for Hopper PPCIe per NVSwitch. Count and model match the miner's claim.
- [ ] Device cert chains to the NVIDIA root and passes OCSP. RIM for the driver and VBIOS matches. Firmware is at least the minimum.
- [ ] CC mode is ON (not devtools). The mode fits the tier: MPT CC or SPT for confidential; PPCIe allowed only if cleartext NVLink is acceptable.
- [ ] The nonce equals the derived gpu_nonce, and H(evidence) appears in REPORTDATA.
- [ ] GPU IDs are not claimed by another UID.

**Identity, liveness, economics**
- [ ] One PPID/CHIP_ID per UID, and no GPU ID reuse. Registry records first-seen time and IP/ASN.
- [ ] Optional Proof-of-Cloud membership gives the "verified-DC" tier.
- [ ] Performance challenge passes within a latency bound (catches under-provisioned or relayed nodes). Outputs are signed with PK_sig.
- [ ] Randomized canary jobs from validators: fixed-seed determinism check, measuring both correctness and tokens/frames per second.
- [ ] Miner stake is at least the tier minimum. Slash or blacklist on attestation failure, hardware-ID collision, or signature mismatch.

### 7.4 Re-attestation cadence [U, recommended]

- **On every CVM boot** (new keys): full attestation before the node receives any work.
- **Randomized challenges** every **10–30 minutes** per node, jittered and unannounced. Targon uses ~72 minutes, which is acceptable but coarse. GPU evidence collection takes seconds, and TD quote generation takes tens of ms.
- **Per job**: no new quote. Every output is signed by the attested key, which gives continuous binding.
- **Collateral refresh**: Intel TCB Info, QE Identity and CRLs, AMD CRLs, and NVIDIA OCSP/RIM daily. After an Intel, AMD or NVIDIA TCB-recovery event, raise the minimums with a grace window of 7–14 days, then evict.
- **Key lifetime**: at most 24 hours or until reboot. Rotate by restarting the CVM (needed anyway for PPCIe, which has no key rotation) or through in-CVM rekey plus re-attestation.
- **Image updates**: publish a new golden manifest, then allow old and new side by side for N days, then revoke the old.

### 7.5 Tiering to reflect residual risk [U]

- **Tier A (verified-DC)**: TDX + Blackwell MPT or H100/H200 SPT. The hardware ID must be in a Proof-of-Cloud-style registry or on a hyperscaler CVM. For sensitive user content.
- **Tier B (self-hosted TEE)**: any policy-compliant bare-metal TEE miner. Default tier. Privacy against software-level snooping, but not against a determined physical attacker.
- **Tier C (non-confidential)**: consumer GPUs. No privacy claims. Only public or benign prompts, or benchmarking.

State the physical-attack caveat plainly in the user-facing privacy policy.

---

## 8. Open questions / to verify before building

1. Does NVENC/NVDEC work in CC mode on H100/H200/B200 under R595+, and at what session limits? (Known Blackwell decoder bug.)
2. Actual overhead of our target video models (e.g. Wan-class 14B, LTX, Hunyuan) on H100 SPT and B200 MPT with CUDA graphs. Measure load time, per-step time and end-to-end time.
3. The AMD fix and minimum TCB for **STALEUS (CVE-2025-54509, AMD-SB-3039)** and **Fabricked**. Both are software-only on Zen 4/5 and can forge attestation-relevant state, which breaks the verifier's assumptions. Pin the SNP minimum TCB to AMD's fixed firmware before admitting any SNP miners. Until then, run a TDX-only confidential tier.
4. GB200/NVL72 CC support status.
5. Whether TDISP/TDX Connect for B200 is usable in 2026 host stacks, and how it changes measurements.
6. Intel PCS / ITA rate limits and costs at validator scale. AMD KDS rate limits.
7. Legal and ToS aspects of promising privacy given the TEE.fail class of attacks.

---

## 9. Key sources (grouped)

- **Intel TDX**: [Linux TDX docs](https://docs.kernel.org/arch/x86/tdx.html) · [TDVF design guide](https://cdrdv2-public.intel.com/733585/tdx-virtual-firmware-design-guide-rev-004-20231206.pdf) · [TDX CPUs](https://www.intel.com/content/www/us/en/support/articles/000091103/processors/intel-xeon-processors.html) · [TCB recovery](https://www.intel.com/content/www/us/en/developer/articles/technical/software-security-guidance/best-practices/trusted-computing-base-recovery.html) · [QVS](https://github.com/intel/SGX-TDX-DCAP-QuoteVerificationService) · [ITA GPU](https://docs.trustauthority.intel.com/main/articles/articles/ita/concept-gpu-attestation.html) · [TDX Connect](https://community.intel.com/t5/Blogs/Tech-Innovation/Data-Center/Announcing-Intel-TDX-Connect-Support-on-Intel-Xeon-6/post/1668423)
- **AMD SEV-SNP**: [SNP primer](https://arxiv.org/html/2608.04039v1) · [AMD-SB-3040](https://www.amd.com/en/resources/product-security/bulletin/amd-sb-3040.html) · [Contrast SNP](https://docs.edgeless.systems/contrast/1.9/architecture/snp) · [SEV-TIO Linux 6.19](https://www.phoronix.com/news/Linux-6.19-PCIe-Link-Encrypt)
- **NVIDIA**: [CC deployment guide v7.1](https://docs.nvidia.com/cc-deployment-guide-tdx.pdf) · [R595 release notes](https://docs.nvidia.com/595trd1-trusted-computing-solutions-release-notes.pdf) · [Secure AI whitepaper](https://docs.nvidia.com/nvidia-secure-ai-with-blackwell-and-hopper-gpus-whitepaper.pdf) · [CoCo platforms](https://docs.nvidia.com/datacenter/cloud-native/confidential-containers/latest/supported-platforms.html) · [NVAT](https://docs.nvidia.com/attestation/nv-attestation-sdk-cpp/latest/overview.html) · [nvtrust](https://github.com/NVIDIA/nvtrust)
- **Performance**: [Blackwell CC benchmark 2608.26575](https://arxiv.org/html/2608.26575) · [Serialized Bridge 2606.23969](https://arxiv.org/abs/2606.23969) · [H100+TDX 2607.19353](https://arxiv.org/html/2607.19353) · [Hopper benchmark 2409.03992](https://arxiv.org/pdf/2409.03992)
- **Stacks**: [dstack](https://github.com/Dstack-TEE/dstack) · [dstack paper](https://arxiv.org/html/2509.11555) · [dstack hardening](https://phala.com/posts/dstack-security-update-attestation-pipeline-hardening) · [sek8s](https://github.com/chutesai/sek8s) · [Chutes security](https://chutes.ai/docs/core-concepts/security-architecture) · [Chutes e2ee-proxy](https://github.com/chutesai/e2ee-proxy) · [Targon/Intel paper](https://arxiv.org/html/2607.21865) · [Tinfoil](https://docs.tinfoil.sh/verification/attestation-architecture) · [SecretVM](https://docs.scrt.network/secret-network-documentation/secretvm-confidential-virtual-machines/architecture) · [Contrast](https://docs.edgeless.systems/contrast/architecture/overview) · [CoCo init-data](https://confidentialcontainers.org/docs/features/initdata/) · [Confidential Space notes](https://docs.cloud.google.com/confidential-computing/confidential-space/docs/release-notes)
- **Attacks**: [TEE.fail](https://tee.fail/) · [Battering RAM](https://batteringram.eu/) · [WireTap](https://thehackernews.com/2025/10/new-wiretap-attack-extracts-intel-sgx.html) · [Heckler](https://arxiv.org/abs/2404.03387) · [TDXdown](https://dl.acm.org/doi/10.1145/3658644.3690230) · [RMPocalypse](https://rmpocalypse.github.io/) · [Heracles](https://heracles-attack.github.io/) · [STALEUS](https://www.usenix.org/conference/usenixsecurity26/presentation/schlueter-2) · [Milan VCEK seed](https://arxiv.org/abs/2605.12990) · [GPU-CC analysis 2507.02770](https://arxiv.org/html/2507.02770v2) · [NVBleed](https://arxiv.org/pdf/2503.17847)
- **Relay / location**: [Proof of Cloud paper](https://arxiv.org/abs/2510.12469) · [proofofcloud.org](https://proofofcloud.org/) · [Flashbots: Mind the Gap](https://writings.flashbots.net/mind-the-gap-tee-poc)
- **Clouds**: [Azure GPU CVM](https://github.com/MicrosoftDocs/azure-docs/blob/main/articles/confidential-computing/gpu-options.md) · [GCP CVM configs](https://docs.cloud.google.com/confidential-computing/confidential-vm/docs/supported-configurations) · [Phala GPU TEE](https://phala.com/gpu-tee/h200) · [OpenMetal H200](https://openmetal.io/resources/hardware-details/gpu-server-h200/)
