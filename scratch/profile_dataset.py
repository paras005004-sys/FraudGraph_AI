import os
import pandas as pd
import json

base_dir = r"C:\Users\VIGNESH\.gemini\antigravity\scratch\FraudGraph-AI\dataset\HHGOA_IEEE"

files = ["README.md", "transactions.csv", "identity.csv", "closed_cases_history.csv", "case_pack.csv"]

report = {}

for f in files:
    path = os.path.join(base_dir, f)
    if not os.path.exists(path):
        report[f] = {"exists": False}
        continue
    size_mb = os.path.getsize(path) / (1024 * 1024)
    
    if f.endswith(".csv"):
        # Process CSV in chunks or head
        if f == "transactions.csv":
            # For 708MB file, read header and count total rows via chunking
            total_rows = 0
            cols = []
            dtypes = {}
            chunk_count = 0
            for chunk in pd.read_csv(path, chunksize=100000, low_memory=False):
                if total_rows == 0:
                    cols = list(chunk.columns)
                    dtypes = {k: str(v) for k, v in chunk.dtypes.items()}
                total_rows += len(chunk)
                chunk_count += 1
            report[f] = {
                "exists": True,
                "size_mb": round(size_mb, 2),
                "total_rows": total_rows,
                "num_columns": len(cols),
                "columns_sample": cols[:15],
                "added_columns": [c for c in ["customer_id", "ts", "channel", "risk_score"] if c in cols]
            }
        else:
            df = pd.read_csv(path, low_memory=False)
            report[f] = {
                "exists": True,
                "size_mb": round(size_mb, 2),
                "total_rows": len(df),
                "num_columns": len(df.columns),
                "columns": list(df.columns),
                "sample_record": df.head(1).to_dict(orient="records")[0] if len(df) > 0 else {}
            }

with open(r"C:\Users\VIGNESH\.gemini\antigravity\scratch\FraudGraph-AI\scratch\dataset_profile.json", "w") as out:
    json.dump(report, out, indent=2)

print("Dataset profiling complete.")
