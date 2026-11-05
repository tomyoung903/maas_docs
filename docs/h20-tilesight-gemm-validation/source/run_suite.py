"""One H20, five fixed shapes, unprofiled and kernel-trace measurements."""
import fcntl
import json
import os
from pathlib import Path
import signal
import subprocess

root=Path(__file__).resolve().parent
cases=json.loads((root/'cases.json').read_text())
# Freeze predictions before any measurement.
assert (root/'predictions.json').is_file()
lock=open('/tmp/tom-h20-gpu0.lock','w')
fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
env=dict(os.environ,CUDA_VISIBLE_DEVICES='0',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1')
def query(*args):
    return subprocess.check_output(['nvidia-smi',*args],text=True).strip()
uuid=query('-i','0','--query-gpu=uuid','--format=csv,noheader')
def idle_check():
    if uuid in query('--query-compute-apps=gpu_uuid,pid,process_name','--format=csv,noheader'):
        raise RuntimeError('GPU 0 is occupied; experiment not started.')
def execute(cmd,dest,log,timeout=180):
    with (dest/log).open('w') as output:
        proc=subprocess.Popen(cmd,cwd=dest,env=env,stdout=output,stderr=subprocess.STDOUT,start_new_session=True)
        try:
            rc=proc.wait(timeout=timeout)
        except BaseException:
            os.killpg(proc.pid,signal.SIGTERM)
            try: proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid,signal.SIGKILL);proc.wait()
            raise
    if rc: raise RuntimeError(f'{cmd[0]} failed with {rc}: {dest/log}')
idle_check()
(root/'device-before.txt').write_text(query('--query-gpu=index,name,memory.used,utilization.gpu,power.limit','--format=csv')+'\n')
try:
    for case in cases:
        dest=root/case['name'];dest.mkdir(exist_ok=True)
        args=[str(root/'benchmark'),str(case['m']),str(case['n']),str(case['k'])]
        idle_check()
        with (dest/'clock-samples.csv').open('w') as clocks:
            monitor=subprocess.Popen(['nvidia-smi','-i','0','--query-gpu=timestamp,utilization.gpu,memory.used,clocks.sm,clocks.mem,power.draw,temperature.gpu','--format=csv','-lms','200'],stdout=clocks,stderr=subprocess.DEVNULL)
            try:
                execute(args,dest,'measurement.jsonl')
                idle_check()
                profile=dest/'profiling';profile.mkdir(exist_ok=True)
                execute(['nsys','profile','--trace=cuda','--sample=none','--cpuctxsw=none','--force-overwrite=true','-o','device',*args],profile,'profile.log')
            finally:
                monitor.terminate();monitor.wait(timeout=5)
        execute(['nsys','export','--type','sqlite','--force-overwrite=true','--output','device.sqlite','device.nsys-rep'],profile,'export.log')
        print(case['name']+' finished',flush=True)
finally:
    (root/'device-after.txt').write_text(query('--query-compute-apps=gpu_uuid,pid,process_name','--format=csv')+'\n')
