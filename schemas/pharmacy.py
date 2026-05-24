from pydantic import BaseModel, ConfigDict
from datetime import date
from typing import TypeVar, Generic, Optional, List

T = TypeVar("T")

class GenericResponse(BaseModel, Generic[T]):
    hasError: bool
    Message: str
    Data: Optional[T] = None

class PaginatedResponse(BaseModel, Generic[T]):
    hasElements: bool
    pages: int
    page: int
    data: List[T]
    Message: Optional[str] = None

class MedicationCreate(BaseModel):
    codigo: int
    nombre_medicamento: str
    reg_invima: int
    principio_activo: str
    presentacion: str

class InventoryDetail(BaseModel):
    id_inventario: int
    lote: str
    cantidad: int
    fecha_vencimiento: date
    precio: int
    model_config = ConfigDict(from_attributes=True)

class MedicationWithBatchesRead(BaseModel):
    codigo: int
    nombre_medicamento: str
    reg_invima: int
    principio_activo: str
    presentacion: str
    lotes_inventario: List[InventoryDetail]
    model_config = ConfigDict(from_attributes=True)

class InventoryBatchCreate(BaseModel):
    lote: str
    cantidad: int
    fecha_vencimiento: date
    precio: int

class InventoryWithMedicationRead(BaseModel):
    id_inventario: int
    lote: str
    cantidad: int
    fecha_vencimiento: date
    precio: int
    codigo_medicamento: int


    model_config = ConfigDict(from_attributes=True)

class InventoryWithMedicationRead2(BaseModel):
    id_inventario: int
    lote: str
    cantidad: int
    fecha_vencimiento: date
    precio: int
    codigo_medicamento: int
    medicamento: MedicationWithBatchesRead

    model_config = ConfigDict(from_attributes=True)

class MedicationRead(BaseModel):
    codigo: int
    nombre_medicamento: str
    reg_invima: int
    principio_activo: str
    presentacion: str
    model_config = ConfigDict(from_attributes=True)

class MedicationRead2(BaseModel):
    nombre_medicamento: str
    reg_invima: int
    principio_activo: str
    presentacion: str
    model_config = ConfigDict(from_attributes=True)

class InventoryDetail(BaseModel):
    id_inventario: int
    lote: str
    cantidad: int
    fecha_vencimiento: date
    precio: int

    model_config = ConfigDict(from_attributes=True)

class APIResponse(BaseModel, Generic[T]):
    hasError: bool = False
    Message: str = "Todo Ok"
    Data: Optional[T] = None
