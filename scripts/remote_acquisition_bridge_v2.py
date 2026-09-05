#!/usr/bin/env python3
"""Remote acquisition bridge v2: source/media compatibility plus bounded article hydration."""
from __future__ import annotations

import argparse, hashlib, json, os, subprocess, sys
from datetime import timedelta
from pathlib import Path
from typing import Any

from scripts import remote_acquisition_bridge as v1

HYDRATION_KEYS={"schema_version","operation","run_id","main_sha","window","batch_sequence","row_ids"}

def validate(value:dict[str,Any], expected_main_sha:str)->dict[str,Any]:
    if value.get("operation")!="article_hydration": return v1.validate_request(value,expected_main_sha=expected_main_sha)
    unknown=set(value)-HYDRATION_KEYS
    if unknown: raise ValueError(f"unknown request keys: {sorted(unknown)}")
    if value.get("schema_version")!="1.0": raise ValueError("schema_version must be 1.0")
    if not v1.RUN_ID_RE.fullmatch(str(value.get("run_id",""))): raise ValueError("run_id is invalid")
    if str(value.get("main_sha",""))!=expected_main_sha: raise ValueError("main_sha is invalid or stale")
    window=value.get("window")
    if not isinstance(window,dict) or set(window)!={"start","end"}: raise ValueError("window must contain only start and end")
    start=v1._parse_time(window["start"],"start"); end=v1._parse_time(window["end"],"end")
    if end-start!=timedelta(hours=24): raise ValueError("window must be exactly 24 hours")
    seq=value.get("batch_sequence")
    if not isinstance(seq,int) or seq<1: raise ValueError("batch_sequence must be a positive integer")
    ids=value.get("row_ids")
    if not isinstance(ids,list) or not 1<=len(ids)<=20 or len(ids)!=len(set(ids)) or not all(str(x).startswith("row-") for x in ids): raise ValueError("row_ids must contain 1..20 unique row IDs")
    return value

def _run(cmd:list[str])->None: subprocess.run(cmd,check=True)

def _enhance_source_scan(request:dict[str,Any], runtime:Path, output:Path)->None:
    python=sys.executable
    source_candidates=output/"source-candidates.json"; gate=output/"news-relevance-gate.json"; admitted=output/"model-source-candidates.json"
    _run([python,str(runtime/"scripts/build_source_candidate_list.py"),"--source-pool",str(output/"regional-news-source-pool.json"),"--scan-dir",str(output/"source-scans"),"--output",str(source_candidates),"--window-start",request["window"]["start"],"--window-end",request["window"]["end"]])
    _run([python,str(runtime/"scripts/build_news_relevance_gate.py"),"--source-candidates",str(source_candidates),"--gate-output",str(gate),"--admitted-output",str(admitted)])

def _append_jsonl(path:Path, value:dict[str,Any])->None:
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("a",encoding="utf-8") as f: f.write(json.dumps(value,ensure_ascii=False,separators=(",",":"))+"\n")

def prepare_hydration(request:dict[str,Any], runlogs:Path)->Path:
    root=runlogs/"logs"/"runs"/request["run_id"]/"remote-acquisition"; batch=root/"content-evidence"/f"batch-{request['batch_sequence']:04d}.jsonl"
    if batch.exists(): raise ValueError("hydration batch sequence already exists; resume must use first incomplete batch rather than overwrite")
    _append_jsonl(batch,{"record":"batch_receipt","status":"running","run_id":request["run_id"],"main_sha":request["main_sha"],"window":request["window"],"batch_sequence":request["batch_sequence"],"row_ids":request["row_ids"]})
    return batch

def execute_hydration(request:dict[str,Any], runtime:Path, runlogs:Path)->Path:
    root=runlogs/"logs"/"runs"/request["run_id"]/"remote-acquisition"; source=root/"source-candidates.json"; batch=root/"content-evidence"/f"batch-{request['batch_sequence']:04d}.jsonl"
    if not source.is_file() or not batch.is_file(): raise ValueError("source-scan candidate universe and running batch receipt are required")
    ids=root/"content-evidence"/f"batch-{request['batch_sequence']:04d}-row-ids.json"; result=root/"content-evidence"/f"batch-{request['batch_sequence']:04d}-result.json"
    ids.write_text(json.dumps(request["row_ids"]),encoding="utf-8")
    _run([sys.executable,str(runtime/"scripts/hydrate_source_rows.py"),"--source-candidates",str(source),"--row-ids",str(ids),"--window-start",request["window"]["start"],"--window-end",request["window"]["end"],"--output",str(result)])
    rows=json.loads(result.read_text(encoding="utf-8"))["rows"]
    for row in rows: _append_jsonl(batch,{"record":"row_result",**row})
    status="passed" if all(r["status"] in {"content_ready","unresolved_exhausted"} for r in rows) else "failed"
    _append_jsonl(batch,{"record":"batch_receipt","status":status,"batch_sequence":request["batch_sequence"],"row_count":len(rows),"content_ready":sum(r["status"]=="content_ready" for r in rows),"unresolved_exhausted":sum(r["status"]=="unresolved_exhausted" for r in rows),"result_sha256":hashlib.sha256(result.read_bytes()).hexdigest()})
    return root

def execute(request:dict[str,Any],runtime:Path,runlogs:Path)->Path:
    if request["operation"]=="article_hydration": return execute_hydration(request,runtime,runlogs)
    output=v1.execute_request(request,runtime_root=runtime,run_logs_root=runlogs)
    if request["operation"]=="source_scan": _enhance_source_scan(request,runtime,output)
    return output

def main()->int:
    p=argparse.ArgumentParser(); sub=p.add_subparsers(dest="command",required=True)
    for name in ("parse-comment","prepare-hydration","execute"):
        q=sub.add_parser(name)
        if name=="parse-comment": q.add_argument("--comment-env",required=True); q.add_argument("--output",required=True,type=Path)
        else: q.add_argument("--request",required=True,type=Path); q.add_argument("--run-logs-root",required=True,type=Path)
        q.add_argument("--expected-main-sha",required=True)
        if name=="execute": q.add_argument("--runtime-root",required=True,type=Path)
    a=p.parse_args()
    if a.command=="parse-comment":
        req=validate(v1.extract_request_from_comment(os.environ.get(a.comment_env,"")),a.expected_main_sha); v1._write_json_atomic(a.output,req); return 0
    req=validate(json.loads(a.request.read_text(encoding="utf-8")),a.expected_main_sha)
    if a.command=="prepare-hydration":
        if req["operation"]!="article_hydration": return 0
        print(prepare_hydration(req,a.run_logs_root)); return 0
    print(execute(req,a.runtime_root,a.run_logs_root)); return 0
if __name__=="__main__": raise SystemExit(main())
