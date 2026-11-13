#!/usr/bin/env python3
"""Attach audited NCCL identity/direction without changing event ownership."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
from build import load_json, require, validate


def enrich(data, audit, audit_sha, manifest_sha):
    require(audit.get('status')=='PASS_RETAINED_NCCL_DIRECTION_CENSUS_FORWARD_PEER_BYTES_UNRESOLVED','NCCL audit did not qualify')
    require(data.get('status')=='measured','NCCL enrichment requires measured input')
    artifacts={a['id']:a for a in data['artifacts']}
    provenance=audit['provenance']
    require(artifacts['parser-sidecar']['sha256']==provenance['sidecar_sha256'],'NCCL audit/sidecar mismatch')
    require(artifacts['trace-sqlite']['sha256']==provenance['sqlite_sha256'],'NCCL audit/SQLite mismatch')
    require(data['timeline']['origin_ns']==provenance['trace_origin_ns'],'NCCL audit/timeline origin mismatch')
    require(audit['direct_forward_enclosures']==0 and audit['nonnull_operation_payload_count']==0,'unsupported NCCL audit scope')
    result=copy.deepcopy(data)
    events={e['id']:e for e in result['events']}
    records=audit['records'];seen=set();counts={'send':0,'recv':0}
    require(len(records)==audit['kernel_count'],'NCCL audit count mismatch')
    for record in records:
        event_id=record['event_id']
        require(event_id not in seen and event_id in events,'unknown or duplicate NCCL event ID');seen.add(event_id)
        event=events[event_id]
        require(event['owner_id'] is None and event['kind']=='kernel','NCCL classification must preserve unresolved ownership')
        require(all(event[k]==record[k] for k in ['rank','start_ns','duration_ns']),'NCCL audit/event interval mismatch')
        require(record['sidecar_forward_ordinal'] is None and record['forward_nvtx_row_id'] is None,'unexpected NCCL forward ownership')
        require(all(record[k] is None for k in ['peer_rank','communicator_id','message_bytes']),'unexpected NCCL payload evidence')
        direction=record['direction'];require(direction in counts,'unsupported NCCL direction');counts[direction]+=1
        require(event.get('category') in {'unclassified','communication'},'NCCL category conflicts with current classification')
        event.update(category='communication',communication_direction=direction,classification_artifact_id='nccl-direction-audit')
    require(counts==audit['directions'],'NCCL direction counts differ')
    for artifact in [dict(id='nccl-direction-audit',label='Independent retained NCCL identity and direction audit',sha256=audit_sha),
                     dict(id='nccl-direction-manifest',label='NCCL audit source and evidence manifest',sha256=manifest_sha)]:
        if artifact['id'] in artifacts:
            require(artifacts[artifact['id']]==artifact,'conflicting NCCL audit artifact')
        else:result['artifacts'].append(artifact)
    note=(f"{len(records)} retained NCCL kernels ({counts['send']} send, {counts['recv']} receive) have audited communication identity and direction. "
          'Their forward ownership, peer, communicator and message bytes remain unavailable. Residency includes waiting and is not a recoverable-time estimate.')
    if note not in result['limitations']:result['limitations'].append(note)
    validate(result)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['input','audit','manifest','output']:parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();audit_raw=args.audit.read_bytes();manifest_raw=args.manifest.read_bytes()
    audit_sha=hashlib.sha256(audit_raw).hexdigest();manifest=load_json(manifest_raw)
    require(manifest.get('status')=='COMPLETE_RETAINED_NCCL_CENSUS_NO_FORWARD_OR_PAYLOAD_ATTRIBUTION','NCCL audit manifest incomplete')
    require(manifest['files_sha256'].get('result.json')==audit_sha,'NCCL result/manifest hash mismatch')
    result=enrich(load_json(args.input.read_bytes()),load_json(audit_raw),audit_sha,hashlib.sha256(manifest_raw).hexdigest())
    args.output.write_text(json.dumps(result,ensure_ascii=False,separators=(',',':'))+'\n')
    print(json.dumps({'events':len(result['events']),'audited_nccl_events':sum(e.get('classification_artifact_id')=='nccl-direction-audit' for e in result['events']),'ownership_changed':False}))


if __name__=='__main__':main()
