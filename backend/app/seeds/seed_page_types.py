from s8.db.database import db

async def seed_page_types():
    page_types = [
        {"name": "single", "description": "Single page website", "max_pages": 1},
        {"name": "double", "description": "Two-page website", "max_pages": 2},
        {"name": "custom", "description": "Custom number of pages", "max_pages": 20},
    ]
    await db.page_types.delete_many({})
    await db.page_types.insert_many(page_types)
    print("Page types seeded!")
