package justfatlard.smithing_templates.gametest;

import justfatlard.pandorical.gametest.Pictures;
import justfatlard.pandorical.gametest.Smoke;
import justfatlard.smithing_templates.Trims;
import net.fabricmc.fabric.api.client.gametest.v1.FabricClientGameTest;
import net.fabricmc.fabric.api.client.gametest.v1.context.ClientGameTestContext;
import net.fabricmc.fabric.api.client.gametest.v1.context.TestServerConnection;
import net.fabricmc.fabric.api.client.gametest.v1.context.TestServerContext;
import net.fabricmc.fabric.api.client.gametest.v1.context.TestSingleplayerContext;
import net.minecraft.client.CameraType;
import net.minecraft.client.gui.screens.inventory.InventoryScreen;
import net.minecraft.client.resources.language.I18n;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Holder;
import net.minecraft.core.component.DataComponents;
import net.minecraft.core.registries.Registries;
import net.minecraft.resources.Identifier;
import net.minecraft.world.entity.EquipmentSlot;
import net.minecraft.world.entity.monster.piglin.PiglinAi;
import net.minecraft.world.inventory.SmithingMenu;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.item.crafting.SmithingTrimRecipe;
import net.minecraft.world.item.equipment.trim.ArmorTrim;
import net.minecraft.world.item.equipment.trim.TrimMaterial;
import net.minecraft.world.item.equipment.trim.TrimMaterials;
import net.minecraft.world.item.equipment.trim.TrimPattern;
import net.minecraft.world.item.equipment.trim.TrimPatterns;
import net.minecraft.world.level.block.Blocks;

import java.util.List;

/**
 * A tool or an elytra goes in the smithing table's base slot and comes out trimmed and a quarter
 * stronger, once only; shears and wooden and stone tools do not go in; a gold trim placates piglins; the templates read as
 * this mod renames them; and the pictures show the trim: the table with its result, a pack of
 * trimmed tools, and a trimmed elytra worn.
 */
public final class ToolsTakeTrims implements FabricClientGameTest {
	private static final long SEED = 20261019L;

	@Override
	public void runTest(ClientGameTestContext context) {
		if (!Smoke.full()) return;
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
				check(!menu.getSlot(SmithingMenu.BASE_SLOT).mayPlace(new ItemStack(Items.SHEARS)),
					"shears went in the base slot");
				check(!menu.getSlot(SmithingMenu.BASE_SLOT).mayPlace(new ItemStack(Items.WOODEN_SWORD)),
					"a wooden sword went in the base slot");
				check(!menu.getSlot(SmithingMenu.BASE_SLOT).mayPlace(new ItemStack(Items.STONE_PICKAXE)),
					"a stone pickaxe went in the base slot");
				check(menu.getSlot(SmithingMenu.BASE_SLOT).mayPlace(new ItemStack(Items.IRON_AXE)),
					"an axe was refused from the base slot");
				check(menu.getSlot(SmithingMenu.BASE_SLOT).mayPlace(new ItemStack(Items.ELYTRA)),
					"an elytra was refused from the base slot");
				menu.getSlot(SmithingMenu.TEMPLATE_SLOT).set(new ItemStack(Items.SILENCE_ARMOR_TRIM_SMITHING_TEMPLATE));
				menu.getSlot(SmithingMenu.BASE_SLOT).set(new ItemStack(Items.NETHERITE_SWORD));
				menu.getSlot(SmithingMenu.ADDITIONAL_SLOT).set(new ItemStack(Items.GOLD_INGOT));
				ItemStack result = menu.getSlot(SmithingMenu.RESULT_SLOT).getItem();
				ArmorTrim trim = result.get(DataComponents.TRIM);
				check(result.is(Items.NETHERITE_SWORD) && trim != null && trim.pattern().is(TrimPatterns.SILENCE),
					"the table made " + result + " with " + trim);

				int plain = new ItemStack(Items.NETHERITE_SWORD).getMaxDamage();
				int stronger = Math.round(plain * (1 + Trims.DURABILITY_BONUS));
				check(result.getMaxDamage() == stronger,
					"a trimmed sword lasts " + result.getMaxDamage() + ", not " + stronger);
				ItemStack again = SmithingTrimRecipe.applyTrim(result, new ItemStack(Items.DIAMOND),
					s.registryAccess().lookupOrThrow(Registries.TRIM_PATTERN).getOrThrow(TrimPatterns.RIB));
				check(again.getMaxDamage() == stronger, "trimming twice stacked the bonus: " + again.getMaxDamage());
			});

			server.runOnServer(s -> {
				var player = connection.getServerPlayer();
				ItemStack helmet = new ItemStack(Items.IRON_HELMET);
				player.setItemSlot(EquipmentSlot.HEAD, helmet);
				check(!PiglinAi.isWearingSafeArmor(player), "a plain iron helmet placated piglins");
				helmet.set(DataComponents.TRIM, new ArmorTrim(
					s.registryAccess().lookupOrThrow(Registries.TRIM_MATERIAL).getOrThrow(TrimMaterials.GOLD),
					s.registryAccess().lookupOrThrow(Registries.TRIM_PATTERN).getOrThrow(TrimPatterns.SENTRY)));
				check(PiglinAi.isWearingSafeArmor(player), "a gold trim did not placate piglins");
				player.setItemSlot(EquipmentSlot.HEAD, ItemStack.EMPTY);
			});
			context.waitTicks(5);
			Pictures.shootScreen(context, connection, "smithing-table");

			// Every pattern twice over, across the kinds of tool and the materials, so one picture
			// shows most of the art and every palette.
			server.runCommand("gamemode survival @a");
			server.runOnServer(s -> {
				var player = connection.getServerPlayer();
				player.closeContainer();
				List<Holder.Reference<TrimPattern>> patterns = s.registryAccess()
					.lookupOrThrow(Registries.TRIM_PATTERN).listElements().toList();
				List<Holder.Reference<TrimMaterial>> materials = s.registryAccess()
					.lookupOrThrow(Registries.TRIM_MATERIAL).listElements().toList();
				Item[] tools = {Items.IRON_SWORD, Items.DIAMOND_PICKAXE, Items.GOLDEN_AXE, Items.NETHERITE_SHOVEL,
					Items.COPPER_HOE, Items.IRON_SPEAR, Items.GOLDEN_SWORD, Items.NETHERITE_PICKAXE, Items.IRON_AXE,
					Items.DIAMOND_SHOVEL, Items.GOLDEN_HOE, Items.DIAMOND_SPEAR, Items.COPPER_SWORD, Items.ELYTRA};
				var pack = player.getInventory();
				for (int i = 0; i < 36; i++) {
					ItemStack tool = new ItemStack(tools[i % tools.length]);
					tool.set(DataComponents.TRIM,
						new ArmorTrim(materials.get(i % materials.size()), patterns.get(i % patterns.size())));
					pack.setItem(i, tool);
				}
			});
			context.waitFor(client -> client.gui.screen() == null);
			context.setScreen(() -> new InventoryScreen(net.minecraft.client.Minecraft.getInstance().player));
			context.waitTicks(10);
			Pictures.shootScreen(context, connection, "trimmed-tools");

			// The worn elytra, from behind, where its trim is drawn from a texture of its own.
			context.setScreen(() -> null);
			server.runOnServer(s -> {
				ItemStack elytra = new ItemStack(Items.ELYTRA);
				elytra.set(DataComponents.TRIM, new ArmorTrim(
					s.registryAccess().lookupOrThrow(Registries.TRIM_MATERIAL).getOrThrow(TrimMaterials.GOLD),
					s.registryAccess().lookupOrThrow(Registries.TRIM_PATTERN).getOrThrow(TrimPatterns.SILENCE)));
				connection.getServerPlayer().setItemSlot(EquipmentSlot.CHEST, elytra);
			});
			context.runOnClient(client -> {
				check(client.getResourceManager().getResource(
						Identifier.withDefaultNamespace("textures/trims/entity/wings/silence.png")).isPresent(),
					"the worn elytra's trim texture never reached the client");
				client.options.setCameraType(CameraType.THIRD_PERSON_BACK);
			});
			Pictures.shoot(context, connection, "trimmed-elytra");
			context.runOnClient(client -> client.options.setCameraType(CameraType.FIRST_PERSON));

			// Which of two lang files wins comes down to the order namespaces load in, so it is
			// checked last, after the pictures, rather than assumed.
			context.runOnClient(client -> {
				String name = I18n.get("trim_pattern.minecraft.silence");
				check(name.equals("Silence Trim"), "the template still reads " + name);
			});
		}
	}

	private static void check(boolean ok, String complaint) {
		if (!ok) throw new AssertionError(complaint);
	}
}
