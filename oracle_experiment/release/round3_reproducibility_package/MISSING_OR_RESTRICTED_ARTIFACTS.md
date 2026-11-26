# Known limits of this package

The following items are intentionally not included:

- model weights and Hugging Face caches;
- Python/Conda environments, build caches, and temporary render files;
- primary raw generation JSONL files, pending a distribution-rights review;
- benchmark text beyond the frozen ID/hash manifests;
- Git credentials, access tokens, or other secrets;
- an independent timestamp or preregistration record;
- a Zenodo DOI or public GitHub release.

The force-answer and primary raw generations remain preserved locally and are
bound to comparison/replay manifests by SHA-256 where available. Reviewers may
request controlled access from the authors. Recreating raw generations requires
the pinned Qwen3 revision, GPU inference, the documented prompts/parsers, and
the recorded seed construction; this package is primarily for replay and audit.
