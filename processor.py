import re
import io
import pymupdf
from pypdf import PdfReader as _R, PdfWriter as _W

RULES = [
    # Caustic Soda
    ("C- 1KG", ["b0f6v48kkk", "caustic soda flakes 1kg", "caustic soda flakes", "1kg | b0f6v48kkk", "caustic_1kg", "caustic soda_1kg", "cleaning - 1 kg", "cleaning - 1kg", "multipurpose cleaning - 1 kg"], ["500g", "500gm", "2kg", "2 kg", "koyla", "charcoal", "gasket", "battery", "courier"]),
    ("C- 2KG", ["caustic soda_2kg", "caustic_2kg", "cleaning (1kg + 1kg)", "b0dmpbhl6h", "caustic soda flakes 2kg"], ["500g", "500gm", "1 kg", "koyla", "charcoal", "gasket", "battery", "courier"]),
    ("C- 500G", ["caustic_500gms", "caustic_500", "500gms", "500gm", "4k-en19-u72g", "caustic soda_500", "b0fktffljw", "b0dmnw79vf", "cleaning - 500", "multipurpose cleaning - 500 grams"], ["1kg", "1 kg", "2kg", "2 kg", "koyla", "charcoal", "gasket", "battery", "courier"]),

    # Salt
    ("2KG SALT", ["vrs-ss-900x2-2", "1b0h25d291w", "900 gms + 900gms", "900gms(pack of 2)", "spiritual cleansing, vastu", "2kg salt"], ["caustic", "koyla", "gasket", "battery", "courier"]),
    ("SALT 900g", ["900 gms", "900g", "b0fcc6bd6k", "gw-gg71-423g", "900 g"], ["caustic", "koyla", "gasket", "battery", "courier", "epsom", "990", "2kg"]),
    ("SALT 990g", ["990g", "990 g", "b0dzxs7bq2", "vastu salt"], ["caustic", "koyla", "gasket", "battery", "courier", "900g"]),
    ("K 2KG", ["k 2kg", "potassium", "k2kg"], ["caustic", "koyla"]),

    # Coal
    ("YELLOW-50", ["b0fdggd8lv", "7e-09wt-e1vt", "coal discs for dhoop", "33 mm", "45+ minutes burning time (5)", "odourless coal disc.*5", "pack of 5.*coal"], ["caustic", "koyla", "gasket", "battery", "courier", "30 discs", "3 roll", "10"]),
    ("YELLOW-30", ["b0fdgf8jr3", "a6-wc4l-oauz", "pack of 3 rolls", "coal disc.*3 roll", "long burning coal for incense", "charcoal tablets.*3"], ["caustic", "koyla", "gasket", "battery", "courier", "5.*roll", "50", "10"]),
    ("YELLOW - 30", ["b0f2ybp3mg", "n0-i890-y72k", "bakhoor dani magic coal pack of 3 rolls (30 discs)"], ["caustic", "koyla", "gasket", "battery", "courier"]),
    ("YELLOW - 50", ["b0f2ynx2g", "gf-f84m-k04x", "bakhoor dani magic coal pack of 5"], ["caustic", "koyla", "gasket", "battery", "courier"]),
    ("YELLOW - 100", ["b0f2y75m27", "bf-1m6x-74j1", "bakhoor dani magic coal pack of 10"], ["caustic", "koyla", "gasket", "battery", "courier"]),
    ("AFANDI 90", ["al-afandi", "afandi", "coconut coal", "96 pieces", "96 pc coal", "b0f4rrlyxg"], ["caustic", "koyla", "gasket", "battery", "courier"]),

    # Gaskets / Pressure Cooker
    ("BUTTERFLY SILICON 7.5L", ["b0g5zg5k3w", "butterfly senior 7.5 silicon", "butterfly.*7.5.*silicon", "butterfly blue line dlx", "silicone gasket.*butterfly.*7.5", "7.5 litres", "7.5 liter", "butterfly senior 7.5"], ["caustic", "koyla", "battery", "courier"]),
    ("STAHL 5L", ["b0gd6gn8q4", "stah 5ltr", "stahl.*5.*liter", "stahl cooker 5", "stahl steel cooker.*5", "silicone gasket.*stahl.*5", "stahlcooker.*5"], ["caustic", "koyla", "battery", "courier", "3 liter", "3ltr", "b0gd6qy5yp"]),
    ("STAHL 3L", ["b0gd6qy5yp", "stah 3ltr", "stahl.*3.*liter", "stahl cooker 3", "stahl steel cooker.*3", "silicone gasket.*stahl.*3", "stahl.*3 liter"], ["caustic", "koyla", "battery", "courier"]),
    ("BLUE VINOD 5L", ["b0g5z9f4f2", "blue vinod 5 ltr", "vinod 5l gasket", "outer lid.*vinod.*5", "blue line.*vinod.*5"], ["caustic", "koyla", "battery", "courier"]),
    ("SILICON VINOD 3L", ["vinod.*3l", "silicon.*vinod.*3l", "vinod.*silicon.*3l", "vinod 3 liter"], ["caustic", "koyla", "battery", "courier"]),
    ("SURYA 3L", ["surya 3l", "surya.*3.*liter", "surya pressure cooker 3", "surya_3l"], ["caustic", "koyla", "battery", "courier"]),
    ("SURYA 4-5L", ["surya 4l", "surya 5l", "surya.*4.*liter", "surya.*5.*liter"], ["caustic", "koyla", "battery", "courier"]),
    ("PRESTIGE 4L", ["prestige 4l", "prestige.*4.*liter", "popular aluminium.*4"], ["caustic", "koyla", "battery", "courier"]),
    ("PRESTIGE 3L", ["prestige 3l", "prestige.*3.*liter"], ["caustic", "koyla", "battery", "courier"]),
    ("SAFETY VALVE", ["safety valve", "pressure cooker valve", "steam release valve"], ["caustic", "koyla", "battery", "courier"]),
    ("MIXER COUPLER", ["mixer coupler", "mixer jaw coupler", "jaw coupler"], ["caustic", "koyla", "battery", "courier"]),
    ("SQUARE SHOWER", ["square shower", "shower square", "square head shower"], ["caustic", "koyla", "battery", "courier"]),
    ("GAS PIPE", ["gas pipe", "lpg pipe", "rubber pipe gas", "gas hose"], ["caustic", "koyla", "battery", "courier"]),
    ("BONDI JAHARA", ["bondi jahara", "jahara", "jhaara"], ["caustic", "koyla", "battery", "courier"]),
    ("PVC TOILET", ["b0fd7p7pj1", "pvc seat cover hinge", "toilet seat hinge", "plastic toilet seat", "seat cover screw hinge"], ["caustic", "koyla", "battery", "courier"]),

    # Batteries
    ("LR41-4PC", ["b0dz2mmw4r", "dx-vg7v", "sr41.*1.5v.*4", "lr41.*4.*pack", "lr41.*ag3.*4", "lr41.*pack.*4"], ["caustic", "koyla", "gasket", "courier", "25", "100"]),
    ("LR41-25PC", ["lr41", "ag3 sr41", "sr41 ag3", "copy line lr41", "lr41.*alkaline.*button"], ["caustic", "koyla", "gasket", "courier", "lr44", "cr2025", "a23", "1130", "4.*pack", "_4"]),
    ("LR44=100PC", ["b0dphdb3zj", "lr44.*ag13.*100", "lr.*44.*tray.*100", "lr44.*pack.*100", "ag13.*100b", "lr 44 ag 13.*tray packing.*100", "lr44.*tray packing.*100b"], ["caustic", "koyla", "gasket", "courier", "lr41", "25pc"]),
    ("LR44=25PC", ["lr44", "ag13", "ag 13", "1.5v.*button.*cell.*25"], ["caustic", "koyla", "gasket", "courier", "lr41", "100b", "tray packing.*100"]),
    ("2025-3PC", ["b0f6yrl437", "cr2025.*3v.*3", "qcg.*cr2025.*3v_3", "cr2025.*3.*pack", "lithium coin.*cr2025.*3", "cr2025.*pack.*3"], ["caustic", "koyla", "gasket", "courier"]),
    ("1130-4PC", ["b0f6yrp87x", "lr1130.*ag10.*4", "qcg.*lr1130.*189_4", "1130.*ag10.*pack.*4", "lr1130.*4.*pack"], ["caustic", "koyla", "gasket", "courier"]),
    ("1130=25PC", ["1130", "lr1130", "ag10 189", "189.*1.5v"], ["caustic", "koyla", "gasket", "courier", "4.*pack", "_4"]),
    ("23A-5PC", ["b0f6yr1wpq", "b0dphdn1qc", "a23.*battery.*5", "qcg.*a23.*23a_5", "23a.*pack.*5", "mn21.*23a.*5", "a23.*battery.*23a_5b", "copy.*line.*a23.*5", "a23.*5.*pack"], ["caustic", "koyla", "gasket", "courier", "2.*pack"]),
    ("23A=2PC", ["b0dwfpxnj1", "mvh.*ecom.*23a.*2", "fn-5vep-ktuc", "23a.*12v.*2.*pack", "a23.*2.*pack", "23a.*high voltage.*2"], ["caustic", "koyla", "gasket", "courier", "5.*pack"]),
    ("27A=2PC", ["27a.*battery", "battery.*27a", "a27.*battery", "2.*27a"], ["caustic", "koyla", "gasket", "courier"]),
    ("916=2PC", ["916.*battery", "battery.*916"], ["caustic", "koyla", "gasket", "courier"]),
    ("920=2PC", ["920.*battery", "battery.*920"], ["caustic", "koyla", "gasket", "courier"]),
    ("FTA-4PC", ["fta.*4pc", "fta.*battery.*4", "4.*fta"], ["caustic", "koyla", "gasket", "courier"]),
    ("HATHWAY I-MODE", ["b0dp9jgqv4", "hathway.*remote.*i.*mod", "hathway.*i.*modle", "hathway.*set.*top.*box.*remote", "hathway remote.*i modle"], ["caustic", "koyla", "gasket", "courier"]),
    ("ACER REMOTE", ["acer.*remote", "remote.*acer", "acer.*projector.*remote"], ["caustic", "koyla", "gasket", "courier"]),
    ("THERMAL ROLL", ["thermal roll", "billing roll", "pos roll", "thermal paper roll"], ["caustic", "koyla", "gasket", "courier"]),

    # Capacitors
    ("CAPACITOR 12.5MFD", ["capacitor.*12.5", "12.5.*mfd", "12.5 mfd"], ["caustic", "koyla", "gasket", "courier"]),
    ("CAPACITOR 15MFD", ["capacitor.*15 mfd", "15.*mfd.*capacitor", "15 mfd capacitor"], ["caustic", "koyla", "gasket", "courier"]),
    ("CAPACITOR 20MFD", ["capacitor.*20 mfd", "20.*mfd.*capacitor", "20 mfd capacitor"], ["caustic", "koyla", "gasket", "courier"]),

    # Extension Cords / Ropes
    ("BUNGEE 15FT", ["b0h25mzfgm", "bng15-mc-1p", "bungee.*15.*feet", "15 feet.*bungee", "bungee cord.*15", "15ft.*bungee", "mvh.*bungee.*15", "15 ft.*bungee", "b0h25x4rrk"], ["caustic", "koyla", "gasket", "courier", "6 feet", "6ft", "8ft"]),
    ("BUNGEE 6FT", ["mvh-brc-6-ft-blkmc", "bungee.*cord.*6.*feet", "6 feet.*bungee", "6ft.*bungee", "6 ft.*bungee", "bungee cord rope.*6", "stretchable elastic rope.*6", "cloth.*drying.*rope.*6 feet"], ["caustic", "koyla", "gasket", "courier", "15", "8ft", "15 feet"]),
    ("B-12-2PC", ["b0f38n9sn3", "8ft.*ropes.*black", "cloths drying rope.*8ft", "bungee.*cord.*8ft.*2", "8 ft.*ropes.*black", "bungee cord.*ropes.*8ft", "8ft ropes black colour.*2"], ["caustic", "koyla", "gasket", "courier"]),
    ("MULTI-6-5FT", ["multi.*6.*5ft", "6.*socket.*5ft", "5ft.*6.*socket"], ["caustic", "koyla", "gasket", "courier"]),
    ("MULTI-6-10FT", ["multi.*6.*10ft", "6.*socket.*10ft", "10ft.*6.*socket"], ["caustic", "koyla", "gasket", "courier"]),
    ("MULTI-2-7FT", ["multi.*2.*7ft", "2.*socket.*7ft", "7ft.*2.*socket"], ["caustic", "koyla", "gasket", "courier"]),
    ("MULTI-3M-2PC", ["multi.*3m", "3.*metre.*board", "3m.*extension"], ["caustic", "koyla", "gasket", "courier"]),
    ("MULTI-6FT-2PC", ["multi.*6ft.*2pc", "2.*pc.*6ft", "6ft.*multi.*2"], ["caustic", "koyla", "gasket", "courier"]),
    ("B-10FT-2PC", ["b.*10ft.*2pc", "10ft.*board.*2", "2pc.*10ft"], ["caustic", "koyla", "gasket", "courier"]),
    ("B-8FT=PC", ["b.*8ft", "8ft.*board", "8 ft.*extension"], ["caustic", "koyla", "gasket", "courier"]),
    ("3PIN PLUG", ["3.*pin.*plug", "3pin.*plug", "plug.*3.*pin"], ["caustic", "koyla", "gasket", "courier"]),

    # Tapes
    ("YELLOW VASTU TAPE", ["yellow.*tape.*vastu", "vastu.*tape", "yellow vastu"], ["caustic", "koyla", "gasket", "courier"]),
    ("YELLOW-30", ["yellow.*30.*roll", "30.*mm.*yellow", "yellow.*tape.*30"], ["caustic", "koyla", "gasket", "courier"]),
    ("YELLOW-50", ["yellow.*50.*roll", "50.*mm.*yellow", "yellow.*tape.*50"], ["caustic", "koyla", "gasket", "courier"]),
    ("YELLOW-100", ["yellow.*100.*roll", "100.*mm.*yellow", "yellow.*tape.*100"], ["caustic", "koyla", "gasket", "courier"]),
    ("WHITE STRING", ["white.*string", "twine.*white", "cotton.*string"], ["caustic", "koyla", "gasket", "courier"]),

    # Home Misc
    ("HANGER 25", ["b0f3csmwz8", "7t-dpfu-q7ld", "25.*clip.*stainless.*steel", "space saving laundry rack", "25-clip", "laundry rack.*25", "steel drying hanger.*25"], ["caustic", "koyla", "gasket", "courier"]),
    ("JIGGER SET", ["b0f21xll2g", "cocktail.*jigger.*set.*2", "maxonic.*jigger", "30ml.*60ml.*jigger", "damru.*tall"], ["caustic", "koyla", "gasket", "courier"]),
    ("INDIAN FLAG", ["b0dtk2l3q1", "indian.*flag.*24.*36", "national.*flag.*2x3", "ghar.*tiranga", "tiranga.*flag"], ["caustic", "koyla", "gasket", "courier"]),
    ("F7A", ["b0fdwydjry", "water.*tap.*aerator.*4", "tap.*aerator.*pack.*4", "brass.*aerator.*22mm", "female.*thread.*aerator", "foam flow.*aerator", "22 mm water tap aerator"], ["caustic", "koyla", "gasket", "courier"]),
    ("KAPOOR DANI", ["kapoor.*dani", "camphor.*holder", "kapoor.*stand"], ["caustic", "koyla", "gasket", "courier"]),
    ("ROSE GOLD LIGHTER", ["rose gold.*lighter", "lighter.*rose gold"], ["caustic", "koyla", "gasket", "courier"]),

    # Bags
    ("MY 11x13-100PC", ["b0dnqh7r3c", "myn shipping courier bag 11x13", "11 x13 myt", "11x13.*myn", "myn.*11.*x.*13", "11x13.*myt"], ["caustic", "koyla", "gasket", "8x11", "14x16"]),
    ("MY 8x11-100PC", ["b0hfbxhw82", "b0dnqk3zbb", "paper courier bag 8 x11", "plastic courier bag 8x11", "8 x11.*pack of 100", "8x11.*100", "my 8x11", "myn.*paper.*8.*11", "myn.*plastic.*8.*11"], ["caustic", "koyla", "gasket", "14x16", "11x13"]),
    ("MY 13x14 + MY 14x16", ["my.*13.*x.*14.*my.*14.*x.*16", "my13x14", "my14x16", "my.*combo", "14x16.*_100", "b0dnqhmw5q.*14x16", "paper courier bag 14x16"], ["caustic", "koyla", "gasket", "courier", "11x13", "8x11"]),
    ("S-8x10=100PC", ["b0drzywpmt", "dm-glyy-u74z", "courier.*bag.*8.*x.*10.*100", "8x10.*100", "8 x 10.*100"], ["caustic", "koyla", "gasket", "courier"]),
    ("S-18x23-50PC", ["s.*18.*x.*23.*50", "18.*23.*50pc", "18x23.*bag"], ["caustic", "koyla", "gasket", "courier"]),
    ("S-14x17-50PC", ["s.*14.*x.*17.*50", "14.*17.*50pc", "14x17.*bag"], ["caustic", "koyla", "gasket", "courier"]),
    ("S-6x8-50PC", ["s.*6.*x.*8.*50", "6.*8.*50pc", "6x8.*bag"], ["caustic", "koyla", "gasket", "courier"]),
    ("SEAL-100PC", ["seal.*100pc", "sealing bag.*100", "self.*seal.*100"], ["caustic", "koyla", "gasket", "courier"]),
    ("AMAZON 10x12", ["amazon.*10.*x.*12", "10x12.*bag", "10.*12.*amazon"], ["caustic", "koyla", "gasket", "courier"]),
    ("AMAZON 11x13", ["amazon.*11.*x.*13", "11x13.*bag", "11.*13.*amazon"], ["caustic", "koyla", "gasket", "courier"]),
    ("POPULAR 4/5", ["popular.*4.*5", "popular bag.*4"], ["caustic", "koyla", "gasket", "courier"]),
    ("1.5-2PC", ["1.5.*2.*pc", "1.5.*bag.*2pc", "courier.*1.5"], ["caustic", "koyla", "gasket", "courier"]),

    # ── NEW RULES 30-AUG-2026 BATCH 2 ──────────────────────────────
    ("YELLOW-50", ["b0fdggd8lv", "7e-09wt-e1vt", "mvh ecom.*coal discs.*dhoop.*33 mm", "premium odourless coal discs.*dhoop.*33 mm", "odourless coal disc.*5", "pack of 5.*coal disc", "coal disc.*33mm.*5"], ["caustic", "koyla", "gasket", "battery", "3 roll", "30 disc", "b0f2ntp6lb"]),
    ("1632=2PC", ["cr-1632", "cr1632", "mvh ecom cr-1632", "3v lithium coin battery.*1632", "1632.*3v.*lithium"], ["caustic", "koyla", "gasket", "courier"]),
    ("SR927-5PC", ["sr927sw", "395 silver oxide", "premium sr927sw 395", "sr927.*silver oxide.*watch"], ["caustic", "koyla", "gasket", "courier"]),
    ("BUNGEE 8FT", ["b0dtpgjr1q", "bungee cord.*ropes.*8 feet", "8 feet.*bungee", "bungee.*8ft", "8ft.*bungee cord.*hooks"], ["caustic", "koyla", "gasket", "courier", "6 feet", "15 feet"]),
    ("K-30", ["b0f2ntp6lb", "magic coal 30", "coal.*30.*discs", "odourless charcoal.*dhoop.*30", "vibrantangan.*30", "charcoal tablets.*dhoop.*30", "bakhoor.*30.*disc"], ["caustic", "koyla", "gasket", "battery", "courier", "50", "60", "100", "b0f2p1529f", "b0f2p68rw8"]),
    ("K-50", ["b0f2p1529f", "mc 60", "coal.*50.*discs", "odourless charcoal.*dhoop.*50", "vibrantangan.*50", "charcoal.*bakhoor.*50"], ["caustic", "koyla", "gasket", "battery", "courier", "30", "100", "b0f2ntp6lb", "b0f2p68rw8"]),
    ("K-100", ["b0f2p68rw8", "5k-v8yt-zp6q", "coal.*100.*discs", "odourless charcoal.*dhoop.*100", "vibrantangan.*100"], ["caustic", "koyla", "gasket", "battery", "courier", "30", "50", "b0f2ntp6lb", "b0f2p1529f"]),
    ("BUTTERFLY SILICON 5-5.5L", ["b0fxy3gtym", "5&5.5 litre butterfly", "butterfly.*5.*5.5.*litre", "silicon gasket.*butterfly.*5", "replacement silicon.*butterfly.*5.5"], ["caustic", "koyla", "battery", "courier"]),
    ("PRESTIGE 5L GASKET", ["b0fxy5cmvn", "prestige popular 5 litre", "gasket.*prestige.*5", "prestige.*5.*gasket", "dont order.*prestige", "suitable gasket.*prestige popular 5"], ["caustic", "koyla", "battery", "courier"]),
    ("PRESTIGE 13CM", ["b0f92fszls", "allumiumum cooker.*13", "gasket.*13 cm", "pressure cooker rubber gasket.*13", "13 cm.*rubber gasket"], ["caustic", "koyla", "battery", "courier"]),
    ("HANDI VINOD 2.5L", ["b0g71hxgrx", "handi vinod 2.5ltr", "vinod.*handi.*2.5", "silicon gasket.*2.5.*vinod", "2.5 liter vinod plus handi"], ["caustic", "koyla", "battery", "courier"]),
    ("HANDI VINOD 3.5L", ["b0g71y9s7l", "handi vinod 3.5 ltr", "vinod.*handi.*3.5", "silicone gasket.*vinod.*3.5", "3.5 liter.*vinod.*handi"], ["caustic", "koyla", "battery", "courier"]),
    ("SILICON VINOD 3L OUTER", ["b0gdqc9y8t", "silicon.*vinod.*3.*litre.*outer", "silicon outer lid.*vinod.*3", "outer lid.*vinod.*3 litre"], ["caustic", "koyla", "battery", "courier"]),
    ("SURYA GASKET", ["b0gkq4sv3w", "surya.*gasket.*3l", "gasket.*surya.*3", "stainless steel.*surya.*3l"], ["caustic", "koyla", "battery", "courier"]),
    ("PRINTED BAG 10x12", ["b0f843zyh9", "printed packing bag 10x12", "ajios.*packing bag.*10x12", "printed.*bag.*10x12.*100"], ["caustic", "koyla", "gasket", "courier"]),
    ("SR521-5PC", ["b0f895xszw", "sr521sw 379 5 pc", "sr521sw.*379.*5", "silver oxide.*sr521", "seizaiken.*sr521.*5"], ["caustic", "koyla", "gasket", "courier"]),
    ("POD BAG 7x7", ["b0f848bq9x", "packing bag sk pod.*7x7", "52 micron.*7x7", "snap deals.*7x7", "pod.*7x7.*100"], ["caustic", "koyla", "gasket", "courier"]),
    ("POD BAG 9.5x12", ["b0f846mzh7", "packing bag sk pod.*9.5x12", "52 micron.*9.5x12", "snap deals.*9.5x12", "pod.*9.5.*12.*100"], ["caustic", "koyla", "gasket", "courier"]),
    ("TAP SPINDLE", ["plumber tap spindle", "spindle inner part", "tap spindle inner", "b0.*spindle.*tap"], ["caustic", "koyla", "gasket", "courier"]),
    ("MY 14x16-100PC", ["myn plastic courier bag 14x16", "myn.*14x16.*100", "plastic courier bag 14x16.*100", "14x16.*pack of 100"], ["caustic", "koyla", "gasket", "courier"]),
    ("S-6x8-50PC", ["b0drzydt54", "polybags.*6 x 8.*50", "shipping.*6.*8.*50", "packing.*6x8.*50"], ["caustic", "koyla", "gasket", "courier"]),
    ("HANGER CLIPS 36PC", ["b0dr28s1pw", "round hanger", "hanging clips.*storage box.*36", "multipurpose hanging clips.*36", "cloth hanger.*clips.*36"], ["caustic", "koyla", "gasket", "courier"]),
    ("SEAL-500PC", ["b0g64zml34", "500 seal", "postal bag sealing.*500", "garment.*bag sealing.*500", "sealing.*500"], ["caustic", "koyla", "gasket", "courier"]),
    ("CAPACITOR 25MFD", ["havells 25.*capacitor", "25.*µf.*capacitor", "25 µf capacitor 440vac", "capacitor.*25.*µf"], ["caustic", "koyla", "gasket", "courier"]),
    ("CR2430=2PC", ["cr2430", "copy line cr2430", "cr2430.*3v.*lithium", "lithium battery.*cr2430.*2"], ["caustic", "koyla", "gasket", "courier"]),
    ("KOYLA 500G", ["b0dr2pk51b", "charcoal koyla.*500gm", "koyla briquettes.*500", "natural wood charcoal.*500gm", "eco-friendly.*koyla.*500"], ["caustic", "koyla", "gasket", "battery", "courier"]),
    ("KOYLA 1KG", ["b0dr2nb6z2", "charcoal koyla.*1kg", "koyla briquettes.*1kg", "natural wood charcoal.*1kg", "eco-friendly.*koyla.*1kg"], ["caustic", "koyla", "gasket", "battery", "courier"]),
    ("TAG STRING 1000PC", ["b0f3j4cfgv", "ou-w4zp-n3rr", "hang tag string fasteners.*1000", "nylon cord.*1000", "clothing.*price tags.*1000"], ["caustic", "koyla", "gasket", "courier"]),
    ("BC BULB HOLDER", ["b.c. parallel adapter holder with bulb", "bc parallel adapter", "bulb holder.*bc", "parallel adapter.*bulb"], ["caustic", "koyla", "gasket", "courier"]),
    ("SR626-5PC", ["seizaiken sr626sw 377", "sr626sw.*377.*silver oxide", "seizaiken.*sr626.*5", "sr626sw.*watch battery.*5"], ["caustic", "koyla", "gasket", "courier"]),
    ("LR41-4PC", ["solutions lr41 battery ag3 lr736 392", "lr41.*ag3.*lr736.*392", "lr41.*battery.*ag3.*4"], ["caustic", "koyla", "gasket", "courier", "25pc", "100"]),
    ("3PIN CABLE 2.5M", ["2.5 meter electric cable cord", "3 pin wire.*tv.*cooler", "copy line.*2.5 meter.*cable", "electric cable.*3 pin.*2.5"], ["caustic", "koyla", "gasket", "courier"]),
    ("VIRGIN BAGS", ["plastic virgin bags", "multi-purpose.*food grade.*lldp", "copy line.*plastic virgin bags", "virgin bags.*food grade"], ["caustic", "koyla", "gasket", "courier"]),
    ("POD BAG 7x10", ["courier bags plain.*7x10.*50", "52 micron.*pod.*7x10", "plain.*pod.*7x10.*50"], ["caustic", "koyla", "gasket", "courier"]),
]

SORT_ORDER = [p for p, _, _ in RULES]


def classify_product(text):
    text_lower = text.lower()
    for code, must_contain, must_not_contain in RULES:
        match = any(re.search(k, text_lower) for k in must_contain)
        if not match:
            continue
        blocked = any(re.search(b, text_lower) for b in must_not_contain)
        if blocked:
            continue
        return code
    return "UNCLASSIFIED"


def get_inv_num(text):
    m = re.search(r'invoice number\s*[:\-]?\s*(IN-\d+)', text, re.IGNORECASE)
    return m.group(1) if m else "UNKNOWN"


def extract_qty(text):
    patterns = [
        r'qty[:\s]+(\d+)',
        r'quantity[:\s]+(\d+)',
        r'units?[:\s]+(\d+)',
        r'(\d+)\s*nos?\b',
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            q = int(m.group(1))
            if 1 <= q <= 20:
                return q
    return 1


def double_check(invoices):
    issues = []
    for inv in invoices:
        if inv['code'] == 'UNCLASSIFIED':
            issues.append({
                'inv_num': inv['inv_num'],
                'type': 'UNCLASSIFIED',
                'reason': 'no rule matched',
                'snippet': inv['text'][:200]
            })
        # Check for ambiguous
        text_lower = inv['text'].lower()
        matched = []
        for code, must_contain, must_not_contain in RULES:
            if any(re.search(k, text_lower) for k in must_contain):
                if not any(re.search(b, text_lower) for b in must_not_contain):
                    matched.append(code)
        if len(matched) > 1:
            issues.append({
                'inv_num': inv['inv_num'],
                'type': 'AMBIGUOUS',
                'reason': f'assigned {matched[0]}. Reason: {matched}',
                'snippet': inv['text'][:200]
            })
    return issues


def parse_pdf(pdf_bytes):
    if isinstance(pdf_bytes, str):
        with open(pdf_bytes, "rb") as f:
            pdf_bytes = f.read()
    doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    invoices = []
    label_page = None

    for i in range(len(doc)):
        page = doc[i]
        text = page.get_text()

        is_invoice = ("Tax Invoice" in text or "Bill of Supply" in text or "Cash Memo" in text) and ("amazon" in text.lower() or "sold by" in text.lower())
        is_label = not is_invoice and len(text.split()) < 150

        if is_label:
            label_page = i
        elif is_invoice:
            code = classify_product(text)
            qty = extract_qty(text)
            inv_num = get_inv_num(text)
            invoices.append({
                "label": label_page if label_page is not None else i,
                "invoice": i,
                "code": code,
                "qty": qty,
                "inv_num": inv_num,
                "text": text,
                "product": code,
                "invoices": [i],
            })
            label_page = None

    doc.close()
    return invoices


def build_output_pdf(input_path, output_path, groups):
    reader = _R(input_path)

    def sort_key(g):
        p = g['product']
        return (SORT_ORDER.index(p) if p in SORT_ORDER else len(SORT_ORDER), g['inv_num'])

    groups_sorted = sorted(groups, key=sort_key)

    writer = _W()
    for g in groups_sorted:
        writer.add_page(reader.pages[g['label']])
        for inv_idx in g['invoices']:
            inv_page = reader.pages[inv_idx]
            pw = float(inv_page.mediabox.width)
            ph = float(inv_page.mediabox.height)
            overlay = create_overlay(pw, ph, g['product'], g['qty'])
            inv_page.merge_page(overlay.pages[0])
            writer.add_page(inv_page)

    with open(output_path, 'wb') as f:
        writer.write(f)
    return output_path


def create_overlay(width, height, code, qty):
    doc = pymupdf.open()
    page = doc.new_page(width=width, height=height)

    # EXACT original format:
    # QTY:1 box: Rect(30, 772, 430, 822) — fixed position
    # QTY:2 box: Rect(30, 744, 430, 822) — taller for stars
    box_x0 = 30.0
    box_x1 = 430.0
    box_y1 = 822.0
    box_y0 = 772.0 if qty <= 1 else 744.0
    box_rect = pymupdf.Rect(box_x0, box_y0, box_x1, box_y1)

    # Black background
    page.draw_rect(box_rect, color=(0, 0, 0), fill=(0, 0, 0))

    # Code left, QTY right — size 26, white
    text_y = box_y0 + 36
    page.insert_text((box_x0 + 10, text_y), code, fontsize=26, color=(1, 1, 1), fontname="helv")
    qty_text = f"QTY: {qty}"
    page.insert_text((box_x1 - 120, text_y), qty_text, fontsize=26, color=(1, 1, 1), fontname="helv")

    # Yellow stars below if qty > 1
    if qty > 1:
        stars = "★" * qty
        page.insert_text((box_x0 + 10, box_y0 + 64), stars, fontsize=24, color=(1, 1, 0), fontname="helv")

    buf = io.BytesIO()
    doc.save(buf)
    doc.close()
    buf.seek(0)
    return _R(buf)
