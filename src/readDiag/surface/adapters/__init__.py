"""
Adapters package (moderno):
- AccessAdapter: ponte para diagAccess moderno (readDiag.surface.access_adapter)
- LegacyCompatAdapter: compat para objetos legados usados em testes
"""
from ..access_adapter import AccessAdapter  # módulo correto
from .legacy import LegacyCompatAdapter

__all__ = ["AccessAdapter", "LegacyCompatAdapter"]
