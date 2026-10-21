package justfatlard.smithing_templates;

import net.minecraft.core.component.DataComponents;
import net.minecraft.world.entity.EquipmentSlot;
import net.minecraft.world.entity.EquipmentSlotGroup;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.equipment.trim.ArmorTrim;
import net.minecraft.world.item.equipment.trim.TrimMaterials;

/** What a trim does beyond its looks, to armor and tools alike. */
public final class Trims {
	private Trims() {}

	/** How much longer a trimmed piece lasts than a plain one. */
	public static final float DURABILITY_BONUS = 0.25F;

	/**
	 * A trimmed piece lasts a quarter longer. Counted from the item's own durability rather than
	 * the stack's, so trimming a piece again, in another pattern or material, never adds a second
	 * quarter on top of the first.
	 */
	public static ItemStack strengthen(ItemStack stack) {
		if (stack.isEmpty() || !stack.has(DataComponents.TRIM)) return stack;
		Integer plain = stack.getPrototype().get(DataComponents.MAX_DAMAGE);
		if (plain == null) return stack;
		stack.set(DataComponents.MAX_DAMAGE, Math.round(plain * (1 + DURABILITY_BONUS)));
		return stack;
	}

	/** Gold inlaid in any worn piece is gold a piglin can see, the same as a piece made of it. */
	public static boolean wearsGoldTrim(LivingEntity entity) {
		for (EquipmentSlot slot : EquipmentSlotGroup.ARMOR) {
			ArmorTrim trim = entity.getItemBySlot(slot).get(DataComponents.TRIM);
			if (trim != null && trim.material().is(TrimMaterials.GOLD)) return true;
		}
		return false;
	}
}
