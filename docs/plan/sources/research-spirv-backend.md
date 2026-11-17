# Research: direct SPIR-V backend references

**Status**: <span class="hg-status summary">sources</span>. A research agent collected these on 2026-11-14 for [W11.2](../work/accel-lang.md), following the owner's Q11.2 refinement: read Slang only after a licence check, look for other stable references as well, and build our own without copying anything one to one. The agent read licence files, READMEs, specs and paper landing pages. It did not read any project's source files. Nothing on this page is a decision.

## Slang licence

- **Repository**: `Apache-2.0 WITH LLVM-exception` ([LICENSE](https://github.com/shader-slang/slang/blob/master/LICENSE)). The copyright holders are CMU and NVIDIA (2016) and The Khronos Group (2024), per [REUSE.toml](https://github.com/shader-slang/slang/blob/master/REUSE.toml). There is no top-level NOTICE file. A few vendored files carry other licences (MIT, BSL-1.0, NCSA, Unlicense).
- **History**: the licence was MIT up to [v2024.1.0](https://github.com/shader-slang/slang/blob/v2024.1.0/LICENSE). The project was relicensed after it moved to Khronos ([press release, 2024-11-21](https://www.khronos.org/news/press/khronos-group-launches-slang-initiative-hosting-open-source-compiler-contributed-by-nvidia)). The CLA binds only upstream contributors.
- **Patents**: Apache-2.0 §3 grants a contributor patent licence. Khronos also plans to ratify the language spec under its IP Framework.
- **Docs**: the in-repo docs fall under the repository default licence (inferred from REUSE.toml, not verified). The shader-slang.org website is "© Khronos, all rights reserved".

**What follows for us** (not legal advice):
- Reading the code, docs and papers and designing our own implementation from them needs no licence. Copyright protects expression, not ideas, algorithms or IR concepts.
- Duties start only if code, or a substantial part of it, is copied, paraphrased closely or translated. This includes tables and opcode or capability maps.
- Working rule: take notes in our own words and write the code from those notes.
- Generated tables come from the SPIR-V grammar JSON in SPIRV-Headers, never from Slang. The SPIRV-Headers licence is still unverified.
- Text from the website is never copied into our docs. The name "Slang" is not used for anything of ours.

## References

| Source | Licence | Stability | Teaches |
|---|---|---|---|
| [SPIR-V 1.6 unified spec](https://registry.khronos.org/SPIR-V/specs/unified1/SPIRV.html) | Khronos spec | Normative | §2.11 structured control flow, §2.23 uniformity, linkage, spec constants, capabilities. Read first. |
| [NonSemantic.Shader.DebugInfo](https://github.khronos.org/SPIRV-Registry/nonsemantic/NonSemantic.Shader.DebugInfo.html) | Khronos spec | 100 ratified 2021 | The only standard for rich debug info. DebugLine is separate from OpLine. |
| Klimis, Clark, Wickerson, Donaldson, "Taking Back Control in an IR for GPU Computing", POPL 2023 ([PDF](https://www.doc.ic.ac.uk/~afd/homepages/papers/pdfs/2023/POPL.pdf), [Alloy model](https://github.com/mc-imperial/spirv-control-flow)) | Paper | Peer-reviewed; its rules are now in the spec | Why the structured control-flow rules look the way they do. |
| [SPIRV-Tools](https://github.com/KhronosGroup/SPIRV-Tools) | Apache-2.0 | Industry standard. The README calls the validator incomplete and the linker under development | The in-test gate (`SpirvTools::Validate`, `Optimizer`, `Linker`). Necessary, not sufficient. |
| [Tint SPIR-V writer](https://dawn.googlesource.com/dawn/+/refs/heads/main/src/tint/lang/spirv/writer/) | BSD-3 | Production (Chrome) | IR to SPIR-V, with lowering ("raise") kept separate from the printer. The closest match to ASL. |
| [glslang SPIR-V builder](https://github.com/KhronosGroup/glslang) | Mixed (per-file header unverified) | Mature | Emission patterns for merge and continue blocks, capability tracking and debug info. Shaped by its GLSL front end. |
| [naga `spv-out`](https://github.com/gfx-rs/wgpu/tree/trunk/naga) | MIT OR Apache-2.0 | Primary backend | A small, readable second emitter to compare against Tint. |
| [WGSL §15.2 Uniformity](https://www.w3.org/TR/WGSL/) | W3C | Candidate Recommendation draft | A complete source-level uniformity analysis to start from. |
| Rosemann, Moll, Hack, "An Abstract Interpretation for SPMD Divergence on Reducible CFGs", POPL 2021 ([DOI](https://doi.org/10.1145/3434312)) | Paper | Peer-reviewed; LLVM UniformityAnalysis builds on it | Divergence analysis at IR level. |
| [LLVM SPIR-V usage](https://llvm.org/docs/SPIRVUsage.html), [Convergence and Uniformity](https://llvm.org/docs/ConvergenceAndUniformity.html) | Apache-2.0 WITH LLVM-exception | OpenCL-first; Vulkan parts not tested extensively | Formal definitions of convergence and uniformity. The emitter itself matters less for us. |
| [rspirv](https://github.com/gfx-rs/rspirv) | Apache-2.0 | SPIR-V 1.5; structured representation unfinished | Ideas for a grammar-driven builder API only. |
| [DXC SPIR-V codegen](https://github.com/microsoft/DirectXShaderCompiler) | NCSA | Mature | Large-scale capability and extension decisions. Read for specific questions only. |
| Mesa `spirv_to_nir` | MIT | Production consumer | Which emitted forms a driver accepts. A consumer view, not an emitter. |
| Bahmann, Reissmann, Jahre, Meyer, "Perfect Reconstructability of Control Flow from Demand Dependence Graphs", TACO 2015 ([DOI](https://doi.org/10.1145/2693261)) | Paper | Foundational | Structurizing control flow. Needed only if the ASL IR ever becomes unstructured. |
| He, Fatahalian, Foley, "Slang", ACM TOG 37(4), SIGGRAPH 2018 ([DOI](https://doi.org/10.1145/3197517.3201380)) | Paper | Peer-reviewed | The module and specialisation model; background for link-time specialisation. Not about emission. |

## Unverified

- The licence of the Slang docs site.
- The SPIRV-Headers grammar JSON licence.
- The licence header of glslang's `SPIRV/SpvBuilder.cpp`.
- The exact commit of Slang's relicensing.
- Whether naga validates uniformity, and whether Tint's `analysis/` holds a uniformity pass.
- The location of Mesa's `spirv_to_nir` (the fetch was blocked).

The agent found no papers on structurization or uniformity newer than 2023; it did not search for them.
