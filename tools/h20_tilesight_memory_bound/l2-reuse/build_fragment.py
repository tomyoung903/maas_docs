"""Pack an already-generated cache trace into the portable visualization."""
import argparse,json
from pathlib import Path
parser=argparse.ArgumentParser();parser.add_argument('--data-dir',type=Path,required=True);args=parser.parse_args()
root=Path(__file__).resolve().parent
payload={'probabilities':(args.data_dir/'probabilities.b64').read_text(),
         'metadata':json.loads((args.data_dir/'metadata.json').read_text())}
text=(root/'template.html').read_text().replace('__MODEL_DATA__',json.dumps(payload,separators=(',',':')))
assert '__MODEL_DATA__' not in text and len(text.encode())<1_000_000
(root/'fragment.html').write_text(text)
print(root/'fragment.html',len(text.encode()))
