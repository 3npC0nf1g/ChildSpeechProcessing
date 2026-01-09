from pathlib import Path
from typing import List


def find_missing_audio(cha_dir: Path, audio_dir: Path) -> List[str]:
    """
    Parcourt les deux répertoires et renvoie la liste des fichiers .cha
    pour lesquels le fichier audio correspondant (.mp3) est manquant.
    """
    # Lister tous les stems des .cha
    cha_stems = [f.stem for f in cha_dir.glob("*.cha")]

    # Lister tous les stems des .mp3
    mp3_stems = [f.stem for f in audio_dir.glob("*.mp3")]

    # Trouver les .cha sans fichier audio correspondant
    missing = [stem + ".cha" for stem in cha_stems if stem not in mp3_stems]

    return missing


# Exemple d'utilisation
if __name__ == "__main__":
    cha_dir = Path("data/2")
    audio_dir = Path("data/2-songs")

    missing_files = find_missing_audio(cha_dir, audio_dir)
    if missing_files:
        print("⚠️ Fichiers audio manquants pour ces .cha :")
        for f in missing_files:
            print(f"  - {f}")
    else:
        print("✅ Tous les fichiers audio sont présents.")
