import pandas as pd
import json

base_dir = r"C:\Users\VIGNESH\.gemini\antigravity\scratch\FraudGraph-AI\dataset\HHGOA_IEEE"

# 1. Inspect closed_cases_history.csv
cc_df = pd.read_csv(f"{base_dir}\\closed_cases_history.csv")
print("=== CLOSED CASES HISTORY INSPECTION ===")
print("Total rows:", len(cc_df))
print("Sample rows:")
print(cc_df[["case_id", "customer_id", "card_id", "connected_card_ids"]].head(10))

print("\nNon-null card_id count:", cc_df["card_id"].dropna().count())
print("Unique card_id count:", cc_df["card_id"].nunique())
print("Non-null connected_card_ids count:", cc_df["connected_card_ids"].dropna().count())

connected_cards_list = []
for idx, val in cc_df["connected_card_ids"].dropna().items():
    cards = [c.strip() for c in str(val).split("|") if c.strip()]
    for c in cards:
        connected_cards_list.append((cc_df.loc[idx, "case_id"], c))

print("Total connected_card pairs extracted:", len(connected_cards_list))
print("Sample connected_card pairs:", connected_cards_list[:10])

# 2. Inspect OWNS in transactions.csv
print("\n=== OWNS INSPECTION IN TRANSACTIONS ===")
customer_card_pairs = set()
tx_chunk_count = 0
for chunk in pd.read_csv(f"{base_dir}\\transactions.csv", chunksize=100000, low_memory=False):
    tx_chunk_count += len(chunk)
    if "customer_id" in chunk.columns and "card1" in chunk.columns:
        valid = chunk.dropna(subset=["customer_id", "card1"])
        for _, row in valid.iterrows():
            cid = str(row["customer_id"])
            # Is card_id in transactions structured as customer_id-K1 or derived from card1?
            c1 = str(int(row["card1"]))
            card_id = f"{cid}-K1"
            customer_card_pairs.add((cid, card_id))

print(f"Total transactions scanned: {tx_chunk_count}")
print(f"Unique Customer-Card pairs found in transactions: {len(customer_card_pairs)}")

# Check closed cases customer-card pairs
cc_pairs = set(zip(cc_df["customer_id"].astype(str), cc_df["card_id"].astype(str)))
print(f"Unique Customer-Card pairs in closed cases: {len(cc_pairs)}")
