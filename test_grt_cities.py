import httpx

def get_tax(street_num, street_name, city, zipcode):
    r = httpx.get('https://grt.edacnm.org/api/by_address', params={
        'street_number': street_num, 'street_name': street_name, 
        'city': city, 'zipcode': zipcode
    })
    data = r.json()['results'][0]
    county = data.get('county', '?')
    loc = data.get('location_code', '?')
    rate = data.get('tax_rate', '?')
    return f"  {street_num} {street_name}, {city} {zipcode} -> County: {county}, Loc: {loc}, Rate: {rate}%"

# Mismo condado (Bernalillo) - DIFERENTES ciudades
print('=== BERNALILLO COUNTY - Diferentes ciudades ===')
print(get_tax('700', 'Main', 'Albuquerque', '87102'))
print(get_tax('100', 'Main', 'Rio Rancho', '87124'))  # Diferente ciudad
print(get_tax('100', 'Camino', 'Los Ranchos de Albuquerque', '87107'))

# Dentro de Albuquerque - muchas direcciones diferentes
print('\n=== ALBUQUERQUE - Muchas direcciones ===')
print(get_tax('1', 'Central', 'Albuquerque', '87102'))
print(get_tax('5000', 'Central', 'Albuquerque', '87108'))
print(get_tax('10000', 'Central', 'Albuquerque', '87123'))
print(get_tax('100', 'San Mateo', 'Albuquerque', '87110'))
print(get_tax('6600', 'Menaul', 'Albuquerque', '87110'))

# Área no incorporada vs ciudad
print('\n=== Comparar área incorporada vs no incorporada ===')
print(get_tax('1000', 'Tramway', 'Albuquerque', '87122'))
