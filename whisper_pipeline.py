"""
Pipeline complet pour:
1. Traiter tous les .cha d'un dossier
2. Générer transcriptions Whisper
3. Calculer WER
4. Fine-tuner Whisper sur voix d'enfants
"""

import json
import subprocess
from pathlib import Path
from typing import List, Dict
import torch
from dataclasses import dataclass
from extract_wor import extract_wor_segments, WorSegment
import whisper
from jiwer import wer as compute_wer


@dataclass
class TranscriptionResult:
    """Transcription d'un segment"""
    segment_id: str
    speaker: str
    ground_truth: str
    whisper_prediction: str
    duration_ms: int
    wer: float
    confidence: float = 0.0


class AudioExtractor:
    """Extraire segments audio avec ffmpeg"""

    def __init__(self, sample_rate: int = 16000, mono: bool = True):
        self.sample_rate = sample_rate
        self.mono = mono

    def extract_segment(self, audio_file: Path, start_ms: int, end_ms: int, output_path: Path) -> bool:
        """Extraire un segment audio"""
        if not audio_file.exists():
            raise FileNotFoundError(f"Fichier audio non trouvé: {audio_file}")

        start_sec = start_ms / 1000.0
        duration_sec = (end_ms - start_ms) / 1000.0

        cmd = [
            "ffmpeg", "-i", str(audio_file),
            "-ss", str(start_sec), "-t", str(duration_sec),
            "-acodec", "libmp3lame", "-ab", "128k",
            "-ar", str(self.sample_rate), "-ac", "1" if self.mono else "2",
            "-y", str(output_path)
        ]

        try:
            subprocess.run(cmd, check=True, capture_output=True, timeout=30)
            return True
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            return False


class WhisperTranscriber:
    """Transcrire audio avec Whisper"""

    def __init__(self, model_name: str = "base", device: str = None):
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.model = whisper.load_model(model_name, device=self.device)

    def transcribe(self, audio_path: Path, language: str = "fr") -> Dict:
        """Transcrire un fichier audio"""
        try:
            result = self.model.transcribe(
                str(audio_path),
                language=language,
                verbose=False
            )
            return {
                "text": result["text"].strip(),
                "confidence": result.get("confidence", 0.0)
            }
        except Exception as e:
            print(f"Erreur transcription {audio_path}: {e}")
            return {"text": "", "confidence": 0.0}


class DatasetBuilder:
    """Construire dataset pour fine-tuning"""

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def create_training_data(self, results: List[TranscriptionResult], split: float = 0.8):
        """Créer splits train/test avec ground truth"""

        # Filtrer les bons segments (WER < 0.5)
        good_segments = [r for r in results if r.wer < 0.5]

        split_idx = int(len(good_segments) * split)
        train = good_segments[:split_idx]
        test = good_segments[split_idx:]

        # Sauvegarder en format Whisper
        self._save_whisper_format(train, self.output_dir / "train.jsonl")
        self._save_whisper_format(test, self.output_dir / "test.jsonl")

        print(f"📊 Dataset créé:")
        print(f"   Train: {len(train)} segments")
        print(f"   Test: {len(test)} segments")

    def _save_whisper_format(self, results: List[TranscriptionResult], output_file: Path):
        """Sauvegarder au format JSONL pour Whisper"""
        with open(output_file, "w", encoding="utf-8") as f:
            for r in results:
                entry = {
                    "audio": r.segment_id,
                    "text": r.ground_truth,
                    "language": "fr"
                }
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")


class WERCalculator:
    """Calculer WER entre transcriptions"""

    @staticmethod
    def calculate(ground_truth: str, prediction: str) -> float:
        """Calculer Word Error Rate"""
        if not ground_truth.strip():
            return 0.0 if not prediction.strip() else 1.0

        return compute_wer(ground_truth, prediction)

    @staticmethod
    def print_stats(results: List[TranscriptionResult]):
        """Afficher statistiques WER"""
        wers = [r.wer for r in results]

        print(f"\n📈 Statistiques WER:")
        print(f"   Moyen: {sum(wers) / len(wers):.3f}")
        print(f"   Min: {min(wers):.3f}")
        print(f"   Max: {max(wers):.3f}")
        print(f"   Median: {sorted(wers)[len(wers) // 2]:.3f}")

        # Segments par WER range
        ranges = [(0, 0.1), (0.1, 0.3), (0.3, 0.5), (0.5, 1.0)]
        for low, high in ranges:
            count = sum(1 for w in wers if low <= w < high)
            print(f"   {low:.1f}-{high:.1f}: {count} segments")


class MultiFileProcessor:
    """Traiter tous les .cha et .wav d'un dossier"""

    def __init__(self, cha_dir: Path, audio_dir: Path, output_dir: Path):
        self.cha_dir = cha_dir
        self.audio_dir = audio_dir
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def find_matching_files(self) -> List[tuple]:
        """Trouver paires .cha/.wav correspondantes"""
        cha_files = list(self.cha_dir.glob("*.cha"))
        pairs = []

        for cha_file in cha_files:
            # Chercher le fichier audio correspondant
            base_name = cha_file.stem
            audio_file = None

            for ext in [".wav", ".mp3", ".m4a", ".flac"]:
                candidate = self.audio_dir / f"{base_name}{ext}"
                if candidate.exists():
                    audio_file = candidate
                    break

            if audio_file:
                pairs.append((cha_file, audio_file))
            else:
                print(f"⚠️  Pas d'audio trouvé pour {cha_file.name}")

        return pairs

    def process_all(self, whisper_model: str = "base", target_speaker: str = None) -> List[TranscriptionResult]:
        """Traiter tous les fichiers"""

        pairs = self.find_matching_files()
        print(f"📁 Trouvé {len(pairs)} paires .cha/.wav\n")

        audio_extractor = AudioExtractor()
        transcriber = WhisperTranscriber(model_name=whisper_model)
        all_results = []

        for cha_file, audio_file in pairs:
            print(f"🔄 Traitement {cha_file.name}...")

            # Extraire segments
            segments = extract_wor_segments(cha_file)

            # Filtrer par speaker si spécifié
            if target_speaker:
                segments = [s for s in segments if s.speaker == target_speaker]

            print(f"   → {len(segments)} segments")

            # Créer dossier de sortie
            file_output_dir = self.output_dir / cha_file.stem
            file_output_dir.mkdir(exist_ok=True)

            # Traiter chaque segment
            results = []
            for i, seg in enumerate(segments):
                segment_id = f"{seg.speaker}_{i:03d}"
                audio_path = file_output_dir / f"{segment_id}.mp3"

                # Extraire audio
                start_ms = seg.words[0][1]
                end_ms = seg.words[-1][2]

                if not audio_extractor.extract_segment(audio_file, start_ms, end_ms, audio_path):
                    continue

                # Transcrire avec Whisper
                transcription = transcriber.transcribe(audio_path)

                # Calculer WER
                wer = WERCalculator.calculate(seg.text, transcription["text"])

                # Sauvegarder résultat
                result = TranscriptionResult(
                    segment_id=segment_id,
                    speaker=seg.speaker,
                    ground_truth=seg.text,
                    whisper_prediction=transcription["text"],
                    duration_ms=end_ms - start_ms,
                    wer=wer,
                    confidence=transcription["confidence"]
                )
                results.append(result)

                if (i + 1) % 10 == 0:
                    print(f"   ✓ {i + 1}/{len(segments)} segments")

            # Sauvegarder résultats par fichier
            self._save_results(results, file_output_dir / "results.json")
            all_results.extend(results)

        return all_results

    def _save_results(self, results: List[TranscriptionResult], output_file: Path):
        """Sauvegarder résultats en JSON"""
        data = [
            {
                "segment_id": r.segment_id,
                "speaker": r.speaker,
                "ground_truth": r.ground_truth,
                "whisper_prediction": r.whisper_prediction,
                "duration_ms": r.duration_ms,
                "wer": r.wer,
                "confidence": r.confidence
            }
            for r in results
        ]

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)


class Pipeline:
    """Pipeline complet: CHAT → Audio → Transcription → WER → Dataset"""

    def __init__(self, cha_dir: Path, audio_dir: Path, output_dir: Path):
        self.cha_dir = cha_dir
        self.audio_dir = audio_dir
        self.output_dir = output_dir

    def run(self, whisper_model: str = "base", target_speaker: str = None):
        """Exécuter le pipeline complet"""

        print("=" * 60)
        print("🚀 PIPELINE WHISPER COMPLET")
        print("=" * 60)

        # Traiter tous les fichiers
        processor = MultiFileProcessor(self.cha_dir, self.audio_dir, self.output_dir)
        results = processor.process_all(whisper_model=whisper_model, target_speaker=target_speaker)

        # Calculer WER
        print(f"\n{'=' * 60}")
        print("📊 RÉSULTATS")
        print("=" * 60)
        WERCalculator.print_stats(results)

        # Créer dataset pour fine-tuning
        print(f"\n{'=' * 60}")
        print("🎯 CRÉATION DATASET FINE-TUNING")
        print("=" * 60)

        builder = DatasetBuilder(self.output_dir / "training_data")
        builder.create_training_data(results)

        print(f"\n{'=' * 60}")
        print("✅ TERMINÉ")
        print("=" * 60)
        print(f"\n📂 Résultats dans: {self.output_dir}")


def main():
    # Configuration
    cha_dir = Path("data")  # Dossier avec tous les .cha
    audio_dir = Path("audio")  # Dossier avec tous les .wav/.mp3
    output_dir = Path("output/whisper_analysis")

    # Optionnel: filtrer par speaker (ex: "Target_Child")
    target_speaker = None

    # Lancer le pipeline
    pipeline = Pipeline(cha_dir, audio_dir, output_dir)
    pipeline.run(whisper_model="base", target_speaker=target_speaker)


if __name__ == "__main__":
    main()