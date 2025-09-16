import asyncio
from app.seeds.seed_components import seed_components
from app.seeds.seed_page_types import seed_page_types
from app.seeds.seed_website_types import seed_website_types

async def main():
    print("Starting DB seeding...")

    await seed_page_types()
    await seed_website_types()
    await seed_components()

    print("All seeders completed!")

if __name__ == "__main__":
    asyncio.run(main())
