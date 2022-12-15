# Takes in a folder of SVG and JPG files
# Outputs into folder Target/ Full size redacted pnhs
# Outputs into folder ZK-Thumbs/ blured thumbnails
# Outputs into folder ZK-Source/ resized thumbnails for ZK
# Outputs into folder ZK-Source/ coords of redaction area

# ImageFilter for using filter() function
from PIL import Image, ImageFilter, ImageDraw
import xml.dom.minidom
import os
def create_asset(source_filename, redaction):


    # Load originally extracted JPG


    GE_prefix=source_filename.replace("MRA22591R0000401246_Page_","C049-")
    if redaction == False:
        # If no redaction, save as is
        orig = Image.open(f"Source/{source_filename}.jpg", "r")
        orig.save(f"Target/{GE_prefix}.png")



    if redaction == True:
        # Create ZK Source
        orig = Image.open(f"Source/{source_filename}.jpg", "r")
        orig.thumbnail((430, 608))
        orig.save(f"ZK-Source/{source_filename}.png")
        orig = orig.filter(ImageFilter.GaussianBlur(radius=2))
        orig.save(f"ZK-Thumbs/{source_filename}-thumb.png")

        # Redaction on fullsize image:
        orig = Image.open(f"Source/{source_filename}.jpg", "r")
        img_cw = orig.size[0]
        print(f"Redaction of {source_filename}")

        # Get coords from XML
        doc = xml.dom.minidom.parse(f"Source/{source_filename}.svg")
        svg = doc.getElementsByTagName("image")
        imgw=int(svg[0].getAttribute("width"))
        transform = svg[0].getAttribute("transform")[7:]

        transform_split = transform.split(" ")

        # Resize info
        multiplier_x = float(transform_split[0])
        multiplier_y = float(transform_split[3])

        # Read Redaction Area
        redactions = doc.getElementsByTagName("rect")
        f = open(f"ZK-Source/{source_filename}_coords.txt", "w")
        for redaction in redactions:
            x = float(redaction.getAttribute("x"))
            y = float(redaction.getAttribute("y"))
            w = float(redaction.getAttribute("width"))
            h = float(redaction.getAttribute("height"))

            # Apply resize modifier
            # Values for WIDTH (800) which is imgw
            x = int(x / multiplier_x)
            y = int(y / multiplier_y)
            w = int(w / multiplier_x)
            h = int(h / multiplier_x)


            # Current Image img_cw
            # So to reposition
            ratio = (img_cw/imgw)
            x= x*ratio
            y=y*ratio
            w=w*ratio
            h=h*ratio

            # Draw redaction
            shape = [(x, y), (w+x, h+y)]
            r = ImageDraw.Draw(orig)
            r.rectangle(shape, fill="#000000")

            #write coord
            x_thumb=int(x*430/img_cw)
            y_thumb=int(y*430/img_cw)
            w_thumb=int(w*430/img_cw)
            h_thumb=int(h*430/img_cw)
            f.write(f"{x_thumb} {y_thumb} {w_thumb} {h_thumb}\n")

        orig.save(f"Target/{GE_prefix}.png")

for filename in os.listdir("Source"):
    if os.path.splitext(filename)[1] == ".jpg":
        base_filename = os.path.splitext(filename)[0]
        if os.path.exists(f"Source/{base_filename}.svg"):
            print("Redacting")
            create_asset(base_filename, True)
        else:
            create_asset(base_filename, False)
