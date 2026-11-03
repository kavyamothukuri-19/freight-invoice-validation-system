# Schema and data dictionary

All IDs are text and immutable. Monetary values are synthetic INR. Date fields use ISO `YYYY-MM-DD`. Amounts are rounded to 2 decimal places. SQLite `REAL` is used for this educational demonstration; production systems should use integer minor units or fixed-precision decimals.

| Entity | Primary key | Required business fields | Relationship / constraints |
|---|---|---|---|
| Carrier | carrier_id | name TEXT, active INTEGER | 1:N RateCard, Shipment, FreightInvoice; active 0/1 |
| Lane | lane_id | origin TEXT, destination TEXT, distance_km INTEGER | 1:N RateCard and Shipment; positive distance |
| RateCard | rate_id | carrier_id FK, lane_id FK, service ENUM, tier_min/max REAL kg, base_charge REAL INR, valid_from/to DATE | carrier+lane+service+tier; STANDARD/EXPRESS; valid_from <= valid_to |
| Shipment | shipment_id | carrier_id FK, lane_id FK, service, ship_date, delivery_date, length/width/height cm, actual_weight_kg, status | 1:N ShipmentLeg, WeightMeasurement, FreightInvoice; positive dimensions, delivery >= ship |
| ShipmentLeg | leg_id | shipment_id FK, sequence_no, origin, destination, delivered_at | 1:N from Shipment; unique(shipment_id,sequence_no) |
| WeightMeasurement | measurement_id | shipment_id FK, actual_kg, dimensional_kg, billable_kg, measured_at | 1:N from Shipment; billable=max(actual,dimensional) |
| Accessorial | accessorial_id | code UNIQUE, description, rate, calculation | catalog; invoice lines use charge_code (FUEL/HANDLING) |
| FreightInvoice | invoice_id | shipment_id reference, carrier_id FK, invoice_date, billed_total, status | 1:N InvoiceLine/AuditException; shipment reference may be intentionally invalid for a negative test |
| InvoiceLine | line_id | invoice_id FK, line_no, charge_code, amount | unique(invoice_id,line_no); BASE/FUEL/HANDLING |
| AuditException | exception_id | invoice_id FK, issue_type, expected_amount, billed_amount, difference, status, created_at | 1:N from invoice; difference=billed-expected |
| CreditNote | credit_id | exception_id FK, invoice_id FK, amount, approved_amount, status, created_at | 1:N from exception; excessive amount rejected |

`EventHistory` is an additional append-only audit event table with event_id, entity_type, entity_id, event_type, event_date, detail. No many-to-many relationship is needed for this simplified model, so no bridge table is created. Relationships and fields can be extended for multi-carrier/multi-leg scenarios.

## Required negative scenarios

1. `UNKNOWN_SHIPMENT`: invoice points to an absent shipment ID.
2. `EXPIRED_RATE`: shipment date is beyond the applicable rate card's effective date.
3. `WRONG_WEIGHT_TIER`: base charge is artificially inflated by 1,200 relative to the rate for billable weight.
4. `DUPLICATE_SURCHARGE`: duplicate FUEL invoice line.
5. `EXCESSIVE_CREDIT_NOTE`: credit amount 1,500 exceeds approved dispute amount 1,000.

Also included: `OVERCHARGE` and `DUPLICATE_BILL`.
