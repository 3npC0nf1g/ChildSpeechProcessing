import re
from pathlib import Path
from dataclasses import dataclass
from typing import List, Union


@dataclass
class WorSegment:
    speaker: str
    text: str
    words: list  # [(word, start, end)]
    file_name: str = ""  # Ajouter le nom du fichier source


def extract_wor_segments(path: Union[Path, str], debug: bool = False) -> List[WorSegment]:
    """
    Extraire segments %wor d'un fichier .cha

    Args:
        path: Chemin vers un fichier .cha OU un dossier contenant des .cha
        debug: Afficher les infos de parsing

    Returns:
        Liste de WorSegment
    """
    path = Path(path)

    if path.is_dir():
        # Si c'est un dossier, traiter tous les .cha
        return _extract_from_directory(path, debug=debug)
    elif path.is_file():
        # Si c'est un fichier, le traiter
        return _extract_from_file(path, debug=debug)
    else:
        raise FileNotFoundError(f"Chemin invalide: {path}")


def _extract_from_directory(cha_dir: Path, debug: bool = False) -> List[WorSegment]:
    """Extraire de tous les fichiers .cha d'un dossier (récursivement)"""

    # Chercher les .cha dans le dossier ET les sous-dossiers
    cha_files = sorted(cha_dir.glob("*.cha")) + sorted(cha_dir.glob("**/*.cha"))
    # Enlever les doublons
    cha_files = sorted(set(cha_files))

    if not cha_files:
        print(f"⚠️  Aucun fichier .cha trouvé dans {cha_dir}")
        return []

    if debug:
        print(f"📁 Traitement de {len(cha_files)} fichiers .cha\n")

    all_segments = []

    for cha_file in cha_files:
        if debug:
            print(f"  🔄 {cha_file.name}...", end=" ")

        segments = _extract_from_file(cha_file, debug=False)
        all_segments.extend(segments)

        if debug:
            print(f"✓ ({len(segments)} segments)")

    if debug:
        print(f"\n{'=' * 60}")
        print(f"Total: {len(all_segments)} segments de {len(cha_files)} fichiers")
        print(f"{'=' * 60}\n")

    return all_segments


def _extract_from_file(cha_file: Path, debug: bool = False) -> List[WorSegment]:
    """Extraire de un seul fichier .cha"""

    segments = []
    current_speaker = None
    file_name = cha_file.stem

    with cha_file.open(encoding="utf-8") as f:
        for line in f:
            line = line.rstrip()

            # ── tour principal
            if line.startswith("*"):
                current_speaker = line.split(":", 1)[0].replace("*", "").strip()

            # ── word tier
            elif line.startswith("%wor:"):
                if not current_speaker:
                    continue

                # Extraire la partie après "%wor:"
                wor_content = line.split(":", 1)[1].strip()

                # Nettoyer les caractères de contrôle
                wor_content = wor_content.replace('\x15', '')

                # Parser simple : splitter par espaces et apparier word + timestamp
                tokens = wor_content.split()

                words = []
                i = 0
                while i < len(tokens):
                    token = tokens[i]

                    # Vérifier si c'est un timestamp (format XXXXX_XXXXX)
                    if re.match(r"^\d{5,}_\d{5,}$", token):
                        # C'est un timestamp → l'attacher au mot précédent
                        if words:
                            word, _, _ = words[-1]
                            match = re.match(r"(\d+)_(\d+)", token)
                            if match:
                                start, end = int(match.group(1)), int(match.group(2))
                                words[-1] = (word, start, end)
                        i += 1
                        continue

                    # Sinon, c'est un mot
                    words.append((token, None, None))
                    i += 1

                # Filtrer : garder seulement les mots avec timestamps
                words_with_ts = [(w, s, e) for w, s, e in words if s is not None and e is not None]

                if not words_with_ts:
                    continue

                # Nettoyer le texte : enlever les ponctuations isolées
                clean_words = [w for w, _, _ in words_with_ts if w not in ('?', '.', ',', '!', '+...')]

                if clean_words:
                    clean_text = " ".join(clean_words)

                    segments.append(
                        WorSegment(
                            speaker=current_speaker,
                            text=clean_text,
                            words=words_with_ts,
                            file_name=file_name
                        )
                    )

                    if debug and len(segments) <= 3:
                        print(f"\n✔️ {current_speaker}")
                        print(f"   Text: {clean_text[:70]}")
                        print(f"   Words: {words_with_ts[:3]}...")

    if debug:
        print(f"\n{'=' * 60}")
        print(f"Total segments ({file_name}): {len(segments)}")
        print(f"{'=' * 60}")

    return segments


def print_statistics(segments: List[WorSegment]):
    """Afficher statistiques détaillées sur les segments"""

    if not segments:
        print("❌ Aucun segment trouvé")
        return

    print(f"\n{'=' * 60}")
    print("📊 STATISTIQUES")
    print(f"{'=' * 60}")

    # Par speaker
    by_speaker = {}
    by_file = {}

    for seg in segments:
        # Par speaker
        by_speaker.setdefault(seg.speaker, []).append(seg)

        # Par fichier
        by_file.setdefault(seg.file_name, []).append(seg)

    print(f"\n👥 Par speaker ({len(by_speaker)} speakers):")
    for speaker in sorted(by_speaker.keys()):
        segs = by_speaker[speaker]
        total_duration = sum(s.words[-1][2] - s.words[0][1] for s in segs) / 1000
        print(f"   {speaker:20} {len(segs):3d} segments | {total_duration:6.1f}s audio")

    print(f"\n📁 Par fichier ({len(by_file)} fichiers):")
    for file_name in sorted(by_file.keys()):
        segs = by_file[file_name]
        total_duration = sum(s.words[-1][2] - s.words[0][1] for s in segs) / 1000
        print(f"   {file_name:30} {len(segs):3d} segments | {total_duration:6.1f}s audio")

    # Stats globales
    total_duration = sum(s.words[-1][2] - s.words[0][1] for s in segments) / 1000 / 60
    avg_words = sum(len(s.words) for s in segments) / len(segments)

    print(f"\n📈 Globales:")
    print(f"   Total segments: {len(segments)}")
    print(f"   Total audio: {total_duration:.1f} minutes")
    print(f"   Mots par segment (moyennes): {avg_words:.1f}")
    print(f"{'=' * 60}\n")


if __name__ == "__main__":
    # Exemple 1: Traiter UN fichier
    print("=" * 60)
    print("EXEMPLE 1: UN FICHIER")
    print("=" * 60)
    segments_single = extract_wor_segments(Path("data/2/01-1a.cha"), debug=True)

    # Exemple 2: Traiter UN DOSSIER ENTIER
    print("\n" + "=" * 60)
    print("EXEMPLE 2: DOSSIER ENTIER")
    print("=" * 60)
    segments_all = extract_wor_segments(Path("data"), debug=True)

    # Afficher statistiques
    print_statistics(segments_all)

    # Exemples
    if segments_all:
        print(f"{'=' * 60}")
        print("EXEMPLES DE SEGMENTS:")
        print(f"{'=' * 60}")
        for i, seg in enumerate(segments_all[:5]):
            print(f"\n[{i + 1}] {seg.speaker} ({seg.file_name})")
            print(f"  Text: {seg.text}")
            if seg.words:
                print(f"  Time: {seg.words[0][1]} → {seg.words[-1][2]} ms")
                print(f"  Words: {seg.words[:3]}...")