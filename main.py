from pathlib import Path
from extract_wor import extract_wor_segments

DATA_DIR = Path("data/2/01-1a.cha")  # dossier contenant tes .cha


def main():
    # Extraction des segments %wor
    segments = extract_wor_segments(DATA_DIR)

    print(f"Total segments with %wor: {len(segments)}\n")

    # Organiser par type de locuteur si besoin
    by_speaker = {}
    for seg in segments:
        by_speaker.setdefault(seg.speaker, []).append(seg)

    # Affichage résumé
    for speaker, segs in by_speaker.items():
        print(f"Speaker {speaker}: {len(segs)} segments")
        for s in segs[:3]:  # afficher max 3 segments par locuteur
            print(f"  Text: {s.text}")
            print(f"  Start: {s.start}, End: {s.end}")
            print(f"  Words: {s.words}\n")


if __name__ == "__main__":
    main()
