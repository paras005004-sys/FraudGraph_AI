import pandas as pd
import json

base_dir = r"C:\Users\VIGNESH\.gemini\antigravity\scratch\FraudGraph-AI\dataset\HHGOA_IEEE"

print("=== AUDITING NEXT EDGE DERIVATION ===")

card_tx_map = {}
chunk_count = 0
for chunk in pd.read_csv(f"{base_dir}\\transactions.csv", chunksize=100000, low_memory=False, usecols=["TransactionID", "customer_id", "ts"]):
    chunk_count += len(chunk)
    valid = chunk.dropna(subset=["TransactionID", "customer_id", "ts"])
    for _, row in valid.iterrows():
        card_id = f"{row['customer_id']}-K1"
        tx_id = str(int(row["TransactionID"]))
        ts = str(row["ts"])
        if card_id not in card_tx_map:
            card_tx_map[card_id] = []
        card_tx_map[card_id].append((ts, tx_id))

next_edges = []
for card_id, tx_list in card_tx_map.items():
    # Sort by timestamp
    tx_list.sort(key=lambda x: x[0])
    for i in range(len(tx_list) - 1):
        from_tx = tx_list[i][1]
        to_tx = tx_list[i+1][1]
        next_edges.append((from_tx, to_tx))

print(f"Total cards processed: {len(card_tx_map)}")
print(f"Total transactions mapped: {chunk_count}")
print(f"Total NEXT edges derived: {len(next_edges)}")
print("Sample NEXT edges:", next_edges[:5])
