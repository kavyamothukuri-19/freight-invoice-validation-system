import tempfile,unittest
from pathlib import Path
from generator import generate
from validator import validate

class ProjectTests(unittest.TestCase):
    def test_starter(self):
        with tempfile.TemporaryDirectory() as tmp:
            generate(tmp,'starter',20261022)
            summary=validate(tmp)
            self.assertEqual(summary['counts']['Carrier'],5)
            self.assertEqual(summary['counts']['Shipment'],100)
            self.assertEqual(summary['counts']['FreightInvoice'],80)
            self.assertEqual(summary['intentional_invalid_shipment_refs'],1)
            self.assertEqual(summary['line_total_mismatches'],0)
            self.assertEqual(summary['false_negatives'],0)
            self.assertEqual(summary['false_positives'],0)
            self.assertEqual(summary['missing_expected_issue_labels'],[])
    def test_reproducibility(self):
        with tempfile.TemporaryDirectory() as a,tempfile.TemporaryDirectory() as b:
            generate(a,'starter',20261022);generate(b,'starter',20261022)
            for name in ('Carrier.csv','Shipment.csv','FreightInvoice.csv','ground_truth.csv'):
                self.assertEqual((Path(a)/name).read_bytes(),(Path(b)/name).read_bytes())
if __name__=='__main__':unittest.main()
