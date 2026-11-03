# Freight Invoice Validation & Audit System

A runnable **Python standard-library + SQLite** project based on the supplied four-page freight invoice validation assignment. All data is synthetic. It includes the 11 requested entities, a separate append-only event history, deterministic IDs, CSV exports, an independent rule-based invoice audit, a ground-truth file, exception/credit records, a validation summary, and a local HTML dashboard.

## Prerequisites

- Python 3.10+ (no `pip install` required)
- VS Code (optional)

## Run in VS Code (Windows)

1. Extract the ZIP file.
2. In VS Code select **File > Open Folder** and choose `freight_invoice_project`.
3. Open **Terminal > New Terminal**.
4. Check Python: `py --version` (or `python --version`).
5. Run the quick starter dataset: `py run.py --scale starter` (or `python run.py --scale starter`).
6. Open `output/dashboard.html` in your browser (double-click in File Explorer).
7. For the full assignment dataset run: `py run.py --scale full`. This replaces files in `output`.
8. Run automated tests: `py -m unittest discover -s tests -v`.

On macOS/Linux use `python3` instead of `py`.

## What is generated?

- `output/freight.db`: SQLite database
- `output/Carrier.csv`, `Lane.csv`, `RateCard.csv`, `Shipment.csv`, `ShipmentLeg.csv`, `WeightMeasurement.csv`, `Accessorial.csv`, `FreightInvoice.csv`, `InvoiceLine.csv`, `AuditException.csv`, `CreditNote.csv`: all 11 entities
- `output/EventHistory.csv`: append-only events
- `output/ground_truth.csv`: separate known answers, **not** used by the audit engine
- `output/audit_results.csv`: independently detected issues
- `output/validation_summary.json`: counts, precision, recall, integrity checks
- `output/manifest.json`: seed, data provenance and CSV checksums
- `output/dashboard.html`: interactive, standalone dashboard viewable without a server

## Dashboard features

- Shows **all PASS and FLAG invoices** in one invoice register.
- Click a PASS or FLAG invoice to inspect its invoice, carrier, shipment, route, weight, charge lines, audit exceptions, credit notes and event history.
- KPI cards for total, passed and flagged invoices, potential positive flagged variance, and precision/recall.
- Flagged-issue breakdown, free-text search, PASS/FLAG filter, invoice-date range, sortable columns and pagination.
- Export the currently filtered invoice register to CSV and print an individual invoice detail view.

After running `python run.py --scale full`, open `output/dashboard.html` in your browser to use the updated dashboard.

Starter: 5 carriers, 100 shipments, 80 invoices. Full: **100 carriers, 20,000 shipments, 15,000 invoices**.

## Sample business rules

- Rate cards are specific to carrier, lane, service and billable weight tier, with effective dates.
- Dimensional weight = `length_cm * width_cm * height_cm / 5000`.
- Billable weight = `max(actual_weight_kg, dimensional_weight_kg)`.
- Expected invoice = `base_rate + 5% fuel surcharge + 200 handling`.
- Validator detects unknown shipment, expired rate, wrong weight tier, duplicate fuel surcharge, excessive credit note, overcharge, and duplicate bill.
- Invoice totals are always derived from their line items. Audit exceptions retain their expected and billed amounts.
- Ground truth labels come from explicit injected scenario rules, not arbitrary independent random labels.

## Deliberate invalid reference

`FreightInvoice.shipment_id` is intentionally not enforced as a physical SQLite foreign key so the **unknown shipment** negative test can exist. All other relationships are enforced, and the validator counts this intentional integrity violation. Do not treat that as an accidental broken relationship.

## Limitations and extension ideas

This is a runnable educational reference implementation, not a production payment system. It is CLI-based with a read-only HTML report (no user login or interactive approval UI). Credits are modeled as rejected when they exceed the approved dispute; no payment integration is included. Shipment-to-invoice uses a simple one-to-many model, and all generated shipments have one leg. Real systems should also handle multi-leg shipments, split invoices, rate amendments, currency/tax, approval authorization and stronger event-sourcing controls.

The `RateCard` identifier includes carrier, year, lane, service and tier to maintain uniqueness; this extends the illustrative identifier pattern in the assignment. The full assignment also requests comprehensive data dictionary/relationship documentation, provided separately as `DATA_DICTIONARY.md`.
