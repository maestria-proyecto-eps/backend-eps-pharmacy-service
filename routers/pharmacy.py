from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import text
import math
from typing import List
from db.session import get_db
from models.medicamentos import MEDICAMENTOS, INVENTARIO
from schemas.pharmacy import GenericResponse,  PaginatedResponse, APIResponse
from schemas.pharmacy import MedicationCreate, MedicationWithBatchesRead, MedicationRead, MedicationRead2
from schemas.pharmacy import InventoryWithMedicationRead,InventoryWithMedicationRead2,InventoryBatchCreate,InventoryDetail
from datetime import datetime, timedelta

from core.dependencias import RequireRole
from models.user import USUARIOS

router = APIRouter(prefix="/api/pharmacy", tags=["Pharmacy"],dependencies = [Depends(RequireRole(["Farmaceuta"]))])

@router.post("/medications", status_code=201, response_model=GenericResponse[MedicationWithBatchesRead])
def create_medication(med: MedicationCreate, db: Session = Depends(get_db)):

    by_codigo = db.query(MEDICAMENTOS).options(joinedload(MEDICAMENTOS.lotes_inventario)) \
        .filter(MEDICAMENTOS.codigo == med.codigo).first()

    # Verificar existencia
    if by_codigo:
        return {
            "hasError": False,
            "Message": f"El código '{med.codigo}' ya está asignado al medicamento: {by_codigo.nombre_medicamento} ({by_codigo.presentacion}).",
            "Data": by_codigo
        }
    by_nombre_pres = db.query(MEDICAMENTOS).options(joinedload(MEDICAMENTOS.lotes_inventario)) \
        .filter(
        MEDICAMENTOS.nombre_medicamento == med.nombre_medicamento,
        MEDICAMENTOS.presentacion == med.presentacion
    ).first()
    if by_nombre_pres:
        return {
            "hasError": False,
            "Message": f"Ya existe el medicamento '{med.nombre_medicamento}' en la presentación '{med.presentacion}' (Código: {by_nombre_pres.codigo}).",
            "Data": by_nombre_pres
        }

    # Si no existe por se crea el nuevo registro
    new_med = MEDICAMENTOS(
        codigo=med.codigo,
        nombre_medicamento=med.nombre_medicamento,
        reg_invima=med.reg_invima,
        principio_activo=med.principio_activo,
        presentacion=med.presentacion
    )

    db.add(new_med)
    db.commit()
    db.refresh(new_med)

    return {
        "hasError": False,
        "Message": "Medicamento creado exitosamente.",
        "Data": new_med
    }

@router.post("/medications/inventory/{codigo_medicamento}", status_code=201, response_model=GenericResponse[InventoryWithMedicationRead])
def create_inventory_batch(codigo_medicamento: int, batch: InventoryBatchCreate, db: Session = Depends(get_db)):
    # Verificar si el medicamento existe
    parent_med = db.query(MEDICAMENTOS).filter(MEDICAMENTOS.codigo == codigo_medicamento).first()
    if not parent_med:
        return {
            "hasError": True,
            "Message": f"No se puede agregar el lote. El medicamento con código {codigo_medicamento} no existe.",
            "Data": None
        }

    # Verificar si el número de lote ya existe para este medicamento
    existing_batch = db.query(INVENTARIO).options(joinedload(INVENTARIO.medicamento)) \
        .filter(INVENTARIO.lote == batch.lote,
                INVENTARIO.codigo_medicamento == codigo_medicamento).first()

    if existing_batch:
        return {
            "hasError": True,
            "Message": f"El lote '{batch.lote}' ya existe para este medicamento.",
            "Data": existing_batch
        }

    # Crear el nuevo lote
    new_batch = INVENTARIO(
        lote=batch.lote,
        cantidad=batch.cantidad,
        fecha_vencimiento=batch.fecha_vencimiento,
        precio=batch.precio,
        codigo_medicamento=codigo_medicamento
    )

    db.add(new_batch)
    db.commit()
    db.refresh(new_batch)

    return {
        "hasError": False,
        "Message": f"Lote '{batch.lote}' registrado exitosamente para el medicamento {parent_med.nombre_medicamento}.",
        "Data": new_batch
    }

@router.get("/medications", response_model=PaginatedResponse[MedicationRead])
def list_medications(page: int = 1, limit: int = 10, db: Session = Depends(get_db)):
    if page < 1: page = 1
    skip = (page - 1) * limit
    query = db.query(MEDICAMENTOS)
    total_count = query.count()
    items = query.order_by(MEDICAMENTOS.nombre_medicamento.asc()) \
        .offset(skip) \
        .limit(limit) \
        .all()
    total_pages = math.ceil(total_count / limit) if total_count > 0 else 0

    return {
        "hasElements": len(items) > 0,
        "pages": total_pages,
        "page": page,
        "data": items
    }

@router.get("/medications/inventory/{codigo_medicamento}", response_model=PaginatedResponse[InventoryDetail])
def list_inventory_by_medication(codigo_medicamento: int,page: int = 1,limit: int = 10,db: Session = Depends(get_db)):
    if page < 1: page = 1
    skip = (page - 1) * limit

    # Consulta por el medicamento
    query = db.query(INVENTARIO).filter(INVENTARIO.codigo_medicamento == codigo_medicamento)

    total_count = query.count()

    # Verificación de existencia de datos
    if total_count == 0:
        return {
            "hasElements": False,
            "pages": 0,
            "page": page,
            "data": [],
            "Message": "Medicamento sin registrar o sin lotes asignados"
        }

    # Obtención de datos paginados
    items = query.order_by(INVENTARIO.fecha_vencimiento.asc()) \
        .offset(skip) \
        .limit(limit) \
        .all()

    total_pages = math.ceil(total_count / limit)

    return {
        "hasElements": True,
        "pages": total_pages,
        "page": page,
        "data": items
    }

@router.get("/medications/low-stock", response_model=PaginatedResponse[InventoryWithMedicationRead])
def get_low_stock_alerts(page: int = 1, limit: int = 10, db: Session = Depends(get_db)):
    # Umbral de alerta
    THRESHOLD = 100

    query = db.query(INVENTARIO).filter(INVENTARIO.cantidad < THRESHOLD)

    # Paginación
    total_count = query.count()
    if page < 1: page = 1
    skip = (page - 1) * limit

    # Obtenemos los lotes que cumplen la condición
    items = query.order_by(INVENTARIO.cantidad.asc()) \
        .offset(skip) \
        .limit(limit) \
        .all()

    total_pages = math.ceil(total_count / limit) if total_count > 0 else 0

    return {
        "hasElements": len(items) > 0,
        "pages": total_pages,
        "page": page,
        "data": items
    }

@router.get("/medications/expiring-soon", response_model=PaginatedResponse[InventoryWithMedicationRead])
def get_expiring_soon_alerts(page: int = 1, limit: int = 10, db: Session = Depends(get_db)):
    # Rango de fechas
    hoy = datetime.now().date()
    fecha_limite = hoy + timedelta(days=30)


    # Fecha de vencimiento esté entre hoy y los próximos 30 días
    query = db.query(INVENTARIO).filter(
        INVENTARIO.fecha_vencimiento >= hoy,
        INVENTARIO.fecha_vencimiento <= fecha_limite
    )

    # Paginación
    total_count = query.count()
    skip = (page - 1) * limit

    items = query.order_by(INVENTARIO.fecha_vencimiento.asc()) \
        .offset(skip) \
        .limit(limit) \
        .all()

    total_pages = math.ceil(total_count / limit) if total_count > 0 else 0

    return {
        "hasElements": len(items) > 0,
        "pages": total_pages,
        "page": page,
        "data": items
    }

@router.put("/medications/{codigo}", response_model=APIResponse[MedicationRead])
def update_medication(codigo: int,payload: MedicationRead2,db: Session = Depends(get_db)):
    # Buscar el medicamento existente
    med_db = db.query(MEDICAMENTOS).filter(MEDICAMENTOS.codigo == codigo).first()

    if not med_db:
        return {
            "hasError": True,
            "Message": f"No se encontró el medicamento con código '{codigo}'.",
            "Data": None
        }

    # Actualizar datos
    med_db.nombre_medicamento = payload.nombre_medicamento
    med_db.reg_invima = payload.reg_invima
    med_db.principio_activo = payload.principio_activo
    med_db.presentacion = payload.presentacion

    try:
        db.commit()
        db.refresh(med_db)
        return {
            "hasError": False,
            "Message": "Medicamento actualizado exitosamente.",
            "Data": med_db
        }
    except Exception as e:
        db.rollback()
        return {
            "hasError": True,
            "Message": f"Error al actualizar: {str(e)}",
            "Data": None
        }

@router.put("/medications/inventory/{id_inventario}", response_model=APIResponse[InventoryWithMedicationRead])
def update_inventory_batch(id_inventario: int,payload: InventoryBatchCreate,db: Session = Depends(get_db)):

    batch_db = db.query(INVENTARIO).filter(INVENTARIO.id_inventario == id_inventario).first()

    if not batch_db:
        return {
            "hasError": True,
            "Message": f"No se encontró el lote con ID {id_inventario}.",
            "Data": None
        }
    hoy = datetime.now().date()
    if batch_db.fecha_vencimiento < hoy:
        return {
            "hasError": True,
            "Message": "No es posible editar este lote porque el medicamento ya se encuentra vencido.",
            "Data": batch_db
        }
    # Actualizar solo los campos del lote
    batch_db.lote = payload.lote
    batch_db.cantidad = payload.cantidad
    batch_db.fecha_vencimiento = payload.fecha_vencimiento
    batch_db.precio = payload.precio

    try:
        db.commit()
        db.refresh(batch_db)
        return {
            "hasError": False,
            "Message": "Lote de inventario actualizado exitosamente.",
            "Data": batch_db
        }
    except Exception as e:
        db.rollback()
        return {
            "hasError": True,
            "Message": f"Error al actualizar el lote: {str(e)}",
            "Data": None
        }

@router.delete("/debug/clear-all-data")
def clear_database_data(db: Session = Depends(get_db)):
    try:
        # Ejecutamos el truncate directamente
        db.execute(text("TRUNCATE TABLE inventario, medicamentos RESTART IDENTITY CASCADE;"))
        db.commit()
        return {"hasError": False, "Message": "Todas las tablas han sido vaciadas y los contadores reiniciados."}
    except Exception as e:
        db.rollback()
        return {"hasError": True, "Message": f"Error al limpiar tablas: {str(e)}"}