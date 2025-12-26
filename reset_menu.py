from sqlalchemy.orm import Session
from database import SessionLocal, engine
import models

# 1. Create the database tables if they don't exist
models.Base.metadata.create_all(bind=engine)


def reset_menu():
    db = SessionLocal()

    # 2. WIPE OLD MENU (But keep users/orders safe)
    print("⚠️  Wiping old menu items...")
    db.query(models.MenuItem).delete()
    db.commit()

    # 3. DEFINE THE NEW 'DESI ZAIKA' MENU
    # Note: For items with multiple sizes (Half/Full), we create separate entries.
    menu_items = [
        # --- CHAMPARAN SPECIAL ---
        {"name": "Matka Chicken (2pc)", "price": 179, "category": "Champaran Special", "is_veg": False},
        {"name": "Matka Chicken (4pc)", "price": 304, "category": "Champaran Special", "is_veg": False},
        {"name": "Matka Chicken (8pc)", "price": 509, "category": "Champaran Special", "is_veg": False},
        {"name": "Matka Chicken (1kg)", "price": 849, "category": "Champaran Special", "is_veg": False},
        {"name": "Matka Mutton (2pc)", "price": 229, "category": "Champaran Special", "is_veg": False},
        {"name": "Matka Mutton (4pc)", "price": 399, "category": "Champaran Special", "is_veg": False},
        {"name": "Matka Mutton (8pc)", "price": 735, "category": "Champaran Special", "is_veg": False},
        {"name": "Matka Mutton (1kg)", "price": 1400, "category": "Champaran Special", "is_veg": False},
        {"name": "Litti Chokha (2 Pc)", "price": 80, "category": "Champaran Special", "is_veg": True},

        # --- MOMOS ---
        {"name": "Veg Momos (Half)", "price": 60, "category": "Momos", "is_veg": True},
        {"name": "Veg Momos (Full)", "price": 100, "category": "Momos", "is_veg": True},
        {"name": "Paneer Momos (Half)", "price": 90, "category": "Momos", "is_veg": True},
        {"name": "Paneer Momos (Full)", "price": 150, "category": "Momos", "is_veg": True},
        {"name": "Chicken Momos (Half)", "price": 120, "category": "Momos", "is_veg": False},
        {"name": "Chicken Momos (Full)", "price": 200, "category": "Momos", "is_veg": False},
        {"name": "Tandoori Veg Momos (Half)", "price": 130, "category": "Momos", "is_veg": True},
        {"name": "Tandoori Veg Momos (Full)", "price": 190, "category": "Momos", "is_veg": True},
        {"name": "Tandoori Paneer Momos (Half)", "price": 150, "category": "Momos", "is_veg": True},
        {"name": "Tandoori Paneer Momos (Full)", "price": 210, "category": "Momos", "is_veg": True},
        {"name": "Tandoori Chicken Momos (Half)", "price": 170, "category": "Momos", "is_veg": False},
        {"name": "Tandoori Chicken Momos (Full)", "price": 250, "category": "Momos", "is_veg": False},

        # --- CHINESE STARTERS ---
        {"name": "Crispy Chilli Potato", "price": 130, "category": "Chinese Starters", "is_veg": True},
        {"name": "Honey Chilli Potato", "price": 140, "category": "Chinese Starters", "is_veg": True},
        {"name": "Chilli Paneer", "price": 210, "category": "Chinese Starters", "is_veg": True},
        {"name": "Chilli Mushroom", "price": 210, "category": "Chinese Starters", "is_veg": True},
        {"name": "Chilli Chaap", "price": 200, "category": "Chinese Starters", "is_veg": True},
        {"name": "Manchurian (Dry/Gravy)", "price": 199, "category": "Chinese Starters", "is_veg": True},
        {"name": "Chilli Chicken", "price": 249, "category": "Chinese Starters", "is_veg": False},
        {"name": "Chicken Lollipop", "price": 270, "category": "Chinese Starters", "is_veg": False},
        {"name": "Chilli Fish", "price": 300, "category": "Chinese Starters", "is_veg": False},

        # --- TANDOORI STARTERS (VEG) ---
        {"name": "Paneer Tikka Ajwain (Half)", "price": 190, "category": "Tandoori Veg", "is_veg": True},
        {"name": "Paneer Tikka Ajwain (Full)", "price": 350, "category": "Tandoori Veg", "is_veg": True},
        {"name": "Paneer Tikka Achari (Half)", "price": 190, "category": "Tandoori Veg", "is_veg": True},
        {"name": "Paneer Tikka Achari (Full)", "price": 350, "category": "Tandoori Veg", "is_veg": True},
        {"name": "Tandoori Chaap Achari (Half)", "price": 170, "category": "Tandoori Veg", "is_veg": True},
        {"name": "Tandoori Chaap Achari (Full)", "price": 299, "category": "Tandoori Veg", "is_veg": True},
        {"name": "Malai Soya Chaap (Half)", "price": 190, "category": "Tandoori Veg", "is_veg": True},
        {"name": "Malai Soya Chaap (Full)", "price": 299, "category": "Tandoori Veg", "is_veg": True},
        {"name": "Tandoori Mushroom (Half)", "price": 170, "category": "Tandoori Veg", "is_veg": True},
        {"name": "Tandoori Mushroom (Full)", "price": 250, "category": "Tandoori Veg", "is_veg": True},
        {"name": "Hara Bhara Kabab", "price": 200, "category": "Tandoori Veg", "is_veg": True},
        {"name": "Dahi Ke Shole", "price": 200, "category": "Tandoori Veg", "is_veg": True},

        # --- TANDOORI STARTERS (NON-VEG) ---
        {"name": "Murgh Malai Tikka (Half)", "price": 259, "category": "Tandoori Non-Veg", "is_veg": False},
        {"name": "Murgh Malai Tikka (Full)", "price": 400, "category": "Tandoori Non-Veg", "is_veg": False},
        {"name": "Tandoori Chicken (Half)", "price": 270, "category": "Tandoori Non-Veg", "is_veg": False},
        {"name": "Tandoori Chicken (Full)", "price": 499, "category": "Tandoori Non-Veg", "is_veg": False},
        {"name": "Afghani Chicken (Half)", "price": 290, "category": "Tandoori Non-Veg", "is_veg": False},
        {"name": "Afghani Chicken (Full)", "price": 550, "category": "Tandoori Non-Veg", "is_veg": False},
        {"name": "Chicken Tikka (Half)", "price": 249, "category": "Tandoori Non-Veg", "is_veg": False},
        {"name": "Chicken Tikka (Full)", "price": 390, "category": "Tandoori Non-Veg", "is_veg": False},
        {"name": "Chicken Kali Mirch Tikka (Half)", "price": 260, "category": "Tandoori Non-Veg", "is_veg": False},
        {"name": "Chicken Kali Mirch Tikka (Full)", "price": 450, "category": "Tandoori Non-Veg", "is_veg": False},
        {"name": "Chicken Fry (Half)", "price": 250, "category": "Tandoori Non-Veg", "is_veg": False},
        {"name": "Chicken Fry (Full)", "price": 400, "category": "Tandoori Non-Veg", "is_veg": False},
        {"name": "Chicken Seekh Kabab (Half)", "price": 249, "category": "Tandoori Non-Veg", "is_veg": False},
        {"name": "Chicken Seekh Kabab (Full)", "price": 450, "category": "Tandoori Non-Veg", "is_veg": False},
        {"name": "Fish Tikka (Half)", "price": 300, "category": "Tandoori Non-Veg", "is_veg": False},
        {"name": "Fish Tikka (Full)", "price": 600, "category": "Tandoori Non-Veg", "is_veg": False},

        # --- MAIN COURSE (VEG) ---
        {"name": "Chaap Butter Masala (Half)", "price": 210, "category": "Main Course (Veg)", "is_veg": True},
        {"name": "Chaap Butter Masala (Full)", "price": 320, "category": "Main Course (Veg)", "is_veg": True},
        {"name": "Dal Makhni (Half)", "price": 189, "category": "Main Course (Veg)", "is_veg": True},
        {"name": "Dal Makhni (Full)", "price": 280, "category": "Main Course (Veg)", "is_veg": True},
        {"name": "Dal Tadka (Half)", "price": 140, "category": "Main Course (Veg)", "is_veg": True},
        {"name": "Dal Tadka (Full)", "price": 220, "category": "Main Course (Veg)", "is_veg": True},
        {"name": "Kadai Paneer (Half)", "price": 199, "category": "Main Course (Veg)", "is_veg": True},
        {"name": "Kadai Paneer (Full)", "price": 310, "category": "Main Course (Veg)", "is_veg": True},
        {"name": "Kadai Chaap (Half)", "price": 170, "category": "Main Course (Veg)", "is_veg": True},
        {"name": "Kadai Chaap (Full)", "price": 290, "category": "Main Course (Veg)", "is_veg": True},
        {"name": "Paneer Lababdar (Half)", "price": 200, "category": "Main Course (Veg)", "is_veg": True},
        {"name": "Paneer Lababdar (Full)", "price": 310, "category": "Main Course (Veg)", "is_veg": True},
        {"name": "Shahi Paneer (Half)", "price": 210, "category": "Main Course (Veg)", "is_veg": True},
        {"name": "Shahi Paneer (Full)", "price": 330, "category": "Main Course (Veg)", "is_veg": True},
        {"name": "Mix Veg (Half)", "price": 180, "category": "Main Course (Veg)", "is_veg": True},
        {"name": "Mix Veg (Full)", "price": 290, "category": "Main Course (Veg)", "is_veg": True},
        {"name": "Matar Paneer (Half)", "price": 190, "category": "Main Course (Veg)", "is_veg": True},
        {"name": "Matar Paneer (Full)", "price": 300, "category": "Main Course (Veg)", "is_veg": True},
        {"name": "Matar Mushroom (Half)", "price": 190, "category": "Main Course (Veg)", "is_veg": True},
        {"name": "Matar Mushroom (Full)", "price": 300, "category": "Main Course (Veg)", "is_veg": True},
        {"name": "Paneer Butter Masala (Half)", "price": 210, "category": "Main Course (Veg)", "is_veg": True},
        {"name": "Paneer Butter Masala (Full)", "price": 320, "category": "Main Course (Veg)", "is_veg": True},
        {"name": "Paneer Do Pyaza (Half)", "price": 190, "category": "Main Course (Veg)", "is_veg": True},
        {"name": "Paneer Do Pyaza (Full)", "price": 300, "category": "Main Course (Veg)", "is_veg": True},

        # --- MAIN COURSE (NON-VEG) ---
        {"name": "Egg Curry (2pc)", "price": 180, "category": "Main Course (Non-Veg)", "is_veg": False},
        {"name": "Egg Curry (4pc)", "price": 250, "category": "Main Course (Non-Veg)", "is_veg": False},
        {"name": "Butter Chicken (Half)", "price": 330, "category": "Main Course (Non-Veg)", "is_veg": False},
        {"name": "Butter Chicken (Full)", "price": 600, "category": "Main Course (Non-Veg)", "is_veg": False},
        {"name": "Kadai Chicken (Half)", "price": 300, "category": "Main Course (Non-Veg)", "is_veg": False},
        {"name": "Kadai Chicken (Full)", "price": 580, "category": "Main Course (Non-Veg)", "is_veg": False},
        {"name": "Chicken Tikka Masala (Half)", "price": 310, "category": "Main Course (Non-Veg)", "is_veg": False},
        {"name": "Chicken Tikka Masala (Full)", "price": 590, "category": "Main Course (Non-Veg)", "is_veg": False},
        {"name": "Chicken Lababdar (Half)", "price": 320, "category": "Main Course (Non-Veg)", "is_veg": False},
        {"name": "Chicken Lababdar (Full)", "price": 600, "category": "Main Course (Non-Veg)", "is_veg": False},
        {"name": "Fish Curry (Half)", "price": 350, "category": "Main Course (Non-Veg)", "is_veg": False},
        {"name": "Fish Curry (Full)", "price": 650, "category": "Main Course (Non-Veg)", "is_veg": False},

        # --- BREADS ---
        {"name": "Tandoori Roti", "price": 20, "category": "Breads", "is_veg": True},
        {"name": "Butter Tandoori Roti", "price": 25, "category": "Breads", "is_veg": True},
        {"name": "Tawa Roti", "price": 20, "category": "Breads", "is_veg": True},
        {"name": "Butter Tawa Roti", "price": 25, "category": "Breads", "is_veg": True},
        {"name": "Plain Naan", "price": 40, "category": "Breads", "is_veg": True},
        {"name": "Butter Naan", "price": 45, "category": "Breads", "is_veg": True},
        {"name": "Garlic Naan", "price": 55, "category": "Breads", "is_veg": True},
        {"name": "Lachha Paratha", "price": 45, "category": "Breads", "is_veg": True},
        {"name": "Missi Roti", "price": 49, "category": "Breads", "is_veg": True},
        {"name": "Stuffed Naan", "price": 70, "category": "Breads", "is_veg": True},

        # --- RICE & BIRYANI ---
        {"name": "Steam Rice (Half)", "price": 75, "category": "Rice & Biryani", "is_veg": True},
        {"name": "Steam Rice (Full)", "price": 120, "category": "Rice & Biryani", "is_veg": True},
        {"name": "Jeera Rice (Half)", "price": 85, "category": "Rice & Biryani", "is_veg": True},
        {"name": "Jeera Rice (Full)", "price": 130, "category": "Rice & Biryani", "is_veg": True},
        {"name": "Matar Pulao (Half)", "price": 99, "category": "Rice & Biryani", "is_veg": True},
        {"name": "Matar Pulao (Full)", "price": 149, "category": "Rice & Biryani", "is_veg": True},
        {"name": "Veg Pulao (Half)", "price": 99, "category": "Rice & Biryani", "is_veg": True},
        {"name": "Veg Pulao (Full)", "price": 149, "category": "Rice & Biryani", "is_veg": True},
        {"name": "Veg Biryani", "price": 210, "category": "Rice & Biryani", "is_veg": True},
        {"name": "Chicken Biryani", "price": 309, "category": "Rice & Biryani", "is_veg": False},

        # --- THALI ---
        {"name": "Veg Thali", "price": 180, "category": "Thali", "is_veg": True},
        {"name": "Veg Deluxe Thali", "price": 240, "category": "Thali", "is_veg": True},
        {"name": "Chicken Thali", "price": 220, "category": "Thali", "is_veg": False},
        {"name": "Chicken Deluxe Thali", "price": 279, "category": "Thali", "is_veg": False},
        {"name": "Mutton Thali", "price": 350, "category": "Thali", "is_veg": False},

        # --- NOODLES & FRIED RICE ---
        {"name": "Hakka Noodles (Veg)", "price": 130, "category": "Chinese Main", "is_veg": True},
        {"name": "Hakka Noodles (Egg)", "price": 150, "category": "Chinese Main", "is_veg": False},
        {"name": "Hakka Noodles (Chicken)", "price": 180, "category": "Chinese Main", "is_veg": False},
        {"name": "Chilli Garlic Noodles (Veg)", "price": 130, "category": "Chinese Main", "is_veg": True},
        {"name": "Chilli Garlic Noodles (Egg)", "price": 150, "category": "Chinese Main", "is_veg": False},
        {"name": "Chilli Garlic Noodles (Chicken)", "price": 180, "category": "Chinese Main", "is_veg": False},
        {"name": "Singapore Noodles", "price": 160, "category": "Chinese Main", "is_veg": True},
        {"name": "Fried Rice (Veg)", "price": 130, "category": "Chinese Main", "is_veg": True},
        {"name": "Fried Rice (Egg)", "price": 150, "category": "Chinese Main", "is_veg": False},
        {"name": "Fried Rice (Chicken)", "price": 180, "category": "Chinese Main", "is_veg": False},

        # --- SOUPS ---
        {"name": "Manchow Soup (Veg)", "price": 140, "category": "Soups", "is_veg": True},
        {"name": "Manchow Soup (Chicken)", "price": 160, "category": "Soups", "is_veg": False},
        {"name": "Hot & Sour Soup (Veg)", "price": 140, "category": "Soups", "is_veg": True},
        {"name": "Hot & Sour Soup (Chicken)", "price": 165, "category": "Soups", "is_veg": False},

        # --- ROLLS ---
        {"name": "Veg Roll", "price": 70, "category": "Rolls", "is_veg": True},
        {"name": "Paneer Roll", "price": 100, "category": "Rolls", "is_veg": True},
        {"name": "Chaap Roll", "price": 100, "category": "Rolls", "is_veg": True},
        {"name": "Egg Roll", "price": 90, "category": "Rolls", "is_veg": False},
        {"name": "Chicken Roll", "price": 120, "category": "Rolls", "is_veg": False},
        {"name": "Egg Chicken Roll", "price": 130, "category": "Rolls", "is_veg": False},
        {"name": "Double Egg Chicken Roll", "price": 150, "category": "Rolls", "is_veg": False},

        # --- SIDES & BEVERAGES ---
        {"name": "Plain Raita", "price": 80, "category": "Sides", "is_veg": True},
        {"name": "Boondi Raita", "price": 90, "category": "Sides", "is_veg": True},
        {"name": "Mix Raita", "price": 99, "category": "Sides", "is_veg": True},
        {"name": "Green Salad", "price": 90, "category": "Sides", "is_veg": True},
        {"name": "Chole Rice", "price": 90, "category": "Quick Bites", "is_veg": True},
        {"name": "Rajma Rice", "price": 90, "category": "Quick Bites", "is_veg": True},
        {"name": "Maggie", "price": 50, "category": "Quick Bites", "is_veg": True},
        {"name": "Chai", "price": 20, "category": "Beverages", "is_veg": True},
    ]

    print(f"🔄 Uploading {len(menu_items)} new menu items...")

    # 4. INSERT INTO DATABASE
    for item in menu_items:
        new_item = models.MenuItem(
            name=item["name"],
            price=item["price"],
            category=item["category"],
            is_veg=item["is_veg"],
            is_available=True
        )
        db.add(new_item)

    # 5. CREATE DEFAULT USERS (If they don't exist)
    # Check if admin exists to avoid errors on re-runs
    if not db.query(models.User).filter(models.User.username == "owner").first():
        print("👤 Creating Users...")
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

        users = [
            models.User(username="owner", password_hash=pwd_context.hash("admin123"), role="owner"),
            models.User(username="manager", password_hash=pwd_context.hash("man123"), role="manager"),
            models.User(username="waiter", password_hash=pwd_context.hash("wait123"), role="waiter"),
        ]
        db.add_all(users)
        print("✅ Users Created: owner/admin123, manager/man123, waiter/wait123")

    db.commit()
    db.close()
    print("🎉 Success! Database reset. Users created. Menu uploaded.")


if __name__ == "__main__":
    reset_menu()