import json,subprocess,sys
from datetime import datetime,timedelta,timezone
from pathlib import Path
S=Path(__file__).resolve().parents[1]/"scripts"/"manage_candidate_audit.py"
def c(g="D",d="excluded",r="below_public_value_threshold",n=2):return {"candidate_id":"c","dedup_key":"c","title":"測試","section":"GLB","provisional_grade":g,"decision":d,"reason_code":r,"reason":"理由","source_audit":{"reliable_source_count":n},"continuity":{"status":"new","material_changes":[],"unchanged_elements":[],"comparison_note":"首次"}}
def test_prune(tmp_path):
 now=datetime(2026,8,14,tzinfo=timezone.utc);old=now-timedelta(days=15);h={"runs":[{"run_id":"o","generated_at":old.isoformat(),"candidates":[c()]}]};r={"run_id":"n","generated_at":now.isoformat(),"window_start":now.isoformat(),"window_end":now.isoformat(),"candidates":[c()]};hp,rp,op=tmp_path/"h",tmp_path/"r",tmp_path/"o";hp.write_text(json.dumps(h));rp.write_text(json.dumps(r));q=subprocess.run([sys.executable,str(S),"append","--history",str(hp),"--run",str(rp),"--output",str(op)]);assert q.returncode==0;assert [x["run_id"] for x in json.loads(op.read_text())["runs"]]==["n"]
def test_single_source_not_exclusion(tmp_path):
 now=datetime.now(timezone.utc).isoformat();d={"schema_version":"1.0.0","runs":[{"run_id":"r","generated_at":now,"candidates":[c("A","excluded","unreliable_or_unverified",1)]}]};p=tmp_path/"a";p.write_text(json.dumps(d));q=subprocess.run([sys.executable,str(S),"validate","--input",str(p)]);assert q.returncode==1
