#!/usr/bin/env python3
"""Generate everything Smithing Templates ships: the trim art for every vanilla
tool, the models and item definitions that put it on them, the smithing
recipes, and the wording that tells players the templates take tools.

Vanilla is the source of truth for what exists. The patterns come from its own
armor trim recipes, the colours from its own trim palettes, the tools from its
own tool tags, and each tool's item definition is vanilla's with the trim
layered on top. All this script adds is the art in art/: one overlay per pattern
per kind of tool, drawn once over the silhouette every tool of that kind shares,
and recoloured per material by the game's paletted atlas exactly the way armor
trim icons are.

A pattern vanilla adds that has no art stops the script rather than shipping a
trim with nothing drawn on it.

Pure stdlib PNG reader and writer (zlib + struct) so it runs without Pillow, the
same script generated art approach as the rest of the suite. Deterministic:
re-running produces identical bytes.

Usage: python3 generate_trims.py [path/to/minecraft.jar]
"""

import glob
import json
import os
import shutil
import struct
import sys
import zipfile
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
MOD_ID = "smithing-templates-justfatlard"
RESOURCES = os.path.join(HERE, "src/main/resources")
ASSETS = os.path.join(RESOURCES, "assets", MOD_ID)
DATA = os.path.join(RESOURCES, "data", MOD_ID)
ART = os.path.join(HERE, "art")

_JAR = None


def minecraft_version():
    """The version this mod targets, so the sprite is cut from the same jar the
    mod is built against rather than whatever happens to be cached."""
    path = os.path.join(HERE, "gradle.properties")
    if not os.path.exists(path):
        return None
    for line in open(path):
        key, sep, value = line.partition("=")
        if sep and key.strip() == "minecraft_version":
            return value.strip()
    return None


def find_jar():
    """Loom caches the remapped Minecraft jars after a build; that is where the
    vanilla files come from. Override with an argument or $MINECRAFT_JAR."""
    global _JAR
    if _JAR:
        return _JAR
    if len(sys.argv) > 1:
        _JAR = sys.argv[1]
        return _JAR
    if os.environ.get("MINECRAFT_JAR"):
        _JAR = os.environ["MINECRAFT_JAR"]
        return _JAR
    cache = os.path.expanduser("~/.gradle/caches/fabric-loom")
    names = ("minecraft-merged.jar", "minecraft-client.jar")
    found = []
    version = minecraft_version()
    if version:
        for name in names:
            found += glob.glob(os.path.join(cache, version, name))
    if not found:
        for name in names:
            found += glob.glob(os.path.join(cache, "*", name))
    if not found:
        sys.exit("no cached Minecraft jar found: build the mod once, "
                 "or pass a jar path as the first argument")
    _JAR = max(found, key=os.path.getmtime)
    return _JAR


def decode_png(data):
    """Minimal PNG reader: no interlacing, every colour type and bit depth
    vanilla actually ships. Returns rows of RGBA tuples."""
    pos = 8
    idat = b""
    width = height = depth = ctype = None
    palette = trns = None
    while pos < len(data):
        (length,) = struct.unpack(">I", data[pos:pos + 4])
        tag = data[pos + 4:pos + 8]
        body = data[pos + 8:pos + 8 + length]
        pos += 12 + length
        if tag == b"IHDR":
            width, height, depth, ctype, _, _, interlace = struct.unpack(">IIBBBBB", body)
            assert interlace == 0, "interlaced PNG not supported"
        elif tag == b"PLTE":
            palette = body
        elif tag == b"tRNS":
            trns = body
        elif tag == b"IDAT":
            idat += body
        elif tag == b"IEND":
            break

    channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[ctype]
    stride = (width * channels * depth + 7) // 8
    step = max(1, (channels * depth) // 8)
    raw = zlib.decompress(idat)
    out = bytearray(stride * height)
    prev = bytearray(stride)
    p = 0
    for y in range(height):
        filt = raw[p]
        p += 1
        line = bytearray(raw[p:p + stride])
        p += stride
        if filt == 1:
            for i in range(step, stride):
                line[i] = (line[i] + line[i - step]) & 0xFF
        elif filt == 2:
            for i in range(stride):
                line[i] = (line[i] + prev[i]) & 0xFF
        elif filt == 3:
            for i in range(stride):
                a = line[i - step] if i >= step else 0
                line[i] = (line[i] + ((a + prev[i]) >> 1)) & 0xFF
        elif filt == 4:
            for i in range(stride):
                a = line[i - step] if i >= step else 0
                b = prev[i]
                c = prev[i - step] if i >= step else 0
                pa, pb, pc = abs(b - c), abs(a - c), abs(a + b - 2 * c)
                pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                line[i] = (line[i] + pr) & 0xFF
        out[y * stride:(y + 1) * stride] = line
        prev = line

    pixels = []
    if depth < 8:
        per = 8 // depth
        mask = (1 << depth) - 1
        for y in range(height):
            base = y * stride
            row = []
            for x in range(width):
                i = x * channels
                value = (out[base + i // per] >> (8 - depth * (i % per + 1))) & mask
                if ctype == 3:
                    r, g, b = palette[value * 3:value * 3 + 3]
                    a = trns[value] if trns and value < len(trns) else 255
                    row.append((r, g, b, a))
                else:
                    v = value * 255 // mask
                    row.append((v, v, v, 255))
            pixels.append(row)
        return pixels

    for y in range(height):
        base = y * stride
        row = []
        for x in range(width):
            i = base + x * channels
            if ctype == 6:
                row.append(tuple(out[i:i + 4]))
            elif ctype == 2:
                row.append((out[i], out[i + 1], out[i + 2], 255))
            elif ctype == 4:
                row.append((out[i], out[i], out[i], out[i + 1]))
            elif ctype == 0:
                row.append((out[i], out[i], out[i], 255))
            else:
                r, g, b = palette[out[i] * 3:out[i] * 3 + 3]
                a = trns[out[i]] if trns and out[i] < len(trns) else 255
                row.append((r, g, b, a))
        pixels.append(row)
    return pixels


def write_png(path, pixels):
    """pixels: rows of RGBA tuples."""
    height = len(pixels)
    width = len(pixels[0])
    raw = b"".join(b"\x00" + b"".join(bytes(px) for px in row) for row in pixels)

    def chunk(tag, body):
        c = tag + body
        return struct.pack(">I", len(body)) + c + struct.pack(">I", zlib.crc32(c))

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    png = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
           + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(png)
    print("wrote %s (%dx%d)" % (path, width, height))


def jar_read(path):
    with zipfile.ZipFile(find_jar()) as jar:
        return jar.read(path)


def jar_json(path):
    return json.loads(jar_read(path))


def jar_list(prefix, suffix):
    with zipfile.ZipFile(find_jar()) as jar:
        return sorted(n for n in jar.namelist() if n.startswith(prefix) and n.endswith(suffix))


def write_json(path, value):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(value, f, indent=2)
        f.write("\n")


def path_of(identifier):
    return identifier.split(":", 1)[1]


# What takes a trim besides armor, by the name of the art file drawn for each: a
# vanilla tag, or the items themselves where vanilla has no tag for them.
KINDS = {
    "sword": "swords",
    "pickaxe": "pickaxes",
    "axe": "axes",
    "shovel": "shovels",
    "hoe": "hoes",
    "spear": "spears",
    "elytra": ["minecraft:elytra"],
}

# An elytra is also trimmed where it is worn: art/elytra_wings.txt is this corner of
# vanilla's wings texture, which the game draws on both wings.
WINGS_ART = "elytra_wings"
WINGS_TEXTURE = "assets/minecraft/textures/entity/equipment/wings/elytra.png"
WINGS_LEFT, WINGS_TOP = 32, 0

# A tool in the trim of its own metal takes the darker shade, the way iron trim on
# iron armor does, so the inlay still reads against a head of the same metal.
TIER_PALETTE = {
    "copper": "copper",
    "iron": "iron",
    "golden": "gold",
    "diamond": "diamond",
    "netherite": "netherite",
}

# Letters in art/, as indexes into vanilla's trim_base palette: the same four shades
# vanilla's own armor trim icons are drawn in.
SHADES = {"W": 0, "H": 1, "M": 2, "D": 6}


def read_art(kind, height=16):
    """Pattern name to its rows, sixteen wide, from art/<kind>.txt."""
    art = {}
    name = None
    for line in open(os.path.join(ART, kind + ".txt")):
        line = line.rstrip("\n")
        if not line or line.startswith("#"):
            continue
        if not line.strip(".WHMD"):
            art[name].append(line)
        else:
            name = line
            art[name] = []
    for name, rows in art.items():
        assert len(rows) == height and all(len(r) == 16 for r in rows), "%s/%s is not 16x%d" % (kind, name, height)
    return art


def vanilla_patterns():
    """Pattern id to template id, from vanilla's armor trim recipes."""
    found = {}
    for name in jar_list("data/minecraft/recipe/", "_smithing_trim.json"):
        recipe = jar_json(name)
        if recipe.get("type") == "minecraft:smithing_trim":
            found[recipe["pattern"]] = recipe["template"]
    return found


def trim_permutations():
    """Palette name to palette texture, from the paletted source vanilla's armor
    trim icons are built with, so a material vanilla adds is picked up here too."""
    for source in jar_json("assets/minecraft/atlases/items.json")["sources"]:
        if source.get("palette_key") == "minecraft:trim_base":
            return source["palette_key"], source["permutations"]
    sys.exit("vanilla's items atlas has no trim palette source")


def materials():
    """Trim material id to the palette it draws with."""
    found = {}
    for name in jar_list("data/minecraft/trim_material/", ".json"):
        material = "minecraft:" + os.path.basename(name)[:-len(".json")]
        found[material] = path_of(jar_json(name)["palette_id"]).split("/")[-1]
    return found


def tools(kind):
    """The items of a kind that take a trim: wood and stone are too plain a stock to inlay."""
    source = KINDS[kind]
    if not isinstance(source, list):
        source = jar_json("data/minecraft/tags/item/%s.json" % source)["values"]
    return [item for item in source if not path_of(item).startswith(("wooden_", "stone_"))]


def overlay_texture(kind, pattern):
    return "%s:trims/items/%s/%s" % (MOD_ID, kind, path_of(pattern))


def overlay_model(kind, pattern, palette):
    return "%s:item/trim/%s/%s_%s" % (MOD_ID, kind, path_of(pattern), palette)


def check_fits(kind, art, tool_ids, texture_of=None):
    """Every lit pixel lands on every tool of its kind, so no material ever paints
    a pixel into the air beside one."""
    for tool in tool_ids:
        if texture_of:
            texture = texture_of(tool)
        else:
            texture = decode_png(jar_read("assets/minecraft/textures/item/%s.png" % path_of(tool)))
        for name, rows in art.items():
            for y, line in enumerate(rows):
                for x, c in enumerate(line):
                    if c != "." and texture[y][x][3] == 0:
                        sys.exit("%s/%s paints off %s at %d,%d" % (kind, name, tool, x, y))


def write_overlays(kind, art, patterns, base):
    for pattern in patterns:
        rows = art[path_of(pattern)]
        pixels = [[base[SHADES[c]] if c != "." else (0, 0, 0, 0) for c in line] for line in rows]
        write_png(os.path.join(ASSETS, "textures", path_of(overlay_texture(kind, pattern)) + ".png"), pixels)


def write_models(kind, patterns, permutations, tool_ids):
    """Each overlay is held the way its tool's own model is, so the two stay lined
    up in the hand: a sword is handheld, an elytra is not."""
    parent = jar_json("assets/minecraft/models/item/%s.json" % path_of(tool_ids[0]))["parent"]
    for pattern in patterns:
        for palette in permutations:
            write_json(os.path.join(ASSETS, "models", path_of(overlay_model(kind, pattern, palette)) + ".json"), {
                "parent": parent,
                "textures": {"layer0": "%s_%s" % (overlay_texture(kind, pattern), palette)},
            })


def trimmed(leaf, kind, patterns, permutations, material_palettes, darker):
    cases = []
    for pattern in patterns:
        for material, palette in sorted(material_palettes.items()):
            if palette == darker and palette + "_darker" in permutations:
                palette += "_darker"
            cases.append({
                "when": {"material": material, "pattern": pattern},
                "model": {"type": "minecraft:model", "model": overlay_model(kind, pattern, palette)},
            })
    return {
        "type": "minecraft:composite",
        "models": [
            leaf,
            {
                "type": "minecraft:select",
                "property": "minecraft:component",
                "component": "minecraft:trim",
                "cases": cases,
                "fallback": {"type": "minecraft:empty"},
            },
        ],
    }


def dress(node, flat_model, wrap):
    """Wrap every use of the tool's flat inventory model, wherever it sits in the
    definition, and leave everything else alone: a spear's model in the hand is a
    different, larger drawing that this art does not fit."""
    if isinstance(node, list):
        return [dress(n, flat_model, wrap) for n in node]
    if not isinstance(node, dict):
        return node
    if node.get("type") == "minecraft:model" and node.get("model") == flat_model:
        return wrap(node)
    return {k: dress(v, flat_model, wrap) for k, v in node.items()}


def undress(node):
    """A definition as it was before this script wrapped it, so dressing it again
    never wraps a trim inside a trim."""
    if isinstance(node, list):
        return [undress(n) for n in node]
    if not isinstance(node, dict):
        return node
    models = node.get("models")
    if node.get("type") == "minecraft:composite" and len(models) == 2 \
            and models[1].get("component") == "minecraft:trim":
        return undress(models[0])
    return {k: undress(v) for k, v in node.items()}


def write_item_definitions(kind, patterns, permutations, material_palettes, tool_ids):
    """Vanilla's own definition for each tool, with the trim drawn over it. A tool
    with no trim, or with a pattern this mod has no art for, draws nothing on top
    and looks exactly as it always has."""
    for tool in tool_ids:
        name = path_of(tool)
        darker = TIER_PALETTE.get(name.split("_")[0])
        definition = jar_json("assets/minecraft/items/%s.json" % name)
        dressed = dress(definition, "minecraft:item/" + name,
            lambda leaf: trimmed(leaf, kind, patterns, permutations, material_palettes, darker))
        if dressed == definition:
            sys.exit("%s's item definition never uses minecraft:item/%s" % (tool, name))
        write_json(os.path.join(RESOURCES, "assets/minecraft/items/%s.json" % name), dressed)


def write_atlas(textures, palette_key, permutations):
    """Atlas sources from every pack are merged, so this adds the tool sprites
    beside vanilla's own rather than replacing its list."""
    write_json(os.path.join(RESOURCES, "assets/minecraft/atlases/items.json"), {
        "sources": [{
            "type": "minecraft:paletted_permutations",
            "palette_key": palette_key,
            "permutations": permutations,
            "textures": textures,
        }]
    })


def write_data(patterns, tool_ids, suite_ids):
    """The suite's tools are optional entries, so the tag still loads on a server
    that runs this mod without them."""
    tag = "%s:trimmable" % MOD_ID
    values = tool_ids + [{"id": item, "required": False} for item in suite_ids]
    write_json(os.path.join(DATA, "tags/item/trimmable.json"), {"values": values})
    for pattern, template in sorted(patterns.items()):
        write_json(os.path.join(DATA, "recipe/%s_trim.json" % path_of(pattern)), {
            "type": "minecraft:smithing_trim",
            "addition": "#minecraft:trim_materials",
            "base": "#" + tag,
            "pattern": pattern,
            "template": template,
        })


# The suite's own gear, beside this mod in the same folder. Their tools share vanilla's
# silhouettes, so this mod's art fits them; their item definitions are theirs, so the
# trim is written into each mod's own file rather than shipped over it from here.
SUITE = os.path.dirname(HERE)
SUITE_TOOLS = ["emerald-tools", "quartz-tools"]
SUITE_ARMOR = ["emerald-armor", "quartz-armor"]
ARMOR_PIECES = ["helmet", "chestplate", "leggings", "boots"]


def suite_assets(mod):
    namespace = mod + "-justfatlard"
    return namespace, os.path.join(SUITE, mod, "src/main/resources/assets", namespace)


def suite_tools(kind):
    """Item id to its definition file, for every suite tool of this kind found."""
    found = {}
    for mod in SUITE_TOOLS:
        namespace, assets = suite_assets(mod)
        items = os.path.join(assets, "items")
        if not os.path.isdir(items):
            print("skipping %s: not beside this mod" % mod)
            continue
        for name in sorted(os.listdir(items)):
            if name.endswith("_%s.json" % kind):
                found["%s:%s" % (namespace, name[:-len(".json")])] = os.path.join(items, name)
    return found


def suite_texture(item):
    namespace, path = item.split(":", 1)
    assets = suite_assets(namespace[:-len("-justfatlard")])[1]
    model = json.load(open(os.path.join(assets, "models/item", path + ".json")))
    texture = path_of(model["textures"]["layer0"])
    return decode_png(open(os.path.join(assets, "textures", texture + ".png"), "rb").read())


def dress_suite_tools(kind, patterns, permutations, material_palettes, found):
    for item, path in found.items():
        namespace, name = item.split(":", 1)
        definition = undress(json.load(open(path)))
        dressed = dress(definition, "%s:item/%s" % (namespace, name),
            lambda leaf: trimmed(leaf, kind, patterns, permutations, material_palettes, None))
        if dressed == definition:
            sys.exit("%s's item definition never uses %s:item/%s" % (item, namespace, name))
        write_json(path, dressed)


def dress_suite_armor(material_palettes):
    """Armor trims are vanilla's and need nothing from this mod to work, but the
    suite's armor icons never showed them. Each piece gets the same select vanilla's
    iron armor uses: a model per material, its own icon with the trim laid over it."""
    for mod in SUITE_ARMOR:
        namespace, assets = suite_assets(mod)
        if not os.path.isdir(assets):
            print("skipping %s: not beside this mod" % mod)
            continue
        prefix = mod.split("-")[0]
        for piece in ARMOR_PIECES:
            name = "%s_%s" % (prefix, piece)
            plain = json.load(open(os.path.join(assets, "models/item", name + ".json")))
            cases = []
            for material, palette in sorted(material_palettes.items()):
                trim_model = "%s_%s_trim" % (name, path_of(material))
                write_json(os.path.join(assets, "models/item", trim_model + ".json"), {
                    "parent": plain["parent"],
                    "textures": {
                        "layer0": plain["textures"]["layer0"],
                        "layer1": "minecraft:trims/items/%s_trim_%s" % (piece, palette),
                    },
                })
                cases.append({"when": material,
                              "model": {"type": "minecraft:model", "model": "%s:item/%s" % (namespace, trim_model)}})
            write_json(os.path.join(assets, "items", name + ".json"), {
                "model": {
                    "type": "minecraft:select",
                    "property": "minecraft:trim_material",
                    "cases": cases,
                    "fallback": {"type": "minecraft:model", "model": "%s:item/%s" % (namespace, name)},
                }
            })


def write_lang(patterns):
    """The templates stop saying armor: each pattern is named for itself, and the
    template says what it applies to now."""
    vanilla = json.loads(jar_read("assets/minecraft/lang/en_us.json"))
    lang = {
        "item.minecraft.smithing_template.armor_trim.applies_to": "Armor, Tools and Elytra",
        "item.minecraft.smithing_template.armor_trim.base_slot_description": "Add armor, a tool or an elytra",
    }
    for pattern in sorted(patterns):
        key = "trim_pattern.minecraft.%s" % path_of(pattern)
        name = vanilla[key]
        if not name.endswith(" Armor Trim"):
            sys.exit("%s is named %r, not '<Name> Armor Trim'" % (key, name))
        lang[key] = name[:-len(" Armor Trim")] + " Trim"
    # In vanilla's own namespace: a key anywhere else loses to vanilla's text or not
    # depending on the order the game happens to load namespaces in. Pandorical merges
    # this with any other mod's copy of the same file.
    write_json(os.path.join(RESOURCES, "assets/minecraft/lang/en_us.json"), lang)


def write_icon():
    """A netherite pickaxe in a gold Silence trim, the most ornate inlay on the
    darkest head, over the smithing table it was made at."""
    gold = decode_png(jar_read("assets/minecraft/textures/palettes/trim/gold.png"))[0]
    tool = decode_png(jar_read("assets/minecraft/textures/item/netherite_pickaxe.png"))
    icon = [list(line) for line in decode_png(jar_read("assets/minecraft/textures/block/smithing_table_top.png"))]
    for y, line in enumerate(read_art("pickaxe")["silence"]):
        for x, c in enumerate(line):
            px = gold[SHADES[c]] if c != "." else tool[y][x]
            if px[3]:
                icon[y][x] = px
    icon = [[px for px in line for _ in range(8)] for line in icon for _ in range(8)]
    write_png(os.path.join(ASSETS, "icon.png"), icon)


def write_wings(patterns, base):
    """The trim on a worn elytra. The game looks for it where it looks for an armor
    trim, under the wings layer's name, and recolours it per material the same way:
    the metadata beside each texture is vanilla's own, naming the palette."""
    art = read_art(WINGS_ART, height=22)
    wings = decode_png(jar_read(WINGS_TEXTURE))
    meta = jar_read("assets/minecraft/textures/trims/entity/humanoid/%s.png.mcmeta" % path_of(sorted(patterns)[0]))
    for pattern in patterns:
        rows = art[path_of(pattern)]
        pixels = [[(0, 0, 0, 0)] * len(wings[0]) for _ in wings]
        for y, line in enumerate(rows):
            for x, c in enumerate(line):
                if c == ".":
                    continue
                tx, ty = WINGS_LEFT + x, WINGS_TOP + y
                if wings[ty][tx][3] == 0:
                    sys.exit("wings/%s paints off the wing at %d,%d" % (path_of(pattern), tx, ty))
                pixels[ty][tx] = base[SHADES[c]]
        asset = jar_json("data/minecraft/trim_pattern/%s.json" % path_of(pattern))["asset_id"]
        namespace, name = asset.split(":", 1)
        path = os.path.join(RESOURCES, "assets", namespace, "textures/trims/entity/wings", name + ".png")
        write_png(path, pixels)
        with open(path + ".mcmeta", "wb") as f:
            f.write(meta)


def clear(*paths):
    """What this script owns is rebuilt from nothing, so a pattern or tool that
    goes away leaves no file behind."""
    for path in paths:
        if os.path.isdir(path):
            shutil.rmtree(path)


if __name__ == "__main__":
    patterns = vanilla_patterns()
    ordered = sorted(patterns)
    palette_key, permutations = trim_permutations()
    base = decode_png(jar_read("assets/minecraft/textures/palettes/%s.png" % path_of(palette_key)))[0]
    material_palettes = materials()

    clear(os.path.join(ASSETS, "textures/trims"), os.path.join(ASSETS, "models/item/trim"),
          os.path.join(DATA, "recipe"), os.path.join(RESOURCES, "assets/minecraft/items"),
          os.path.join(ASSETS, "lang"), os.path.join(RESOURCES, "assets/minecraft/textures/trims"),
          os.path.join(DATA, "tags"))

    textures = []
    all_tools = []
    suite_ids = []
    for kind in KINDS:
        art = read_art(kind)
        missing = sorted(p for p in patterns if path_of(p) not in art)
        if missing:
            sys.exit("no %s art for: %s" % (kind, ", ".join(missing)))
        tool_ids = tools(kind)
        check_fits(kind, art, tool_ids)
        write_overlays(kind, art, ordered, base)
        write_models(kind, ordered, permutations, tool_ids)
        write_item_definitions(kind, ordered, permutations, material_palettes, tool_ids)
        found = suite_tools(kind)
        check_fits(kind, art, list(found), suite_texture)
        dress_suite_tools(kind, ordered, permutations, material_palettes, found)
        suite_ids += list(found)
        textures += [overlay_texture(kind, p) for p in ordered]
        all_tools += tool_ids

    write_atlas(textures, palette_key, permutations)
    write_data(patterns, all_tools, suite_ids)
    dress_suite_armor(material_palettes)
    write_wings(ordered, base)
    write_lang(patterns)
    write_icon()
