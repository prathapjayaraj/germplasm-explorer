# Germplasam Descriptor Explorer

Generate a searchable, offline germplasm Descriptor explorer from an Excel workbook. No setup is required.

## Quick start

1. Clone or download this repository.
2. Open `germplasm-Descriptor.xlsx` and enter your crop's data. **The included workbook is an example using banana germplasm descriptors.**
3. Save the Excel file.
4. Double-click `index.html` to open the generator in your browser.
5. Select the updated Excel workbook.
6. Review the data and DUS mapping preview, then click **Generate standalone HTML**.
7. Open the downloaded HTML file to search, filter, and compare germplasm accessions offline.

## Excel sheets

- **Master Data** — descriptors and their coded states; repeated or grouped CID rows are supported.
- **Germplasm Data** — accession details and coded trait observations.
- **DUS Equivalent** — optional DUS-to-germplasm descriptor/state mappings.
- **Configurations** — explorer settings.

Keep the sheet names and required column headers unchanged. The generated HTML is self-contained and can be shared without the Excel workbook.

> **Note:** `germplasm-Descriptor.xlsx` contains banana example data. Replace it with your own crop data before generating an explorer for another crop. The current schema expects the existing workbook structure.
