"""
Curated reference dataset and lookup engine for the Health Tracker.
Provides verified nutritional reference values (calories and macronutrients)
and standardized portion sizes for common meals and ingredients.

Policy:
- Never invent nutritional precision.
- Clearly flag unsupported foods and uncertain estimates.
- Keep assumed portion sizes explicit.
"""
from typing import Optional, Dict, Any, List, Tuple
from decimal import Decimal
import re


# Standard Food Reference Item
class FoodReferenceItem:
    def __init__(
        self,
        name: str,
        standard_portion_desc: str,
        standard_weight_g: Optional[float],
        calories: int,
        protein_g: float,
        carbs_g: float,
        fat_g: float,
        aliases: List[str],
        category: str = "general",
    ):
        self.name = name
        self.standard_portion_desc = standard_portion_desc
        self.standard_weight_g = standard_weight_g
        self.calories = calories
        self.protein_g = protein_g
        self.carbs_g = carbs_g
        self.fat_g = fat_g
        self.aliases = [a.lower().strip() for a in aliases]
        self.category = category


# Curated dataset of reference foods with verified nutritional baselines
FOOD_DATABASE: List[FoodReferenceItem] = [
    # Breads & Grains
    FoodReferenceItem(
        name="Roti / Chapati",
        standard_portion_desc="1 medium roti (~40g)",
        standard_weight_g=40.0,
        calories=104,
        protein_g=3.1,
        carbs_g=22.0,
        fat_g=0.4,
        aliases=["roti", "rotis", "chapati", "chapatis", "phulka", "phulkas"],
        category="grains",
    ),
    FoodReferenceItem(
        name="Cooked White Rice",
        standard_portion_desc="1 bowl/cup (~150g)",
        standard_weight_g=150.0,
        calories=195,
        protein_g=4.0,
        carbs_g=43.0,
        fat_g=0.5,
        aliases=["rice", "white rice", "steamed rice", "cooked rice", "chawal"],
        category="grains",
    ),
    FoodReferenceItem(
        name="Cooked Brown Rice",
        standard_portion_desc="1 bowl/cup (~150g)",
        standard_weight_g=150.0,
        calories=165,
        protein_g=3.5,
        carbs_g=35.0,
        fat_g=1.4,
        aliases=["brown rice"],
        category="grains",
    ),
    FoodReferenceItem(
        name="Plain Paratha",
        standard_portion_desc="1 medium paratha (~70g)",
        standard_weight_g=70.0,
        calories=210,
        protein_g=4.0,
        carbs_g=30.0,
        fat_g=8.5,
        aliases=["paratha", "parathas", "plain paratha"],
        category="grains",
    ),
    FoodReferenceItem(
        name="Aloo Paratha",
        standard_portion_desc="1 stuffed paratha (~100g)",
        standard_weight_g=100.0,
        calories=260,
        protein_g=5.0,
        carbs_g=38.0,
        fat_g=10.0,
        aliases=["aloo paratha", "alu paratha"],
        category="grains",
    ),
    FoodReferenceItem(
        name="Bread (Whole Wheat)",
        standard_portion_desc="1 slice (~30g)",
        standard_weight_g=30.0,
        calories=75,
        protein_g=3.0,
        carbs_g=13.0,
        fat_g=1.0,
        aliases=["wheat bread", "brown bread", "whole wheat bread"],
        category="grains",
    ),
    FoodReferenceItem(
        name="Bread (White)",
        standard_portion_desc="1 slice (~30g)",
        standard_weight_g=30.0,
        calories=80,
        protein_g=2.5,
        carbs_g=15.0,
        fat_g=1.0,
        aliases=["white bread", "bread", "bread slice", "toast"],
        category="grains",
    ),
    FoodReferenceItem(
        name="Oats (Cooked)",
        standard_portion_desc="1 bowl (~150g)",
        standard_weight_g=150.0,
        calories=140,
        protein_g=5.0,
        carbs_g=25.0,
        fat_g=2.5,
        aliases=["oats", "oatmeal", "porridge"],
        category="grains",
    ),

    # Dal, Legumes & Curries
    FoodReferenceItem(
        name="Yellow Dal / Dal Tadka",
        standard_portion_desc="1 katori/cup (~150g)",
        standard_weight_g=150.0,
        calories=165,
        protein_g=9.0,
        carbs_g=22.0,
        fat_g=4.5,
        aliases=["dal", "dal tadka", "yellow dal", "toor dal", "moong dal", "daal"],
        category="legumes",
    ),
    FoodReferenceItem(
        name="Dal Makhani",
        standard_portion_desc="1 katori/cup (~150g)",
        standard_weight_g=150.0,
        calories=260,
        protein_g=8.5,
        carbs_g=24.0,
        fat_g=14.0,
        aliases=["dal makhani", "daal makhani"],
        category="legumes",
    ),
    FoodReferenceItem(
        name="Rajma / Chhole Curry",
        standard_portion_desc="1 bowl (~150g)",
        standard_weight_g=150.0,
        calories=190,
        protein_g=9.0,
        carbs_g=28.0,
        fat_g=5.0,
        aliases=["rajma", "chhole", "chana masala", "chickpeas", "kidney beans"],
        category="legumes",
    ),
    FoodReferenceItem(
        name="Sambar",
        standard_portion_desc="1 bowl/cup (~150g)",
        standard_weight_g=150.0,
        calories=90,
        protein_g=3.5,
        carbs_g=14.0,
        fat_g=2.5,
        aliases=["sambar", "sambhar"],
        category="legumes",
    ),

    # Dairy & Proteins
    FoodReferenceItem(
        name="Paneer (Raw/Cubes)",
        standard_portion_desc="100g serving",
        standard_weight_g=100.0,
        calories=265,
        protein_g=18.0,
        carbs_g=3.5,
        fat_g=20.0,
        aliases=["paneer", "cottage cheese"],
        category="dairy",
    ),
    FoodReferenceItem(
        name="Paneer Butter Masala",
        standard_portion_desc="1 bowl (~150g)",
        standard_weight_g=150.0,
        calories=320,
        protein_g=10.0,
        carbs_g=12.0,
        fat_g=26.0,
        aliases=["paneer butter masala", "paneer masala", "shahi paneer"],
        category="dairy",
    ),
    FoodReferenceItem(
        name="Palak Paneer",
        standard_portion_desc="1 bowl (~150g)",
        standard_weight_g=150.0,
        calories=230,
        protein_g=11.0,
        carbs_g=8.0,
        fat_g=17.0,
        aliases=["palak paneer"],
        category="dairy",
    ),
    FoodReferenceItem(
        name="Curd / Plain Yogurt",
        standard_portion_desc="1 katori/cup (~150g)",
        standard_weight_g=150.0,
        calories=95,
        protein_g=5.0,
        carbs_g=7.0,
        fat_g=5.0,
        aliases=["curd", "dahi", "yogurt", "plain curd", "raita"],
        category="dairy",
    ),
    FoodReferenceItem(
        name="Milk (Whole/Full Cream)",
        standard_portion_desc="1 cup / glass (~200ml)",
        standard_weight_g=200.0,
        calories=120,
        protein_g=6.5,
        carbs_g=9.5,
        fat_g=6.5,
        aliases=["milk", "cow milk", "whole milk"],
        category="dairy",
    ),
    FoodReferenceItem(
        name="Boiled Egg",
        standard_portion_desc="1 large egg (~50g)",
        standard_weight_g=50.0,
        calories=74,
        protein_g=6.3,
        carbs_g=0.4,
        fat_g=5.0,
        aliases=["egg", "eggs", "boiled egg", "hard boiled egg"],
        category="poultry",
    ),
    FoodReferenceItem(
        name="Egg Omelette / Fried Egg",
        standard_portion_desc="1 egg with oil/butter (~60g)",
        standard_weight_g=60.0,
        calories=110,
        protein_g=6.5,
        carbs_g=0.8,
        fat_g=9.0,
        aliases=["omelette", "omelet", "fried egg", "scrambled egg", "bhurji", "egg bhurji"],
        category="poultry",
    ),
    FoodReferenceItem(
        name="Grilled Chicken Breast",
        standard_portion_desc="100g cooked breast",
        standard_weight_g=100.0,
        calories=165,
        protein_g=31.0,
        carbs_g=0.0,
        fat_g=3.6,
        aliases=["chicken breast", "grilled chicken", "roast chicken"],
        category="poultry",
    ),
    FoodReferenceItem(
        name="Chicken Curry",
        standard_portion_desc="1 bowl with chicken & gravy (~150g)",
        standard_weight_g=150.0,
        calories=250,
        protein_g=22.0,
        carbs_g=6.0,
        fat_g=15.0,
        aliases=["chicken curry", "murgh curry", "chicken gravy", "butter chicken"],
        category="poultry",
    ),

    # South Indian Breakfast & Staples
    FoodReferenceItem(
        name="Idli",
        standard_portion_desc="1 medium idli (~40g)",
        standard_weight_g=40.0,
        calories=58,
        protein_g=2.0,
        carbs_g=12.0,
        fat_g=0.2,
        aliases=["idli", "idlis", "idly"],
        category="breakfast",
    ),
    FoodReferenceItem(
        name="Plain Dosa",
        standard_portion_desc="1 medium dosa (~80g)",
        standard_weight_g=80.0,
        calories=135,
        protein_g=3.0,
        carbs_g=23.0,
        fat_g=3.5,
        aliases=["dosa", "plain dosa", "dosai"],
        category="breakfast",
    ),
    FoodReferenceItem(
        name="Masala Dosa",
        standard_portion_desc="1 masala dosa with potato (~150g)",
        standard_weight_g=150.0,
        calories=250,
        protein_g=5.0,
        carbs_g=38.0,
        fat_g=9.0,
        aliases=["masala dosa"],
        category="breakfast",
    ),
    FoodReferenceItem(
        name="Poha",
        standard_portion_desc="1 plate/bowl (~150g)",
        standard_weight_g=150.0,
        calories=210,
        protein_g=4.0,
        carbs_g=38.0,
        fat_g=5.0,
        aliases=["poha", "pohe", "aval"],
        category="breakfast",
    ),
    FoodReferenceItem(
        name="Upma",
        standard_portion_desc="1 plate/bowl (~150g)",
        standard_weight_g=150.0,
        calories=200,
        protein_g=4.5,
        carbs_g=34.0,
        fat_g=5.5,
        aliases=["upma", "uppittu"],
        category="breakfast",
    ),
    FoodReferenceItem(
        name="Khichdi",
        standard_portion_desc="1 bowl (~200g)",
        standard_weight_g=200.0,
        calories=220,
        protein_g=7.0,
        carbs_g=38.0,
        fat_g=4.5,
        aliases=["khichdi", "khichri", "pongal"],
        category="grains",
    ),
    FoodReferenceItem(
        name="Veg Biryani / Pulao",
        standard_portion_desc="1 plate (~250g)",
        standard_weight_g=250.0,
        calories=290,
        protein_g=6.0,
        carbs_g=48.0,
        fat_g=9.0,
        aliases=["veg biryani", "pulao", "vegetable biryani", "peas pulao"],
        category="grains",
    ),
    FoodReferenceItem(
        name="Chicken Biryani",
        standard_portion_desc="1 plate (~250g)",
        standard_weight_g=250.0,
        calories=380,
        protein_g=20.0,
        carbs_g=45.0,
        fat_g=13.0,
        aliases=["chicken biryani", "biryani"],
        category="poultry",
    ),

    # Fruits & Vegetables
    FoodReferenceItem(
        name="Apple",
        standard_portion_desc="1 medium apple (~150g)",
        standard_weight_g=150.0,
        calories=78,
        protein_g=0.4,
        carbs_g=20.0,
        fat_g=0.3,
        aliases=["apple", "apples"],
        category="fruit",
    ),
    FoodReferenceItem(
        name="Banana",
        standard_portion_desc="1 medium banana (~120g)",
        standard_weight_g=120.0,
        calories=105,
        protein_g=1.3,
        carbs_g=27.0,
        fat_g=0.3,
        aliases=["banana", "bananas", "kela"],
        category="fruit",
    ),
    FoodReferenceItem(
        name="Orange",
        standard_portion_desc="1 medium orange (~130g)",
        standard_weight_g=130.0,
        calories=62,
        protein_g=1.2,
        carbs_g=15.0,
        fat_g=0.2,
        aliases=["orange", "oranges", "santara"],
        category="fruit",
    ),
    FoodReferenceItem(
        name="Mixed Fresh Salad",
        standard_portion_desc="1 bowl cucumber, tomato, carrot (~150g)",
        standard_weight_g=150.0,
        calories=35,
        protein_g=1.5,
        carbs_g=7.0,
        fat_g=0.5,
        aliases=["salad", "green salad", "cucumber salad", "fresh salad"],
        category="vegetable",
    ),
    FoodReferenceItem(
        name="Cooked Mixed Vegetables (Sabzi)",
        standard_portion_desc="1 katori/bowl (~150g)",
        standard_weight_g=150.0,
        calories=130,
        protein_g=3.0,
        carbs_g=14.0,
        fat_g=7.0,
        aliases=["sabzi", "sabji", "mixed veg", "bhindi", "gobi", "aloo gobi"],
        category="vegetable",
    ),

    # Beverages & Snacks
    FoodReferenceItem(
        name="Masala Chai (with Milk & Sugar)",
        standard_portion_desc="1 cup (~150ml)",
        standard_weight_g=150.0,
        calories=90,
        protein_g=2.5,
        carbs_g=12.0,
        fat_g=3.5,
        aliases=["chai", "tea", "masala chai", "milk tea"],
        category="beverage",
    ),
    FoodReferenceItem(
        name="Coffee with Milk & Sugar",
        standard_portion_desc="1 cup (~150ml)",
        standard_weight_g=150.0,
        calories=95,
        protein_g=2.5,
        carbs_g=13.0,
        fat_g=3.5,
        aliases=["coffee", "filter coffee", "latte", "cappuccino"],
        category="beverage",
    ),
    FoodReferenceItem(
        name="Black Coffee / Green Tea (Unsweetened)",
        standard_portion_desc="1 cup (~150ml)",
        standard_weight_g=150.0,
        calories=5,
        protein_g=0.2,
        carbs_g=0.5,
        fat_g=0.0,
        aliases=["black coffee", "green tea", "black tea", "espresso"],
        category="beverage",
    ),
    FoodReferenceItem(
        name="Samosa",
        standard_portion_desc="1 fried piece (~80g)",
        standard_weight_g=80.0,
        calories=220,
        protein_g=3.5,
        carbs_g=24.0,
        fat_g=12.0,
        aliases=["samosa", "samosas"],
        category="snack",
    ),
    FoodReferenceItem(
        name="Almonds",
        standard_portion_desc="10 almonds (~12g)",
        standard_weight_g=12.0,
        calories=70,
        protein_g=2.5,
        carbs_g=2.5,
        fat_g=6.0,
        aliases=["almond", "almonds", "badam"],
        category="snack",
    ),
    FoodReferenceItem(
        name="Peanut Butter",
        standard_portion_desc="1 tablespoon (~16g)",
        standard_weight_g=16.0,
        calories=95,
        protein_g=4.0,
        carbs_g=3.0,
        fat_g=8.0,
        aliases=["peanut butter"],
        category="snack",
    ),
    FoodReferenceItem(
        name="Pizza Slice (Cheese/Veg)",
        standard_portion_desc="1 medium slice (~100g)",
        standard_weight_g=100.0,
        calories=260,
        protein_g=11.0,
        carbs_g=30.0,
        fat_g=10.0,
        aliases=["pizza", "pizza slice"],
        category="snack",
    ),
]


def find_food_in_reference(text: str) -> Optional[Tuple[FoodReferenceItem, str]]:
    """
    Search reference database for a matching food item.
    Returns (item, matched_alias) or None.
    Sorts matches by alias length descending to match longest specific phrases first.
    """
    text_lower = text.lower().strip()
    
    # Check exact alias matches first
    for item in sorted(FOOD_DATABASE, key=lambda i: max(len(a) for a in i.aliases), reverse=True):
        for alias in sorted(item.aliases, key=len, reverse=True):
            # Word boundary regex search to avoid matching inside words
            pattern = rf"\b{re.escape(alias)}\b"
            if re.search(pattern, text_lower):
                return item, alias
                
    return None


def extract_quantity_and_multiplier(text: str, matched_alias: str, default_desc: str) -> Tuple[float, str]:
    """
    Extract numeric multiplier (e.g., '2 rotis', '1.5 cups', 'half plate')
    and format the human-readable assumed portion string.
    Returns (multiplier, portion_notes).
    """
    text_lower = text.lower().strip()
    
    # Check for written numbers or fractions
    word_to_num = {
        "one": 1.0, "two": 2.0, "three": 3.0, "four": 4.0, "five": 5.0,
        "half": 0.5, "quarter": 0.25, "double": 2.0, "triple": 3.0,
    }
    
    multiplier = 1.0
    found_number = False

    # Check for direct number before the alias, e.g. "2 rotis", "3 eggs", "1.5 cup rice"
    pattern = rf"(\d+(?:\.\d+)?|\bhalf\b|\bone\b|\btwo\b|\bthree\b|\bfour\b|\bfive\b)\s*(?:pieces?|cups?|bowls?|katoris?|plates?|slices?|glasses?)?\s*(?:of\s*)?\b{re.escape(matched_alias)}\b"
    match = re.search(pattern, text_lower)
    
    if match:
        num_str = match.group(1).lower()
        if num_str in word_to_num:
            multiplier = word_to_num[num_str]
        else:
            try:
                multiplier = float(num_str)
            except ValueError:
                multiplier = 1.0
        found_number = True
    else:
        # Check if number appears anywhere in the single item clause, e.g. "roti 2"
        post_pattern = rf"\b{re.escape(matched_alias)}\b\s*(\d+(?:\.\d+)?)"
        post_match = re.search(post_pattern, text_lower)
        if post_match:
            try:
                multiplier = float(post_match.group(1))
                found_number = True
            except ValueError:
                multiplier = 1.0

    if multiplier <= 0 or multiplier > 20:
        multiplier = 1.0  # Sanity bound

    if found_number and multiplier != 1.0:
        if multiplier.is_integer():
            count_str = f"{int(multiplier)}x"
        else:
            count_str = f"{multiplier}x"
        portion_desc = f"{count_str} standard portion ({default_desc})"
    else:
        portion_desc = f"1x standard portion ({default_desc})"

    return multiplier, portion_desc
