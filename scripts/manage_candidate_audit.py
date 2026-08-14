#!/usr/bin/env python3
import argparse,json,sys
from datetime import datetime,timedelta,timezone
from pathlib import Path
B={"SS","S+","S","S-","A+","A","A-","B+","B","B-"}
R={"selected_threshold_met","outside_time_window","duplicate_merged","continuation_no_material_change","below_public_value_threshold","unreliable_or_unverified","superseded_by_later_update","wrong_scope","processing_failure","search_recall_failure"}
def load(p):return json.loads(Path(p).read_text(encoding="utf-8"))
def dt(v):
 x=datetime.fromisoformat(v.replace("Z","+00:00"));return x if x.tzinfo else x.replace(tzinfo=timezone.utc)
def validate(d):
 e=[]
 if d.get("schema_version")!="1.0.0":e.append("schema_version 必須是 1.0.0")
 for ri,r in enumerate(d.get("runs",[]),1):
  for ci,c in enumerate(r.get("candidates",[]),1):
   p=f"runs[{ri}].candidates[{ci}]"
   if c.get("reason_code") not in R:e.append(p+" reason_code 無效")
   if c.get("provisional_grade") in {"D","E"} and c.get("decision")=="selected":e.append(p+" D/E 不得入選")
   if c.get("provisional_grade") in B and c.get("decision")!="selected" and not c.get("reason"):e.append(p+" B 級以上未入選但沒有理由")
   if c.get("source_audit",{}).get("reliable_source_count")==1 and c.get("reason_code")=="unreliable_or_unverified":e.append(p+" 已有一個可靠來源，不得僅以來源不足排除")
 return e
def main():
 p=argparse.ArgumentParser();s=p.add_subparsers(dest="cmd",required=True)
 a=s.add_parser("append");a.add_argument("--history",required=True);a.add_argument("--run",required=True);a.add_argument("--output",required=True);a.add_argument("--retention-days",type=int,default=14)
 v=s.add_parser("validate");v.add_argument("--input",required=True);x=p.parse_args()
 try:
  if x.cmd=="validate":
   e=validate(load(x.input));[print("FAIL:",z) for z in e];print("OK" if not e else "");return int(bool(e))
  h=load(x.history) if Path(x.history).exists() else {"runs":[]};r=load(x.run);cut=dt(r["generated_at"])-timedelta(days=x.retention_days)
  runs=[z for z in h.get("runs",[]) if dt(z["generated_at"])>=cut and z.get("run_id")!=r.get("run_id")]+[r];runs.sort(key=lambda z:dt(z["generated_at"]))
  out={"schema_version":"1.0.0","retention_days":x.retention_days,"updated_at":dt(r["generated_at"]).isoformat(),"runs":runs};e=validate(out)
  if e:raise ValueError("；".join(e))
  Path(x.output).write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8");print("OK");return 0
 except Exception as z:print("FAIL:",z);return 1
if __name__=="__main__":sys.exit(main())
