import re
from pathlib import Path
from dataclasses import dataclass

WORD_TS_RE = re.compile(r"(\S+)\s+\^U(\d+)_(\d+)\^U")


@dataclass
class WorSegment:
    speaker: str
    text: str
    words: list  # [(word, start, end)]


def extract_wor_segments(path: Path):
    segments = []
    current_speaker = None
    pending_text = None

    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.rstrip()

            # ── tour principal
            if line.startswith("*"):
                current_speaker, content = line.split(":", 1)
                current_speaker = current_speaker.replace("*", "").strip()
                pending_text = content.strip()

            # ── word tier (seul point de vérité)
            elif line.startswith("%wor:") and current_speaker:
                words = []
                for w, start, end in WORD_TS_RE.findall(line):
                    words.append((w, int(start), int(end)))

                if not words:
                    continue

                clean_text = " ".join(w for w, _, _ in words)

                segments.append(
                    WorSegment(
                        speaker=current_speaker,
                        text=clean_text,
                        words=words
                    )
                )

                # reset
                current_speaker = None
                pending_text = None

    return segments
