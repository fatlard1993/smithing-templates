package justfatlard.smithing_templates.mixin;

import com.llamalad7.mixinextras.injector.ModifyReturnValue;
import justfatlard.smithing_templates.Trims;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.crafting.SmithingTrimRecipe;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;

/** Every trim the smithing table makes, armor and tools, comes out stronger. */
@Mixin(SmithingTrimRecipe.class)
public abstract class SmithingTrimRecipeMixin {

	@ModifyReturnValue(method = "applyTrim", at = @At("RETURN"))
	private static ItemStack smithingTemplates$strengthen(ItemStack result) {
		return Trims.strengthen(result);
	}
}
