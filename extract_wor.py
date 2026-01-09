import re
from pathlib import Path
from dataclasses import dataclass

# Regex qui capture TOUS les mots, avec ou sans timestamps
WORD_TS_RE = re.compile(r"(\S+)(?:\s+\^U(\d+)_(\d+)\^U)?")


@dataclass
class WorSegment:
    speaker: str
    text: str
    words: list  # [(word, start, end)] ou [(word, None, None)]


def extract_wor_segments(path: Path, debug=False):
    segments = []
    current_speaker = None
    line_count = 0
    star_count = 0
    wor_count = 0
    matched_wor = 0

    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.rstrip()
            line_count += 1

            # ── tour principal
            if line.startswith("*"):
                current_speaker = line.split(":", 1)[0].replace("*", "").strip()
                star_count += 1
                if debug:
                    print(f"[Line {line_count}] Speaker: {current_speaker}")

            # ── word tier
            elif line.startswith("%wor:"):
                wor_count += 1
                if debug:
                    print(f"[Line {line_count}] %wor line found: {line[:80]}")

                if not current_speaker:
                    if debug:
                        print(f"  ⚠️  No current_speaker set!")
                    continue

                # Extraire la partie après "%wor:"
                wor_content = line.split(":", 1)[1].strip()

                # Splitter par espaces et reconstruire les mots avec timestamps
                words = []
                tokens = wor_content.split()

                i = 0
                while i < len(tokens):
                    word = tokens[i]
                    start = None
                    end = None

                    # Vérifier si le token suivant contient les timestamps
                    if i + 1 < len(tokens) and tokens[i + 1].startswith("^U"):
                        ts_token = tokens[i + 1]
                        match = re.match(r"\^U(\d+)_(\d+)\^U", ts_token)
                        if match:
                            start, end = int(match.group(1)), int(match.group(2))
                            i += 2
                            words.append((word, start, end))
                            continue

                    # Sinon, c'est un mot sans timestamp
                    words.append((word, start, end))
                    i += 1

                if not words:
                    if debug:
                        print(f"  ⚠️  No words extracted!")
                    continue

                matched_wor += 1
                clean_text = " ".join(w for w, _, _ in words)

                segments.append(
                    WorSegment(
                        speaker=current_speaker,
                        text=clean_text,
                        words=words
                    )
                )

                if debug:
                    print(f"  ✔️ Segment added: {current_speaker} - {clean_text[:50]}")
                    print(f"     Words: {len(words)}")

    if debug:
        print("\n" + "=" * 60)
        print(f"Total lines: {line_count}")
        print(f"Speaker lines (*): {star_count}")
        print(f"Word tier lines (%wor:): {wor_count}")
        print(f"Successfully matched %wor: {matched_wor}")
        print(f"Segments created: {len(segments)}")
        print("=" * 60)

    return segments


if __name__ == "__main__":
    path = Path("data.cha")

    if not path.exists():
        print(f"❌ File not found: {path}")
        print(f"   Current directory: {Path.cwd()}")
        print(f"   Files in current dir: {list(Path.cwd().glob('*'))[:10]}")
    else:
        segments = extract_wor_segments(path, debug=True)
        print(f"\n📊 Final result: {len(segments)} segments")
        for i, seg in enumerate(segments[:5]):
            print(f"\n[{i + 1}] {seg.speaker}: {seg.text}")
            print(f"    Words with timestamps: {[(w, s, e) for w, s, e in seg.words if s is not None][:3]}")