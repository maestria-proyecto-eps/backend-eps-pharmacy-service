from sqlalchemy import Column, Integer, String, BigInteger, ForeignKey, Boolean, TIMESTAMP, SmallInteger
from sqlalchemy.orm import relationship
from db.session import BaseAdmin

class USUARIOS(BaseAdmin):
    __tablename__ = "usuarios"
    id_usuario = Column(Integer, primary_key=True, autoincrement=True) #PK
    password = Column(String(60), nullable=False)
    id_rol = Column(Integer, ForeignKey("roles.id_rol"), nullable=False) #FK
    estado = Column(Boolean, default=True)
    intentos_login = Column(SmallInteger, default=0)
    tiempo_de_fallo_login = Column(TIMESTAMP, nullable=True)
    num_documento = Column(BigInteger, ForeignKey("persona.num_documento"), nullable=False) #FK

    # Relaciones
    rol = relationship("ROLES")

class ROLES(BaseAdmin):
    __tablename__ = "roles"
    id_rol = Column(Integer, primary_key=True, index=True) #PK
    nombre_rol = Column(String(50), nullable=False, unique=True)