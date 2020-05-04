from PIL import Image
import imagehash
hash0 = imagehash.average_hash(Image.open("H:/scripts/test-data/powershot-photos-videos/IMG_1635.png"))
hash1 = imagehash.average_hash(Image.open("H:/scripts/test-data/powershot-photos-videos/IMG_1635.JPG"))
hash2 = imagehash.average_hash(Image.open("H:/scripts/test-data/powershot-photos-videos/IMG_1635 (Copier).JPG"))
hash3 = imagehash.average_hash(Image.open("H:/scripts/test-data/powershot-photos-videos/IMG_1636.JPG"))
cutoff = 5
print(str(hash0))
print(str(hash1))
print(str(hash2))
print(str(hash3))
if hash0 - hash1 < cutoff:
  print('images are similar')
else:
  print('images are not similar')