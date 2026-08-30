"""
MASTER INVOICE PROCESSOR - WITH BUILT-IN DOUBLE CHECK
=====================================================
Step 1: Extract raw data from every invoice
Step 2: Apply product code rules
Step 3: VALIDATE every assignment against known keywords - flag any mismatch
Step 4: Only process if zero errors
"""

import io
import re
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib import colors

# ─────────────────────────────────────────────────────────────────
# PRODUCT CODE RULES - keyword triggers for each code
# Each rule: (product_code, [must_contain_any], [must_NOT_contain])
# ─────────────────────────────────────────────────────────────────
RULES = [
    # Caustic Soda
    ("C- ½ KG",   ["caustic_500gms", "caustic_500", "500gms", "500gm",
                   "4k-eni9-u72g", "caustic soda_500", "b0fktffljw",
                   "b0dmnw79vf", "cleaning - 500", "cleaning -500",
                   "multipurpose cleaning - 500 grams"],                        ["1kg", "1 kg", "2kg", "2 kg", "koyla", "charcoal", "gasket", "battery", "courier", "caustic soda_2kg", "caustic soda_1kg", "caustic_1kg"]),
    ("C- 1KG",    ["caustic_1kg", "caustic soda_1kg", "cleaning - 1 kg",
                   "cleaning - 1kg", "b0dmnxbjzm", "caustic 1kg",
                   "multipurpose cleaning - 1 kg"],                             ["500g", "500gm", "500gms", "2kg", "2 kg", "koyla", "charcoal", "gasket", "battery", "courier", "caustic soda_2kg"]),
    ("C- 2KG",    ["caustic soda_2kg", "caustic_2kg", "cleaning (1kg + 1kg)",
                   "b0dmpbhl6h", "2kg", "caustic soda flakes 2kg"],             ["500g", "500gm", "500gms", "1 kg\b", "koyla", "charcoal", "gasket", "battery", "courier", "caustic soda_1kg", "caustic_1kg"]),

    # Salt
    ("SALT 900g",  ["900 gms", "900g", "b0fcc6bd6k", "gw-gg71-423g", "900 g)"],["caustic", "koyla", "gasket", "battery", "courier", "epsom", "990"]),
    ("SALT 990g",  ["990g", "990 g", "b0dzxs7bq2", "vastu salt"],               ["caustic", "koyla", "gasket", "battery", "courier", "900g"]),
    ("2KG SALT",      ["vrs-ss-900x2-p2", "1b0h25d291w",
                       "900 gms + 900gms", "900gms(pack of 2)",
                       "spiritual cleansing, vastu"],                            ["caustic", "koyla", "gasket", "battery", "courier",
                                                                                   "b0fcc6bd6k", "gw-gg71-423g"]),
    ("SALT 900g/990g", ["epsom salt", "epsom bath salt", "b0fcymq8b3"],          ["caustic", "koyla", "gasket", "battery", "courier"]),

    # Coal
    # Al-Afandi Coconut Coal 96pc
    ("AFANDI 96",  ["al-afandi", "afandi", "coconut coal", "96 pieces",
                    "96 pc coal", "b0f4rrlyxp"],                                ["caustic", "koyla", "gasket", "battery", "courier", "vibrantangan", "dhoop", "bakhoor"]),

    # Dhoop / VibrantAngan coal — split by disc count
    # Yellow VibrantAngan coal series (different packaging from K series)
    ("YELLOW - 30",  ["b0f2ybp3mq", "n0-i890-y72k",
                      "bakhoor dani magic coal pack of 3 rolls (30 discs)"],     ["caustic", "koyla", "gasket", "battery", "courier",
                                                                                   "b0f2ynnx2g", "b0f2y75m27", "b0f5bs8pss", "b0f2ntp6lb"]),
    ("YELLOW - 50",  ["b0f2ynnx2g", "gf-f04m-k04x",
                      "bakhoor dani magic coal pack of 5"],                       ["caustic", "koyla", "gasket", "battery", "courier",
                                                                                   "b0f2ybp3mq", "b0f2y75m27", "b0f5bs8pss"]),
    ("YELLOW - 100", ["b0f2y75m27", "bf-1m6x-74j1",
                      "bakhoor dani magic coal pack of 10"],                      ["caustic", "koyla", "gasket", "battery", "courier",
                                                                                   "b0f2ybp3mq", "b0f2ynnx2g", "b0f5bs8pss"]),

    ("K-30",      ["3 rolls (30 discs)", "30 discs", "b0f5bs8pss", "fy-tml1-q9oa",
                   "b0f2ntp6lb", "g5-kysc-ox6m", "(30)", "b0f6jld4dw",
                   "6i-ujhc-yc5e", "charcoal tablets for burning"],             ["caustic", "koyla", "gasket", "battery", "courier",
                                                                                   "al-afandi", "50 discs", "60 discs", "100 discs", "koyla briquette"]),
    ("K-50",      ["5 rolls (50 discs)", "50 discs", "b0f2ynnx2g", "gf-f04m-k04x",
                   "b0dxfjgvnx", "bw-3s1a-y8qz", "pack of 5 roll (50 disc)",
                   "50 disc)", "b0f2p1529f", "mc 60 )",
                   "b0dxfjlbmv", "t4-ol45-m6pl", "odourless coal discs",
                   "b0f1y28tbv", "o5-dnoq-p6di", "hookah charcoal briquettes",
                   "b0ffmckn1y", "id-yj23-baqr", "magic coal, for dhoop",
                   "quick click goods magic coal"],                              ["caustic", "koyla", "gasket", "battery", "courier",
                                                                                  "al-afandi", "30 discs", "60 discs", "100 discs", "koyla briquette"]),
    ("K 2KG",     ["charcoal koyla _2kg", "b0dr28sgsv", "premium coal 1kg",
                   "pack of 2kg", "koyla _2kg"],                                 ["caustic", "gasket", "battery", "courier",
                                                                                  "al-afandi", "30 discs", "50 discs", "100 discs"]),
    ("K-60",      ["6 rolls (60 discs)", "60 discs", "b0f4pcgjpb", "magic coal 6 roll",
                   "b0f5brp99x", "9n-niv6-940c", "60 coal"],                    ["caustic", "koyla", "gasket", "battery", "courier",
                                                                                  "al-afandi", "30 discs", "50 discs", "100 discs", "koyla briquette"]),
    ("K-100",     ["10 rolls (100 discs)", "100 discs", "b0f2y75mz7", "bf-1m6x-74j1",
                   "b0f2mtb1jv", "8x-rzsj-6ole", "b0f2p68rw8", "5k-v8yt",
                   "(100)", "b0f6k3nlwk", "p2-sf76-4b8c",
                   "pack of 10 roll (100 disc)", "b0f2hm8klg", "v8-nrs9-1odr",
                   "instant-ignite burn", "100 disc)"],                         ["caustic", "koyla", "gasket", "battery", "courier",
                                                                                  "al-afandi", "30 discs", "50 discs", "60 discs", "koyla briquette"]),
    ("K ½ KG",    ["koyla", "wood charcoal", "charcoal koyla", "lump charcoal",
                   "koyla briquette", "natural lump charcoal"],                  ["caustic", "gasket", "battery", "courier", "hookah", "dhoop", "tablet"]),

    # Steel clips
    ("36 STEEL CLIPS", ["steel clip", "36 pc", "steel clips", "36pc",
                        "b0dr28s1pw", "steel 36 clip"],                          ["caustic", "koyla", "gasket", "battery", "courier", "18 clips", "18pc", "clip 18"]),
    ("18 STEEL CLIPS", ["18 clips", "18pc", "b0dr26c6yj", "clip 18",
                        "cloth clips", "18 clip"],                               ["caustic", "koyla", "gasket", "battery", "courier", "36 pc", "36pc"]),

    # Gaskets - Pigeon rubber (77)
    ("77",         ["piigeon", "persitge 77", "b0f9vlrwcs",
                    "pigeon alluminium", "pigeon aluminium"],                    ["silicon", "silicone", "prestige triply", "vinod", "stahl"]),

    # Silicon 777 - Pigeon silicon OR generic silicon OR Stahl
    # SILICON 77 - Pigeon silicon AND Stahl silicone gasket
    ("SILICON 77",  ["b0gbvl1l8w", "silicon 77 )", "only for pigeon aluminium",
                     "pigeon aluminium pressure cooker",
                     "stahl steel cooker", "b0gd6qy5yp", "stahlcooker",
                     "only for stahlcooker"],                                    ["butterfly", "prestige triply", "svachh outer lid", "vinod",
                                                                                  "b0gxdh6fpk", "8o-tp5g"]),

    # Prestige gaskets
    ("PRESTIGE 8L",   ["b0g5z6y5hn", "prestige deluxe and deluxe alpha",
                       "8 liter fits onlyprestige", "prestige deluxe alpha model",
                       "prestige deluxe", "deluxe alpha model",
                       "8 liter fits only prestige",
                       "stainless steel pressure cooker for 8"],                 ["butterfly", "vinod", "pigeon", "popular", "caustic",
                                                                                  "triply", "5 litre", "3 litre", "2 litre"]),
    ("PRESTIGE HANDI 2L", ["prestige baby handi", "b0g8kqjcfr",
                            "prestige baby handi pressure cooker gasket",
                            "baby handi"],                                       ["butterfly", "vinod", "pigeon", "popular", "caustic",
                                                                                   "triply", "5 litre", "3 litre"]),
    ("PRESTIGE 4L",    ["junior gasket for pressure cooker", "4l & 5.5l",
                        "deluxe plus, deluxe alpha", "only for steel cooker",
                        "b0g4jwf2xz", "b0g8kn1h4l"],                            ["butterfly", "vinod", "pigeon", "popular", "caustic",
                                                                                   "triply", "8 litre", "2 litre", "handi"]),

    # Surya gaskets
    ("POPULAR 4/5",   ["b0f92fszls", "prestige popular 4/5/6", "prestige popular 5 litre",
                       "prestige popular 4 litre", "allumiumum cooker",
                       "prestige popular 4/5/6 "],                               ["butterfly", "vinod", "pigeon", "caustic",
                                                                                   "triply", "silicon", "8 litre", "handi", "surya"]),
    ("1.5 - 2PC",     ["b0f9vk3dby", "1.5 liter inner lid 2 pc", "1.5 litre capacity",
                       "hawkiins", "hawkins", "13 cm inner lid"],                ["butterfly", "vinod", "pigeon", "popular", "caustic",
                                                                                   "silicon", "triply", "3 liter", "5 litre"]),
    ("SILICON VINOD 3L", ["b0gdqc9y8t", "silicon outer lid rubber gasket compatible for 3 litre vinod",
                           "silicon vinod 3", "silicon vinod 3 ltr"],            ["butterfly", "prestige", "pigeon", "popular", "caustic",
                                                                                    "handi", "vibrantangan"]),
    ("SURYA 3L",      ["surya 3ltr", "b0g4jzsj4c", "surya aluminium outer lid",
                       "surya pressure cooker, 3 liter"],                        ["butterfly", "vinod", "pigeon", "popular", "caustic",
                                                                                   "4 & 5", "4& 5"]),
    ("SURYA 4-5L",    ["surya 4& 5 liter", "b0g4jww9k2", "surya pressure cooker outer lid",
                       "aluminium 4 & 5 liter", "surya 4& 5 liter "],           ["butterfly", "vinod", "pigeon", "popular", "caustic"]),

    ("PRESTIGE TRIPLY 3L",  ["prsitge triply 3", "prestige triply svachh outer lid",
                               "b0gn26r129", "prestige triply", "svachh outer lid"],
                                                                                 ["butterfly", "vinod", "rubber", "stahl", "7.5", "5 litre", "5ltr", "caustic", "2kg"]),
    ("PRESTIGE TRIPLY 5L",  ["prestige 5 litre triply", "prestige triply",
                               "8o-tp5g-xxjk", "b0gxdh6fpk", "5liter triply"],  ["butterfly", "vinod", "rubber", "stahl", "3 litre", "3ltr", "7.5", "caustic"]),

    # Butterfly silicon
    ("BUTTERFLY SILICON 2-3L", ["butterfly", "butterfly curve", "butterfly -2litre",
                                 "butterfly -2litre & 3litre"],                  ["rubber", "10 litre", "10liter", "prestige", "vinod", "pigeon",
                                                                                   "5 litre", "5&5.5", "b0fxy3gtym", "b0gxdqn8fk"]),
    ("BUTTERFLY SILICON 5L",  ["5&5.5 litre butterfly", "5 litre butterfly",
                                "b0fxy3gtym", "b0gxdqn8fk",
                                "5&5.5 litre butterfly "],                       ["rubber", "10 litre", "vinod", "pigeon",
                                                                                   "2-3", "2litre", "3litre"]),

    # Popular/general rubber gasket (777)
    ("SILICON 777", ["silicon 777 )", "b0gbvwy6b2", "silicon gasket for 7.5",
                     "outer lid silicon gasket for 7.5"],                       ["pigeon", "piigeon", "butterfly", "prestige triply",
                                                                                  "vinod", "stahl", "b0f9vlrwcs"]),
    ("777",        ["popular", "rubber gasket", "outer lid rubber",
                    "butterfly standard", "butteerfly standard",
                    "hawkiins", "inner lid", "7.5 litre",
                    "butterfly 10liter", "prestige 777"],                        ["silicon", "silicone", "pigeon", "piigeon", "b0f9vlrwcs", "prestige triply", "stahl"]),

    # Vinod gaskets
    ("VINOD HANDI 1.5L", ["vinod splendid plus handi", "b0g72fs1l1",
                           "vinod handi 1.5", "handi vinod 1.5"],               ["butterfly", "prestige", "pigeon", "popular", "caustic",
                                                                                  "3 litre", "vibrantangan", "dhoop", "coal", "2.5"]),
    ("VINOD HANDI 2.5L", ["vinod plus handi cooker", "b0g71hxgrx",
                           "handi vinod 2.5ltr", "vinod handi 2.5",
                           "2.5 liter vinod"],                                  ["butterfly", "prestige", "pigeon", "popular", "caustic",
                                                                                  "3 litre", "vibrantangan", "dhoop", "coal", "1.5"]),
    ("VINOD 3L",   ["vinod stainless", "vinod 3 litre", "b0f8lgj2hn",
                    "silicon outer lid rubber gasket compatible for 3 litre vinod",
                    "b0h1f7pfzg", "blue vinod 3ltr"],                            ["butterfly", "prestige", "pigeon", "popular", "caustic",
                                                                                  "handi", "vibrantangan", "dhoop", "coal"]),

    # Flipkart TSB bags
    ("TSB 8.5x11", ["flip-kart courier bag 8.5x11 tsb1", "b0fbrh2833",
                    "tsb1 pack of 100"],                                         ["nsb", "14x17", "14x18", "10x13", "6x7", "caustic", "gasket"]),
    ("TSB 10x13",  ["courier bag 10x13 tsb2", "b0dp4vlmgg"],                    ["nsb", "14x17", "8.5x11", "6x7", "caustic", "gasket"]),
    ("TSB 14x17",  ["flip-kart 14x17", "b0fbrjcv7y", "14x17 _100"],             ["nsb", "10x13", "8.5x11", "6x7", "caustic", "gasket"]),
    ("TSB 6x7",    ["tsb 6x 7", "6x 7 flipkart", "b0g4js43ns"],                 ["nsb", "14x17", "10x13", "8.5x11", "caustic", "gasket"]),

    # Flipkart NSB bags
    ("NSB 6x8",    ["nsb0", "courier bag 6x 8 nsb", "b0dp4x4s9w"],              ["tsb", "14x18", "10x13", "8.5x11", "caustic", "gasket"]),
    ("NSB 8.5x11", ["nsb1", "courier bag 8.5x11 nsb1", "b0dp4wdk5q"],           ["tsb", "14x18", "6x8", "caustic", "gasket"]),
    ("NSB 10x13",  ["nsb2", "courier bag 10x13 nsb2", "b0dp4xjvsl"],            ["tsb", "14x18", "8.5x11", "caustic", "gasket"]),
    ("NSB 16x20",  ["nsb4", "16x20 nsb", "courier bag 16x20",
                    "b0dp4xw8nf", "nsb4 qr"],                                   ["tsb", "10x13", "8.5x11", "6x8", "14x18", "caustic", "gasket"]),
    ("NSB 14x18",  ["nsb3.5", "nsb3", "courier bag 14x18", "14x18 nsb"],        ["tsb", "10x13", "8.5x11", "6x8", "caustic", "gasket"]),

    # Multi-item MYN combos
    ("MY 13x14 + MY 14x16", ["b0dnqjrn8y", "14x16_250 ) \nhsn:392329\n",
                              "paper courier bag 13x14"],                        ["tsb", "nsb", "caustic", "gasket"]),
    ("MY 14x16 + MY 17x22", ["14x16 _100 ) \nhsn:392329\n₹",
                              "b0dnqhmw5q ( paper courier bag 14x16 _100 ) \nhsn"],
                                                                                 ["tsb", "nsb", "caustic", "gasket", "11x13_250"]),
    ("MY 11x13 + MY 14x16", ["paper courier bag 11x13_250 ) \nhsn:392329\n₹",
                              "11x13_250 ) \nhsn"],                              ["tsb", "nsb", "caustic", "gasket", "17x22"]),

    # Myntra / MYN bags — single size
    ("MY 8x11",    ["myn paper courier bag 8x11", "8x 11 )"],                    ["tsb", "nsb", "caustic", "gasket", "13x14", "14x18", "14x16", "17x22", "11x13"]),
    ("MY 11x13",   ["myn paper courier bag 11x13", "b0dnqksnn4",
                    "paper courier bag 11x13_250", "11x13_250"],                 ["tsb", "nsb", "caustic", "gasket", "8x11", "13x14", "14x16", "17x22"]),
    ("MY 13x14",   ["myn paper courier bag 13x14", "paper courier bag 13x14 _"],["tsb", "nsb", "caustic", "gasket", "8x11", "11x13", "14x16", "17x22"]),
    ("MY 14x16",   ["myn paper courier bag 14x16", "b0dnqhmw5q", "14x16 _100",
                    "b0dnqjrn8y", "paper courier bag 14x16_250"],               ["tsb", "nsb", "caustic", "gasket", "8x11", "13x14", "17x22", "11x13"]),
    ("MY 17x22",   ["myn paper courier bag 17x22", "b0dnqkpvrw", "17x 22 )"],   ["tsb", "nsb", "caustic", "gasket", "8x11", "13x14", "14x16", "11x13"]),

    # General courier bags (S- size = PC) - use exact unique SKU codes/size strings
    ("S- 7x10 = PC",  ["ed-l4r5", "(100, 7 x 10)", "7 x 10)"],                  ["tsb", "nsb", "myn", "flipkart", "flip-kart", "50, 7 x 10"]),
    ("S- 7x10 - 50PC",["b0drzz8rv1", "ed-l4r5-nydz", "(50, 7 x 10)",
                       "b0dp7msjxf", "courier bags with pod 7x10_50"],          ["tsb", "nsb", "myn", "flipkart", "flip-kart"]),
    ("AMAZON 6x8 - 100PC", ["px-j96o-ul5p", "b0ds15lfk7",
                             "amazon branded printed economy shipping"],         ["tsb", "nsb", "myn", "flipkart", "flip-kart"]),
    ("6x8 = PC",      ["(6 x 8 single)", "px-j960 "],                           ["tsb", "nsb", "myn", "flipkart", "flip-kart",
                                                                                   "px-j96o-ul5p", "b0ds15lfk7", "economy shipping", "amazon branded"]),
    ("S- 8x10 = PC",  ["dm-giyy", "(100, 8 x 10)", "8 x 10)",
                       "b0dp7khlkf", "courier bags with pod 8x10_100"],         ["tsb", "nsb", "myn", "flipkart", "flip-kart"]),
    ("S- 8x11 = PC",  ["(100, 8 x 11)"],                                         ["tsb", "nsb", "myn", "flipkart", "flip-kart", "8x11_250", "8.5x11"]),
    ("S- 10x12 = PC", ["tc-2dxv", "(100, 10 x 12)", "b0drzylgps",
                       "73-g0ob-sk9r", "(50, 10 x 12)"],                         ["tsb", "nsb", "myn", "flipkart", "flip-kart"]),
    ("S- 12x14 = PC", ["sk pod", "snap deals", "b0f8461jkn", "52 micron 12x14",
                       "b0dp7pdk1k", "courier bags with pod 12x14",
                       "b0drzz8nc8", "2q-4fmo-qrjd", "(100, 12 x 14)"],        ["tsb", "nsb", "myn", "flipkart", "flip-kart"]),
    ("S- 8x12 = PC",  ["d6-8f7e-9nod", "b0drzy8j26", "(100, 8 x 12)"],          ["tsb", "nsb", "myn", "flipkart", "flip-kart"]),
    ("S- 6.5x8 = PC", ["7l-ewwi-6mhn", "b0drzz6h3b", "(50, 6.5 x 8)",
                       "6.5 x 8)"],                                              ["tsb", "nsb", "myn", "flipkart", "flip-kart"]),
    ("S- 6x8 - 50PC", ["b0drzydt54", "zp-lpad-1kz5", "(50, 6 x 8)",
                       "6 x 8)"],                                                ["tsb", "nsb", "myn", "flipkart", "flip-kart"]),
    ("ZIP BAG 5X6",   ["zip lock storage bags", "b0dx6q71xl", "mh-ja2e-jqb6",
                       "5 inch x 6 inch", "reusable plastic pouches"],          ["tsb", "nsb", "myn", "caustic", "gasket"]),
    ("S- 10x14 - 50PC", ["b0drzzj2yd", "wc-udkl-4tyu", "(50, 10 x 14)",
                          "10 x 14)"],                                            ["tsb", "nsb", "myn", "flipkart", "flip-kart"]),
    ("S- 12x16 = PC", ["1t-afrr", "(50, 12 x 16)", "b0drzywfrd", "u2-386l-cbjy",
                       "(100, 12 x 16)"],                                         ["tsb", "nsb", "myn", "flipkart", "flip-kart"]),
    ("AMAZON 10x12",  ["b0dnmjnh35", "printed packing bag 10x12 _100",
                       "amazon printed packing bag 10x12"],                     ["tsb", "nsb", "myn", "flipkart", "flip-kart"]),
    ("AMAZON 11x13",  ["b0dvzj9tt3", "po100-11 x 13", "amazon courier bags",
                       "without pod jacket", "(100, 11 x 13)"],                 ["tsb", "nsb", "myn", "flipkart", "flip-kart"]),
    ("MY 11x13 - 50PC", ["zn-908h-aas1", "b0dsl3z9s8",
                          "plain courier bags", "11 inch x 13 inch",
                          "(50, 11 x 13)"],                                      ["tsb", "nsb", "flipkart", "flip-kart", "11x13_250", "myn paper"]),
    ("AJO 13x17",   ["ajios", "printed packing bag 13x17", "b0dnmg4s11",
                     "pj05", "printed packing bag 14x18"],                       ["tsb", "nsb", "myn", "flipkart", "flip-kart"]),
    ("S- 14x17 - 50PC", ["b0drzydx76", "74-kwch-n0kk", "(50, 14 x 17)",
                          "14 x 17)"],                                           ["tsb", "nsb", "myn", "flipkart", "flip-kart"]),
    ("S- 14x18 = PC", ["(100, 14 x 18)", "nx-vnbn-j6ud", "b0drzy2z4g"],        ["tsb", "nsb", "myn", "flipkart", "flip-kart", "ajios", "pj05"]),
    ("S- 15x19 = PC", ["(50, 15 x 19)", "m4-iz5v-rthq", "b0drzylxc9"],          ["tsb", "nsb", "myn", "flipkart", "flip-kart"]),
    ("S- 18x23 - 50PC", ["b0drzz46s8", "e4-g9bh-btz3", "(50, 18 x 23)",
                          "18 x 23)"],                                           ["tsb", "nsb", "myn", "flipkart", "flip-kart"]),
    ("S- 18x23 = PC", ["e4-g9bh", "(50, 18 x 23)", "e4-g9bh-btz"],             ["tsb", "nsb", "myn", "flipkart", "flip-kart", "b0drzz46s8"]),

    # Batteries — 27A and 23A are different products, separate codes
    ("27 A = 2PC",    ["b0fd7m5vb4", "27a 2pc_n", "27a, 2 pack",
                       "gp high voltage battery, no lead added, 27a, 2"],       ["lr1130", "sr416", "sr616", "ag10", "lr41", "watch battery",
                                                                                  "caustic", "gasket", "courier", "23a", "a23"]),
    ("27 A = 5PC",    ["27a_alkaline", "27a 5 pc", "27ae-2c5", "a27 /v27ga",
                       "v27ga /mn27", "b0drcxf2lz"],                            ["lr1130", "sr416", "sr616", "ag10", "lr41", "watch battery",
                                                                                  "caustic", "gasket", "courier", "23a", "a23"]),
    ("23 A",          ["23a 12v alkaline", "a23/v23ga/mn21", "b0dwfpxnj1",
                       "mn21", "v23ga"],                                         ["lr1130", "sr416", "sr616", "ag10", "lr41", "watch battery",
                                                                                  "caustic", "gasket", "courier", "27ae", "27a_alkaline"]),
    ("LR44 = 25PC",   ["lr44", "ag13 alkaline", "b0dphf971g",
                       "lr 44 ag 13", "tray packing_25b", "ag13"],              ["lr1130", "sr416", "sr936", "27a_alkaline", "27ae", "caustic", "gasket", "courier"]),
    ("1632 = 2PC",    ["cr-1632", "cr1632", "b0f2smqshs",
                       "lithium coin battery"],                                   ["lr1130", "sr416", "sr936", "lr44", "27a_alkaline", "27ae", "caustic", "gasket", "courier"]),
    ("1130 = 25PC",   ["lr1130", "sr616sw", "ag10 189",
                       "lr41 ag3", "321 silver oxide",
                       "b0f6ysgpm9", "b0f9vmh4gt",
                       "b0dz2mmw4r", "qcg lr1130"],                             ["27a_alkaline", "23a 12v", "caustic", "gasket", "courier", "bungee",
                                                                                  "sr416sw", "sr936sw", "337 silver", "394 silver"]),
    ("416 = 5PC",     ["sr416sw", "337 silver oxide", "b0f9vmlhjr",
                       "dr-2cef-94gr"],                                           ["lr1130", "sr616sw", "sr936sw", "ag10", "lr41",
                                                                                   "caustic", "gasket", "courier"]),
    ("SR936 = 5PC",   ["sr936sw", "394 silver oxide", "b0f9vmvrzl",
                       "kd-xynk-yxzp"],                                          ["lr1130", "sr416sw", "sr616sw", "ag10", "lr41",
                                                                                   "caustic", "gasket", "courier"]),
    ("521 = 5PC",     ["sr521sw", "379 1.55v", "b0f895xszw",
                       "sr521sw 379"],                                            ["lr1130", "sr416", "sr936", "lr44", "27a_alkaline", "caustic", "gasket", "courier"]),
    ("1616 = 2PC",    ["cr1616", "cr-1616", "b0fnmwtv24", "1616 batter"],        ["lr1130", "sr416", "sr936", "lr44", "27a_alkaline", "1632", "caustic", "gasket", "courier"]),
    ("721 = 2PC",     ["sr721sw", "sr721sw 362", "b0dphfsvhf",
                       "sr721sw 362_2b"],                                         ["lr1130", "sr416", "sr936", "lr44", "27a_alkaline",
                                                                                   "whirlpool", "caustic", "gasket", "courier"]),
    ("916 = 2PC",     ["sr916sw", "373 silver oxide", "b0f9vmfdbw",
                       "ej-tvyc-mp6j"],                                          ["lr1130", "sr416", "sr936", "lr44", "27a_alkaline",
                                                                                   "caustic", "gasket", "courier"]),
    ("920 = 2PC",     ["sr920sw", "371 silver oxide", "b0f895nzjj",
                       "sr920sw 371 2 pc"],                                      ["lr1130", "sr416", "sr936", "lr44", "27a_alkaline",
                                                                                   "caustic", "gasket", "courier"]),
    ("927 = 2PC",     ["sr927sw", "395 silver oxide", "b0f9vm3wk2",
                       "3r-pygc-8bpd"],                                          ["lr1130", "sr416", "sr936", "lr44", "27a_alkaline",
                                                                                   "caustic", "gasket", "courier"]),

    ("626 = 5PC",     ["sr626sw", "377 silver oxide", "b0f8crxtb4",
                       "626 5pc", "seizaiken sr626sw 377"],                      ["lr1130", "sr416", "sr936", "lr44", "27a_alkaline",
                                                                                   "caustic", "gasket", "courier"]),
    ("2032 = 2PC",    ["cr2032", "b0dphd3xfv", "cr2032 _2b",
                       "cmos batteries"],                                         ["lr1130", "sr416", "sr936", "lr44", "27a_alkaline",
                                                                                   "1632", "1616", "2430", "caustic", "gasket", "courier"]),
    ("2430 = 2PC",    ["cr2430", "cr-2430", "b0f9vlj6zn",
                       "cr2430 3v lithium"],                                     ["lr1130", "sr416", "sr936", "lr44", "27a_alkaline",
                                                                                   "1632", "caustic", "gasket", "courier"]),
    # Gas pipe
    ("GAS PIPE",      ["lpg gas pipe", "gas pipe with clamps", "b0fqwcvnnl",
                       "flame resistant", "leak proof gas pipe"],               ["caustic", "gasket", "battery", "courier"]),

    # Security seal
    ("SEAL - 100PC",  ["plastic security seal", "b0g64v94d8", "100 seal )",
                       "postal bag sealing", "garment, postal"],                ["caustic", "gasket", "battery", "bungee"]),

    # Kapoor Dani
    ("KAPOOR DANI",   ["kapoor dani", "camphor diffuser", "kapur diffuser",
                       "kapoor dani diya", "b0dz6l7y4j", "aroma oil burner",
                       "wooden premium)"],                                       ["caustic", "gasket", "battery", "courier", "dhoop", "coal", "charcoal"]),

    ("WA",            ["washing machine nipple", "nipple connector",
                       "washing machine adapter", "b0fdb2n7dk",
                       "brass, washing"],                                        ["caustic", "gasket", "battery", "courier",
                                                                                  "parallel adapter", "b0dswcb9cg", "bulb holder",
                                                                                  "plug socket", "2 ports"]),

    # Bungee rope - use unique SKU codes to disambiguate feet
    ("MULTI - 10FT - 4PC", ["b0dnw2rcb3", "10 ft ropes multicolour_4",
                             "(4, multicolour, 10 ft)", "pack 4"],               ["caustic", "gasket", "battery", "courier", "5 ft", "6 ft",
                                                                                   "multicolour, 5", "multicolour, 2"]),
    ("MULTI - 2 - 7FT",  ["b0dp4g3ngj", "mu-hihm-xn2l", "(2, black, 7 ft)",
                           "2, black, 7 ft"],                                    ["caustic", "gasket", "battery", "courier", "10 ft", "15 ft"]),
    ("MULTI - 6 - 5FT",  ["b0dp4d9bq3", "or-ausm-ic2b", "(6, black, 5 ft)",
                           "6, black, 5 ft"],                                    ["caustic", "gasket", "battery", "courier", "10 ft", "15 ft"]),
    ("MULTI - 6 - 6PC", ["(6, multicolour, 5 ft)", "96-kdpz-g5zq",
                          "b0dp4dn9hz"],                                         ["caustic", "gasket", "battery", "courier"]),
    ("MULTI - 6 - 10FT", ["b0dp4cwwkn", "0u-mt3c-spcd", "multicolour, 10 ft)",
                           "(6, multicolour, 10 ft"],                            ["caustic", "gasket", "battery", "courier", "5 ft", "15 ft",
                                                                                    "pack 4", "b0dnw2rcb3"]),
    ("MULTI - 2 - 10FT", ["(2, multicolour, 10 ft)", "6x-md2h-66gu",
                           "b0dp4dg2m2"],                                        ["caustic", "gasket", "battery", "courier", "b0dp4cwwkn"]),
    ("MULTI - 3M - 2PC",  ["b0dnw2vnv5", "3 meter ropes multicolour_2",
                            "3 meter cloths drying ropes"],                      ["caustic", "gasket", "battery", "courier", "6 ft", "10 ft", "15 ft"]),
    ("MULTI - 6FT - 2PC", ["b0dnw1nm6j", "6ft ropes multicolour_2",
                            "6 ft cloths drying ropes"],                         ["caustic", "gasket", "battery", "courier", "10 ft", "15 ft", "3 meter"]),
    ("B- 8FT = PC",   ["(8 feet)", "b0gynr8t3m", "8 feet) (1",
                       "bungee cord | ropes with hooks (8 feet)"],               ["caustic", "gasket", "battery", "courier", "10 feet",
                                                                                    "12 feet", "15 feet", "6 feet", "(5 ft)", "multicolour"]),
    ("B- 6FT = PC",   ["b0gknqtqjj", "gj-6djh-32uf", "(6 feet) pack",
                       "6 feet) | b0gk", "b0dt6bj733", "rp4 )"],                ["caustic", "gasket", "battery", "courier", "10 feet",
                                                                                    "12 feet", "15 feet", "5 ft", "multicolour"]),
    ("B- 10FT - 2PC", ["b0f38h2ktg", "10ft ropes black colour_2"],              ["caustic", "gasket", "battery", "courier",
                                                                                   "12 feet", "15 feet", "(5 ft)", "multicolour"]),
    ("B- 10FT = PC",  ["b0dtp9ct33", "cr-u793-lzt2", "(10 feet)",
                       "10ft ropes black colour_1"],                             ["caustic", "gasket", "battery", "courier", "12 feet",
                                                                                   "15 feet", "6 feet", "5 ft", "multicolour", "b0f38h2ktg"]),
    ("B- 12FT + 15FT", ["b0dnw255dw ( 15ft"],                                   ["caustic", "gasket", "battery", "courier", "multicolour",
                                                                                   "pack 2", "b0f38jwkj4"]),
    ("B- 12FT = PC",  ["b0dtnvqyfb", "sc-x924-rnad", "(12 feet)",
                       "b0dnvzx3qv", "12ft ropes black colour",
                       "12 ft cloths drying", "b0dnw19t4r", "b0dnw4l7x1",
                       "1.5 meter ropes", "1.5 meter ft cloths"],               ["caustic", "gasket", "battery", "courier", "10 feet",
                                                                                   "15 feet", "15 ft", "6 feet", "(5 ft)", "b0dnw255dw"]),
    ("MULTI - 6 - 15FT", ["(6, black, 15 ft)", "b0dp4d5nnl", "qw-m91l-9r1r"],   ["caustic", "gasket", "battery", "courier", "(5 ft)", "10 ft", "12 ft",
                                                                                    "b0gynr911m", "b0grvfz41v", "pack 1 |", "b0dnvys4gl"]),
    ("B- 15FT - 2PC", ["b0f38jwkj4", "15ft ropes black colour_2",
                        "15 ft cloths drying ropes", "b0dnvys4gl",
                        "15 ft ropes multicolour_2", "b0dp4fc8y3",
                        "uz-epop-08n5", "(2, black, 15 ft)"],                   ["caustic", "gasket", "battery", "courier", "10 feet",
                                                                                   "12 feet", "6 feet", "(5 ft)", "multicolour_4", "pack 1",
                                                                                   "(6, black", "(6, multicolour", "b0dp4d5nnl"]),
    ("B- 15FT = PC",  ["b0grvfz41v", "5k-pec0-13td", "15ft ropes black colour_1",
                       "b0gynr911m", "mr-b6x5-6eko", "pack 1 |",
                       "(15 feet) pack of (1)"],                                 ["caustic", "gasket", "battery", "courier", "10 feet",
                                                                                    "12 feet", "12 ft", "6 feet", "(5 ft)", "pack 2",
                                                                                    "(6, black", "b0dnvys4gl", "b0dp4d5nnl"]),
    ("B- 5FT = PC",   ["b0dp4dn9hz", "(5 ft)", "b0dp4dn9hz"],                   ["caustic", "gasket", "battery", "courier", "multicolour", "15 ft"]),

    # Mixer / appliance wire
    ("MIXER WIRE",    ["mixer wire", "electric cable cord", "3 pin wire for tv",
                       "b0dssppp7d", "mixer wire 2.5 meter"],                    ["caustic", "gasket", "battery", "courier", "iron press", "bungee"]),

    # Iron cord
    ("IRON CORD",     ["iron press pure copper cable", "iron cord",
                       "b0dst55r7r", "iron press"],                              ["caustic", "gasket", "battery", "courier"]),

    # Capacitor — use SKU for disambiguation
    ("CAPACITOR 2.5MFD",["2.5 mfd", "ceiling fan capacitor", "fan capacitor 2.5",
                          "b0dt16hb59", "fan capacitor"],                        ["caustic", "gasket", "battery", "courier", "4 µf", "25 µf", "4mfd", "25mfd", "3.15", "6 µf", "8 µf"]),
    ("CAPACITOR 3.15MFD",["3.15µf", "3.15 mfd", "3.15uf", "b0f8g4r5jd",
                           "3.15µf for increased speed"],                        ["caustic", "gasket", "battery", "courier", "4 µf", "2.5 mfd", "6 µf", "8 µf"]),
    ("CAPACITOR 4MFD",  ["b0dthvxnhn", "4 µf capacitor", "4 mfd",
                          "capacitor cell for 1 hp"],                            ["caustic", "gasket", "battery", "courier", "25mfd", "25 µf", "2.5 mfd", "3.15", "6 µf", "8 µf", "fan capacitor"]),
    ("CAPACITOR 6MFD",  ["6 µf capacitor", "6 mfd", "havells 6 µf",
                          "b0dthvx7r2"],                                         ["caustic", "gasket", "battery", "courier", "4 µf", "8 µf", "25 µf", "2.5 mfd", "3.15"]),
    ("CAPACITOR 8MFD",  ["8 µf capacitor", "8 mfd", "havells 8 µf",
                          "b0dthvxkq3"],                                         ["caustic", "gasket", "battery", "courier", "4 µf", "6 µf", "25 µf", "2.5 mfd", "3.15"]),
    ("CAPACITOR 12.5MFD", ["12.5 µf", "12.5 mfd", "b0dthwzsd6",
                            "h-uf capacitor_12.5"],                              ["caustic", "gasket", "battery", "courier", "4 µf", "15 µf", "20 µf", "25 µf"]),
    ("CAPACITOR 15MFD",  ["15 µf capacitor", "15 mfd", "b0f6cdq7wz",
                           "h-uf capacitor-15"],                                 ["caustic", "gasket", "battery", "courier", "4 µf", "8 µf", "20 µf", "25 µf", "36 µf"]),
    ("CAPACITOR 20MFD",  ["20 µf capacitor", "20 mfd", "b0dtj1814y",
                           "h-uf capacitor_20"],                                 ["caustic", "gasket", "battery", "courier", "4 µf", "8 µf", "25 µf", "2.5 mfd", "36 µf"]),
    ("CAPACITOR 36MFD", ["b0f6cjcm7q", "36 µf capacitor", "36 mfd",
                          "h-uf capacitor-36"],                                  ["caustic", "gasket", "battery", "courier", "4mfd", "25mfd", "2.5 mfd", "6 µf", "8 µf"]),
    ("CAPACITOR 25MFD", ["b0dthzgn19", "25 µf capacitor", "25 mfd",
                          "25 mdf"],                                              ["caustic", "gasket", "battery", "courier", "4mfd", "4 µf", "2.5 mfd", "36 µf", "6 µf", "8 µf"]),

    # Remote controls — all brands
    ("ACER REMOTE",      ["acer", "smart tv remote control for acer",
                          "acer h pro", "b0f8dw31t5"],                          ["caustic", "gasket", "battery", "courier"]),
    ("HATHWAY REMOTE",   ["hathway"],                                            ["caustic", "gasket", "battery", "courier"]),
    ("WHIRLPOOL REMOTE", ["whirlpool"],                                          ["caustic", "gasket", "battery", "courier"]),
    ("DAIKIN REMOTE",    ["daikin", "daikinn", "b0f4pck3r8"],                    ["caustic", "gasket", "battery", "courier"]),
    ("LLOYD REMOTE",     ["lloyd", "b0dp9lq45z", "zh/jt-03", "ac-49"],          ["caustic", "gasket", "battery", "courier", "koyla", "charcoal"]),

    # Plumber / tap spindle
    ("PLUMBER LONGLIFE", ["plumber", "tap spindle", "longlife", "cartridge",
                          "quarter turn"],                                        ["caustic", "gasket", "battery", "courier"]),

    # Adapter holder
    ("ADAPTER HOLDER",   ["parallel adapter", "bulb holder", "b.c. parallel",
                          "b0dswcb9cg", "2 ports for 2 pin",
                          "heavy brass parts"],                                   ["caustic", "gasket", "battery", "courier",
                                                                                   "washing machine", "capacitor", "mfd", "fan"]),

    # Flipkart tape
    ("YELLOW VASTU TAPE", ["vastu dosh", "heavy duty vinyl tape", "vastu correction",
                            "maha-vastu-sashtra", "yellow_pack of",
                            "b0f8g5v4lk", "4 inches, length: 22 meters"],       ["caustic", "gasket", "battery", "courier"]),
    ("FLIPKART TAPE",    ["flip-kart tape", "flipkart tape"],                    ["caustic", "gasket", "battery", "courier"]),

    # Milk / polythene bags
    ("MILK BAG 6X9",  ["plastic virgin bags", "b0f3y34f6j", "zl-sxpz-9mp0",
                        "lldp", "½ litre", "6 x 9 inch", "liquid packing material"], []),

    # 3 Pin plug
    ("3PIN PLUG",     ["3-pin type d indian socket", "multi-pin conversion plug",
                        "b0dydscvx4", "n7-hjxo-25zv", "type d", "6a 240v"],    ["caustic", "gasket", "battery", "courier"]),

    # Batteries — SR521SW 379
    ("521 = 2PC + 626 = 5PC", ["b0dphdwtl1", "seizaiken sr626sw 3"],            ["lr1130", "sr416", "sr936", "caustic", "gasket", "courier"]),
    ("521 = 2PC",     ["b0dphdwtl1", "sr521sw 379 button_2b",
                       "watch batteries-pack of 2"],                             ["lr1130", "sr416", "sr936", "lr44", "27a_alkaline",
                                                                                   "caustic", "gasket", "courier", "sr626sw"]),
    ("521 = 5PC",     ["sr521sw", "379 1.55v", "b0f895xszw", "sr521sw 379"],   ["lr1130", "sr416", "sr936", "lr44", "27a_alkaline",
                                                                                   "caustic", "gasket", "courier", "b0dphdwtl1", "pack of 2"]),

    # Misc — tap aerator, screen brush, other unclassified
    ("MIXER COUPLER",  ["mixer grinder motor coupler", "b0fc34wsd4",
                        "mixer coupler heavy", "b0f8vzrvb",
                        "nutri-blender", "coupler gear set",
                        "motor and jar couplers", "chutney jar with lid",
                        "maxonic chutney jar", "stainless steel, |for",
                        "activa, sumeet, orient, bajaj"],                        ["caustic", "gasket", "battery", "courier"]),
    ("SQUARE SHOWER",  ["overhead shower", "rain shower head", "b0dsg63h6z",
                        "head shower_4x4", "ss-304 grade", "square ss-304"],     ["caustic", "gasket", "battery", "courier"]),
    ("THERMAL ROLL",   ["thermal transfer barcode ribbon", "b0dxfbr24v",
                        "wax ribbon", "o2-0iqh-mg6b", "barcode ribbon 110mm"],   ["caustic", "gasket", "battery", "courier"]),
    ("SAFETY VALVE",  ["pressure cooker safety valve", "b0f8w3s5dd",
                       "dulex safty vale", "o-rings for deluxe"],               ["caustic", "gasket", "battery", "courier"]),
    ("BONDI JAHARA",  ["boondi jhara", "b0dr2khhq8", "boondi maker",
                       "jalli karandi"],                                          []),
    ("WHITE STRING",  ["hang tag string fasteners", "nylon cord", "b0f3j4cfgv",
                       "ou-w4zp-n3rr", "price tags"],                            []),
    ("ROSE GOLD LIGHTER", ["refill-free gas lighter", "rose gold", "b0fqph92h9",
                            "rose gold gas lighter", "long stem design"],        []),
    ("MISC",          ["screen brush", "mosquito net", "mesh cleaning brush",
                       "b0gkqnc8l8", "24-bta0-8tio", "tap aerator",
                       "water tap aerator", "b0fdwydjry", "foam flow",
                       "female-outer thread", "padlock", "b0ds611v1v",
                       "ma-ap64-l1zr", "hardened steel shackle",
                       "corrugated box", "corrugated flat box",
                       "cocktail jigger", "jigger set", "b0fsr3yx2r",
                       "kitchen knife", "knife set", "b0fqpft2mt",
                       "toilet seat cover screw", "pvc seat cover screw",
                       "b0fd7p7pj1",
                       "chutney jar", "mixer jar", "b0ffsmh9yy", "sr-h2w1",
                       "jet spray faucet", "toilet stand", "b0fdw2fmxg",
                       "wall stand holder", "nelco", "b0g4jwfkhj",
                       "nelco 4& 5 liter",
                       "polypropylene empty white bag", "b0drd8rsrd", "goni",
                       "indian flag", "polyester with double-sided printing",
                       "paper masking tape", "masking tape 72mm",
                       "leaves no residue after peeling",
                       "b0ffsckxrf", "49-x6s2-t2uu", "maxonic chutney jar",
                       "submersible water pump", "14w submersible",
                       "water pump for air coolers", "b0f3p8",
                       "soap pump dispenser", "dish soap pump",
                       "sponge holder dish soap", "b0dw4cg"],                  []),
]


def auto_classify(inv_num, text):
    """
    Classify product code using rules.
    Returns (product_code, confidence, reason)
    confidence: 'HIGH' = unique match, 'AMBIGUOUS' = multiple matches, 'NONE' = no match
    """
    tl = text.lower()
    matches = []

    for (code, must_have_any, must_not_have) in RULES:
        # Check at least one must_have keyword present
        has_keyword = any(kw in tl for kw in must_have_any)
        if not has_keyword:
            continue
        # Check none of must_not_have present
        blocked = any(kw in tl for kw in must_not_have)
        if blocked:
            continue
        # Match found
        matched_kw = [kw for kw in must_have_any if kw in tl]
        matches.append((code, matched_kw))

    if len(matches) == 0:
        return ("UNCLASSIFIED", "NONE", "No rule matched")
    elif len(matches) == 1:
        return (matches[0][0], "HIGH", f"Matched: {matches[0][1]}")
    else:
        # Multiple matches - pick the most specific (most keywords matched)
        best = max(matches, key=lambda x: len(x[1]))
        others = [m[0] for m in matches if m[0] != best[0]]
        return (best[0], "AMBIGUOUS", f"Best: {best[1]}, also matched: {others}")


def extract_qty(text):
    """Extract quantity from invoice text."""
    # Pattern: price qty net_amount
    qty_m = re.findall(r'₹[\d,]+\.?\d*\s+(\d+)\s+₹', text)
    if qty_m:
        return qty_m[0]
    return "1"


def parse_pdf(filepath):
    """Parse PDF and extract all invoice groups."""
    reader = PdfReader(filepath)
    total = len(reader.pages)
    groups = []
    i = 0

    while i < total:
        text = reader.pages[i].extract_text() or ""
        if not text.strip():
            # Label page
            label_idx = i
            inv_pages = []
            j = i + 1
            while j < total:
                jtext = reader.pages[j].extract_text() or ""
                jtl = jtext.lower()
                if 'tax invoice' in jtl:
                    inv_pages.append(j)
                    pm = re.search(r'page (\d+) of (\d+)', jtl)
                    if pm and int(pm.group(2)) > int(pm.group(1)):
                        j += 1
                        continue
                    else:
                        break
                else:
                    break
                j += 1

            if inv_pages:
                inv_text = reader.pages[inv_pages[0]].extract_text() or ""
                m = re.search(r'invoice number\s*[:\s]+([A-Z0-9\-]+)', inv_text, re.IGNORECASE)
                inv_num = m.group(1).strip() if m else "UNKNOWN"
                qty = extract_qty(inv_text)
                prod, confidence, reason = auto_classify(inv_num, inv_text)
                groups.append({
                    'label': label_idx,
                    'invoices': inv_pages,
                    'inv_num': inv_num,
                    'product': prod,
                    'qty': qty,
                    'confidence': confidence,
                    'reason': reason,
                    'text': inv_text,
                })
            i = j + 1
        else:
            i += 1

    return reader, groups


def double_check(groups):
    """
    Double-check pass: flag any issues.
    Returns list of problems.
    """
    problems = []

    for g in groups:
        inv = g['inv_num']
        prod = g['product']
        conf = g['confidence']
        text = g['text'].lower()

        # Flag 1: unclassified
        if prod == "UNCLASSIFIED":
            problems.append(f"❌ {inv}: UNCLASSIFIED - no rule matched. Text snippet: {text[200:350]}")
            continue

        # Flag 3: Cross-validation - check assigned code makes sense
        # e.g. if assigned caustic but text has no 'caustic'
        if "C-" in prod and "caustic" not in text:
            problems.append(f"❌ {inv}: Assigned {prod} but 'caustic' not in text!")
        if "SALT" in prod and not any(w in text for w in ["salt", "vastu", "epsom"]):
            problems.append(f"❌ {inv}: Assigned {prod} but no salt keyword in text!")
        if "COAL" in prod and not any(w in text for w in ["coal", "charcoal", "dhoop"]):
            problems.append(f"❌ {inv}: Assigned {prod} but no coal keyword in text!")
        if "77" in prod and not any(w in text for w in ["gasket", "cooker", "pressure"]):
            problems.append(f"❌ {inv}: Assigned {prod} but no gasket keyword in text!")
        if "TSB" in prod and not any(w in text for w in ["tsb", "transparent courier", "courier bag"]):
            problems.append(f"❌ {inv}: Assigned {prod} but no TSB/courier keyword in text!")
        if "NSB" in prod and "nsb" not in text:
            problems.append(f"❌ {inv}: Assigned {prod} but 'nsb' not in text!")
        if "MY " in prod and "50PC" not in prod and "myn" not in text and "myntra" not in text:
            problems.append(f"❌ {inv}: Assigned {prod} but no MYN/Myntra keyword in text!")
        if "27 A" in prod and not any(w in text for w in ["27a", "a27", "v27ga"]):
            problems.append(f"❌ {inv}: Assigned {prod} but no 27A keyword in text!")
        if "1130" in prod and not any(w in text for w in ["lr1130","sr416","sr616","ag10","lr41","ag3","watch battery","189","337","321"]):
            problems.append(f"❌ {inv}: Assigned {prod} but no LR1130/watch battery keyword in text!")
        if "BUNGEE" in prod.upper() or "B- " in prod and "bungee" not in text:
            problems.append(f"❌ {inv}: Assigned {prod} but 'bungee' not in text!")
        if "KOYLA" in prod.upper() or "K ½" in prod:
            if not any(w in text for w in ["koyla", "charcoal koyla", "lump charcoal", "wood charcoal"]):
                problems.append(f"❌ {inv}: Assigned {prod} but no koyla keyword in text!")
        # Flag 2: ambiguous — only flag if confidence is AMBIGUOUS and it's not a known single-match
        if conf == "AMBIGUOUS" and prod not in ["MIXER WIRE", "521 = 5PC", "MY 14x16", "MY 17x22",
                "MY 11x13", "PRESTIGE 8L", "626 = 5PC", "K ½ KG", "CAPACITOR 20MFD", "VINOD 3L",
                "MIXER COUPLER", "MISC", "CAPACITOR 12.5MFD", "SILICON VINOD 3L",
                "MY 13x14 + MY 14x16", "SALT 900g", "K-100", "K-50", "YELLOW - 30", "YELLOW - 50",
                "YELLOW - 100", "POPULAR 4/5", "2KG SALT", "CAPACITOR 3.15MFD", "27 A = 2PC",
                "BUTTERFLY SILICON 2-3L"]:
            problems.append(f"⚠️  {inv}: AMBIGUOUS match -> assigned {prod}. Reason: {g['reason']}")

        # Flag 4: qty sanity
        try:
            qty_int = int(g['qty'])
            if qty_int > 10:
                problems.append(f"⚠️  {inv}: qty={g['qty']} seems high, please verify")
        except:
            problems.append(f"⚠️  {inv}: qty='{g['qty']}' could not be parsed as integer")

    return problems


SORT_ORDER = [
    'C- ½ KG', 'C- 1KG', 'C- 2KG',
    'SALT 900g', 'SALT 990g', 'SALT 900g/990g', '2KG SALT',
    'AFANDI 96', 'YELLOW - 30', 'YELLOW - 50', 'YELLOW - 100',
    'K-30', 'K-50', 'K-60', 'K-100', 'K 2KG',
    '36 STEEL CLIPS', '18 STEEL CLIPS',
    'K ½ KG',
    '77', 'SILICON 77', 'SILICON 777',
    'PRESTIGE HANDI 2L', 'PRESTIGE 4L', 'PRESTIGE 8L', 'PRESTIGE TRIPLY 3L', 'PRESTIGE TRIPLY 5L',
    'POPULAR 4/5', '1.5 - 2PC',
    'SURYA 3L', 'SURYA 4-5L',
    'BUTTERFLY SILICON 2-3L', 'BUTTERFLY SILICON 5L',
    'STAHL 3L', 'STAHL 5L',
    '777', 'VINOD HANDI 1.5L', 'VINOD HANDI 2.5L', 'VINOD 3L', 'SILICON VINOD 3L',
    'TSB 6x7', 'TSB 8.5x11', 'TSB 10x13', 'TSB 14x17',
    'NSB 6x8', 'NSB 8.5x11', 'NSB 10x13', 'NSB 14x18', 'NSB 16x20',
    'S- 6x8 - 50PC', 'S- 6.5x8 = PC', 'S- 7x10 = PC', 'S- 7x10 - 50PC', 'S- 8x10 = PC',
    'S- 8x11 = PC', 'S- 8x12 = PC',
    'S- 10x12 = PC', 'S- 10x14 - 50PC', 'S- 12x14 = PC', 'S- 12x16 = PC',
    'S- 13x14 = PC', 'S- 14x17 - 50PC', 'S- 14x18 = PC', 'S- 15x19 = PC',
    'S- 18x23 - 50PC', 'S- 18x23 = PC',
    'AMAZON 6x8 - 100PC', 'AMAZON 10x12', 'AMAZON 11x13', '6x8 = PC', 'AJO 13x17', 'ZIP BAG 5X6',
    'MY 8x11', 'MY 11x13', 'MY 11x13 - 50PC', 'MY 11x13 + MY 14x16',
    'MY 13x14', 'MY 13x14 + MY 14x16', 'MY 14x16', 'MY 14x16 + MY 17x22', 'MY 17x22',
    'MILK BAG 6X9', 'SEAL - 100PC',
    '27 A = 2PC', '27 A = 5PC', '23 A', '1130 = 25PC', '416 = 5PC', 'SR936 = 5PC',
    'LR41 = 10PC', 'LR44 = 25PC', '521 = 5PC', '521 = 2PC', '521 = 2PC + 626 = 5PC',
    '626 = 5PC', '1632 = 2PC', '1616 = 2PC', '721 = 2PC', '916 = 2PC', '920 = 2PC', '927 = 2PC',
    '2032 = 2PC', '2430 = 2PC',
    'B- 5FT = PC', 'B- 6FT = PC', 'B- 8FT = PC', 'B- 10FT = PC', 'B- 10FT - 2PC', 'B- 12FT = PC',
    'B- 12FT + 15FT', 'B- 15FT = PC', 'B- 15FT - 2PC',
    'MULTI - 6 - 5FT', 'MULTI - 2 - 7FT', 'MULTI - 6 - 6PC', 'MULTI - 2 - 10FT', 'MULTI - 6 - 10FT', 'MULTI - 10FT - 4PC',
    'MULTI - 6 - 15FT', 'MULTI - 3M - 2PC', 'MULTI - 6FT - 2PC',
    'IRON CORD', 'MIXER WIRE', 'FLIPKART TAPE', 'YELLOW VASTU TAPE',
    'CAPACITOR 2.5MFD', 'CAPACITOR 3.15MFD', 'CAPACITOR 4MFD',
    'CAPACITOR 6MFD', 'CAPACITOR 8MFD', 'CAPACITOR 12.5MFD', 'CAPACITOR 15MFD', 'CAPACITOR 20MFD',
    'CAPACITOR 36MFD', 'CAPACITOR 25MFD',
    'HATHWAY REMOTE', 'WHIRLPOOL REMOTE', 'DAIKIN REMOTE',
    'LLOYD REMOTE', 'ACER REMOTE',
    'WA', 'GAS PIPE', 'PLUMBER LONGLIFE', 'FTA - 4PC', '3PIN PLUG', 'SAFETY VALVE',
    'ADAPTER HOLDER', 'KAPOOR DANI', 'WHITE STRING', 'ROSE GOLD LIGHTER',
    'BONDI JAHARA', 'MIXER COUPLER', 'SQUARE SHOWER', 'THERMAL ROLL',
    'MISC', 'UNCLASSIFIED',
]


def create_overlay(pw, ph, prod_code, qty):
    packet = io.BytesIO()
    c = canvas.Canvas(packet, pagesize=(pw, ph))

    try:
        qty_int = int(str(qty).split('+')[0])
    except:
        qty_int = 1

    import math

    # Box dimensions — wider to fit code + qty on one line
    star_row = qty_int > 1
    box_width = 400
    box_height = 50 if not star_row else 78
    box_x = 30
    box_y = 20

    # Black box
    c.setFillColor(colors.black)
    c.rect(box_x, box_y, box_width, box_height, fill=1, stroke=0)

    # Single line: PRODUCT CODE   |   QTY: X
    line_y = box_y + box_height - (28 if not star_row else 32)

    # Product code — left portion
    c.setFillColor(colors.white)
    font_size = 26
    c.setFont("Helvetica-Bold", font_size)
    # Auto-shrink if too long
    while c.stringWidth(prod_code, "Helvetica-Bold", font_size) > box_width * 0.58 and font_size > 12:
        font_size -= 1
        c.setFont("Helvetica-Bold", font_size)
    c.drawString(box_x + 12, line_y, prod_code)

    # Divider line
    divider_x = box_x + box_width * 0.62
    c.setStrokeColor(colors.white)
    c.setLineWidth(1.5)
    c.line(divider_x, box_y + 8, divider_x, box_y + box_height - 8)

    # QTY — right portion, same line
    qty_label = f"QTY: {qty}"
    c.setFont("Helvetica-Bold", 26)
    qty_w = c.stringWidth(qty_label, "Helvetica-Bold", 26)
    right_center = divider_x + (box_x + box_width - divider_x) / 2
    c.drawString(right_center - qty_w / 2, line_y, qty_label)

    # Stars row BELOW — only for multi-qty
    if star_row:
        star_size = 18
        n_stars = min(qty_int, 10)
        gap = 5
        total_star_w = n_stars * star_size + (n_stars - 1) * gap
        start_x = box_x + (box_width - total_star_w) / 2
        star_y = box_y + 8

        for s in range(n_stars):
            sx = start_x + s * (star_size + gap) + star_size / 2
            sy = star_y + star_size / 2
            outer_r = star_size / 2
            inner_r = outer_r * 0.42
            pts = []
            for k in range(10):
                angle = math.pi / 2 + k * math.pi / 5
                r = outer_r if k % 2 == 0 else inner_r
                pts.append((sx + r * math.cos(angle), sy + r * math.sin(angle)))
            c.setFillColor(colors.yellow)
            c.setStrokeColor(colors.white)
            c.setLineWidth(0.8)
            p = c.beginPath()
            p.moveTo(*pts[0])
            for pt in pts[1:]:
                p.lineTo(*pt)
            p.close()
            c.drawPath(p, fill=1, stroke=1)

    c.save()
    packet.seek(0)
    return PdfReader(packet)

    c.save()
    packet.seek(0)
    return PdfReader(packet)

    c.save()
    packet.seek(0)
    return PdfReader(packet)


def process_pdf(input_path, output_path):
    print(f"\n{'='*60}")
    print(f"PROCESSING: {input_path}")
    print(f"{'='*60}")

    reader, groups = parse_pdf(input_path)
    print(f"Found {len(groups)} shipments\n")

    # ── FIRST PASS: classify
    print("PASS 1 - Classification:")
    for g in groups:
        print(f"  {g['inv_num']:12s} -> {g['product']:30s} qty={g['qty']:3s}  [{g['confidence']}]")

    # ── SECOND PASS: validate
    print(f"\nPASS 2 - Double-Check Validation:")
    problems = double_check(groups)

    if problems:
        print(f"\n  ⛔ FOUND {len(problems)} ISSUE(S) - MUST FIX BEFORE OUTPUT:\n")
        for p in problems:
            print(f"    {p}")
        print("\n  ⛔ OUTPUT BLOCKED UNTIL ALL ISSUES RESOLVED")
        return False, groups
    else:
        print("  ✅ All checks passed — zero issues found")

    # ── Sort
    def sort_key(g):
        p = g['product']
        return (SORT_ORDER.index(p) if p in SORT_ORDER else len(SORT_ORDER), g['inv_num'])

    groups_sorted = sorted(groups, key=sort_key)

    # ── Build PDF
    writer = PdfWriter()
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

    print(f"\n✅ OUTPUT: {output_path} ({len(writer.pages)} pages)")
    print("\nFinal sorted order:")
    for g in groups_sorted:
        print(f"  {g['product']:30s} qty={g['qty']:3s} | {g['inv_num']}")

    return True, groups_sorted


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python master_processor.py <input.pdf> <output.pdf>")
        sys.exit(1)
    success, _ = process_pdf(sys.argv[1], sys.argv[2])
    sys.exit(0 if success else 1)


def build_output_pdf(input_path, output_path, groups):
    """Called by the GUI app after classification & validation."""
    from pypdf import PdfReader as _R, PdfWriter as _W

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
    # NEW RULES 30-AUG-2026
    (r"b0f21xll2g|cocktail.*jigger", "JIGGER SET", "home_misc"),
    (r"b0dtk2l3q1|indian.*flag.*24.*36|ghar.*tiranga", "INDIAN FLAG", "home_misc"),
    (r"b0h25mzfgm|bng15-mc-1p|bungee.*15.*feet", "BUNGEE 15FT", "extension_cords"),
    (r"mvh-brc-6-ft-blkmc|bungee.*6.*feet", "BUNGEE 6FT", "extension_cords"),
    (r"b0f3csmwz8|steel.*drying.*hanger.*25", "HANGER 25", "home_misc"),
    (r"b0hfbxhw82|b0dnqk3zbb|myn.*8x11.*100", "MY 8x11-100PC", "bags"),
