"""Original diagnostics, no external texture assets. Run with normal Python + Pillow."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import math
ROOT = Path(__file__).resolve().parents[1]
out = ROOT / 'textures/checker'
out.mkdir(parents=True, exist_ok=True)
im = Image.new('RGB', (512,512)); d = ImageDraw.Draw(im)
font = ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf', 20)
for y in range(8):
    for x in range(8):
        color = ((54,101,124) if (x+y)%2 else (214,195,132))
        d.rectangle((64*x,64*y,64*x+63,64*y+63), fill=color, outline=(240,240,230))
        d.text((64*x+4,64*y+4), f'{chr(72-y)}{x+1}', font=font, fill=(15,20,27))
        d.line((64*x+12,64*y+48,64*x+49,64*y+48),fill='white',width=2)
        d.polygon([(64*x+49,64*y+48),(64*x+42,64*y+43),(64*x+42,64*y+53)],fill='white')
        d.line((64*x+54,64*y+47,64*x+54,64*y+29),fill=(255,100,80),width=2)
        d.polygon([(64*x+54,64*y+25),(64*x+50,64*y+32),(64*x+58,64*y+32)],fill=(255,100,80))
im.save(out/'labelled_checker.png')
# Tangent-space +Y normal test: periodic, asymmetric amplitude in X/Y.
normal=Image.new('RGB',(256,256)); px=normal.load()
for y in range(256):
    for x in range(256):
        nx=.35*math.sin(2*math.pi*x/256); ny=.65*math.sin(2*math.pi*(255-y)/256)
        nz=math.sqrt(1-nx*nx-ny*ny)
        px[x,y]=tuple(round((n+1)*127.5) for n in (nx,ny,nz))
normal.save(out/'normal_opengl_plus_y.png')
Image.new('RGB',(16,16),(180,180,180)).save(out/'roughness.png')
Image.new('RGB',(16,16),(0,0,0)).save(out/'metallic.png')
Image.new('RGB',(16,16),(255,255,255)).save(out/'ao.png')
print(out)
