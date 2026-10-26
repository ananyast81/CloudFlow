"""Synthetic examples; no personal or externally sourced data."""
from pathlib import Path

import numpy as np
import pandas as pd


def main():
    root = Path(__file__).resolve().parents[1] / "data"
    root.mkdir(exist_ok=True)
    rng = np.random.default_rng(42)
    count = 180
    age = rng.integers(18, 70, count)
    charges = rng.uniform(20, 110, count).round(2)
    contract = rng.choice(["Monthly", "Annual"], count)
    churn = np.where(((charges > 64) & (contract == "Monthly")) | (age < 27), "Yes", "No")
    frame = pd.DataFrame({"Age": age, "MonthlyCharges": charges, "Contract": contract, "Churn": churn})
    frame.loc[3, "Age"] = np.nan
    frame.loc[5, "Contract"] = None
    frame.to_csv(root / "churn.csv", index=False)
    area = rng.normal(1200, 230, 160).round()
    rooms = rng.integers(1, 6, 160)
    houses = pd.DataFrame({"area": area, "rooms": rooms,
        "neighborhood": rng.choice(["North", "South", "Central"], 160),
        "price": (50000 + 130 * area + 10000 * rooms + rng.normal(0, 1500, 160)).round(2)})
    houses.to_csv(root / "housing.csv", index=False)
    print("Created data/churn.csv and data/housing.csv (synthetic).")


if __name__ == "__main__":
    main()
