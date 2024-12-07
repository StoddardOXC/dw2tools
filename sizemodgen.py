#!/usr/bin/env python3

"""

makes a ship/weap resize mod for DW2.

Usage:  ./sizemodgen /path/to/datadir  /path/to/mod/dir

/path/to/datadir is ".wine/drive_c/GOG Games/Distant Worlds 2/data"
or the like

1. ship sizes:

ArrayOfShipHull
    ShipHull
        DisplaySize  (int)

 -- per-role. see metafactors dict

2. weap sizes:

ArrayOfComponentDefinition
    ComponentDefinition
        WeaponEffect
            BodyScaling
                X (float)
                Y (float)

 -- divide by weap_divider

"""

import sys, glob, os, os.path
from lxml import etree

from icon import icon_png

divider = 12.0
weap_divider = 6.0
metafactors = {
    'fighter':              1.0,
    'civilian':             1.0/divider,
    'freighter':            1.0/divider,
    'navysmall':            1.0/divider,
    'navycap':              1.0/divider,
    'supercap':             1.0/divider,
    'base':                 1.0/divider,
}
factors = {
    'FighterBomber':        'fighter',
    'FighterInterceptor':   'fighter',

    'ExplorationShip':      'civilian',
    'ConstructionShip':     'civilian',
    'MiningShip':           'civilian',
    'PassengerShip':        'civilian',
    'ColonyShip':           'civilian',
    'TroopTransport':       'civilian',
    'FuelTanker':           'civilian',

    'FreighterSmall':       'freighter',
    'FreighterMedium':      'freighter',
    'FreighterLarge':       'freighter',
    
    'Escort':               'navysmall',
    'Frigate':              'navysmall',
    'Destroyer':            'navysmall',
    'Cruiser':              'navysmall',

    'Carrier':              'navycap',
    'CapitalShip':          'navycap',
    
    'PlanetDestroyer':      'supercap',

    'SpaceportLarge':       'base',
    'SpaceportMedium':      'base',
    'SpaceportSmall':       'base',
    'MiningStation':        'base',
    'ResortBase':           'base',
    'MonitoringStation':    'base',
    'ResearchStation':      'base',
    'DefensiveBase':        'base',   
}

roles = set()
def role_factor(role):
    roles.add(role)
    if role not in factors:
        print(role, "role not found")
        return 1.0 / divider
    return metafactors[factors[role]]

def resize_ships(root, path):
    for stuff in root.iterfind(path):
        hull = stuff.getparent()
        role = hull.find("Role").text
        stuff.text = "{:d}".format(int(float(stuff.text) * role_factor(role)))

cats = set()
fams = set()
def resize_weaps(root, path):
    for stuff in root.iterfind(path):
        comp = stuff.getparent().getparent()
        name = comp.find("Name").text
        famc = comp.find("Family")
        fam = None if famc is None else famc.text
        cat = comp.find("Category").text
        cats.add(cat)
        fams.add(fam)
        xc = stuff.find("X")
        yc = stuff.find("Y")
        x = float(xc.text)
        y = float(yc.text)
        xc.text = "{:.2f}".format(x / weap_divider)
        yc.text = "{:.2f}".format(y / weap_divider)
        #print(name, fam, cat, "{:.2f} {:.2f} -> {} {}".format(x,y, xc.text, yc.text))

modjs = """
{{
        "displayName": "resizemod",
        "shortDescription": "ship {:.2f} wpn {:.2f}",
        "descriptionFile": "dsc.text",
        "previewImage": "rsz.png",
        "version": "0.1"
}}
""".format(divider, weap_divider)

descr = "    {:16s}: {:.3f}\n\n".format("weapons", 1.0/weap_divider)
for k,v in metafactors.items():
    descr += "    {:16s}: {:.3f}\n".format(k, v)

datadir = sys.argv[1]
destdir = sys.argv[2]

if not os.path.isdir(destdir):
    os.mkdir(destdir)

open(os.path.join(destdir, "mod.json"), "wb").write(modjs.encode('utf-8'))
open(os.path.join(destdir, "dsc.text"), "wb").write(descr.encode('utf-8'))
open(os.path.join(destdir, "rsz.png"), "wb").write(icon_png)

for fn in glob.glob(os.path.join(datadir, "*.xml")):
    dfn = os.path.basename(fn)
    c = etree.parse(open(fn, "r"))
    root  = c.getroot()
    if root.tag == 'ArrayOfShipHull':
        resize_ships(c, "ShipHull/DisplaySize", )
    elif root.tag == 'ArrayOfComponentDefinition':
        resize_weaps(c, "ComponentDefinition/WeaponEffect/BodyScaling")
    else:
        continue
    open(os.path.join(destdir, dfn), "wb").write(etree.tostring(c, encoding="utf-8", xml_declaration=True))

print("Roles", roles)
print("Cats", cats)
print("Fams", fams)
