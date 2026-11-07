"""Registro local de folios y documentos.

Prototipo sin conexión a PostgreSQL. Se almacena un historial de reservas y
registros para no entregar dos veces el mismo folio aunque se cierre la app.
"""
from contextlib import contextmanager
from dataclasses import dataclass, asdict
from datetime import datetime
import json
import os
from pathlib import Path
import re
import time
from typing import ClassVar
from uuid import uuid4


@dataclass
class Documento:
    """Un folio reservado o un documento ya creado."""

    folio: str
    estado: str = "Reservado"          # "Reservado" | "Creado"
    asunto: str = ""
    area_emisora: str = ""
    recepcion: str = ""
    elaboro: str = ""
    reviso: str = ""
    autorizo: str = ""
    reservado_el: str = ""
    creado_el: str = ""

    # Campos que el usuario captura, con el nombre que se muestra en pantalla.
    ETIQUETAS: ClassVar[dict] = {
        "asunto": "Asunto",
        "area_emisora": "Área emisora",
        "recepcion": "Recepción",
        "elaboro": "Quién elaboró",
        "reviso": "Quién revisó",
        "autorizo": "Quién autorizó",
    }

    @property
    def creado(self):
        return self.estado == "Creado"

    @classmethod
    def desde_dict(cls, datos):
        folio = str(datos.get("folio") or datos.get("id") or "")
        estado = datos.get("estado") or (
            "Creado" if folio.startswith("DOC-") else "Reservado"
        )
        # Los registros guardados antes de agregar nuevos campos se leen con "".
        otros = {
            nombre: str(datos.get(nombre) or "")
            for nombre in (*cls.ETIQUETAS, "reservado_el", "creado_el")
        }
        return cls(folio=folio, estado=estado, **otros)

    def a_dict(self):
        # Se conserva la clave "id" para que el archivo siga siendo compatible.
        return {"id": self.folio, **asdict(self)}


class DocumentStore:
    """Lee y escribe el historial de documentos en un archivo JSON local."""

    def __init__(self, ruta=None):
        self.ruta = Path(ruta) if ruta is not None else self.ruta_predeterminada()

    @staticmethod
    def ruta_predeterminada():
        base = Path(os.environ.get("LOCALAPPDATA") or Path.home())
        return base / "GestionInstitucional" / "documentos.json"

    # ---- lectura / escritura --------------------------------------------
    def leer(self):
        if not self.ruta.exists():
            return []
        try:
            datos = json.loads(self.ruta.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            raise ValueError("El historial de documentos está dañado.") from error
        if not isinstance(datos, list) or not all(isinstance(d, dict) for d in datos):
            raise ValueError("El archivo de documentos no tiene un formato válido.")
        return [Documento.desde_dict(d) for d in datos]

    def _escribir(self, documentos):
        self.ruta.parent.mkdir(parents=True, exist_ok=True)
        temporal = self.ruta.with_name(f"{self.ruta.name}.{uuid4().hex}.tmp")
        try:
            contenido = json.dumps(
                [d.a_dict() for d in documentos], ensure_ascii=False, indent=2
            )
            temporal.write_text(contenido, encoding="utf-8")
            temporal.replace(self.ruta)
        finally:
            if temporal.exists():
                temporal.unlink()

    @contextmanager
    def _bloqueo(self):
        """Impide reservas duplicadas si hay dos ventanas de la app abiertas."""
        self.ruta.parent.mkdir(parents=True, exist_ok=True)
        carpeta = self.ruta.with_name(self.ruta.name + ".lock")
        inicio = time.monotonic()
        while True:
            try:
                carpeta.mkdir()
                break
            except FileExistsError:
                # Se permite limpiar un bloqueo abandonado tras un fallo del proceso.
                if carpeta.exists() and time.time() - carpeta.stat().st_mtime > 60:
                    try:
                        carpeta.rmdir()
                    except OSError:
                        pass
                if time.monotonic() - inicio > 5:
                    raise OSError("Otro proceso está usando el historial. Vuelve a intentar.")
                time.sleep(0.05)
        try:
            yield
        finally:
            try:
                carpeta.rmdir()
            except OSError:
                pass

    # ---- operaciones -----------------------------------------------------
    @staticmethod
    def _estructura_folio():
        """Lee la estructura configurable por Administración > Admin 2.
        Si todavía no existe, conserva el formato original CVDR-AÑO-###.
        """
        base = Path(os.environ.get("LOCALAPPDATA") or Path.home())
        ruta = base / "GestionInstitucional" / "administracion.json"
        try:
            datos = json.loads(ruta.read_text(encoding="utf-8"))
            segmentos = datos.get("folio", {}).get("segments", [])
            if segmentos and sum(s.get("type") == "Numero" for s in segmentos) == 1:
                return segmentos
        except (OSError, json.JSONDecodeError, TypeError, AttributeError):
            pass
        return [
            {"type": "Texto", "parameter": "CVDR"},
            {"type": "Texto", "parameter": "AÑO"},
            {"type": "Numero", "parameter": ""},
        ]

    @classmethod
    def _nuevo_folio(cls, documentos, anio):
        segmentos = cls._estructura_folio()

        # El bloque numérico es el consecutivo; los demás son texto.
        patron = []
        partes = []
        for segmento in segmentos:
            if segmento.get("type") == "Numero":
                patron.append(r"(\d+)")
                partes.append(None)
            else:
                valor = str(segmento.get("parameter", "")).strip()
                valor = str(anio) if valor.upper() == "AÑO" else valor
                patron.append(re.escape(valor))
                partes.append(valor)

        regex = re.compile(r"^" + "-".join(patron) + r"$")
        numeros = []
        for documento in documentos:
            match = regex.fullmatch(documento.folio)
            if match:
                numeros.append(int(match.group(1)))

        consecutivo = max(numeros, default=0) + 1
        salida = []
        numero_insertado = False
        for segmento, valor in zip(segmentos, partes):
            if segmento.get("type") == "Numero":
                salida.append(f"{consecutivo:03d}")
                numero_insertado = True
            else:
                salida.append(valor)

        if not numero_insertado:
            # Respaldo de seguridad; Admin 2 no permite guardar una estructura
            # sin bloque numérico.
            return f"CVDR-{anio}-{consecutivo:03d}"
        return "-".join(salida)

    def reservar_folio(self):
        with self._bloqueo():
            documentos = self.leer()
            ahora = datetime.now()
            folio = self._nuevo_folio(documentos, ahora.year)
            documentos.append(Documento(
                folio=folio,
                reservado_el=ahora.isoformat(timespec="seconds"),
            ))
            self._escribir(documentos)
        return folio

    def obtener(self, folio):
        for documento in self.leer():
            if documento.folio == folio:
                return documento
        return None

    def guardar(self, campos, folio=None):
        """Completa una reserva con los `campos` capturados.

        Con folio=None crea un registro nuevo (útil para importar datos antiguos).
        """
        limpios = {nombre: str(campos.get(nombre, "")).strip() for nombre in Documento.ETIQUETAS}
        for nombre, valor in limpios.items():
            if not valor:
                raise ValueError(f"Completa el campo: {Documento.ETIQUETAS[nombre]}")

        with self._bloqueo():
            documentos = self.leer()
            if folio is None:
                folio = self._nuevo_folio(documentos, datetime.now().year)
                documentos.append(Documento(
                    folio=folio,
                    reservado_el=datetime.now().isoformat(timespec="seconds"),
                ))
            for documento in documentos:
                if documento.folio != folio:
                    continue
                if documento.creado:
                    raise ValueError(f"El folio {folio} ya se utilizó para un documento.")
                for nombre, valor in limpios.items():
                    setattr(documento, nombre, valor)
                documento.estado = "Creado"
                documento.creado_el = datetime.now().isoformat(timespec="seconds")
                self._escribir(documentos)
                return documento
        raise ValueError(f"No se encontró la reserva {folio}. Regresa y reserva otro folio.")
