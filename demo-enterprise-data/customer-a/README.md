# Customer A enterprise demo data

This directory is the file-backed source package for Demo 1. The files are
project-generated simulation data, not Lenovo data, production CRM records, or
real customer information.

The folder structure and field semantics are informed by public enterprise
sample systems, especially Microsoft AdventureWorks and the Power BI sample
datasets. No Microsoft workbook rows are copied into this package.

`manifest.json` is the allowlist and integrity index. The API reads only files
listed there, verifies their SHA-256 digests, parses them with structured
readers, and freezes the resulting source snapshot into each new Demo 1 task.

Scenario:

- the finance/CRM close export records recognized revenue of CNY 24.00 million;
- the sales forecast export records forecast revenue of CNY 26.80 million;
- the current report draft must not write the forecast field as recognized
  revenue;
- the weekly status and customer request provide the risk and response context.
