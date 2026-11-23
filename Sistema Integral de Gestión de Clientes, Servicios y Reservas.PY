from __future__ import annotations

import logging
import re
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional, overload


# =====================================================================
# 1. CONFIGURACIÓN DE LOGS Y EXCEPCIONES PERSONALIZADAS
# =====================================================================

def configurar_logger(ruta_log: str = "software_fj.log") -> logging.Logger:
    logger = logging.getLogger("SoftwareFJ")
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        formato = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        archivo_handler = logging.FileHandler(ruta_log, mode="a", encoding="utf-8")
        archivo_handler.setFormatter(formato)
        logger.addHandler(archivo_handler)

        consola_handler = logging.StreamHandler()
        consola_handler.setFormatter(formato)
        logger.addHandler(consola_handler)

    return logger


logger = configurar_logger()


class ErrorSoftwareFJ(Exception):
    """Excepción base del dominio de Software FJ."""


class ErrorValidacion(ErrorSoftwareFJ):
    """Datos inválidos, vacíos o fuera de rango."""


class ErrorDisponibilidad(ErrorSoftwareFJ):
    """El servicio no está disponible o no soporta la operación."""


class ErrorOperacion(ErrorSoftwareFJ):
    """Transición de estado o acción no permitida."""


class ErrorCalculo(ErrorSoftwareFJ):
    """Inconsistencias matemáticas o parámetros inválidos de cálculo."""


# =====================================================================
# 2. ENTIDAD ABSTRACTA Y CLIENTE (ENCAPSULACIÓN Y VALIDACIONES)
# =====================================================================

class EntidadSistema(ABC):
    """Clase abstracta base para entidades gestionadas en memoria."""

    def __init__(self, id_entidad: str) -> None:
        if not isinstance(id_entidad, str) or not id_entidad.strip():
            raise ErrorValidacion("El ID de la entidad debe ser un texto no vacío.")
        self._id: str = id_entidad.strip().upper()
        self._fecha_creacion: datetime = datetime.now()

    @property
    def id(self) -> str:
        return self._id

    @property
    def fecha_creacion(self) -> datetime:
        return self._fecha_creacion

    @abstractmethod
    def resumen(self) -> str:
        """Retorna una representación resumida de la entidad."""


class Cliente(EntidadSistema):
    """Representa un cliente con datos personales encapsulados y validados."""

    _EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

    def __init__(self, id_cliente: str, nombre: str, correo: str, telefono: str) -> None:
        super().__init__(id_cliente)
        self.nombre = nombre
        self.correo = correo
        self.telefono = telefono

    @property
    def nombre(self) -> str:
        return self._nombre

    @nombre.setter
    def nombre(self, valor: str) -> None:
        if not isinstance(valor, str) or len(valor.strip()) < 3:
            raise ErrorValidacion("El nombre del cliente debe tener al menos 3 caracteres.")
        self._nombre = valor.strip()

    @property
    def correo(self) -> str:
        return self._correo

    @correo.setter
    def correo(self, valor: str) -> None:
        if not isinstance(valor, str) or not self._EMAIL_REGEX.match(valor.strip()):
            raise ErrorValidacion(f"Correo electrónico inválido: '{valor}'.")
        self._correo = valor.strip().lower()

    @property
    def telefono(self) -> str:
        return self._telefono

    @telefono.setter
    def telefono(self, valor: str) -> None:
        limpio = re.sub(r"[\s\-()]", "", valor) if isinstance(valor, str) else ""
        if not limpio.isdigit() or not (7 <= len(limpio) <= 15):
            raise ErrorValidacion(f"Teléfono inválido: '{valor}'. Debe tener entre 7 y 15 dígitos.")
        self._telefono = limpio

    def resumen(self) -> str:
        return f"Cliente[{self.id}] {self.nombre} | {self.correo} | Tel: {self.telefono}"


# =====================================================================
# 3. JERARQUÍA DE SERVICIOS Y SOBRECARGA DE CÁLCULO DE COSTOS
# =====================================================================

class Servicio(EntidadSistema, ABC):
    """Clase abstracta para servicios ofertados por Software FJ."""

    def __init__(
        self,
        codigo: str,
        nombre: str,
        tarifa_base: float,
        disponible: bool = True,
    ) -> None:
        super().__init__(codigo)
        if not isinstance(nombre, str) or not nombre.strip():
            raise ErrorValidacion("El nombre del servicio no puede estar vacío.")
        if not isinstance(tarifa_base, (int, float)) or tarifa_base <= 0:
            raise ErrorCalculo("La tarifa base debe ser un número mayor que 0.")

        self._nombre: str = nombre.strip()
        self._tarifa_base: float = float(tarifa_base)
        self._disponible: bool = bool(disponible)

    @property
    def nombre(self) -> str:
        return self._nombre

    @property
    def tarifa_base(self) -> float:
        return self._tarifa_base

    @property
    def disponible(self) -> bool:
        return self._disponible

    @disponible.setter
    def disponible(self, estado: bool) -> None:
        self._disponible = bool(estado)

    @abstractmethod
    def validar_parametros(self, duracion_horas: float, extra: Optional[int] = None) -> None:
        """Valida parámetros específicos de duración y cantidad/capacidad."""

    @abstractmethod
    def _subtotal_por_duracion(self, duracion_horas: float, extra: Optional[int] = None) -> float:
        """Calcula el subtotal antes de descuentos e impuestos."""

    @overload
    def calcular_costo(self, duracion_horas: float) -> float: ...

    @overload
    def calcular_costo(
        self,
        duracion_horas: float,
        *,
        descuento_pct: float = 0.0,
        impuesto_pct: float = 0.0,
        extra: Optional[int] = None,
    ) -> float: ...

    def calcular_costo(
        self,
        duracion_horas: float,
        *,
        descuento_pct: float = 0.0,
        impuesto_pct: float = 0.0,
        extra: Optional[int] = None,
    ) -> float:
        """
        Variantes sobrecargadas de cálculo de costo:
        - Solo duración: calcular_costo(horas)
        - Con descuento y/o impuesto: calcular_costo(horas, descuento_pct=10, impuesto_pct=19, extra=...)
        """
        if not isinstance(descuento_pct, (int, float)) or not (0 <= descuento_pct < 100):
            raise ErrorCalculo("El descuento porcentual debe estar entre 0 y < 100.")
        if not isinstance(impuesto_pct, (int, float)) or impuesto_pct < 0:
            raise ErrorCalculo("El impuesto porcentual no puede ser negativo.")

        try:
            subtotal = self._subtotal_por_duracion(duracion_horas, extra=extra)
            con_descuento = subtotal * (1.0 - float(descuento_pct) / 100.0)
            total = con_descuento * (1.0 + float(impuesto_pct) / 100.0)
        except ErrorSoftwareFJ:
            raise
        except Exception as exc:
            raise ErrorCalculo("Error inesperado al calcular el costo del servicio.") from exc

        if total <= 0:
            raise ErrorCalculo("El costo total calculado es inconsistente (<= 0).")
        return round(total, 2)

    @abstractmethod
    def describir(self) -> str:
        """Descripción detallada del servicio."""

    def resumen(self) -> str:
        estado = "Disponible" if self._disponible else "No disponible"
        return f"Servicio[{self.id}] {self.nombre} (${self.tarifa_base:.2f}/h) - {estado}"


class ReservaSala(Servicio):
    """Reserva de salas de reuniones o auditorios."""

    def __init__(
        self,
        codigo: str,
        nombre: str,
        tarifa_base: float,
        capacidad_maxima: int,
        disponible: bool = True,
    ) -> None:
        super().__init__(codigo, nombre, tarifa_base, disponible)
        if not isinstance(capacidad_maxima, int) or capacidad_maxima <= 0:
            raise ErrorValidacion("La capacidad máxima de la sala debe ser un entero positivo.")
        self._capacidad_maxima = capacidad_maxima

    def validar_parametros(self, duracion_horas: float, extra: Optional[int] = None) -> None:
        if not isinstance(duracion_horas, (int, float)) or duracion_horas < 1 or duracion_horas > 12:
            raise ErrorValidacion("La reserva de sala debe durar entre 1 y 12 horas.")
        if extra is not None:
            if not isinstance(extra, int) or extra <= 0 or extra > self._capacidad_maxima:
                raise ErrorValidacion(
                    f"Asistentes inválidos ({extra}). Capacidad máxima: {self._capacidad_maxima}."
                )

    def _subtotal_por_duracion(self, duracion_horas: float, extra: Optional[int] = None) -> float:
        self.validar_parametros(duracion_horas, extra)
        # Recargo leve del 15% si supera el 75% de la capacidad
        recargo = 1.15 if (extra is not None and extra > self._capacidad_maxima * 0.75) else 1.0
        return self._tarifa_base * float(duracion_horas) * recargo

    def describir(self) -> str:
        return (
            f"Sala '{self.nombre}' (Cap. máx: {self._capacidad_maxima} personas) | "
            f"Tarifa base: ${self.tarifa_base:.2f}/hora"
        )


class AlquilerEquipo(Servicio):
    """Alquiler de equipos tecnológicos (portátiles, proyectores, estaciones)."""

    def __init__(
        self,
        codigo: str,
        nombre: str,
        tarifa_base: float,
        unidades_totales: int,
        disponible: bool = True,
    ) -> None:
        super().__init__(codigo, nombre, tarifa_base, disponible)
        if not isinstance(unidades_totales, int) or unidades_totales <= 0:
            raise ErrorValidacion("Las unidades totales deben ser un entero positivo.")
        self._unidades_totales = unidades_totales

    def validar_parametros(self, duracion_horas: float, extra: Optional[int] = None) -> None:
        if not isinstance(duracion_horas, (int, float)) or duracion_horas < 2 or duracion_horas > 72:
            raise ErrorValidacion("El alquiler de equipo debe ser entre 2 y 72 horas.")
        unidades = 1 if extra is None else extra
        if not isinstance(unidades, int) or unidades <= 0 or unidades > self._unidades_totales:
            raise ErrorValidacion(
                f"Cantidad de equipos inválida ({unidades}). Disponibles en stock: {self._unidades_totales}."
            )

    def _subtotal_por_duracion(self, duracion_horas: float, extra: Optional[int] = None) -> float:
        self.validar_parametros(duracion_horas, extra)
        unidades = 1 if extra is None else extra
        return self._tarifa_base * float(duracion_horas) * unidades

    def describir(self) -> str:
        return (
            f"Equipo '{self.nombre}' (Stock: {self._unidades_totales} uds.) | "
            f"Tarifa base: ${self.tarifa_base:.2f}/hora por unidad"
        )


class AsesoriaEspecializada(Servicio):
    """Asesorías técnicas o arquitectónicas con expertos de Software FJ."""

    def __init__(
        self,
        codigo: str,
        nombre: str,
        tarifa_base: float,
        especialidad: str,
        disponible: bool = True,
    ) -> None:
        super().__init__(codigo, nombre, tarifa_base, disponible)
        if not isinstance(especialidad, str) or not especialidad.strip():
            raise ErrorValidacion("La especialidad de la asesoría es obligatoria.")
        self._especialidad = especialidad.strip()

    def validar_parametros(self, duracion_horas: float, extra: Optional[int] = None) -> None:
        if not isinstance(duracion_horas, (int, float)) or duracion_horas < 1 or duracion_horas > 8:
            raise ErrorValidacion("Una sesión de asesoría debe durar entre 1 y 8 horas.")
        if extra is not None:
            if not isinstance(extra, int) or extra < 1 or extra > 5:
                raise ErrorValidacion("El número de consultores asignados debe estar entre 1 y 5.")

    def _subtotal_por_duracion(self, duracion_horas: float, extra: Optional[int] = None) -> float:
        self.validar_parametros(duracion_horas, extra)
        consultores = 1 if extra is None else extra
        return self._tarifa_base * float(duracion_horas) * consultores

    def describir(self) -> str:
        return (
            f"Asesoría '{self.nombre}' [{self._especialidad}] | "
            f"Tarifa base: ${self.tarifa_base:.2f}/hora por consultor"
        )


# =====================================================================
# 4. RESERVA Y GESTOR EN MEMORIA
# =====================================================================

class Reserva(EntidadSistema):
    """Integra cliente, servicio, duración, costo y ciclo de vida de estado."""

    ESTADOS_VALIDOS = {"PENDIENTE", "CONFIRMADA", "CANCELADA", "PROCESADA"}

    def __init__(
        self,
        id_reserva: str,
        cliente: Cliente,
        servicio: Servicio,
        duracion_horas: float,
        *,
        extra: Optional[int] = None,
        descuento_pct: float = 0.0,
        impuesto_pct: float = 0.0,
    ) -> None:
        super().__init__(id_reserva)
        if not isinstance(cliente, Cliente):
            raise ErrorValidacion("Debe proporcionar una instancia válida de Cliente.")
        if not isinstance(servicio, Servicio):
            raise ErrorValidacion("Debe proporcionar una instancia válida de Servicio.")
        if not servicio.disponible:
            raise ErrorDisponibilidad(f"El servicio '{servicio.nombre}' no está disponible.")

        try:
            servicio.validar_parametros(duracion_horas, extra=extra)
            costo_total = servicio.calcular_costo(
                duracion_horas,
                descuento_pct=descuento_pct,
                impuesto_pct=impuesto_pct,
                extra=extra,
            )
        except ErrorSoftwareFJ as exc:
            raise ErrorOperacion(f"No se pudo crear la reserva {self.id}: {exc}") from exc

        self._cliente = cliente
        self._servicio = servicio
        self._duracion_horas = float(duracion_horas)
        self._extra = extra
        self._costo_total = costo_total
        self._estado = "PENDIENTE"

    @property
    def estado(self) -> str:
        return self._estado

    @property
    def costo_total(self) -> float:
        return self._costo_total

    def confirmar(self) -> None:
        if self._estado == "CANCELADA":
            raise ErrorOperacion(f"La reserva {self.id} está cancelada y no puede confirmarse.")
        if self._estado == "PROCESADA":
            raise ErrorOperacion(f"La reserva {self.id} ya fue procesada.")
        self._estado = "CONFIRMADA"
        logger.info("Reserva %s confirmada para cliente %s.", self.id, self._cliente.id)

    def cancelar(self, motivo: str = "Cancelación solicitada") -> None:
        if self._estado == "PROCESADA":
            raise ErrorOperacion(f"No se puede cancelar la reserva {self.id} porque ya fue procesada.")
        if self._estado == "CANCELADA":
            raise ErrorOperacion(f"La reserva {self.id} ya se encuentra cancelada.")
        self._estado = "CANCELADA"
        logger.warning("Reserva %s cancelada (%s).", self.id, motivo)

    def procesar(self, auto_confirmar: bool = False) -> float:
        """Procesa la reserva y retorna el monto final facturado."""
        if self._estado == "CANCELADA":
            raise ErrorOperacion(f"No se puede procesar una reserva cancelada ({self.id}).")
        if self._estado == "PROCESADA":
            raise ErrorOperacion(f"La reserva {self.id} ya fue procesada previamente.")

        if self._estado == "PENDIENTE":
            if auto_confirmar:
                self.confirmar()
            else:
                raise ErrorOperacion(
                    f"La reserva {self.id} está PENDIENTE. Confírmela antes de procesarla."
                )

        self._estado = "PROCESADA"
        logger.info(
            "Reserva %s procesada | Cliente: %s | Servicio: %s | Total: $%.2f",
            self.id,
            self._cliente.id,
            self._servicio.id,
            self._costo_total,
        )
        return self._costo_total

    def resumen(self) -> str:
        return (
            f"Reserva[{self.id}] Estado={self._estado} | Cliente={self._cliente.nombre} | "
            f"Servicio={self._servicio.nombre} ({self._duracion_horas}h) | Total=${self._costo_total:.2f}"
        )


class GestorSoftwareFJ:
    """Administra clientes, servicios y reservas en memoria sin base de datos."""

    def __init__(self) -> None:
        self.clientes: list[Cliente] = []
        self.servicios: list[Servicio] = []
        self.reservas: list[Reserva] = []

    def registrar_cliente(self, cliente: Cliente) -> Cliente:
        if any(c.id == cliente.id for c in self.clientes):
            raise ErrorOperacion(f"Ya existe un cliente registrado con ID '{cliente.id}'.")
        if any(c.correo == cliente.correo for c in self.clientes):
            raise ErrorOperacion(f"El correo '{cliente.correo}' ya está registrado.")
        self.clientes.append(cliente)
        logger.info("Cliente registrado: %s", cliente.resumen())
        return cliente

    def registrar_servicio(self, servicio: Servicio) -> Servicio:
        if any(s.id == servicio.id for s in self.servicios):
            raise ErrorOperacion(f"Ya existe un servicio con código '{servicio.id}'.")
        self.servicios.append(servicio)
        logger.info("Servicio registrado: %s", servicio.resumen())
        return servicio

    def crear_reserva(self, reserva: Reserva) -> Reserva:
        if any(r.id == reserva.id for r in self.reservas):
            raise ErrorOperacion(f"Ya existe una reserva con ID '{reserva.id}'.")
        self.reservas.append(reserva)
        logger.info("Reserva creada: %s", reserva.resumen())
        return reserva

    def buscar_cliente(self, id_cliente: str) -> Cliente:
        for cliente in self.clientes:
            if cliente.id == id_cliente.strip().upper():
                return cliente
        raise ErrorValidacion(f"Cliente con ID '{id_cliente}' no encontrado.")

    def buscar_servicio(self, id_servicio: str) -> Servicio:
        for servicio in self.servicios:
            if servicio.id == id_servicio.strip().upper():
                return servicio
        raise ErrorValidacion(f"Servicio con ID '{id_servicio}' no encontrado.")

    def buscar_reserva(self, id_reserva: str) -> Reserva:
        for reserva in self.reservas:
            if reserva.id == id_reserva.strip().upper():
                return reserva
        raise ErrorValidacion(f"Reserva con ID '{id_reserva}' no encontrada.")


# =====================================================================
# 5. SIMULACIÓN DE OPERACIONES (VÁLIDAS Y CON ERRORES CONTROLADOS)
# =====================================================================

def ejecutar_operacion(indice: int, descripcion: str, accion) -> None:
    print(f"\n--- Operación #{indice}: {descripcion} ---")
    operacion_exitosa = False
    try:
        resultado = accion()
    except ErrorSoftwareFJ as exc:
        logger.error("Op #%d fallida [%s]: %s", indice, type(exc).__name__, exc)
        print(f"Error controlado ({type(exc).__name__}): {exc}")
    except Exception as exc:
        logger.exception("Op #%d error no esperado: %s", indice, exc)
        print(f"Error inesperado: {exc}")
    else:
        operacion_exitosa = True
        print(f"Éxito: {resultado}")
    finally:
        estado_op = "COMPLETADA" if operacion_exitosa else "RECHAZADA/REGISTRADA EN LOG"
        logger.info("Fin Op #%d (%s) -> %s", indice, descripcion, estado_op)


def simular_sistema() -> None:
    gestor = GestorSoftwareFJ()
    logger.info("=== INICIO SIMULACIÓN SOFTWARE FJ ===")

    # Op 1: Registro válido de cliente 1
    ejecutar_operacion(
        1,
        "Registrar cliente válido (Ana Torres)",
        lambda: gestor.registrar_cliente(
            Cliente("CLI-01", "Ana Torres", "ana.torres@empresa.com", "3001234567")
        ).resumen(),
    )

    # Op 2: Registro inválido de cliente (correo y teléfono incorrectos)
    ejecutar_operacion(
        2,
        "Registrar cliente con datos inválidos",
        lambda: gestor.registrar_cliente(
            Cliente("CLI-02", "Lu", "correo_sin_arroba", "abc")
        ).resumen(),
    )

    # Op 3: Registro válido de cliente 2
    ejecutar_operacion(
        3,
        "Registrar cliente válido (Carlos Ruiz)",
        lambda: gestor.registrar_cliente(
            Cliente("CLI-03", "Carlos Ruiz", "cruiz@corporativo.co", "3119876543")
        ).resumen(),
    )

    # Op 4: Creación válida de 3 servicios (Sala, Equipo, Asesoría)
    def crear_servicios_base() -> str:
        s1 = gestor.registrar_servicio(ReservaSala("SAL-01", "Sala Innovación", 45.0, capacidad_maxima=12))
        s2 = gestor.registrar_servicio(AlquilerEquipo("EQ-01", "Laptop Dev Pro", 15.0, unidades_totales=6))
        s3 = gestor.registrar_servicio(
            AsesoriaEspecializada("ASE-01", "Arquitectura Cloud", 90.0, especialidad="Cloud & DevOps")
        )
        return f"{s1.id}, {s2.id}, {s3.id}"

    ejecutar_operacion(4, "Crear servicios de sala, equipo y asesoría", crear_servicios_base)

    # Op 5: Creación inválida de servicio (tarifa negativa)
    ejecutar_operacion(
        5,
        "Crear servicio con tarifa inválida",
        lambda: gestor.registrar_servicio(
            ReservaSala("SAL-02", "Sala Beta", -20.0, capacidad_maxima=8)
        ).resumen(),
    )

    # Op 6: Reserva válida de sala con sobrecarga de descuento e impuesto
    def crear_y_procesar_reserva_1() -> str:
        cli = gestor.buscar_cliente("CLI-01")
        sal = gestor.buscar_servicio("SAL-01")
        res = Reserva("RES-01", cli, sal, duracion_horas=4, extra=8, descuento_pct=10, impuesto_pct=19)
        gestor.crear_reserva(res)
        res.confirmar()
        total = res.procesar()
        return f"{res.id} procesada por ${total:.2f}"

    ejecutar_operacion(6, "Reserva válida de sala con descuento e impuesto", crear_y_procesar_reserva_1)

    # Op 7: Reserva fallida por exceder capacidad de sala
    def reserva_exceso_capacidad() -> str:
        cli = gestor.buscar_cliente("CLI-03")
        sal = gestor.buscar_servicio("SAL-01")
        res = Reserva("RES-02", cli, sal, duracion_horas=2, extra=25)
        return gestor.crear_reserva(res).resumen()

    ejecutar_operacion(7, "Reserva de sala excediendo capacidad máxima", reserva_exceso_capacidad)

    # Op 8: Reserva válida de alquiler de equipos
    def crear_reserva_equipo() -> str:
        cli = gestor.buscar_cliente("CLI-03")
        eq = gestor.buscar_servicio("EQ-01")
        res = Reserva("RES-03", cli, eq, duracion_horas=6, extra=3, impuesto_pct=19)
        gestor.crear_reserva(res)
        res.confirmar()
        return res.resumen()

    ejecutar_operacion(8, "Reserva válida de alquiler de 3 equipos", crear_reserva_equipo)

    # Op 9: Operación no permitida (procesar reserva sin confirmar)
    def procesar_sin_confirmar() -> str:
        cli = gestor.buscar_cliente("CLI-01")
        ase = gestor.buscar_servicio("ASE-01")
        res = Reserva("RES-04", cli, ase, duracion_horas=2, extra=1)
        gestor.crear_reserva(res)
        res.procesar(auto_confirmar=False)
        return res.resumen()

    ejecutar_operacion(9, "Intentar procesar reserva PENDIENTE sin confirmar", procesar_sin_confirmar)

    # Op 10: Reserva fallida por servicio no disponible
    def reserva_servicio_no_disponible() -> str:
        ase = gestor.buscar_servicio("ASE-01")
        ase.disponible = False
        cli = gestor.buscar_cliente("CLI-03")
        res = Reserva("RES-05", cli, ase, duracion_horas=3)
        return gestor.crear_reserva(res).resumen()

    ejecutar_operacion(10, "Intentar reservar asesoría marcada como no disponible", reserva_servicio_no_disponible)

    # Op 11: Cancelación de reserva confirmada (RES-03)
    def cancelar_reserva_3() -> str:
        res = gestor.buscar_reserva("RES-03")
        res.cancelar("Cambio de cronograma del proyecto")
        return res.resumen()

    ejecutar_operacion(11, "Cancelar reserva confirmada RES-03", cancelar_reserva_3)

    logger.info("=== FIN SIMULACIÓN SOFTWARE FJ ===")
    print("\n=== RESUMEN FINAL EN MEMORIA ===")
    print(f"Clientes registrados: {len(gestor.clientes)}")
    print(f"Servicios registrados: {len(gestor.servicios)}")
    print(f"Reservas registradas: {len(gestor.reservas)}")
    for r in gestor.reservas:
        print("  -", r.resumen())


if __name__ == "__main__":
    simular_sistema()