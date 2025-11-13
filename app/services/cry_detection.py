import os
import numpy as np
import soundfile as sf
import librosa
import matplotlib.pyplot as plt
from pathlib import Path
from ultralytics import YOLO
from typing import Optional
import tempfile

from ..config import settings


class CryDetectionService:
    """
    Service for detecting baby crying in audio files using YOLOv8 model.
    """
    
    # Spectrogram parameters (matching your training config)
    SR = 16000
    N_MELS = 128
    HOP_LENGTH = 320
    WIN_LENGTH = 640
    FMIN, FMAX = 50, 8000
    DURATION_TARGET = 10.0
    IMGSZ = 224
    SAVE_DPI = 100
    
    def __init__(self):
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """Load the YOLOv8 cry detection model."""
        try:
            if os.path.exists(settings.cry_model_path):
                self.model = YOLO(settings.cry_model_path)
                print(f"✅ YOLOv8 cry detection model loaded from {settings.cry_model_path}")
            else:
                print(f"⚠️ Warning: Model file not found at {settings.cry_model_path}")
                print("Using fallback detection logic")
        except Exception as e:
            print(f"❌ Error loading model: {e}")
            print("Using fallback detection logic")
    
    def analyze(self, audio_path: str) -> bool:
        """
        Analyze an audio file to detect baby crying.
        
        Args:
            audio_path: Path to the audio file
        
        Returns:
            True if crying detected, False otherwise
        """
        try:
            if self.model is not None:
                return self._analyze_with_yolo(audio_path)
            else:
                return self._analyze_with_heuristics(audio_path)
        except Exception as e:
            print(f"Error analyzing audio: {e}")
            return False
    
    def _analyze_with_yolo(self, audio_path: str) -> bool:
        """
        Analyze audio using YOLOv8 model.
        
        Process:
        1. Load and preprocess audio
        2. Generate mel-spectrogram
        3. Save as temporary image
        4. Run YOLOv8 inference
        5. Return cry detection result
        """
        try:
            # Load audio
            y = self._load_audio(audio_path)
            
            # Compute spectrogram
            S_db = self._compute_spectrogram(y)
            
            # Create temporary spectrogram image
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
                temp_img_path = tmp_file.name
            
            try:
                self._save_spectrogram(S_db, temp_img_path)
                
                # Run YOLOv8 inference
                results = self.model.predict(temp_img_path, verbose=False)
                
                # Extract prediction
                probs = results[0].probs
                top_class = results[0].names[probs.top1]
                confidence = probs.top1conf.item()
                
                print(f"🔍 Cry detection: {top_class} (confidence: {confidence:.2f})")
                
                # Return True if "crying" class is detected with high confidence
                # Adjust class name and threshold based on your model
                is_crying = top_class.lower() in ['crying', 'cry', 'baby_cry'] and confidence > 0.5
                
                return is_crying
            finally:
                # Clean up temporary file
                if os.path.exists(temp_img_path):
                    os.unlink(temp_img_path)
                    
        except Exception as e:
            print(f"Error in YOLO analysis: {e}")
            return False
    
    def _load_audio(self, audio_path: str) -> np.ndarray:
        """Load and preprocess audio file."""
        try:
            # Load audio
            y, orig_sr = sf.read(audio_path, dtype='float32', always_2d=False)
        except:
            # Fallback to librosa
            y, orig_sr = librosa.load(audio_path, sr=None, mono=False)
        
        # Convert to mono
        if y.ndim > 1:
            y = np.mean(y, axis=1)
        
        # Resample if needed
        if orig_sr != self.SR:
            y = librosa.resample(y, orig_sr=orig_sr, target_sr=self.SR)
        
        # Pad or trim to target duration
        target_len = int(self.DURATION_TARGET * self.SR)
        if len(y) < target_len:
            y = np.pad(y, (0, target_len - len(y)), mode='constant')
        else:
            y = y[:target_len]
        
        return y
    
    def _compute_spectrogram(self, y: np.ndarray) -> np.ndarray:
        """Compute log-mel spectrogram."""
        S = librosa.feature.melspectrogram(
            y=y, sr=self.SR, n_fft=self.WIN_LENGTH, 
            hop_length=self.HOP_LENGTH, win_length=self.WIN_LENGTH,
            n_mels=self.N_MELS, fmin=self.FMIN, fmax=self.FMAX, power=2.0
        )
        S_db = librosa.power_to_db(S, ref=np.max)
        return S_db
    
    def _save_spectrogram(self, S_db: np.ndarray, output_path: str):
        """Save spectrogram as image."""
        fig = plt.figure(figsize=(self.IMGSZ/100, self.IMGSZ/100), dpi=self.SAVE_DPI)
        ax = fig.add_axes([0, 0, 1, 1])
        ax.set_axis_off()
        librosa.display.specshow(
            S_db, sr=self.SR, hop_length=self.HOP_LENGTH, 
            x_axis=None, y_axis=None, cmap="magma"
        )
        plt.savefig(output_path, bbox_inches='tight', pad_inches=0)
        plt.close(fig)
    
    def _analyze_with_heuristics(self, audio_path: str) -> bool:
        """
        Fallback heuristic-based cry detection.
        Used when YOLOv8 model is not available.
        """
        try:
            y, sr = librosa.load(audio_path, sr=None)
            
            # Calculate zero crossing rate
            zcr = librosa.feature.zero_crossing_rate(y)[0]
            zcr_mean = np.mean(zcr)
            
            # Calculate RMS energy
            rms = librosa.feature.rms(y=y)[0]
            rms_mean = np.mean(rms)
            
            # Simple threshold-based detection
            # Crying typically has moderate ZCR and high energy
            is_crying = zcr_mean > 0.1 and rms_mean > 0.02
            
            print(f"🔍 Heuristic detection: {'Crying' if is_crying else 'Not crying'} (ZCR: {zcr_mean:.3f}, RMS: {rms_mean:.3f})")
            
            return is_crying
            
        except Exception as e:
            print(f"Error in heuristic analysis: {e}")
            return False


# Singleton instance
cry_detection_service = CryDetectionService()