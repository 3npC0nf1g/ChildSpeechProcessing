"""
Module pour extraire segments audio et générer datasets
Chaque classe a une unique responsabilité
"""

import json
import csv
from pathlib import Path
from dataclasses import asdict
from extract_wor import extract_wor_segments, WorSegment
import subprocess


class AudioExtractor:
    """Responsabilité unique: Extraire des segments audio avec ffmpeg"""

    def __init__(self, audio_file: Path, sample_rate: int = 16000, mono: bool = True):
        self.audio_file = audio_file
        self.sample_rate = sample_rate
        self.mono = mono

    def extract_segment(self, start_ms: int, end_ms: int, output_path: Path) -> bool:
        """Extraire un segment audio"""
        if not self.audio_file.exists():
            raise FileNotFoundError(f"Fichier audio non trouvé: {self.audio_file}")

        start_sec = start_ms / 1000.0
        duration_sec = (end_ms - start_ms) / 1000.0

        cmd = [
            "ffmpeg",
            "-i", str(self.audio_file),
            "-ss", str(start_sec),
            "-t", str(duration_sec),
            "-acodec", "libmp3lame",
            "-ab", "128k",
            "-ar", str(self.sample_rate),
            "-ac", "1" if self.mono else "2",
            "-y",
            str(output_path)
        ]

        try:
            subprocess.run(cmd, check=True, capture_output=True, timeout=30)
            return True
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            print(f"Erreur extraction: {e}")
            return False


class DatasetEntry:
    """Responsabilité unique: Représenter une entrée du dataset"""

    def __init__(self, segment_id: str, segment: WorSegment, audio_path: Path):
        self.id = segment_id
        self.speaker = segment.speaker
        self.audio = str(audio_path)
        self.text = segment.text
        self.start_ms = segment.words[0][1]
        self.end_ms = segment.words[-1][2]
        self.duration_ms = self.end_ms - self.start_ms
        self.num_words = len(segment.words)

    def to_dict(self):
        return {
            "id": self.id,
            "speaker": self.speaker,
            "audio": self.audio,
            "text": self.text,
            "start_ms": self.start_ms,
            "end_ms": self.end_ms,
            "duration_ms": self.duration_ms,
            "num_words": self.num_words
        }


class DirectoryManager:
    """Responsabilité unique: Gérer la structure de répertoires"""

    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.speaker_dirs = {}
        self._setup()

    def _setup(self):
        """Créer les répertoires nécessaires"""
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def get_speaker_dir(self, speaker: str) -> Path:
        """Obtenir ou créer le répertoire pour un speaker"""
        if speaker not in self.speaker_dirs:
            speaker_dir = self.base_dir / speaker
            speaker_dir.mkdir(exist_ok=True)
            self.speaker_dirs[speaker] = speaker_dir
        return self.speaker_dirs[speaker]

    def get_segment_audio_path(self, segment_id: str, speaker: str, ext: str = ".mp3") -> Path:
        """Construire le chemin pour un segment audio"""
        speaker_dir = self.get_speaker_dir(speaker)
        return speaker_dir / f"{segment_id}{ext}"

    def get_dataset_file(self, format: str = "json") -> Path:
        """Obtenir le chemin du fichier dataset"""
        return self.base_dir / f"dataset.{format}"


class DatasetWriter:
    """Responsabilité unique: Écrire le dataset dans différents formats"""

    @staticmethod
    def write_json(entries: list[dict], output_path: Path):
        """Écrire en JSON"""
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(entries, f, indent=2, ensure_ascii=False)

    @staticmethod
    def write_csv(entries: list[dict], output_path: Path):
        """Écrire en CSV"""
        if not entries:
            return

        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=entries[0].keys())
            writer.writeheader()
            writer.writerows(entries)


class SegmentProcessor:
    """Responsabilité unique: Orchestrer le traitement des segments"""

    def __init__(self, audio_extractor: AudioExtractor, dir_manager: DirectoryManager):
        self.extractor = audio_extractor
        self.dir_manager = dir_manager
        self.dataset = []

    def process_segments(self, segments: list[WorSegment], verbose: bool = True):
        """Traiter tous les segments"""
        successful = 0

        for i, seg in enumerate(segments, 1):
            segment_id = f"{seg.speaker}_{i:03d}"
            audio_path = self.dir_manager.get_segment_audio_path(segment_id, seg.speaker)

            start_ms = seg.words[0][1]
            end_ms = seg.words[-1][2]

            if self.extractor.extract_segment(start_ms, end_ms, audio_path):
                entry = DatasetEntry(segment_id, seg, audio_path)
                self.dataset.append(entry.to_dict())
                successful += 1

                if verbose and i % 10 == 0:
                    print(f"✓ {i}/{len(segments)} segments traités...")
            else:
                if verbose:
                    print(f"✗ Erreur segment {segment_id}")

        if verbose:
            print(f"✅ {successful}/{len(segments)} segments extraits")

        return successful


class PipelineOrchestrator:
    """Responsabilité unique: Coordonner le pipeline complet"""

    def __init__(self, cha_file: Path, audio_file: Path, output_dir: Path):
        self.cha_file = cha_file
        self.audio_file = audio_file
        self.output_dir = output_dir

    def run(self):
        """Exécuter le pipeline complet"""
        print("🔄 Démarrage du pipeline...\n")

        # Étape 1: Extraire les segments CHAT
        print("1️⃣  Extraction des segments %wor...")
        segments = extract_wor_segments(self.cha_file)
        print(f"   → {len(segments)} segments trouvés\n")

        # Étape 2: Initialiser les composants
        print("2️⃣  Initialisation des composants...")
        audio_extractor = AudioExtractor(self.audio_file)
        dir_manager = DirectoryManager(self.output_dir)
        processor = SegmentProcessor(audio_extractor, dir_manager)
        print("   ✓ Prêt\n")

        # Étape 3: Traiter les segments
        print("3️⃣  Extraction des segments audio...")
        successful = processor.process_segments(segments, verbose=True)
        print()

        # Étape 4: Écrire les datasets
        print("4️⃣  Génération des datasets...")
        DatasetWriter.write_json(processor.dataset, dir_manager.get_dataset_file("json"))
        DatasetWriter.write_csv(processor.dataset, dir_manager.get_dataset_file("csv"))
        print("   ✓ Fichiers générés\n")

        # Afficher les statistiques
        self._print_stats(processor.dataset, dir_manager)

    def _print_stats(self, dataset: list[dict], dir_manager: DirectoryManager):
        """Afficher les statistiques finales"""
        print("=" * 60)
        print("📊 STATISTIQUES FINALES")
        print("=" * 60)

        # Par speaker
        by_speaker = {}
        total_duration_ms = 0
        for entry in dataset:
            speaker = entry["speaker"]
            by_speaker.setdefault(speaker, []).append(entry)
            total_duration_ms += entry["duration_ms"]

        print(f"\n📂 Segments par speaker:")
        for speaker in sorted(by_speaker.keys()):
            count = len(by_speaker[speaker])
            print(f"   {speaker}: {count} segments")

        print(f"\n💾 Audio total: {total_duration_ms / 1000 / 60:.1f} minutes")
        print(f"\n📁 Fichiers de sortie:")
        print(f"   - {dir_manager.get_dataset_file('json')}")
        print(f"   - {dir_manager.get_dataset_file('csv')}")
        print("=" * 60)


def main():
    # Configuration
    cha_file = Path("data/2/01-1a.cha")
    audio_file = Path("data/2-songs/01-1a.mp3")  # Adapte l'extension si nécessaire
    output_dir = Path("output/segments")

    # Valider les inputs
    if not cha_file.exists():
        print(f"❌ Fichier CHAT non trouvé: {cha_file}")
        return

    if not audio_file.exists():
        print(f"❌ Fichier audio non trouvé: {audio_file}")
        print(f"   Fichiers disponibles: {list(audio_file.parent.glob('*'))}")
        return

    # Lancer le pipeline
    pipeline = PipelineOrchestrator(cha_file, audio_file, output_dir)
    pipeline.run()


if __name__ == "__main__":
    main()