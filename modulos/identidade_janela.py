"""Identidade da interface na barra de tarefas do Windows."""

import os
import subprocess


def aplicar_identidade(hwnd):
    from win32com.propsys import propsys, pscon

    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    propriedades = propsys.SHGetPropertyStoreForWindow(hwnd)
    # Sem os dados de relançamento, o Explorer usa nome e ícone do python.exe.
    valores = (
        (pscon.PKEY_AppUserModel_RelaunchCommand,
         subprocess.list2cmdline([os.path.join(os.environ['WINDIR'], 'System32', 'wscript.exe'),
                                  os.path.join(raiz, 'Atalhos', 'Luna.vbs')])),
        (pscon.PKEY_AppUserModel_RelaunchDisplayNameResource, 'Luna'),
        (pscon.PKEY_AppUserModel_RelaunchIconResource,
         os.path.join(raiz, 'static', 'luna.ico') + ',0'),
        (pscon.PKEY_AppUserModel_ID, 'LunaLLM.Interface'),
    )
    for chave, valor in valores:
        propriedades.SetValue(chave, propsys.PROPVARIANTType(valor))
    propriedades.Commit()
