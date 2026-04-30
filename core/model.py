import logging
import pickle
import numpy as np
import pandas as pd
from pathlib import Path
from dataclasses import dataclass
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, f1_score

logger = logging.getLogger(__name__)

@dataclass
class ModelReport:
    accuracy: float
    f1_score: float
    num_training_rows: int
    feature_names: list

class Model:
    def __init__(self, n_estimators=100, random_state=42):
        self.clf = RandomForestClassifier(
            n_estimators=n_estimators,
            random_state=random_state,
            class_weight='balanced' 
        )
        self.feature_names = None
        self.is_trained = False

    def train(self, df: pd.DataFrame, target_column: str) -> ModelReport:
        """
        Train on a DataFrame.
        Splits into train/test internally so we can report honest accuracy.
        """
        X = df.drop(columns=[target_column])
        y = df[target_column]

        self.feature_names = X.columns.tolist()

        # 80% train, 20% test
        # random_state=42 means the split is always the same — reproducible
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )

        self.clf.fit(X_train, y_train)
        self.is_trained = True

        # Evaluate on the held-out test set.
        # For imbalanced fraud detection, the default 0.5 threshold is too conservative —
        # the model never reaches 50% confidence on rare fraud cases.
        # 0.3 threshold: predict fraud if model is at least 30% confident.
        fraud_proba = self.clf.predict_proba(X_test)[:, 1]
        predictions = (fraud_proba >= 0.3).astype(int)
        acc = accuracy_score(y_test, predictions)
        f1 = f1_score(y_test, predictions, zero_division=0)

        return ModelReport(
            accuracy=round(acc, 4),
            f1_score=round(f1, 4),
            num_training_rows=len(X_train),
            feature_names=self.feature_names
        )

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        if not self.is_trained:
            raise RuntimeError("Model has not been trained yet.")
        X = df[self.feature_names]
        return self.clf.predict(X)

    def save(self, path: str):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump(self, f)
        logger.info(f"Model saved to {path}")

    @staticmethod
    def load(path: str) -> "Model":
        with open(path, "rb") as f:
            model = pickle.load(f)
        logger.info(f"Model loaded from {path}")
        return model