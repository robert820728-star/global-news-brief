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
    w=value.get("window")
    if not isinstance(w,dict) or set(w)!={"start","end"}: raise ValueError("window must contain only start and end")
    if v1._parse_time(w["end"],"end")-v1._parse_time(w["start"],"start")!=timedelta(hours=24): raise ValueError("window must be exactly 24 hours")
    seq=value.get("batch_sequence"); ids=value.get("row_ids")
    if not isinstance(seq,int) or seq<1: raise ValueError("batch_sequence must be a positive integer")
    if not isinstance(ids,list) or not 1<=len(ids)<=20 or len(ids)!=len(set(ids)) or not all(str(x).startswith("row-") for x in ids): raise ValueError("row_ids must contain 1..20 unique row IDs")
    return value

def _run(cmd:list[str])->None: subprocess.run(cmd,check=True)
def _enhance_source_scan(request:dict[str,Any],runtime:Path,output:Path)->None:
    py=sys.executable; source=output/"source-candidates.json"; gate=output/"news-relevance-gate.json"; admitted=output/"model-source-candidates.json"
    _run([py,str(runtime/"scripts/build_source_candidate_list.py"),"--source-pool",str(output/"regional-news-source-pool.json"),"--scan-dir",str(output/"source-scans"),"--output",str(source),"--window-start",request["window"]["start"],"--window-end",request["window"]["end"]])
    _run([py,str(runtime/"scripts/build_news_relevance_gate.py"),"--source-candidates",str(source),"--gate-output",str(gate),"--admitted-output",str(admitted)])
def _append(path:Path,value:dict[str,Any])->None:
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("a",encoding="utf-8") as f: f.write(json.dumps(value,ensure_ascii=False,separators=(",",":"))+"\n")
def prepare_hydration(request:dict[str,Any],runlogs:Path)->Path:
    root=runlogs/"logs"/"runs"/request["run_id"]/"remote-acquisition"; batch=root/"content-evidence"/f"batch-{request['batch_sequence']:04d}.jsonl"
    if batch.exists(): raise ValueError("hydration batch sequence already exists; resume must use first incomplete batch rather than overwrite")
    _append(batch,{"record":"batch_receipt","status":"running","run_id":request["run_id"],"main_sha":request["main_sha"],"window":request["window"],"batch_sequence":request["batch_sequence"],"row_ids":request["row_ids"]}); return batch

def _finalize_if_complete(request:dict[str,Any],runtime:Path,runlogs:Path,root:Path)->None:
    source=json.loads((root/"source-candidates.json").read_text(encoding="utf-8")); expected={x["row_id"] for x in source["items"]}; collected={}
    for p in sorted((root/"content-evidence").glob("batch-*-result.json")):
        for r in json.loads(p.read_text(encoding="utf-8")).get("rows",[]):
            rid=r.get("row_id")
            if rid in collected: raise ValueError(f"duplicate hydrated row across batches: {rid}")
            collected[rid]=r
    if set(collected)-expected: raise ValueError("hydration produced rows outside source candidate universe")
    if set(collected)!=expected: return
    evidence=[]
    for item in source["items"]:
        r=collected[item["row_id"]]; ready=r["status"]=="content_ready"
        e={"row_id":item["row_id"],"candidate_id":item["candidate_id"],"admission_status":r["status"],"article_body_published_at":r.get("article_body_published_at"),"article_body_timestamp_evidence":r.get("article_body_timestamp_evidence"),"article_body_evidence_url":r.get("article_body_evidence_url"),"content_sha256":r.get("content_sha256"),"failure_evidence":None if ready else {"attempted_url":r["requested_url"],"error":r.get("error") or "hydration exhausted"},"model_evidence":{"review_status":"pending_semantic_review" if ready else "unresolved_exhausted","reason":"article body fetched and bound to this row" if ready else "article-body recovery exhausted without fabricating evidence","evidence_refs":[r.get("article_body_evidence_url") or r["requested_url"]]}}
        evidence.append(e)
    article=root/"article-evidence.json"; article.write_text(json.dumps({"schema_version":"1.0","rows":evidence},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    output=runlogs/"logs"/"runs"/request["run_id"]/"source-row-admissions.json"
    _run([sys.executable,str(runtime/"scripts/materialize_source_row_admissions.py"),"build","--source-candidates",str(root/"source-candidates.json"),"--relevance-gate",str(root/"news-relevance-gate.json"),"--article-evidence",str(article),"--run-id",request["run_id"],"--output",str(output)])

def execute_hydration(request:dict[str,Any],runtime:Path,runlogs:Path)->Path:
    root=runlogs/"logs"/"runs"/request["run_id"]/"remote-acquisition"; source=root/"source-candidates.json"; batch=root/"content-evidence"/f"batch-{request['batch_sequence']:04d}.jsonl"
    if not source.is_file() or not batch.is_file(): raise ValueError("source-scan candidate universe and running batch receipt are required")
    ids=root/"content-evidence"/f"batch-{request['batch_sequence']:04d}-row-ids.json"; result=root/"content-evidence"/f"batch-{request['batch_sequence']:04d}-result.json"; ids.write_text(json.dumps(request["row_ids"]),encoding="utf-8")
    _run([sys.executable,str(runtime/"scripts/hydrate_source_rows.py"),"--source-candidates",str(source),"--row-ids",str(ids),"--window-start",request["window"]["start"],"--window-end",request["window"]["end"],"--output",str(result)])
    rows=json.loads(result.read_text(encoding="utf-8"))["rows"]
    for r in rows: _append(batch,{"record":"row_result",**r})
    status="passed" if all(r["status"] in {"content_ready","unresolved_exhausted"} for r in rows) else "failed"
    _append(batch,{"record":"batch_receipt","status":status,"batch_sequence":request["batch_sequence"],"row_count":len(rows),"content_ready":sum(r["status"]=="content_ready" for r in rows),"unresolved_exhausted":sum(r["status"]=="unresolved_exhausted" for r in rows),"result_sha256":hashlib.sha256(result.read_bytes()).hexdigest()})
    _finalize_if_complete(request,runtime,runlogs,root); return root

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
    if a.command=="parse-comment": req=validate(v1.extract_request_from_comment(os.environ.get(a.comment_env,"")),a.expected_main_sha); v1._write_json_atomic(a.output,req); return 0
    req=validate(json.loads(a.request.read_text(encoding="utf-8")),a.expected_main_sha)
    if a.command=="prepare-hydration":
        if req["operation"]!="article_hydration": return 0
        print(prepare_hydration(req,a.run_logs_root)); return 0
    print(execute(req,a.runtime_root,a.run_logs_root)); return 0
if __name__=="__main__": raise SystemExit(main())
