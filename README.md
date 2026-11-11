# Germplasm Descriptor — Offline Generator

**Edit one Excel file. Open one HTML file. Generate your own offline explorer.** No installation, terminal, Python, Node.js, Docker, account, database, or internet is needed for end users.

## Quick start (3 steps)

1. **Clone or download this repository.** Open **`germplasm.xlsx`** in Excel, edit your germplasm details, and **save** it. The supplied workbook is a working banana example.
2. **Double-click `index.html`**. In the browser, select **`germplasm.xlsx`** using **Choose workbook** (or drag and drop). Check the validation summary; use **View mappings** to inspect all configured DUS-to-germplasm state relationships **before** generating.
3. Click **Generate standalone HTML**. Your browser downloads **`germplasm_explorer.html`** to its downloads location. Open it directly to search or share the germplasm catalogue offline.

**No other folders need to be opened.** The `app/` folder contains internal JavaScript, the HTML template, licenses, and optional developer tests; leave it as-is.

> Browsers cannot automatically read the edited local Excel workbook without user permission. You will need to select the file after every edit and regeneration. The generated explorer is downloaded by the browser rather than silently saved back into the project folder.

## Minimal project layout

```text
crop-germplasm-explorer/
├── index.html         ← OPEN THIS to generate
├── germplasm.xlsx     ← EDIT THIS to configure your crop
├── README.md          ← instructions
└── app/               ← internal files; normally ignore this folder
    ├── assets/        JavaScript parser, generator, template bundle, license
    ├── source/        editable explorer UI source
    └── tests/         optional developer tests
```

**Important:** Keep `index.html` and `app/` in the same directory. Do not move or rename files inside `app/` unless you also update the relative paths.

## Excel format (four sheets)

| Sheet | Required columns | Purpose |
| --- | --- | --- |
| **Master Data** | `CID`, `IPGRI`, `Descriptor`, `Description`, `Code`, `State` | One row **per descriptor state**; the CID can be repeated or left blank on subsequent state rows |
| **Germplasm Data** | `ID`, `Accession`, `Name`, `Genome`, `Subgroup`, plus each descriptor's CID | One row per accession; observation cells contain Master Data **state codes** |
| **DUS Equivalent** | `DUS ID`, `DUS Descriptor`, `DUS Code`, `DUS Value`, `Germplasm Descriptor`, `Germplasm Value` | DUS-to-germplasm descriptor and state mappings; multiple target states may use repeated DUS rows |
| **Configurations** | `Setting`, `Value`, `Description` | Explorer title, subtitle, output settings and defaults |

### Example Master Data — grouped or repeated CID

**Recommended layout:** Enter the CID, IPGRI, Descriptor and Description on the **first state row**. Leave these fields blank on subsequent state rows for the same descriptor. Each state always has its own `Code` and `State`.

| CID | IPGRI | Descriptor | Description | Code | State |
| --- | --- | --- | --- | --- | --- |
| cid101 | 6.1.1 | Leaf habit | Leaf orientation | 1 | Erect |
| | | | | 2 | Intermediate |
| | | | | 3 | Drooping |
| cid102 | 6.1.2 | Dwarfism | | 1 | Normal |
| | | | | 2 | Dwarf type |

**Also accepted:** Repeat `cid101`, `6.1.1`, and `Leaf habit` on every state row. Both workbook styles produce the same descriptor definitions and generated explorer.

**Rules:**
- An empty CID inherits the **most recently defined CID**. A new nonempty CID begins or resumes that descriptor. Do **not** merge cells: leave continuation cells truly empty.
- The **first nonempty Master Data row** must specify a CID; otherwise generation stops with an orphan-row error.
- Nonempty IPGRI, Descriptor and Description cells on continuation rows must agree with the value already defined for that CID. Conflicts cause a validation error.
- Each descriptor needs a name. `(CID, Code)` must be unique, even when a CID is left blank on continuation rows.
- Every state must have a `Code`; an empty `State` uses the code as its display label (prefer entering a meaningful label).
- Do not put a new descriptor name under a blank CID: supply a new CID to start that descriptor.

### Example DUS Equivalent

| DUS ID | DUS Descriptor | DUS Code | DUS Value | Germplasm Descriptor | Germplasm Value |
| --- | --- | --- | --- | --- | --- |
| 5 | Leaf orientation | 1 | Upright | Leaf habit | Erect |
| 5 | Leaf orientation | 2 | Spreading | Leaf habit | Intermediate |

The inspector shows these configured correspondences, including unmapped states, **without applying search filters**. Maps are not automatically biological certifications; confirm equivalences with relevant domain guidance before interpreting DUS matches.

## Features

- **Browser-only generator:** parses `.xlsx` locally, validates required sheets/codes, shows warnings and a searchable mapping inspector, then downloads a self-contained HTML file.
- **Standalone explorer:** accession search, readable characteristic tiles, morphological key–value filter, DUS state filters and mapping preview, and nearest recorded-phenotype matches after selecting an accession.
- **Portable:** HTML output embeds the entire dataset and operates without network access or a Python installation.

## Validation and caveats

The banana example was tested with **589 accessions, 132 descriptors, 602 states and 41 DUS characteristics**. A malformed workbook or duplicate descriptor-state code blocks generation; undefined observed codes are export-blocking validation issues unless the curator explicitly opts to exclude them; unresolved DUS mappings are warnings. The viewer does not infer genome groups. Nearest-accession scores are simple categorical agreement, **not genomic or biological relatedness**.

This release supports coded categorical traits and retains required `Genome` and `Subgroup` columns (values may be empty). A different crop can use this format, but arbitrary continuous traits or radically different metadata schemas are not supported without extending the generator. The HTML embeds all records: **do not share it if the underlying workbook data is confidential**.

## Developer notes (optional)

End users need **no developer tooling**. For source changes:

- UI entry: `index.html`
- Generator logic: `app/assets/generator.js`
- Explorer source template: `app/source/explorer.html`
- Browser-ready embedded template: `app/assets/explorer-template.js` (keep synchronized with HTML source)
- Bundled JSZip and license: `app/assets/jszip.min.js`, `app/assets/JSZIP_LICENSE.md`
- Optional smoke test (requires Python + Playwright + Chromium): `python app/tests/browser_smoke.py`

Everything is local. The browser never uploads the workbook, and the generator does not call external APIs or CDNs.


## Performance and memory considerations

- Workbook processing is local; the generator limits input files to **40 MB** and the uncompressed workbook to **180 MB** to guard against browser-memory exhaustion. Larger institutional datasets may need a command-line/streaming pipeline.
- Worksheet parsing yields to the browser between sheets; the browser may still briefly pause while processing a single very large worksheet because XML DOM parsing is synchronous.
- Choosing another workbook supersedes any previous parse result, so an earlier operation cannot overwrite a later selection.
- Search results and mapping search use brief input debouncing to avoid rebuilding the interface on every keystroke. Repeated accession similarity rankings, sorted accession lists and valid-state counts are cached per explorer page.
- Downloads use an object URL which is revoked after the download is initiated. No network requests, background polling or recurring intervals are used.
- For datasets much larger than the banana example, performance depends on browser memory and computer hardware. Benchmark with your actual workbook and test on target devices before public distribution.

### Run browser performance regression

On a developer machine with Python, Playwright and Chromium installed, run:

```bash
python app/tests/performance_smoke.py
```

This tests repeated searches, mapping inspector navigation, repeated workbook loads, generation and browser heap use (where supported). End users do not need Python or these test packages. The measured results are environment-specific, not guarantees for other machines.

### Verified performance sample (Chromium, 589 banana accession records)

The regression test measured a **603 ms median** workbook load/validation time over four fresh selections. After forced garbage collection, generator heap was **2.89 MB** after four loads. The explorer used **1.21 MB** initially, **2.09 MB** after 16 accession selection/profile interactions and **2.14 MB** after 12 more DUS searches. No uncaught JavaScript errors occurred. These numbers describe this test environment, not a universal memory-leak guarantee. Browser heap does not include all native memory used by XML processing, rendering, or compressed workbook buffers.

## Updated validation and accession lookup

- Master Data: mandatory Code on every state row (blank State labels are reported and display the code as a fallback); unique CID, descriptor name, and state codes; no non-contiguous CID groups; repeated or grouped CID layout supported. IPGRI numbers are optional reference metadata.
- Germplasm Data: required ID, Accession, Name, Genome, Subgroup, and exactly the CID columns from Master Data. Duplicate/unknown headers are blocked. Observation codes must exist in the matching descriptor's permitted state list. Blank observations remain blank.
- Invalid observation values: generation is blocked by default. The interface shows row, accession, descriptor and invalid code and offers a downloadable CSV audit report. An explicit provisional-export checkbox allows invalid values to be removed from the **generated copy only**; the original Excel file is never changed.
- Accession lookup: the selected reference shows just its name and an eye-shaped view control. Full characteristics appear only inside the on-demand details popup. Similarity results remain available separately.

## Interface revision (November 2026)
- Application and example workbook title: **Germplasm Descriptor**. The exported HTML heading, source, subtitle, and footer are read from the `Configurations` sheet; the example workbook title can be changed there.
- The generator interface uses compact CSS-only styling; no new libraries or network dependencies were added.
- The DUS lookup has one **DUS mappings** control above the filters instead of per-card mapping buttons. The mapping viewer reads the uploaded workbook's configured equivalents.
- Accession results use view (eye) icon actions instead of text buttons; the existing detail dialog is unchanged.
- Workbook structure and categorical observation values continue to be validated; undefined codes block export unless the user explicitly opts to exclude them. The example workbook currently has 118 undefined observation codes.

### UI verification
`python app/tests/strict_validation_smoke.py`
`python app/tests/descriptor_ui_smoke.py`

### UI refinement (November 2026)
- Generator opens directly on the workbook editor; the upper header was removed.
- DUS cards no longer show internal `cid...` codes or an explanation before a state is selected.
- When configured, germplasm Optional reference numbers appear in selected-state and mapping details. Missing IPGRI values are omitted rather than replaced with a CID.
- DUS matching result search explicitly supports accession names. Each result displays a compact eye icon on the title row, with no second mapping icon or trait count.

## Mapping statuses

- **Fully mapped:** a configured germplasm descriptor exists and every DUS state has at least one valid mapped state.
- **Partially mapped:** a configured descriptor exists, but only some DUS states have usable mappings.
- **Not mapped:** no usable state mappings exist.

These are **coverage statuses**, not claims that equivalence is biologically exact or approximate. Every valid mapped state is still configured and reviewed in the Excel workbook. Selecting an unmapped DUS state never returns matches. Blank selections do not filter results. Optional external standard references (the `IPGRI` column in the provided sample workbook) are displayed only when configured.
