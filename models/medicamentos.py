from sqlalchemy import Column, Integer, String, Date, ForeignKey
from sqlalchemy.orm import relationship
from db.session import Base

class MEDICAMENTOS(Base):
    __tablename__ = "medicamentos"
    codigo = Column(Integer, primary_key=True, index=True) # PK
    nombre_medicamento = Column(String(50), nullable=False)
    reg_invima = Column(Integer)
    principio_activo = Column(String(50))
    presentacion = Column(String(50))

    #Relaciones
    lotes_inventario = relationship("INVENTARIO", back_populates="medicamento")

class INVENTARIO(Base):
    __tablename__ = "inventario"

    id_inventario = Column(Integer, primary_key=True, index=True,autoincrement=True) #PK
    lote = Column(String(50))
    cantidad = Column(Integer)
    fecha_vencimiento = Column(Date)
    precio = Column(Integer)
    codigo_medicamento = Column(Integer, ForeignKey("medicamentos.codigo")) # FK

    #Relaciones
    medicamento = relationship("MEDICAMENTOS", back_populates="lotes_inventario")