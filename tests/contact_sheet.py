"""Create complete and category contact sheets from all 89 inspected render candidates."""
from pathlib import Path
import json,math
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1]
assets=json.loads((ROOT/'manifest.json').read_text())['assets']
font=ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf',20)
small=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',16)
def sheet(items,path,columns=6):
    w=330;h=365;rows=math.ceil(len(items)/columns)
    im=Image.new('RGB',(columns*w,rows*h+100),(18,24,33));d=ImageDraw.Draw(im)
    d.text((20,15),'ROBOTDOLLY / CRAZY 88 — PHASE 2',font=font,fill='white')
    d.text((20,45),f'{len(items)} assets shown | 2m per repeat | FBX candidates: DarkRide unverified',font=small,fill=(190,200,210))
    for i,a in enumerate(items):
        p=ROOT/'previews/uv_checks'/f"{a['asset_id']}.png"
        with Image.open(p) as src:src.verify()
        src=Image.open(p).convert('RGB');src.thumbnail((320,290));x=i%columns*w;y=i//columns*h+90
        im.paste(src,(x+(w-src.width)//2,y))
        prefix=f"{a['inventory_number']:02d}" if a['inventory_number'] else '+1'
        label=prefix+' '+a['asset_id']
        if len(label)>31:
            cut=label.rfind('_',0,30);lines=[label[:cut],label[cut+1:]]
        else:lines=[label]
        for j,line in enumerate(lines):d.text((x+8,y+294+j*18),line,font=small,fill='white')
        d.text((x+8,y+335),f"{a['triangles']} tris / {a['quads']} quads"+(' / APPROVED' if a['approved_pilot'] else ''),font=small,fill=(190,200,210))
    im.save(path)
sheet(assets,ROOT/'previews/contact_sheet.png',8)
groups=[('A_walls_floors_ceilings',1,16),('B_arches_columns_trim',17,30),('C_doors_windows',31,42),('D_pipes',43,58),('E_ventilation',59,68),('F_stairs_bridges_elevators',69,78),('G_lighting_details',79,88)]
for name,start,end in groups:
    chosen=[a for a in assets if a['inventory_number'] and start<=a['inventory_number']<=end]
    if name.startswith('F_'):chosen+=[a for a in assets if a['additional_variation']]
    sheet(chosen,ROOT/'previews'/f'{name}.png',4)
print('Complete 89-asset sheet and 7 category sheets generated')
