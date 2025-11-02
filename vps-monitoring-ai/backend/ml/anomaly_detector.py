"""
Machine Learning Anomaly Detection System
Combines Isolation Forest (for outlier detection) and LSTM (for time-series patterns)
Centralized training on master node
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from tensorflow import keras
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout
from typing import Dict, List, Any, Tuple, Optional
import joblib
import os
from datetime import datetime, timedelta
from loguru import logger

from backend.config.settings import settings


class AnomalyDetector:
    """
    Hybrid anomaly detection combining:
    - Isolation Forest: Unsupervised outlier detection
    - LSTM: Time-series pattern recognition
    """
    
    def __init__(self):
        self.isolation_forest = None
        self.lstm_model = None
        self.scaler = StandardScaler()
        self.model_path = settings.ml_model_path
        self.sequence_length = 60  # Use last 60 data points for LSTM
        
        os.makedirs(self.model_path, exist_ok=True)
        
        logger.info("Anomaly Detector initialized")
    
    def train_isolation_forest(self, training_data: pd.DataFrame) -> Dict[str, Any]:
        """
        Train Isolation Forest model on historical metrics
        
        Args:
            training_data: DataFrame with columns [cpu_percent, memory_percent, disk_percent, ...]
        
        Returns:
            Training metrics
        """
        logger.info(f"Training Isolation Forest with {len(training_data)} samples")
        
        if len(training_data) < settings.min_training_samples:
            logger.warning(f"Insufficient training data: {len(training_data)} < {settings.min_training_samples}")
            return {"status": "insufficient_data", "samples": len(training_data)}
        
        # Select features
        features = ['cpu_percent', 'memory_percent', 'disk_percent', 
                   'memory_used_mb', 'disk_used_gb']
        X = training_data[features].values
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        
        # Train Isolation Forest
        self.isolation_forest = IsolationForest(
            contamination=0.1,  # Expect 10% anomalies
            random_state=42,
            n_estimators=100,
            max_samples='auto',
            n_jobs=-1
        )
        
        self.isolation_forest.fit(X_scaled)
        
        # Calculate training metrics
        predictions = self.isolation_forest.predict(X_scaled)
        anomaly_count = np.sum(predictions == -1)
        anomaly_percentage = (anomaly_count / len(X)) * 100
        
        # Save model
        model_file = os.path.join(self.model_path, 'isolation_forest.joblib')
        scaler_file = os.path.join(self.model_path, 'scaler.joblib')
        
        joblib.dump(self.isolation_forest, model_file)
        joblib.dump(self.scaler, scaler_file)
        
        logger.success(f"Isolation Forest trained: {anomaly_percentage:.1f}% anomalies detected")
        
        return {
            "status": "success",
            "samples": len(X),
            "anomaly_count": int(anomaly_count),
            "anomaly_percentage": float(anomaly_percentage),
            "model_file": model_file,
            "trained_at": datetime.utcnow().isoformat()
        }
    
    def train_lstm(self, time_series_data: pd.DataFrame) -> Dict[str, Any]:
        """
        Train LSTM model for time-series anomaly detection
        
        Args:
            time_series_data: DataFrame with timestamp and metrics columns
        
        Returns:
            Training metrics
        """
        logger.info(f"Training LSTM with {len(time_series_data)} time-series samples")
        
        if len(time_series_data) < self.sequence_length * 2:
            logger.warning("Insufficient data for LSTM training")
            return {"status": "insufficient_data"}
        
        # Prepare sequences
        features = ['cpu_percent', 'memory_percent', 'disk_percent']
        data = time_series_data[features].values
        
        X, y = self._create_sequences(data)
        
        # Split train/validation
        split_idx = int(len(X) * 0.8)
        X_train, X_val = X[:split_idx], X[split_idx:]
        y_train, y_val = y[:split_idx], y[split_idx:]
        
        # Build LSTM model
        self.lstm_model = Sequential([
            LSTM(64, return_sequences=True, input_shape=(self.sequence_length, len(features))),
            Dropout(0.2),
            LSTM(32, return_sequences=False),
            Dropout(0.2),
            Dense(16, activation='relu'),
            Dense(len(features), activation='linear')  # Predict next values
        ])
        
        self.lstm_model.compile(
            optimizer='adam',
            loss='mse',
            metrics=['mae']
        )
        
        # Train
        history = self.lstm_model.fit(
            X_train, y_train,
            validation_data=(X_val, y_val),
            epochs=50,
            batch_size=32,
            verbose=0,
            callbacks=[
                keras.callbacks.EarlyStopping(
                    patience=5,
                    restore_best_weights=True
                )
            ]
        )
        
        # Save model
        model_file = os.path.join(self.model_path, 'lstm_model.h5')
        self.lstm_model.save(model_file)
        
        val_loss = float(history.history['val_loss'][-1])
        val_mae = float(history.history['val_mae'][-1])
        
        logger.success(f"LSTM trained: val_loss={val_loss:.4f}, val_mae={val_mae:.4f}")
        
        return {
            "status": "success",
            "samples": len(X),
            "val_loss": val_loss,
            "val_mae": val_mae,
            "model_file": model_file,
            "trained_at": datetime.utcnow().isoformat()
        }
    
    def predict(self, current_metrics: Dict[str, float], 
                historical_sequence: Optional[List[Dict[str, float]]] = None) -> Dict[str, Any]:
        """
        Predict anomaly score for current metrics
        
        Args:
            current_metrics: Current system metrics
            historical_sequence: Recent historical data for LSTM
        
        Returns:
            Anomaly prediction with scores
        """
        result = {
            "is_anomaly": False,
            "anomaly_score": 0.0,
            "confidence": 0.0,
            "isolation_forest_score": None,
            "lstm_score": None,
            "prediction": None
        }
        
        # Load models if not loaded
        if self.isolation_forest is None:
            self._load_models()
        
        # Isolation Forest prediction
        if self.isolation_forest is not None:
            features = np.array([[
                current_metrics.get('cpu_percent', 0),
                current_metrics.get('memory_percent', 0),
                current_metrics.get('disk_percent', 0),
                current_metrics.get('memory_used_mb', 0),
                current_metrics.get('disk_used_gb', 0)
            ]])
            
            features_scaled = self.scaler.transform(features)
            if_prediction = self.isolation_forest.predict(features_scaled)[0]
            if_score = self.isolation_forest.score_samples(features_scaled)[0]
            
            result["isolation_forest_score"] = float(if_score)
            result["is_anomaly"] = (if_prediction == -1)
        
        # LSTM prediction
        if self.lstm_model is not None and historical_sequence and len(historical_sequence) >= self.sequence_length:
            try:
                sequence = np.array([[
                    item.get('cpu_percent', 0),
                    item.get('memory_percent', 0),
                    item.get('disk_percent', 0)
                ] for item in historical_sequence[-self.sequence_length:]])
                
                sequence = sequence.reshape(1, self.sequence_length, 3)
                prediction = self.lstm_model.predict(sequence, verbose=0)[0]
                
                # Calculate prediction error (anomaly score)
                actual = np.array([
                    current_metrics.get('cpu_percent', 0),
                    current_metrics.get('memory_percent', 0),
                    current_metrics.get('disk_percent', 0)
                ])
                
                error = np.abs(prediction - actual)
                lstm_score = float(np.mean(error))
                
                result["lstm_score"] = lstm_score
                result["prediction"] = {
                    "cpu_percent": float(prediction[0]),
                    "memory_percent": float(prediction[1]),
                    "disk_percent": float(prediction[2])
                }
                
                # LSTM anomaly if error > threshold
                if lstm_score > 15:  # 15% average error threshold
                    result["is_anomaly"] = True
            except Exception as e:
                logger.error(f"LSTM prediction error: {e}")
        
        # Combined anomaly score
        scores = []
        if result["isolation_forest_score"] is not None:
            # Normalize IF score to 0-1 range (higher = more anomalous)
            if_normalized = 1 / (1 + np.exp(-result["isolation_forest_score"]))
            scores.append(if_normalized)
        
        if result["lstm_score"] is not None:
            # Normalize LSTM score
            lstm_normalized = min(result["lstm_score"] / 30, 1.0)
            scores.append(lstm_normalized)
        
        if scores:
            result["anomaly_score"] = float(np.mean(scores))
            result["confidence"] = float(1 - np.std(scores)) if len(scores) > 1 else 0.8
        
        # Final decision
        result["is_anomaly"] = result["anomaly_score"] > settings.anomaly_threshold
        
        return result
    
    def _create_sequences(self, data: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Create sequences for LSTM training"""
        X, y = [], []
        for i in range(len(data) - self.sequence_length):
            X.append(data[i:i+self.sequence_length])
            y.append(data[i+self.sequence_length])
        return np.array(X), np.array(y)
    
    def _load_models(self):
        """Load pre-trained models from disk"""
        try:
            if_path = os.path.join(self.model_path, 'isolation_forest.joblib')
            scaler_path = os.path.join(self.model_path, 'scaler.joblib')
            lstm_path = os.path.join(self.model_path, 'lstm_model.h5')
            
            if os.path.exists(if_path):
                self.isolation_forest = joblib.load(if_path)
                self.scaler = joblib.load(scaler_path)
                logger.info("Isolation Forest model loaded")
            
            if os.path.exists(lstm_path):
                self.lstm_model = keras.models.load_model(lstm_path)
                logger.info("LSTM model loaded")
        
        except Exception as e:
            logger.error(f"Error loading models: {e}")
