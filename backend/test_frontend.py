"""
Diagnóstico rápido de endpoints que alimentan el frontend.
Ejecuta:  py test_frontend.py
"""

import requests
import json

BASE = 'http://localhost:5000/api'


def main():
    # Login
    r = requests.post(f'{BASE}/auth/login', json={
        'username': 'admin', 'password': 'Admin123!',
    })
    token = r.json()['access_token']
    H = {'Authorization': f'Bearer {token}'}

    print('=' * 60)
    print('  DIAGNÓSTICO ENDPOINTS FRONTEND')
    print('=' * 60)

    # 1. Mesas
    r = requests.get(f'{BASE}/mesas', headers=H)
    mesas = r.json()
    print(f'\n🍽️  /mesas ({r.status_code}): {len(mesas)} mesas')
    if mesas:
        print(f'    Ejemplo: {mesas[0]}')
        estados = {}
        for m in mesas:
            estados[m['estado']] = estados.get(m['estado'], 0) + 1
        print(f'    Por estado: {estados}')

    # 2. Productos
    r = requests.get(f'{BASE}/pedidos/productos', headers=H)
    if r.status_code != 200:
        r = requests.get(f'{BASE}/productos', headers=H)
    print(f'\n🍔 /productos ({r.status_code}):', end=' ')
    if r.status_code == 200:
        prods = r.json()
        print(f'{len(prods)} productos')
        if prods:
            print(f'    Ejemplo: {prods[0]}')
    else:
        print(f'❌ {r.text[:100]}')

    # 3. Cocina
    r = requests.get(f'{BASE}/cocina/comandas', headers=H)
    print(f'\n👨‍🍳 /cocina/comandas ({r.status_code}):', end=' ')
    if r.status_code == 200:
        print(f'{len(r.json())} comandas activas')
    else:
        print(f'❌ {r.text[:100]}')

    # 4. Reportes - kpis
    r = requests.get(f'{BASE}/reportes/kpis', headers=H)
    print(f'\n📊 /reportes/kpis ({r.status_code}):', end=' ')
    if r.status_code == 200:
        k = r.json()
        print(f'ventas ${k["ventas"]["total"]:,.0f}, '
              f'{k["pedidos"]["total"]} pedidos')
    else:
        print(f'❌ {r.text[:100]}')

    # 5. Reportes - ventas por día
    r = requests.get(f'{BASE}/reportes/ventas-por-dia', headers=H)
    print(f'📈 /reportes/ventas-por-dia ({r.status_code}):', end=' ')
    if r.status_code == 200:
        print(f'{len(r.json())} días con datos')
    else:
        print(f'❌ {r.text[:100]}')

    # 6. Reportes - top productos
    r = requests.get(f'{BASE}/reportes/top-productos?limite=5', headers=H)
    print(f'🏆 /reportes/top-productos ({r.status_code}):', end=' ')
    if r.status_code == 200:
        tops = r.json()
        print(f'{len(tops)} productos')
        for t in tops[:3]:
            print(f'    - {t["nombre"]}: {t["unidades"]} uds, '
                  f'${t["ingresos"]:,.0f}')
    else:
        print(f'❌ {r.text[:100]}')

    # 7. Reportes - ventas por categoría
    r = requests.get(f'{BASE}/reportes/ventas-por-categoria', headers=H)
    print(f'🍰 /reportes/ventas-por-categoria ({r.status_code}):', end=' ')
    if r.status_code == 200:
        cats = r.json()
        print(f'{len(cats)} categorías')
    else:
        print(f'❌ {r.text[:100]}')

    # 8. Reportes - food cost
    r = requests.get(f'{BASE}/reportes/food-cost-productos', headers=H)
    print(f'💸 /reportes/food-cost-productos ({r.status_code}):', end=' ')
    if r.status_code == 200:
        fc = r.json()
        print(f'{len(fc)} productos analizados')
    else:
        print(f'❌ {r.text[:100]}')

    # 9. Usuarios
    r = requests.get(f'{BASE}/usuarios', headers=H)
    print(f'\n👥 /usuarios ({r.status_code}):', end=' ')
    if r.status_code == 200:
        us = r.json()
        print(f'{len(us)} usuarios')
        for u in us[:3]:
            print(f'    - {u["nombre"]} ({u["username"]}) - '
                  f'roles: {u.get("roles", [])}')
    else:
        print(f'❌ {r.text[:100]}')

    print('\n' + '=' * 60)


if __name__ == '__main__':
    main()