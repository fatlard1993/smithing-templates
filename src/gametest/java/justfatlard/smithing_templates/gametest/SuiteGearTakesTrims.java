package justfatlard.smithing_templates.gametest;

import justfatlard.pandorical.gametest.Pictures;
import justfatlard.pandorical.gametest.Smoke;
import net.fabricmc.fabric.api.client.gametest.v1.FabricClientGameTest;
import net.fabricmc.fabric.api.client.gametest.v1.context.ClientGameTestContext;
import net.fabricmc.fabric.api.client.gametest.v1.context.TestServerConnection;
import net.fabricmc.fabric.api.client.gametest.v1.context.TestServerContext;
import net.fabricmc.fabric.api.client.gametest.v1.context.TestSingleplayerContext;
import net.fabricmc.loader.api.FabricLoader;
import net.minecraft.client.gui.screens.inventory.InventoryScreen;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Holder;
import net.minecraft.core.component.DataComponents;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.core.registries.Registries;
import net.minecraft.resources.Identifier;
import net.minecraft.world.inventory.SmithingMenu;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.item.equipment.trim.ArmorTrim;
import net.minecraft.world.item.equipment.trim.TrimMaterial;
import net.minecraft.world.item.equipment.trim.TrimPattern;
import net.minecraft.world.level.block.Blocks;

import java.util.ArrayList;
import java.util.List;

/**
 * The suite's own gear takes trims too: an emerald sword and an emerald helmet go in the smithing
 * table's base slot, and a pack of trimmed emerald and quartz gear is photographed.
 *
 * <p>Those mods are not this one's dependencies, so this runs only when they are in the game's
 * {@code mods} folder, and passes without them.
 */
public final class SuiteGearTakesTrims implements FabricClientGameTest {
	private static final long SEED = 20261020L;
	private static final String[] MODS = {"emerald-tools", "quartz-tools", "emerald-armor", "quartz-armor"};

	@Override
	public void runTest(ClientGameTestContext context) {
		if (!Smoke.full()) return;
		for (String mod : MODS) {
			if (!FabricLoader.getInstance().isModLoaded(mod + "-justfatlard")) return;
		}
		try (TestSingleplayerContext world = Pictures.world(context, SEED)) {
			TestServerContext server = world.getServer();
			TestServerConnection connection = world.getConnection();
			Pictures.stage(context, server, Pictures.MORNING);

			BlockPos table = server.computeOnServer(s -> {
				BlockPos spawn = connection.getServerPlayer().blockPosition();
				return Pictures.dryGround(s.overworld(), spawn.getX(), spawn.getZ(), 16);
			});
			check(table != null, "no dry ground near spawn");
			server.runOnServer(s -> s.overworld().setBlockAndUpdate(table, Blocks.SMITHING_TABLE.defaultBlockState()));
			Pictures.open(context, server, connection, table);
			server.runOnServer(s -> {
				SmithingMenu menu = (SmithingMenu) connection.getServerPlayer().containerMenu;
				for (String item : new String[] {"emerald-tools-justfatlard:emerald_sword", "emerald-armor-justfatlard:emerald_helmet"}) {
					check(menu.getSlot(SmithingMenu.BASE_SLOT).mayPlace(new ItemStack(item(item))),
						item + " was refused from the base slot");
				}
			});

			server.runCommand("gamemode survival @a");
			server.runOnServer(s -> {
				var player = connection.getServerPlayer();
				player.closeContainer();
				List<Holder.Reference<TrimPattern>> patterns = s.registryAccess()
					.lookupOrThrow(Registries.TRIM_PATTERN).listElements().toList();
				List<Holder.Reference<TrimMaterial>> materials = s.registryAccess()
					.lookupOrThrow(Registries.TRIM_MATERIAL).listElements().toList();
				List<Item> gear = new ArrayList<>();
				for (String mod : MODS) {
					String prefix = mod.substring(0, mod.indexOf('-'));
					String[] pieces = mod.endsWith("tools")
						? new String[] {"sword", "pickaxe", "axe", "shovel", "hoe"}
						: new String[] {"helmet", "chestplate", "leggings", "boots"};
					for (String piece : pieces) gear.add(item(mod + "-justfatlard:" + prefix + "_" + piece));
				}
				var pack = player.getInventory();
				for (int i = 0; i < 36; i++) {
					ItemStack stack = new ItemStack(gear.get(i % gear.size()));
					stack.set(DataComponents.TRIM,
						new ArmorTrim(materials.get(i % materials.size()), patterns.get(i % patterns.size())));
					pack.setItem(i, stack);
				}
			});
			context.waitFor(client -> client.gui.screen() == null);
			context.setScreen(() -> new InventoryScreen(net.minecraft.client.Minecraft.getInstance().player));
			context.waitTicks(10);
			Pictures.shootScreen(context, connection, "trimmed-suite-gear");
		}
	}

	private static Item item(String id) {
		Item item = BuiltInRegistries.ITEM.getValue(Identifier.parse(id));
		check(item != Items.AIR, id + " is not registered");
		return item;
	}

	private static void check(boolean ok, String complaint) {
		if (!ok) throw new AssertionError(complaint);
	}
}
