"""Reproducible freight invoice synthetic dataset generator (Python standard library)."""
import argparse, csv, hashlib, json, random, sqlite3
from datetime import date, timedelta
from pathlib import Path

TABLES = ['Carrier','Lane','RateCard','Shipment','ShipmentLeg','WeightMeasurement','Accessorial','FreightInvoice','InvoiceLine','AuditException','CreditNote']
SCHEMA = '''
PRAGMA foreign_keys=ON;
CREATE TABLE Carrier(carrier_id TEXT PRIMARY KEY,name TEXT NOT NULL,active INTEGER NOT NULL CHECK(active IN (0,1)));
CREATE TABLE Lane(lane_id TEXT PRIMARY KEY,origin TEXT NOT NULL,destination TEXT NOT NULL, distance_km INTEGER NOT NULL CHECK(distance_km>0));
CREATE TABLE RateCard(rate_id TEXT PRIMARY KEY,carrier_id TEXT NOT NULL REFERENCES Carrier(carrier_id),lane_id TEXT NOT NULL REFERENCES Lane(lane_id),service TEXT NOT NULL CHECK(service IN ('STANDARD','EXPRESS')),tier_min REAL NOT NULL,tier_max REAL NOT NULL,base_charge REAL NOT NULL,valid_from TEXT NOT NULL,valid_to TEXT NOT NULL,CHECK(tier_min<tier_max));
CREATE TABLE Shipment(shipment_id TEXT PRIMARY KEY,carrier_id TEXT NOT NULL REFERENCES Carrier(carrier_id),lane_id TEXT NOT NULL REFERENCES Lane(lane_id),service TEXT NOT NULL,ship_date TEXT NOT NULL,delivery_date TEXT NOT NULL,length_cm REAL NOT NULL,width_cm REAL NOT NULL,height_cm REAL NOT NULL,actual_weight_kg REAL NOT NULL,status TEXT NOT NULL);
CREATE TABLE ShipmentLeg(leg_id TEXT PRIMARY KEY,shipment_id TEXT NOT NULL REFERENCES Shipment(shipment_id),sequence_no INTEGER NOT NULL,origin TEXT NOT NULL,destination TEXT NOT NULL,delivered_at TEXT,UNIQUE(shipment_id,sequence_no));
CREATE TABLE WeightMeasurement(measurement_id TEXT PRIMARY KEY,shipment_id TEXT NOT NULL REFERENCES Shipment(shipment_id),actual_kg REAL NOT NULL,dimensional_kg REAL NOT NULL,billable_kg REAL NOT NULL,measured_at TEXT NOT NULL);
CREATE TABLE Accessorial(accessorial_id TEXT PRIMARY KEY,code TEXT UNIQUE NOT NULL,description TEXT NOT NULL,rate REAL NOT NULL,calculation TEXT NOT NULL);
CREATE TABLE FreightInvoice(invoice_id TEXT PRIMARY KEY,shipment_id TEXT NOT NULL,carrier_id TEXT NOT NULL REFERENCES Carrier(carrier_id),invoice_date TEXT NOT NULL,billed_total REAL NOT NULL,status TEXT NOT NULL,original_invoice_id TEXT);
CREATE TABLE InvoiceLine(line_id TEXT PRIMARY KEY,invoice_id TEXT NOT NULL REFERENCES FreightInvoice(invoice_id),line_no INTEGER NOT NULL,charge_code TEXT NOT NULL,amount REAL NOT NULL,UNIQUE(invoice_id,line_no));
CREATE TABLE AuditException(exception_id TEXT PRIMARY KEY,invoice_id TEXT NOT NULL REFERENCES FreightInvoice(invoice_id),issue_type TEXT NOT NULL,expected_amount REAL NOT NULL,billed_amount REAL NOT NULL,difference REAL NOT NULL,status TEXT NOT NULL,created_at TEXT NOT NULL);
CREATE TABLE CreditNote(credit_id TEXT PRIMARY KEY,exception_id TEXT NOT NULL REFERENCES AuditException(exception_id),invoice_id TEXT NOT NULL REFERENCES FreightInvoice(invoice_id),amount REAL NOT NULL,approved_amount REAL NOT NULL,status TEXT NOT NULL,created_at TEXT NOT NULL);
CREATE TABLE EventHistory(event_id INTEGER PRIMARY KEY AUTOINCREMENT,entity_type TEXT NOT NULL,entity_id TEXT NOT NULL,event_type TEXT NOT NULL,event_date TEXT NOT NULL,detail TEXT NOT NULL);
'''
LANES=[('Hyderabad','Bengaluru',570),('Mumbai','Pune',150),('Delhi','Jaipur',280),('Chennai','Coimbatore',500),('Kolkata','Bhubaneswar',440),('Hyderabad','Vijayawada',275),('Pune','Nagpur',710),('Delhi','Chandigarh',250)]
TIERS=[(0,100),(100,500),(500,1000),(1000,100000)]
ISSUES=['UNKNOWN_SHIPMENT','EXPIRED_RATE','WRONG_WEIGHT_TIER','DUPLICATE_SURCHARGE','EXCESSIVE_CREDIT_NOTE']

def write_csv(path,headers,rows):
    with open(path,'w',newline='',encoding='utf-8') as f:
        w=csv.writer(f);w.writerow(headers);w.writerows(rows)

def generate(output='output',scale='full',seed=20261022):
    root=Path(output);root.mkdir(parents=True,exist_ok=True)
    rng=random.Random(seed)
    carriers_count, shipments_count, invoices_count=(100,20000,15000) if scale=='full' else (5,100,80)
    db=root/'freight.db'
    if db.exists():db.unlink()
    con=sqlite3.connect(db);con.executescript(SCHEMA)
    c=con.cursor()
    carriers=[(f'CAR-{i:06d}',f'Carrier {i:03d} Logistics',1) for i in range(1,carriers_count+1)]
    c.executemany('INSERT INTO Carrier VALUES (?,?,?)',carriers)
    lanes=[(f'LANE-{i:04d}',*row) for i,row in enumerate(LANES,1)]
    c.executemany('INSERT INTO Lane VALUES (?,?,?,?)',lanes)
    c.executemany('INSERT INTO Accessorial VALUES (?,?,?,?,?)',[('ACC-FUEL','FUEL','Fuel surcharge',0.05,'PERCENT_BASE'),('ACC-HAND','HANDLING','Handling charge',200,'FLAT')])
    rates={}
    for carrier in carriers:
        for lane in lanes:
            for service in ('STANDARD','EXPRESS'):
                for tier_no,(low,high) in enumerate(TIERS):
                    amount=round((800+lane[3]*4+(tier_no+1)*1200)*(1.5 if service=='EXPRESS' else 1),2)
                    rid=f'RATE-{carrier[0]}-2026-{lane[0]}-{service}-{tier_no+1}'
                    c.execute('INSERT INTO RateCard VALUES (?,?,?,?,?,?,?,?,?)',(rid,carrier[0],lane[0],service,low,high,amount,'2026-01-01','2026-12-31'))
                    rates[(carrier[0],lane[0],service,tier_no)]=(rid,amount)
    shipments=[];legs=[];weights=[];shipment_info={}
    base_date=date(2026,1,5)
    for i in range(1,shipments_count+1):
        sid=f'SHP-2026-{i:06d}'; carrier=rng.choice(carriers)[0];lane=rng.choice(lanes);service=rng.choice(['STANDARD','STANDARD','EXPRESS'])
        shipped=(date(2027,1,5) if i==2 else base_date+timedelta(days=rng.randrange(270)));delivered=shipped+timedelta(days=rng.randint(1,5))
        length,width,height=(rng.randint(20,150),rng.randint(20,100),rng.randint(20,100))
        actual=round(rng.uniform(20,1500),2);dim=round(length*width*height/5000,2);billable=max(actual,dim)
        tier=next(j for j,(lo,hi) in enumerate(TIERS) if lo<billable<=hi)
        rate=rates[(carrier,lane[0],service,tier)][1]
        shipments.append((sid,carrier,lane[0],service,shipped.isoformat(),delivered.isoformat(),length,width,height,actual,'DELIVERED'))
        legs.append((f'LEG-{i:06d}-01',sid,1,lane[1],lane[2],delivered.isoformat()))
        weights.append((f'WGT-{i:06d}',sid,actual,dim,billable,shipped.isoformat()))
        shipment_info[sid]={'carrier':carrier,'rate':rate,'ship_date':shipped.isoformat(),'tier':tier,'lane':lane[0],'service':service}
    c.executemany('INSERT INTO Shipment VALUES (?,?,?,?,?,?,?,?,?,?,?)',shipments)
    c.executemany('INSERT INTO ShipmentLeg VALUES (?,?,?,?,?,?)',legs)
    c.executemany('INSERT INTO WeightMeasurement VALUES (?,?,?,?,?,?)',weights)
    invoice_rows=[];line_rows=[];labels=[];exceptions=[];credits=[];events=[]
    # Every issue type appears in both starter and full datasets.
    special={1:'UNKNOWN_SHIPMENT',2:'EXPIRED_RATE',3:'WRONG_WEIGHT_TIER',4:'DUPLICATE_SURCHARGE',5:'EXCESSIVE_CREDIT_NOTE'}
    for i in range(1,invoices_count+1):
        iid=f'FINV-2026-{i:06d}'
        sid=f'SHP-2026-{i:06d}' if i<=shipments_count else f'SHP-2026-{rng.randint(1,shipments_count):06d}'
        if i==6:sid='SHP-2026-000007' # intentional duplicate with invoice 7
        info=shipment_info[sid];carrier=info['carrier'];base=info['rate'];fuel=round(base*.05,2);handling=200.0
        issue=special.get(i,'NONE')
        if i>6 and i%47==0:issue=rng.choice(['OVERCHARGE','DUPLICATE_SURCHARGE','WRONG_WEIGHT_TIER'])
        inv_sid='SHP-2026-999999' if issue=='UNKNOWN_SHIPMENT' else sid
        invoice_date=(date.fromisoformat(info['ship_date'])+timedelta(days=7)).isoformat()
        # Shipment 2 deliberately occurs in 2027, after all 2026 rate cards expire.
        if issue=='WRONG_WEIGHT_TIER':base=round(base+1200,2)
        if issue=='OVERCHARGE':base=round(base+500,2)
        amounts=[('BASE',base),('FUEL',fuel),('HANDLING',handling)]
        if issue=='DUPLICATE_SURCHARGE':amounts.append(('FUEL',fuel))
        billed=round(sum(a for _,a in amounts),2)
        invoice_rows.append((iid,inv_sid,carrier,invoice_date,billed,'SUBMITTED',None))
        for j,(code,amount) in enumerate(amounts,1):line_rows.append((f'FLINE-{iid}-{j:02d}',iid,j,code,amount))
        # Validation ground truth is generated from explicit rules / injected scenario.
        if issue=='NONE' and i==7:issue='DUPLICATE_BILL'
        expected=round(info['rate']*1.05+200,2)
        if issue=='UNKNOWN_SHIPMENT':expected=0
        if issue=='EXPIRED_RATE':expected=round(info['rate']*1.05+200,2)
        if issue=='EXCESSIVE_CREDIT_NOTE':expected=round(info['rate']*1.05+200,2)
        if issue=='DUPLICATE_BILL':expected=round(info['rate']*1.05+200,2)
        labels.append((iid,issue,'FLAG' if issue!='NONE' else 'PASS',round(expected,2),billed))
        if issue!='NONE':
            eid=f'FEX-2026-{len(exceptions)+1:06d}'
            difference=round(billed-expected,2)
            exceptions.append((eid,iid,issue,expected,billed,difference,'OPEN',invoice_date))
            events.append(('AuditException',eid,'CREATED',invoice_date,issue))
            if issue=='EXCESSIVE_CREDIT_NOTE':
                credits.append((f'CRN-2026-{len(credits)+1:06d}',eid,iid,1500.0,1000.0,'REJECTED',invoice_date))
        events.append(('FreightInvoice',iid,'SUBMITTED',invoice_date,'Invoice generated'))
    c.executemany('INSERT INTO FreightInvoice VALUES (?,?,?,?,?,?,?)',invoice_rows)
    c.executemany('INSERT INTO InvoiceLine VALUES (?,?,?,?,?)',line_rows)
    c.executemany('INSERT INTO AuditException VALUES (?,?,?,?,?,?,?,?)',exceptions)
    c.executemany('INSERT INTO CreditNote VALUES (?,?,?,?,?,?,?)',credits)
    c.executemany('INSERT INTO EventHistory(entity_type,entity_id,event_type,event_date,detail) VALUES (?,?,?,?,?)',events)
    con.commit()
    # CSVs preserve invalid invoice references intentionally; SQLite FK is omitted only for FreightInvoice.shipment_id.
    for table in TABLES:
        rows=c.execute(f'SELECT * FROM {table}').fetchall()
        headers=[d[0] for d in c.description]
        write_csv(root/f'{table}.csv',headers,rows)
    write_csv(root/'ground_truth.csv',['invoice_id','issue_type','expected_decision','expected_amount','billed_amount'],labels)
    write_csv(root/'EventHistory.csv',['event_id','entity_type','entity_id','event_type','event_date','detail'],c.execute('SELECT * FROM EventHistory').fetchall())
    con.close()
    manifest={'seed':seed,'scale':scale,'counts':{'carriers':carriers_count,'shipments':shipments_count,'invoices':invoices_count},'source':'Entirely synthetic; no external data','sha256':{}}
    for path in sorted(root.glob('*.csv')):manifest['sha256'][path.name]=hashlib.sha256(path.read_bytes()).hexdigest()
    (root/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(f'Generated {carriers_count} carriers, {shipments_count} shipments, {invoices_count} invoices in {root}')
    return root

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--scale',choices=['starter','full'],default='starter');p.add_argument('--seed',type=int,default=20261022);p.add_argument('--output',default='output');a=p.parse_args()
    generate(a.output,a.scale,a.seed)
