import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from datetime import datetime, timedelta
import random
from db.session import Base, get_db
from main import app


from models.user import USUARIOS, ROLES, PERSONA
from models.medicamentos import MEDICAMENTOS, INVENTARIO
from datetime import datetime, timedelta, timezone
from jose import jwt
from core.config import settings

#  CONFIGURACIÓN DEL MOCK
SQLALCHEMY_DATABASE_URL = "sqlite://"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

# Inyectamos el mock en la aplicación
app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

# limpiar la base de datos antes de cada test individual
@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def auth_headers():
    db = TestingSessionLocal()
    try:
        rol = db.query(ROLES).filter(ROLES.id_rol == 5).first()
        if not rol:
            rol = ROLES(id_rol=5, nombre_rol="Farmaceuta")
            db.add(rol)
            db.commit()
        persona = db.query(PERSONA).filter(PERSONA.num_documento == 12345678).first()
        if not persona:
            persona = PERSONA(num_documento=12345678, nombres="Test", apellidos="User")
            db.add(persona)
            db.commit()
        usuario = db.query(USUARIOS).filter(USUARIOS.id_usuario == 1).first()
        if not usuario:
            usuario = USUARIOS(
                id_usuario=1,
                num_documento=12345678,
                id_rol=5,
                password="hash_falso",
                estado=True
            )
            db.add(usuario)
            db.commit()

        datos_usuario = {
            "id_usuario": 1,
            "num_documento": 12345678,
            "id_role": 5,
            "role": "Farmaceuta"
        }
        token = crear_token_acceso(data=datos_usuario)
        return {"Authorization": f"Bearer {token}"}
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()
def crear_token_acceso(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRES_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

RANDOM_CODE_BASE = 20000
RANDOM_NAME = "Acetaminofén_Test_Mock"



def test_health_check():
    response = client.get("/")
    assert response.status_code in [200, 404]

def test_crear_medicamento_exitoso(auth_headers):
    payload = {
        "codigo": RANDOM_CODE_BASE,
        "nombre_medicamento": RANDOM_NAME,
        "reg_invima": 2026123,
        "principio_activo": "Acetaminofén",
        "presentacion": "Tabletas 500mg"
    }

    response = client.post("/api/pharmacy/medications", json=payload, headers=auth_headers)
    json_response = response.json()

    assert response.status_code == 201
    assert json_response["hasError"] is False
    assert json_response["Message"] == "Medicamento creado exitosamente."

    # Validamos la data retornada
    data = json_response["Data"]
    assert data["codigo"] == payload["codigo"]
    assert data["nombre_medicamento"] == payload["nombre_medicamento"]
    assert data["presentacion"] == payload["presentacion"]
    assert data["principio_activo"] == payload["principio_activo"]
def test_crear_medicamento_codigo_repetido(auth_headers):
    payload_original = {
        "codigo": RANDOM_CODE_BASE,
        "nombre_medicamento": RANDOM_NAME,
        "reg_invima": 2026123,
        "principio_activo": "Acetaminofén",
        "presentacion": "Tabletas 500mg"
    }
    client.post("/api/pharmacy/medications", json=payload_original, headers=auth_headers)
    payload_repetido = {
        "codigo": RANDOM_CODE_BASE,
        "nombre_medicamento": "Otro Nombre Diferente",
        "reg_invima": 99999,
        "principio_activo": "Otro",
        "presentacion": "Jarabe"
    }

    response = client.post("/api/pharmacy/medications", json=payload_repetido, headers=auth_headers)
    json_response = response.json()

    assert response.status_code == 201
    assert json_response["hasError"] is False
    assert f"El código '{RANDOM_CODE_BASE}' ya está asignado" in json_response["Message"]

    # Validamos que la data retornada sea la del medicamento original
    data = json_response["Data"]
    assert data["codigo"] == RANDOM_CODE_BASE
    assert data["nombre_medicamento"] == RANDOM_NAME # El nombre original
def test_crear_medicamento_nombre_y_presentacion_repetidos(auth_headers):
    payload_original = {
        "codigo": RANDOM_CODE_BASE,
        "nombre_medicamento": RANDOM_NAME,
        "reg_invima": 2026123,
        "principio_activo": "Acetaminofén",
        "presentacion": "Tabletas 500mg"
    }
    client.post("/api/pharmacy/medications", json=payload_original, headers=auth_headers)
    payload = {
        "codigo": RANDOM_CODE_BASE + 1,
        "nombre_medicamento": RANDOM_NAME, # Nombre repetido
        "reg_invima": 2026123,
        "principio_activo": "Acetaminofén",
        "presentacion": "Tabletas 500mg" # Presentación repetida
    }

    response = client.post("/api/pharmacy/medications", json=payload, headers=auth_headers)
    json_response = response.json()

    assert response.status_code == 201
    assert json_response["hasError"] is False
    assert "Ya existe el medicamento" in json_response["Message"]
    assert f"en la presentación 'Tabletas 500mg'" in json_response["Message"]

    # Validamos que nos devuelva el registro que ya existía (el del código original)
    data = json_response["Data"]
    assert data["codigo"] == RANDOM_CODE_BASE
    assert data["nombre_medicamento"] == RANDOM_NAME
def test_crear_medicamento_mismo_nombre_diferente_presentacion(auth_headers):
    """Escenario 4: Mismo nombre pero presentación distinta (debe permitir crear)."""
    NUEVA_PRESENTACION = "Suspensión Oral 120mg"
    payload = {
        "codigo": RANDOM_CODE_BASE + 2, # Código nuevo
        "nombre_medicamento": RANDOM_NAME, # Mismo nombre
        "reg_invima": 2026123,
        "principio_activo": "Acetaminofén",
        "presentacion": NUEVA_PRESENTACION # Presentación nueva
    }

    response = client.post("/api/pharmacy/medications", json=payload, headers=auth_headers)
    json_response = response.json()

    assert response.status_code == 201
    assert json_response["hasError"] is False
    assert json_response["Message"] == "Medicamento creado exitosamente."

    # Validamos que sea el nuevo registro
    data = json_response["Data"]
    assert data["codigo"] == RANDOM_CODE_BASE + 2
    assert data["presentacion"] == NUEVA_PRESENTACION
    assert data["nombre_medicamento"] == RANDOM_NAME
def test_asociar_lote_medicamento_no_existente(auth_headers):
    """
    Escenario: Intento de agregar un lote a un medicamento inexistente.
    """
    codigo_inexistente = 888888
    payload = {
        "lote": "DLX2301",
        "cantidad": 100,
        "fecha_vencimiento": "2028-12-31", # Formato ISO estricto
        "precio": 15000
    }

    response = client.post(f"/api/pharmacy/medications/inventory/{codigo_inexistente}", json=payload, headers=auth_headers)

    # Si recibes un 422, imprimimos el detalle para saber qué campo falló
    if response.status_code == 422:
        print(f"\nError de validación Pydantic: {response.json()}")

    json_response = response.json()

    # Validaciones
    assert response.status_code == 201
    assert json_response["hasError"] is True
    assert "no existe" in json_response["Message"]
    assert json_response["Data"] is None
def test_agregar_lote_exitoso(auth_headers):
    # Crear el medicamento base
    codigo_test = RANDOM_CODE_BASE + 50
    payload_med = {
        "codigo": codigo_test,
        "nombre_medicamento": "Loratadina Test",
        "reg_invima": 123456,
        "principio_activo": "Loratadina",
        "presentacion": "Tabletas 10mg"
    }
    client.post("/api/pharmacy/medications", json=payload_med, headers=auth_headers)

    # lote para ese medicamento
    payload_lote = {
        "lote": "LOT-2026-ABC",
        "cantidad": 500,
        "fecha_vencimiento": "2027-12-31",
        "precio": 12500
    }

    response = client.post(f"/api/pharmacy/medications/inventory/{codigo_test}", json=payload_lote, headers=auth_headers)
    json_response = response.json()

    assert response.status_code == 201
    assert json_response["hasError"] is False
    assert "registrado exitosamente" in json_response["Message"]

    # Validamos la estructura de la data
    data = json_response["Data"]
    assert data["lote"] == payload_lote["lote"]
    assert data["codigo_medicamento"] == codigo_test
    assert "id_inventario" in data  # Verificamos que se generó la PK
def test_agregar_lote_duplicado(auth_headers):
    # Agregar Medicamento
    codigo_med = RANDOM_CODE_BASE + 100
    payload_med = {
        "codigo": codigo_med,
        "nombre_medicamento": "Prueba Duplicados",
        "reg_invima": 777,
        "principio_activo": "Test",
        "presentacion": "Tabletas"
    }
    client.post("/api/pharmacy/medications", json=payload_med, headers=auth_headers)

    # Registrar el lote por primera vez
    lote_nombre = "LOTE-UNICO-123"
    payload_lote = {
        "lote": lote_nombre,
        "cantidad": 100,
        "fecha_vencimiento": "2026-12-31",
        "precio": 5000
    }

    primer_res = client.post(f"/api/pharmacy/medications/inventory/{codigo_med}", json=payload_lote, headers=auth_headers)
    data_original = primer_res.json()["Data"]
    id_original = data_original["id_inventario"]

    # Registrar exactamente el mismo lote
    segundo_res = client.post(f"/api/pharmacy/medications/inventory/{codigo_med}", json=payload_lote, headers=auth_headers)
    json_response = segundo_res.json()

    assert segundo_res.status_code == 201
    assert json_response["hasError"] is True
    assert "ya existe para este medicamento" in json_response["Message"]
    data_retornada = json_response["Data"]
    assert data_retornada["id_inventario"] == id_original
    assert data_retornada["lote"] == lote_nombre
    assert data_retornada["codigo_medicamento"] == codigo_med
def test_agregar_multiples_lotes_a_un_medicamento(auth_headers):

    # Crear el medicamento base
    codigo_med = RANDOM_CODE_BASE + 200
    payload_med = {
        "codigo": codigo_med,
        "nombre_medicamento": "Medicamento Multilote",
        "reg_invima": 888,
        "principio_activo": "Multi-test",
        "presentacion": "Ampolla"
    }
    client.post("/api/pharmacy/medications", json=payload_med, headers=auth_headers)

    # Agregar el Primer Lote
    lote_1 = {
        "lote": "LOTE-AAA",
        "cantidad": 100,
        "fecha_vencimiento": "2026-05-20",
        "precio": 1000
    }
    client.post(f"/api/pharmacy/medications/inventory/{codigo_med}", json=lote_1, headers=auth_headers)

    # Agregar el Segundo Lote
    lote_2 = {
        "lote": "LOTE-BBB",
        "cantidad": 250,
        "fecha_vencimiento": "2026-08-15",
        "precio": 1200
    }
    response = client.post(f"/api/pharmacy/medications/inventory/{codigo_med}", json=lote_2, headers=auth_headers)
    json_response = response.json()

    assert response.status_code == 201
    assert json_response["hasError"] is False
    assert json_response["Data"]["lote"] == "LOTE-BBB"
    assert json_response["Data"]["codigo_medicamento"] == codigo_med

    res_listado = client.get(f"/api/pharmacy/medications/inventory/{codigo_med}", headers=auth_headers)
    data_listado = res_listado.json()

    assert data_listado["hasElements"] is True
    lista_lotes = data_listado["data"]

    assert len(lista_lotes) == 2

    nombres_lotes = [l["lote"] for l in lista_lotes]
    assert "LOTE-AAA" in nombres_lotes
    assert "LOTE-BBB" in nombres_lotes
    cantidades = [l["cantidad"] for l in lista_lotes]
    assert 100 in cantidades
    assert 250 in cantidades

def test_paginacion_medicamentos(auth_headers):
    # Limpiar datos previos
    client.delete("/api/pharmacy/debug/clear-all-data", headers=auth_headers)

    # Crear 10 medicamentos aleatorios
    nombres_creados = []
    for i in range(10):
        codigo = 50000 + i
        nombre = f"Medicamento_Pagi_{i}"
        nombres_creados.append(nombre)

        payload = {
            "codigo": codigo,
            "nombre_medicamento": nombre,
            "reg_invima": 100 + i,
            "principio_activo": "Generico",
            "presentacion": "Tableta"
        }
        client.post("/api/pharmacy/medications", json=payload, headers=auth_headers)

    # Probar Página 1 (Límite 3)
    response_p1 = client.get("/api/pharmacy/medications?page=1&limit=3", headers=auth_headers)
    data_p1 = response_p1.json()

    assert response_p1.status_code == 200
    assert data_p1["hasElements"] is True
    assert data_p1["page"] == 1
    assert data_p1["pages"] == 4
    assert len(data_p1["data"]) == 3
    # Verificar que el primer elemento sea el primero
    assert data_p1["data"][0]["nombre_medicamento"] == nombres_creados[0]

    # Probar Página 2 (Límite 3)
    response_p2 = client.get("/api/pharmacy/medications?page=2&limit=3", headers=auth_headers)
    data_p2 = response_p2.json()

    assert data_p2["page"] == 2
    assert len(data_p2["data"]) == 3
    # El primer elemento de la pág 2 debe ser el 4to creado
    assert data_p2["data"][0]["nombre_medicamento"] == nombres_creados[3]

    # Última Página (Página 4)
    # Debería tener solo 1 elemento
    response_p4 = client.get("/api/pharmacy/medications?page=4&limit=3", headers=auth_headers)
    data_p4 = response_p4.json()
    assert data_p4["page"] == 4
    assert len(data_p4["data"]) == 1
    assert data_p4["data"][0]["nombre_medicamento"] == nombres_creados[9]

    # Probar página fuera de rango
    response_p5 = client.get("/api/pharmacy/medications?page=5&limit=3", headers=auth_headers)
    data_p5 = response_p5.json()
    assert data_p5["hasElements"] is False
    assert len(data_p5["data"]) == 0
def test_lotes_medicamento_inexistente(auth_headers):
    codigo_no_existe = 999999
    response = client.get(f"/api/pharmacy/medications/inventory/{codigo_no_existe}", headers=auth_headers)
    data = response.json()

    assert response.status_code == 200
    assert data["hasElements"] is False
    assert data["data"] == []
    assert data["Message"] == "Medicamento sin registrar o sin lotes asignados"
def test_lotes_medicamento_sin_lotes(auth_headers):

    # Crear el medicamento
    codigo_vacio = 77000
    payload_med = {
        "codigo": codigo_vacio,
        "nombre_medicamento": "Medicamento Solo",
        "reg_invima": 111,
        "principio_activo": "N/A",
        "presentacion": "N/A"
    }
    client.post("/api/pharmacy/medications", json=payload_med, headers=auth_headers)

    # Consultar sus lotes
    response = client.get(f"/api/pharmacy/medications/inventory/{codigo_vacio}", headers=auth_headers)
    data = response.json()

    assert data["hasElements"] is False
    assert len(data["data"]) == 0
    assert data["Message"] == "Medicamento sin registrar o sin lotes asignados"
def test_paginacion_lotes_especifico(auth_headers):

    codigo_med = 88000
    # Crear medicamento
    client.post("/api/pharmacy/medications", json={
        "codigo": codigo_med,
        "nombre_medicamento": "Paginacion Lotes",
        "reg_invima": 222,
        "principio_activo": "Test",
        "presentacion": "Capsula"
    }, headers=auth_headers)

    # Crear 3 lotes con diferentes fechas
    lotes = [
        {"lote": "LOTE-C", "cantidad": 10, "fecha_vencimiento": "2028-01-01", "precio": 100},
        {"lote": "LOTE-A", "cantidad": 10, "fecha_vencimiento": "2025-01-01", "precio": 100},
        {"lote": "LOTE-B", "cantidad": 10, "fecha_vencimiento": "2026-01-01", "precio": 100}
    ]

    for l in lotes:
        client.post(f"/api/pharmacy/medications/inventory/{codigo_med}", json=l, headers=auth_headers)

    # Probar Página 1 con límite 2
    response = client.get(f"/api/pharmacy/medications/inventory/{codigo_med}?page=1&limit=2", headers=auth_headers)
    data = response.json()

    assert data["page"] == 1
    assert data["pages"] == 2
    assert len(data["data"]) == 2
    assert data["data"][0]["lote"] == "LOTE-A"
    assert data["data"][1]["lote"] == "LOTE-B"

    # Probar Página 2
    response_p2 = client.get(f"/api/pharmacy/medications/inventory/{codigo_med}?page=2&limit=2", headers=auth_headers)
    data_p2 = response_p2.json()

    assert data_p2["page"] == 2
    assert len(data_p2["data"]) == 1
    assert data_p2["data"][0]["lote"] == "LOTE-C"
def test_alerta_stock_bajo(auth_headers):
    client.delete("/api/pharmacy/debug/clear-all-data", headers=auth_headers)

    # Crear Medicamentos de prueba
    cod_a = 90001
    cod_b = 90002

    client.post("/api/pharmacy/medications", json={
        "codigo": cod_a, "nombre_medicamento": "Med_Bajo_A",
        "reg_invima": 1, "principio_activo": "P1", "presentacion": "T1"
    }, headers=auth_headers)
    client.post("/api/pharmacy/medications", json={
        "codigo": cod_b, "nombre_medicamento": "Med_Bajo_B",
        "reg_invima": 2, "principio_activo": "P2", "presentacion": "T2"
    }, headers=auth_headers)

    # 3. Crear Lotes
    client.post(f"/api/pharmacy/medications/inventory/{cod_a}", json={
        "lote": "LOTE-BAJO-A", "cantidad": 50, "fecha_vencimiento": "2027-01-01", "precio": 1000
    }, headers=auth_headers)
    client.post(f"/api/pharmacy/medications/inventory/{cod_b}", json={
        "lote": "LOTE-BAJO-B", "cantidad": 10, "fecha_vencimiento": "2027-01-01", "precio": 2000
    }, headers=auth_headers)
    client.post(f"/api/pharmacy/medications/inventory/{cod_b}", json={
        "lote": "LOTE-ALTO", "cantidad": 150, "fecha_vencimiento": "2027-01-01", "precio": 3000
    }, headers=auth_headers)

    # Consultar endpoint de alertas
    response = client.get("/api/pharmacy/medications/low-stock?page=1&limit=10", headers=auth_headers)
    data = response.json()

    assert response.status_code == 200
    assert data["hasElements"] is True
    assert len(data["data"]) == 2

    assert data["data"][0]["cantidad"] == 10
    assert data["data"][0]["lote"] == "LOTE-BAJO-B"
    assert data["data"][1]["cantidad"] == 50
    assert data["data"][1]["lote"] == "LOTE-BAJO-A"
def test_alertas_vencimiento_proximo(auth_headers):
    #Limpieza y preparación
    client.delete("/api/pharmacy/debug/clear-all-data", headers=auth_headers)
    cod_med = 95000
    client.post("/api/pharmacy/medications", json={
        "codigo": cod_med, "nombre_medicamento": "Med_Vencimiento",
        "reg_invima": 123, "principio_activo": "Test", "presentacion": "Tab"
    }, headers=auth_headers)

    hoy = datetime.now().date()

    # Definir fechas
    fecha_cerca = (hoy + timedelta(days=5)).isoformat()
    fecha_limite = (hoy + timedelta(days=30)).isoformat()
    fecha_lejos = (hoy + timedelta(days=60)).isoformat()
    fecha_vencida = (hoy - timedelta(days=1)).isoformat()

    # Cargar lotes
    # Lote A (Cerca)
    client.post(f"/api/pharmacy/medications/inventory/{cod_med}", json={
        "lote": "LOTE-5-DIAS", "cantidad": 100, "fecha_vencimiento": fecha_cerca, "precio": 10
    }, headers=auth_headers)
    # Lote B (Límite)
    client.post(f"/api/pharmacy/medications/inventory/{cod_med}", json={
        "lote": "LOTE-30-DIAS", "cantidad": 100, "fecha_vencimiento": fecha_limite, "precio": 10
    }, headers=auth_headers)
    # Lote C (Fuera de rango futuro)
    client.post(f"/api/pharmacy/medications/inventory/{cod_med}", json={
        "lote": "LOTE-SEGURO", "cantidad": 100, "fecha_vencimiento": fecha_lejos, "precio": 10
    }, headers=auth_headers)
    # Lote D (Ya vencido)
    client.post(f"/api/pharmacy/medications/inventory/{cod_med}", json={
        "lote": "LOTE-VENCIDO", "cantidad": 100, "fecha_vencimiento": fecha_vencida, "precio": 10
    }, headers=auth_headers)

    # Consultar endpoint
    response = client.get("/api/pharmacy/medications/expiring-soon?page=1&limit=10", headers=auth_headers)
    data = response.json()

    assert response.status_code == 200
    assert data["hasElements"] is True
    # Solo deben aparecer los 2 que están entre hoy y +30 días
    assert len(data["data"]) == 2
    lotes_nombres = [item["lote"] for item in data["data"]]
    assert lotes_nombres == ["LOTE-5-DIAS", "LOTE-30-DIAS"] #Orden

    # Asegurarse de que el lote de 60 días y el vencido no se colaron
    assert "LOTE-SEGURO" not in lotes_nombres
    assert "LOTE-VENCIDO" not in lotes_nombres
def test_actualizar_medicamento_exitoso(auth_headers):
    # Crear medicamento inicial
    codigo_update = 44000
    client.post("/api/pharmacy/medications", json={
        "codigo": codigo_update,
        "nombre_medicamento": "Nombre Original",
        "reg_invima": 111,
        "principio_activo": "P1",
        "presentacion": "Tableta"
    }, headers=auth_headers)

    # Enviar actualización
    payload_update = {
        "codigo": codigo_update, # El código se mantiene
        "nombre_medicamento": "Nombre Actualizado",
        "reg_invima": 222,
        "principio_activo": "P1-Modificado",
        "presentacion": "Jarabe"
    }

    response = client.put(f"/api/pharmacy/medications/{codigo_update}", json=payload_update, headers=auth_headers)
    data = response.json()

    assert response.status_code == 200
    assert data["hasError"] is False
    assert data["Data"]["nombre_medicamento"] == "Nombre Actualizado"
    assert data["Data"]["presentacion"] == "Jarabe"
def test_actualizar_lote_inventario_exitoso(auth_headers):
    cod_med = 66000
    client.post("/api/pharmacy/medications", json={
        "codigo": cod_med, "nombre_medicamento": "Med_Update_Lote",
        "reg_invima": 1, "principio_activo": "P", "presentacion": "T"
    }, headers=auth_headers)

    res_creacion = client.post(f"/api/pharmacy/medications/inventory/{cod_med}", json={
        "lote": "LOTE-ORIGINAL",
        "cantidad": 100,
        "fecha_vencimiento": "2027-01-01",
        "precio": 5000
    }, headers=auth_headers)

    # Extraemos el ID autogenerado que nos devuelve la API
    id_generado = res_creacion.json()["Data"]["id_inventario"]

    # Enviar actualización usando ID
    payload_update = {
        "lote": "LOTE-CORREGIDO",
        "cantidad": 150, # Aumentamos stock
        "fecha_vencimiento": "2028-01-01",
        "precio": 5500
    }

    response = client.put(f"/api/pharmacy/medications/inventory/{id_generado}", json=payload_update, headers=auth_headers)
    json_response = response.json()

    # Validaciones
    assert response.status_code == 200
    assert json_response["hasError"] is False
    assert json_response["Data"]["lote"] == "LOTE-CORREGIDO"
    assert json_response["Data"]["cantidad"] == 150
    assert json_response["Data"]["id_inventario"] == id_generado
def test_bloqueo_edicion_lote_vencido(auth_headers):
    cod_med = 99000
    client.post("/api/pharmacy/medications", json={
        "codigo": cod_med,
        "nombre_medicamento": "Med_Para_Bloqueo",
        "reg_invima": 123,
        "principio_activo": "Test",
        "presentacion": "Tab"
    }, headers=auth_headers)

    fecha_vencida = (datetime.now() - timedelta(days=5)).date().isoformat()

    res_creacion = client.post(f"/api/pharmacy/medications/inventory/{cod_med}", json={
        "lote": "LOTE-EXPIRADO",
        "cantidad": 100,
        "fecha_vencimiento": fecha_vencida,
        "precio": 1000
    }, headers=auth_headers)

    id_inventario = res_creacion.json()["Data"]["id_inventario"]


    payload_update = {
        "lote": "LOTE-INTENTO-CAMBIO",
        "cantidad": 500,
        "fecha_vencimiento": "2028-01-01", # Intentamos una fecha
        "precio": 2000
    }

    response = client.put(f"/api/pharmacy/medications/inventory/{id_inventario}", json=payload_update, headers=auth_headers)
    json_response = response.json()


    assert json_response["hasError"] is True
    assert "no es posible editar" in json_response["Message"].lower()
    assert "vencido" in json_response["Message"].lower()

    assert json_response["Data"]["lote"] == "LOTE-EXPIRADO"
    assert json_response["Data"]["cantidad"] == 100