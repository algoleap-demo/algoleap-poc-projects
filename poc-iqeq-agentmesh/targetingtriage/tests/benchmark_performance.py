import time
import asyncio
import os
import sys
import pandas as pd

# Add project root to path
sys.path.append(os.getcwd())

from app.orchestration_agent import run_pipeline

async def run_benchmark():
    print("=== IQ-EQ Agent Mesh Performance Benchmark ===")
    
    # 1. Warm up (Load data)
    print("Warming up...")
    
    # 2. Measure Live Pipeline
    print("Executing full 6-agent pipeline for 50 accounts...")
    start_time = time.perf_counter()
    
    # Trigger pipeline
    # Note: run_pipeline uses the synthetic/ runtime data (50 accounts)
    result = await run_pipeline()
    
    end_time = time.perf_counter()
    duration = end_time - start_time
    
    num_accounts = len(result["accounts"])
    ms_per_account = (duration * 1000) / num_accounts
    
    print("-" * 40)
    print(f"Total Accounts:    {num_accounts}")
    print(f"Total Duration:    {duration:.3f} seconds")
    print(f"Latency per Acct:  {ms_per_account:.2f} ms")
    print("-" * 40)
    
    # Verification of scaling
    # In a real benchmark, we'd run with 500, but for POC1 we stick to the 50 demographic.
    
    if ms_per_account < 500:
        print("PERFORMANCE: [PASS] - Latency is well within real-time SLA (<500ms/acct)")
    else:
        print("PERFORMANCE: [WARNING] - High latency detected.")

if __name__ == "__main__":
    asyncio.run(run_benchmark())
