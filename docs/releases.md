# Releases and offline archives

## What a release contains

A versioned release publishes the project source plus a bilingual offline catalogue ZIP and its sibling SHA-256 file. Extract the whole ZIP and open `index.html`. The archive contains local interface assets, catalogue pages, technical profiles, the MIT license, instructions and source-rights notes. It excludes manufacturer PDFs, installers, private research, live counters and nested downloads.

Ordinary website builds also generate this distribution for the native download menu. The site download does not depend on GitHub release publication. The optional site's download counter measures its own complete ZIP responses only; it does not count GitHub downloads.

## Build and verify a distribution

```sh
mkdir -p dist
python3 -m thinkpad_archive offline-release --output dist/offline
```

The output directory must be new and its parent must exist. `--default-language es` selects a Spanish root entry without removing English. The builder creates a fresh collection-free site from validated metadata, checks ZIP membership and every member hash, then publishes the ZIP/checksum pair into the output directory. It does not accept an arbitrary prebuilt site.

The sibling `.zip.sha256` verifies the whole archive. On Linux, from its directory:

```sh
sha256sum -c thinkpad-archive-*.zip.sha256
```

PowerShell users can run `Get-FileHash PATH_TO_ZIP -Algorithm SHA256` and compare the result with the checksum file. The extracted `SHA256SUMS.json` lists hashes for individual members. These checks establish byte integrity, not publisher authentication or hardware compatibility.

Member order, timestamps and modes are fixed. Compare compressed ZIP hashes only for the same metadata, build options and Python/zlib toolchain. A Spanish-default build intentionally changes root-language and x-default metadata. Ordinary failures remove task-owned partial output; interruption or power loss can leave incomplete files, so directory presence alone is not verification.

## Version and channel

`VERSION` identifies the website/software release, not a promise of exhaustive model coverage or certified drivers. The matching Git tag is `vVERSION` at the exact accepted commit. Versions below 1.0 remain prereleases; the 1.x line uses stable releases.

The 1.0 boundary is the documented catalogue/build behavior and public data formats. Preserve model IDs, existing native links, the no-script/offline path and aggregate history when extending the project. Explain necessary incompatible changes in their release notes; uncertain source facts remain qualified rather than silently becoming guarantees.

## Publication sequence

1. Update `VERSION` and the corresponding changelog section. Complete the [checklist](release-checklist.md) and independent source review before integration.
2. Push the accepted source to the intended branch. Verify the remote SHA and its exact-head CI. Source publication may trigger the separate hosting webhook; it is not proof of a successful deployment.
3. Create and push the matching version tag on the accepted commit. The **Release draft** workflow reruns CI on Python 3.11 and 3.13 plus workflow syntax checks, then prepares one draft with changelog notes and the verified offline files already attached.
4. Inspect that draft's tag target, notes, channel and both asset names, sizes and GitHub-reported SHA-256 digests. Download and validate the real ZIP and every manifest member. Only then publish the existing draft.
5. Verify the public release and downloads. The **Offline release archive** workflow tests the released snapshot and reconciles identical existing assets without uploading them again. Changed or partial asset sets are refused, never overwritten.

The draft workflow owns creation. Do not race it with another `gh release create`, move an existing tag or use `--clobber`. After an ambiguous command, inspect the existing ref/release before repeating anything. Authentication or network errors are not evidence of absence.

The draft and published-release paths were exercised successfully for [v0.5.6](https://github.com/MikelCalvo/thinkpad-archive/releases/tag/v0.5.6), including actual asset downloads and full manifest validation. Future versions still need their own exact-head checks. GitHub workflows do not change branch protection, deploy the website, modify DNS or submit sitemaps to webmaster accounts.
