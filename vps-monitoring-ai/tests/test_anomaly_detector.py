"""
Unit tests for AnomalyDetector
Tests training and prediction for Isolation Forest and LSTM models
"""
import pytest
import numpy as np
import pandas as pd
from unittest.mock import Mock, patch, MagicMock
import tempfile
import os

from backend.ml.anomaly_detector import AnomalyDetector


@pytest.mark.unit
class TestAnomalyDetector:
    """Test ML Anomaly Detection System"""
    
    def test_initialization(self, test_settings):
        """Test anomaly detector initialization"""
        with patch('backend.ml.anomaly_detector.settings', test_settings):
            detector = AnomalyDetector()
            
            assert detector.isolation_forest is None
            assert detector.lstm_model is None
            assert detector.scaler is not None
            assert detector.sequence_length == 60
    
    @pytest.mark.slow
    def test_train_isolation_forest_success(self, test_settings):
        """Test successful Isolation Forest training"""
        with patch('backend.ml.anomaly_detector.settings', test_settings):
            detector = AnomalyDetector()
            
            # Create training data
            np.random.seed(42)
            training_data = pd.DataFrame({
                'cpu_percent': np.random.normal(50, 20, 1500),
                'memory_percent': np.random.normal(60, 15, 1500),
                'disk_percent': np.random.normal(45, 10, 1500),
                'memory_used_mb': np.random.normal(4000, 1000, 1500),
                'disk_used_gb': np.random.normal(100, 30, 1500)
            })
            
            result = detector.train_isolation_forest(training_data)
            
            assert result['status'] == 'success'
            assert result['samples'] == 1500
            assert 'anomaly_count' in result
            assert 'anomaly_percentage' in result
            assert detector.isolation_forest is not None
    
    def test_train_isolation_forest_insufficient_data(self, test_settings):
        """Test Isolation Forest training with insufficient data"""
        with patch('backend.ml.anomaly_detector.settings', test_settings):
            detector = AnomalyDetector()
            
            # Create insufficient training data
            training_data = pd.DataFrame({
                'cpu_percent': [50, 60, 70],
                'memory_percent': [60, 65, 70],
                'disk_percent': [45, 50, 55],
                'memory_used_mb': [4000, 4200, 4400],
                'disk_used_gb': [100, 105, 110]
            })
            
            result = detector.train_isolation_forest(training_data)
            
            assert result['status'] == 'insufficient_data'
            assert result['samples'] == 3
    
    def test_train_isolation_forest_edge_case_all_zeros(self, test_settings):
        """Test Isolation Forest with all zero values (edge case)"""
        with patch('backend.ml.anomaly_detector.settings', test_settings):
            detector = AnomalyDetector()
            
            training_data = pd.DataFrame({
                'cpu_percent': [0] * 1500,
                'memory_percent': [0] * 1500,
                'disk_percent': [0] * 1500,
                'memory_used_mb': [0] * 1500,
                'disk_used_gb': [0] * 1500
            })
            
            result = detector.train_isolation_forest(training_data)
            
            assert result['status'] == 'success'
            assert result['samples'] == 1500
    
    def test_train_isolation_forest_edge_case_extreme_values(self, test_settings):
        """Test Isolation Forest with extreme values (edge case)"""
        with patch('backend.ml.anomaly_detector.settings', test_settings):
            detector = AnomalyDetector()
            
            # Mix of normal and extreme values
            cpu = [50] * 1400 + [100] * 100
            memory = [60] * 1400 + [100] * 100
            disk = [45] * 1450 + [99] * 50
            
            training_data = pd.DataFrame({
                'cpu_percent': cpu,
                'memory_percent': memory,
                'disk_percent': disk,
                'memory_used_mb': [4000] * 1500,
                'disk_used_gb': [100] * 1500
            })
            
            result = detector.train_isolation_forest(training_data)
            
            assert result['status'] == 'success'
            # Should detect the extreme values as anomalies
            assert result['anomaly_percentage'] > 5
    
    @pytest.mark.slow
    def test_train_lstm_success(self, test_settings):
        """Test successful LSTM training"""
        with patch('backend.ml.anomaly_detector.settings', test_settings):
            detector = AnomalyDetector()
            
            # Create time series data
            np.random.seed(42)
            time_series_data = pd.DataFrame({
                'cpu_percent': np.sin(np.linspace(0, 10, 500)) * 20 + 50 + np.random.normal(0, 5, 500),
                'memory_percent': np.cos(np.linspace(0, 10, 500)) * 15 + 60 + np.random.normal(0, 3, 500),
                'disk_percent': np.linspace(40, 50, 500) + np.random.normal(0, 2, 500)
            })
            
            result = detector.train_lstm(time_series_data)
            
            assert result['status'] == 'success'
            assert 'val_loss' in result
            assert 'val_mae' in result
            assert detector.lstm_model is not None
    
    def test_train_lstm_insufficient_data(self, test_settings):
        """Test LSTM training with insufficient data"""
        with patch('backend.ml.anomaly_detector.settings', test_settings):
            detector = AnomalyDetector()
            
            # Create insufficient data (less than sequence_length * 2)
            time_series_data = pd.DataFrame({
                'cpu_percent': [50, 55, 60],
                'memory_percent': [60, 62, 65],
                'disk_percent': [45, 46, 47]
            })
            
            result = detector.train_lstm(time_series_data)
            
            assert result['status'] == 'insufficient_data'
    
    def test_train_lstm_edge_case_constant_values(self, test_settings):
        """Test LSTM training with constant values (edge case)"""
        with patch('backend.ml.anomaly_detector.settings', test_settings):
            detector = AnomalyDetector()
            
            # Constant values throughout
            time_series_data = pd.DataFrame({
                'cpu_percent': [50.0] * 300,
                'memory_percent': [60.0] * 300,
                'disk_percent': [45.0] * 300
            })
            
            result = detector.train_lstm(time_series_data)
            
            # Should still train but with low loss (predictable pattern)
            assert result['status'] == 'success'
    
    def test_predict_with_isolation_forest_only(self, test_settings):
        """Test prediction using only Isolation Forest"""
        with patch('backend.ml.anomaly_detector.settings', test_settings):
            detector = AnomalyDetector()
            
            # Train model
            np.random.seed(42)
            training_data = pd.DataFrame({
                'cpu_percent': np.random.normal(50, 20, 1500),
                'memory_percent': np.random.normal(60, 15, 1500),
                'disk_percent': np.random.normal(45, 10, 1500),
                'memory_used_mb': np.random.normal(4000, 1000, 1500),
                'disk_used_gb': np.random.normal(100, 30, 1500)
            })
            detector.train_isolation_forest(training_data)
            
            # Predict on normal metrics
            current_metrics = {
                'cpu_percent': 55.0,
                'memory_percent': 65.0,
                'disk_percent': 48.0,
                'memory_used_mb': 4200,
                'disk_used_gb': 105
            }
            
            result = detector.predict(current_metrics)
            
            assert 'is_anomaly' in result
            assert 'anomaly_score' in result
            assert 'isolation_forest_score' in result
            assert result['lstm_score'] is None
    
    def test_predict_anomaly_detection(self, test_settings):
        """Test anomaly detection with extreme values"""
        with patch('backend.ml.anomaly_detector.settings', test_settings):
            detector = AnomalyDetector()
            
            # Train with normal data
            np.random.seed(42)
            training_data = pd.DataFrame({
                'cpu_percent': np.random.normal(50, 10, 1500),
                'memory_percent': np.random.normal(60, 10, 1500),
                'disk_percent': np.random.normal(45, 5, 1500),
                'memory_used_mb': np.random.normal(4000, 500, 1500),
                'disk_used_gb': np.random.normal(100, 20, 1500)
            })
            detector.train_isolation_forest(training_data)
            
            # Predict on anomalous metrics
            anomalous_metrics = {
                'cpu_percent': 98.0,  # Extreme
                'memory_percent': 95.0,  # Extreme
                'disk_percent': 99.0,  # Extreme
                'memory_used_mb': 8000,
                'disk_used_gb': 200
            }
            
            result = detector.predict(anomalous_metrics)
            
            # Should detect as anomaly
            assert result['is_anomaly'] is True
            assert result['anomaly_score'] > 0.5
    
    @pytest.mark.slow
    def test_predict_with_lstm_and_isolation_forest(self, test_settings):
        """Test prediction using both models"""
        with patch('backend.ml.anomaly_detector.settings', test_settings):
            detector = AnomalyDetector()
            
            # Train Isolation Forest
            np.random.seed(42)
            training_data = pd.DataFrame({
                'cpu_percent': np.random.normal(50, 20, 1500),
                'memory_percent': np.random.normal(60, 15, 1500),
                'disk_percent': np.random.normal(45, 10, 1500),
                'memory_used_mb': np.random.normal(4000, 1000, 1500),
                'disk_used_gb': np.random.normal(100, 30, 1500)
            })
            detector.train_isolation_forest(training_data)
            
            # Train LSTM
            time_series_data = pd.DataFrame({
                'cpu_percent': np.sin(np.linspace(0, 10, 300)) * 20 + 50,
                'memory_percent': np.cos(np.linspace(0, 10, 300)) * 15 + 60,
                'disk_percent': np.linspace(40, 50, 300)
            })
            detector.train_lstm(time_series_data)
            
            # Create historical sequence
            historical_sequence = [
                {'cpu_percent': 50 + i, 'memory_percent': 60 + i, 'disk_percent': 45 + i * 0.1}
                for i in range(60)
            ]
            
            current_metrics = {
                'cpu_percent': 110.0,  # Continue trend
                'memory_percent': 120.0,
                'disk_percent': 51.0,
                'memory_used_mb': 4500,
                'disk_used_gb': 110
            }
            
            result = detector.predict(current_metrics, historical_sequence)
            
            assert result['isolation_forest_score'] is not None
            assert result['lstm_score'] is not None
            assert 'prediction' in result
            assert result['confidence'] > 0
    
    def test_predict_with_insufficient_historical_data(self, test_settings):
        """Test prediction with insufficient historical data for LSTM"""
        with patch('backend.ml.anomaly_detector.settings', test_settings):
            detector = AnomalyDetector()
            
            # Train LSTM
            time_series_data = pd.DataFrame({
                'cpu_percent': [50.0] * 300,
                'memory_percent': [60.0] * 300,
                'disk_percent': [45.0] * 300
            })
            detector.train_lstm(time_series_data)
            
            # Insufficient historical data (less than sequence_length)
            historical_sequence = [
                {'cpu_percent': 50.0, 'memory_percent': 60.0, 'disk_percent': 45.0}
                for _ in range(30)  # Less than 60
            ]
            
            current_metrics = {
                'cpu_percent': 55.0,
                'memory_percent': 65.0,
                'disk_percent': 48.0
            }
            
            result = detector.predict(current_metrics, historical_sequence)
            
            # Should not use LSTM
            assert result['lstm_score'] is None
    
    def test_predict_without_trained_models(self, test_settings):
        """Test prediction without any trained models (edge case)"""
        with patch('backend.ml.anomaly_detector.settings', test_settings):
            detector = AnomalyDetector()
            
            current_metrics = {
                'cpu_percent': 55.0,
                'memory_percent': 65.0,
                'disk_percent': 48.0,
                'memory_used_mb': 4200,
                'disk_used_gb': 105
            }
            
            result = detector.predict(current_metrics)
            
            assert result['is_anomaly'] is False
            assert result['anomaly_score'] == 0.0
            assert result['isolation_forest_score'] is None
    
    def test_predict_with_missing_metrics(self, test_settings):
        """Test prediction with missing metric values (edge case)"""
        with patch('backend.ml.anomaly_detector.settings', test_settings):
            detector = AnomalyDetector()
            
            # Train model
            np.random.seed(42)
            training_data = pd.DataFrame({
                'cpu_percent': np.random.normal(50, 20, 1500),
                'memory_percent': np.random.normal(60, 15, 1500),
                'disk_percent': np.random.normal(45, 10, 1500),
                'memory_used_mb': np.random.normal(4000, 1000, 1500),
                'disk_used_gb': np.random.normal(100, 30, 1500)
            })
            detector.train_isolation_forest(training_data)
            
            # Metrics with missing values
            current_metrics = {
                'cpu_percent': 55.0,
                'memory_percent': 65.0
                # Missing disk_percent, memory_used_mb, disk_used_gb
            }
            
            result = detector.predict(current_metrics)
            
            # Should handle missing values by using defaults (0)
            assert 'is_anomaly' in result
            assert 'anomaly_score' in result
    
    def test_predict_edge_case_negative_values(self, test_settings):
        """Test prediction with negative values (edge case)"""
        with patch('backend.ml.anomaly_detector.settings', test_settings):
            detector = AnomalyDetector()
            
            training_data = pd.DataFrame({
                'cpu_percent': np.random.normal(50, 20, 1500),
                'memory_percent': np.random.normal(60, 15, 1500),
                'disk_percent': np.random.normal(45, 10, 1500),
                'memory_used_mb': np.random.normal(4000, 1000, 1500),
                'disk_used_gb': np.random.normal(100, 30, 1500)
            })
            detector.train_isolation_forest(training_data)
            
            # Negative values (shouldn't happen but edge case)
            current_metrics = {
                'cpu_percent': -10.0,
                'memory_percent': -5.0,
                'disk_percent': -2.0,
                'memory_used_mb': -100,
                'disk_used_gb': -50
            }
            
            result = detector.predict(current_metrics)
            
            # Should detect as anomaly
            assert result['is_anomaly'] is True
    
    def test_create_sequences(self, test_settings):
        """Test LSTM sequence creation"""
        with patch('backend.ml.anomaly_detector.settings', test_settings):
            detector = AnomalyDetector()
            
            # Create sample data
            data = np.array([[i, i*2, i*3] for i in range(100)])
            
            X, y = detector._create_sequences(data)
            
            assert X.shape == (40, 60, 3)  # 100 - 60 = 40 sequences
            assert y.shape == (40, 3)
            assert np.array_equal(y[0], data[60])
    
    @patch('backend.ml.anomaly_detector.joblib.load')
    @patch('backend.ml.anomaly_detector.keras.models.load_model')
    @patch('backend.ml.anomaly_detector.os.path.exists')
    def test_load_models(self, mock_exists, mock_keras_load, mock_joblib_load, test_settings):
        """Test loading pre-trained models from disk"""
        with patch('backend.ml.anomaly_detector.settings', test_settings):
            mock_exists.return_value = True
            mock_joblib_load.side_effect = [Mock(), Mock()]  # isolation_forest, scaler
            mock_keras_load.return_value = Mock()
            
            detector = AnomalyDetector()
            detector._load_models()
            
            assert detector.isolation_forest is not None
            assert detector.scaler is not None
            assert detector.lstm_model is not None
    
    @patch('backend.ml.anomaly_detector.os.path.exists')
    def test_load_models_files_not_exist(self, mock_exists, test_settings):
        """Test loading models when files don't exist"""
        with patch('backend.ml.anomaly_detector.settings', test_settings):
            mock_exists.return_value = False
            
            detector = AnomalyDetector()
            detector._load_models()
            
            # Should remain None
            assert detector.isolation_forest is None
            assert detector.lstm_model is None
    
    def test_lstm_prediction_error_handling(self, test_settings):
        """Test LSTM prediction error handling"""
        with patch('backend.ml.anomaly_detector.settings', test_settings):
            detector = AnomalyDetector()
            
            # Mock LSTM model that raises exception
            detector.lstm_model = Mock()
            detector.lstm_model.predict = Mock(side_effect=Exception("LSTM error"))
            
            historical_sequence = [
                {'cpu_percent': 50.0, 'memory_percent': 60.0, 'disk_percent': 45.0}
                for _ in range(60)
            ]
            
            current_metrics = {
                'cpu_percent': 55.0,
                'memory_percent': 65.0,
                'disk_percent': 48.0
            }
            
            result = detector.predict(current_metrics, historical_sequence)
            
            # Should handle error gracefully
            assert result['lstm_score'] is None
