
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

# Utilitaire pour créer une image JPEG avec des données EXIF et une couleur donnée.
def create_jpeg_file(file_path: Path, mod_time: datetime.datetime, camera_model: str, color: str):
    """
    Crée une image JPEG de couleur uniforme avec les métadonnées EXIF DateTime et Model.
    Le paramètre 'color' est fourni sous forme de chaîne (ex: "red").
    """
    # Création d'une image uniforme avec la couleur donnée.
    image = Image.new("RGB", (100, 100), color)
    # Préparer les données EXIF
    zeroth_ifd = {
        piexif.ImageIFD.Make: "TestMake",
        piexif.ImageIFD.Model: camera_model,
        piexif.ImageIFD.DateTime: mod_time.strftime("%Y:%m:%d %H:%M:%S")
    }
    exif_dict = {"0th": zeroth_ifd, "Exif": {}}
    exif_bytes = piexif.dump(exif_dict)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(file_path, "jpeg", exif=exif_bytes)
    # Régler la date de modification du fichier
    timestamp = mod_time.timestamp()
    os.utime(file_path, (timestamp, timestamp))

# Utilitaire pour créer une "vidéo" fake.
# Ici, on crée une image JPEG avec EXIF et une couleur donnée, mais on sauvegarde avec l'extension .mp4.
def create_video_file(file_path: Path, mod_time: datetime.datetime, camera_model: str, color: str):
    create_jpeg_file(file_path, mod_time, camera_model, color)

# Fixture pour créer des répertoires source et destination temporaires.
@pytest.fixture
def temp_source_and_destination(tmp_path: Path):
    source_dir = tmp_path / "source"
    dest_dir = tmp_path / "destination"
    source_dir.mkdir()
    dest_dir.mkdir()
    return source_dir, dest_dir

def test_organize_integration(temp_source_and_destination):
    source_dir, dest_dir = temp_source_and_destination

    # ===== Album1/event =====
    # Pour album1/event, on crée 3 photos aux dates différentes (même mois) et une vidéo,
    # toutes avec le modèle de caméra "CameraA" et chacune avec une couleur différente.
    cam1 = "CameraA"
    # Dates différentes du même mois de mai 2023.
    date_event1 = datetime.datetime(2023, 5, 10, 12, 0, 0)
    date_event2 = datetime.datetime(2023, 5, 11, 12, 0, 0)
    date_event3 = datetime.datetime(2023, 5, 12, 12, 0, 0)
    date_event_video = datetime.datetime(2023, 5, 13, 12, 0, 0)
    album1_event_dir = source_dir / "album1" / "event"
    photo1 = album1_event_dir / "photo1.jpg"  # Couleur : red
    photo2 = album1_event_dir / "photo2.jpg"  # Couleur : green
    photo3 = album1_event_dir / "photo3.jpg"  # Couleur : blue
    video1 = album1_event_dir / "video1.mp4"  # Couleur : yellow
    create_jpeg_file(photo1, date_event1, cam1, "red")
    create_jpeg_file(photo2, date_event2, cam1, "green")
    create_jpeg_file(photo3, date_event3, cam1, "blue")
    create_video_file(video1, date_event_video, cam1, "yellow")

    # ===== Album2/holiday =====
    # Pour album2/holiday, on crée 3 photos avec le modèle "CameraB".
    # Deux photos seront identiques (même couleur, même date) pour simuler un doublon, mais auront des noms différents.
    cam2 = "CameraB"
    date_holiday_dup = datetime.datetime(2022, 12, 20, 15, 30, 0)  # Pour les photos en double.
    date_holiday_unique = datetime.datetime(2022, 12, 21, 15, 30, 0)  # Pour la photo unique.
    album2_holiday_dir = source_dir / "album2" / "holiday"
    photo4 = album2_holiday_dir / "photo1.jpg"  # Photo originale du doublon. Couleur : purple.
    photo5 = album2_holiday_dir / "photo2.jpg"  # Doublon de photo4 (même contenu, même couleur, même date).
    photo6 = album2_holiday_dir / "photo3.jpg"  # Photo unique. Couleur : orange.
    create_jpeg_file(photo4, date_holiday_dup, cam2, "purple")
    # Pour simuler un doublon exact, copions photo4 vers photo5.
    photo5.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(photo4, photo5)
    create_jpeg_file(photo6, date_holiday_unique, cam2, "orange")

    # Construction du chemin vers cfm.py. On suppose qu'il se trouve en /code/cfm/camerafile/cfm.py.
    current_dir = Path(__file__).parent.parent.parent  # => /code/cfm
    cfm_py = current_dir / "camerafile" / "cfm.py"
    assert cfm_py.exists(), f"Le fichier {cfm_py} n'existe pas."

    # Préparation de la commande d'exécution
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
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode == 0, f"Erreur lors de l'exécution de cfm.py organize: {result.stderr}"

    # Fonction pour calculer le chemin attendu dans la destination.
    def expected_path(src_file: Path) -> Path:
        mod_time = datetime.datetime.fromtimestamp(src_file.stat().st_mtime)
        year = mod_time.strftime("%Y")
        month = mod_time.strftime("%m[%B]")
        # Détermine le modèle de caméra attendu selon le chemin source.
        rel_parts = src_file.relative_to(source_dir).parts
        if "album1" in rel_parts:
            cam = cam1
        elif "album2" in rel_parts:
            cam = cam2
        else:
            cam = "Unknown"
        return dest_dir / year / month / cam / src_file.name

    # Définir les chemins attendus pour chaque fichier organisé.
    organized_photo1 = expected_path(photo1)
    organized_photo2 = expected_path(photo2)
    organized_photo3 = expected_path(photo3)
    organized_video1 = expected_path(video1)
    organized_photo4 = expected_path(photo4)
    organized_photo5 = expected_path(photo5)
    organized_photo6 = expected_path(photo6)
    # Pour le doublon (photo5), aucun fichier ne doit être copié.
    
    # Attente active pour prise en compte d'un éventuel traitement asynchrone/multiprocessus
    timeout = 10
    start_time = time.time()
    while time.time() - start_time < timeout:
        if (organized_photo1.exists() and organized_photo2.exists() and organized_photo3.exists() and 
            organized_video1.exists() and (organized_photo4.exists() or organized_photo5.exists()) and organized_photo6.exists()):
            break
        time.sleep(0.5)

    # ===== Vérifications pour album1/event =====
    assert organized_photo1.exists(), f"{organized_photo1} est introuvable dans la destination."
    assert organized_photo2.exists(), f"{organized_photo2} est introuvable dans la destination."
    assert organized_photo3.exists(), f"{organized_photo3} est introuvable dans la destination."
    assert organized_video1.exists(), f"{organized_video1} est introuvable dans la destination."

    # On vérifie que les images de album1/event ont les bonnes couleurs.
    # La couleur attendue est vérifiée en réouvrant l'image et en récupérant le pixel (0,0).
    pil_photo1 = Image.open(organized_photo1)
    pil_photo2 = Image.open(organized_photo2)
    pil_photo3 = Image.open(organized_photo3)
    pil_video1 = Image.open(organized_video1)
    assert pil_photo1.getpixel((0,0)) == (254,0,0)#ImageColor.getrgb("red"), "La couleur de photo1 n'est pas rouge."
    assert pil_photo2.getpixel((0,0)) == (0,128,1)#ImageColor.getrgb("green"), "La couleur de photo2 n'est pas verte."
    assert pil_photo3.getpixel((0,0)) == (0,0,254)#ImageColor.getrgb("blue"), "La couleur de photo3 n'est pas bleue."
    assert pil_video1.getpixel((0,0)) == ImageColor.getrgb("yellow"), "La couleur de video1 n'est pas jaune."

    # ===== Vérifications pour album2/holiday =====
    
    assert organized_photo6.exists(), f"{organized_photo6} est introuvable dans la destination."
    organized_photo5 = expected_path(photo5)
    photo4or5 = photo4
    if organized_photo4.exists():
        assert organized_photo4.exists(), f"{organized_photo4} est introuvable dans la destination."
        assert not organized_photo5.exists(), f"Le doublon {organized_photo5} ne doit pas être copié."
        pil_photo4 = Image.open(organized_photo4)
        assert pil_photo4.getpixel((0,0)) == (129,0,127)#ImageColor.getrgb("purple"), "La couleur de photo4 n'est pas violette (purple)."

    if organized_photo5.exists():
        photo4or5 = photo5
        assert organized_photo5.exists(), f"{organized_photo5} est introuvable dans la destination."
        assert not organized_photo4.exists(), f"Le doublon {organized_photo4} ne doit pas être copié."
        pil_photo5 = Image.open(organized_photo5)
        assert pil_photo5.getpixel((0,0)) == (129,0,127)#ImageColor.getrgb("purple"), "La couleur de photo4 n'est pas violette (purple)."

    # Pour album2, vérifier la couleur et date de la photo unique et celle du doublon attendu.
    pil_photo6 = Image.open(organized_photo6)
    assert pil_photo6.getpixel((0,0)) == ImageColor.getrgb("orange"), "La couleur de photo6 n'est pas orange."

    # (Optionnel) Vérifier que le contenu binaire (bytes) correspond pour chaque fichier organisé, car ce test repose sur la création fidèle des JPEG.
    for src in [photo1, photo2, photo3, video1, photo4or5, photo6]:
        dest_file = expected_path(src)
        assert dest_file.read_bytes() == src.read_bytes(), f"Le contenu de {dest_file} ne correspond pas à celui de {src}."

if __name__ == '__main__':
    import pytest
    pytest.main([__file__])
