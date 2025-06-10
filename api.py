from aiogram.client.session import aiohttp

API_URL = 'http://localhost:8000/'

async def get_cities_from_api():
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(API_URL + 'api/places/cities') as response:
                if response.status == 200:
                    cities_data = await response.json()
                    return cities_data
                else:
                    print(f"Ошибка API: {response.status}")
                    return []
    except Exception as e:
        print(f"Ошибка при запросе к API: {e}")
        return []

async def get_categories_from_api():
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(API_URL + 'api/places/categories') as response:
                if response.status == 200:
                    cities_data = await response.json()
                    return cities_data
                else:
                    print(f"Ошибка API: {response.status}")
                    return []
    except Exception as e:
        print(f"Ошибка при запросе к API: {e}")
        return []

async def fetch_organizations(data):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(API_URL + 'api/organizations/query', json=data) as response:
                if response.status == 200:
                    organizations_data = await response.json()
                    return organizations_data
                else:
                    print(f"Ошибка API: {response.status}")
                    return []
    except Exception as e:
        print(f"Ошибка при запросе к API: {e}")
        return []

def prepare_cities_db(cities_data):
    db = {}
    for city in cities_data:
        key = city['name'].lower()
        db[key] = {
            'id': city['id'],
            'name': city['name']
        }
    return db
