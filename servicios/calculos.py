"""Legacy compatibility stub.

Este módulo fue reemplazado por las vistas de Supabase y ya no se usa en la app.
Se conserva en el repositorio solo como referencia histórica.
"""

from __future__ import annotations

import warnings

warnings.warn(
    "servicios.calculos.py está obsoleto. La lógica de cálculo ahora se obtiene desde las vistas de Supabase.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = []
