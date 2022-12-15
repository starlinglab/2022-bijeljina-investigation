# Input png files in Source directory
# Output clean PNGs in Target directory
# import image module from pillow
from PIL import Image
import os

for filename in os.listdir("Source"):
    if os.path.splitext(filename)[1] == ".png":
        # open the image
        base_filename = os.path.splitext(filename)[0]
        Image1 = Image.open(f"Source\{filename}")
        Image2 = Image.new("RGB", Image1.size)
        #Image1copy = Image1.copy()
        Image2.paste(Image1,(0,0))
        Image2.save(f"Clean\{base_filename}.png")
