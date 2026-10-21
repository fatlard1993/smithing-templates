package justfatlard.smithing_templates.mixin;

import com.llamalad7.mixinextras.injector.ModifyReturnValue;
import com.llamalad7.mixinextras.sugar.Local;
import justfatlard.smithing_templates.Trims;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.monster.piglin.PiglinAi;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;

/** A piglin leaves alone anyone wearing a gold trim, as it does anyone wearing gold. */
@Mixin(PiglinAi.class)
public abstract class PiglinAiMixin {

	@ModifyReturnValue(method = "isWearingSafeArmor", at = @At("RETURN"))
	private static boolean smithingTemplates$goldTrim(boolean safe, @Local(argsOnly = true) LivingEntity entity) {
		return safe || Trims.wearsGoldTrim(entity);
	}
}
