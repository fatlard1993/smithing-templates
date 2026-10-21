package justfatlard.smithing_templates;

import justfatlard.pandorical.api.PandoricalApi;
import net.fabricmc.api.ModInitializer;

/**
 * Armor trim templates become smithing templates for tools and elytra too: a sword, pickaxe, axe,
 * shovel, hoe, spear or elytra takes a trim at the smithing table the same way armor does.
 *
 * <p>The server half is data alone: one vanilla trim recipe per pattern, with the tools as its
 * base, so the template, the material and the screen are all vanilla's. What a trim looks like on
 * a tool is art shipped to Pandorical clients: an overlay per pattern per kind of tool, and each
 * tool's item definition with it drawn on top, under the {@code minecraft} namespace because that
 * is where the game looks for a vanilla tool's definition. The same clients read the templates
 * with "Armor" taken out of their names. A vanilla client still trims tools; it just sees a plain
 * one with the trim named in its tooltip.
 */
public class Main implements ModInitializer {
	public static final String MOD_ID = "smithing-templates-justfatlard";

	@Override
	public void onInitialize() {
		if (PandoricalApi.isAvailable()) {
			PandoricalApi.content().registerModAssets(MOD_ID);
		}

		System.out.println("[" + MOD_ID + "] Loaded (server-side with Pandorical)");
	}
}
