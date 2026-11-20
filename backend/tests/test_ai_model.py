import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class IntentModelTests(unittest.TestCase):
    def test_training_produces_reloadable_model_and_honest_evaluation(self):
        from train_ai import train
        from ai.intent_model import IntentClassifier, DATA_DIR
        train_rows = json.loads((DATA_DIR / 'train.json').read_text(encoding='utf-8'))
        test_rows = json.loads((DATA_DIR / 'test.json').read_text(encoding='utf-8'))
        normalize = lambda text: ' '.join(text.casefold().split())
        self.assertFalse({normalize(r['text']) for r in train_rows} & {normalize(r['text']) for r in test_rows})
        with tempfile.TemporaryDirectory() as folder:
            report = train(Path(folder))
            self.assertEqual(report['test_count'], len(test_rows))
            self.assertEqual(len(report['predictions']), len(test_rows))
            self.assertEqual(report['train_count'], len(train_rows))
            self.assertIn('macro_f1', report)
            model = IntentClassifier(Path(folder) / 'intent_model.joblib')
            for text, label in [
                ('Event apa saja besok?', 'event_schedule'),
                ('Berapa harga tiket Pantai Kutang?', 'ticket_price'),
                ('Bagaimana cara memesan tiket?', 'booking'),
                ('Di mana lokasi WBL?', 'destination_info'),
                ('Halo Megi', 'greeting'),
            ]:
                with self.subTest(text=text):
                    self.assertEqual(model.predict(text)['intent'], label)

    def test_missing_model_is_explicit(self):
        from ai.intent_model import IntentClassifier, ModelUnavailable
        with self.assertRaises(ModelUnavailable):
            IntentClassifier(Path('does-not-exist.joblib')).predict('halo')


if __name__ == '__main__':
    unittest.main()
