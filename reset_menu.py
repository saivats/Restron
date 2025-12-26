from sqlalchemy.orm import Session
from database import SessionLocal, engine
import models

# Re-build database to ensure clean slate
models.Base.metadata.drop_all(bind=engine)
models.Base.metadata.create_all(bind=engine)


def reset_menu():
    db = SessionLocal()
    print("⚠️  Database wiped. Uploading NEW UPDATED MENU...")

    menu_items = [
        # --- SPECIALS (NEW) ---
        {"cat": "SPECIALS", "name": "Maggie", "price": 50, "veg": True,
         "desc": "Classic comfort noodles cooked with mild spices."},
        {"cat": "SPECIALS", "name": "Chai", "price": 20, "veg": True,
         "desc": "Hot, aromatic indian tea brewed with ginger and cardamom."},

        # --- MOMOS (Updated: 5pcs/10pcs descriptions) ---
        {"cat": "MOMOS", "name": "Veg Momos (Half)", "price": 60, "veg": True,
         "desc": "5 pieces. Steamed dumplings filled with a light, savory mix of cabbage, carrots, and onions."},
        {"cat": "MOMOS", "name": "Veg Momos (Full)", "price": 100, "veg": True,
         "desc": "10 pieces. Steamed dumplings filled with a light, savory mix of cabbage, carrots, and onions."},
        {"cat": "MOMOS", "name": "Paneer Momos (Half)", "price": 90, "veg": True,
         "desc": "5 pieces. Soft, steamed dumplings stuffed with fresh, crumbled cottage cheese and mild herbs."},
        {"cat": "MOMOS", "name": "Paneer Momos (Full)", "price": 150, "veg": True,
         "desc": "10 pieces. Soft, steamed dumplings stuffed with fresh, crumbled cottage cheese and mild herbs."},
        {"cat": "MOMOS", "name": "Chicken Momos (Half)", "price": 120, "veg": False,
         "desc": "5 pieces. Juicy steamed dumplings packed with seasoned minced chicken and aromatic spices."},
        {"cat": "MOMOS", "name": "Chicken Momos (Full)", "price": 200, "veg": False,
         "desc": "10 pieces. Juicy steamed dumplings packed with seasoned minced chicken and aromatic spices."},

        # --- TANDOORI MOMOS (Updated Prices & Count) ---
        {"cat": "MOMOS", "name": "Tandoori Veg Momos (Half)", "price": 130, "veg": True,
         "desc": "5 pieces. Veg dumplings marinated in spicy yogurt masala and roasted in the clay oven."},
        {"cat": "MOMOS", "name": "Tandoori Veg Momos (Full)", "price": 190, "veg": True,
         "desc": "10 pieces. Veg dumplings marinated in spicy yogurt masala and roasted in the clay oven."},
        {"cat": "MOMOS", "name": "Tandoori Paneer Momos (Half)", "price": 150, "veg": True,
         "desc": "5 pieces. Paneer-stuffed momos marinated in tandoori spices and char-grilled to perfection."},
        {"cat": "MOMOS", "name": "Tandoori Paneer Momos (Full)", "price": 210, "veg": True,
         "desc": "10 pieces. Paneer-stuffed momos marinated in tandoori spices and char-grilled to perfection."},
        {"cat": "MOMOS", "name": "Tandoori Chicken Momos (Half)", "price": 170, "veg": False,
         "desc": "5 pieces. Chicken momos coated in bold red marinade and roasted until smoky."},
        {"cat": "MOMOS", "name": "Tandoori Chicken Momos (Full)", "price": 250, "veg": False,
         "desc": "10 pieces. Chicken momos coated in bold red marinade and roasted until smoky."},

        # --- TANDOORI STARTERS (VEG) - (Updated Paneer Tikka Logic) ---
        {"cat": "TANDOORI STARTERS (VEG)", "name": "Paneer Tikka (Ajwain) Half", "price": 190, "veg": True,
         "desc": "Cottage cheese cubes marinated in yogurt and ajwain (carom seeds) for a distinct earthy flavor."},
        {"cat": "TANDOORI STARTERS (VEG)", "name": "Paneer Tikka (Ajwain) Full", "price": 350, "veg": True,
         "desc": "Cottage cheese cubes marinated in yogurt and ajwain (carom seeds) for a distinct earthy flavor."},
        {"cat": "TANDOORI STARTERS (VEG)", "name": "Paneer Tikka (Achari) Half", "price": 190, "veg": True,
         "desc": "Cottage cheese cubes marinated in a tangy, spicy pickle (achar) masala."},
        {"cat": "TANDOORI STARTERS (VEG)", "name": "Paneer Tikka (Achari) Full", "price": 350, "veg": True,
         "desc": "Cottage cheese cubes marinated in a tangy, spicy pickle (achar) masala."},

        # --- CHAAP (Renamed) ---
        {"cat": "TANDOORI STARTERS (VEG)", "name": "Tandoori Chaap (Achari) Half", "price": 170, "veg": True,
         "desc": "Soya chaap sticks marinated in a tangy achari masala and roasted for a spicy kick."},
        {"cat": "TANDOORI STARTERS (VEG)", "name": "Tandoori Chaap (Achari) Full", "price": 299, "veg": True,
         "desc": "Soya chaap sticks marinated in a tangy achari masala and roasted for a spicy kick."},
        {"cat": "TANDOORI STARTERS (VEG)", "name": "Malai Soya Chaap (Half)", "price": 190, "veg": True,
         "desc": "Tender soya chunks coated in a rich, creamy cashew marinade with a hint of black pepper."},
        {"cat": "TANDOORI STARTERS (VEG)", "name": "Malai Soya Chaap (Full)", "price": 299, "veg": True,
         "desc": "Tender soya chunks coated in a rich, creamy cashew marinade with a hint of black pepper."},

        # --- VEG STARTERS (Updated Prices) ---
        {"cat": "TANDOORI STARTERS (VEG)", "name": "Hara Bhara Kabab", "price": 200, "veg": True,
         "desc": "Healthy and delicious patties made from spinach, green peas, and potatoes, deep-fried."},
        {"cat": "TANDOORI STARTERS (VEG)", "name": "Dahi Ke Shole", "price": 200, "veg": True,
         "desc": "Crispy bread rolls stuffed with a creamy, spiced hung curd mixture."},
        {"cat": "TANDOORI STARTERS (VEG)", "name": "Tandoori Mushroom (Half)", "price": 170, "veg": True,
         "desc": "Whole mushrooms marinated in tikka spices and grilled until juicy and smoky."},
        {"cat": "TANDOORI STARTERS (VEG)", "name": "Tandoori Mushroom (Full)", "price": 250, "veg": True,
         "desc": "Whole mushrooms marinated in tikka spices and grilled until juicy and smoky."},

        # --- TANDOORI STARTERS (NON-VEG) - (Updated Prices) ---
        {"cat": "TANDOORI STARTERS (NON-VEG)", "name": "Tandoori Chicken (Half)", "price": 270, "veg": False,
         "desc": "Chicken on the bone marinated in yogurt and traditional Indian spices, roasted in a clay oven."},
        {"cat": "TANDOORI STARTERS (NON-VEG)", "name": "Tandoori Chicken (Full)", "price": 499, "veg": False,
         "desc": "Chicken on the bone marinated in yogurt and traditional Indian spices, roasted in a clay oven."},
        {"cat": "TANDOORI STARTERS (NON-VEG)", "name": "Afghani Chicken (Half)", "price": 290, "veg": False,
         "desc": "Mild and creamy chicken marinated in cashew paste and cream, roasted to a golden hue."},
        {"cat": "TANDOORI STARTERS (NON-VEG)", "name": "Afghani Chicken (Full)", "price": 550, "veg": False,
         "desc": "Mild and creamy chicken marinated in cashew paste and cream, roasted to a golden hue."},

        {"cat": "TANDOORI STARTERS (NON-VEG)", "name": "Chicken Tikka (Half)", "price": 249, "veg": False,
         "desc": "Boneless chicken chunks marinated in spicy yogurt and roasted until charred and tender."},
        {"cat": "TANDOORI STARTERS (NON-VEG)", "name": "Chicken Tikka (Full)", "price": 390, "veg": False,  # UPDATED
         "desc": "Boneless chicken chunks marinated in spicy yogurt and roasted until charred and tender."},

        {"cat": "TANDOORI STARTERS (NON-VEG)", "name": "Chicken Kali Mirch Tikka (Half)", "price": 260, "veg": False,
         "desc": "Boneless chicken marinated with crushed black pepper and cream for a spicy, earthy flavor."},
        {"cat": "TANDOORI STARTERS (NON-VEG)", "name": "Chicken Kali Mirch Tikka (Full)", "price": 450, "veg": False,
         # UPDATED
         "desc": "Boneless chicken marinated with crushed black pepper and cream for a spicy, earthy flavor."},

        {"cat": "TANDOORI STARTERS (NON-VEG)", "name": "Chicken Fry (Half)", "price": 250, "veg": False,
         "desc": "Crispy deep-fried chicken tossed with Indian spices."},
        {"cat": "TANDOORI STARTERS (NON-VEG)", "name": "Chicken Fry (Full)", "price": 400, "veg": False,  # UPDATED
         "desc": "Crispy deep-fried chicken tossed with Indian spices."},

        {"cat": "TANDOORI STARTERS (NON-VEG)", "name": "Chicken Seekh Kabab (Half)", "price": 249, "veg": False,
         "desc": "Minced chicken seasoned with herbs and spices, skewered and grilled in the tandoor."},
        {"cat": "TANDOORI STARTERS (NON-VEG)", "name": "Chicken Seekh Kabab (Full)", "price": 450, "veg": False,
         # UPDATED
         "desc": "Minced chicken seasoned with herbs and spices, skewered and grilled in the tandoor."},

        {"cat": "TANDOORI STARTERS (NON-VEG)", "name": "Fish Tikka (Half)", "price": 300, "veg": False,  # UPDATED
         "desc": "Tender chunks of fish marinated in carom seeds (ajwain) and spices, grilled perfectly."},
        {"cat": "TANDOORI STARTERS (NON-VEG)", "name": "Fish Tikka (Full)", "price": 600, "veg": False,  # UPDATED
         "desc": "Tender chunks of fish marinated in carom seeds (ajwain) and spices, grilled perfectly."},

        # --- CHAMPARAN SPECIAL (Updated Logic) ---
        {"cat": "CHAMPARAN SPECIAL", "name": "Matka Chicken (2pc)", "price": 179, "veg": False,
         "desc": "Ahuna chicken slow-cooked in a sealed clay pot over charcoal."},
        {"cat": "CHAMPARAN SPECIAL", "name": "Matka Chicken (4pc)", "price": 304, "veg": False,
         "desc": "Ahuna chicken slow-cooked in a sealed clay pot over charcoal."},
        {"cat": "CHAMPARAN SPECIAL", "name": "Matka Chicken (8pc)", "price": 509, "veg": False,
         "desc": "Ahuna chicken slow-cooked in a sealed clay pot over charcoal."},
        {"cat": "CHAMPARAN SPECIAL", "name": "Matka Chicken (1kg)", "price": 849, "veg": False,
         "desc": "Ahuna chicken slow-cooked in a sealed clay pot over charcoal."},

        {"cat": "CHAMPARAN SPECIAL", "name": "Matka Mutton (2pc)", "price": 229, "veg": False,
         "desc": "Tender mutton slow-cooked in a sealed clay pot with whole garlic."},
        {"cat": "CHAMPARAN SPECIAL", "name": "Matka Mutton (4pc)", "price": 399, "veg": False,
         "desc": "Tender mutton slow-cooked in a sealed clay pot with whole garlic."},
        {"cat": "CHAMPARAN SPECIAL", "name": "Matka Mutton (8pc)", "price": 735, "veg": False,
         "desc": "Tender mutton slow-cooked in a sealed clay pot with whole garlic."},
        {"cat": "CHAMPARAN SPECIAL", "name": "Matka Mutton (1kg)", "price": 1400, "veg": False,
         "desc": "Tender mutton slow-cooked in a sealed clay pot with whole garlic."},

        {"cat": "CHAMPARAN SPECIAL", "name": "Litti Chokha (2 Pc)", "price": 80, "veg": True,  # UPDATED
         "desc": "Roasted wheat balls stuffed with sattu, served with mashed potato-brinjal chokha."},

        # --- RAITA & SALAD (Updated Salad) ---
        {"cat": "RAITA & SALAD", "name": "Plain Raita", "price": 80, "veg": True, "desc": "Fresh, smooth yogurt."},
        {"cat": "RAITA & SALAD", "name": "Boondi Raita", "price": 90, "veg": True,
         "desc": "Yogurt with crispy pearls."},
        {"cat": "RAITA & SALAD", "name": "Mix Raita", "price": 99, "veg": True, "desc": "Yogurt with chopped veggies."},
        {"cat": "RAITA & SALAD", "name": "Green Salad", "price": 90, "veg": True,  # UPDATED
         "desc": "Slices of fresh cucumber, tomato, onion, and carrot."},

        # --- MAIN COURSE (NON-VEG) ---
        {"cat": "MAIN COURSE (NON-VEG)", "name": "Egg Curry (Half)", "price": 180, "veg": False,
         "desc": "Boiled eggs simmered in a homestyle onion and tomato gravy."},
        {"cat": "MAIN COURSE (NON-VEG)", "name": "Egg Curry (Full)", "price": 280, "veg": False,
         "desc": "Boiled eggs simmered in a homestyle onion and tomato gravy."},
        {"cat": "MAIN COURSE (NON-VEG)", "name": "Butter Chicken (Half)", "price": 330, "veg": False,
         "desc": "Tandoori chicken simmered in a rich, creamy, buttery tomato gravy."},
        {"cat": "MAIN COURSE (NON-VEG)", "name": "Butter Chicken (Full)", "price": 600, "veg": False,
         "desc": "Tandoori chicken simmered in a rich, creamy, buttery tomato gravy."},
        {"cat": "MAIN COURSE (NON-VEG)", "name": "Kadai Chicken (Half)", "price": 300, "veg": False,
         "desc": "Chicken cooked with bell peppers, onions, and freshly ground kadai spices."},
        {"cat": "MAIN COURSE (NON-VEG)", "name": "Kadai Chicken (Full)", "price": 580, "veg": False,
         "desc": "Chicken cooked with bell peppers, onions, and freshly ground kadai spices."},
        {"cat": "MAIN COURSE (NON-VEG)", "name": "Chicken Tikka Masala (Full)", "price": 590, "veg": False,
         "desc": "Roasted chicken tikka pieces tossed in a spicy and thick onion-tomato masala."},
        {"cat": "MAIN COURSE (NON-VEG)", "name": "Chicken Lababdar (Full)", "price": 600, "veg": False,
         "desc": "A rich, Mughal-style chicken curry with a smooth, creamy gravy."},
        {"cat": "MAIN COURSE (NON-VEG)", "name": "Fish Curry (Full)", "price": 650, "veg": False,
         "desc": "Fish fillets cooked in a traditional tangy and spicy curry."},

        # --- MAIN COURSE (VEG) ---
        {"cat": "MAIN COURSE (VEG)", "name": "Dal Makhni (Half)", "price": 189, "veg": True,
         "desc": "Black lentils slow-cooked with butter/cream."},
        {"cat": "MAIN COURSE (VEG)", "name": "Dal Makhni (Full)", "price": 280, "veg": True,
         "desc": "Black lentils slow-cooked with butter/cream."},
        {"cat": "MAIN COURSE (VEG)", "name": "Dal Tadka (Half)", "price": 140, "veg": True,
         "desc": "Yellow lentils tempered with cumin/garlic."},
        {"cat": "MAIN COURSE (VEG)", "name": "Dal Tadka (Full)", "price": 230, "veg": True,
         "desc": "Yellow lentils tempered with cumin/garlic."},
        {"cat": "MAIN COURSE (VEG)", "name": "Kadai Paneer (Half)", "price": 199, "veg": True,
         "desc": "Cottage cheese with peppers and spices."},
        {"cat": "MAIN COURSE (VEG)", "name": "Kadai Paneer (Full)", "price": 310, "veg": True,
         "desc": "Cottage cheese with peppers and spices."},
        {"cat": "MAIN COURSE (VEG)", "name": "Kadai Chaap (Half)", "price": 170, "veg": True,
         "desc": "Soya chaap tossed in spicy kadai gravy."},
        {"cat": "MAIN COURSE (VEG)", "name": "Kadai Chaap (Full)", "price": 290, "veg": True,
         "desc": "Soya chaap tossed in spicy kadai gravy."},
        {"cat": "MAIN COURSE (VEG)", "name": "Paneer Lababdar (Half)", "price": 200, "veg": True,
         "desc": "Soft paneer in creamy onion-tomato gravy."},
        {"cat": "MAIN COURSE (VEG)", "name": "Paneer Lababdar (Full)", "price": 310, "veg": True,
         "desc": "Soft paneer in creamy onion-tomato gravy."},
        {"cat": "MAIN COURSE (VEG)", "name": "Shahi Paneer (Half)", "price": 210, "veg": True,
         "desc": "Paneer in sweet nutty white gravy."},
        {"cat": "MAIN COURSE (VEG)", "name": "Shahi Paneer (Full)", "price": 330, "veg": True,
         "desc": "Paneer in sweet nutty white gravy."},
        {"cat": "MAIN COURSE (VEG)", "name": "Mix Veg (Half)", "price": 180, "veg": True,
         "desc": "Fresh veggies in dry masala."},
        {"cat": "MAIN COURSE (VEG)", "name": "Mix Veg (Full)", "price": 290, "veg": True,
         "desc": "Fresh veggies in dry masala."},
        {"cat": "MAIN COURSE (VEG)", "name": "Matar Paneer (Half)", "price": 190, "veg": True,
         "desc": "Peas and paneer curry."},
        {"cat": "MAIN COURSE (VEG)", "name": "Matar Paneer (Full)", "price": 300, "veg": True,
         "desc": "Peas and paneer curry."},
        {"cat": "MAIN COURSE (VEG)", "name": "Matar Mushroom (Half)", "price": 190, "veg": True,
         "desc": "Mushrooms and peas in spiced gravy."},
        {"cat": "MAIN COURSE (VEG)", "name": "Matar Mushroom (Full)", "price": 300, "veg": True,
         "desc": "Mushrooms and peas in spiced gravy."},
        {"cat": "MAIN COURSE (VEG)", "name": "Paneer Butter Masala (Half)", "price": 210, "veg": True,
         "desc": "Paneer in buttery tomato gravy."},
        {"cat": "MAIN COURSE (VEG)", "name": "Paneer Butter Masala (Full)", "price": 320, "veg": True,
         "desc": "Paneer in buttery tomato gravy."},
        {"cat": "MAIN COURSE (VEG)", "name": "Paneer Do Pyaza (Half)", "price": 190, "veg": True,
         "desc": "Paneer curry with lots of onions."},
        {"cat": "MAIN COURSE (VEG)", "name": "Paneer Do Pyaza (Full)", "price": 300, "veg": True,
         "desc": "Paneer curry with lots of onions."},

        # --- THALI (Updated Mutton Price) ---
        {"cat": "THALI", "name": "Veg Thali", "price": 180, "veg": True,
         "desc": "A complete meal: Dal Tadka, Paneer, Rice, 2 Roti, Salad."},
        {"cat": "THALI", "name": "Veg Deluxe Thali", "price": 240, "veg": True,
         "desc": "A feast: Dal Makhni, Paneer, Jeera Rice, Raita, Sweet, 2 Butter Roti."},
        {"cat": "THALI", "name": "Chicken Thali", "price": 220, "veg": False,
         "desc": "Chicken Curry (2pc), Rice, 2 Roti, Salad."},
        {"cat": "THALI", "name": "Chicken Deluxe Thali", "price": 279, "veg": False,
         "desc": "Chicken Curry (2pc), Jeera Rice, 2 Butter Roti, Raita, Salad, Sweet."},
        {"cat": "THALI", "name": "Mutton Thali", "price": 350, "veg": False,  # UPDATED
         "desc": "Mutton Curry (2pc), Rice, 2 Roti, Salad."},

        # --- BREADS ---
        {"cat": "BREADS", "name": "Tandoori Roti", "price": 20, "veg": True,
         "desc": "Whole wheat bread baked in clay oven."},
        {"cat": "BREADS", "name": "Butter Tandoori Roti", "price": 25, "veg": True,
         "desc": "Tandoori roti with butter."},
        {"cat": "BREADS", "name": "Tawa Roti", "price": 20, "veg": True, "desc": "Thin whole wheat bread on griddle."},
        {"cat": "BREADS", "name": "Butter Tawa Roti", "price": 25, "veg": True, "desc": "Tawa roti with butter."},
        {"cat": "BREADS", "name": "Plain Naan", "price": 40, "veg": True, "desc": "Soft, leavened white flour bread."},
        {"cat": "BREADS", "name": "Butter Naan", "price": 45, "veg": True, "desc": "Soft naan with butter."},
        {"cat": "BREADS", "name": "Garlic Naan", "price": 55, "veg": True, "desc": "Naan with garlic and coriander."},
        {"cat": "BREADS", "name": "Lachha Paratha", "price": 45, "veg": True,
         "desc": "Multi-layered whole wheat bread."},
        {"cat": "BREADS", "name": "Missi Roti", "price": 49, "veg": True, "desc": "Gram flour and wheat bread."},
        {"cat": "BREADS", "name": "Stuffed Naan", "price": 70, "veg": True,
         "desc": "Naan stuffed with spicy potato or paneer."},

        # --- RICE ---
        {"cat": "RICE", "name": "Steam Rice (Half)", "price": 75, "veg": True,
         "desc": "Fluffy, plain white basmati rice."},
        {"cat": "RICE", "name": "Steam Rice (Full)", "price": 120, "veg": True,
         "desc": "Fluffy, plain white basmati rice."},
        {"cat": "RICE", "name": "Jeera Rice (Half)", "price": 85, "veg": True,
         "desc": "Basmati rice with cumin seeds."},
        {"cat": "RICE", "name": "Jeera Rice (Full)", "price": 130, "veg": True,
         "desc": "Basmati rice with cumin seeds."},
        {"cat": "RICE", "name": "Matar Pulao (Half)", "price": 99, "veg": True, "desc": "Mild rice with green peas."},
        {"cat": "RICE", "name": "Matar Pulao (Full)", "price": 149, "veg": True, "desc": "Mild rice with green peas."},
        {"cat": "RICE", "name": "Veg Pulao (Half)", "price": 99, "veg": True, "desc": "Rice with mixed veggies."},
        {"cat": "RICE", "name": "Veg Pulao (Full)", "price": 149, "veg": True, "desc": "Rice with mixed veggies."},
        {"cat": "BIRYANI", "name": "Veg Biryani", "price": 210, "veg": True,
         "desc": "Spicy vegetable curry and saffron rice."},
        {"cat": "BIRYANI", "name": "Chicken Biryani", "price": 309, "veg": False,
         "desc": "Basmati rice layered with spiced chicken."},

        # --- CHINESE ---
        {"cat": "CHINESE STARTERS", "name": "Crispy Chilli Potato", "price": 130, "veg": True,
         "desc": "Crispy potatoes in spicy sauce."},
        {"cat": "CHINESE STARTERS", "name": "Honey Chilli Potato", "price": 140, "veg": True,
         "desc": "Potatoes in sweet and spicy sauce."},
        {"cat": "CHINESE STARTERS", "name": "Chilli Paneer", "price": 210, "veg": True,
         "desc": "Paneer tossed with chillies and soy."},
        {"cat": "CHINESE STARTERS", "name": "Chilli Chicken", "price": 249, "veg": False,
         "desc": "Chicken tossed with peppers and chillies."},
        {"cat": "CHINESE STARTERS", "name": "Chicken Lollipop", "price": 270, "veg": False,
         "desc": "Spicy deep-fried chicken winglets."},
        {"cat": "CHINESE STARTERS", "name": "Chilli Chaap", "price": 200, "veg": True,
         "desc": "Soya chaap in spicy chinese sauce."},
        {"cat": "CHINESE STARTERS", "name": "Manchurian (Dry / Gravy)", "price": 199, "veg": True,
         "desc": "Veg balls in tangy soy-garlic sauce."},
        {"cat": "CHINESE STARTERS", "name": "Chilli Mushroom", "price": 210, "veg": True,
         "desc": "Mushrooms tossed with chillies."},
        {"cat": "CHINESE STARTERS", "name": "Chilli Fish", "price": 300, "veg": False,
         "desc": "Fish fillets in spicy chilli sauce."},

        {"cat": "NOODLES & FRIED RICE", "name": "Hakka Noodles (Veg)", "price": 130, "veg": True,
         "desc": "Stir-fried noodles with veggies."},
        {"cat": "NOODLES & FRIED RICE", "name": "Hakka Noodles (Egg)", "price": 150, "veg": False,
         "desc": "Stir-fried noodles with egg."},
        {"cat": "NOODLES & FRIED RICE", "name": "Hakka Noodles (Chicken)", "price": 180, "veg": False,
         "desc": "Stir-fried noodles with chicken."},
        {"cat": "NOODLES & FRIED RICE", "name": "Chilli Garlic Noodles (Veg)", "price": 130, "veg": True,
         "desc": "Spicy noodles with burnt garlic."},
        {"cat": "NOODLES & FRIED RICE", "name": "Chilli Garlic Noodles (Egg)", "price": 150, "veg": False,
         "desc": "Spicy noodles with burnt garlic and egg."},
        {"cat": "NOODLES & FRIED RICE", "name": "Chilli Garlic Noodles (Chicken)", "price": 180, "veg": False,
         "desc": "Spicy noodles with burnt garlic and chicken."},
        {"cat": "NOODLES & FRIED RICE", "name": "Singapore Noodles", "price": 160, "veg": True,
         "desc": "Noodles with curry powder and veggies."},
        {"cat": "NOODLES & FRIED RICE", "name": "Fried Rice (Veg)", "price": 130, "veg": True,
         "desc": "Rice with carrots, beans, spring onions."},
        {"cat": "NOODLES & FRIED RICE", "name": "Fried Rice (Egg)", "price": 150, "veg": False,
         "desc": "Rice with scrambled eggs."},
        {"cat": "NOODLES & FRIED RICE", "name": "Fried Rice (Chicken)", "price": 180, "veg": False,
         "desc": "Rice with tender chicken."},

        {"cat": "SOUPS", "name": "Manchow Soup (Veg)", "price": 140, "veg": True,
         "desc": "Spicy soy-based soup with crispy noodles."},
        {"cat": "SOUPS", "name": "Manchow Soup (Chicken)", "price": 160, "veg": False,
         "desc": "Spicy soy-based soup with chicken."},
        {"cat": "SOUPS", "name": "Hot & Sour Soup (Veg)", "price": 140, "veg": True,
         "desc": "Tangy soup with vinegar and chilli."},
        {"cat": "SOUPS", "name": "Hot & Sour Soup (Chicken)", "price": 165, "veg": False,
         "desc": "Tangy soup with vinegar and chicken."},

        {"cat": "ROLLS", "name": "Veg Roll", "price": 70, "veg": True, "desc": "Paratha wrap with spiced veggies."},
        {"cat": "ROLLS", "name": "Egg Roll", "price": 90, "veg": False, "desc": "Paratha lined with egg and filling."},
        {"cat": "ROLLS", "name": "Paneer Roll", "price": 100, "veg": True, "desc": "Wrap with spiced paneer cubes."},
        {"cat": "ROLLS", "name": "Chaap Roll", "price": 120, "veg": True, "desc": "Wrap with tandoori soya chaap."},
        {"cat": "ROLLS", "name": "Chicken Roll", "price": 130, "veg": False,
         "desc": "Wrap with roasted chicken chunks."},
        {"cat": "ROLLS", "name": "Egg Chicken Roll", "price": 150, "veg": False,
         "desc": "Roll with both egg and chicken."},
    ]

    for item in menu_items:
        db_item = models.MenuItem(
            name=item["name"],
            price=float(item["price"]),
            category=item["cat"],
            description=item["desc"],
            image_url="",
            is_veg=item["veg"],
            is_available=True
        )
        db.add(db_item)

    db.commit()
    db.close()
    print(f"🎉 Success! Uploaded {len(menu_items)} items. Matka Chicken, Momos, and Specials are live!")


if __name__ == "__main__":
    reset_menu()