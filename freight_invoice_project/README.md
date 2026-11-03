# Freight Invoice Validation & Audit System – Synthetic Data Project

## 1. Objective

Generate a reproducible synthetic freight logistics dataset and validate carrier invoices against contracted rates, shipment characteristics, additional charges (accessorials), and shipment records.

The solution creates shipments and invoices, calculates expected freight charges, flags incorrect or suspicious bills, records audit exceptions and credit notes, and evaluates audit decisions against separately stored ground-truth labels.

## 2. Environment and Dependencies

- Python 3.10+
- Python standard library (`argparse`, `csv`, `json`, `sqlite3`, etc.)
- SQLite database
- CSV and JSON reports
- VS Code (recommended, optional)
- **No external Python packages required**

> This is a command-line Python project with a standalone HTML dashboard. It is **not a Django application**: there is no `manage.py` or `runserver` command.

## 3. Project Setup

Download and extract the project ZIP, then open the **inner** `freight_invoice_project` folder in VS Code. In **Terminal → New Terminal**, verify Python:

```powershell
python --version
```

If you are in the outer extracted folder, move into the inner folder:

```powershell
cd .\freight_invoice_project
```

Confirm that `run.py`, `generator.py`, `validator.py`, and `report.py` are present:

```powershell
dir
```

## 4. Run the Complete Dataset

Run the full assignment dataset:

```powershell
python run.py --scale full
```

| Parameter | Full dataset |
| --- | ---: |
| Carriers | 100 |
| Shipments | 20,000 |
| Freight invoices | 15,000 |
| Default random seed | 20261022 |

The generator also creates the other required entities, invoice lines, event history, and audit outputs. **Running the full dataset replaces generated files in `output/`.**

## 5. Generate a Starter Dataset

For a quick test, run:

```powershell
python run.py --scale starter
```

| Parameter | Starter dataset |
| --- | ---: |
| Carriers | 5 |
| Shipments | 100 |
| Freight invoices | 80 |

Supported command-line arguments:

```powershell
python run.py --help
python run.py --scale full --seed 20261022 --output output
```

- `--scale`: `starter` or `full` (default: `starter`)
- `--seed`: random seed (default: `20261022`)
- `--output`: output folder (default: `output`)

## 6. Required ID Conventions

| Entity | Example identifier |
| --- | --- |
| Carrier | `CAR-000001` |
| RateCard | `RATE-CAR-000001-2026-LANE-0001-STANDARD-1` |
| Lane | `LANE-0001` |
| Shipment | `SHP-2026-000001` |
| FreightInvoice | `FINV-2026-000001` |
| InvoiceLine | `FLINE-FINV-2026-000001-01` |
| AuditException | `FEX-2026-000001` |

IDs are generated deterministically and reused across related records. The rate-card ID includes lane, service, and tier to keep records unique.

## 7. Data Model and Relationships

The eleven required core entities are:

1. Carrier
2. RateCard
3. Lane
4. Shipment
5. ShipmentLeg
6. WeightMeasurement
7. Accessorial
8. FreightInvoice
9. InvoiceLine
10. AuditException
11. CreditNote

An additional `EventHistory` table records lifecycle events. Key relationships include carrier-to-rate-card, carrier-to-shipment, shipment-to-shipment-leg, shipment-to-weight-measurement, shipment-to-invoice, invoice-to-invoice-line, and invoice-to-audit-exception. See `DATA_DICTIONARY.md` for the documented schema.

**Intentional exception:** An invoice can deliberately reference a nonexistent shipment for the required unknown-shipment negative test. That specific invoice reference is validated by the audit logic rather than enforced as a SQLite foreign key.

## 8. Data Generation and Processing Workflow

1. Create carriers, lanes, and contracted rate cards.
2. Generate shipments with service types, routes, dimensions, and actual weights.
3. Generate shipment legs and weight measurements.
4. Calculate dimensional and billable weight.
5. Select the applicable carrier/lane/service/weight-tier rate.
6. Generate invoice base-freight and accessorial lines.
7. Inject controlled invoice anomalies.
8. Generate separate ground-truth labels.
9. Run the independent rule-based invoice validator.
10. Record audit exceptions and credit-note decisions.
11. Export CSV files, SQLite data, metrics, and an HTML dashboard.

## 9. Controlled Anomalies and Ground Truth

| Scenario | Expected audit decision | Description |
| --- | --- | --- |
| Valid invoice | `PASS` | Charges and references satisfy the implemented rules |
| `UNKNOWN_SHIPMENT` | `FLAG` | Invoice references a nonexistent shipment |
| `EXPIRED_RATE` | `FLAG` | Rate card is invalid for the shipment date |
| `WRONG_WEIGHT_TIER` | `FLAG` | Incorrect weight-based rate is applied |
| `DUPLICATE_SURCHARGE` | `FLAG` | Fuel surcharge is charged more than once |
| `EXCESSIVE_CREDIT_NOTE` | `FLAG` | Credit exceeds approved dispute amount |
| `DUPLICATE_BILL` | `FLAG` | Duplicate freight bill detected |
| `OVERCHARGE` | `FLAG` | Billed freight exceeds the expected charge |

Ground-truth labels are saved in `output/ground_truth.csv`. The validator makes its decisions from invoice and shipment data, not from the ground-truth answer file.

## 10. Freight Charge Calculation

The demonstration uses the following rules:

```text
Dimensional weight (kg) = length_cm × width_cm × height_cm / 5000
Billable weight (kg) = max(actual weight, dimensional weight)
Expected fuel surcharge = base freight × 5%
Expected handling charge = 200
Expected invoice = base freight + fuel surcharge + handling charge
Difference = billed invoice − expected invoice
```

Example:

| Charge | Expected | Billed |
| --- | ---: | ---: |
| Base freight | 10,000 | 11,000 |
| Fuel surcharge | 500 | 500 |
| Handling | 200 | 200 |
| **Total** | **10,700** | **11,700** |

The invoice is flagged for a **1,000 overcharge**. Amounts and rates in this project are synthetic demonstration values.

## 11. Validation

The project checks invoice references, applicable rates, weight tiers, duplicate charges, duplicate invoices, credit-note limits, and arithmetic reconciliation. It reports precision and recall against known labels.

### Included Full-Dataset Validation Results

| Metric | Result |
| --- | ---: |
| Carriers | 100 |
| Shipments | 20,000 |
| Freight invoices | 15,000 |
| Invoice lines | 45,105 |
| Audit exceptions | 325 |
| Passed invoices | 14,675 |
| Flagged invoices | 325 |
| True positives | 325 |
| False positives | 0 |
| False negatives | 0 |
| Precision | 100% |
| Recall | 100% |
| Invoice line-total mismatches | 0 |
| Intentional invalid shipment references | 1 |

These are results from the supplied generated **synthetic** full dataset, not a claim of production accuracy.

Run automated tests:

```powershell
python -m unittest discover -s tests -v
```

## 12. Freight Audit Dashboard

Generate the data and dashboard:

```powershell
python run.py --scale starter
```

Open the dashboard in the default Windows browser:

```powershell
start output\dashboard.html
```

The dashboard shows invoice count, flagged count, precision, recall, and the first 250 detected exceptions. The complete invoice register is available in `output/audit_results.csv`.

**No web server is required.** Do not run `python manage.py runserver` or expect a `localhost:8000` portal; this implementation produces a static HTML file.

## 13. Reproducibility

The default seed is `20261022`. Re-run with the same scale, seed, and generator version:

```powershell
python run.py --scale full --seed 20261022
```

The generated `output/manifest.json` records the seed, provenance, and CSV checksums, supporting repeatability checks. To demonstrate reproducibility, compare manifests/checksums from two separately saved runs.

## 14. Exports

Generated files are stored under `output/`:

```text
output/
├── Carrier.csv
├── RateCard.csv
├── Lane.csv
├── Shipment.csv
├── ShipmentLeg.csv
├── WeightMeasurement.csv
├── Accessorial.csv
├── FreightInvoice.csv
├── InvoiceLine.csv
├── AuditException.csv
├── CreditNote.csv
├── EventHistory.csv
├── ground_truth.csv
├── audit_results.csv
├── validation_summary.json
├── manifest.json
├── freight.db
└── dashboard.html
```

The core entity data is exported as CSV and stored in a populated SQLite database. The summary and manifest are JSON; the dashboard is HTML.

## 15. Data Provenance

All carriers, shipments, contracts, and invoices are **synthetic**. The project does not require real carrier invoices or confidential customer information. The manifest documents generation parameters and checksums.

## 16. Assumptions and Limitations

- This is an educational rule-based audit simulation, not a production freight-payment platform.
- The dashboard is read-only HTML; it does not provide login, approvals, or editable invoice screens.
- Shipment-to-invoice modeling is simplified, and generated shipments use one leg.
- The synthetic fuel and handling rules are illustrative rather than universal freight tariffs.
- Credit notes are modeled as records; there is no payment or bank integration.
- No machine-learning model or external carrier API is included.
- The known-anomaly evaluation measures behavior on generated scenarios, not real-world generalization.

## 17. Repository and Project Structure

```text
freight_invoice_project/
├── run.py
├── generator.py
├── validator.py
├── report.py
├── tests/
│   └── test_project.py
├── output/
│   ├── dashboard.html
│   ├── audit_results.csv
│   ├── validation_summary.json
│   ├── ground_truth.csv
│   ├── freight.db
│   └── ... other generated datasets
├── DATA_DICTIONARY.md
└── README.md
```

**Primary execution:** `python run.py --scale starter`  
**Full execution:** `python run.py --scale full`  
**Dashboard:** `output/dashboard.html`

## 18. PowerShell Commands and Execution Output

These steps correspond to the VS Code terminal screenshot from the project run.

### 18.1 Locate the Project Files

From the outer extracted directory:

```powershell
Get-ChildItem -Path . -Filter run.py -Recurse
cd .\freight_invoice_project
dir
```

The inner directory contains `run.py`, `generator.py`, `validator.py`, `report.py`, `tests`, `output`, `README.md`, and `DATA_DICTIONARY.md`.

### 18.2 Generate the Starter Dataset

Run:

```powershell
python run.py --scale starter
```

**Observed terminal output (from the supplied screenshot):**

```text
Starter
Generated 5 carriers, 100 shipments, 80 invoices in output
Audit completed: 80 invoices | precision 1.0, recall 1.0
Results: output\audit_results.csv and output\validation_summary.json
Open output\dashboard.html in a browser
```

This confirms that the generator, validator, and HTML report completed for the starter dataset.

### 18.3 Open the Dashboard

Run:

```powershell
start output\dashboard.html
```

This opens the generated report in a browser. There is no server process to keep running.

### 18.4 Generate the Full Dataset

Run:

```powershell
python run.py --scale full
```

The included full-dataset summary reports 100 carriers, 20,000 shipments, 15,000 invoices, and 325 flagged invoices. Open `output/dashboard.html` again to view the refreshed report.

### 18.5 Run Tests

```powershell
python -m unittest discover -s tests -v
```

### 18.6 Common Errors

- **`No such file or directory: run.py`**: you are in the wrong directory; use `dir` and navigate to the inner `freight_invoice_project` folder.
- **`No such file or directory: manage.py`**: this is not a Django project; run `python run.py --scale starter` instead.
- **`python` is not recognized**: check your Python installation or try `py` instead of `python`.

---

**Project:** Freight Invoice Validation & Audit System – Synthetic Data Project  
**Language:** Python  
**Database:** SQLite  
**Outputs:** CSV, JSON, SQLite, HTML

