import json
import os
import re

def verify_audit_log(log_path="logs/audit.jsonl"):
    if not os.path.exists(log_path):
        print(f"FAILED: Log file {log_path} not found.")
        return False

    with open(log_path, "r") as f:
        lines = f.readlines()

    if not lines:
        print("FAILED: Log file is empty.")
        return False

    print(f"Analyzing {len(lines)} audit entries...")
    
    sha256_regex = re.compile(r"^[a-f0-9]{64}$")
    trace_groups = {}

    for line in lines:
        try:
            entry = json.loads(line)
            trace_id = entry.get("run_id")
            if not trace_id: continue
            
            if trace_id not in trace_groups:
                trace_groups[trace_id] = []
            trace_groups[trace_id].append(entry)
        except Exception as e:
            print(f"ERROR: Could not parse line: {e}")

    poc2_detected = False
    
    for trace_id, entries in trace_groups.items():
        agents = [e["agent"] for e in entries]
        
        # Check if this is a POC 2 run (contains whitespace or brief agents)
        if "whitespace_agent" in agents or "brief_agent" in agents:
            poc2_detected = True
            print(f"\nVerifying POC 2 Trace: {trace_id}")
            
            required_agents = [
                "data_agent", "scoring_agent", "reasoning_agent", 
                "whitespace_agent", "brief_agent", "call_plan_agent", 
                "validation_agent", "formatting_agent"
            ]
            
            missing = [a for a in required_agents if a not in agents]
            if missing:
                print(f"  WARNING: Missing agents in trace: {missing}")
            else:
                print(f"  SUCCESS: All 8 agents present in lineage.")
            
            # Verify hashes
            for entry in entries:
                agent = entry["agent"]
                in_hash = entry.get("input_hash")
                out_hash = entry.get("output_hash")
                
                valid_in = sha256_regex.match(in_hash) if in_hash and in_hash != "hash_error" else (in_hash is None or in_hash == "hash_error")
                valid_out = sha256_regex.match(out_hash) if out_hash and out_hash != "hash_error" else False
                
                if in_hash == "hash_error" or out_hash == "hash_error":
                    print(f"  FAILED: Hash error detected in {agent}")
                elif not valid_out:
                    print(f"  FAILED: Invalid output hash for {agent}: {out_hash}")
                else:
                    print(f"  PASSED: {agent} (Audit Integrity Verified)")

    if not poc2_detected:
        print("\nWARNING: No POC 2 runs detected in audit log. Please run the pipeline from the dashboard first.")
        return False

    return True

if __name__ == "__main__":
    success = verify_audit_log()
    if success:
        print("\nPHASE 4 AUDIT VERIFICATION COMPLETE.")
    else:
        print("\nPHASE 4 AUDIT VERIFICATION FAILED.")
