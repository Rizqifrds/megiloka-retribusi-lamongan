"""Load only the model produced locally by backend/train_ai.py."""
from functools import lru_cache
from pathlib import Path

import joblib

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / 'data'
MODEL_PATH = ROOT / 'artifacts' / 'intent_model.joblib'
MODEL_NAME = 'tfidf-logistic-regression'


class ModelUnavailable(RuntimeError):
    pass


class IntentClassifier:
    def __init__(self, path=MODEL_PATH):
        self.path = Path(path)
        self.bundle = None
        self.modified = None

    def predict(self, message: str) -> dict:
        try:
            modified = self.path.stat().st_mtime_ns
            if self.bundle is None or modified != self.modified:
                # joblib is pickle-based: never accept uploaded/remote model files.
                bundle = joblib.load(self.path)
                if bundle['model_name'] != MODEL_NAME:
                    raise ValueError('Unknown model format')
                self.bundle, self.modified = bundle, modified
            pipeline = self.bundle['pipeline']
            probabilities = pipeline.predict_proba([message])[0]
            ranking = probabilities.argsort()[::-1]
            confidence = float(probabilities[ranking[0]])
            margin = confidence - float(probabilities[ranking[1]])
            intent = str(pipeline.classes_[ranking[0]])
            if confidence < self.bundle['min_confidence'] or margin < self.bundle['min_margin']:
                intent = 'uncertain'
            return {'intent': intent, 'confidence': round(confidence, 4), 'model': MODEL_NAME}
        except Exception as exc:
            raise ModelUnavailable('Model lokal tidak tersedia. Jalankan training ulang.') from exc


@lru_cache(maxsize=1)
def get_classifier():
    return IntentClassifier()


def predict_intent(message: str) -> dict:
    return get_classifier().predict(message)
