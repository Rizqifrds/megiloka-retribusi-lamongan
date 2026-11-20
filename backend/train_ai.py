"""Train on train.json only; evaluate on an independently authored test.json."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import tempfile

import joblib
import sklearn
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
from sklearn.pipeline import FeatureUnion, Pipeline

from ai.intent_model import DATA_DIR, MODEL_NAME, MODEL_PATH


def load_data(path):
    rows = json.loads(path.read_text(encoding='utf-8'))
    if not rows or any(not isinstance(r.get('text'), str) or not r['text'].strip() or not r.get('intent') for r in rows):
        raise ValueError(f'Dataset invalid: {path}')
    normalized = [' '.join(r['text'].casefold().split()) for r in rows]
    if len(normalized) != len(set(normalized)):
        raise ValueError(f'Duplicate questions: {path}')
    return rows


def train(output_dir: Path = MODEL_PATH.parent) -> dict:
    training = load_data(DATA_DIR / 'train.json')
    testing = load_data(DATA_DIR / 'test.json')
    normalize = lambda t: ' '.join(t.casefold().split())
    if {normalize(r['text']) for r in training} & {normalize(r['text']) for r in testing}:
        raise ValueError('Training and test questions overlap')
    if {r['intent'] for r in testing} != {r['intent'] for r in training}:
        raise ValueError('Every intent must appear in both splits')
    pipeline = Pipeline([
        ('features', FeatureUnion([
            ('word', TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True)),
            ('character', TfidfVectorizer(analyzer='char_wb', ngram_range=(3, 5), sublinear_tf=True)),
        ])),
        ('classifier', LogisticRegression(C=8, max_iter=1500, class_weight='balanced', random_state=42)),
    ])
    pipeline.fit([r['text'] for r in training], [r['intent'] for r in training])
    expected = [r['intent'] for r in testing]
    predicted = pipeline.predict([r['text'] for r in testing])
    probabilities = pipeline.predict_proba([r['text'] for r in testing])
    labels = pipeline.classes_.tolist()
    min_confidence, min_margin = 0.32, 0.04  # Fixed before inspecting held-out results.
    accepted = []
    predictions = []
    for row, label, probs in zip(testing, predicted, probabilities):
        sorted_probs = sorted(probs, reverse=True)
        confidence = float(sorted_probs[0])
        runtime_label = str(label) if confidence >= min_confidence and sorted_probs[0] - sorted_probs[1] >= min_margin else 'uncertain'
        accepted.append(runtime_label)
        predictions.append({'text': row['text'], 'expected': row['intent'], 'predicted': str(label), 'runtime_intent': runtime_label, 'confidence': round(confidence, 4), 'correct': bool(label == row['intent'])})
    report = {
        'model': MODEL_NAME,
        'trained_at_utc': datetime.now(timezone.utc).isoformat(),
        'seed': 42, 'python': platform.python_version(), 'sklearn': sklearn.__version__,
        'train_count': len(training), 'test_count': len(testing),
        'train_class_counts': dict(Counter(r['intent'] for r in training)),
        'test_class_counts': dict(Counter(expected)),
        'data_sha256': {name: hashlib.sha256((DATA_DIR / name).read_bytes()).hexdigest() for name in ['train.json', 'test.json']},
        'accuracy': float(accuracy_score(expected, predicted)),
        'macro_f1': float(f1_score(expected, predicted, average='macro')),
        'runtime_accuracy_including_abstentions': float(accuracy_score(expected, accepted)),
        'abstentions': accepted.count('uncertain'),
        'labels': labels,
        'classification_report': classification_report(expected, predicted, output_dict=True, zero_division=0),
        'confusion_matrix': confusion_matrix(expected, predicted, labels=labels).tolist(),
        'predictions': predictions,
        'limitations': 'Small manually authored educational dataset, not a real-user benchmark. Test set is evaluation-only. Runtime answers also use deterministic date/entity parsing and live database facts.',
    }
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    bundle = {'model_name': MODEL_NAME, 'pipeline': pipeline, 'min_confidence': min_confidence, 'min_margin': min_margin, 'trained_at_utc': report['trained_at_utc']}
    # Atomic replacement lets a running Flask worker reload after retraining.
    with tempfile.NamedTemporaryFile(dir=output_dir, suffix='.joblib', delete=False) as file:
        temporary = Path(file.name)
    try:
        joblib.dump(bundle, temporary)
        os.replace(temporary, output_dir / 'intent_model.joblib')
    finally:
        temporary.unlink(missing_ok=True)
    (output_dir / 'evaluation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=MODEL_PATH.parent)
    args = parser.parse_args()
    result = train(args.output_dir)
    print(json.dumps({k: result[k] for k in ['model', 'train_count', 'test_count', 'accuracy', 'macro_f1', 'runtime_accuracy_including_abstentions', 'abstentions']}, indent=2))
    print('Evaluation:', args.output_dir / 'evaluation.json')
