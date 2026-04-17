from typing import Any
import requests
import logging

def fetch_products_list(session, query: str) -> list[dict[str, Any]]:
    url = 'https://www.wildberries.ru/__internal/u-search/exactmatch/ru/common/v18/search'
    params = {
        'dest': '1259570983',
        'resultset': 'catalog',
        'sort': 'popular',
        'curr': 'rub',
        'lang': 'ru',
        #'ab_testing': 'false',
        #'appType': '1',
        #'hide_vflags': '4294967296',
        #'inheritFilters': 'false',
        #'spp': '30',
        #'suppressSpellcheck': 'false'
    }
    headers = {
        'Cookie': 'x_wbaas_token=1.1000.fb92bd65c323401b90849f3e4b49917a.MHwzNy4xMTMuMjE1LjI0MXxNb3ppbGxhLzUuMCAoWDExOyBMaW51eCB4ODZfNjQ7IHJ2OjE0OS4wKSBHZWNrby8yMDEwMDEwMSBGaXJlZm94LzE0OS4wfDE3Nzc0NTY3NzN8cmV1c2FibGV8MnxleUpvWVhOb0lqb2lJbjA9fDB8M3wxNzc2ODUxOTczfDE=.MEYCIQDm7YOWzal7CUMAB72WH35tn7mO8t+qG4KeeOWAME7qOwIhAJEmzeCnVeqQorW0FbLW5uz7gd5aNhRsEKMkARkSYSja; _cp=1',
        #'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:149.0) Gecko/20100101 Firefox/149.0',
        #'Accept': '/',
        #'Accept-Language': 'en-US,en;q=0.9',
        #'Accept-Encoding': 'gzip, deflate, br, zstd',
        #'Referer': 'https://www.wildberries.ru/catalog/0/search.aspx?search=',
        #'deviceid': 'site_768880546eda4f8ca1c78ea8a822effe',
        #'x-queryid': 'qidnull20260416171507',
        #'x-requested-with': 'XMLHttpRequest',
        #'x-spa-version': '14.5.8',
        #'x-userid': '0',
        #'Sec-GPC': '1',
        #'Connection': 'keep-alive',
        #'Sec-Fetch-Dest': 'empty',
        #'Sec-Fetch-Mode': 'cors',
        #'Sec-Fetch-Site': 'same-origin',
        #'Priority': 'u=4',
        #'TE': 'trailers'
    }
    products_list = []

    local_params = params.copy()
    local_params['query'] = query

    page = 1
    while True:
        catalog_response = session.get(url + f"?page={str(page)}", params=local_params, headers=headers)
        catalog_response.raise_for_status()
        catalog_data = catalog_response.json()
        if not catalog_data:
            logging.error("Can't parse catalog json")
            break
        total = catalog_data.get('total')
        products_json_list = catalog_data.get('products')
        if not products_json_list:
            if page == 1: logging.error(f"Error: No products found for {query} search phrase")
            break
        try:
            for product_json in products_json_list:
                details = get_description_and_features(session=session, product_json=product_json)
                products_list.append({
                    'link': f"https://www.wildberries.ru/catalog/{str(product_json.get('id'))}/detail.aspx",
                    'product_id': product_json.get('id'),
                    'name': product_json.get('name'),
                    'price': get_price(product_json=product_json),
                    'description': details.get('description'),
                    'image_links': ','.join(get_image_links(product_json=product_json)),
                    'features': ','.join(details.get('features', [])),
                    'seller_name': product_json.get('supplier'),
                    'seller_link': f"https://www.wildberries.ru/seller/{str(product_json.get('supplierId'))}",
                    'sizes': ','.join([s.get('name') for s in product_json.get('sizes', [])]),
                    'stocks': product_json.get('totalQuantity'),# not sure - check by comparing with some of 'stock' fied in each size
                    'rating': product_json.get('reviewRating'),# maybe replace with nm prefix
                    'reviews_count': product_json.get('feedbacks'),# maybe replace with nm prefix
                })
                logging.info(f"Added product with id {product_json.get('id')}")
        except KeyboardInterrupt: #allows to write some data if interrupted
            break
        page += 1
    
    return products_list

def get_price(product_json: dict[str, Any]) -> float | None:
    product_sizes = product_json.get('sizes')
    if not product_sizes or len(product_sizes) <= 0: return None

    prices = product_sizes[0].get('price')
    if not prices: return None
    price = int(str(prices.get('basic'))) / 100
    return price

def get_cdn_identifiers(product_json: dict[str, Any]) -> dict[str, str]:
    product_id = str(product_json.get('id'))
    vol = product_id[0:-5]
    part = product_id[0:-3]
    return {'product_id': product_id, 'vol': vol, 'part': part}

def get_image_links(product_json: dict[str, Any]) -> list[str]:
    product_identifiers = get_cdn_identifiers(product_json=product_json)
    image_count = int(product_json.get('pics', 0))
    image_links = []
    for i in range(1, image_count + 1):
        image_url = f"https://mow-basket-cdn-03.geobasket.ru/vol{product_identifiers['vol']}/part{product_identifiers['part']}/{product_identifiers['product_id']}/images/tm/{i}.webp"
        image_links.append(image_url)
    return image_links

def get_description_and_features(session, product_json: dict[str, Any]) -> dict[str, Any]:
    product_identifiers = get_cdn_identifiers(product_json=product_json)
    description_url = f"https://mow-basket-cdn-01.geobasket.ru/vol{product_identifiers['vol']}/part{product_identifiers['part']}/{product_identifiers['product_id']}/info/ru/card.json"
    product_data_response = session.get(description_url)
    try: product_data_response.raise_for_status()
    except:
        logging.error(f"Couldn't retrieve description and features for product with id: {product_identifiers['product_id']}")
        return {'description': 'No description', 'features': 'No features'}
    data = product_data_response.json()
    description = str(data.get('description'))

    options = data.get('options')
    features = []
    if not options: logging.error(f"No feature found for product with id: {product_identifiers['product_id']}")
    else:
        for option in options:
            features.append(f"{option.get('name')}:{option.get('value')}")

    return {
        'description': description,
        'features': features
    }

import pandas as pd
def main(product_query: str):
    session = requests.Session()
    result = fetch_products_list(session=session, query=product_query)

    df = pd.DataFrame(result)
    df.rename(columns={
        'link': 'Ссылка на товар',
        'product_id': 'Артикул',
        'name': 'Название',
        'price': 'Цена',
        'description': 'Описание',
        'image_links': 'Ссылки на изображения',
        'features': 'Характеристики',
        'seller_name': 'Название селлера',
        'seller_link': 'Ссылка на селлера',
        'sizes': 'Размеры',
        'stocks': 'Остатки по товару',
        'rating': 'Рейтинг',
        'reviews_count': 'Количество отзывов',
    }, inplace=True)
    df.to_excel('output.xlsx', index=False)


import argparse
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", default="INFO")
    parser.add_argument("--query", required=True)
    args = parser.parse_args()
    logging.basicConfig(level=getattr(logging, args.log.upper()))
    main(args.query)