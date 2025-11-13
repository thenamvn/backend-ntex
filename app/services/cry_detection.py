import os
import numpy as np
import librosa
import matplotlib.pyplot as plt
from pathlib import Path
from ultralytics import YOLO
import tempfile

class CryDetectionService:
    """
    Baby cry detection using YOLOv8 classification on spectrograms.
    Model trained to classify audio into: InfantCry or Snoring
    """
    
    def __init__(self, model_path: str = "models/best.pt"):
        """
        Initialize the cry detection service with YOLOv8 model.
        
        Args:
            model_path: Path to trained YOLOv8 classification model
        """
        self.model_path = model_path
        self.model = None
        self.classes = ["InfantCry", "Snoring"]  # Model output classes
        
        # Spectrogram parameters (must match training config)
        self.SR = 16000
        self.N_MELS = 128
        self.HOP_LENGTH = 320
        self.WIN_LENGTH = 640
        self.FMIN = 50
        self.FMAX = 8000
        self.DURATION_TARGET = 10.0  # seconds
        self.IMGSZ = 224
        
        self._load_model()
    
    def _load_model(self):
        """Load the YOLOv8 classification model."""
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"Model file not found: {self.model_path}")
        
        try:
            self.model = YOLO(self.model_path)
            print(f"✅ YOLOv8 cry detection model loaded from {self.model_path}")
        except Exception as e:
            raise RuntimeError(f"Failed to load YOLOv8 model: {e}")
    
    def _load_audio_mono(self, path: str) -> np.ndarray:
        """
        Load audio file and convert to mono with target duration.
        
        Args:
            path: Path to audio file
            
        Returns:
            Audio waveform as numpy array
        """
        try:
            # Load audio
            y, orig_sr = librosa.load(path, sr=self.SR, mono=True)
            
            # Pad or trim to target duration
            target_len = int(self.DURATION_TARGET * self.SR)
            if len(y) < target_len:
                y = np.pad(y, (0, target_len - len(y)), mode='constant')
            else:
                y = y[:target_len]
            
            return y
        except Exception as e:
            raise RuntimeError(f"Error loading audio file: {e}")
    
    def _compute_logmel_spectrogram(self, y: np.ndarray) -> np.ndarray:
        """
        Compute log-mel spectrogram from audio waveform.
        
        Args:
            y: Audio waveform
            
        Returns:
            Log-mel spectrogram in dB
        """
        # Compute mel spectrogram
        S = librosa.feature.melspectrogram(
            y=y,
            sr=self.SR,
            n_fft=self.WIN_LENGTH,
            hop_length=self.HOP_LENGTH,
            win_length=self.WIN_LENGTH,
            n_mels=self.N_MELS,
            fmin=self.FMIN,
            fmax=self.FMAX,
            power=2.0
        )
        
        # Convert to dB scale
        S_db = librosa.power_to_db(S, ref=np.max)
        return S_db
    
    def _save_spectrogram(self, S_db: np.ndarray, output_path: str):
        """
        Save spectrogram as PNG image for YOLOv8 input.
        
        Args:
            S_db: Log-mel spectrogram in dB
            output_path: Path to save PNG file
        """
        # Create figure without axes
        fig = plt.figure(figsize=(self.IMGSZ/100, self.IMGSZ/100), dpi=100)
        ax = fig.add_axes([0, 0, 1, 1])
        ax.set_axis_off()
        
        # Plot spectrogram
        librosa.display.specshow(
            S_db,
            sr=self.SR,
            hop_length=self.HOP_LENGTH,
            x_axis=None,
            y_axis=None,
            cmap="magma"
        )
        
        # Save to file
        plt.savefig(output_path, bbox_inches='tight', pad_inches=0)
        plt.close(fig)
    
    def analyze(self, audio_path: str) -> bool:
        """
        Analyze audio file to detect if it contains baby crying.
        
        Process:
        1. Load audio file
        2. Convert to log-mel spectrogram
        3. Save as temporary PNG
        4. Run YOLOv8 classification
        5. Return True if predicted class is "InfantCry"
        
        Args:
            audio_path: Path to audio file (.wav, .mp3, etc.)
            
        Returns:
            True if baby crying detected (class = InfantCry), False otherwise
        """
        if self.model is None:
            raise RuntimeError("Model not loaded. Call _load_model() first.")
        
        temp_spectrogram_path = None
        
        try:
            # 1. Load audio
            y = self._load_audio_mono(audio_path)
            
            # 2. Compute spectrogram
            S_db = self._compute_logmel_spectrogram(y)
            
            # 3. Save spectrogram as temporary PNG
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
                temp_spectrogram_path = tmp_file.name
                self._save_spectrogram(S_db, temp_spectrogram_path)
            
            # 4. Run YOLOv8 prediction
            results = self.model.predict(
                source=temp_spectrogram_path,
                imgsz=self.IMGSZ,
                verbose=False
            )
            
            # 5. Parse results
            if len(results) > 0:
                result = results[0]
                
                # Get top prediction
                probs = result.probs  # Probs object
                top_class_idx = int(probs.top1)  # Index of top class
                top_class_name = self.classes[top_class_idx]
                confidence = float(probs.top1conf)  # Confidence score
                
                print(f"🔍 Cry detection: {top_class_name} (confidence: {confidence:.2f})")
                
                # Return True if InfantCry is detected
                return top_class_name == "InfantCry"
            
            return False
            
        except Exception as e:
            print(f"❌ Error during cry detection: {e}")
            return False
        
        finally:
            # Clean up temporary spectrogram file
            if temp_spectrogram_path and os.path.exists(temp_spectrogram_path):
                try:
                    os.remove(temp_spectrogram_path)
                except:
                    pass


# Singleton instance
cry_detection_service = CryDetectionService()