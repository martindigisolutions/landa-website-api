import httpx

def get_tax(street_num, street_name, city, zipcode):
    r = httpx.get('https://grt.edacnm.org/api/by_address', params={
        'street_number': street_num, 'street_name': street_name, 
        'city': city, 'zipcode': zipcode
    })
    data = r.json()['results'][0]
    return f"{city} ({data.get('county', '?')}, {data.get('location_code', '?')}): {data.get('tax_rate')}%"

# Mismo condado (Bernalillo) - diferentes direcciones en Albuquerque
print('=== BERNALILLO COUNTY (Albuquerque) ===')
print(get_tax('700', 'Main', 'Albuquerque', '87102'))
print(get_tax('200', 'Central', 'Albuquerque', '87102'))
print(get_tax('4000', 'Lomas', 'Albuquerque', '87110'))
print(get_tax('10000', 'Coors', 'Albuquerque', '87121'))

# Otro condado - Dona Ana (Las Cruces)
print('\n=== DONA ANA COUNTY (Las Cruces) ===')
print(get_tax('100', 'Main', 'Las Cruces', '88001'))
print(get_tax('500', 'University', 'Las Cruces', '88003'))

# Otro condado - Santa Fe
print('\n=== SANTA FE COUNTY ===')
print(get_tax('100', 'Palace', 'Santa Fe', '87501'))
print(get_tax('500', 'Cerrillos', 'Santa Fe', '87505'))

# Otro condado - San Juan (Farmington)
print('\n=== SAN JUAN COUNTY ===')
print(get_tax('100', 'Main', 'Farmington', '87401'))
