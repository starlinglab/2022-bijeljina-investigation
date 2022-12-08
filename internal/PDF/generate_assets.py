# ImageFilter for using filter() function
from PIL import Image, ImageFilter, ImageDraw
import xml.dom.minidom
import os
c2papath="./c2patool.exe"
import subprocess
thumb_blur_image = ""
def create_thumb(filename, redaction):
    # Generate thumbnails
    thumb_blur = Image.open(f"Source/{filename}.jpg", "r")
    thumb_blur.thumbnail((430, 608))
    # Blur if SVG is available
    if redaction == True: # and blur_parts == False:
        # Blur Code
        # Blurring image by sending the ImageFilter.
        # GaussianBlur predefined kernel argument
        thumb_blur = thumb_blur.filter(ImageFilter.GaussianBlur(radius=2))
    thumb_blur.save(f"Target/{filename}-c1-thumb.png")    

    # Convert to PNG
    orig = Image.open(f"Source/{filename}.jpg", "r")
    # resize original image 
    thumb = Image.open(f"Source/{filename}.jpg", "r")
    thumb.thumbnail((800, 1132))
    thumb.save(f"Target/{filename}-c1.png")

    # Read SVG, transform and create coors.txt
    if redaction == True:      
        print(f"Redaction of {filename}")
        doc = xml.dom.minidom.parse(f"Source/{filename}.svg")
        svg = doc.getElementsByTagName("image")
        transform = svg[0].getAttribute("transform")[7:]

        transform_split = transform.split(" ")
        multiplier_x = float(transform_split[0])
        multiplier_y = float(transform_split[3])
        redactions = doc.getElementsByTagName("rect")
        f = open(f"Target/{filename}-coords.txt", "w")
        for redaction in redactions:

            x = float(redaction.getAttribute("x"))
            y = float(redaction.getAttribute("y"))
            w = float(redaction.getAttribute("width"))
            h = float(redaction.getAttribute("height"))
            x = int(x / multiplier_x)
            y = int(y / multiplier_y)
            w = int(w / multiplier_x)
            h = int(h / multiplier_x)
#            print (f"x {x} y {y} x+w {w} y+h {h}")

            thumb_ratio = 1 / thumb.size[0] * orig.size[0]
            x_thumb = int(x / thumb_ratio)
            y_thumb = int(y / thumb_ratio)
            w_thumb = int(w / thumb_ratio)
            h_thumb = int(h / thumb_ratio)
            f.write(f"{x_thumb} {y_thumb} {w_thumb} {h_thumb}\n")

        f.close()

# Loop through "Source" folder and create assets in "Target" folder
for filename in os.listdir("Source"):
    if os.path.splitext(filename)[1] == ".jpg":
        base_filename = os.path.splitext(filename)[0]
        if os.path.exists(f"Source/{base_filename}.svg"):
            print("Redacting")
            create_thumb(base_filename, True)
        else:
            create_thumb(base_filename, False)
