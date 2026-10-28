# Data quality and source errata

Introduction years are source-backed navigation metadata, not hardware compatibility claims. Version 0.3.2 additionally accepts explicitly qualified dated commercial listings and regional availability records; these do not certify first launch. Their evidence kind and localized limitations are visible on each affected model page. The catalogue distinguishes an exact product launch, an explicitly dated SKU announcement, and a community history assertion. An earliest published PSREF SKU date documents that platform in that year; it does not certify the first worldwide sale. Where a manufacturer's dated announcement is available, it takes priority. Manual copyright, a driver release, a product-name resemblance and a declaration's issue date are not launch evidence.

## Historical selector corrections

The original [Lenovo selector](https://download.lenovo.com/eol/resources/ddfm.js) is an observed support index, not an error-free product taxonomy. These explicit label-and-route corrections are applied only by the offline reconciliation command. The raw selector parser remains strict and unchanged; any other identity drift still fails reconciliation. Stable model IDs and their existing support-route associations remain unchanged, except the excluded desktop record.

| Raw selector label | Route | Catalogue treatment |
| --- | --- | --- |
| ThinkPad 750, 750CSE, 750CS, 755C, 755CS | 750.html | Display only documented 750/750CS/755C/755CS. Preserve 750CSE as an explicitly unverified selector member, not a confirmed product alias. |
| ThinkPad A21e (Type 2632) | A21e-2632.html | Display i Series 1800 (Type 2632). Preserve A21e as a historical support alias, not a separately launched model. |
| ThinkPad A22m (Type 2629, 2633) | A22m-2629.html | Display A22m (Type 2633), still undated. Type 2629 is A22p, already represented by a22p; do not duplicate it or merge the two support listings. |
| ThinkPad 1400, 1500 (Type 2621, 2651) | 1500-2621.html | Display 1400 (Type 2621) and 1500 (Types 2621, 2651). Do not promote the unsupported 1400/2651 Cartesian combination into a confirmed product. |
| ThinkPad S51 | S51.html | Exclude: the linked matrix and BIOS documentation describe a ThinkCentre desktop, not a ThinkPad. |

IBM's [A-series HMM](https://download.lenovo.com/pccbbs/bp_thinkpad/23p0896.pdf) identifies A22m types 2628/2633 and A22p type 2629. The latter has an explicit 2001 availability row in [PSREF page 14](https://psref.lenovo.com/syspool/Sys/PDF/withdrawnbook/tawbook.pdf#page=14). The distinct selector-bound driver lists are retained as provenance, not certified exact-model compatibility.

The [2632 HMM](https://download.lenovo.com/pccbbs/bp_thinkpad/06p8883.pdf) identifies its i-series branding. A [contemporary IBM announcement report](https://pc.watch.impress.co.jp/docs/article/20001025/ibm.htm) explicitly identifies 1800 SKU 2632-I1J and i Series 1124 SKU 2609-73J in October 2000. A generic 1800 entry dated 2001 would duplicate the type-qualified record and misstate the first documented year, so it is not added.

The official [S51 support matrix](https://download.lenovo.com/lenovo/content/ddfm/S51.html) identifies ThinkCentre. The removed record had no indexed document or driver associations.

## Regional names and dates

The 2010 dates for Edge E30, E40 and E50 rely on explicit manufacturer name crosswalks and overlapping machine types, not an assumption that similar names are equivalent:

| Regional model | Manufacturer identity bridge | Dated PSREF page |
| --- | --- | --- |
| Edge E30 | [Edge 13/E30; MT 0196/0197/0492](https://p4-ofp.static.pub/ShareResource/compliance/eco-declaration/pdfs/Batch5/ThinkPad-Edge-13.pdf) | [Page 9](https://psref.lenovo.com/syspool/Sys/PDF/withdrawnbook/lslwbook.pdf#page=9) |
| Edge E40 | [Edge 14/E40; MT 0578/0579](https://p4-ofp.static.pub/ShareResource/compliance/eco-declaration/pdfs/Batch5/ThinkPad-Edge-14-E40-TED.pdf) | [Page 13](https://psref.lenovo.com/syspool/Sys/PDF/withdrawnbook/lslwbook.pdf#page=13) |
| Edge E50 | [Edge 15/E50; MT 0301/0319](https://p4-ofp.static.pub/ShareResource/compliance/eco-declaration/pdfs/Batch5/ThinkPad-Edge-15-E50-TED.pdf) | [Page 29](https://psref.lenovo.com/syspool/Sys/PDF/withdrawnbook/lslwbook.pdf#page=29) |

The declarations establish names and machine types only; their publication dates are not used as launch dates. [Contemporary reporting](https://notebook.yesky.com/242/11572742.shtml) explicitly dates Edge E10's launch to September 28, 2010. No year is transferred to Edge E31 from Edge 13: its shared HMM names it, but does not establish the same introduction date.

## Remaining exact-variant gaps

Unresolved launch dates and qualified documentary years are kept distinct rather than borrowing a generic family year:

- A22m type 2633 remains wholly undated.
- Edge E31, X200si and X230i Tablet now have qualified exact-SKU regional dates, while their earliest worldwide launches remain unconfirmed.
- R52 special-bid types 1850, 1870, 1862 and 1863 now have a March 2005 exact-type commercial brochure citation, explicitly not a proved first sale. The ordinary types retain their independent dated PSREF rows. See the [0.3.2 backfill and its source limits](year-backfill-0.3.2.md).
- The selector string 750CSE is attested, but a distinct launch was not established. It remains explicitly unverified; it is not silently replaced with 750C, 750CE or 755CSE.
- 1400 type 2651 is an unverified member implied by a compound selector, not a confirmed product. The documented 1400/2621 and 1500/2621 dates are 1999; 1500/2651 is 2000.

## Coverage method and limits

The 0.3.1 research compares every dated token in ThinkWiki History revision 62053: 436 occurrences, 429 unique tokens. It reconciles source-grouped i-series names instead of duplicating them, excludes unbranded PC110/Power Series 800/RS/6000 860, and does not accept six ambiguous history names without additional identity evidence: 315E, 315ED, 385E, 380X, T540 and E570p.

The manufacturer comparison combines the current and withdrawn PSREF laptop, tablet and mobile-workstation branches, deduplicated by exact product key: all 377 captured keys are represented (116 in the first expansion/baseline and 261 in the completion pass). Every completion entry has explicitly labelled SKU announcement evidence and a verified official product-key-to-PDF binding. Dates with only month/year precision are not promoted to invented days. E545/Edge E545 and Helix's parenthesized second-generation name are explicitly supported aliases; the first-generation X1 Yoga remains generation-qualified even though its PDF cover omits the suffix. Neither that index nor the catalogue is claimed to contain every regional ThinkPad ever made. Modern processor/generation variants remain distinct. New records receive only verified reference links; no driver associations are inferred from their family or shared chassis.

ThinkWiki categories may be stubs and community dates may disagree with manufacturer evidence. P50/P70 use the manufacturer's 2015 announcement rather than the community history's 2016 row. Tablet 2 uses its 2012 announcement rather than the community history's 2013 row. Specifications references, HMMs, user guides and announcement links remain external documents and are not represented as interchangeable manual types. No manufacturer source bodies, PDFs or installers are redistributed.
