from s8.db.database import db

async def seed_website_types():
    website_types = [
        {"name": "portfolio", "description": "Portfolio website"},
        {"name": "landing", "description": "Landing page website"},
        {"name": "ecommerce", "description": "E-commerce platform"},
        {"name": "blog", "description": "Blog website"},
    ]
    await db.website_types.delete_many({})
    await db.website_types.insert_many(website_types)
    print("Website types seeded!")
