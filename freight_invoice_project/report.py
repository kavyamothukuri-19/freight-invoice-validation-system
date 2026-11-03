"""Generate a standalone interactive freight invoice audit dashboard."""
import argparse
import csv
import html
import json
import sqlite3
from collections import Counter
from pathlib import Path


def report(output='output'):
    root = Path(output)
    summary = json.loads((root / 'validation_summary.json').read_text(encoding='utf-8'))
    audit_rows = list(csv.DictReader((root / 'audit_results.csv').open(encoding='utf-8')))
    flagged = [r for r in audit_rows if r['decision'] == 'FLAG']
    passed = [r for r in audit_rows if r['decision'] == 'PASS']
    db = sqlite3.connect(root / 'freight.db')
    db.row_factory = sqlite3.Row

    def rows(sql, args=()):
        return [dict(r) for r in db.execute(sql, args).fetchall()]

    invoices = rows('''SELECT i.*, c.name AS carrier_name, s.service, s.ship_date, s.delivery_date,
        s.status AS shipment_status, s.actual_weight_kg, s.length_cm, s.width_cm, s.height_cm,
        s.lane_id, l.origin, l.destination, l.distance_km
        FROM FreightInvoice i LEFT JOIN Carrier c ON c.carrier_id=i.carrier_id
        LEFT JOIN Shipment s ON s.shipment_id=i.shipment_id
        LEFT JOIN Lane l ON l.lane_id=s.lane_id ORDER BY i.invoice_date DESC, i.invoice_id''')
    details = {}
    for inv in invoices:
        iid, sid = inv['invoice_id'], inv['shipment_id']
        details[iid] = {
            'invoice': inv,
            'lines': rows('SELECT line_no,charge_code,amount FROM InvoiceLine WHERE invoice_id=? ORDER BY line_no', (iid,)),
            'exceptions': rows('SELECT issue_type,expected_amount,billed_amount,difference,status,created_at FROM AuditException WHERE invoice_id=?', (iid,)),
            'credits': rows('SELECT credit_id,amount,approved_amount,status,created_at FROM CreditNote WHERE invoice_id=?', (iid,)),
            'legs': rows('SELECT sequence_no,origin,destination,delivered_at FROM ShipmentLeg WHERE shipment_id=? ORDER BY sequence_no', (sid,)) if sid else [],
            'weights': rows('SELECT actual_kg,dimensional_kg,billable_kg,measured_at FROM WeightMeasurement WHERE shipment_id=? ORDER BY measured_at DESC', (sid,)) if sid else [],
            'events': rows('SELECT event_type,event_date,detail FROM EventHistory WHERE entity_id IN (?,?) ORDER BY event_date DESC LIMIT 30', (iid, sid or '')),
        }
    db.close()
    audit_by_id = {r['invoice_id']: r for r in audit_rows}
    for iid, detail in details.items():
        detail['audit'] = audit_by_id.get(iid, {})

    data = json.dumps(details, ensure_ascii=False).replace('</', '<\\/')
    audit_data = json.dumps(audit_rows, ensure_ascii=False).replace('</', '<\\/')
    issue_counts = Counter(issue for r in flagged for issue in (r['detected_issues'] or '').split(';') if issue)
    issue_total = sum(issue_counts.values()) or 1
    issue_bars = ''.join(
        f'<div class="issue-row"><span>{html.escape(k.replace("_", " ").title())}</span>'
        f'<div class="bar-track"><i style="width:{v / max(issue_counts.values(), default=1) * 100:.1f}%"></i></div><b>{v:,}</b></div>'
        for k, v in issue_counts.most_common()
    ) or '<p class="muted">No detected issues.</p>'
    flagged_value = sum(max(float(r.get('difference') or 0), 0) for r in flagged)
    total_billed = sum(float(r.get('billed_amount') or 0) for r in audit_rows)

    page = f'''<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Freight Invoice Audit Dashboard</title>
<style>
:root{{--navy:#142d4e;--blue:#2563eb;--muted:#64748b;--line:#e2e8f0;--bg:#f4f7fb}}*{{box-sizing:border-box}}body{{font:14px Inter,system-ui,Arial;background:var(--bg);color:#17233c;margin:0}}header{{background:linear-gradient(120deg,#102a4c,#1e5590);color:white;padding:27px max(22px,calc((100% - 1480px)/2));display:flex;justify-content:space-between;align-items:center;gap:18px;flex-wrap:wrap}}header h1{{margin:0 0 6px;font-size:27px}}header p{{margin:0;color:#dbeafe}}.header-tag{{border:1px solid #ffffff55;border-radius:30px;padding:8px 13px;font-size:12px}}main{{max-width:1480px;margin:24px auto;padding:0 20px}}.stats{{display:grid;grid-template-columns:repeat(5,minmax(140px,1fr));gap:13px;margin-bottom:17px}}.stat,.panel,.detail-card{{background:white;border:1px solid var(--line);border-radius:13px;box-shadow:0 3px 12px #0f172a08}}.stat{{padding:17px;text-align:left;cursor:pointer;color:inherit;font:inherit}}.stat:hover{{border-color:#93c5fd;transform:translateY(-1px)}}.stat span{{color:var(--muted);font-size:12px;display:block}}.stat strong{{display:block;font-size:25px;margin-top:7px;color:#1e5ea8}}.stat small{{display:block;color:var(--muted);margin-top:3px}}.panel{{padding:19px;margin-bottom:17px}}.overview{{display:grid;grid-template-columns:1.4fr 1fr;gap:16px}}.panel h2{{font-size:17px;margin:0 0 4px}}.muted{{color:var(--muted)}}.issue-row{{display:grid;grid-template-columns:175px 1fr 45px;align-items:center;gap:10px;margin:10px 0;font-size:12px}}.bar-track{{height:9px;border-radius:20px;background:#edf2f7;overflow:hidden}}.bar-track i{{display:block;height:100%;border-radius:20px;background:linear-gradient(90deg,#3b82f6,#0f766e)}}.toolbar{{display:flex;gap:10px;justify-content:space-between;align-items:end;flex-wrap:wrap;margin:17px 0 13px}}.filters{{display:flex;gap:8px;flex-wrap:wrap;align-items:center}}input,select{{border:1px solid #cbd5e1;border-radius:8px;padding:10px 11px;background:white;font:inherit;color:#17233c}}input{{min-width:240px}}button{{font:inherit;cursor:pointer}}.action{{border:0;border-radius:8px;padding:10px 13px;background:#1d4ed8;color:white;font-weight:650}}.action.secondary{{background:#eaf1ff;color:#1d4ed8}}.scroll{{overflow:auto}}table{{border-collapse:collapse;width:100%;background:white;white-space:nowrap}}td,th{{padding:11px 12px;border-bottom:1px solid #edf0f5;text-align:left;font-size:12px}}th{{background:#f1f5f9;color:#475569;position:sticky;top:0;cursor:pointer;user-select:none}}th:hover{{color:#1d4ed8}}tbody tr{{cursor:pointer}}tbody tr:hover{{background:#eff6ff}}.pill{{display:inline-block;padding:5px 9px;border-radius:20px;font-size:10px;font-weight:800;background:#fee2e2;color:#991b1b}}.pill.pass{{background:#dcfce7;color:#166534}}.pagination{{display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap;margin-top:13px}}.page-buttons{{display:flex;gap:6px;align-items:center}}.page-buttons button{{border:1px solid #cbd5e1;background:white;border-radius:7px;padding:7px 11px}}.page-buttons button:disabled{{opacity:.4;cursor:not-allowed}}.hidden{{display:none!important}}#detail{{margin-top:20px;padding:22px}}.detail-head{{display:flex;justify-content:space-between;gap:15px;align-items:center;flex-wrap:wrap;border-bottom:1px solid var(--line);padding-bottom:16px}}.detail-head h2{{margin:0 0 6px}}.detail-actions{{display:flex;gap:8px;align-items:center}}.close{{border:1px solid #cbd5e1;background:white;border-radius:8px;padding:9px 13px}}.detail-grid{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:13px;margin:18px 0}}.detail-card{{padding:16px;box-shadow:none}}.detail-card h3{{font-size:13px;color:#315579;margin:0 0 12px}}.kv{{display:flex;justify-content:space-between;gap:10px;padding:6px 0;border-bottom:1px solid #f1f5f9}}.kv:last-child{{border:0}}.kv span:first-child{{color:var(--muted)}}.kv strong{{text-align:right;overflow-wrap:anywhere}}.section-title{{font-size:16px;margin:22px 0 10px}}.empty{{color:var(--muted);padding:12px}}.footer-note{{color:var(--muted);font-size:12px;margin:18px 2px}}@media(max-width:1000px){{.stats{{grid-template-columns:repeat(3,1fr)}}.overview{{grid-template-columns:1fr}}}}@media(max-width:650px){{.stats{{grid-template-columns:repeat(2,1fr)}}.detail-grid{{grid-template-columns:1fr}}input{{min-width:100%}}.issue-row{{grid-template-columns:125px 1fr 35px}}}}@media print{{header,.stats,.overview,#invoicePanel,.footer-note,.detail-actions{{display:none!important}}body{{background:white}}main{{max-width:none;margin:0}}#detail{{display:block!important;border:0}}}}
</style></head><body><header><div><h1>Freight Invoice Audit</h1><p>Complete invoice visibility · Exception monitoring · Shipment-level drill-down</p></div><span class="header-tag">LIVE REPORT · GENERATED DATA</span></header><main>
<section class="stats">
<button class="stat" data-filter=""><span>Total invoices</span><strong>{len(audit_rows):,}</strong><small>Click to view all invoices</small></button>
<button class="stat" data-filter="PASS"><span>Passed invoices</span><strong>{len(passed):,}</strong><small>Within validation rules</small></button>
<button class="stat" data-filter="FLAG"><span>Flagged invoices</span><strong>{len(flagged):,}</strong><small>Require review</small></button>
<div class="stat"><span>Potential overcharge</span><strong>{html.escape(f'₹{flagged_value:,.2f}')}</strong><small>Positive flagged variance only</small></div>
<div class="stat"><span>Audit precision / recall</span><strong>{summary['precision']:.1%} / {summary['recall']:.1%}</strong><small>Total billed: ₹{total_billed:,.2f}</small></div>
</section>
<section class="overview"><div class="panel"><h2>Audit performance</h2><p class="muted">Validation quality based on the generated ground-truth checks.</p><div class="detail-grid" style="grid-template-columns:repeat(2,minmax(0,1fr));margin-bottom:0"> <div class="detail-card"><span class="muted">Precision</span><h2 style="font-size:27px;color:#15803d">{summary['precision']:.1%}</h2></div><div class="detail-card"><span class="muted">Recall</span><h2 style="font-size:27px;color:#1d4ed8">{summary['recall']:.1%}</h2></div><div class="detail-card"><span class="muted">True positives</span><h2>{summary['true_positives']:,}</h2></div><div class="detail-card"><span class="muted">True negatives</span><h2>{summary['true_negatives']:,}</h2></div></div></div>
<div class="panel"><h2>Flagged issue breakdown</h2><p class="muted">Number of detected issue instances by type.</p>{issue_bars}</div></section>
<section class="panel" id="invoicePanel"><div><h2>Invoice register</h2><span class="muted">All PASS and FLAG invoices are listed. Select any invoice to open its full details.</span></div>
<div class="toolbar"><div class="filters"><input id="search" placeholder="Search invoice, carrier, shipment or issue..."><select id="decision"><option value="">All decisions</option><option value="PASS">PASS only</option><option value="FLAG">FLAG only</option></select><input id="dateFrom" type="date" aria-label="Invoice date from"><input id="dateTo" type="date" aria-label="Invoice date to"><select id="pageSize"><option>25</option><option>50</option><option>100</option></select></div><div class="filters"><button class="action secondary" id="reset">Reset filters</button><button class="action" id="export">Export CSV</button></div></div>
<div class="scroll"><table><thead><tr><th data-sort="invoice_id">Invoice ↕</th><th data-sort="decision">Decision ↕</th><th data-sort="detected_issues">Detected issues ↕</th><th data-sort="expected_amount">Expected ↕</th><th data-sort="billed_amount">Billed ↕</th><th data-sort="difference">Difference ↕</th><th>Action</th></tr></thead><tbody id="invoiceRows"></tbody></table></div>
<div class="pagination"><span class="muted" id="resultCount">Loading invoices...</span><div class="page-buttons"><button id="prev">Previous</button><span id="pageInfo" class="muted"></span><button id="next">Next</button></div></div></section>
<section id="detail" class="panel hidden" aria-live="polite"><div id="detailContent"></div></section>
<p class="footer-note">Synthetic demonstration data. PASS means no configured validation rule was triggered; FLAG means one or more exceptions require review. This dashboard is a read-only audit view.</p></main>
<script>
const INVOICES={data};
const AUDIT_ROWS={audit_data};
const money=v=>v===null||v===undefined||v===''?'—':new Intl.NumberFormat('en-IN',{{style:'currency',currency:'INR',maximumFractionDigits:2}}).format(Number(v));
const val=v=>v===null||v===undefined||v===''?'—':String(v);
let filtered=[...AUDIT_ROWS],page=1,pageSize=25,sortKey='invoice_id',sortDir=1;
function esc(v){{return String(v??'').replace(/[&<>"']/g,c=>({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c]))}}
function applyFilters(){{const q=document.getElementById('search').value.toLowerCase().trim(),decision=document.getElementById('decision').value,from=document.getElementById('dateFrom').value,to=document.getElementById('dateTo').value;
filtered=AUDIT_ROWS.filter(r=>{{const d=INVOICES[r.invoice_id]?.invoice||{{}};const text=[r.invoice_id,r.decision,r.detected_issues,d.carrier_name,d.shipment_id,d.origin,d.destination].join(' ').toLowerCase();return (!q||text.includes(q))&&(!decision||r.decision===decision)&&(!from||(d.invoice_date||'')>=from)&&(!to||(d.invoice_date||'')<=to)}});
filtered.sort((a,b)=>{{let x=a[sortKey]??'',y=b[sortKey]??'';if(['expected_amount','billed_amount','difference'].includes(sortKey)){{x=Number(x);y=Number(y)}}else{{x=String(x).toLowerCase();y=String(y).toLowerCase()}}return (x>y?1:x<y?-1:0)*sortDir}});page=1;renderRows()}}
function renderRows(){{const total=filtered.length,pages=Math.max(1,Math.ceil(total/pageSize));page=Math.min(page,pages);const start=(page-1)*pageSize,subset=filtered.slice(start,start+pageSize);document.getElementById('invoiceRows').innerHTML=subset.map(r=>`<tr data-id="${{esc(r.invoice_id)}}"><td><b>${{esc(r.invoice_id)}}</b></td><td><span class="pill ${{r.decision==='PASS'?'pass':''}}">${{esc(r.decision)}}</span></td><td>${{esc((r.detected_issues||'—').replaceAll(';',', '))}}</td><td>${{money(r.expected_amount)}}</td><td>${{money(r.billed_amount)}}</td><td>${{money(r.difference)}}</td><td><button class="action secondary view" data-id="${{esc(r.invoice_id)}}">View details</button></td></tr>`).join('')||'<tr><td colspan="7" class="empty">No invoices match the selected filters.</td></tr>';
document.getElementById('resultCount').textContent=`Showing ${{total?start+1:0}}–${{Math.min(start+pageSize,total)}} of ${{total.toLocaleString()}} invoices`;document.getElementById('pageInfo').textContent=`Page ${{page}} of ${{pages}}`;document.getElementById('prev').disabled=page<=1;document.getElementById('next').disabled=page>=pages;
document.querySelectorAll('#invoiceRows tr[data-id]').forEach(tr=>tr.addEventListener('click',()=>openInvoice(tr.dataset.id)));document.querySelectorAll('.view').forEach(b=>b.addEventListener('click',e=>{{e.stopPropagation();openInvoice(b.dataset.id)}}))}}
function card(title,items){{return `<div class="detail-card"><h3>${{title}}</h3>${{items.map(([k,v])=>`<div class="kv"><span>${{esc(k)}}</span><strong>${{esc(val(v))}}</strong></div>`).join('')}}</div>`}}
function table(title,headers,rows){{const head=headers.map(h=>'<th>'+esc(h)+'</th>').join('');const body=rows.length?rows.map(r=>'<tr>'+r.map(x=>'<td>'+esc(val(x))+'</td>').join('')+'</tr>').join(''):'<tr><td colspan="'+headers.length+'" class="empty">No records available</td></tr>';return '<h3 class="section-title">'+title+'</h3><div class="scroll"><table><thead><tr>'+head+'</tr></thead><tbody>'+body+'</tbody></table></div>'}}
function openInvoice(id){{const d=INVOICES[id];if(!d)return;const i=d.invoice,a=d.audit||{{}};const issues=(a.detected_issues||'').split(';').filter(Boolean);const status=(a.decision||'PASS');
let out=`<div class="detail-head"><div><h2>${{esc(val(i.invoice_id))}}</h2><span class="muted">Invoice date: ${{esc(val(i.invoice_date))}} · ${{esc(val(i.status))}}</span></div><div class="detail-actions"><span class="pill ${{status==='PASS'?'pass':''}}">${{esc(status)}}</span><button class="close" onclick="window.print()">Print invoice</button><button class="close" onclick="closeDetail()">Close ✕</button></div></div>`;
out+=`<div class="detail-grid">${{card('Invoice summary',[['Invoice ID',i.invoice_id],['Invoice date',i.invoice_date],['Invoice status',i.status],['Carrier',i.carrier_name],['Carrier ID',i.carrier_id],['Original invoice',i.original_invoice_id]])}}${{card('Shipment details',[['Shipment ID',i.shipment_id],['Service',i.service],['Shipment status',i.shipment_status],['Ship date',i.ship_date],['Delivery date',i.delivery_date],['Actual weight',i.actual_weight_kg===null?'—':i.actual_weight_kg+' kg']])}}${{card('Route & dimensions',[['Origin',i.origin],['Destination',i.destination],['Distance',i.distance_km===null?'—':i.distance_km+' km'],['Length',i.length_cm===null?'—':i.length_cm+' cm'],['Width',i.width_cm===null?'—':i.width_cm+' cm'],['Height',i.height_cm===null?'—':i.height_cm+' cm']])}}</div>`;
out+=`<div class="detail-grid">${{card('Audit result',[['Decision',status],['Detected issues',issues.join(', ')||'None'],['Expected amount',money(a.expected_amount)],['Billed amount',money(a.billed_amount)],['Difference',money(a.difference)]])}}${{card('Payment summary',[['Invoice billed total',money(i.billed_total)],['Expected total',money(a.expected_amount)],['Variance',money(a.difference)],['Credit notes',d.credits.length]])}}${{card('Weight verification',d.weights.length?[['Actual kg',d.weights[0].actual_kg],['Dimensional kg',d.weights[0].dimensional_kg],['Billable kg',d.weights[0].billable_kg],['Measured at',d.weights[0].measured_at]]:[['Measurement','Not available']])}}</div>`;
out+=table('Invoice charge breakdown',['Line','Charge code','Amount'],d.lines.map(x=>[x.line_no,x.charge_code,money(x.amount)]));
out+=table('Audit exceptions',['Issue','Expected','Billed','Difference','Status','Created'],d.exceptions.map(x=>[x.issue_type,money(x.expected_amount),money(x.billed_amount),money(x.difference),x.status,x.created_at]));
out+=table('Shipment journey',['Leg','From','To','Delivered at'],d.legs.map(x=>[x.sequence_no,x.origin,x.destination,x.delivered_at]));
out+=table('Credit notes',['Credit ID','Requested amount','Approved amount','Status','Created'],d.credits.map(x=>[x.credit_id,money(x.amount),money(x.approved_amount),x.status,x.created_at]));
out+=table('Activity history',['Event','Date','Details'],d.events.map(x=>[x.event_type,x.event_date,x.detail]));document.getElementById('detailContent').innerHTML=out;const box=document.getElementById('detail');box.classList.remove('hidden');box.scrollIntoView({{behavior:'smooth',block:'start'}})}}
function closeDetail(){{document.getElementById('detail').classList.add('hidden')}}
function exportCsv(){{const cols=['invoice_id','decision','detected_issues','expected_amount','billed_amount','difference'];const lines=[cols.join(','),...filtered.map(r=>cols.map(k=>'"'+String(r[k]??'').replaceAll('"','""')+'"').join(','))];const blob=new Blob([lines.join('\\n')],{{type:'text/csv;charset=utf-8;'}});const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download='freight_invoice_audit_filtered.csv';a.click();URL.revokeObjectURL(url)}}
['search','decision','dateFrom','dateTo'].forEach(id=>document.getElementById(id).addEventListener(id==='search'?'input':'change',applyFilters));document.getElementById('pageSize').addEventListener('change',e=>{{pageSize=Number(e.target.value);page=1;renderRows()}});document.getElementById('reset').addEventListener('click',()=>{{['search','decision','dateFrom','dateTo'].forEach(id=>document.getElementById(id).value='');applyFilters()}});document.getElementById('export').addEventListener('click',exportCsv);document.getElementById('prev').addEventListener('click',()=>{{page--;renderRows()}});document.getElementById('next').addEventListener('click',()=>{{page++;renderRows()}});document.querySelectorAll('th[data-sort]').forEach(th=>th.addEventListener('click',()=>{{const k=th.dataset.sort;if(sortKey===k)sortDir*=-1;else{{sortKey=k;sortDir=1}}applyFilters()}}));document.querySelectorAll('.stat[data-filter]').forEach(b=>b.addEventListener('click',()=>{{document.getElementById('decision').value=b.dataset.filter;applyFilters();document.getElementById('invoicePanel').scrollIntoView({{behavior:'smooth'}})}}));applyFilters();
</script></body></html>'''
    (root / 'dashboard.html').write_text(page, encoding='utf-8')
    print('Open', root / 'dashboard.html', 'in a browser')


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--output', default='output')
    a = p.parse_args()
    report(a.output)
