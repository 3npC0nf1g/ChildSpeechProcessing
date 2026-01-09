import re
from pathlib import Path
from dataclasses import dataclass


@dataclass
class WorSegment:
    speaker: str
    text: str
    words: list  # [(word, start, end)]


def extract_wor_segments(path: Path, debug=False):
    segments = []
    current_speaker = None

    with path.open(encoding="utf-8") as f:
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
                            words=words_with_ts
                        )
                    )

                    if debug and len(segments) <= 3:
                        print(f"\n✔️ {current_speaker}")
                        print(f"   Text: {clean_text[:70]}")
                        print(f"   Words: {words_with_ts[:3]}...")

    if debug:
        print(f"\n{'=' * 60}")
        print(f"Total segments: {len(segments)}")
        print(f"{'=' * 60}")

    return segments


if __name__ == "__main__":
    path = Path("data/2/01-1a.cha")

    if not path.exists():
        print(f"❌ File not found: {path}")
    else:
        segments = extract_wor_segments(path, debug=True)
        print(f"\n📊 Final result: {len(segments)} segments\n")

        # Grouper par speaker
        by_speaker = {}
        for seg in segments:
            by_speaker.setdefault(seg.speaker, []).append(seg)

        # Stats
        for speaker in sorted(by_speaker.keys()):
            segs = by_speaker[speaker]
            print(f"Speaker {speaker}: {len(segs)} segments")

        # Exemples
        print(f"\n{'=' * 60}")
        print("EXAMPLES:")
        print(f"{'=' * 60}")
        for i, seg in enumerate(segments[:5]):
            print(f"\n[{i + 1}] {seg.speaker}")
            print(f"  Text: {seg.text}")
            if seg.words:
                print(f"  Time: {seg.words[0][1]} → {seg.words[-1][2]} ms")
                print(f"  Words: {seg.words[:3]}...")