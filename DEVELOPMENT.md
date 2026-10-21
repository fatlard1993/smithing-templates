# Smithing Templates - Development Guide

For what the mod is and how it plays, see [README.md](README.md).

## Installation

Install server-side alongside its declared dependencies (see `fabric.mod.json`); connecting clients need only Pandorical. Version targets live in `gradle.properties` (Minecraft, loader, Fabric API) and `fabric.mod.json` (Java).

## Art

The trims are drawn in `art/`, one file per kind of tool, one sixteen by sixteen block per pattern. Each is drawn once over the silhouette every tool of that kind shares, in four shades that the game recolours per material. `elytra_wings.txt` is the exception: the trim on a worn elytra, drawn on the corner of vanilla's wings texture that holds a wing's broad face, and written where the game looks for an armor trim on the wings layer, `trims/entity/wings/`.

`generate_trims.py` turns the art into everything under `src/main/resources` except `fabric.mod.json` and the changelog: the overlays, the atlas entry, the models, each tool's item definition, the recipes, the tool tag, the lang file and the icon. Edit `art/` or the script, never their output; the script clears its own folders and rebuilds them. Re-run it after a Minecraft version bump: it reads the patterns, palettes, tools, item definitions and pattern names out of the vanilla jar, checks every lit pixel lands on every tool it is drawn for, and stops if vanilla has added a pattern with no art.

## The suite's gear

The script also writes into its neighbours in the suite folder. Emerald Tools and Quartz Tools share vanilla's tool silhouettes, so their item definitions are wrapped with this mod's overlays and their tools join the tag as optional entries; Emerald Armor and Quartz Armor get vanilla's armor trim icons. Each mod keeps owning its own files, so they are written there rather than shipped from here over the top of them, and re-running the script leaves them as it found them. A neighbour that is missing is skipped.

## Mechanics

`Trims` holds what a trim does beyond its looks, and two mixins apply it. `SmithingTrimRecipeMixin` raises the durability of whatever the table trims, counted from the item's own durability so trimming again does not stack. `PiglinAiMixin` adds a worn gold trim to what piglins treat as gold armor.

## Shared paths

`assets/minecraft/atlases/items.json` and `assets/minecraft/items/*.json` sit in Pandorical's one shared asset pack, which keeps one file per path: another mod in the suite that ships one of those paths replaces this one's, and Pandorical logs the clash.

The lang file is `assets/minecraft/lang/en_us.json`, the only place a key reliably beats vanilla's own text: a key in another namespace wins or loses on the order the game loads namespaces in. Lets Cook ships the same path, and Pandorical merges the two key by key. The full gametest checks the renamed text is what a client reads.

## Tests

`./gradlew runClientGameTest -Ptest.level=full` trims a tool at a real smithing table, checks shears, a wooden sword and a stone pickaxe are refused and an axe and an elytra are taken, checks the trim adds a quarter to its durability and only once, checks a gold trim placates piglins, checks the renamed pattern reaches the client, checks the worn elytra's trim texture reaches the client, and photographs the table, a pack of trimmed tools, and a trimmed elytra worn. Add `-Ppictures` to keep the photographs in `screenshots/`.

Add `-Psuite` to load the last builds of Emerald Tools, Quartz Tools, Emerald Armor and Quartz Armor into the test game: `SuiteGearTakesTrims` then checks their gear goes in the smithing table and photographs it trimmed. Build those four first. Without the flag that test passes having done nothing.
