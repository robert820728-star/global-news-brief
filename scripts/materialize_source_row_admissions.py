#!/usr/bin/env python3
"""Build and validate the immutable, lossless source-row admission universe."""
from __future__ import annotations

import argparse, json, re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

SCHEMA_VERSION="1.1.0"; HEX64=re.compile(r"^[0-9a-f]{64}$"); ROW_ID=re.compile(r"^row-[0-9a-f]{24}$")
STATUSES={"content_ready","unresolved_exhausted"}; REVIEWS={"pending_semantic_review","unresolved_exhausted"}

def _rows(v:Any,label:str):
    if not isinstance(v,list) or not all(isinstance(x,dict) for x in v): raise ValueError(f"{label} rows must be an array of objects")
    ids=[str(x.get("row_id","")) for x in v]
    if any(not x for x in ids) or len(ids)!=len(set(ids)): raise ValueError(f"{label} row_id values must be non-empty and unique")
    return v,dict(zip(ids,v))

def _required(v:dict,fields:tuple[str,...],label:str):
    for f in fields:
        if not str(v.get(f,"")).strip(): raise ValueError(f"{label} missing {f}")

def build(source_candidates:dict,relevance_gate:dict,article_evidence:dict,*,run_id:str)->dict:
    candidates,cmap=_rows(source_candidates.get("items"),"source candidate"); decisions,dmap=_rows(relevance_gate.get("decisions"),"relevance decision"); evidence,emap=_rows(article_evidence.get("rows"),"article evidence")
    expected=set(cmap)
    if set(dmap)!=expected or set(emap)!=expected: raise ValueError("relevance decisions and article evidence must match source rows exactly")
    if relevance_gate.get("input_article_row_count")!=len(candidates): raise ValueError("relevance gate input count must equal source row count")
    out=[]
    for c in candidates:
        rid=c["row_id"]; d=dmap[rid]; e=emap[rid]; _required(c,("candidate_id","provisional_group_id","source_id","section","url","canonical_url","published_at","listing_timestamp_evidence"),f"source row {rid}")
        if d.get("candidate_id")!=c.get("candidate_id") or d.get("source_id")!=c.get("source_id") or d.get("canonical_url")!=c.get("canonical_url"): raise ValueError(f"relevance decision mismatch for {rid}")
        status=e.get("admission_status")
        if status not in STATUSES: raise ValueError(f"article evidence {rid} admission_status is invalid")
        model=e.get("model_evidence")
        if not isinstance(model,dict) or model.get("review_status") not in REVIEWS or not str(model.get("reason","")).strip() or not isinstance(model.get("evidence_refs"),list) or not model["evidence_refs"]: raise ValueError(f"article evidence {rid} model_evidence is invalid")
        row={"row_id":rid,"candidate_id":c["candidate_id"],"provisional_group_id":c["provisional_group_id"],"source_id":c["source_id"],"section":c["section"],"url":c["url"],"canonical_url":c["canonical_url"],"listing_published_at":c["published_at"],"listing_timestamp_evidence":c["listing_timestamp_evidence"],"relevance_route":d["route"],"relevance_reasons":d["reasons"],"admission_status":status,"model_evidence":model}
        if status=="content_ready":
            _required(e,("article_body_published_at","article_body_timestamp_evidence","article_body_evidence_url","content_sha256"),f"article evidence {rid}")
            if not HEX64.fullmatch(str(e["content_sha256"]).lower()): raise ValueError(f"article evidence {rid} content_sha256 is invalid")
            row.update({k:e[k] for k in ("article_body_published_at","article_body_timestamp_evidence","article_body_evidence_url")}); row["content_sha256"]=str(e["content_sha256"]).lower(); row["failure_evidence"]=None
        else:
            failure=e.get("failure_evidence")
            if not isinstance(failure,dict) or not str(failure.get("attempted_url","")).strip() or not str(failure.get("error","")).strip(): raise ValueError(f"exhausted article evidence {rid} requires failure_evidence")
            row.update({"article_body_published_at":None,"article_body_timestamp_evidence":None,"article_body_evidence_url":None,"content_sha256":None,"failure_evidence":failure})
        out.append(row)
    result={"schema_version":SCHEMA_VERSION,"run_id":run_id,"window_start":source_candidates.get("window_start"),"window_end":source_candidates.get("window_end"),"source_row_count":len(candidates),"admitted_row_count":len(out),"rows":out}
    errors=validate(result)
    if errors: raise ValueError("; ".join(errors))
    return result

def validate(data:dict)->list[str]:
    errors=[]
    if data.get("schema_version")!=SCHEMA_VERSION: errors.append(f"schema_version must be {SCHEMA_VERSION}")
    rows=data.get("rows")
    if not isinstance(rows,list): return errors+["rows must be an array"]
    ids=[x.get("row_id") for x in rows if isinstance(x,dict)]
    if len(ids)!=len(rows) or any(not x for x in ids) or len(set(ids))!=len(ids): errors.append("admission row_id values must be present and unique")
    try:
        start=datetime.fromisoformat(str(data.get("window_start","")).replace("Z","+00:00")); end=datetime.fromisoformat(str(data.get("window_end","")).replace("Z","+00:00"))
    except ValueError: start=end=None; errors.append("run window is invalid")
    for i,x in enumerate(rows,1):
        if not isinstance(x,dict): continue
        label=f"rows[{i}]"; status=x.get("admission_status")
        if not ROW_ID.fullmatch(str(x.get("row_id",""))): errors.append(f"{label}.row_id is invalid")
        for f in ("candidate_id","provisional_group_id","source_id","section","url","canonical_url","listing_published_at","listing_timestamp_evidence"):
            if not str(x.get(f,"")).strip(): errors.append(f"{label}.{f} is required")
        if x.get("relevance_route") not in {"content_hydration","lightweight_semantic_review"}: errors.append(f"{label}.relevance_route is invalid")
        if status not in STATUSES: errors.append(f"{label}.admission_status is invalid")
        m=x.get("model_evidence")
        if not isinstance(m,dict) or m.get("review_status") not in REVIEWS or not str(m.get("reason","")).strip() or not isinstance(m.get("evidence_refs"),list) or not m.get("evidence_refs"): errors.append(f"{label}.model_evidence is invalid")
        if status=="content_ready":
            for f in ("article_body_published_at","article_body_timestamp_evidence","article_body_evidence_url","content_sha256"):
                if not str(x.get(f,"")).strip(): errors.append(f"{label}.{f} is required for content_ready")
            if not HEX64.fullmatch(str(x.get("content_sha256",""))): errors.append(f"{label}.content_sha256 is invalid")
            if start and end:
                try:
                    t=datetime.fromisoformat(str(x.get("article_body_published_at","")).replace("Z","+00:00"))
                    if not start<=t<=end: errors.append(f"{label}.article_body_published_at must be inside run window")
                except ValueError: errors.append(f"{label}.article_body_published_at is invalid")
        elif status=="unresolved_exhausted":
            f=x.get("failure_evidence")
            if not isinstance(f,dict) or not str(f.get("attempted_url","")).strip() or not str(f.get("error","")).strip(): errors.append(f"{label}.failure_evidence is required for unresolved_exhausted")
            if isinstance(m,dict) and m.get("review_status")!="unresolved_exhausted": errors.append(f"{label} exhausted row must preserve exhausted model evidence")
    if data.get("source_row_count")!=len(rows) or data.get("admitted_row_count")!=len(rows): errors.append("row counts must equal durable row count")
    if sum(Counter(x.get("admission_status") for x in rows if isinstance(x,dict)).values())!=len(rows): errors.append("admission status count must conserve all rows")
    return errors

def load(path:str)->dict:
    v=json.loads(Path(path).read_text(encoding="utf-8"));
    if not isinstance(v,dict): raise ValueError(f"{path} must contain a JSON object")
    return v

def main()->int:
    p=argparse.ArgumentParser(); s=p.add_subparsers(dest="command",required=True); b=s.add_parser("build");
    for n in ("source-candidates","relevance-gate","article-evidence","run-id","output"): b.add_argument("--"+n,required=True)
    v=s.add_parser("validate"); v.add_argument("--input",required=True); a=p.parse_args()
    try:
        if a.command=="validate":
            e=validate(load(a.input)); [print("FAIL:",x) for x in e]; print("OK") if not e else None; return int(bool(e))
        r=build(load(a.source_candidates),load(a.relevance_gate),load(a.article_evidence),run_id=a.run_id); o=Path(a.output); o.parent.mkdir(parents=True,exist_ok=True); o.write_text(json.dumps(r,ensure_ascii=False,indent=2)+"\n",encoding="utf-8"); print(o); return 0
    except (OSError,ValueError,json.JSONDecodeError) as e: print("FAIL:",e); return 1
if __name__=="__main__": raise SystemExit(main())
