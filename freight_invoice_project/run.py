import argparse
from generator import generate
from validator import validate
from report import report

if __name__=='__main__':
    p=argparse.ArgumentParser(description='Generate, audit and report synthetic freight invoices')
    p.add_argument('--scale',choices=['starter','full'],default='starter')
    p.add_argument('--seed',type=int,default=20261022)
    p.add_argument('--output',default='output')
    a=p.parse_args()
    generate(a.output,a.scale,a.seed)
    validate(a.output)
    report(a.output)
