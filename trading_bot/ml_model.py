import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers
import pickle
import os
from datetime import datetime

class TradingModel:
    """Machine Learning model for trading decisions"""
    
    def __init__(self, model_path: str, scaler_path: str):
        self.model_path = model_path
        self.scaler_path = scaler_path
        self.model = None
        self.scaler = StandardScaler()
        self.feature_columns = None
        self.performance_history = []
        
    def build_model(self, input_shape: int) -> keras.Model:
        """Build neural network model"""
        model = keras.Sequential([
            layers.Dense(128, activation='relu', input_shape=(input_shape,)),
            layers.Dropout(0.3),
            layers.Dense(64, activation='relu'),
            layers.Dropout(0.2),
            layers.Dense(32, activation='relu'),
            layers.Dense(3, activation='softmax')  # 3 classes: BUY, HOLD, SELL
        ])
        
        model.compile(
            optimizer='adam',
            loss='sparse_categorical_crossentropy',
            metrics=['accuracy']
        )
        
        return model
    
    def train(self, df: pd.DataFrame, epochs: int = 50, batch_size: int = 32):
        """Train the model on historical data"""
        # Prepare features and labels
        self.feature_columns = [col for col in df.columns if col not in ['label', 'time', 'close']]
        X = df[self.feature_columns].values
        y = df['label'].values + 1  # Convert -1,0,1 to 0,1,2 for classification
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, shuffle=False
        )
        
        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # Build and train model
        self.model = self.build_model(X_train_scaled.shape[1])
        
        early_stopping = keras.callbacks.EarlyStopping(
            monitor='val_loss',
            patience=10,
            restore_best_weights=True
        )
        
        history = self.model.fit(
            X_train_scaled, y_train,
            validation_data=(X_test_scaled, y_test),
            epochs=epochs,
            batch_size=batch_size,
            callbacks=[early_stopping],
            verbose=1
        )
        
        # Evaluate
        test_loss, test_accuracy = self.model.evaluate(X_test_scaled, y_test, verbose=0)
        
        print(f"Training completed. Test accuracy: {test_accuracy:.4f}")
        
        # Save performance
        self.performance_history.append({
            'timestamp': datetime.now().isoformat(),
            'test_accuracy': test_accuracy,
            'test_loss': test_loss
        })
        
        # Save model and scaler
        self.save()
        
        return history
    
    def predict(self, features: pd.DataFrame) -> tuple:
        """Make prediction on new data"""
        if self.model is None:
            raise ValueError("Model not trained or loaded")
        
        X = features[self.feature_columns].values
        X_scaled = self.scaler.transform(X)
        
        predictions = self.model.predict(X_scaled, verbose=0)
        predicted_class = np.argmax(predictions, axis=1) - 1  # Convert back to -1,0,1
        confidence = np.max(predictions, axis=1)
        
        return predicted_class, confidence
    
    def save(self):
        """Save model and scaler"""
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        self.model.save(self.model_path)
        
        with open(self.scaler_path, 'wb') as f:
            pickle.dump(self.scaler, f)
        
        print(f"Model saved to {self.model_path}")
    
    def load(self) -> bool:
        """Load model and scaler"""
        try:
            self.model = keras.models.load_model(self.model_path)
            
            with open(self.scaler_path, 'rb') as f:
                self.scaler = pickle.load(f)
            
            print(f"Model loaded from {self.model_path}")
            return True
        except Exception as e:
            print(f"Failed to load model: {e}")
            return False
    
    def get_performance_metrics(self) -> dict:
        """Get model performance metrics"""
        if not self.performance_history:
            return {}
        
        latest = self.performance_history[-1]
        return {
            'latest_accuracy': latest['test_accuracy'],
            'latest_loss': latest['test_loss'],
            'training_count': len(self.performance_history),
            'last_trained': latest['timestamp']
        }
