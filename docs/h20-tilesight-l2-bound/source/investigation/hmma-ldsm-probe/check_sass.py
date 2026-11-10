"""Check expected static instruction counts after compiling the three probe modes."""
from pathlib import Path
import argparse,json,re
p=argparse.ArgumentParser();p.add_argument('sass',type=Path);a=p.parse_args()
text=a.sass.read_text();result={}
for section in text.split('Function : ')[1:]:
    name=section.splitlines()[0].strip()
    match=re.search(r'instruction_mix_probeILi([012])E',name)
    if not match: continue
    mode=int(match.group(1));hmma=len(re.findall(r'\bHMMA\.16816\.F32\b',section));ldsm=len(re.findall(r'\bLDSM\.16\.',section))
    expected_ldsm={0:0,1:27,2:24}[mode]
    result[['pure','pipelined','serial'][mode]]=dict(function=name,static_hmma=hmma,static_ldsm=ldsm,expected_hmma=32,expected_ldsm=expected_ldsm,pass_counts=hmma==32 and ldsm==expected_ldsm)
passed=len(result)==3 and all(r['pass_counts'] for r in result.values())
print(json.dumps(dict(pass_counts=passed,kernels=result,caveat='Static total counts; inspect branch/back-edge boundaries before treating them as dynamic loop counts.'),indent=2))
if not passed: raise SystemExit(1)
