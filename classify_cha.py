import re
from pathlib import Path
from collections import defaultdict

from plotly.io._kaleido import root_dir

TIMESTAMP_RE = re.compile(r"\^U\d+_\d+\^U")


def classify_cha_file(path):
    """
    Classifies a .cha file into Type A / B / C
    based on child utterance timestamp coverage.
    """

    child_speakers = set()
    utterances = []

    # --- first pass: identify Target_Child speakers ---
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.startswith("@ID:"):
                parts = line.strip().split("|")
                if len(parts) >= 6 and parts[5] == "Target_Child":
                    child_speakers.add(parts[2])

    # --- second pass: collect child utterances ---
    with open(path, encoding="utf-8") as f:
        for line in f:
            if not line.startswith("*"):
                continue

            speaker, content = line.split(":", 1)
            speaker = speaker.replace("*", "").strip()

            if speaker not in child_speakers:
                continue

            has_timestamp = bool(TIMESTAMP_RE.search(content))
            has_xxx = "xxx" in content.lower()

            utterances.append({
                "speaker": speaker,
                "has_timestamp": has_timestamp,
                "has_xxx": has_xxx,
                "raw": content.strip()
            })

    # --- summary stats ---
    total = len(utterances)
    with_ts = sum(u["has_timestamp"] for u in utterances)

    if total == 0:
        file_type = "EMPTY"
    elif with_ts == total:
        file_type = "A"  # fully timestamped
    elif with_ts > 0:
        file_type = "B"  # partially timestamped
    else:
        file_type = "C"  # no timestamps

    return {
        "file": path.name,
        "type": file_type,
        "child_utterances": total,
        "with_timestamps": with_ts,
        "without_timestamps": total - with_ts,
        "has_xxx": any(u["has_xxx"] for u in utterances),
        "child_speakers": sorted(child_speakers)
    }


def classify_cha_files_in_directory(directory):
    results = defaultdict(list)

    for cha_path in Path(root_dir).rglob("*.cha"):
        info = classify_cha_file(cha_path)
        results[info["type"]].append(info)

    return results


# Utilisation example:
"""results = classify_dataset("palasis_dataset")

for t, files in results.items():
    print(f"\nType {t}: {len(files)} files")
    for f in files[:3]:
        print("  ", f)
"""
