import numpy as np
import pandas as pd


def make_training_data(n: int = 1000, seed: int = 42) -> pd.DataFrame:
    np.random.seed(seed)
    return pd.DataFrame({
        'age':                np.random.normal(34, 10, n).clip(18, 80).astype(int),
        'income':             np.random.normal(55000, 15000, n).clip(10000, 200000),
        'credit_score':       np.random.normal(680, 80, n).clip(300, 850).astype(int),
        'transaction_amount': np.random.exponential(150, n).clip(1, 5000),
        'num_transactions':   np.random.poisson(8, n),
        'region':             np.random.choice(['north', 'south', 'east', 'west'], n, p=[0.3, 0.3, 0.2, 0.2]),
        'account_type':       np.random.choice(['savings', 'checking', 'premium'], n, p=[0.5, 0.35, 0.15]),
        'is_fraud':           np.random.choice([0, 1], n, p=[0.97, 0.03]),
    })


def make_serving_data_stable(n: int = 500, seed: int = 99) -> pd.DataFrame:
    np.random.seed(seed)
    return pd.DataFrame({
        'age':                np.random.normal(35, 10, n).clip(18, 80).astype(int),
        'income':             np.random.normal(56000, 15000, n).clip(10000, 200000),
        'credit_score':       np.random.normal(675, 80, n).clip(300, 850).astype(int),
        'transaction_amount': np.random.exponential(155, n).clip(1, 5000),
        'num_transactions':   np.random.poisson(8, n),
        'region':             np.random.choice(['north', 'south', 'east', 'west'], n, p=[0.3, 0.3, 0.2, 0.2]),
        'account_type':       np.random.choice(['savings', 'checking', 'premium'], n, p=[0.5, 0.35, 0.15]),
        'is_fraud':           np.random.choice([0, 1], n, p=[0.97, 0.03]),
    })


def make_serving_data_drifted(n: int = 500, seed: int = 77) -> pd.DataFrame:
    np.random.seed(seed)
    df = pd.DataFrame({
        'age':                np.random.normal(52, 12, n).clip(18, 80).astype(int),
        'income':             np.random.normal(55000, 15000, n).clip(10000, 200000),
        'credit_score':       np.random.normal(620, 90, n).clip(300, 850).astype(int),
        'transaction_amount': np.random.exponential(600, n).clip(1, 20000),
        'num_transactions':   np.random.poisson(8, n),
        'region':             np.random.choice(['north', 'south', 'east', 'international'], n, p=[0.25, 0.25, 0.25, 0.25]),
        'account_type':       np.random.choice(['savings', 'checking', 'premium'], n, p=[0.5, 0.35, 0.15]),
        'is_fraud':           np.random.choice([0, 1], n, p=[0.97, 0.03]),
    })
    null_idx = np.random.choice(df.index, size=int(n * 0.30), replace=False)
    df.loc[null_idx, 'income'] = np.nan
    return df


def make_schema_broken_data(n: int = 500, seed: int = 55) -> pd.DataFrame:
    np.random.seed(seed)
    return pd.DataFrame({
        'age':                [str(x) for x in np.random.normal(34, 10, n).clip(18, 80).astype(int)],
        'income':             np.random.normal(55000, 15000, n).clip(10000, 200000),
        'transaction_amount': np.random.exponential(150, n).clip(1, 5000),
        'num_transactions':   np.random.poisson(8, n),
        'region':             np.random.choice(['north', 'south', 'east', 'west'], n),
        'account_type':       np.random.choice(['savings', 'checking', 'premium'], n),
        'is_fraud':           np.random.choice([0, 1], n, p=[0.97, 0.03]),
        'unexpected_col':     np.random.random(n),
    })
