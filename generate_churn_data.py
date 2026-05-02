# generate_churn_data.py

import numpy as np
import pandas as pd

np.random.seed(42)

def generate_churn_data(n=1000):
    # Customer features
    tenure_months        = np.random.randint(1, 72, size=n)
    monthly_charges      = np.random.normal(65, 30, size=n).clip(20, 150)
    num_support_calls    = np.random.poisson(lam=2, size=n)
    contract_type        = np.random.choice(['monthly', 'yearly', 'two_year'], size=n, p=[0.5, 0.3, 0.2])
    num_products         = np.random.randint(1, 5, size=n)

    # Causal churn signal
    # Short tenure + monthly contract + many support calls = high churn risk
    is_high_risk = (
        (tenure_months < 12)        |
        (num_support_calls > 4)     |
        (monthly_charges > 100)
    )
    churn_prob = np.where(is_high_risk, 0.45, 0.05)
    churned = (np.random.random(n) < churn_prob).astype(int)

    df = pd.DataFrame({
        'tenure_months':     tenure_months,
        'monthly_charges':   monthly_charges.round(2),
        'num_support_calls': num_support_calls,
        'contract_type':     contract_type,
        'num_products':      num_products,
        'churned':           churned
    })

    df.to_csv('data_churn.csv', index=False)
    print(f"Generated {len(df)} rows")
    print(f"Churn rate: {df['churned'].mean():.1%}")
    print(df.head())

if __name__ == '__main__':
    generate_churn_data()