# 1.0.0 acceptance checklist

This is a checklist, not a claim that the steps already passed.

- Confirm the public file allowlist and inspect source plus all reachable Git history for manufacturer originals, personal records, host paths and credentials.
- Confirm the MIT license for original project material remains included, with third-party rights and icon attribution unaffected.
- Validate model/source/document/driver references and programmatically deduplicate counts; preserve exact variants and documented gaps.
- Confirm X200/X201/X220/X230 and supported variants are present, and early models receive source-backed references rather than invented support.
- Verify driver associations against their actual source route or explicit README model list. Distinguish listing records from unique packages and live availability checks.
- Run the full offline test suite with a nonempty selected count.
- Rehearse documented build commands from a clean source copy. Build fresh English-root and Spanish-root sites.
- Validate internal links, fragments, language counterparts and metadata escaping. All manufacturer files remain external links.
- Exercise model search, combined filters, a historical model, X230, EN/ES switching, source links, utility layout and narrow-screen behavior in a real browser.
- Exercise every calendar year in the timeline, its native keyboard/touch control, global search, all-model/unknown-date views, grouped variants and same-year language switching. Verify static year pages and empty years without JavaScript.
- Confirm file:// browsing works without a local server, and all entries remain readable without scripts. State untested legacy-browser and hardware boundaries.
- Generate the versioned offline ZIP with `python3 -m thinkpad_archive offline-release --output NEW_DIR`. Check its sibling SHA-256 and every manifest member, extract to an isolated folder, then exercise catalogue/model/language/filter/no-script flows from the actual extracted files. Verify no collection or bundled manufacturer files/live counter history.
- For published releases, require the exact released tag to match VERSION and verify the offline workflow's tested commit plus both attached asset names/checksums. Local workflow rehearsal is not hosted execution; never replace assets silently or publish a release merely to test automation.
- For tag-driven release drafts, verify both Python CI jobs and workflow syntax on the exact tag commit before inspecting the draft, notes, prerelease state and both assets. Draft creation is not public publication; manually publish only after review. If an interrupted attempt leaves a draft or partial assets, reconcile it rather than replacing it or replaying a create command.
- Check that branch/PR CI actually ran after the push; a local commit or local passing runner is not hosted CI. Repository required-check rules and source-triggered deployment are separate operator decisions.
- Check firmware warnings, evidence-level labels and missing-data states. Remove personal-inventory/physical-media features from the public project.
- Review SPEC compliance, then implementation quality on the frozen candidate. Fix demonstrated defects and rerun affected gates.
- Update public status/changelog from actual results; declare 1.0.0 only after acceptance.
- Confirm the exact public remote target and authorized assets before upload. Verify published URL and exact HEAD without replaying a successful write.
