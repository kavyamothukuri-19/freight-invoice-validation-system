"""Independent rule-based audit; does not read ground_truth during prediction."""
import argparse,csv,json,sqlite3
from collections import Counter
from pathlib import Path

def validate(output='output'):
    root=Path(output); con=sqlite3.connect(root/'freight.db');con.row_factory=sqlite3.Row
    c=con.cursor(); predicted=[]; details=[]; seen=set()
    for inv in c.execute('SELECT * FROM FreightInvoice ORDER BY invoice_id').fetchall():
        iid=inv['invoice_id'];sid=inv['shipment_id'];issues=[]
        shipment=con.execute('SELECT * FROM Shipment WHERE shipment_id=?',(sid,)).fetchone()
        lines=con.execute('SELECT * FROM InvoiceLine WHERE invoice_id=? ORDER BY line_no',(iid,)).fetchall()
        line_total=round(sum(x['amount'] for x in lines),2)
        if abs(line_total-inv['billed_total'])>.01:issues.append('LINE_TOTAL_MISMATCH')
        if not shipment:
            issues.append('UNKNOWN_SHIPMENT');expected=0.0
        else:
            w=con.execute('SELECT * FROM WeightMeasurement WHERE shipment_id=?',(sid,)).fetchone()
            rate=con.execute('''SELECT * FROM RateCard WHERE carrier_id=? AND lane_id=? AND service=? AND tier_min<? AND tier_max>=? ORDER BY valid_from DESC LIMIT 1''',(shipment['carrier_id'],shipment['lane_id'],shipment['service'],w['billable_kg'],w['billable_kg'])).fetchone()
            if not rate:issues.append('MISSING_RATE');expected=0.0
            else:
                expected=round(rate['base_charge']*1.05+200,2)
                if not(rate['valid_from']<=shipment['ship_date']<=rate['valid_to']):issues.append('EXPIRED_RATE')
                base_lines=[x for x in lines if x['charge_code']=='BASE']
                if len(base_lines)!=1:issues.append('INVALID_BASE_LINES')
                elif abs(base_lines[0]['amount']-rate['base_charge'])>.01:issues.append('WRONG_WEIGHT_TIER' if abs(base_lines[0]['amount']-rate['base_charge']-1200)<.01 else 'OVERCHARGE')
                fuel_lines=[x for x in lines if x['charge_code']=='FUEL']
                if len(fuel_lines)>1:issues.append('DUPLICATE_SURCHARGE')
                elif len(fuel_lines)!=1 or abs(fuel_lines[0]['amount']-round(rate['base_charge']*.05,2))>.01:issues.append('INCORRECT_FUEL')
                hand_lines=[x for x in lines if x['charge_code']=='HANDLING']
                if len(hand_lines)!=1 or abs(hand_lines[0]['amount']-200)>.01:issues.append('INCORRECT_HANDLING')
            # A shipment is expected to have at most one non-adjustment invoice in this sample.
            if sid in seen:issues.append('DUPLICATE_BILL')
            seen.add(sid)
        credit=con.execute('SELECT * FROM CreditNote WHERE invoice_id=?',(iid,)).fetchone()
        if credit and credit['amount']>credit['approved_amount']:issues.append('EXCESSIVE_CREDIT_NOTE')
        issues=list(dict.fromkeys(issues))
        predicted.append((iid,'FLAG' if issues else 'PASS',';'.join(issues) if issues else 'NONE',expected,inv['billed_total'],round(inv['billed_total']-expected,2)))
        if issues:details.append({'invoice_id':iid,'issues':issues,'expected':expected,'billed':inv['billed_total']})
    with (root/'audit_results.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.writer(f);w.writerow(['invoice_id','decision','detected_issues','expected_amount','billed_amount','difference']);w.writerows(predicted)
    with (root/'ground_truth.csv').open(encoding='utf-8') as truth_file:
        truth={r['invoice_id']:r for r in csv.DictReader(truth_file)}
    tp=fp=tn=fn=0;wrong_labels=[]
    for iid,decision,issues,*_ in predicted:
        actual=truth[iid]['expected_decision']
        if decision=='FLAG' and actual=='FLAG':tp+=1
        elif decision=='FLAG':fp+=1
        elif actual=='FLAG':fn+=1
        else:tn+=1
        true_issue=truth[iid]['issue_type']
        if true_issue!='NONE' and true_issue not in issues.split(';'):wrong_labels.append({'invoice_id':iid,'expected_issue':true_issue,'detected':issues})
    checks={}
    for table in ('Carrier','Lane','RateCard','Shipment','ShipmentLeg','WeightMeasurement','Accessorial','FreightInvoice','InvoiceLine','AuditException','CreditNote'):
        checks[table]=con.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]
    summary={'counts':checks,'true_positives':tp,'false_positives':fp,'true_negatives':tn,'false_negatives':fn,'precision':round(tp/(tp+fp),4) if tp+fp else 0,'recall':round(tp/(tp+fn),4) if tp+fn else 0,'missing_expected_issue_labels':wrong_labels[:30],'predicted_issues':dict(Counter(issue for d in details for issue in d['issues'])),'intentional_invalid_shipment_refs':con.execute('SELECT COUNT(*) FROM FreightInvoice f LEFT JOIN Shipment s ON s.shipment_id=f.shipment_id WHERE s.shipment_id IS NULL').fetchone()[0],'line_total_mismatches':con.execute('SELECT COUNT(*) FROM FreightInvoice f WHERE ABS(f.billed_total-(SELECT SUM(amount) FROM InvoiceLine l WHERE l.invoice_id=f.invoice_id))>0.01').fetchone()[0]}
    (root/'validation_summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    con.close()
    print('Audit completed:',len(predicted),'invoices | precision:',summary['precision'],'recall:',summary['recall'])
    print('Results:',root/'audit_results.csv','and',root/'validation_summary.json')
    return summary
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',default='output');a=p.parse_args();validate(a.output)
