from datetime import datetime
from typing import Any, Dict, List
import pandas as pd
import pytest
from readDiag.surface.access_adapter import AccessAdapter


# --- backends falsos mínimos para acionar ramos específicos -----------------

class _NoFileInfoBackend:
    """Sem get_file_info → cai no except do __init__ e levanta RuntimeError."""
    def __init__(self): ...
    
class _BadFileInfoBackend:
    """get_file_info não retorna dict → levanta RuntimeError por tipo inválido."""
    def get_file_info(self):
        return ["not-a-dict"]  # força o TypeError interno e o RuntimeError encadeado


# --- testes que cobrem ramos de erro/guards --------------------------------

def test_init_runtime_error_no_file_info():
    with pytest.raises(RuntimeError):
        AccessAdapter(_NoFileInfoBackend())  # cobre linhas 163-165 (try/except do __init__)

def test_init_runtime_error_bad_file_info_type():
    with pytest.raises(RuntimeError):
        AccessAdapter(_BadFileInfoBackend())  # cobre 175-178 (tipo inválido no file_info)

def test_rad_table_unknown_raises_keyerror(rad_backend_fake):
    a = AccessAdapter(rad_backend_fake)  # usa fixture injetada (sem parênteses)
    with pytest.raises(KeyError):
        a.table("does_not_exist")  # cobre ramo de erro em table()

def test_bring_rad_rejects_extra_args(rad_backend_fake):
    a = AccessAdapter(rad_backend_fake)
    with pytest.raises(TypeError):
        a.bring("obs_df", kx=999)  # em RAD, bring não aceita kx/names

def test_conv_bring_alias_and_order_ok(conv_backend_fake):
    a = AccessAdapter(conv_backend_fake)
    out = a.bring("t", 120, ["qc_flag", "omf"])
    assert list(out.columns) == ["qc_flag", "omf"]
    # não assumimos tamanho fixo; garantimos que trouxe linhas
    assert len(out) >= 1

def test_conv_bring_requires_kx(conv_backend_fake):
    a = AccessAdapter(conv_backend_fake)
    with pytest.raises(TypeError):
        a.bring("t")  # kx obrigatório para conv

def test_conv_kx_list_and_frame_errors(conv_backend_fake):
    a = AccessAdapter(conv_backend_fake)
    with pytest.raises(ValueError):
        a.kx_list("pw")  # var inexistente
    with pytest.raises(KeyError):
        a.frame_conv("t", 121)  # kx inexistente

def test_access_adapter_file_name_property(rad_backend_fake):
    a = AccessAdapter(rad_backend_fake)
    assert a.file_name == "diag_amsua_n15_03.2025010106"
    # escrever no property deve falhar
    with pytest.raises(AttributeError):
        setattr(a, "file_name", "Y")

