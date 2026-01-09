from pathlib import Path
from extract_wor import extract_wor_segments

DATA_DIR = Path("data/1", debug=True)  # dossier contenant tes .cha

segments = extract_wor_segments("data", debug=True)

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

            # Extraire start et end depuis les words
            if s.words:
                words_with_ts = [(w, st, e) for w, st, e in s.words if st is not None and e is not None]
                if words_with_ts:
                    start_ts = words_with_ts[0][1]
                    end_ts = words_with_ts[-1][2]
                    print(f"  Start: {start_ts}, End: {end_ts}")

            print(f"  Words: {s.words}\n")


if __name__ == "__main__":
    main()