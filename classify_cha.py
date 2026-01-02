import re
from pathlib import Path
from collections import defaultdict

TIMESTAMP_RE = re.compile(r"\^U\d+_\d+\^U")


def classify_cha_file(path):
    """
    Classify a CHILDES .cha file based on:
    - presence of Target_Child participants
    - presence of actual child utterances
    - presence of timestamps on child utterances
    """

    child_speaker_ids = set()
    has_target_child = False
    utterances = []

    # ======================
    # PASS 1 — METADATA
    # ======================
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.startswith("@Participants:"):
                if "Target_Child" in line:
                    has_target_child = True

            if line.startswith("@ID:"):
                parts = line.strip().split("|")
                # CHILDES invariant:
                # speaker code = parts[2]
                # role = last meaningful field
                if len(parts) >= 3 and "Target_Child" in parts:
                    child_speaker_ids.add(parts[2])
                    has_target_child = True

    # ======================
    # PASS 2 — UTTERANCES
    # ======================
    with open(path, encoding="utf-8") as f:
        for line in f:
            if not line.startswith("*"):
                continue

            if ":" not in line:
                continue

            speaker, content = line.split(":", 1)
            speaker = speaker[1:].strip()  # remove '*'

            # CHILD DETECTION (strict but correct)
            is_child = (
                speaker == "CHI"  # legacy CHILDES
                or speaker in child_speaker_ids
            )

            if not is_child:
                continue

            utterances.append({
                "speaker": speaker,
                "has_timestamp": bool(TIMESTAMP_RE.search(content)),
                "has_xxx": "xxx" in content.lower(),
            })

    # ======================
    # SUMMARY + CLASS
    # ======================
    total = len(utterances)
    with_ts = sum(u["has_timestamp"] for u in utterances)

    if not has_target_child:
        file_type = "EMPTY"   # no children at all (metadata-level)
    elif total == 0:
        file_type = "EMPTY"   # children exist, but never speak
    elif with_ts == total:
        file_type = "A"       # fully aligned
    elif with_ts > 0:
        file_type = "B"       # partially aligned
    else:
        file_type = "B"       # child speech, no timestamps (IMPORTANT FIX)

    return {
        "file": path.name,
        "type": file_type,
        "child_utterances": total,
        "with_timestamps": with_ts,
        "without_timestamps": total - with_ts,
        "has_xxx": any(u["has_xxx"] for u in utterances),
        "child_speakers": sorted(child_speaker_ids),
    }


def classify_cha_files_in_directory(directory):
    results = defaultdict(list)
    directory = Path(directory)

    for cha_path in directory.rglob("*.cha"):
        info = classify_cha_file(cha_path)
        results[info["type"]].append(info)

    return results
