# SPDX-License-Identifier: GPL-3.0-only
"""Leitor do Remastered para o piloto. Apenas PROCESS_VM_READ/QUERY_INFORMATION.

Mapeamento de memória, flags e fogueiras adaptado de SoulMemory/SoulSplitter:
Copyright (c) 2022 Frank van der Stam; créditos adicionais a JKAnderson e
CapitaineToinon. Consulte FONTES.md e LICENSE nesta pasta.
"""
import ctypes as ct
from ctypes import wintypes as wt
import json
from pathlib import Path
import re
import struct


class LeituraIndisponivel(RuntimeError):
    pass


PADROES = {
    "game": ("48 8b 05 ? ? ? ? c6 40 18 00", 7),
    "data": ("48 8b 05 ? ? ? ? 48 8b 50 10 48 89 54 24 60", 7),
    "player": ("48 8b 0d ? ? ? ? 0f 28 f1 48 85 c9 74 ? 48 89 7c", 7),
    "flags": ("48 8b 0d ? ? ? ? 99 33 c2 45 33 c0 2b c2 8d 50 f6", 7),
    "bonfires": ("48 83 3d ? ? ? ? 00 48 8b f1", 8),
}


def localizar(codigo, base, padrao, tamanho):
    regex = b"".join(b"." if b == "?" else re.escape(bytes([int(b, 16)]))
                     for b in padrao.split())
    achados = list(re.finditer(regex, codigo, re.DOTALL))
    if len(achados) != 1:
        raise LeituraIndisponivel("Assinatura ausente ou ambígua; versão não validada")
    pos = achados[0].start()
    return base + pos + tamanho + struct.unpack_from("<i", codigo, pos + 3)[0]


def flag_offset(flag):
    numero = f"{flag:08d}"
    grupos = {"0": 0, "1": 0x500, "5": 0x5f00, "6": 0xb900, "7": 0x11300}
    areas = ["000", "100", "101", "102", "110", "120", "121", "130", "131",
             "132", "140", "141", "150", "151", "160", "170", "180", "181"]
    n = int(numero[5:])
    offset = grupos[numero[0]] + areas.index(numero[1:4]) * 0x500
    return offset + int(numero[4]) * 128 + (n // 32) * 4, 0x80000000 >> (n % 32)


class MemoriaWindows:
    def __init__(self, pid):
        self.kernel = ct.WinDLL("kernel32", use_last_error=True)
        self.kernel.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
        self.kernel.OpenProcess.restype = wt.HANDLE
        self.kernel.CloseHandle.argtypes = [wt.HANDLE]
        self.kernel.ReadProcessMemory.argtypes = [wt.HANDLE, ct.c_void_p, ct.c_void_p,
                                                 ct.c_size_t, ct.POINTER(ct.c_size_t)]
        self.kernel.ReadProcessMemory.restype = wt.BOOL
        self.handle = self.kernel.OpenProcess(0x0400 | 0x0010, False, pid)
        if not self.handle:
            raise LeituraIndisponivel("Sem acesso de leitura ao processo")
        try:
            psapi = ct.WinDLL("psapi", use_last_error=True)
            psapi.EnumProcessModulesEx.argtypes = [wt.HANDLE, ct.POINTER(ct.c_void_p),
                                                  wt.DWORD, ct.POINTER(wt.DWORD), wt.DWORD]
            psapi.EnumProcessModulesEx.restype = wt.BOOL
            modulos = (ct.c_void_p * 1024)()
            usado = wt.DWORD()
            if not psapi.EnumProcessModulesEx(self.handle, modulos, ct.sizeof(modulos),
                                              ct.byref(usado), 3) or not modulos[0]:
                raise LeituraIndisponivel("Módulo principal indisponível")
            self.base = modulos[0]
        except Exception:
            self.close()
            raise

    def close(self):
        if self.handle:
            self.kernel.CloseHandle(self.handle)
            self.handle = None

    def read(self, endereco, tamanho):
        if not endereco or tamanho < 1 or tamanho > 32 * 1024 * 1024:
            raise LeituraIndisponivel("Endereço ou tamanho inválido")
        buffer = ct.create_string_buffer(tamanho)
        lidos = ct.c_size_t()
        if not self.kernel.ReadProcessMemory(self.handle, endereco, buffer, tamanho,
                                              ct.byref(lidos)) or lidos.value != tamanho:
            raise LeituraIndisponivel("Leitura incompleta; aguardando estado estável")
        return buffer.raw

    def ptr(self, endereco):
        p = struct.unpack("<Q", self.read(endereco, 8))[0]
        if not p:
            raise LeituraIndisponivel("Personagem ou dados ainda não carregados")
        return p

    def int(self, endereco):
        return struct.unpack("<i", self.read(endereco, 4))[0]

    def codigo(self):
        # Varre só .text uma vez por processo, sem vasculhar toda a RAM do jogo.
        pe = self.base + self.int(self.base + 0x3c)
        cab = self.read(pe, 24)
        if cab[:4] != b"PE\x00\x00":
            raise LeituraIndisponivel("Cabeçalho PE inválido")
        secoes = struct.unpack_from("<H", cab, 6)[0]
        opcional = struct.unpack_from("<H", cab, 20)[0]
        if not 1 <= secoes <= 96:
            raise LeituraIndisponivel("Tabela PE inválida")
        for i in range(secoes):
            s = self.read(pe + 24 + opcional + i * 40, 40)
            if s[:8].rstrip(b"\0") == b".text":
                tamanho, relativo = struct.unpack_from("<II", s, 8)
                return self.base + relativo, self.read(self.base + relativo, tamanho)
        raise LeituraIndisponivel("Seção de código indisponível")


def versao_exe(caminho):
    api = ct.WinDLL("version", use_last_error=True)
    api.GetFileVersionInfoSizeW.argtypes = [wt.LPCWSTR, ct.POINTER(wt.DWORD)]
    api.GetFileVersionInfoW.argtypes = [wt.LPCWSTR, wt.DWORD, wt.DWORD, ct.c_void_p]
    api.VerQueryValueW.argtypes = [ct.c_void_p, wt.LPCWSTR, ct.POINTER(ct.c_void_p),
                                  ct.POINTER(wt.UINT)]
    tamanho = api.GetFileVersionInfoSizeW(caminho, None)
    if not tamanho:
        raise LeituraIndisponivel("Versão do executável indisponível")
    dados = ct.create_string_buffer(tamanho)
    ptr, n = ct.c_void_p(), wt.UINT()
    if (not api.GetFileVersionInfoW(caminho, 0, tamanho, dados)
            or not api.VerQueryValueW(dados, "\\", ct.byref(ptr), ct.byref(n)) or n.value < 16):
        raise LeituraIndisponivel("Versão inválida")
    alto, baixo = struct.unpack_from("<II", ct.string_at(ptr, n.value), 8)
    return (alto >> 16, alto & 65535, baixo >> 16, baixo & 65535)


class LeitorRemastered:
    def __init__(self):
        self.mem = None
        self.processo = None
        self.catalogo = json.loads(Path(__file__).with_name("catalogo.json").read_text(encoding="utf-8"))

    def close(self):
        if self.mem:
            self.mem.close()
        self.mem = self.processo = None

    def em_foco(self):
        api = ct.WinDLL("user32", use_last_error=True)
        api.GetForegroundWindow.restype = wt.HWND
        api.GetWindowThreadProcessId.argtypes = [wt.HWND, ct.POINTER(wt.DWORD)]
        pid = wt.DWORD()
        api.GetWindowThreadProcessId(api.GetForegroundWindow(), ct.byref(pid))
        return bool(self.processo and pid.value == self.processo.pid)

    def conectar(self):
        import psutil
        processo = next((p for p in psutil.process_iter(["name"])
                         if (p.info["name"] or "").lower() == "darksoulsremastered.exe"), None)
        if processo is None:
            raise LeituraIndisponivel("Remastered fechado")
        versao = versao_exe(processo.exe())
        if versao not in {(1, 0, 0, 0), (1, 3, 0, 0), (1, 3, 1, 0)}:
            raise LeituraIndisponivel("Versão do Remastered não mapeada")
        self.mem = MemoriaWindows(processo.pid)
        try:
            base, codigo = self.mem.codigo()
            self.raizes = {k: localizar(codigo, base, *v) for k, v in PADROES.items()}
            self.slot_offset = 0xa90 if versao == (1, 0, 0, 0) else 0xaa0
            self.processo = processo
            self.identidade = f"{processo.pid}:{processo.create_time()}"
        except Exception:
            self.close()
            raise

    def snapshot(self):
        if self.processo and not self.processo.is_running():
            self.close()
        if self.mem is None:
            self.conectar()
        m = self.mem
        player = m.ptr(m.ptr(self.raizes["player"]) + 0x68)
        game = m.ptr(self.raizes["game"])
        data = m.ptr(self.raizes["data"])
        flags = m.ptr(m.ptr(self.raizes["flags"]))
        slot, ng, tempo = m.int(game + self.slot_offset), m.int(data + 0x78), m.int(data + 0xa4)
        mortes = m.int(data + 0x98)
        if not (0 <= slot <= 9 and 0 <= ng <= 100 and tempo > 0 and 0 <= mortes <= 1000000):
            raise LeituraIndisponivel("Save carregando ou leitura incoerente")
        chefes = {}
        for id_, nome in self.catalogo["chefes"].items():
            offset, mask = flag_offset(int(id_))
            chefes[id_] = {"nome": nome, "derrotado": bool(m.int(flags + offset) & mask)}
        db = m.ptr(m.ptr(self.raizes["bonfires"]) + 0xb68)
        elemento = m.ptr(m.ptr(db + 0x28))
        vistos, fogueiras = set(), {}
        for _ in range(100):
            if elemento in vistos:
                break
            vistos.add(elemento)
            item = struct.unpack("<Q", m.read(elemento + 0x10, 8))[0]
            if not item:
                break
            id_, estado = str(m.int(item + 8)), m.int(item + 12)
            if id_ in self.catalogo["fogueiras"] and estado in {-1, 0, 10, 20, 30, 40}:
                fogueiras[id_] = {"nome": self.catalogo["fogueiras"][id_], "estado": estado}
            # A lista pode terminar em NULL ou voltar ao sentinela.
            proximo = struct.unpack("<Q", m.read(elemento, 8))[0]
            if not proximo:
                break
            elemento = proximo
        else:
            raise LeituraIndisponivel("Lista de fogueiras incoerente")
        if not fogueiras:
            raise LeituraIndisponivel("Fogueiras ainda não carregadas")
        if (slot != m.int(game + self.slot_offset) or ng != m.int(data + 0x78)
                or player != m.ptr(m.ptr(self.raizes["player"]) + 0x68)):
            raise LeituraIndisponivel("Personagem mudou durante a leitura")
        return {"sessao": f"{self.identidade}:{slot}:{ng}", "jogo": "DARK SOULS REMASTERED",
                "tempo_jogo_ms": tempo, "mortes": mortes, "chefes": chefes, "fogueiras": fogueiras}
