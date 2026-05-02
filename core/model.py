import logging
import pickle
import joblib
import numpy as np
import pandas as pd
from pathlib import Path
from dataclasses import dataclass

from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
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
        # The new scikit-learn Pipeline will be stored here
        self.pipeline = None
        
        # Legacy support (for older models trained before the pipeline upgrade)
        self.rf = RandomForestClassifier(
            n_estimators=n_estimators,
            random_state=random_state,
            class_weight='balanced'
        )
        self.feature_names = None
        self.is_trained = False
        self.is_pipeline = False

    def train(self, df: pd.DataFrame, target_column: str, categorical_columns: list = None) -> ModelReport:
        """
        Train a modern Pipeline that handles imputation and encoding natively.
        """
        X = df.drop(columns=[target_column])
        y = df[target_column]

        self.feature_names = X.columns.tolist()

        numeric_features = [c for c in X.columns if c not in (categorical_columns or [])]
        categorical_features = categorical_columns or []

        numeric_transformer = Pipeline(steps=[
            ('imputer', SimpleImputer(strategy='median')),
            ('scaler', StandardScaler())
        ])

        categorical_transformer = Pipeline(steps=[
            ('imputer', SimpleImputer(strategy='constant', fill_value='missing')),
            ('onehot', OneHotEncoder(handle_unknown='ignore'))
        ])

        preprocessor = ColumnTransformer(transformers=[
            ('num', numeric_transformer, numeric_features),
            ('cat', categorical_transformer, categorical_features)
        ])

        self.pipeline = Pipeline(steps=[
            ('preprocessor', preprocessor),
            ('classifier', RandomForestClassifier(n_estimators=100, class_weight='balanced', random_state=42))
        ])

        # 80% train, 20% test
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )

        self.pipeline.fit(X_train, y_train)
        
        # Update flags
        self.is_trained = True
        self.is_pipeline = True

        # Evaluate (using 0.3 threshold logic from before)
        fraud_proba = self.pipeline.predict_proba(X_test)[:, 1]
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
            
        if self.is_pipeline:
            # New Pipeline way
            return self.pipeline.predict(df)
        else:
            # Legacy fallback: Models trained with cat.codes previously 
            # Note: The old pipeline expected the same columns as training.
            X = df[self.feature_names]
            return self.rf.predict(X)

    def save(self, path: str):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        # Pickle the entire Model object to preserve flags and states
        with open(path, "wb") as f:
            pickle.dump(self, f)
        logger.info(f"Model saved to {path}")

    @staticmethod
    def load(path: str) -> "Model":
        with open(path, "rb") as f:
            model = pickle.load(f)
        logger.info(f"Model loaded from {path}")
        return model