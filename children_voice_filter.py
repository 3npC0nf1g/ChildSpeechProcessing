"""
Filtrer spécifiquement les voix d'enfants
Les métadonnées CHILDES contiennent les info de rôle (Target_Child vs Investigator, etc)
"""

import json
from pathlib import Path
from typing import List, Set
from extract_wor import extract_wor_segments, WorSegment


class ChildrenVoiceFilter:
    """Filtrer les segments pour ne garder que les enfants"""

    # Rôles qui correspondent à des enfants (selon CHILDES)
    CHILD_ROLES = {
        "Target_Child",  # L'enfant principal
        "Child",  # Enfant générique
        "Sibling",  # Frère/sœur
        "Peer",  # Copain/copine
        "Playmate",  # Camarade de jeu
    }

    # Rôles adultes (à exclure)
    ADULT_ROLES = {
        "Investigator",  # Chercheur
        "Teacher",  # Enseignant
        "Mother",  # Mère
        "Father",  # Père
        "Adult",  # Adulte générique
        "Caregiver",  # Soigneur
        "Parent",  # Parent
    }

    @staticmethod
    def extract_speakers_from_cha(cha_file: Path) -> dict:
        """
        Parser le fichier .cha pour extraire les rôles des speakers

        Format CHILDES:
        @Participants: KAT Investigator, WIL Target_Child, DYL Target_Child
        @ID: fra|Palasis|KAT|||||Investigator|||
        """

        speakers = {}

        with cha_file.open(encoding="utf-8") as f:
            for line in f:
                # Chercher la ligne @Participants
                if line.startswith("@Participants:"):
                    # Format: NAME Role, NAME Role, ...
                    participants_str = line.split(":", 1)[1].strip()

                    # Parser chaque participant
                    for participant in participants_str.split(","):
                        participant = participant.strip()
                        parts = participant.rsplit(" ", 1)  # Split du dernier espace

                        if len(parts) == 2:
                            speaker_name, role = parts
                            speakers[speaker_name] = role

                # Alternative: chercher les lignes @ID
                elif line.startswith("@ID:"):
                    # Format: fra|Palasis|KAT|||||Investigator|||
                    parts = line.split("|")
                    if len(parts) >= 7:
                        speaker_name = parts[2]
                        role = parts[6]
                        if speaker_name and role:
                            speakers[speaker_name] = role

        return speakers

    @classmethod
    def is_child(cls, speaker: str, speakers_info: dict) -> bool:
        """Vérifier si un speaker est un enfant"""
        role = speakers_info.get(speaker, "Unknown")
        return role in cls.CHILD_ROLES

    @classmethod
    def is_adult(cls, speaker: str, speakers_info: dict) -> bool:
        """Vérifier si un speaker est un adulte"""
        role = speakers_info.get(speaker, "Unknown")
        return role in cls.ADULT_ROLES

    @classmethod
    def filter_children_only(cls, segments: List[WorSegment]) -> List[WorSegment]:
        """Filtrer pour garder SEULEMENT les enfants"""
        return [s for s in segments if "Target_Child" in s.speaker or "Child" in s.speaker]

    @classmethod
    def get_speaker_statistics(cls, segments: List[WorSegment], speakers_info: dict) -> dict:
        """Afficher stats détaillées par type de speaker"""

        by_role = {}

        for seg in segments:
            speaker = seg.speaker
            role = speakers_info.get(speaker, "Unknown")

            by_role.setdefault(role, {
                "speakers": set(),
                "segment_count": 0,
                "total_duration_ms": 0
            })

            by_role[role]["speakers"].add(speaker)
            by_role[role]["segment_count"] += 1
            by_role[role]["total_duration_ms"] += seg.words[-1][2] - seg.words[0][1]

        return by_role


class SegmentFilter:
    """Filtrer les segments selon différents critères"""

    @staticmethod
    def by_speaker_role(segments: List[WorSegment], speakers_info: dict, role: str) -> List[WorSegment]:
        """Filtrer par rôle spécifique"""
        return [s for s in segments if speakers_info.get(s.speaker) == role]

    @staticmethod
    def by_min_words(segments: List[WorSegment], min_words: int = 2) -> List[WorSegment]:
        """Filtrer par nombre minimum de mots"""
        return [s for s in segments if len(s.words) >= min_words]

    @staticmethod
    def by_age_range(segments: List[WorSegment], speakers_info: dict,
                     min_age: float = 2.0, max_age: float = 5.0) -> List[WorSegment]:
        """
        Filtrer par tranche d'âge
        Format CHILDES: "2;06.15" = 2 ans, 6 mois, 15 jours
        """
        filtered = []

        for seg in segments:
            # L'âge n'est pas dans WorSegment, il faudrait le parser du .cha
            # Pour l'instant, retourner tous
            filtered.append(seg)

        return filtered

    @staticmethod
    def combine_filters(segments: List[WorSegment], speakers_info: dict,
                        min_words: int = 2, role: str = None) -> List[WorSegment]:
        """Combiner plusieurs filtres"""

        # Filter 1: Mots minimum
        filtered = SegmentFilter.by_min_words(segments, min_words)

        # Filter 2: Rôle
        if role:
            filtered = SegmentFilter.by_speaker_role(filtered, speakers_info, role)

        return filtered


def demonstrate_filtering():
    """Montrer comment utiliser les filtres"""

    print("=" * 70)
    print("🧒 EXTRACTION DES VOIX D'ENFANTS")
    print("=" * 70 + "\n")

    # Chemins
    cha_file = Path("data/1/01-1a.cha")  # Un seul fichier pour démo

    if not cha_file.exists():
        print(f"❌ Fichier non trouvé: {cha_file}")
        return

    # 1. Extraire les métadonnées speakers
    print("1️⃣  EXTRACTION DES RÔLES")
    print("-" * 70)

    speakers_info = ChildrenVoiceFilter.extract_speakers_from_cha(cha_file)

    print(f"✓ Trouvé {len(speakers_info)} speakers:\n")
    for speaker, role in sorted(speakers_info.items()):
        print(f"   {speaker:15} → {role}")

    # 2. Extraire tous les segments
    print(f"\n2️⃣  EXTRACTION DES SEGMENTS")
    print("-" * 70)

    all_segments = extract_wor_segments(cha_file)
    print(f"✓ Total: {len(all_segments)} segments\n")

    # 3. Statistiques par rôle
    print(f"3️⃣  STATISTIQUES PAR RÔLE")
    print("-" * 70)

    stats = ChildrenVoiceFilter.get_speaker_statistics(all_segments, speakers_info)

    for role, info in sorted(stats.items()):
        total_duration = info["total_duration_ms"] / 1000 / 60
        avg_duration = info["total_duration_ms"] / info["segment_count"] / 1000
        print(f"\n{role}:")
        print(f"   Speakers: {', '.join(sorted(info['speakers']))}")
        print(f"   Segments: {info['segment_count']}")
        print(f"   Durée totale: {total_duration:.1f} minutes")
        print(f"   Durée moyenne/segment: {avg_duration:.2f}s")

    # 4. FILTRER: ENFANTS UNIQUEMENT
    print(f"\n4️⃣  FILTRAGE: ENFANTS UNIQUEMENT")
    print("-" * 70)

    # Méthode 1: Simple (basé sur le nom du speaker)
    children_segments_simple = ChildrenVoiceFilter.filter_children_only(all_segments)

    print(f"\nMéthode simple (Target_Child in speaker name):")
    print(f"   Segments d'enfants: {len(children_segments_simple)}/{len(all_segments)}")

    # Méthode 2: Utiliser les métadonnées
    children_segments = SegmentFilter.combine_filters(
        all_segments,
        speakers_info,
        min_words=2,
        role="Target_Child"
    )

    print(f"\nMéthode avec métadonnées (@ID):")
    print(f"   Segments d'enfants: {len(children_segments)}/{len(all_segments)}")

    # 5. Statistiques finales enfants
    print(f"\n5️⃣  RÉSULTATS FINAUX")
    print("-" * 70)

    if children_segments:
        total_duration = sum(s.words[-1][2] - s.words[0][1] for s in children_segments) / 1000 / 60
        avg_words = sum(len(s.words) for s in children_segments) / len(children_segments)

        print(f"\n✅ ENFANTS UNIQUEMENT:")
        print(f"   Segments: {len(children_segments)}")
        print(f"   Durée audio: {total_duration:.1f} minutes")
        print(f"   Mots/segment (moyenne): {avg_words:.1f}")
        print(f"\n   Speakers (enfants):")

        by_speaker = {}
        for seg in children_segments:
            by_speaker.setdefault(seg.speaker, []).append(seg)

        for speaker in sorted(by_speaker.keys()):
            segs = by_speaker[speaker]
            duration = sum(s.words[-1][2] - s.words[0][1] for s in segs) / 1000
            print(f"      {speaker:15} {len(segs):3d} segments | {duration:6.1f}s")

    print(f"\n{'=' * 70}\n")


if __name__ == "__main__":
    demonstrate_filtering()