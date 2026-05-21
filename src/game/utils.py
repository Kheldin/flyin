import pygame as pg
import os


main_dir = os.path.split(os.path.abspath(__file__))[0]
data_dir = os.path.join(main_dir, "assets")

def load_image(name: str, colorkey: pg.Color | None = None, scale: int = 1):
    fullname = os.path.join(data_dir, name)
    image = pg.image.load(fullname)
    print(fullname)
    size = image.get_size()
    size = (size[0] * scale, size[1] * scale)
    image = pg.transform.scale(image, size)

    image = image.convert()
    if colorkey is not None:
        image.set_colorkey(colorkey, pg.RLEACCEL)
    return image, image.get_rect()
