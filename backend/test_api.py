import requests
import json

BASE = 'http://localhost:5000/api'

def log(titulo, data):
    print(f'\n{"="*60}')
    print(f'  {titulo}')
    print(f'{"="*60}')
    print(json.dumps(data, indent=2, ensure_ascii=False)[:800])

def main():
    # ---------- 1. LOGIN ----------
    print('\n🔐 Probando LOGIN...')
    r = requests.post(f'{BASE}/auth/login', json={
        'username': 'admin',
        'password': 'Admin123!',
    })
    print(f'   Status: {r.status_code}')

    if r.status_code != 200:
        print(f'   ❌ Error: {r.text}')
        return

    data = r.json()
    log('LOGIN OK', {
        'usuario': data['usuario']['nombre'],
        'roles': data['usuario']['roles'],
        'permisos_count': len(data['usuario']['permisos']),
    })

    token = data['access_token']
    headers = {'Authorization': f'Bearer {token}'}

    # ---------- 2. /ME ----------
    print('\n👤 Probando /me...')
    r = requests.get(f'{BASE}/auth/me', headers=headers)
    print(f'   Status: {r.status_code}')
    log('/me', r.json())

    # ---------- 3. MESAS ----------
    print('\n🍽️  Probando listar mesas...')
    r = requests.get(f'{BASE}/mesas', headers=headers)
    print(f'   Status: {r.status_code}')
    if r.status_code == 200:
        mesas = r.json()
        print(f'   Mesas encontradas: {len(mesas)}')
    else:
        print(f'   Respuesta: {r.text[:200]}')

    # ---------- 4. INVENTARIO ----------
    print('\n📦 Probando listar insumos...')
    r = requests.get(f'{BASE}/inventario/insumos', headers=headers)
    print(f'   Status: {r.status_code}')
    if r.status_code == 200:
        insumos = r.json()
        print(f'   Insumos encontrados: {len(insumos)}')
        if insumos:
            log('Primer insumo', insumos[0])
    else:
        print(f'   Respuesta: {r.text[:200]}')

    # ---------- 5. REPORTES ----------
    print('\n📊 Probando KPIs...')
    r = requests.get(f'{BASE}/reportes/kpis', headers=headers)
    print(f'   Status: {r.status_code}')
    if r.status_code == 200:
        log('KPIs', r.json())
    else:
        print(f'   Respuesta: {r.text[:200]}')

    # ---------- 6. RESUMEN INVENTARIO ----------
    print('\n📈 Probando resumen inventario...')
    r = requests.get(f'{BASE}/inventario/resumen', headers=headers)
    print(f'   Status: {r.status_code}')
    if r.status_code == 200:
        log('Resumen', r.json())
    else:
        print(f'   Respuesta: {r.text[:200]}')

    print(f'\n{"="*60}')
    print('✅ Pruebas completadas')
    print(f'{"="*60}\n')


if __name__ == '__main__':
    try:
        main()
    except requests.exceptions.ConnectionError:
        print('\n❌ No se puede conectar al backend.')
        print('   Asegúrate de que Flask esté corriendo en otra terminal:')
        print('   py app.py\n')
    except Exception as e:
        print(f'\n❌ Error inesperado: {type(e).__name__}: {e}\n')