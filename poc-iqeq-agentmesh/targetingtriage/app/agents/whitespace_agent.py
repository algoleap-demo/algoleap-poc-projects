import pandas as pd
from typing import List, Dict
from app.progress_tracker import tracker

def run_whitespace_agent(raw_data: Dict[str, pd.DataFrame]) -> List[Dict]:
    tracker.emit("ag-ml", "started", message="Analyzing whitespace potential across product matrices...")
    
    matrix_df = raw_data["account_product_matrix"]
    catalog_df = raw_data["product_catalog"]
    
    total_products = len(catalog_df)
    results = []
    
    account_ids = matrix_df["account_id"].unique()
    
    for i, acc_id in enumerate(account_ids):
        if i % 10 == 0:
            tracker.emit("ag-ml", "processing", message=f"Calculating whitespace for {acc_id} ({i+1}/{len(account_ids)})...")
            
        acc_matrix = matrix_df[matrix_df.account_id == acc_id]
        active_products = acc_matrix[acc_matrix.is_active == True]
        
        active_count = len(active_products)
        api_score = (active_count / total_products) if total_products > 0 else 0
        
        # Identify Gaps
        whitespace_products = acc_matrix[acc_matrix.is_active == False]
        total_potential = whitespace_products["current_revenue_eur"].count() * 15000 # Mock potential: 15k per prod
        
        gaps = []
        for _, row in whitespace_products.iterrows():
            prod_info = catalog_df[catalog_df.product_id == row["product_id"]].iloc[0]
            gaps.append({
                "product_id": row["product_id"],
                "product_name": prod_info["product_name"],
                "estimated_potential_eur": 15000 
            })
            
        results.append({
            "account_id": acc_id,
            "api_score": api_score,
            "total_ws_potential_eur": total_potential,
            "whitespace_summary": gaps
        })
        
    tracker.emit("ag-ml", "completed", message=f"Whitespace analysis complete for {len(results)} accounts.")
    return results
