import os

os.environ["MPLBACKEND"] = "Agg"
os.environ["CLOUDFLOW_AUTO_WORKER"] = "false"

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from api.app import create_app
from shared.config import Settings


@pytest.fixture
def settings(tmp_path):
    return Settings(workspace=tmp_path / "workspace", auto_worker=False)


@pytest.fixture
def client(settings):
    with TestClient(create_app(settings)) as client:
        yield client


@pytest.fixture
def classification_data():
    rng = np.random.default_rng(42)
    count = 100
    age = rng.integers(18, 70, count)
    charge = rng.uniform(20, 110, count)
    contract = rng.choice(["Monthly", "Annual"], count)
    churn = np.where((charge > 64) & (contract == "Monthly") | (age < 27), "Yes", "No")
    frame = pd.DataFrame({"customer_id": [f"C{i}" for i in range(count)], "Age": age,
                          "MonthlyCharges": charge, "Contract": contract, "Churn": churn})
    frame.loc[3, "Age"] = np.nan
    frame.loc[4, "Contract"] = None
    return frame


@pytest.fixture
def regression_data():
    rng = np.random.default_rng(7)
    size = rng.normal(1200, 200, 90)
    rooms = rng.integers(1, 6, 90)
    return pd.DataFrame({"area": size, "rooms": rooms,
        "neighborhood": rng.choice(["North", "South"], 90),
        "price": 50000 + 130 * size + 10000 * rooms + rng.normal(0, 1000, 90)})
