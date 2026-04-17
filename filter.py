import pandas as pd

def main(full_catalog):
    result = []

    df = pd.read_excel(full_catalog)
    data = df.to_dict(orient="records")
    for prod in data:
        rate = float(str(prod.get('Рейтинг')))
        price = int(str(prod.get('Цена')))
        additional_info = str(prod.get('Характеристики')).split(',')
        country = ''
        for info in additional_info:
            if info.split(':')[0] == 'Страна производства':
                country = info.split(':')[1]
                break
        if rate < 4.5: continue
        if price >= 10000: continue
        if country != 'Россия': continue

        result.append(prod)
    df = pd.DataFrame(result)
    df.to_excel("filtered_output.xlsx", index=False)


if __name__ == '__main__':
    main('output.xlsx')