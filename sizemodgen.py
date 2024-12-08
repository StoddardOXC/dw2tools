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


3. orbits

approx formula for maxpop is
maxpop(K) = 392.72 * (size^2 / 1e6 ) * quality / 100
where 
    size = game ui size (i.e. 4453)
    quality = game ui quality (i.e. 100)
where game ui quality is
    base quality + race suitability bonus - damage percent points + terraforming percent points
    capped at 100 I think. or maybe not.

"""

def maxpop(sz,q):
    return int(q * sz * sz * 392.72 / 1e9)

import sys, glob, os, os.path, copy
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
    rv = False
    for stuff in root.iterfind(path):
        hull = stuff.getparent()
        role = hull.find("Role").text
        stuff.text = "{:d}".format(int(float(stuff.text) * role_factor(role)))
        rv = True
    return rv

cats = set()
fams = set()
def resize_weaps(root, path):
    rv = False
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
        rv = True
    return rv

# This only works IFF there is only one OrbTypes.xml
# Also looks like there is an implicit assumption of no secondary moons
# that is a moon can't have a moon.
def resize_orbits(root, moon_orb_factor = 23.0):
    ocats = set()
    allchildren = set() # mentioned as children
    childless = set() # not ever having children
    l2children = set() # mentioned as children of orbs that are in allchildren
    l1onlychildren = set() # only mentioned of as children of non-children orbs
    orbids = set() # all
    names = {}
    parents_of = {}
    max_orbid = -1

    for ot in root.iterfind("OrbType"):
        orbid = int(ot.find("OrbTypeId").text)
        if orbid > max_orbid:
            max_orbid = orbid
        orbids.add(orbid)
        cat = ot.find("Category").text
        ocats.add(cat)
        name = ot.find("Name").text
        diamin = ot.find("DiameterMinimum").text
        diamax = ot.find("DiameterMaximum").text
        odimin = ot.find("OrbitalDistanceFromSunRatioMinimum").text
        odimax = ot.find("OrbitalDistanceFromSunRatioMaximum").text
        
        has_child = False
        names[orbid] = "{: 4d}: {:8s}  {:32s} {:5d}-{:<5d} {:.3f}-{:.3f}".format(orbid, 
                        cat, name, int(diamin), int(diamax), float(odimin), float(odimax))
        for child in ot.iterfind("ChildTypes/OrbTypeFactor"):            
            chid = int(child.find("OrbTypeId").text)
            factor = float(child.find("Factor").text)
            allchildren.add(chid)
            has_child = True
            
            if chid not in parents_of:
                parents_of[chid] = set((orbid,))
            else:
                parents_of[chid].add(orbid)

        if not has_child:
            childless.add(orbid)

    print("\nocats:", ocats)
    
    print("\nchildless")
    for orbid in childless:
        print(names[orbid])
    
    nonchildren = orbids - allchildren
    print("\nnot mentioned as children")
    for orbid in nonchildren:
        print(names[orbid])
    
    # l1-only children
    # only mentioned of as children of non-children orbs
    l1only = set()
    for chid, parents in parents_of.items():
        if nonchildren.intersection(parents) == parents:
            l1only.add(chid)

    # l2-only children - moons, whose orbits were fixed
    l2only = set()
    for orbid, parents in parents_of.items():
        if l1only.intersection(parents) == parents:
            l2only.add(orbid)

    # l1 and l2 chidren - possible moons, to be fixed
    print("\n to be fixed")
    tobefixed = set()
    for orbid in allchildren:
        if orbid not in l1only and orbid not in l2only:
            print(names[orbid])
            print("    parents: {}".format(parents_of[orbid]))
            tobefixed.add(orbid)

    print("\nmentioned as children")
    for orbid in allchildren:
        l1os = " [L1-only]" if orbid in l1only else ""
        l2os = " [L2-only]" if orbid in l2only else ""
        print(names[orbid], l1os, l2os)
        if orbid not in l1only and orbid not in l2only:
            #continue
            print("    parents: {}".format(parents_of[orbid]))
    
    print("\nmax_id: ", max_orbid)
    
    # nothing to be done
    if len(tobefixed) == 0:
        #return False
        pass

    L2ONLY_START = 100
    new_orbs = set()
    for ot in root.iterfind("OrbType"):
        orbid = int(ot.find("OrbTypeId").text)
        if orbid in tobefixed: # and orb that is both l1 and l2
            # that is used both as a planet and as a moon
            # copy an Orb to be the moon orb.
            neworb = copy.copy(ot)
            # set new id
            neworb.find("OrbTypeId").text = "{:d}".format(orbid + L2ONLY_START)
            # fix orbit
            odimin_el = neworb.find("OrbitalDistanceFromSunRatioMinimum")
            odimax_el = neworb.find("OrbitalDistanceFromSunRatioMaximum")
            odimin_el.text = "{:.3f}".format(float(odimin_el.text) * moon_orb_factor)
            odimax_el.text = "{:.3f}".format(float(odimax_el.text) * moon_orb_factor)
            # drop chidlren
            neworb.find("ChildTypes").clear()

            new_orbs.add(neworb)

        # fix child ids to point to the moon orbs.
        # skip child ids in l2only.
        if orbid not in nonchildren:
            for child in ot.iterfind("ChildTypes/OrbTypeFactor"):
                child_el = child.find("OrbTypeId")
                child_id = int(child_el.text) 
                if child_id in tobefixed:
                    child_el.text = "{:d}".format(child_id + L2ONLY_START)

    if len(new_orbs) > 0:
        root.extend(new_orbs)
        return True
    return False

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
    touched = False
    c = etree.parse(open(fn, "r"))
    root  = c.getroot()
    if root.tag == 'ArrayOfOrbType':
        touched = resize_orbits(root)
    elif root.tag == 'ArrayOfShipHull':
        touched = resize_ships(c, "ShipHull/DisplaySize", )
    elif root.tag == 'ArrayOfComponentDefinition':
        touched = resize_weaps(c, "ComponentDefinition/WeaponEffect/BodyScaling")
    else:
        continue
    if touched:
        open(os.path.join(destdir, dfn), "wb").write(etree.tostring(c, encoding="utf-8", xml_declaration=True))

print("Roles", roles)
print("Cats", cats)
print("Fams", fams)
