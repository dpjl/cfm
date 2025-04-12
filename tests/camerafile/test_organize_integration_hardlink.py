import os
import sys
import shutil
import subprocess
import datetime
from pathlib import Path
import time

import pytest
from PIL import Image, ImageColor
import piexif

# Utilitaire pour créer une image JPEG avec données EXIF et couleur spécifiée.
def create_jpeg_file(file_path: Path, mod_time: datetime.datetime, camera_model: str, color: str):
    """
    Crée une image JPEG de couleur uniforme avec EXIF contenant DateTime et Model.
    """
    # Création d'une image uniforme avec la couleur donnée.
    image = Image.new("RGB", (100, 100), color)
    # Préparation des données EXIF.
    zeroth_ifd = {
        piexif.ImageIFD.Make: "TestMake",
        piexif.ImageIFD.Model: camera_model,
        piexif.ImageIFD.DateTime: mod_time.strftime("%Y:%m:%d %H:%M:%S")
    }
    exif_dict = {"0th": zeroth_ifd, "Exif": {}}
    exif_bytes = piexif.dump(exif_dict)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(file_path, "jpeg", exif=exif_bytes)
    # Régler la date de modification.
    timestamp = mod_time.timestamp()
    os.utime(file_path, (timestamp, timestamp))

# Utilitaire pour créer une vraie mini vidéo MP4 sans méta-données.
def create_video_file_real(file_path: Path, mod_time: datetime.datetime):
    """
    Crée un fichier MP4 minimal valide.
    On écrit des octets de header minimal pour simuler une vidéo MP4 réelle.
    """
    # Données minimales pour un fichier MP4 (ftyp atom and some dummy bytes).
    minimal_mp4_data = (
        b'\x00\x00\x00\x20ftypisom\x00\x00\x02\x00isomiso2avc1mp41'
    )
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, "wb") as f:
        f.write(minimal_mp4_data)
    # Régler la date de modification.
    timestamp = mod_time.timestamp()
    os.utime(file_path, (timestamp, timestamp))

# Fixture pour créer un répertoire source et destination temporaires.
@pytest.fixture
def temp_source_and_destination(tmp_path: Path):
    source_dir = tmp_path / "source"
    dest_dir = tmp_path / "destination"
    source_dir.mkdir()
    dest_dir.mkdir()
    return source_dir, dest_dir

def test_organize_integration_hardlink(temp_source_and_destination):
    source_dir, dest_dir = temp_source_and_destination

    # ===== Album1/event =====
    # Pour album1/event, on crée 3 JPEGs avec EXIF de couleurs, dates et modèle "CameraA",
    # et une vraie vidéo MP4 créée par create_video_file_real.
    cam1 = "CameraA"
    # Dates différentes dans le même mois.
    date_event1 = datetime.datetime(2023, 5, 10, 12, 0, 0)
    date_event2 = datetime.datetime(2023, 5, 11, 12, 0, 0)
    date_event3 = datetime.datetime(2023, 5, 12, 12, 0, 0)
    date_event_video = datetime.datetime(2023, 5, 13, 12, 0, 0)
    album1_event_dir = source_dir / "album1" / "event"
    photo1 = album1_event_dir / "photo1.jpg"  # Couleur: red.
    photo2 = album1_event_dir / "photo2.jpg"  # Couleur: green.
    photo3 = album1_event_dir / "photo3.jpg"  # Couleur: blue.
    video1 = album1_event_dir / "video1.mp4"  # Réelle vidéo MP4.
    create_jpeg_file(photo1, date_event1, cam1, "red")
    create_jpeg_file(photo2, date_event2, cam1, "green")
    create_jpeg_file(photo3, date_event3, cam1, "blue")
    create_video_file_real(video1, date_event_video)

    # ===== Album2/holiday =====
    # Pour album2/holiday, on crée 3 JPEGs avec modèle "CameraB".
    # Deux photos seront des doublons exacts (même couleur et même date) mais avec noms différents.
    cam2 = "CameraB"
    date_holiday_dup = datetime.datetime(2022, 12, 20, 15, 30, 0)  # Pour le doublon.
    date_holiday_unique = datetime.datetime(2022, 12, 21, 15, 30, 0)  # Pour la photo unique.
    album2_holiday_dir = source_dir / "album2" / "holiday"
    photo4 = album2_holiday_dir / "photo1.jpg"  # Original du doublon, couleur: purple.
    photo5 = album2_holiday_dir / "photo2.jpg"  # Doublon de photo4.
    photo6 = album2_holiday_dir / "photo3.jpg"  # Photo unique, couleur: orange.
    create_jpeg_file(photo4, date_holiday_dup, cam2, "purple")
    # Copie exacte pour le doublon.
    photo5.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(photo4, photo5)
    create_jpeg_file(photo6, date_holiday_unique, cam2, "orange")

    # Construction du chemin vers cfm.py. Supposé être en /code/cfm/camerafile/cfm.py.
    current_dir = Path(__file__).parent.parent.parent  # => /code/cfm
    cfm_py = current_dir / "camerafile" / "cfm.py"
    assert cfm_py.exists(), f"Le fichier {cfm_py} n'existe pas."

    # Préparation de la commande d'exécution avec le même format.
    cmd = [
        sys.executable,
        str(cfm_py),
        "--no-progress",
        "organize",
        str(source_dir),
        str(dest_dir),
        "--ignore-duplicates",
        "-f",
        "{date:%Y}/{date:%m[%B]}/{cm:Unknown}/{filename:x}"
    ]
    command_line = ' '.join(cmd)
    print(f"CFM command line: {command_line}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode == 0, f"Erreur lors de l'exécution de cfm.py organize: {result.stderr}"

    # Fonction utilitaire pour déterminer le chemin attendu dans la destination.
    def expected_path(src_file: Path) -> Path:
        mod_time = datetime.datetime.fromtimestamp(src_file.stat().st_mtime)
        year = mod_time.strftime("%Y")
        month = mod_time.strftime("%m[%B]")
        # Déterminer le modèle en fonction du répertoire source.
        rel_parts = src_file.relative_to(source_dir).parts
        if "album1" in rel_parts:
            cam = cam1
        elif "album2" in rel_parts:
            cam = cam2
        else:
            cam = "Unknown"
        return dest_dir / year / month / cam / src_file.name

    # Définition des chemins attendus pour les fichiers d'album1/event.
    organized_photo1 = expected_path(photo1)
    organized_photo2 = expected_path(photo2)
    organized_photo3 = expected_path(photo3)
    organized_video1 = expected_path(video1)
    # Pour album2/holiday, calculer les chemins pour photo4 et photo5 (doublons) et photo6.
    organized_photo4 = expected_path(photo4)
    organized_photo5 = expected_path(photo5)
    organized_photo6 = expected_path(photo6)
    
    # Attente active pour tenir compte d'un éventuel traitement asynchrone.
    timeout = 10
    start_time = time.time()
    while time.time() - start_time < timeout:
        if (organized_photo1.exists() and organized_photo2.exists() and organized_photo3.exists() and 
            organized_video1.exists() and (organized_photo4.exists() or organized_photo5.exists()) and
            organized_photo6.exists()):
            break
        time.sleep(0.5)

    # ===== Vérifications pour album1/event =====
    for src in [photo1, photo2, photo3, video1]:
        dest_file = expected_path(src)
        assert dest_file.exists(), f"{dest_file} est introuvable dans la destination."
        # Vérifier que le fichier de destination est un hard-link du fichier source.
        src_stat = os.stat(src)
        dest_stat = os.stat(dest_file)
        assert src_stat.st_ino == dest_stat.st_ino, f"{dest_file} n'est pas un hard-link de {src}."
        # Vérifier que le contenu est identique.
        assert dest_file.read_bytes() == src.read_bytes(), f"Le contenu de {dest_file} diffère de {src}."

    # ===== Vérifications pour album2/holiday =====
    # Vérifier que parmi les doublons photo4 et photo5, exactement l'un d'eux est copié.
    exists_photo4 = organized_photo4.exists()
    exists_photo5 = organized_photo5.exists()
    assert (exists_photo4 or exists_photo5) and not (exists_photo4 and exists_photo5), (
        f"Parmi les doublons, une seule photo doit être copiée: photo4 existe: {exists_photo4}, photo5 existe: {exists_photo5}"
    )
    # Pour la photo unique.
    assert organized_photo6.exists(), f"{organized_photo6} est introuvable dans la destination."
    for src in [photo4, photo6]:
        # Pour le fichier effectivement copié parmi photo4/photo5, on vérifie le hard-link.
        if expected_path(src).exists():
            dest_file = expected_path(src)
            src_stat = os.stat(src)
            dest_stat = os.stat(dest_file)
            assert src_stat.st_ino == dest_stat.st_ino, f"{dest_file} n'est pas un hard-link de {src}."
            assert dest_file.read_bytes() == src.read_bytes(), f"Le contenu de {dest_file} diffère de {src}."

if __name__ == '__main__':
    import pytest
    pytest.main([__file__])
