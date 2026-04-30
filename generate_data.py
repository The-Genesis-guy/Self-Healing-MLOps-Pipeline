import numpy as np
import pandas as pd

np.random.seed(42)

def generate_fraud_data(n=1000):
    transaction_amount   = np.random.exponential(scale=200, size=n)
    hour_of_day          = np.random.choice(range(24), size=n, p=[
        0.02, 0.01, 0.01, 0.01, 0.01, 0.02,
        0.04, 0.06, 0.07, 0.07, 0.07, 0.07,
        0.07, 0.07, 0.07, 0.06, 0.04, 0.04,
        0.04, 0.04, 0.04, 0.03, 0.02, 0.02
    ])
    distance_from_home   = np.random.exponential(scale=30, size=n)
    num_transactions_24h = np.random.poisson(lam=3, size=n)
    is_foreign           = np.random.choice([0, 1], size=n, p=[0.9, 0.1])
    merchant_category    = np.random.choice(
        ["grocery", "restaurant", "gas", "online", "travel"],
        size=n, p=[0.35, 0.25, 0.15, 0.20, 0.05]
    )

    # Simple OR-based risk — fires more often, gives enough fraud cases to train on
    is_high_risk = (
        (is_foreign == 1)          |   # foreign card — 10% of transactions
        (hour_of_day < 5)          |   # late night — ~6% of transactions
        (num_transactions_24h > 5)     # many rapid transactions — ~8% of transactions
    )
    # High risk = 45% fraud | Low risk = 2% fraud  →  expect ~10-12% overall fraud
    fraud_prob = np.where(is_high_risk, 0.45, 0.02)
    is_fraud = (np.random.random(n) < fraud_prob).astype(int)

    return pd.DataFrame({
        "transaction_amount": transaction_amount,
        "hour_of_day": hour_of_day,
        "distance_from_home": distance_from_home,
        "num_transactions_24h": num_transactions_24h,
        "is_foreign": is_foreign,
        "merchant_category": merchant_category,
        "is_fraud": is_fraud
    })

if __name__ == "__main__":
    df = generate_fraud_data(n=1000)
    df.to_csv("data_training.csv", index=False)
    print(f"Generated {len(df)} rows")
    print(f"Fraud rate: {df['is_fraud'].mean():.1%}")
    print(df.head())
