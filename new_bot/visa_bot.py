from collections import defaultdict
import httpx
import math  # <--- Adicione esta linha
import csv  # <--- Adicione esta linha
import time
import logging
import random
import os
import asyncio
import re
import subprocess
from datetime import date, timedelta, datetime, timezone
import json
import string
import sys
import signal
from typing import Dict, Tuple, List, Any, Optional, TYPE_CHECKING
import colorlog
import redis
import socket
import functools
import numpy as np
from curl_cffi import requests as curl_requests
if TYPE_CHECKING:
    import pandas as pd
import tomllib
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing
from bs4 import BeautifulSoup
from datetime import datetime
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
import gc
import pytz
import threading
from urllib.parse import quote

# =================================================================================
# SCRIPT DE STEALTH AVANÇADO (GHOST MODE DINÂMICO)
# =================================================================================

# =================================================================================
# MELHORIA 2.1 — Pool alargado de WebGL Fingerprints (15 perfis reais)
# Cada worker escolhe um perfil aleatorio — fingerprints nunca sao identicos
# =================================================================================
GPU_PROFILES = [
    # Intel (Mac / iGPU)
    ("Intel Inc.", "Intel Iris OpenGL Engine"),
    ("Intel Inc.", "Intel(R) Iris(TM) Plus Graphics OpenGL Engine"),
    ("Intel Inc.", "Intel(R) UHD Graphics 630 OpenGL Engine"),
    # NVIDIA via ANGLE (Windows D3D11)
    ("Google Inc. (NVIDIA)", "ANGLE (NVIDIA, NVIDIA GeForce GTX 1060 Direct3D11 vs_5_0 ps_5_0, D3D11)"),
    ("Google Inc. (NVIDIA)", "ANGLE (NVIDIA, NVIDIA GeForce GTX 1650 Direct3D11 vs_5_0 ps_5_0, D3D11)"),
    ("Google Inc. (NVIDIA)", "ANGLE (NVIDIA, NVIDIA GeForce GTX 1660 SUPER Direct3D11 vs_5_0 ps_5_0, D3D11)"),
    ("Google Inc. (NVIDIA)", "ANGLE (NVIDIA, NVIDIA GeForce RTX 2060 Direct3D11 vs_5_0 ps_5_0, D3D11)"),
    ("Google Inc. (NVIDIA)", "ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0, D3D11)"),
    ("Google Inc. (NVIDIA)", "ANGLE (NVIDIA, NVIDIA GeForce RTX 3070 Direct3D11 vs_5_0 ps_5_0, D3D11)"),
    ("Google Inc. (NVIDIA)", "ANGLE (NVIDIA, NVIDIA GeForce RTX 4060 Direct3D11 vs_5_0 ps_5_0, D3D11)"),
    # AMD via ANGLE (Windows D3D11)
    ("Google Inc. (AMD)", "ANGLE (AMD, AMD Radeon RX 580 Series Direct3D11 vs_5_0 ps_5_0, D3D11)"),
    ("Google Inc. (AMD)", "ANGLE (AMD, AMD Radeon RX 6600 XT Direct3D11 vs_5_0 ps_5_0, D3D11)"),
    ("Google Inc. (AMD)", "ANGLE (AMD, AMD Radeon RX 6700 XT Direct3D11 vs_5_0 ps_5_0, D3D11)"),
    # Intel via ANGLE (Windows D3D11)
    ("Google Inc. (Intel)", "ANGLE (Intel, Intel(R) UHD Graphics 620 Direct3D11 vs_5_0 ps_5_0, D3D11)"),
    ("Google Inc. (Intel)", "ANGLE (Intel, Intel(R) UHD Graphics 630 Direct3D11 vs_5_0 ps_5_0, D3D11)"),
    ("Google Inc. (Intel)", "ANGLE (Intel, Intel(R) Iris(R) Xe Graphics Direct3D11 vs_5_0 ps_5_0, D3D11)"),
]


def get_dynamic_stealth_script(gpu_vendor: str, gpu_renderer: str) -> str:
    """
    Gera o script de stealth injetado antes de cada pagina carregar.
    Cobre: WebGL (2.1), Canvas Noise (2.2), AudioContext (2.3),
           ClientRects e toString fix.
    Cada valor aleatorio e gerado uma vez no arranque do browser e mantido
    consistente durante toda a sessao (nao muda a cada chamada de API).
    """
    v = gpu_vendor.replace("'", "\\'")
    r = gpu_renderer.replace("'", "\\'")

    return f"""
    () => {{
        // ── 2.1 WEBGL FINGERPRINT ────────────────────────────────────────────────
        // Substitui vendor e renderer pelo perfil selecionado para este worker.
        // Aplicado em WebGL1 e WebGL2 para cobrir todos os browsers.
        const _wgl1Get = WebGLRenderingContext.prototype.getParameter;
        WebGLRenderingContext.prototype.getParameter = function(parameter) {{
            if (parameter === 37445) return '{v}';  // UNMASKED_VENDOR_WEBGL
            if (parameter === 37446) return '{r}';  // UNMASKED_RENDERER_WEBGL
            return _wgl1Get.call(this, parameter);
        }};
        if (typeof WebGL2RenderingContext !== 'undefined') {{
            const _wgl2Get = WebGL2RenderingContext.prototype.getParameter;
            WebGL2RenderingContext.prototype.getParameter = function(parameter) {{
                if (parameter === 37445) return '{v}';
                if (parameter === 37446) return '{r}';
                return _wgl2Get.call(this, parameter);
            }};
        }}

        // ── 2.2 CANVAS NOISE INJECTION ───────────────────────────────────────────
        // Injeta ruido de 1 bit (XOR) em todos os canais RGBA de cada pixel.
        // Invisivel ao olho humano mas torna o hash do canvas unico por sessao.
        // Aplicado em getImageData (leitura de pixels) E toDataURL (export PNG).
        const _origGetImageData = CanvasRenderingContext2D.prototype.getImageData;
        CanvasRenderingContext2D.prototype.getImageData = function(x, y, w, h) {{
            const imageData = _origGetImageData.call(this, x, y, w, h);
            // Ruido de 1 bit: invisivel, mas muda o hash do fingerprint
            for (let i = 0; i < imageData.data.length; i += 4) {{
                imageData.data[i]     ^= 1;  // R
                imageData.data[i + 1] ^= 1;  // G
                // Alpha (i+3) nao e alterado para nao afetar transparencias
            }}
            return imageData;
        }};

        const _origToDataURL = HTMLCanvasElement.prototype.toDataURL;
        HTMLCanvasElement.prototype.toDataURL = function(type) {{
            const ctx = this.getContext('2d');
            if (ctx && this.width > 0 && this.height > 0) {{
                try {{
                    // Le pixels, injeta ruido e reescreve — garante que o export
                    // tambem inclui o ruido mesmo que nao passe por getImageData
                    const imageData = _origGetImageData.call(ctx, 0, 0, this.width, this.height);
                    for (let i = 0; i < imageData.data.length; i += 4) {{
                        imageData.data[i]     ^= 1;
                        imageData.data[i + 1] ^= 1;
                    }}
                    ctx.putImageData(imageData, 0, 0);
                }} catch(e) {{
                    // Canvas pode ser tainted (cross-origin) — ignorar silenciosamente
                }}
            }}
            return _origToDataURL.apply(this, arguments);
        }};

        // toBlob tambem precisa de cobertura (usado por alguns fingerprinters)
        const _origToBlob = HTMLCanvasElement.prototype.toBlob;
        if (_origToBlob) {{
            HTMLCanvasElement.prototype.toBlob = function(callback, type, quality) {{
                const ctx = this.getContext('2d');
                if (ctx && this.width > 0 && this.height > 0) {{
                    try {{
                        const imageData = _origGetImageData.call(ctx, 0, 0, this.width, this.height);
                        for (let i = 0; i < imageData.data.length; i += 4) {{
                            imageData.data[i]     ^= 1;
                            imageData.data[i + 1] ^= 1;
                        }}
                        ctx.putImageData(imageData, 0, 0);
                    }} catch(e) {{}}
                }}
                return _origToBlob.call(this, callback, type, quality);
            }};
        }}

        // ── 2.3 AUDIOCONTEXT SPOOFING ────────────────────────────────────────────
        // Spoofa sampleRate, maxChannelCount e AudioBuffer para parecer hardware real.
        // Cada sessao escolhe valores ligeiramente diferentes dentro de ranges normais.
        const _AudioCtx = window.AudioContext || window.webkitAudioContext;
        if (_AudioCtx) {{
            // Valores reais possiveis em hardware de consumidor
            const _sampleRates  = [44100, 48000];
            const _maxChannels  = [2, 6, 8];
            const _sr  = _sampleRates[Math.floor(Math.random() * _sampleRates.length)];
            const _mch = _maxChannels[Math.floor(Math.random() * _maxChannels.length)];

            const _origAudioCtx = _AudioCtx;
            window.AudioContext = window.webkitAudioContext = function(...args) {{
                const ctx = new _origAudioCtx(...args);

                // Spoofa sampleRate (read-only via defineProperty)
                try {{
                    Object.defineProperty(ctx, 'sampleRate', {{
                        get: () => _sr,
                        configurable: true,
                    }});
                }} catch(e) {{}}

                // Spoofa destination.maxChannelCount
                try {{
                    Object.defineProperty(ctx.destination, 'maxChannelCount', {{
                        get: () => _mch,
                        configurable: true,
                    }});
                }} catch(e) {{}}

                // Spoofa createAnalyser — adiciona ruido minusculo nos dados de frequencia
                const _origCreateAnalyser = ctx.createAnalyser.bind(ctx);
                ctx.createAnalyser = function() {{
                    const analyser = _origCreateAnalyser();
                    const _origGetFloat = analyser.getFloatFrequencyData.bind(analyser);
                    analyser.getFloatFrequencyData = function(array) {{
                        _origGetFloat(array);
                        for (let i = 0; i < array.length; i++) {{
                            array[i] += (Math.random() - 0.5) * 0.0001;
                        }}
                    }};
                    return analyser;
                }};

                // Spoofa createBuffer — varia ligeiramente o length reportado
                const _origCreateBuffer = ctx.createBuffer.bind(ctx);
                ctx.createBuffer = function(numChannels, length, sampleRate) {{
                    // Pequena variacao no length (invisivel ao audio, detetavel por fingerprint)
                    const _tweakedLength = length + Math.floor(Math.random() * 3);
                    return _origCreateBuffer(numChannels, _tweakedLength, sampleRate);
                }};

                return ctx;
            }};
            // Preservar prototype chain para nao quebrar instanceof checks
            window.AudioContext.prototype = _origAudioCtx.prototype;
        }}

        // ── 4. CLIENT RECTS ──────────────────────────────────────────────────────
        // Variacao decimal minima para parecer renderizacao real de GPU
        const _origGetBCR = Element.prototype.getBoundingClientRect;
        Element.prototype.getBoundingClientRect = function() {{
            const rect = _origGetBCR.call(this);
            return {{
                x: rect.x + (Math.random() * 0.000001),
                y: rect.y + (Math.random() * 0.000001),
                width:  rect.width,
                height: rect.height,
                top:    rect.top,
                right:  rect.right,
                bottom: rect.bottom,
                left:   rect.left,
                toJSON: rect.toJSON,
            }};
        }};

        // ── 5. toString FIX ──────────────────────────────────────────────────────
        // Garante que as funcoes sobrepostas reportam [native code]
        const _nativeToString = Function.prototype.toString;
        Function.prototype.toString = function() {{
            if (
                this === WebGLRenderingContext.prototype.getParameter ||
                (typeof WebGL2RenderingContext !== 'undefined' &&
                 this === WebGL2RenderingContext.prototype.getParameter)
            ) {{
                return 'function getParameter() {{ [native code] }}';
            }}
            return _nativeToString.call(this);
        }};
    }}
    """

# =================================================================================
# MELHORIA 2.4 — Hardware Profiles consistentes com UA e GPU
# navigator.hardwareConcurrency, navigator.deviceMemory e navigator.platform
# sao valores fixos por defeito — detetaveis como automacao.
# Cada sessao escolhe UM perfil completo que casa com o User-Agent selecionado.
# =================================================================================
HARDWARE_PROFILES = [
    # --- Windows / laptop basico ---
    {"cores": 4,  "memory": 4,  "platform": "Win32",   "label": "laptop-entry"},
    {"cores": 4,  "memory": 8,  "platform": "Win32",   "label": "laptop-mid"},
    # --- Windows / desktop ---
    {"cores": 8,  "memory": 8,  "platform": "Win32",   "label": "desktop-std"},
    {"cores": 8,  "memory": 16, "platform": "Win32",   "label": "desktop-high"},
    {"cores": 12, "memory": 16, "platform": "Win32",   "label": "workstation"},
    {"cores": 16, "memory": 32, "platform": "Win32",   "label": "workstation-hi"},
    # --- macOS ---
    {"cores": 4,  "memory": 8,  "platform": "MacIntel", "label": "macbook-air"},
    {"cores": 8,  "memory": 16, "platform": "MacIntel", "label": "macbook-pro"},
    {"cores": 10, "memory": 16, "platform": "MacIntel", "label": "imac"},
]

# Valores validos para deviceMemory (API usa potencias de 2, max 8 GB reportado)
_VALID_MEMORY_GB = {1, 2, 4, 8}


def pick_hardware_profile(user_agent: str) -> dict:
    """
    Escolhe um perfil de hardware consistente com o User-Agent.
    - UA Windows  → plataforma Win32
    - UA Macintosh → plataforma MacIntel
    - Outros       → escolha aleatoria livre
    """
    if "Macintosh" in user_agent or "Mac OS" in user_agent:
        candidates = [p for p in HARDWARE_PROFILES if p["platform"] == "MacIntel"]
    else:
        candidates = [p for p in HARDWARE_PROFILES if p["platform"] == "Win32"]

    if not candidates:
        candidates = HARDWARE_PROFILES

    profile = random.choice(candidates)

    # Garante que memory e sempre uma potencia de 2 valida (max 8 que a API reporta)
    mem = profile["memory"]
    if mem not in _VALID_MEMORY_GB:
        mem = min(_VALID_MEMORY_GB, key=lambda v: abs(v - mem))
    return {**profile, "memory": mem}


def get_dynamic_stealth_script_full(gpu_vendor: str, gpu_renderer: str,
                                    hw: dict) -> str:
    """
    Versao completa do stealth script que inclui:
      2.1 WebGL spoofing
      2.2 Canvas noise
      2.3 AudioContext spoofing
      2.4 Hardware spoofing (hardwareConcurrency, deviceMemory, platform)
      2.5 WebRTC leak prevention
      4   ClientRects jitter
      5   toString fix
    Recebe o perfil de hardware pre-selecionado para manter consistencia
    em toda a sessao (o mesmo objeto hw e reutilizado em reinjecoes).
    """
    v    = gpu_vendor.replace("'", "\\'")
    r    = gpu_renderer.replace("'", "\\'")
    cores  = hw["cores"]
    memory = hw["memory"]
    plat   = hw["platform"].replace("'", "\\'")

    return f"""
    () => {{
        // ── 2.1 WEBGL FINGERPRINT ────────────────────────────────────────────────
        const _wgl1Get = WebGLRenderingContext.prototype.getParameter;
        WebGLRenderingContext.prototype.getParameter = function(parameter) {{
            if (parameter === 37445) return '{v}';
            if (parameter === 37446) return '{r}';
            return _wgl1Get.call(this, parameter);
        }};
        if (typeof WebGL2RenderingContext !== 'undefined') {{
            const _wgl2Get = WebGL2RenderingContext.prototype.getParameter;
            WebGL2RenderingContext.prototype.getParameter = function(parameter) {{
                if (parameter === 37445) return '{v}';
                if (parameter === 37446) return '{r}';
                return _wgl2Get.call(this, parameter);
            }};
        }}

        // ── 2.2 CANVAS NOISE INJECTION ───────────────────────────────────────────
        const _origGetImageData = CanvasRenderingContext2D.prototype.getImageData;
        CanvasRenderingContext2D.prototype.getImageData = function(x, y, w, h) {{
            const imageData = _origGetImageData.call(this, x, y, w, h);
            for (let i = 0; i < imageData.data.length; i += 4) {{
                imageData.data[i]     ^= 1;
                imageData.data[i + 1] ^= 1;
            }}
            return imageData;
        }};
        const _origToDataURL = HTMLCanvasElement.prototype.toDataURL;
        HTMLCanvasElement.prototype.toDataURL = function(type) {{
            const ctx = this.getContext('2d');
            if (ctx && this.width > 0 && this.height > 0) {{
                try {{
                    const id = _origGetImageData.call(ctx, 0, 0, this.width, this.height);
                    for (let i = 0; i < id.data.length; i += 4) {{
                        id.data[i] ^= 1; id.data[i+1] ^= 1;
                    }}
                    ctx.putImageData(id, 0, 0);
                }} catch(e) {{}}
            }}
            return _origToDataURL.apply(this, arguments);
        }};
        const _origToBlob = HTMLCanvasElement.prototype.toBlob;
        if (_origToBlob) {{
            HTMLCanvasElement.prototype.toBlob = function(cb, type, quality) {{
                const ctx = this.getContext('2d');
                if (ctx && this.width > 0 && this.height > 0) {{
                    try {{
                        const id = _origGetImageData.call(ctx, 0, 0, this.width, this.height);
                        for (let i = 0; i < id.data.length; i += 4) {{
                            id.data[i] ^= 1; id.data[i+1] ^= 1;
                        }}
                        ctx.putImageData(id, 0, 0);
                    }} catch(e) {{}}
                }}
                return _origToBlob.call(this, cb, type, quality);
            }};
        }}

        // ── 2.3 AUDIOCONTEXT SPOOFING ────────────────────────────────────────────
        const _AudioCtx = window.AudioContext || window.webkitAudioContext;
        if (_AudioCtx) {{
            const _sampleRates = [44100, 48000];
            const _maxChannels = [2, 6, 8];
            const _sr  = _sampleRates[Math.floor(Math.random() * _sampleRates.length)];
            const _mch = _maxChannels[Math.floor(Math.random() * _maxChannels.length)];
            const _origAudioCtx = _AudioCtx;
            window.AudioContext = window.webkitAudioContext = function(...args) {{
                const ctx = new _origAudioCtx(...args);
                try {{ Object.defineProperty(ctx, 'sampleRate', {{ get: () => _sr, configurable: true }}); }} catch(e) {{}}
                try {{ Object.defineProperty(ctx.destination, 'maxChannelCount', {{ get: () => _mch, configurable: true }}); }} catch(e) {{}}
                const _origCreateAnalyser = ctx.createAnalyser.bind(ctx);
                ctx.createAnalyser = function() {{
                    const analyser = _origCreateAnalyser();
                    const _origGetFloat = analyser.getFloatFrequencyData.bind(analyser);
                    analyser.getFloatFrequencyData = function(array) {{
                        _origGetFloat(array);
                        for (let i = 0; i < array.length; i++) array[i] += (Math.random() - 0.5) * 0.0001;
                    }};
                    return analyser;
                }};
                const _origCreateBuffer = ctx.createBuffer.bind(ctx);
                ctx.createBuffer = function(numChannels, length, sampleRate) {{
                    return _origCreateBuffer(numChannels, length + Math.floor(Math.random() * 3), sampleRate);
                }};
                return ctx;
            }};
            window.AudioContext.prototype = _origAudioCtx.prototype;
        }}

        // ── 2.4 HARDWARE SPOOFING ────────────────────────────────────────────────
        // hardwareConcurrency, deviceMemory e platform sao valores fixos por defeito.
        // Substituimos pelos valores do perfil selecionado para este worker.
        try {{
            Object.defineProperty(navigator, 'hardwareConcurrency', {{
                get: () => {cores},
                configurable: true,
            }});
        }} catch(e) {{}}

        try {{
            // deviceMemory e opcional (nao suportado em Firefox/Safari)
            if ('deviceMemory' in navigator) {{
                Object.defineProperty(navigator, 'deviceMemory', {{
                    get: () => {memory},
                    configurable: true,
                }});
            }}
        }} catch(e) {{}}

        try {{
            Object.defineProperty(navigator, 'platform', {{
                get: () => '{plat}',
                configurable: true,
            }});
        }} catch(e) {{}}

        // ── 2.5 WEBRTC LEAK PREVENTION ───────────────────────────────────────────
        // WebRTC pode expor o IP real mesmo com proxy ativo.
        // Desativamos RTCPeerConnection completamente para evitar fugas de IP.
        // Mantemos a API definida (undefined causaria erros em alguns sites)
        // mas substituimos por uma versao que nunca faz STUN/TURN requests.
        try {{
            const _RTCNoop = function() {{
                throw new DOMException('WebRTC disabled by privacy policy', 'NotSupportedError');
            }};
            _RTCNoop.prototype = Object.create(EventTarget.prototype);
            window.RTCPeerConnection        = _RTCNoop;
            window.webkitRTCPeerConnection  = _RTCNoop;
            window.mozRTCPeerConnection     = _RTCNoop;
            // Tambem cobre o MTI (MediaStream Interface) para prevenir fugas via getUserMedia
            if (navigator.mediaDevices) {{
                const _origGetUserMedia = navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);
                navigator.mediaDevices.getUserMedia = function(constraints) {{
                    // Bloquear pedidos de audio/video que usam WebRTC por baixo
                    if (constraints && (constraints.video || constraints.audio)) {{
                        return Promise.reject(new DOMException('Blocked by privacy policy', 'NotAllowedError'));
                    }}
                    return _origGetUserMedia(constraints);
                }};
            }}
        }} catch(e) {{}}

        // ── 4. CLIENT RECTS ──────────────────────────────────────────────────────
        const _origGetBCR = Element.prototype.getBoundingClientRect;
        Element.prototype.getBoundingClientRect = function() {{
            const rect = _origGetBCR.call(this);
            return {{
                x: rect.x + (Math.random() * 0.000001),
                y: rect.y + (Math.random() * 0.000001),
                width: rect.width, height: rect.height,
                top: rect.top, right: rect.right,
                bottom: rect.bottom, left: rect.left,
                toJSON: rect.toJSON,
            }};
        }};

        // ── 5. toString FIX ──────────────────────────────────────────────────────
        const _nativeToString = Function.prototype.toString;
        Function.prototype.toString = function() {{
            if (
                this === WebGLRenderingContext.prototype.getParameter ||
                (typeof WebGL2RenderingContext !== 'undefined' &&
                 this === WebGL2RenderingContext.prototype.getParameter)
            ) {{
                return 'function getParameter() {{ [native code] }}';
            }}
            return _nativeToString.call(this);
        }};
    }}
    """

# BUG C1 FIX: Semaphore NAO pode ser criado no import (event loop errado).
# Sera criado lazily no primeiro uso dentro do async loop correto.
_PLAYWRIGHT_SEMAPHORE: asyncio.Semaphore = None
_PLAYWRIGHT_SEMAPHORE_LOCK = threading.Lock()

def _get_playwright_semaphore(limit: int = 8) -> asyncio.Semaphore:
    """Retorna o semaphore, criando-o no event loop correto se necessario."""
    global _PLAYWRIGHT_SEMAPHORE
    if _PLAYWRIGHT_SEMAPHORE is None:
        # Cria no event loop do worker async — nunca no import global
        _PLAYWRIGHT_SEMAPHORE = asyncio.Semaphore(limit)
    return _PLAYWRIGHT_SEMAPHORE

# =================================================================================
# TLS/JA3 SPOOFING — TLSClient com curl_cffi Chrome120 Impersonation
#
# Problema resolvido:
#   O Playwright usa a pilha TLS do Chromium que pode ser identificada pelo
#   servidor (JA3 fingerprint). curl_cffi replica o JA3 exato do Chrome 120,
#   tornando o preflight indistinguivel de um browser real.
#
# Fluxo de integração:
#   1. TLSClient.preflight_tls()  → GET com JA3 Chrome120 antes do Playwright
#      → Obtém cookies de sessão iniciais (_USER_CONSENT, cookiesession1, etc.)
#   2. TLSClient.stealth_context() → cria o contexto Playwright com:
#      - User-Agent e sec-ch-ua consistentes com o preflight
#      - Cookies do preflight injetados antes de qualquer navegação
#      - Init script que remove navigator.webdriver e adiciona window.chrome
#
# Resultado: o servidor vê uma sessão TLS "limpa" antes do Playwright
# abrir qualquer conexão, reduzindo drasticamente a probabilidade de
# desafios PoW e bloqueios de fingerprint.
# =================================================================================

# Perfis Chrome disponíveis no curl_cffi — usamos o mais recente suportado
_CURL_CFFI_PROFILES = [
    "chrome120",
    "chrome119",
    "chrome116",
    "chrome110",
]

class TLSClient:
    """
    Cliente TLS com impersonation de Chrome real via curl_cffi.

    Responsabilidades:
      - preflight_tls()   : GET com JA3 Chrome120 para obter cookies iniciais
      - stealth_context() : cria contexto Playwright com UA e cookies do preflight
      - inject_cookies()  : injeta cookies do preflight num contexto existente

    Thread-safety: a Session do curl_cffi NAO e thread-safe para pedidos
    concorrentes — cada instancia deve ser usada por um unico worker/login.
    """

    def __init__(self, user_agent: str, proxy_raw: str = None,
                 impersonate: str = "chrome120"):
        """
        user_agent  : UA a usar (deve ser consistente com o Playwright)
        proxy_raw   : "ip:port:user:pwd" (formato padrao do bot)
        impersonate : perfil curl_cffi (chrome120, chrome119, ...)
        """
        self.user_agent   = user_agent
        self.proxy_raw    = proxy_raw
        self.impersonate  = impersonate if impersonate in _CURL_CFFI_PROFILES else "chrome120"
        self._cookies: dict = {}
        self._resp_headers: dict = {}

        # Construir sec-ch-ua dinamicamente a partir do UA (usa a funcao ja existente)
        sec_ch_ua, ch_mobile, ch_platform = build_sec_ch_ua(user_agent)

        # BUG C3 FIX: derivar perfil JA3 do User-Agent para consistencia
        # chrome146 nao existe no curl_cffi — mapear para o mais proximo
        _ua_ver_match = re.search(r'Chrome/(\d+)\.', user_agent)
        _ua_ver = int(_ua_ver_match.group(1)) if _ua_ver_match else 120
        if _ua_ver >= 130:
            _derived = 'chrome124'   # mais recente suportado pelo curl_cffi
        elif _ua_ver >= 120:
            _derived = 'chrome120'
        elif _ua_ver >= 116:
            _derived = 'chrome116'
        else:
            _derived = 'chrome110'
        self.impersonate = _derived
        self.session = curl_requests.Session(impersonate=self.impersonate)
        self.session.headers.update({
            "User-Agent":        user_agent,
            "Accept":            "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language":   "pt-PT,pt;q=0.9,en;q=0.8",
            "Accept-Encoding":   "gzip, deflate, br, zstd",
            "Sec-Fetch-Dest":    "document",
            "Sec-Fetch-Mode":    "navigate",
            "Sec-Fetch-Site":    "none",
            "Sec-Fetch-User":    "?1",
            "Upgrade-Insecure-Requests": "1",
            "Cache-Control":     "no-cache",
            "Pragma":            "no-cache",
            "sec-ch-ua":         sec_ch_ua,
            "sec-ch-ua-mobile":  ch_mobile,
            "sec-ch-ua-platform": ch_platform,
        })

        # Configurar proxy se fornecido
        if proxy_raw:
            self._apply_proxy(proxy_raw)

    def _apply_proxy(self, proxy_raw: str):
        """Converte 'ip:port:user:pwd' para o formato do curl_cffi."""
        try:
            proxy_url = _proxy_to_http_url(proxy_raw)
            if not proxy_url:
                safe_print(f"[TLSClient] Formato de proxy invalido: {_proxy_log_label(proxy_raw)}")
                return
            self.session.proxies = {
                "http":  proxy_url,
                "https": proxy_url,
            }
        except Exception as e:
            safe_print(f"[TLSClient] Erro ao configurar proxy: {e}")

    async def preflight_tls(self, url: str = None) -> dict:
        """
        Faz um GET com JA3 Chrome real para:
          - Resolver desafio PoW inicial (se existir)
          - Obter cookies de sessao (_USER_CONSENT, cookiesession1, Vistos_sid)
          - Validar que o proxy funciona com o site alvo

        Retorna dict com status, perfil ja3, cookies e headers de resposta.
        Nao bloqueia o event loop (usa run_in_executor internamente).
        """
        target = url or f"{BASE_URL}/VistosOnline/"

        def _do_get():
            try:
                resp = self.session.get(target, timeout=15, allow_redirects=True)
                return resp
            except Exception as e:
                raise RuntimeError(f"TLS preflight falhou: {e}")

        loop = asyncio.get_running_loop()
        try:
            resp = await loop.run_in_executor(None, _do_get)
            self._cookies      = dict(resp.cookies)
            self._resp_headers = dict(resp.headers)
            try:
                resp_text = str(resp.text or "")
            except Exception:
                resp_text = ""

            preflight_icon = "✅" if resp.status_code < 500 else "⚠️"
            safe_print(
                f"[TLSClient] {preflight_icon} Preflight HTTP status={resp.status_code} "
                f"ja3={self.impersonate} cookies={list(self._cookies.keys())}"
            )
            return {
                "status":  resp.status_code,
                "ja3":     self.impersonate,
                "cookies": self._cookies,
                "headers": self._resp_headers,
                "text":    resp_text[:500],
            }
        except Exception as e:
            safe_print(f"[TLSClient] ⚠️ Preflight falhou (nao critico): {e}")
            return {"status": 0, "ja3": self.impersonate, "cookies": {}, "headers": {}, "text": ""}

    async def stealth_context(self, browser, extra_http_headers: dict = None,
                               viewport_size: dict = None, locale: str = "pt-BR",
                               timezone_id: str = "Europe/Lisbon",
                               proxy_config: dict = None):
        """
        Cria um contexto Playwright com:
          - UA e sec-ch-ua consistentes com o preflight TLS
          - Cookies do preflight injetados antes de qualquer navegacao
          - Init script anti-detecao (webdriver, chrome runtime)

        Substitui o browser.new_context() manual no fluxo de login.
        Retorna (context, page) prontos a usar.
        """
        vp = viewport_size or {"width": 1920, "height": 1080}
        headers = extra_http_headers or {}

        # Garantir que sec-ch-ua esta nos extra_headers do contexto
        sec_ch_ua, ch_mobile, ch_platform = build_sec_ch_ua(self.user_agent)
        merged_headers = {
            "Accept-Language":   "pt-BR,pt;q=0.9",
            "sec-ch-ua":         sec_ch_ua,
            "sec-ch-ua-mobile":  ch_mobile,
            "sec-ch-ua-platform": ch_platform,
            **headers,
        }

        ctx_opts: Dict[str, Any] = {
            "viewport": vp,
            "user_agent": self.user_agent,
            "extra_http_headers": merged_headers,
            "locale": locale,
            "timezone_id": timezone_id,
        }
        if proxy_config:
            ctx_opts["proxy"] = proxy_config

        context = await browser.new_context(**ctx_opts)

        # Injetar init script anti-detecao
        await context.add_init_script("""
            () => {
                // Remove webdriver flag — principal sinal de automacao
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined,
                    configurable: true,
                });
                // Adicionar window.chrome que browsers reais tem
                if (!window.chrome) {
                    window.chrome = {
                        runtime: {},
                        loadTimes: function() {},
                        csi: function() {},
                        app: {},
                    };
                }
                // Remover propriedades que o Playwright/CDP adicionam
                delete window.__playwright;
                delete window.__pw_manual;
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
            }
        """)

        # Injetar cookies do preflight para simular sessao ja estabelecida
        await self.inject_cookies(context)

        page = await context.new_page()
        return context, page

    async def inject_cookies(self, context, extra_cookies: list = None):
        """
        Injeta os cookies obtidos no preflight no contexto Playwright.
        Converte o formato dict (curl_cffi) para list of dicts (Playwright).
        extra_cookies: lista adicional no formato Playwright (opcional).
        """
        if not self._cookies and not extra_cookies:
            return

        playwright_cookies = []

        # Converter cookies do preflight (dict simples) para formato Playwright
        for name, value in self._cookies.items():
            playwright_cookies.append({
                "name":   name,
                "value":  str(value),
                "domain": "pedidodevistos.mne.gov.pt",
                "path":   "/",
                "httpOnly": False,
                "secure":   True,
                "sameSite": "Lax",
            })

        if extra_cookies:
            playwright_cookies.extend(extra_cookies)

        if playwright_cookies:
            try:
                await context.add_cookies(playwright_cookies)
                safe_print(
                    f"[TLSClient] 🍪 {len(playwright_cookies)} cookies injetados no contexto"
                )
            except Exception as e:
                safe_print(f"[TLSClient] ⚠️ Erro ao injetar cookies: {e}")

    def close(self):
        """Fecha a sessao curl_cffi."""
        try:
            self.session.close()
        except Exception:
            pass

# =================================================================================
# HEADERS REAIS DO CHROME 146 (Capturados via F12 DevTools)
# =================================================================================
# Estes headers replicam EXATAMENTE o que um Chrome 146 real envia.
# Base URL do site alvo (usado em Origin e Referer)
SITE_ORIGIN = 'https://pedidodevistos.mne.gov.pt'
SITE_REFERER = 'https://pedidodevistos.mne.gov.pt/VistosOnline/Authentication.jsp'

# Headers para navegação de páginas (GET requests) - Usado pelo httpx session
# =================================================================================
# MELHORIA 1.3 — sec-ch-ua DINAMICO (gerado a partir do User-Agent real)
# Elimina inconsistencia entre UA e sec-ch-ua que causava detecao
# =================================================================================

def build_sec_ch_ua(user_agent: str) -> tuple:
    """
    Gera os valores sec-ch-ua, sec-ch-ua-mobile e sec-ch-ua-platform
    dinamicamente, extraindo a versao do Chrome do User-Agent fornecido.
    Garante que UA e sec-ch-ua tem sempre a mesma versao.
    """
    chrome_match = re.search(r'Chrome/(\d+)\.', user_agent)
    chrome_version = chrome_match.group(1) if chrome_match else "146"

    if "Windows" in user_agent:
        platform = '"Windows"'
        mobile = "?0"
    elif "Macintosh" in user_agent:
        platform = '"macOS"'
        mobile = "?0"
    elif "Android" in user_agent:
        platform = '"Android"'
        mobile = "?1"
    else:
        platform = '"Linux"'
        mobile = "?0"

    sec_ch_ua = (
        f'"Google Chrome";v="{chrome_version}", '
        f'"Chromium";v="{chrome_version}", '
        f'"Not A(Brand";v="24"'
    )
    return sec_ch_ua, mobile, platform


def get_main_headers(user_agent: str) -> dict:
    """Gera headers de navegacao GET com sec-ch-ua consistente com o UA."""
    sec_ch_ua, mobile, platform = build_sec_ch_ua(user_agent)
    return {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,/;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Encoding': 'gzip, deflate, br, zstd',
        'Accept-Language': 'pt-BR,pt;q=0.9',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'Origin': SITE_ORIGIN,
        'Pragma': 'no-cache',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Upgrade-Insecure-Requests': '1',
        'User-Agent': user_agent,
        'sec-ch-ua': sec_ch_ua,
        'sec-ch-ua-mobile': mobile,
        'sec-ch-ua-platform': platform,
    }


def get_login_headers(user_agent: str) -> dict:
    """Gera headers de AJAX POST com sec-ch-ua consistente com o UA."""
    sec_ch_ua, mobile, platform = build_sec_ch_ua(user_agent)
    return {
        'Accept': '*/*',
        'Accept-Encoding': 'gzip, deflate, br, zstd',
        'Accept-Language': 'pt-BR,pt;q=0.9',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'Origin': SITE_ORIGIN,
        'Pragma': 'no-cache',
        'Referer': SITE_REFERER,
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin',
        'User-Agent': user_agent,
        'X-Requested-With': 'XMLHttpRequest',
        'sec-ch-ua': sec_ch_ua,
        'sec-ch-ua-mobile': mobile,
        'sec-ch-ua-platform': platform,
    }


# Headers estaticos mantidos como fallback (usado antes de ter UA definido)
main_headers = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,/;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'Accept-Encoding': 'gzip, deflate, br, zstd',
    'Accept-Language': 'pt-BR,pt;q=0.9',
    'Cache-Control': 'no-cache',
    'Connection': 'keep-alive',
    'Origin': SITE_ORIGIN,
    'Pragma': 'no-cache',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-User': '?1',
    'Upgrade-Insecure-Requests': '1',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36',
    'sec-ch-ua': '"Google Chrome";v="146", "Chromium";v="146", "Not A(Brand";v="24"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
}

# Headers para AJAX POST (login, submissoes) - fallback estatico
login_headers = {
    'Accept': '*/*',
    'Accept-Encoding': 'gzip, deflate, br, zstd',
    'Accept-Language': 'pt-BR,pt;q=0.9',
    'Cache-Control': 'no-cache',
    'Connection': 'keep-alive',
    'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
    'Origin': SITE_ORIGIN,
    'Pragma': 'no-cache',
    'Referer': SITE_REFERER,
    'Sec-Fetch-Dest': 'empty',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Site': 'same-origin',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36',
    'X-Requested-With': 'XMLHttpRequest',
    'sec-ch-ua': '"Google Chrome";v="146", "Chromium";v="146", "Not A(Brand";v="24"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
}

# User-Agent consistente com os headers acima (Chrome 146)
user_agents = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36",
]
OUTPUT_DIR = os.path.join(os.getcwd(), 'PDFs')
WORKING_DIR = os.path.dirname(os.path.abspath(sys.argv[0]))
BASE_URL = "https://pedidodevistos.mne.gov.pt"

# Lista de proxies = [DIRECT_PROXY_MARKER] quando use_proxy=false no TOML
DIRECT_PROXY_MARKER = "__DIRECT__"

# Status no CSV — não enfileirar de novo (concluído, em curso, ou pausa manual)
CSV_STATUS_EXCLUDE_FROM_QUEUE = frozenset({
    "true", "success", "processing",
    "blocked_site", "banned_403", "recaptcha_quota",
    "failed_retry_later",
})


def _norm_csv_status(val) -> str:
    return str(val or "").strip().lower()


def _csv_status_summary(df) -> tuple[dict, int]:
    """
    Resume os estados presentes no CSV e quantos utilizadores ainda podem entrar
    na fila de trabalho.
    """
    counts = defaultdict(int)
    queue_eligible = 0

    if 'status' not in df.columns:
        return dict(counts), 0

    for raw_status in df['status'].tolist():
        norm = _norm_csv_status(raw_status)
        label = norm or "<empty>"
        counts[label] += 1
        if norm not in CSV_STATUS_EXCLUDE_FROM_QUEUE:
            queue_eligible += 1

    return dict(counts), queue_eligible


def _is_server_login_rejection(err: str) -> bool:
    """Resposta JSON explícita do /login — retentar outra chave Anti-Captcha só piora a quota."""
    return "Login Rejeitado pelo Site" in err


def _reclaim_stale_processing_rows(df, credentials_file: str) -> int:
    """
    Recupera linhas presas em 'processing' no CSV, deixadas para trás por um
    bot anterior que crashou ou foi morto a meio do fluxo.

    Sem isto, o status 'processing' fica permanentemente no CSV e como
    'processing' está em CSV_STATUS_EXCLUDE_FROM_QUEUE o utilizador nunca
    volta a entrar na work queue — o bot arranca a seguir e termina logo
    com "Nenhum utilizador elegivel para a queue", como aconteceu em
    06:39:04 do log.

    A função actualiza directamente o CSV via update_csv_status (com lock
    atómico), e altera o DataFrame em memória para que o resumo seguinte
    e a construção da queue já vejam o novo status.

    Retorna o número de linhas recuperadas. Esta função só deve ser chamada
    no arranque do processo principal, antes de qualquer worker existir —
    nesse momento nenhuma linha 'processing' pode legitimamente estar a ser
    trabalhada.
    """
    if 'status' not in df.columns:
        return 0

    csv_basename = os.path.basename(credentials_file)
    reclaimed = 0
    for idx in df.index:
        username = str(df.at[idx, 'username']).strip()
        status = _norm_csv_status(df.at[idx, 'status'])
        if status != 'processing' or not username:
            continue

        ok = update_csv_status(
            username, 'false', csv_basename,
            expected_old_status='processing',
        )
        if ok:
            df.at[idx, 'status'] = 'false'
            reclaimed += 1
            logger.info(
                f"[Recovery] {username}: 'processing' (preso de run anterior) → 'false'"
            )
        else:
            logger.warning(
                f"[Recovery] {username}: não foi possível recuperar de 'processing' "
                "(lock CSV ocupado ou status mudou entretanto)"
            )

    if reclaimed:
        logger.info(
            f"[Recovery] {reclaimed} linha(s) 'processing' recuperadas para 'false'."
        )
    return reclaimed


def _cleanup_interrupted_user_state(
    username: str,
    credentials_file: str,
    redis_client=None,
    reset_status: str = "false",
) -> bool:
    """Limpa estado deixado por um worker interrompido a meio.

    Isto cobre o caso em que o processo pai mata workers activos durante o
    shutdown: o `finally` do worker pode não chegar a correr, então o utilizador
    fica preso em `processing`, continua em `wq:active` e ainda segura um lease
    de proxy no Redis.
    """
    username = str(username or "").strip()
    if not username:
        return False

    cleaned = False
    csv_basename = os.path.basename(credentials_file)

    try:
        if update_csv_status(
            username,
            reset_status,
            csv_basename,
            expected_old_status="processing",
        ):
            logger.info(
                f"[Recovery] {username}: cleanup de interrupcao "
                f"'processing' -> '{reset_status}'"
            )
            cleaned = True
    except Exception as csv_err:
        logger.warning(
            f"[Recovery] {username}: falha a limpar CSV apos interrupcao: {csv_err}"
        )

    if redis_client:
        try:
            redis_client.srem(_WQ_ACTIVE, username)
            redis_client.srem(_WQ_KNOWN, username)
            redis_client.lrem(_WQ_PENDING, 0, username)
            redis_client.delete(_WQ_ATTEMPTS.format(username))
            redis_client.delete(_WQ_PROCESSING.format(username))
            for lease_key in redis_client.scan_iter("plm:lease:*"):
                if redis_client.get(lease_key) == username:
                    redis_client.delete(lease_key)
                    logger.info(
                        f"[Recovery] {username}: lease de proxy libertado ({lease_key})"
                    )
        except Exception as redis_err:
            logger.warning(
                f"[Recovery] {username}: falha a limpar estado Redis apos interrupcao: "
                f"{redis_err}"
            )

    return cleaned


def _is_ip_banned_http_error(err: str) -> bool:
    """403 no POST /login — mesma rotação de chave CAPTCHA não resolve."""
    el = err.lower()
    return "403" in el and ("banned" in el or "proxy/ip" in el)


def _is_site_unavailable_error(err: str) -> bool:
    s = _normalize_server_text(err)
    if not s:
        return False
    sl = s.lower()
    return (
        "manutenção/indisponibilidade" in sl
        or "manutencao/indisponibilidade" in sl
        or _is_mne_service_unavailable_text(s)
    )


def _is_proxy_provider_quota_error(err: str) -> bool:
    """Webshare/proxy-provider quota or billing exhaustion before reaching MNE."""
    s = _normalize_server_text(err).lower()
    return (
        "response 402" in s
        or " 402" in s
        or "402 payment" in s
        or "bandwidth" in s and ("exhaust" in s or "allowance" in s or "quota" in s)
        or "you've used up all your bandwidth" in s
    )


def _login_fatal_skip_captcha_key_rotate(err: str) -> bool:
    return (
        _is_server_login_rejection(err)
        or _is_ip_banned_http_error(err)
        or _is_site_unavailable_error(err)
        or _is_proxy_provider_quota_error(err)
    )


def _is_recaptcha_quota_exhausted_msg(err: str) -> bool:
    """Site MNE: esgotou tentativas de ReCaptcha (ex.: '0 tentativas')."""
    e = err.lower()
    return "0 tentativas" in e or "mais 0 tentativas" in e


def _extract_remaining_recaptcha_attempts(err: str) -> Optional[int]:
    """Extrai o número de tentativas restantes do texto do servidor, quando existir."""
    try:
        m = re.search(r"(?:mais|de mais)\s+(\d+)\s+tentativas?", str(err).lower())
        if m:
            return int(m.group(1))
    except Exception:
        pass
    return None


def _is_soft_recaptcha_server_warning(err: str) -> bool:
    """ReCaptchaError do MNE com tentativas ainda restantes: pausar, não tratar como bloqueio total."""
    e = str(err).lower()
    if "recaptchaerror" not in e:
        return False
    remaining = _extract_remaining_recaptcha_attempts(e)
    return remaining is not None and remaining > 0


def _normalize_server_text(text: Optional[str]) -> str:
    """
    Corrige mojibake comum do servidor/login (ex.: 'DispÃµe' -> 'Dispõe')
    sem mexer em strings ASCII normais.
    """
    s = str(text or "")
    if not s:
        return ""
    if not any(marker in s for marker in ("Ã", "Â", "â", "€", "™")):
        return s
    try:
        fixed = s.encode("latin-1", errors="ignore").decode("utf-8", errors="ignore")
        return fixed or s
    except Exception:
        return s


def _short_normalized_text(text: Optional[str], limit: int = 180) -> str:
    s = re.sub(r"\s+", " ", _normalize_server_text(text)).strip()
    if len(s) <= limit:
        return s
    return s[: max(0, limit - 3)].rstrip() + "..."


def _is_mne_service_unavailable_text(text: Optional[str]) -> bool:
    s = _normalize_server_text(text).lower()
    if not s:
        return False
    has_unavailable = (
        "serviço indisponível" in s
        or "servico indisponivel" in s
        or "service unavailable" in s
    )
    has_maintenance = (
        "serviço em manutenção" in s
        or "servico em manutencao" in s
        or "please visit again later" in s
    )
    return has_unavailable or has_maintenance


async def _page_service_unavailable_snapshot(page) -> tuple[bool, str, str]:
    title = ""
    visible_text = ""
    try:
        title = _normalize_server_text(await page.title())
    except Exception:
        pass
    try:
        visible_text = await page.evaluate(
            """() => {
                const body = document.body;
                const t = body && body.innerText ? body.innerText : "";
                return t.slice(0, 4000);
            }"""
        )
    except Exception:
        visible_text = ""
    visible_text = _normalize_server_text(visible_text)
    combined = "\n".join(part for part in (title, visible_text) if part)
    return _is_mne_service_unavailable_text(combined), title, visible_text


def _is_direct_proxy(proxy_raw: Optional[str]) -> bool:
    """True se httpx/Playwright devem usar rede direta (sem proxy HTTP)."""
    if not proxy_raw:
        return True
    return str(proxy_raw).strip() in (DIRECT_PROXY_MARKER, "DIRECT")


def _proxy_log_label(proxy_raw: Optional[str]) -> str:
    if _is_direct_proxy(proxy_raw):
        return "direct"
    try:
        return str(proxy_raw).split(":")[0]
    except Exception:
        return "?"


def _proxy_safe_label(proxy_raw: Optional[str]) -> str:
    """Human-readable proxy label without exposing the proxy password."""
    parsed = _parse_proxy_raw(proxy_raw)
    if not parsed:
        return _proxy_log_label(proxy_raw)
    host, port, username, _ = parsed
    if len(username) <= 10:
        safe_user = username
    else:
        safe_user = f"{username[:6]}...{username[-4:]}"
    return f"{host}:{port}:{safe_user}"


def _parse_proxy_raw(proxy_raw: Optional[str]) -> Optional[Tuple[str, str, str, str]]:
    """Parse bot proxy format as host:port:username:password."""
    if _is_direct_proxy(proxy_raw):
        return None
    parts = str(proxy_raw or "").strip().split(":", 3)
    if len(parts) != 4:
        return None
    host, port, username, password = (part.strip() for part in parts)
    if not host or not port or not username or not password:
        return None
    return host, port, username, password


def _proxy_to_http_url(proxy_raw: str) -> Optional[str]:
    parsed = _parse_proxy_raw(proxy_raw)
    if not parsed:
        return None
    host, port, username, password = parsed
    scheme = "http"
    try:
        if scraper_settings is not None:
            scheme = str(scraper_settings.get("proxy_scheme") or scheme).strip().lower()
    except Exception:
        pass
    if scheme not in ("http", "https", "socks5", "socks5h"):
        scheme = "http"
    return f"{scheme}://{quote(username, safe='')}:{quote(password, safe='')}@{host}:{port}"


def _proxy_to_playwright_config(proxy_raw: Optional[str]) -> Optional[Dict[str, str]]:
    parsed = _parse_proxy_raw(proxy_raw)
    if not parsed:
        return None
    host, port, username, password = parsed
    scheme = "http"
    try:
        if scraper_settings is not None:
            scheme = str(scraper_settings.get("proxy_scheme") or scheme).strip().lower()
    except Exception:
        pass
    if scheme not in ("http", "https", "socks5", "socks5h"):
        scheme = "http"
    return {
        "server": f"{scheme}://{host}:{port}",
        "username": username,
        "password": password,
    }


def _cookie_pool_key(proxy_raw: Optional[str], username: Optional[str] = None) -> str:
    """
    Key for cookie/session reuse.
    In direct mode, isolate by username to avoid leaking one account's cookies
    into another account on the same local IP.
    """
    if _is_direct_proxy(proxy_raw):
        safe_user = re.sub(r"[^\w\-.]+", "_", str(username or "direct"))[:80]
        return f"{DIRECT_PROXY_MARKER}:{safe_user}"
    return str(proxy_raw or "")

PDF_SUCCESS_SENTINEL = "PDF_SUCCESS"
_shutdown_signal_seen = False


def _raise_keyboard_interrupt_on_signal(signum, _frame):
    global _shutdown_signal_seen
    if _shutdown_signal_seen:
        return
    _shutdown_signal_seen = True
    for sig in (getattr(signal, "SIGTERM", None), getattr(signal, "SIGINT", None)):
        if sig is None:
            continue
        try:
            signal.signal(sig, signal.SIG_IGN)
        except Exception:
            pass
    try:
        signame = signal.Signals(signum).name
    except Exception:
        signame = str(signum)
    raise KeyboardInterrupt(f"Received {signame}")


def _install_graceful_signal_handlers():
    for sig in (getattr(signal, "SIGTERM", None), getattr(signal, "SIGINT", None)):
        if sig is None:
            continue
        try:
            signal.signal(sig, _raise_keyboard_interrupt_on_signal)
        except Exception:
            pass


def _force_stop_process_pool(executor, grace_seconds: float = 3.0) -> tuple[int, int]:
    processes = list((getattr(executor, "_processes", {}) or {}).values())
    live = [p for p in processes if p is not None and p.is_alive()]
    if not live:
        return 0, 0

    terminated = 0
    killed = 0

    if os.name == "nt":
        # On Windows, ProcessPool workers can leave Playwright Chrome children
        # behind if only the Python process is terminated. Kill the whole tree.
        for proc in live:
            pid = getattr(proc, "pid", None)
            if not pid:
                continue
            try:
                result = subprocess.run(
                    ["taskkill", "/PID", str(pid), "/T", "/F"],
                    capture_output=True,
                    text=True,
                    timeout=20,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                    check=False,
                )
                if result.returncode == 0:
                    killed += 1
            except Exception:
                pass
        for proc in live:
            try:
                proc.join(timeout=0.5)
            except Exception:
                pass
        return 0, killed

    for proc in live:
        try:
            proc.terminate()
            terminated += 1
        except Exception:
            pass

    deadline = time.time() + max(0.1, float(grace_seconds))
    for proc in live:
        try:
            remaining = max(0.0, deadline - time.time())
            proc.join(timeout=remaining)
        except Exception:
            pass

    survivors = [p for p in live if p.is_alive()]
    for proc in survivors:
        try:
            proc.kill()
            killed += 1
        except Exception:
            pass

    for proc in survivors:
        try:
            proc.join(timeout=0.5)
        except Exception:
            pass

    return terminated, killed


class PostLoginFailure(RuntimeError):
    """Raised when the MNE server has already accepted POST /login for this
    session but a *downstream* step (cookies / Questionario / Formulario /
    second form / PDF) failed.

    Callers MUST NOT retry the full login flow for this user on the same run:
    repeating the CAPTCHA + POST /login with the same account within a short
    window is what triggers the MNE WAF to escalate from a soft warning to a
    hard block, and it also wastes paid CAPTCHA solver credits.
    """
    pass


class CaptchaTokenExpired(RuntimeError):
    """Raised when a reCAPTCHA token returned by the solver is already older
    than Google's 120s validity window by the time we are about to submit it.

    The MNE backend forwards the token to Google for verification and Google
    answers ``expired-input-response``; MNE then returns the catch-all
    ``{"type":"error","description":"Foi encontrado um erro ao executar a
    operação."}`` JSON which is INDISTINGUISHABLE from a poisoned-proxy
    rejection. By raising this BEFORE the POST we:

      * never burn a doomed POST /login (saves rate-limit pressure on MNE),
      * never falsely increment the per-proxy server-rejection counter
        (the proxy is innocent — it's the slow solver to blame),
      * surface the real cause in the logs so the operator can see the
        solver SLA is degraded.
    """
    pass


class LoginPostSubmittedFailure(RuntimeError):
    """Raised when `POST /login` was already sent by the browser, but the
    outcome failed before we got a trustworthy application response.

    Typical case: Playwright emits `requestfailed` with
    `net::ERR_EMPTY_RESPONSE` after the login POST was captured. At that
    point, firing a brand-new CAPTCHA + POST /login for the same account in
    the same run is unsafe: the first POST may already have reached the MNE
    edge/server and a second immediate login tends to look like automation.

    Callers should stop retrying the full login flow for this user in the
    current run, park the account in `failed_retry_later`, and penalize the
    proxy that dropped the submitted request.
    """
    pass


def _post_login_failure_allows_full_retry(exc: Exception) -> bool:
    """
    A maioria das falhas pós-login NÃO deve repetir o fluxo completo, porque
    isso gasta outro CAPTCHA e tende a disparar o WAF. Excepção limitada:
    `/Questionario` a devolver a página "Perdeu a sessão" mesmo após login
    aceite. Esse estado pode ser transitório/proxy-side, por isso permitimos
    UMA nova tentativa completa noutro proxy.
    """
    msg = str(exc).lower()
    return (
        "sessão perdida ao abrir questionario" in msg
        or "sessao perdida ao abrir questionario" in msg
        or (
            "questionario" in msg
            and "perdeu a sessão" in msg
        )
    )


# =================================================================================
# MONITORIZAÇÃO CAPTCHA — Estatísticas em tempo real
# =================================================================================
import threading as _threading
_captcha_stats_lock = _threading.Lock()
captcha_stats = {
    "anti-captcha": {"solved": 0, "failed": 0, "total_time": 0.0, "wins": 0},
    "2captcha":     {"solved": 0, "failed": 0, "total_time": 0.0, "wins": 0},
    "capmonster":   {"solved": 0, "failed": 0, "total_time": 0.0, "wins": 0},
    "capsolver":    {"solved": 0, "failed": 0, "total_time": 0.0, "wins": 0},
}

def _captcha_record(provider: str, success: bool, elapsed: float, winner: bool = False):
    """Regista estatísticas de um solve de CAPTCHA."""
    with _captcha_stats_lock:
        s = captcha_stats.get(provider)
        if s is None:
            return
        if success:
            s["solved"] += 1
            s["total_time"] += elapsed
            if winner:
                s["wins"] += 1
        else:
            s["failed"] += 1

def captcha_stats_report() -> str:
    """Devolve um relatório formatado das estatísticas."""
    lines = ["\n📊 CAPTCHA STATS:"]
    with _captcha_stats_lock:
        for provider, s in captcha_stats.items():
            total = s["solved"] + s["failed"]
            if total == 0:
                continue
            avg = s["total_time"] / s["solved"] if s["solved"] > 0 else 0
            rate = (s["solved"] / total * 100) if total > 0 else 0
            lines.append(
                f"  {provider:15s} | solves={s['solved']:3d} | fails={s['failed']:3d} "
                f"| avg={avg:5.1f}s | win={s['wins']:3d} | rate={rate:5.1f}%"
            )
    return "\n".join(lines)
# =================================================================================
# =================================================================================
# NOVO GESTOR DE ESTADO (REDIS) - ALTA PERFORMANCE
# =================================================================================
# Configuração do Redis
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))

class StateManager:
    def __init__(self):
        self.r = None
        try:
            self.r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
            self.r.ping()
            safe_print("[Redis] ✅ Conectado.")
        except Exception as e:
            self.r = None
            safe_print(f"[Redis] ❌ Erro: {e}. Continuando sem persistência distribuída.")

    # --- JAIL ---
    def is_user_jailed(self, username: str) -> bool:
        if not self.r: return False
        return self.r.exists(f"jail:{username}")

    def send_to_jail(self, username: str, duration_minutes: float = 10):
        if not self.r: return
        ex_seconds = max(1, int(duration_minutes * 60))
        self.r.set(f"jail:{username}", "1", ex=ex_seconds)
        safe_print(f"[Jail] 🚨 {username} preso por {duration_minutes} min ({ex_seconds}s).")
    def check_and_burn_bad_proxy(self, proxy_raw: str, error_type: str):
        """Analisa o erro e decide se queima o proxy imediatamente.
        FIX: Ban proporcional — 403 isolado = 10 min, reincidente = 30 min."""
        if not self.r: return
        
        key_score = f"proxy_score:{proxy_raw}"
        key_ban   = f"proxy_banned:{proxy_raw}"
        key_403   = f"proxy_403count:{proxy_raw}"

        # Se deu 403 ou Cloudflare — ban proporcional ao numero de incidentes
        if "403" in error_type or "cloudflare" in error_type.lower() or error_type == "banned":
            # Contar 403s nas ultimas 2 horas
            count = self.r.incr(key_403)
            self.r.expire(key_403, 7200)  # janela de 2 horas

            # 1 incidente → 10 min | 2-3 → 20 min | 4+ → 30 min
            if count <= 1:
                ban_secs = 600     # 10 min
            elif count <= 3:
                ban_secs = 1200    # 20 min
            else:
                ban_secs = 1800    # 30 min

            self.r.set(key_ban, "1", ex=ban_secs)
            self.r.set(key_score, -100)
            safe_print(
                f"[AntiBan] 🔥 Proxy {proxy_raw[:15]} BANIDO por {ban_secs//60}min "
                f"(incidente #{count}, motivo: {error_type})"
            )
        
        # Timeout ou conexao falhou — penaliza levemente, nao bane
        elif "timeout" in error_type.lower() or "connection" in error_type.lower():
            self.r.incrby(key_score, -10)

    # --- PROXY SCORES ---
    def update_proxy_score(self, proxy_raw: str, delta: int, latency_ms: int = 0):
        if not self.r: return 0
        
        key = f"proxy_score:{proxy_raw}"
        
        # 1. Aplica o delta (pontos base)
        new_score = self.r.incrby(key, delta)
        
        # 2. Bónus de Velocidade (Elite)
        # Se o proxy foi rápido (ex: < 500ms), damos pontos extra.
        # Se foi lento (> 1000ms), removemos pontos.
        if latency_ms > 0:
            if latency_ms < 300:
                self.r.incrby(key, 5) # Muito rápido: +5 extra
            elif latency_ms < 600:
                self.r.incrby(key, 2) # Rápido: +2 extra
            elif latency_ms > 1500:
                self.r.incrby(key, -3) # Lento: -3 (penalizado)
                
        return new_score
    
        # --- ADICIONAR DENTRO DA CLASSE StateManager ---
    
    def check_proxy_burn(self, proxy_raw: str, failure_window_sec: int = 300) -> bool:
        """Verifica se o proxy está 'queimando' (muitas falhas recentes)."""
        if not self.r: return False
        
        key = f"proxy_fails:{proxy_raw}"
        
        # Incrementa contador de falhas
        fails = self.r.incr(key)
        # Expira em X segundos (janela de tempo)
        self.r.expire(key, failure_window_sec)
        
        # Se falhou mais de 3 vezes nos últimos 5 minutos -> BAN temporário
        if fails > 3:
            self.r.set(f"proxy_banned:{proxy_raw}", "1", ex=600) # Ban por 10 min
            safe_print(f"[Burn] 🔥 Proxy {proxy_raw[:15]} queimado. Banido por 10 min.")
            return True
        return False

    def is_proxy_banned(self, proxy_raw: str) -> bool:
        """Verifica se o proxy está atualmente banido."""
        if not self.r: return False
        return self.r.exists(f"proxy_banned:{proxy_raw}")

    def get_best_proxy(self, proxy_list: list) -> str:
        if not self.r or not proxy_list: return random.choice(proxy_list) if proxy_list else None
        
        # FIX: Filtrar proxies banidos ANTES de ordenar por score
        # Um proxy banido nunca deve ser escolhido independentemente do seu score
        active_proxies = [p for p in proxy_list if not self.is_proxy_banned(p)]
        if not active_proxies:
            safe_print("[Proxy] ⚠️ Todos os proxies estao banidos temporariamente. Usando qualquer um.")
            active_proxies = proxy_list  # Fallback — usar mesmo que banido
        
        # Busca scores de uma vez só (Pipeline)
        pipe = self.r.pipeline()
        for p in active_proxies: pipe.get(f"proxy_score:{p}")
        scores = pipe.execute()
        
        # Ordena por score descrescente
        scored = list(zip(active_proxies, scores))
        scored.sort(key=lambda x: int(x[1] or 0), reverse=True)
        
        # Retorna o melhor com score nao negativo
        for p, s in scored:
            if int(s or 0) >= 0: return p
        
        return random.choice(active_proxies)  # Fallback

# Instancia global (inicializada no worker)
state_manager = None

# =================================================================================
# PROXY LEASE MANAGER
# Garante exclusividade 1 proxy : 1 utilizador em cada momento.
# =================================================================================
# PROXY LEASE MANAGER — GARANTIA ABSOLUTA 1 PROXY : 1 UTILIZADOR
#
# Regras imutaveis:
#   1. Cada utilizador tem SEMPRE um proxy dedicado — nenhum outro user partilha
#   2. Proxy com ban 403 e banido por 30 min automaticamente
#   3. Proxy com falhas repetidas e banido progressivamente (5m → 15m → 60m)
#   4. Rotatividade uniforme: proxy com menos usos historicos e preferido
#   5. Estado persistido no Redis (cross-process); fallback in-memory
#   6. Libertar proxy no finally de process_single_user — sem fugas
# =================================================================================
class ProxyLeaseManager:
    """
    Gestor de arrendamento exclusivo de proxies.

    Garante que dois utilizadores NUNCA partilham o mesmo IP simultaneamente.
    Usa Redis com SET NX (atomic) para evitar race conditions entre processos.
    """

    # TTLs de lease e ban
    _LEASE_TTL_S    = 600   # 10 min — renovado a cada uso
    _BAN_403_S      = 1800  # 30 min para 403/Cloudflare
    _BAN_REPEAT_S   = [15, 60, 300]   # 15s, 1m, 5m para falhas de ligação
    _BAN_RECAPTCHA_SOFT_S  = 180      # 3 min para ReCaptchaError com tentativas restantes
    _BAN_RECAPTCHA_QUOTA_S = 600      # 10 min para quota esgotada (0 tentativas)

    # Chaves Redis
    _K_LEASE        = "plm:lease:{}"      # valor = username
    _K_USER         = "plm:user:{}"       # valor = proxy_raw
    _K_BAN          = "plm:ban:{}"        # valor = "1"
    _K_FAILS        = "plm:fails:{}"      # valor = contador
    _K_USES         = "plm:uses:{}"       # valor = total usos historicos
    _K_SCORE        = "plm:score:{}"      # valor = score de qualidade
    _K_SREJ         = "plm:srej:{}"       # valor = contador de server rejections
    _SREJ_WINDOW_S  = 3600                # janela de 1h para acumular rejeições

    def __init__(self, redis_client=None):
        self._r    = redis_client
        self._lock = threading.Lock()
        # Fallback in-memory (por processo)
        self._leases:     Dict[str, str] = {}  # proxy -> username
        self._user_proxy: Dict[str, str] = {}  # username -> proxy
        self._banned_mem: Dict[str, float] = {}  # proxy -> ban_until timestamp
        self._uses_mem:   Dict[str, int] = {}  # proxy -> total uses in this process

    # ─────────────────────────────────────────────────────────────────────────
    # INTERFACE PUBLICA
    # ─────────────────────────────────────────────────────────────────────────

    def acquire(self, username: str, proxy_list: list, ignore_ban: bool = False) -> Optional[str]:
        """
        Adquire proxy EXCLUSIVO para este utilizador.
        Retorna o proxy_raw ou None se nenhum estiver livre.
        Thread-safe e process-safe via Redis NX.
        """
        if self._r:
            try:
                return self._acquire_redis(username, proxy_list, ignore_ban=ignore_ban)
            except Exception as e:
                safe_print(f"[PLM] Redis acquire erro: {e} — usando memory")
        return self._acquire_memory(username, proxy_list, ignore_ban=ignore_ban)

    def release(self, username: str):
        """Liberta o proxy deste utilizador. Chamar sempre no finally."""
        if self._r:
            try:
                self._release_redis(username)
                return
            except Exception as e:
                safe_print(f"[PLM] Redis release erro: {e}")
        self._release_memory(username)

    def ban_proxy(self, proxy_raw: str, reason: str = "403"):
        """
        Bane o proxy por um periodo baseado no motivo.
        403/cloudflare/server_rejection = 30 min. Falhas repetidas = progressivo.
        """
        if _is_direct_proxy(proxy_raw):
            return
        if reason in ("403", "cloudflare", "banned", "server_rejection_streak"):
            ttl = self._BAN_403_S
        elif reason == "recaptcha_server_soft":
            ttl = self._BAN_RECAPTCHA_SOFT_S
        elif reason == "recaptcha_server_quota":
            ttl = self._BAN_RECAPTCHA_QUOTA_S
        elif reason == "site_unavailable":
            ttl = max(60, _cfg_int("proxy_ban_seconds_on_site_unavailable", 300))
        else:
            # Ler numero de falhas para decidir o nivel de ban
            fails = self._get_fail_count(proxy_raw)
            idx   = min(fails, len(self._BAN_REPEAT_S) - 1)
            ttl   = self._BAN_REPEAT_S[idx]
            self._incr_fail_count(proxy_raw)

        if self._r:
            try:
                self._r.set(self._K_BAN.format(proxy_raw), "1", ex=ttl)
                _pid = ":".join(proxy_raw.split(":")[:2])
                safe_print(
                    f"[PLM] 🚫 BAN {_pid} "
                    f"por {ttl//60}min (motivo={reason})"
                )
                return
            except Exception:
                pass
        # Fallback memory
        with self._lock:
            self._banned_mem[proxy_raw] = time.time() + ttl
            _pid = _proxy_safe_label(proxy_raw)
            safe_print(
                f"[PLM] 🚫 BAN(mem) {_pid} "
                f"por {ttl}s (motivo={reason})"
            )

    def rotate(self, username: str, bad_proxy: str, proxy_list: list,
               reason: str = "error") -> Optional[str]:
        """
        Liberta o proxy mau, bane-o e adquire um novo para o utilizador.
        Filtra proxies banidos antes de tentar acquire.
        Retorna o novo proxy ou None se nao houver alternativa.
        """
        self.ban_proxy(bad_proxy, reason)
        self.release(username)
        # Filtrar: excluir o proxy banido E todos os outros ja banidos
        available = [p for p in proxy_list
                     if p != bad_proxy and not self.is_banned(p)]
        ignore_ban = False
        if not available:
            # Fallback real apenas para falhas "soft" (timeout/connection/ssl/http_error):
            # tentar proxies actualmente em soft-ban como ÚLTIMO recurso.
            # Isto evita o dead-end em pools pequenos (1-2 proxies), onde um
            # timeout transitório acabava por esgotar a pool inteira por lógica
            # interna do bot. Para bans "hard" (403 / server rejection streak),
            # NUNCA ignorar o ban.
            allow_soft_last_resort = reason not in (
                "403", "cloudflare", "banned", "server_rejection_streak"
            )
            fallback_all = [p for p in proxy_list if p != bad_proxy]
            if allow_soft_last_resort and fallback_all:
                available = fallback_all
                ignore_ban = True
                safe_print(
                    f"[PLM] ⚠️ Todos os {len(proxy_list)} proxies banidos — "
                    f"tentando {len(available)} sem filtro ban "
                    f"(ultimo recurso para falha soft: {reason})"
                )
            else:
                safe_print(f"[PLM] ⚠️ Sem proxies alternativos para {username}")
                return None
        new_proxy = self.acquire(username, available, ignore_ban=ignore_ban)
        # Log com ip:port para nao enganar quando hostname e o mesmo
        _bad_id  = ":".join(bad_proxy.split(":")[:2]) if bad_proxy else "?"
        _new_id  = ":".join(new_proxy.split(":")[:2]) if new_proxy else "NENHUM"
        safe_print(
            f"[PLM] ROTATE {username}: "
            f"{_bad_id} -> {_new_id} "
            f"(motivo={reason})"
        )
        return new_proxy

    def current_proxy_of(self, username: str) -> Optional[str]:
        """Devolve o proxy actualmente arrendado a `username`, ou None."""
        if self._r:
            try:
                val = self._r.get(self._K_USER.format(username))
                return val if val else None
            except Exception:
                pass
        with self._lock:
            return self._user_proxy.get(username)

    def record_server_rejection(self, username: str, threshold: int = 3) -> bool:
        """
        Regista uma rejeição genérica do servidor para o proxy actualmente
        arrendado a este utilizador (mensagem do tipo "Foi encontrado um erro
        ao executar a operação." retornada pelo POST /login do MNE).

        Cada proxy tem um contador (chave `plm:srej:{proxy}`) com janela de
        1 hora. Quando o contador chega a `threshold`, o proxy é banido por
        30 minutos como `server_rejection_streak`. Isto evita continuar a
        gastar solves de CAPTCHA num proxy que o MNE já decidiu silenciar.

        Devolve True se o proxy foi banido nesta chamada.
        """
        proxy = self.current_proxy_of(username)
        if not proxy or _is_direct_proxy(proxy):
            return False

        count = 0
        if self._r:
            try:
                key = self._K_SREJ.format(proxy)
                count = self._r.incr(key)
                if count == 1:
                    self._r.expire(key, self._SREJ_WINDOW_S)
            except Exception:
                count = 0

        if count == 0:
            with self._lock:
                self._banned_mem.setdefault(proxy + ":__srej_meta__", 0.0)
                # Mirror em memória (best-effort): contar via _user_proxy/_leases
                # não é fiável cross-process, mas serve como fallback local.
                attr = getattr(self, "_srej_mem", None)
                if attr is None:
                    self._srej_mem = {}
                count = self._srej_mem.get(proxy, 0) + 1
                self._srej_mem[proxy] = count

        _pid = ":".join(proxy.split(":")[:2])
        safe_print(
            f"[PLM] ⚠️ SERVER-REJECTION counter {_pid} = {count}/{threshold} "
            f"(janela {self._SREJ_WINDOW_S//60}min, user={username})"
        )

        if count >= threshold:
            self.ban_proxy(proxy, reason="server_rejection_streak")
            safe_print(
                f"[PLM] 🛑 QUARENTENA {_pid}: {count} rejeições genéricas em "
                f"<{self._SREJ_WINDOW_S//60}min — provavelmente bloqueado pelo MNE. "
                f"Não será usado por 30min para poupar CAPTCHAs."
            )
            return True
        return False

    def is_banned(self, proxy_raw: str) -> bool:
        """Verifica se o proxy esta banido."""
        if self._r:
            try:
                return bool(self._r.exists(self._K_BAN.format(proxy_raw)))
            except Exception:
                pass
        with self._lock:
            until = self._banned_mem.get(proxy_raw, 0)
            return time.time() < until

    def stats(self) -> str:
        if self._r:
            try:
                leases = len(self._r.keys("plm:lease:*"))
                bans   = len(self._r.keys("plm:ban:*"))
                return f"[PLM] {leases} proxies em uso | {bans} bans totais no Redis"
            except Exception:
                pass
        with self._lock:
            bans = sum(1 for t in self._banned_mem.values() if time.time() < t)
            return (f"[PLM] {len(self._leases)} em uso | "
                    f"{bans} banidos (memory)")

    # ─────────────────────────────────────────────────────────────────────────
    # IMPLEMENTACAO REDIS
    # ─────────────────────────────────────────────────────────────────────────

    def _acquire_redis(self, username: str, proxy_list: list, ignore_ban: bool = False) -> Optional[str]:
        # 1. Verificar se ja tem proxy arrendado e ainda valido
        user_key = self._K_USER.format(username)
        existing = self._r.get(user_key)
        if existing and existing in proxy_list:
            lease_key = self._K_LEASE.format(existing)
            if self._r.get(lease_key) == username and (ignore_ban or not self.is_banned(existing)):
                # Renovar TTL
                self._r.expire(lease_key, self._LEASE_TTL_S)
                self._r.expire(user_key,  self._LEASE_TTL_S)
                return existing

        # 2. Recolher estado de todos os proxies em pipeline (1 RTT)
        pipe = self._r.pipeline()
        for p in proxy_list:
            pipe.get(self._K_LEASE.format(p))   # owner
            pipe.exists(self._K_BAN.format(p))  # banido?
            pipe.get(self._K_USES.format(p))    # usos historicos
        results = pipe.execute()

        # 3. Construir lista de candidatos livres e nao banidos
        candidates = []
        for i, p in enumerate(proxy_list):
            owner  = results[i * 3]
            banned = results[i * 3 + 1]
            uses   = int(results[i * 3 + 2] or 0)
            if banned and not ignore_ban:
                continue  # proxy banido — saltar
            if owner and owner != username:
                continue  # ocupado por outro utilizador
            candidates.append((p, uses))

        if not candidates:
            safe_print(
                f"[PLM] ⚠️ SEM PROXIES LIVRES para {username} "
                f"({len(proxy_list)} total)"
            )
            return None

        # 4. Ordenar por menor numero de usos (rotatividade uniforme)
        candidates.sort(key=lambda x: x[1])

        # 5. Tentar adquirir atomicamente com SET NX
        for chosen, _ in candidates:
            lease_key = self._K_LEASE.format(chosen)
            # SET NX = atomico — so 1 processo ganha
            ok = self._r.set(lease_key, username,
                             ex=self._LEASE_TTL_S, nx=True)
            if ok:
                self._r.set(user_key, chosen, ex=self._LEASE_TTL_S)
                self._r.incr(self._K_USES.format(chosen))
                safe_print(
                    f"[PLM] ✅ ACQUIRED {username} -> "
                    f"{chosen.split(':')[0]} (usos={_})"
                )
                return chosen

        safe_print(f"[PLM] Race condition: todos os candidatos tomados. Retry.")
        return None

    def _release_redis(self, username: str):
        user_key = self._K_USER.format(username)
        proxy    = self._r.get(user_key)
        if not proxy:
            return
        lease_key = self._K_LEASE.format(proxy)
        # So apagar o lease se ainda for deste utilizador
        owner = self._r.get(lease_key)
        if owner == username:
            self._r.delete(lease_key)
        self._r.delete(user_key)
        safe_print(f"[PLM] 🔓 RELEASED {username} -> {proxy.split(':')[0]}")

    # ─────────────────────────────────────────────────────────────────────────
    # IMPLEMENTACAO IN-MEMORY (fallback por processo)
    # ─────────────────────────────────────────────────────────────────────────

    def _acquire_memory(self, username: str, proxy_list: list, ignore_ban: bool = False) -> Optional[str]:
        with self._lock:
            # Verificar arrendamento existente
            existing = self._user_proxy.get(username)
            if (existing and existing in proxy_list
                    and self._leases.get(existing) == username
                    and (ignore_ban or not self._is_banned_mem(existing))):
                return existing

            # Construir candidatos
            candidates = []
            for p in proxy_list:
                if self._is_banned_mem(p) and not ignore_ban:
                    continue
                owner = self._leases.get(p)
                if owner and owner != username:
                    continue
                candidates.append((p, self._uses_mem.get(p, 0), random.random()))

            if not candidates:
                return None

            candidates.sort(key=lambda item: (item[1], item[2]))
            chosen = candidates[0][0]
            self._leases[chosen]       = username
            self._user_proxy[username] = chosen
            self._uses_mem[chosen] = self._uses_mem.get(chosen, 0) + 1
            return chosen

    def _release_memory(self, username: str):
        with self._lock:
            proxy = self._user_proxy.pop(username, None)
            if proxy and self._leases.get(proxy) == username:
                self._leases.pop(proxy, None)

    def _is_banned_mem(self, proxy_raw: str) -> bool:
        until = self._banned_mem.get(proxy_raw, 0)
        return time.time() < until

    # ─────────────────────────────────────────────────────────────────────────
    # AUXILIARES
    # ─────────────────────────────────────────────────────────────────────────

    def _get_fail_count(self, proxy_raw: str) -> int:
        if self._r:
            try:
                v = self._r.get(self._K_FAILS.format(proxy_raw))
                return int(v or 0)
            except Exception:
                pass
        return 0

    def _incr_fail_count(self, proxy_raw: str):
        if self._r:
            try:
                key = self._K_FAILS.format(proxy_raw)
                self._r.incr(key)
                self._r.expire(key, 3600)  # reset apos 1h sem falhas
            except Exception:
                pass

proxy_lease_manager: Optional[ProxyLeaseManager] = None

# =================================================================================
# MELHORIA 3.1 — CAPTCHARouter: monitorizacao em tempo real por provider
# =================================================================================
class CAPTCHARouter:
    """
    Monitoriza solve time e success rate de cada provider em tempo real.
    get_best_service() devolve o provider mais rapido com success rate >= 80%.
    Thread-safe via threading.Lock.
    """
    def __init__(self):
        self._lock = threading.Lock()
        self.services: Dict[str, Dict] = {
            "anti-captcha": {"total": 0, "solved": 0, "total_time": 0.0, "cost_per": 0.003},
            "2captcha":     {"total": 0, "solved": 0, "total_time": 0.0, "cost_per": 0.003},
            "capmonster":   {"total": 0, "solved": 0, "total_time": 0.0, "cost_per": 0.002},
            "capsolver":    {"total": 0, "solved": 0, "total_time": 0.0, "cost_per": 0.002},
        }

    def record(self, provider: str, success: bool, elapsed: float):
        with self._lock:
            s = self.services.get(provider)
            if s is None:
                return
            s["total"] += 1
            if success:
                s["solved"] += 1
                s["total_time"] += elapsed

    def get_best_service(self, available: list) -> Optional[str]:
        """
        Devolve o nome do melhor provider disponivel.
        Criterio: menor avg_time entre os com success_rate >= 0.80.
        """
        with self._lock:
            candidates = []
            for name in available:
                s = self.services.get(name)
                if not s or s["total"] == 0:
                    continue
                rate = s["solved"] / s["total"]
                avg  = s["total_time"] / s["solved"] if s["solved"] > 0 else 9999.0
                candidates.append((name, rate, avg))
            if not candidates:
                return None
            good = [(n, r, a) for n, r, a in candidates if r >= 0.80]
            if good:
                return min(good, key=lambda x: x[2])[0]
            return max(candidates, key=lambda x: x[1])[0]

    def report(self) -> str:
        lines = ["\n📊 CAPTCHARouter Stats:"]
        with self._lock:
            for name, s in self.services.items():
                if s["total"] == 0:
                    continue
                rate = s["solved"] / s["total"] * 100
                avg  = s["total_time"] / s["solved"] if s["solved"] > 0 else 0
                lines.append(
                    f"  {name:15s} | ok={s['solved']:3d}/{s['total']:3d} "
                    f"| rate={rate:5.1f}% | avg={avg:5.1f}s"
                )
        return "\n".join(lines)

captcha_router = CAPTCHARouter()

# =================================================================================
# MELHORIA 3.2 — TokenBuffer: pre-solve de tokens CAPTCHA em background
# Mantem um buffer de tokens prontos para injecao instantanea (0s de espera).
# =================================================================================
class TokenBuffer:
    """
    Resolve tokens CAPTCHA em background e guarda-os num asyncio.Queue.
    get_token() devolve instantaneamente se o buffer tiver tokens prontos.
    """
    def __init__(self, proxy_raw: str, user_agent: str,
                 captcha_key_index: int = 0, size: int = 3):
        self.proxy_raw         = proxy_raw
        self.user_agent        = user_agent
        self.captcha_key_index = captcha_key_index
        self._queue: asyncio.Queue = asyncio.Queue(maxsize=size)
        self._running          = False
        self._size             = size

    async def pre_solve_loop(self):
        """Corre indefinidamente em background, mantendo o buffer cheio."""
        self._running = True
        loop = asyncio.get_running_loop()
        try:
            while self._running:
                if self._queue.qsize() < self._size:
                    try:
                        token = await loop.run_in_executor(
                            None,
                            functools.partial(
                                solve_recaptcha_v2,
                                self.proxy_raw,
                                self.user_agent,
                                captcha_key_index=self.captcha_key_index,
                            )
                        )
                        if token:
                            await self._queue.put(token)
                            safe_print(
                                f"[TokenBuffer] token pre-solved "
                                f"(buffer {self._queue.qsize()}/{self._size})"
                            )
                    except Exception as e:
                        safe_print(f"[TokenBuffer] pre-solve falhou: {e}")
                        await asyncio.sleep(5)
                else:
                    await asyncio.sleep(2)
        except asyncio.CancelledError:
            self._running = False

    async def get_token(self, max_wait_s: float = 90.0) -> Optional[str]:
        """Devolve token do buffer; aguarda ate max_wait_s se estiver vazio."""
        try:
            return await asyncio.wait_for(self._queue.get(), timeout=max_wait_s)
        except asyncio.TimeoutError:
            safe_print("[TokenBuffer] Timeout aguardando token pre-solved.")
            return None

    def stop(self):
        self._running = False

_token_buffers: Dict[str, "TokenBuffer"] = {}
_token_buffers_lock = threading.Lock()

def get_or_create_token_buffer(proxy_raw: str, user_agent: str,
                                captcha_key_index: int = 0) -> "TokenBuffer":
    with _token_buffers_lock:
        if proxy_raw not in _token_buffers:
            _token_buffers[proxy_raw] = TokenBuffer(
                proxy_raw, user_agent, captcha_key_index, size=3
            )
        return _token_buffers[proxy_raw]

# =================================================================================
# MELHORIA 3.3 — ProxyCookiePool: emparelhamento 1:1 proxy <-> cookies de sessao
# Reutiliza cookies validos sem criar sessao nova (menos logins = menos detecao).
# Persiste no Redis (TTL 30 min); fallback in-memory se Redis nao disponivel.
# =================================================================================
class ProxyCookiePool:
    """
    Mapeia cookie_pool_key -> {cookies, user_agent, last_used, health}.
    Persiste no Redis com TTL de 30 minutos.
    """
    _KEY_PREFIX  = "cookie_pool:"
    _TTL_SECONDS = 30 * 60

    def __init__(self, redis_client=None):
        self._r = redis_client
        self._mem: Dict[str, dict] = {}
        self._mem_lock = threading.Lock()

    def _redis_key(self, proxy_raw: str) -> str:
        import hashlib
        h = hashlib.md5(proxy_raw.encode()).hexdigest()[:12]
        return f"{self._KEY_PREFIX}{h}"

    def get(self, proxy_raw: str) -> Optional[dict]:
        """Devolve entry valido ou None se nao existir / bad / expirado."""
        if self._r:
            try:
                raw = self._r.get(self._redis_key(proxy_raw))
                if raw:
                    entry = json.loads(raw)
                    return entry if entry.get("health") == "good" else None
            except Exception:
                pass
        with self._mem_lock:
            entry = self._mem.get(proxy_raw)
            if not entry:
                return None
            if time.time() - entry.get("last_used", 0) > self._TTL_SECONDS:
                return None
            return entry if entry.get("health") == "good" else None

    def save(self, proxy_raw: str, cookies: list, user_agent: str):
        """Guarda cookies apos login bem-sucedido."""
        entry = {
            "cookies":    cookies,
            "user_agent": user_agent,
            "last_used":  time.time(),
            "health":     "good",
        }
        if self._r:
            try:
                self._r.set(self._redis_key(proxy_raw), json.dumps(entry),
                            ex=self._TTL_SECONDS)
                return
            except Exception:
                pass
        with self._mem_lock:
            self._mem[proxy_raw] = entry

    def mark_bad(self, proxy_raw: str):
        """Invalida os cookies deste proxy (ex: 401 recebido)."""
        if self._r:
            try:
                key = self._redis_key(proxy_raw)
                raw = self._r.get(key)
                if raw:
                    entry = json.loads(raw)
                    entry["health"] = "bad"
                    self._r.set(key, json.dumps(entry), ex=300)
                return
            except Exception:
                pass
        with self._mem_lock:
            if proxy_raw in self._mem:
                self._mem[proxy_raw]["health"] = "bad"

    def stats(self) -> str:
        if self._r:
            try:
                keys = self._r.keys(f"{self._KEY_PREFIX}*")
                good = sum(
                    1 for k in keys
                    if (raw := self._r.get(k)) and json.loads(raw).get("health") == "good"
                )
                return f"[CookiePool] Redis: {good} good / {len(keys)-good} bad"
            except Exception:
                pass
        with self._mem_lock:
            good = sum(1 for e in self._mem.values() if e.get("health") == "good")
            return f"[CookiePool] Memory: {good} good / {len(self._mem)-good} bad"

proxy_cookie_pool: Optional[ProxyCookiePool] = None

# =================================================================================
# MELHORIA 3.6 — Persistent Browser Context Pool
# Em vez de criar um browser NOVO por cada ciclo (lento + fingerprint novo),
# reutilizamos o mesmo contexto entre tentativas do mesmo utilizador.
# O contexto e limpo (cookies + storage) apenas quando necessario.
# =================================================================================
class BrowserContextPool:
    """
    Pool de contextos Playwright reutilizaveis, indexados por proxy_raw.
    Cada entrada guarda: browser, context, page, user_agent, e timestamps.

    Ciclo de vida:
      1. get(proxy_raw)      -> devolve entry existente se valido
      2. (login usa entry)
      3. release(proxy_raw)  -> marca como disponivel para reutilizacao
      4. invalidate(proxy_raw) -> fecha tudo e remove (ex: proxy ficou mau)

    Thread-safety: usa asyncio.Lock porque e usado exclusivamente em
    contextos async (dentro do loop do worker).
    """

    # Tempo maximo que um contexto pode estar inativo antes de ser fechado
    _MAX_IDLE_SECONDS = 120

    def __init__(self):
        self._pool: Dict[str, dict] = {}
        self._lock  = asyncio.Lock()

    async def get(self, proxy_raw: str) -> Optional[dict]:
        """Devolve entry existente se valido e nao expirado; None caso contrario."""
        async with self._lock:
            entry = self._pool.get(proxy_raw)
            if not entry:
                return None
            # Verificar se a pagina ainda esta aberta
            try:
                if entry["page"].is_closed():
                    await self._close_entry(proxy_raw)
                    return None
            except Exception:
                await self._close_entry(proxy_raw)
                return None
            # Verificar idle timeout
            idle = time.time() - entry.get("last_used", 0)
            if idle > self._MAX_IDLE_SECONDS:
                await self._close_entry(proxy_raw)
                return None
            entry["in_use"] = True
            entry["last_used"] = time.time()
            return entry

    async def store(self, proxy_raw: str, browser, context, page, user_agent: str):
        """Guarda um contexto recem-criado no pool."""
        async with self._lock:
            # Fechar entry anterior se existir
            if proxy_raw in self._pool:
                await self._close_entry(proxy_raw)
            self._pool[proxy_raw] = {
                "browser":    browser,
                "context":    context,
                "page":       page,
                "user_agent": user_agent,
                "created_at": time.time(),
                "last_used":  time.time(),
                "in_use":     True,
            }

    async def release(self, proxy_raw: str):
        """Marca o contexto como disponivel (nao o fecha)."""
        async with self._lock:
            if proxy_raw in self._pool:
                self._pool[proxy_raw]["in_use"]    = False
                self._pool[proxy_raw]["last_used"] = time.time()

    async def reset_context(self, proxy_raw: str):
        """Limpa cookies e storage sem fechar o browser (reutilizacao limpa)."""
        async with self._lock:
            entry = self._pool.get(proxy_raw)
            if not entry:
                return
            try:
                await entry["context"].clear_cookies()
                await entry["context"].clear_permissions()
                # Reabrir uma pagina limpa
                try:
                    await entry["page"].close()
                except Exception:
                    pass
                entry["page"] = await entry["context"].new_page()
                entry["last_used"] = time.time()
            except Exception as e:
                safe_print(f"[BrowserPool] Falha ao limpar contexto: {e}")
                await self._close_entry(proxy_raw)

    async def invalidate(self, proxy_raw: str):
        """Fecha e remove o contexto (proxy ficou mau ou sessao corrompida)."""
        async with self._lock:
            await self._close_entry(proxy_raw)

    async def _close_entry(self, proxy_raw: str):
        """Fecha browser e remove do pool. Chamar dentro do lock."""
        entry = self._pool.pop(proxy_raw, None)
        if not entry:
            return
        try:
            await entry["browser"].close()
        except Exception:
            pass

    async def cleanup_idle(self):
        """Remove entradas inativas ha mais de _MAX_IDLE_SECONDS. Chamar periodicamente."""
        async with self._lock:
            stale = [
                k for k, v in self._pool.items()
                if not v.get("in_use") and
                   time.time() - v.get("last_used", 0) > self._MAX_IDLE_SECONDS
            ]
            for k in stale:
                await self._close_entry(k)
            if stale:
                safe_print(f"[BrowserPool] Fechados {len(stale)} contextos ociosos.")

    def stats(self) -> str:
        total  = len(self._pool)
        in_use = sum(1 for v in self._pool.values() if v.get("in_use"))
        return f"[BrowserPool] {total} contextos ({in_use} em uso, {total-in_use} livres)"


# Instancia global do pool (uma por processo worker)
browser_context_pool: Optional[BrowserContextPool] = None

# =================================================================================
# FUNÇÕES AUXILIARES ADAPTADAS
# =================================================================================

def pre_flight_warmup(proxy_raw: str, process_id: int):
    """Faz uma requisição leve para 'aquecer' a conexão do proxy."""
    try:
        parsed_proxy = _parse_proxy_raw(proxy_raw)
        proxy_url = _proxy_to_http_url(proxy_raw)
        if not parsed_proxy or not proxy_url:
            return False
        ip, port, _, _ = parsed_proxy
        
        proxies = {"http://": proxy_url, "https://": proxy_url}
        
        with httpx.Client(proxies=proxies, timeout=5.0) as client:
            client.get("https://pedidodevistos.mne.gov.pt/VistosOnline/")
            
        safe_print(f"[Process-{process_id}] 🔥 Warmup OK: Proxy {ip}:{port}")
        return True
        
    except Exception as e:
        safe_print(f"[Process-{process_id}] ❄️ Warmup FAIL: {proxy_raw[:15]}...")
        if state_manager: state_manager.update_proxy_score(proxy_raw, -5)
        return False


# --- COLE O BLOCO ABAIXO INTEIRO AQUI ---
async def send_telegram_alert(message: str):
    """
    Envia mensagem para um ou mais bots Telegram lendo credenciais do config1.toml.
    """
    try:
        settings = scraper_settings or {}
        telegram_targets = []
        for section_name in ("telegram", "telegram_secondary"):
            section = settings.get(section_name, {})
            if not isinstance(section, dict):
                continue
            bot_token = str(section.get("bot_token") or "").strip()
            chat_id = str(section.get("chat_id") or "").strip()
            enabled = _coerce_bool(section.get("enabled", True), True)
            if bot_token and chat_id and enabled:
                telegram_targets.append((section_name, bot_token, chat_id))
    except Exception as e:
        try:
            logger.warning(f"[Telegram] Configurações não carregadas: {e}")
        except NameError:
            print(f"[Telegram] Configurações não carregadas: {e}")
        return

    if not telegram_targets:
        try:
            logger.warning("[Telegram] ⚠️ Nenhum bot Telegram habilitado/configurado. Pulando alerta.")
        except NameError:
            print("[Telegram] ⚠️ Nenhum bot Telegram habilitado/configurado.")
        return

    try:
        async with httpx.AsyncClient() as client:
            for section_name, bot_token, chat_id in telegram_targets:
                url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                payload = {
                    "chat_id": chat_id,
                    "text": message,
                    "parse_mode": "HTML"
                }
                try:
                    response = await client.post(url, data=payload, timeout=10.0)
                    if response.status_code >= 400:
                        logger.warning(
                            f"[Telegram] {section_name} falhou: HTTP {response.status_code} "
                            f"{response.text[:200]}"
                        )
                except Exception as send_err:
                    logger.warning(f"[Telegram] Falha ao enviar alerta via {section_name}: {send_err}")
    except Exception as e:
        try:
            logger.warning(f"[Telegram] Falha ao enviar alerta: {e}")
        except NameError:
            print(f"[Telegram] Falha ao enviar alerta: {e}")

async def check_api_balance():
    """Verifica o saldo da API de Captcha. Retorna False se estiver baixo."""
    try:
        # Pega a chave do config
        api_key = scraper_settings.get('anti_captcha_api_key')
        if isinstance(api_key, list): api_key = api_key[0] # Pega a primeira se for lista
        if not api_key:
            return True # Se não tem chave configurada, ignora

        url = "https://api.anti-captcha.com/getBalance"
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json={"clientKey": api_key}, timeout=10.0)
            data = resp.json()
            
            balance = float(data.get('balance', 0))
            
            if balance < 2.0: # Se tiver menos de $2 dólares
                await send_telegram_alert(
                    f"🚨 <b>ALERTA DE SALDO!</b>\n"
                    f"💰 Saldo Baixo: <b>${balance:.2f}</b>\n"
                    f"🛑 O bot está pausado até recarregar."
                )
                logger.error(f"🚨 SALDO BAIXO: ${balance:.2f}. Pausando processos...")
                return False
            else:
                logger.info(f"💰 Saldo OK: ${balance:.2f}")
                return True
    except Exception as e:
        logger.warning("Não foi possível checar saldo: %r", e)
    return True

async def send_status_report(credentials_file_path: str):
    """Lê o CSV e manda um resumo para o Telegram."""
    try:
        import pandas as pd
        if not os.path.exists(credentials_file_path):
            return
        
        df = pd.read_csv(credentials_file_path)
        total = len(df)
        
        if 'status' not in df.columns:
            return
            
        df['status'] = df['status'].astype(str).str.strip().str.lower()
        success_count = len(df[df['status'] == 'true'])
        pending_count = len(df[df['status'] == 'pending'])
        failed_count = total - success_count - pending_count
        
        now = time.strftime("%H:%M:%S")
        
        # Estatísticas CAPTCHA por provider
        captcha_lines = []
        for prov, s in captcha_stats.items():
            total_cap = s["solved"] + s["failed"]
            if total_cap == 0:
                continue
            avg = s["total_time"] / s["solved"] if s["solved"] > 0 else 0
            rate = (s["solved"] / total_cap * 100) if total_cap > 0 else 0
            captcha_lines.append(
                f"  {prov}: ✅{s['solved']} ❌{s['failed']} avg={avg:.0f}s win={s['wins']} ({rate:.0f}%)"
            )
        captcha_section = "\n🤖 <b>CAPTCHA</b>:\n" + "\n".join(captcha_lines) if captcha_lines else ""

        msg = (
            f"📊 <b>STATUS REPORT</b> ({now})\n"
            f"✅ Sucesso: {success_count}\n"
            f"⏳ Pendentes: {pending_count}\n"
            f"❌ Falhas: {failed_count}\n"
            f"📈 Total: {total}"
            f"{captcha_section}"
        )
        
        await send_telegram_alert(msg)
        logger.info("[Report] Status enviado para o Telegram.")
    except Exception as e:
        logger.warning(f"Erro ao gerar relatório: {e}")

def reporter_thread_loop(credentials_file_path: str, interval_seconds: int = 900):
    """
    Roda em uma thread separada para enviar reports periódicos.
    Default: 900 segundos = 15 minutos.
    """
    logger.info(f"[Reporter] Iniciando loop de report (cada {interval_seconds}s)...")
    while True:
        time.sleep(interval_seconds)
        try:
            # Cria um loop de eventos para rodar o async dentro da thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(send_status_report(credentials_file_path))
            loop.close()
        except Exception as e:
            logger.error(f"[Reporter] Erro na thread de report: {e}")
# ----------------------------------------

def update_csv_status(username: str, status: str, csv_file: str = 'creds_2.csv', expected_old_status: str = None):
    """
    Update the status column. 
    If 'expected_old_status' is provided, only updates if current status matches (Atomic Lock).
    Returns True if updated, False if skipped (race condition).
    """
    import csv
    import tempfile
    import shutil
    
    try:
        log_func = logger.info
        log_warn = logger.warning
    except NameError:
        log_func = print
        log_warn = print
    
    csv_path = os.path.join(WORKING_DIR, csv_file)
    if not os.path.exists(csv_path):
        log_warn(f"[CSV Update] CSV file not found: {csv_path}")
        return False

    lock_file = csv_path + '.lock'
    lock_acquired = False
    
    for attempt in range(20):
        try:
            with open(lock_file, 'x') as lf:
                lf.write(str(os.getpid()))
            lock_acquired = True
            break
        except FileExistsError:
            try:
                if time.time() - os.path.getmtime(lock_file) > 60:
                    os.remove(lock_file)
                    continue
            except OSError:
                pass
            time.sleep(0.2 * (attempt + 1))
    
    if not lock_acquired:
        log_warn(f"[CSV Update] Could not acquire lock for {csv_file}")
        return False

    try:
        rows = []
        updated = False
        user_found = False
        
        with open(csv_path, 'r', encoding='utf-8', newline='') as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
             # CORREÇÃO: Se fieldnames for None (arquivo vazio), falha graciosamente
            if not fieldnames:
                 log_warn(f"[CSV Update] CSV file has no headers: {csv_path}")
                 return False
            for row in reader:
                if row.get('username') == username:
                    user_found = True
                    current_status = row.get('status', '').strip().lower()
                    
                    # --- CORREÇÃO: TRATAR VAZIO COMO 'FALSE' ---
                    # Se o status estiver vazio, consideramos como 'false' (pronto para processar)
                    if not current_status:
                        current_status = 'false'
                    # -------------------------------------------

                    # LÓGICA DE TRAVA (LOCK)
                    if expected_old_status:
                        if current_status == expected_old_status.lower():
                            row['status'] = status
                            updated = True
                        else:
                            # O status mudou ou era diferente do esperado
                            log_warn(f"[CSV Lock] Usuário {username} status atual é '{current_status}', esperado '{expected_old_status}'. Pulando.")
                            updated = False 
                    else:
                        # Atualização forçada
                        row['status'] = status
                        updated = True
                        
                rows.append(row)

        if not user_found:
             log_warn(f"[CSV Update] User {username} not found in file.")
             return False

        if updated:
            temp_file = csv_path + '.tmp'
            with open(temp_file, 'w', encoding='utf-8', newline='') as f:
                if fieldnames:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(rows)

            shutil.move(temp_file, csv_path)
            log_func(f"[CSV Update] Updated {username} -> '{status}'")
            return True
        else:
            return False

    except Exception as e:
        log_func(f"[CSV Update] Failed: {e}")
        return False
    finally:
        try:
            os.remove(lock_file)
        except OSError:
            pass
        # =================================================================================
# CLASSE HUMAN SIMULATOR (ADICIONAR AQUI)
# =================================================================================
class HumanSimulator:
    """
    Simulates human-like interactions to bypass bot detection.
    Uses mathematical Bezier curves for mouse movement and variable typing speeds.
    """
    
    def __init__(self, page):
        self.page = page
        self.viewport = None
        
    async def _get_viewport(self):
        if not self.viewport:
            self.viewport = await self.page.viewport_size()
        return self.viewport
    async def move_mouse_natural(self, target_x: int, target_y: int):
        """
        Moves the mouse in a human-like curve (Bezier) + Tremores Gaussianos.
        """
        viewport = await self._get_viewport()
        current_pos = await self.page.mouse.position()
        
        start_x, start_y = current_pos['x'], current_pos['y']
        
        if start_x == 0 and start_y == 0:
            start_x = random.randint(100, viewport['width'] - 100)
            start_y = random.randint(100, viewport['height'] - 100)

        steps = random.randint(15, 30)
        
        control_points = [
            (start_x, start_y),
            (random.randint(min(start_x, target_x), max(start_x, target_x)), 
             random.randint(min(start_y, target_y), max(start_y, target_y))),
            (target_x, target_y)
        ]

        for i in range(steps):
            t = i / steps
            # Quadratic Bezier formula
            x = (1 - t)**2 * control_points[0][0] + 2 * (1 - t) * t * control_points[1][0] + t**2 * control_points[2][0]
            y = (1 - t)**2 * control_points[0][1] + 2 * (1 - t) * t * control_points[1][1] + t**2 * control_points[2][1]
            
            # --- NOVO: TREMORES GAUSSIANOS (HUMANIZAÇÃO MÁXIMA) ---
            tremor_x = random.gauss(0, 1.2)  # Desvio padrão de 1.2px
            tremor_y = random.gauss(0, 1.2)
            
            final_x = x + tremor_x
            final_y = y + tremor_y
            # --------------------------------------------------

            await self.page.mouse.move(final_x, final_y)
            await asyncio.sleep(_hs_delay(0.001, 0.005))

    async def human_click(self, selector: str, wait_before_click: bool = True):
        """
        Locates element, moves mouse to it naturally, and clicks with random delay.
        """
        try:
            locator = self.page.locator(selector)
            await locator.wait_for(state="visible", timeout=10000)
            
            box = await locator.bounding_box()
            if not box:
                logger.warning(f"[HumanSim] No box for {selector}")
                return False

            # Target a random point inside the element (not the exact center)
            target_x = box['x'] + random.randint(5, int(box['width'] - 5))
            target_y = box['y'] + random.randint(5, int(box['height'] - 5))

            await self.move_mouse_natural(target_x, target_y)
            
            if wait_before_click:
                await asyncio.sleep(_hs_delay(0.1, 0.3))
            
            await self.page.mouse.down()
            await asyncio.sleep(_hs_delay(0.05, 0.15))
            await self.page.mouse.up()
            
            await asyncio.sleep(_hs_delay(0.2, 0.5))
            return True

        except Exception as e:
            logger.warning(f"[HumanSim] Click failed on {selector}: {e}")
            return False

    async def human_paste(self, selector: str, text: str):
        """
        Simulates a user pasting text. Fast like injection, safe like typing.
        """
        
        try:
            # 1. Focus the field using human click
            if not await self.human_click(selector):
                 # Fallback: simple click if human_click failed
                await self.page.locator(selector).click(timeout=5000)
            
            # 2. Clear existing text (Ctrl+A -> Backspace)
            await asyncio.sleep(_hs_delay(0.1, 0.2))
            await self.page.keyboard.down("Control")
            await self.page.keyboard.press("A")
            await self.page.keyboard.up("Control")
            await asyncio.sleep(_hs_delay(0.05, 0.1))
            await self.page.keyboard.press("Backspace")
            await asyncio.sleep(_hs_delay(0.1, 0.2))

            # 3. MELHORIA: Usar insert_text nativo do Playwright
            # Isso evita erros de permissão do clipboard e é mais rápido
            await self.page.keyboard.insert_text(text)
            
            # 4. Small post-fill delay
            await asyncio.sleep(_hs_delay(0.1, 0.3))
            return True

        except Exception as e:
            logger.warning(f"[HumanSim] Paste failed: {e}. Falling back to typing.")
            return await self.human_type(selector, text)

    async def human_type(self, selector: str, text: str, clear_first: bool = True):
        """
        Standard char-by-char typing. Used as fallback or for sensitive fields.
        """
        try:
            await self.human_click(selector)
            
            if clear_first:
                await asyncio.sleep(_hs_delay(0.1, 0.2))
                await self.page.keyboard.down("Control")
                await self.page.keyboard.press("A")
                await self.page.keyboard.up("Control")
                await self.page.keyboard.press("Backspace")

            _tscale = _human_delay_scale()
            for char in str(text):
                delay = random.uniform(0.01, 0.08) * _tscale
                if random.random() < 0.05: # Occasional thinking pause
                    delay += random.uniform(0.3, 0.5) * _tscale
                
                await self.page.keyboard.type(char)
                await asyncio.sleep(delay)
            return True
        except Exception as e:
            logger.error(f"[HumanSim] Type failed: {e}")
            return False

    async def human_select(self, selector: str, value: str):
        """
        Handles dropdowns. Clicks to open, then selects the option.
        """
        try:
            # Click to focus/open
            await self.human_click(selector)
            await asyncio.sleep(_hs_delay(0.2, 0.4))

            # Use Playwright's select option but ensure events trigger
            await self.page.select_option(selector, value)
            
            # Trigger change event explicitly for legacy JS frameworks
            await self.page.dispatchEvent(selector, "change")
            await asyncio.sleep(_hs_delay(0.2, 0.4))
            return True
            
        except Exception as e:
            logger.warning(f"[HumanSim] Select failed: {e}")
            return False


scraper_settings = None


def _cfg_float(key: str, default: float) -> float:
    try:
        if scraper_settings is not None and key in scraper_settings:
            return float(scraper_settings[key])
    except (TypeError, ValueError):
        pass
    return default


def _cfg_int(key: str, default: int) -> int:
    try:
        if scraper_settings is not None and key in scraper_settings:
            return int(scraper_settings[key])
    except (TypeError, ValueError):
        pass
    return default


def _cfg_bool(key: str, default: bool) -> bool:
    try:
        if scraper_settings is not None and key in scraper_settings:
            value = scraper_settings[key]
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                return value.strip().lower() in ("1", "true", "yes", "on")
            return bool(value)
    except Exception:
        pass
    return default


def _human_delay_scale() -> float:
    try:
        if scraper_settings and scraper_settings.get("fast_human_delays"):
            return float(scraper_settings.get("human_delay_scale", 0.55))
    except (TypeError, ValueError):
        pass
    return 1.0


def _hs_delay(lo: float, hi: float) -> float:
    return random.uniform(lo, hi) * _human_delay_scale()


async def _ui_wait(page, ms: int) -> None:
    try:
        if scraper_settings and scraper_settings.get("fast_ui_delays", True):
            ms = max(120, int(ms * float(scraper_settings.get("ui_wait_scale", 0.62))))
    except (TypeError, ValueError):
        pass
    await page.wait_for_timeout(ms)


def safe_print(*args, **kwargs):
    """Print function that handles Unicode encoding errors on Windows console."""
    try:
        print(*args, **kwargs)
    except UnicodeEncodeError:
        safe_args = [str(arg).encode('ascii', 'replace').decode('ascii') if isinstance(arg, str) else arg for arg in args]
        print(*safe_args, **kwargs)


def _resolve_logging_level(level_name: Any, default: int = logging.INFO) -> int:
    try:
        if isinstance(level_name, int):
            return level_name
        candidate = str(level_name or "").strip().upper()
        if not candidate:
            return default
        return int(getattr(logging, candidate, default))
    except Exception:
        return default


def _coerce_bool(value: Any, default: bool = False) -> bool:
    try:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in ("1", "true", "yes", "on")
        if value is None:
            return default
        return bool(value)
    except Exception:
        return default


def _runtime_logs_dir() -> str:
    d = os.path.join(WORKING_DIR, "logs")
    os.makedirs(d, exist_ok=True)
    return d


def _current_run_log_path() -> str:
    run_id = os.environ.get("VISA_BOT_RUN_ID", "").strip()
    if not run_id:
        run_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
        os.environ["VISA_BOT_RUN_ID"] = run_id
    return os.path.join(_runtime_logs_dir(), f"visa_bot_run_{run_id}.log")


def _cleanup_orphaned_playwright_browsers(settings: Optional[Dict] = None) -> int:
    effective_settings = settings or scraper_settings or {}
    if os.name != "nt":
        return 0
    if not _coerce_bool(
        effective_settings.get("cleanup_orphaned_playwright_browsers_on_start", True),
        True,
    ):
        return 0

    ps_query = (
        "Get-CimInstance Win32_Process | "
        "Where-Object { $_.Name -eq 'chrome.exe' -and "
        "$_.CommandLine -like '*playwright_chromiumdev_profile-*' } | "
        "Select-Object -ExpandProperty ProcessId"
    )
    try:
        query = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_query],
            capture_output=True,
            text=True,
            timeout=20,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            check=False,
        )
        pids = []
        for line in (query.stdout or "").splitlines():
            line = line.strip()
            if line.isdigit():
                pids.append(int(line))
        if not pids:
            return 0

        killed = 0
        for pid in pids:
            result = subprocess.run(
                ["taskkill", "/PID", str(pid), "/T", "/F"],
                capture_output=True,
                text=True,
                timeout=20,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                check=False,
            )
            if result.returncode == 0:
                killed += 1

        if killed:
            logging.getLogger().warning(
                f"[StartupCleanup] Killed {killed} orphaned Playwright Chrome root process(es): {pids}"
            )
        return killed
    except Exception as cleanup_err:
        logging.getLogger().warning(
            f"[StartupCleanup] Failed to clear orphaned Playwright Chrome processes: {cleanup_err}"
        )
        return 0


def _cleanup_orphaned_bot_processes(settings: Optional[Dict] = None) -> int:
    """Kill stale multiprocessing child workers left after interrupted runs."""
    effective_settings = settings or scraper_settings or {}
    if os.name != "nt":
        return 0
    if not _coerce_bool(
        effective_settings.get("cleanup_orphaned_playwright_browsers_on_start", True),
        True,
    ):
        return 0

    current_pid = os.getpid()
    ps_query = rf"""
Get-CimInstance Win32_Process |
Where-Object {{
  $_.ProcessId -ne {current_pid} -and
  $_.Name -match '^(python|pythonw|py)\.exe$' -and
  ($_.CommandLine -match 'multiprocessing-fork' -or
   $_.CommandLine -match 'spawn_main') -and
  -not (Get-Process -Id $_.ParentProcessId -ErrorAction SilentlyContinue)
}} |
Select-Object -ExpandProperty ProcessId
"""
    try:
        query = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_query],
            capture_output=True,
            text=True,
            timeout=20,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            check=False,
        )
        pids = []
        for line in (query.stdout or "").splitlines():
            line = line.strip()
            if line.isdigit():
                pids.append(int(line))
        if not pids:
            return 0

        killed = 0
        for pid in pids:
            result = subprocess.run(
                ["taskkill", "/PID", str(pid), "/T", "/F"],
                capture_output=True,
                text=True,
                timeout=20,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                check=False,
            )
            if result.returncode == 0:
                killed += 1

        if killed:
            logging.getLogger().warning(
                f"[StartupCleanup] Killed {killed} orphaned bot Python process tree(s): {pids}"
            )
        return killed
    except Exception as cleanup_err:
        logging.getLogger().warning(
            f"[StartupCleanup] Failed to clear orphaned bot Python processes: {cleanup_err}"
        )
        return 0


def setup_logging(process_id: int = 0, settings: Optional[Dict] = None):
    """Setup logging for each process with Process ID prefix"""
    effective_settings = settings or scraper_settings or {}
    console_level = _resolve_logging_level(
        effective_settings.get("logger_console_level", effective_settings.get("log_level", "INFO")),
        logging.INFO,
    )
    file_level = _resolve_logging_level(
        effective_settings.get("logger_file_level", effective_settings.get("log_level", "INFO")),
        logging.INFO,
    )
    log_to_file = _coerce_bool(effective_settings.get("log_to_file", False), False)

    handler = colorlog.StreamHandler()
    handler.setLevel(console_level)
    # ADICIONADO O PREFIXO [Proc-{process_id}]
    formatter = colorlog.ColoredFormatter(
        fmt="%(log_color)s[Proc-%(process_id)s] %(asctime)s - %(levelname)-8s - %(message)s",
        datefmt="%H:%M:%S",
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'bold_red',
        }
    )
    handler.setFormatter(formatter)
    logger = colorlog.getLogger()
    for existing in list(logger.handlers):
        try:
            existing.close()
        except Exception:
            pass
    logger.setLevel(min(console_level, file_level) if log_to_file else console_level)
    logger.handlers = []
    logger.propagate = False
    logger.addHandler(handler)

    if log_to_file:
        file_handler = logging.FileHandler(_current_run_log_path(), encoding="utf-8")
        file_handler.setLevel(file_level)
        file_handler.setFormatter(
            logging.Formatter(
                "[Proc-%(process_id)s] %(asctime)s - %(levelname)-8s - %(message)s",
                datefmt="%H:%M:%S",
            )
        )
        logger.addHandler(file_handler)
    
    # Passa o process_id para o formatter via extra
    old_factory = logging.getLogRecordFactory()
    def record_factory(*args, **kwargs):
        record = old_factory(*args, **kwargs)
        record.process_id = process_id
        return record
    logging.setLogRecordFactory(record_factory)

    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("hpack").setLevel(logging.WARNING)
    logging.getLogger("playwright").setLevel(logging.WARNING)
    if log_to_file:
        try:
            logger.info(f"[Logging] File log enabled: {_current_run_log_path()}")
        except Exception:
            pass
    return logger


def _error_logs_dir() -> str:
    d = os.path.join(os.path.dirname(WORKING_DIR), "logs")
    os.makedirs(d, exist_ok=True)
    return d


def _append_error_register_line(record: dict) -> None:
    """Append one JSON object to logs/error_register.jsonl (best-effort; multi-process safe enough for triage)."""
    try:
        path = os.path.join(_error_logs_dir(), "error_register.jsonl")
        line = json.dumps(record, ensure_ascii=False) + "\n"
        with open(path, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        pass


def _playwright_login_error_already_bundled(exc: BaseException) -> bool:
    """
    True if this exception was raised immediately after capture_browser_error_bundle
    on a login path — evita duplicar critical_playwright no except exterior.
    """
    msg = str(exc)
    markers = (
        "Login Rejeitado pelo Site:",
        "Login HTTP 429",
        "Login falhou com HTTP",
        "Login possivelmente rejeitado:",
        "Timeout no Submit",
        "Login POST network failure",
        "[Playwright] Failed during profile/first/second form flow:",
    )
    return any(m in msg for m in markers)


def _error_register_class(reason: str, exc: Optional[BaseException]) -> str:
    """Categoria estável para triagem em error_register.jsonl (ver info/04_error_tracking.md)."""
    if reason == "login_rejected_server":
        return "login_server"
    if reason == "login_rejected_suspect":
        return "login_server_suspect"
    if reason == "login_rate_limited":
        return "rate_limited"
    if reason == "login_server_http_error":
        return "server_http"
    if reason == "login_submit_timeout":
        return "timeout"
    if reason == "form_flow_error":
        return "form_flow"
    if exc:
        return _classify_proxy_error(str(exc))
    return "browser_state"


async def capture_browser_error_bundle(
    page,
    reason: str,
    username: Optional[str] = None,
    exc: Optional[BaseException] = None,
    extra_context: Optional[dict] = None,
) -> Optional[str]:
    """
    Capture what the browser actually shows (URL, title, text, HTML snippet, visible error nodes)
    plus a full-page screenshot. Writes a JSON report under browser_error_reports/.
    Appends a summary line to logs/error_register.jsonl for session continuity.
    Optional extra_context merges into the JSON (e.g. server login message fields).
    """
    log = logging.getLogger()
    cfg = scraper_settings or {}
    max_text = int(cfg.get("browser_error_max_text_chars", 12000))
    max_html = int(cfg.get("browser_error_max_html_chars", 16000))
    out_dir = os.path.join(WORKING_DIR, "browser_error_reports")
    os.makedirs(out_dir, exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")
    safe_user = (username or "unknown").replace("/", "_").replace("\\", "_")[:80]
    stem = f"{safe_user}_{reason}_{ts}".replace(" ", "_")
    stem = re.sub(r"[^\w\-.]+", "_", stem)[:180]

    report: dict = {
        "ts_utc": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "reason": reason,
        "username_ref": safe_user,
        "exception_type": type(exc).__name__ if exc else None,
        "exception_message": (str(exc)[:4000] if exc else None),
    }
    if extra_context:
        try:
            report["extra_context"] = {
                str(k): (v if isinstance(v, (str, int, float, bool, type(None))) else str(v)[:2000])
                for k, v in extra_context.items()
            }
        except Exception:
            report["extra_context"] = {"_error": "could not serialize extra_context"}
    json_path = os.path.join(out_dir, f"{stem}.json")
    png_path = os.path.join(out_dir, f"{stem}.png")

    try:
        report["url"] = page.url
    except Exception:
        report["url"] = None
    try:
        report["title"] = await page.title()
    except Exception:
        report["title"] = None

    try:
        report["visible_text"] = await page.evaluate(
            f"""() => {{
                const t = document.body && document.body.innerText;
                return t ? t.slice(0, {max_text}) : "";
            }}"""
        )
    except Exception as et:
        report["visible_text"] = f"(unavailable: {et})"

    try:
        html = await page.content()
        report["html_snippet"] = html[:max_html] if html else ""
        report["html_total_len"] = len(html) if html else 0
    except Exception as eh:
        report["html_snippet"] = f"(unavailable: {eh})"
        report["html_total_len"] = None

    try:
        report["dom_error_hints"] = await page.evaluate("""() => {
            const out = [];
            const sel = '[class*="error"],[class*="alert"],[id*="error"],.validationMessage,.mensagemErro,.formError';
            document.querySelectorAll(sel).forEach(el => {
                const tx = (el.innerText || "").trim();
                if (tx && tx.length < 800) out.push(tx.slice(0, 500));
            });
            return out.slice(0, 20);
        }""")
    except Exception:
        report["dom_error_hints"] = []

    try:
        await page.screenshot(path=png_path, full_page=True)
        report["screenshot_png"] = png_path
    except Exception as es:
        report["screenshot_png"] = None
        report["screenshot_error"] = str(es)[:500]

    try:
        with open(json_path, "w", encoding="utf-8") as jf:
            json.dump(report, jf, ensure_ascii=False, indent=2)
    except Exception as ej:
        log.warning(f"[BrowserCapture] Failed to write JSON report: {ej}")
        return None

    log.warning(
        f"[BrowserCapture] reason={reason} | report={json_path} | "
        f"url={report.get('url', '')[:120]}"
    )

    reg = {
        "ts_utc": report["ts_utc"],
        "component": "playwright_browser",
        "severity": "error",
        "reason": reason,
        "username_ref": safe_user,
        "error_class": _error_register_class(reason, exc),
        "browser_report_json": os.path.relpath(json_path, os.path.dirname(WORKING_DIR)),
        "url": (report.get("url") or "")[:500],
        "exception_type": report.get("exception_type"),
        "build": "new_bot",
    }
    ec = report.get("extra_context")
    if isinstance(ec, dict):
        if ec.get("http_status") is not None:
            reg["http_status"] = ec["http_status"]
        smt = ec.get("server_message_type")
        if smt is not None:
            reg["server_message_type"] = str(smt)[:80]
        smd = ec.get("server_message_description")
        if smd is not None:
            reg["server_message_description"] = str(smd)[:500]
        th = ec.get("triage_hint")
        if th:
            reg["triage_hint"] = str(th)[:500]

    _append_error_register_line(reg)
    return json_path


def human_time(min_s: float, max_s: float, skew: float = 1.5) -> float:
    """
    Gera tempos com distribuição Log-Normal (mais natural que uniforme).
    skew > 1 = mais picos rápidos (humano apressado).
    Nunca falha. Retorna sempre um valor seguro.
    """
    try:
        val = np.random.lognormal(mean=0, sigma=0.5)
        scaled = min_s + (max_s - min_s) * (val / (val + skew))
        # Clamp (garante que está dentro dos limites)
        return min(max(scaled, min_s), max_s)
    except Exception:
        # Fallback seguro se o numpy falhar
        return random.uniform(min_s, max_s)

def get_timezone_from_proxy(proxy_raw: str) -> str:
    """
    Conecta via Proxy usando Impressão Digital TLS de Chrome Real (curl_cffi).
    Isto engana firewalls avançados (Cloudflare, etc) que bloqueiam scripts Python.
    """
    try:
        proxy_url = _proxy_to_http_url(proxy_raw)
        if not proxy_url:
            return "Europe/Lisbon"
        
        # TENTA COM CURL_CFFI (Modo Elite)
        try:
            response = curl_requests.get(
                "https://ipwho.is/json/",
                proxies={"http": proxy_url, "https": proxy_url},
                impersonate="chrome110",  # <--- A MAGIA: FINGE SER CHROME 110
                timeout=3.0
            )
            
            if response.status_code == 200:
                data = response.json()
                tz_str = data.get('timezone', {}).get('id')
                
                if tz_str and tz_str in pytz.all_timezones_set:
                    logger.info(f"[GeoIP] ✅ Timezone detectado (TLS): {tz_str}")
                    return tz_str
        except Exception as curl_err:
            # Se curl_cffi falhar (raro), cai no fallback httpx
            logger.warning(f"[GeoIP] curl_cffi falhou ({curl_err}), usando fallback httpx.")
            
            # FALLBACK SEGURO (HTTPX ANTIGO)
            with httpx.Client(proxy=proxy_url, timeout=3.0) as client:
                response = client.get("https://ipwho.is/json/")
                if response.status_code == 200:
                    data = response.json()
                    tz_str = data.get('timezone', {}).get('id')
                    if tz_str and tz_str in pytz.all_timezones_set:
                        return tz_str

    except Exception as e:
        logger.warning(f"[GeoIP] Erro geral: {e}")
    
    return "Europe/Lisbon"

def get_current_ip_simple(proxy_info: Optional[str] = None) -> Optional[str]:
    # ALTERAÇÃO: ipv4.icanhazip.com movido para a primeira posição (prioridade)
    simple_services = [
        ("https://ipv4.icanhazip.com", "text"),
        ("https://ifconfig.me/ip", "text"),
        ("https://icanhazip.com", "text"),
        ("https://api.ipify.org?format=json", "json"),
        ("https://ident.me", "text")
    ]
    headers = {'User-Agent': 'curl/7.68.0', 'Accept': '*/*'}
    detected_ip = None
    for service_url, response_type in simple_services:
        try:
            logger.info(f"Trying IP check with {service_url}")
            with httpx.Client(timeout=10.0, headers=headers) as client:
                response = client.get(service_url)
                if response.status_code == 200:
                    if response_type == "json":
                        data = response.json()
                        ip = data.get("ip", "").strip()
                    else:
                        ip = response.text.strip()
                    if ip and len(ip.split('.')) == 4:
                        octets = [int(o) for o in ip.split('.')]
                        if all(0 <= o <= 255 for o in octets):
                            logger.info(f"IP from {service_url}: {ip}")
                            if detected_ip is None:
                                detected_ip = ip
                            elif ip != detected_ip:
                                logger.info(f"IP change detected: {detected_ip} → {ip}")
                                return ip
        except Exception as e:
            logger.info(f"{service_url} failed: {e}")
    return detected_ip or proxy_info

def test_proxy_list(proxy_list: list[str], current_ip: str) -> tuple[httpx.HTTPTransport, str]:
    """
    Testa proxies com LIMITE DE TEMPO RIGOROSO (5s).
    Se não carregar o site alvo em 5s, descarta. Competidores não esperam.
    """
    proxy_list = [p for p in proxy_list if p]
    random.shuffle(proxy_list)

    for proxy_raw in proxy_list:
        if not proxy_raw: continue
            
        try:
            parsed_proxy = _parse_proxy_raw(proxy_raw)
            proxy_url = _proxy_to_http_url(proxy_raw)
            if not parsed_proxy or not proxy_url:
                continue
            ip, port, _, _ = parsed_proxy
            
            # TESTE AGRESSIVO: 5 Segundos total para carregar a página inicial
            # Isso simula a paciência de um usuário real e a velocidade de um sniper bot
            start_time = time.time()
            
            response = curl_requests.get(
                "https://api.ipify.org?format=json", 
                proxies={"http": proxy_url, "https": proxy_url}, 
                impersonate="chrome110",
                timeout=5.0, # <--- TIMEOUT REDUZIDO DE 10s PARA 5s
                allow_redirects=True
            )
            
            latency_ms = int((time.time() - start_time) * 1000)
            
            if response.status_code == 403:
                logger.warning(f"[Proxy Fail] {ip}:{port} -> 403 (Banned)")
                if state_manager: state_manager.update_proxy_score(proxy_raw, -50)
                continue # Próximo!
            
            if response.status_code >= 400:
                continue

            # Sucesso!
            logger.info(f"[Proxy OK] ✅ IP: {ip} | Latência: {latency_ms}ms")
            
            if state_manager: state_manager.update_proxy_score(proxy_raw, 15, latency_ms=latency_ms)
            
            proxy = httpx.Proxy(proxy_url)
            transport = httpx.HTTPTransport(proxy=proxy)
            return transport, proxy_raw
                
        except Exception as e:
            # Qualquer erro (timeout, conexão recusada) = Próximo proxy
            # Não logamos excessivamente para não poluir
            if state_manager: state_manager.update_proxy_score(proxy_raw, -5)
            continue

    raise ValueError("Nenhum proxy funcional encontrado (todos falharam no teste de 5s).")

def create_session(proxy_list: list, user_agent: str,
                   username: str = None) -> tuple:
    """
    Cria sessao httpx com proxy EXCLUSIVO e dedicado para este utilizador.

    GARANTIAS:
      - NUNCA dois utilizadores partilham o mesmo proxy (arrendamento atomico)
      - Proxy com 403 e banido 30 min automaticamente
      - Proxy com timeout/erro e banido progressivamente
      - Se nenhum proxy livre -> excecao clara (nao fallback inseguro)
      - Rotatividade: proxy com menos usos historicos e sempre preferido

    Args:
        proxy_list : lista de proxies "ip:port:user:pwd"
        user_agent : User-Agent a usar nos headers
        username   : nome do utilizador (obrigatorio para exclusividade)

    Returns:
        (httpx.Client, proxy_raw) prontos a usar
    """
    if not proxy_list:
        raise ValueError("[Session] CRITICO: lista de proxies VAZIA.")

    if not username:
        raise ValueError("[Session] CRITICO: username obrigatorio para garantir exclusividade de proxy.")

    global proxy_lease_manager, state_manager
    if not proxy_lease_manager:
        # Permite chamar create_session / main fora do worker (testes, scripts)
        if state_manager is None:
            state_manager = StateManager()
        proxy_lease_manager = ProxyLeaseManager(redis_client=state_manager.r)
        logger.warning(
            "[Session] proxy_lease_manager inicializado inline (processo sem worker)."
        )

    if str(proxy_list[0]).strip() == DIRECT_PROXY_MARKER:
        logger.info("[Session] Tráfego direto (use_proxy=false) — httpx sem proxy")
        headers = get_main_headers(user_agent)
        session = httpx.Client(
            headers=headers,
            timeout=httpx.Timeout(connect=30.0, read=300.0, write=30.0, pool=30.0),
            http2=False,
            follow_redirects=True,
            limits=httpx.Limits(
                max_keepalive_connections=3,
                max_connections=5,
                keepalive_expiry=15.0,
            ),
        )
        return session, DIRECT_PROXY_MARKER

    # ── PASSO 1: Adquirir proxy EXCLUSIVO via LeaseManager ───────────────────
    # Tenta ate 3 vezes com pausa curta (pode haver race condition transitoria)
    proxy_raw = None
    for _acq_attempt in range(3):
        proxy_raw = proxy_lease_manager.acquire(username, proxy_list)
        if proxy_raw:
            break
        logger.warning(
            f"[Session] {username}: sem proxies livres (tentativa {_acq_attempt+1}/3). "
            f"Aguardando 2s..."
        )
        time.sleep(2)

    if not proxy_raw:
        raise RuntimeError(
            f"[Session] {username}: TODOS os {len(proxy_list)} proxies estao ocupados ou banidos. "
            f"Nao e possivel criar sessao — adicione mais proxies ao ficheiro."
        )

    logger.info(f"[Session] 🔒 Proxy exclusivo adquirido: {username} -> {_proxy_safe_label(proxy_raw)}")

    # ── PASSO 2: Testar conectividade — ate 3 proxies diferentes se necessario ─
    # Se o proxy adquirido nao responder, rodar para um novo (ban + novo acquire)
    MAX_PROXY_ROTATIONS = 3
    transport = None
    attempted_proxies = []
    proxy_test_timeout = _cfg_float("proxy_connectivity_timeout_sec", 12.0)

    for _rot in range(MAX_PROXY_ROTATIONS):
        parsed_proxy = _parse_proxy_raw(proxy_raw)
        if not parsed_proxy:
            logger.error(f"[Session] Formato invalido: {proxy_raw}")
            proxy_raw = proxy_lease_manager.rotate(
                username, proxy_raw, proxy_list, reason="invalid_format"
            )
            if not proxy_raw:
                break
            continue

        ip, port, puser, ppwd = parsed_proxy
        proxy_url = _proxy_to_http_url(proxy_raw)
        if not proxy_url:
            logger.error(f"[Session] Formato invalido: {proxy_raw}")
            proxy_raw = proxy_lease_manager.rotate(
                username, proxy_raw, proxy_list, reason="invalid_format"
            )
            if not proxy_raw:
                break
            continue
        proxy_id = f"{ip}:{port}"
        if proxy_id not in attempted_proxies:
            attempted_proxies.append(proxy_id)

        try:
            start_t = time.time()
            proxy_validation_url = "https://api.ipify.org?format=json"
            try:
                if scraper_settings is not None:
                    proxy_validation_url = str(
                        scraper_settings.get("proxy_validation_url") or proxy_validation_url
                    ).strip() or proxy_validation_url
            except Exception:
                pass
            resp = curl_requests.get(
                proxy_validation_url,
                proxies={"http": proxy_url, "https": proxy_url},
                impersonate="chrome120",
                timeout=proxy_test_timeout,
                allow_redirects=True,
            )
            latency_ms = int((time.time() - start_t) * 1000)
            validator_exit_ip = ""
            try:
                if "json" in proxy_validation_url.lower():
                    validator_exit_ip = str((resp.json() or {}).get("ip") or "").strip()
                if not validator_exit_ip:
                    validator_exit_ip = str(resp.text or "").strip().splitlines()[0][:80]
            except Exception:
                validator_exit_ip = ""

            if resp.status_code == 403:
                # 403 = IP banido pelo site — ban imediato de 30 min
                logger.warning(f"[Session] ❌ 403 em {ip} — banido 30 min, rotacionando...")
                if state_manager:
                    state_manager.update_proxy_score(proxy_raw, -80)
                # rotate() já chama ban_proxy() internamente — não chamar duas vezes
                proxy_raw = proxy_lease_manager.rotate(
                    username, proxy_raw, proxy_list, reason="403"
                )
                if not proxy_raw:
                    break
                continue

            if resp.status_code >= 400:
                logger.warning(
                    f"[Session] Proxy validator HTTP {resp.status_code} em {ip} "
                    f"({proxy_validation_url}) — rotacionando..."
                )
                # rotate() já chama ban_proxy() internamente
                proxy_raw = proxy_lease_manager.rotate(
                    username, proxy_raw, proxy_list, reason="http_error"
                )
                if not proxy_raw:
                    break
                continue

            # ✅ Proxy OK
            if state_manager:
                state_manager.update_proxy_score(proxy_raw, 15, latency_ms=latency_ms)
            transport = httpx.HTTPTransport(proxy=httpx.Proxy(proxy_url))
            logger.info(
                f"[Session] ✅ Proxy OK: {_proxy_safe_label(proxy_raw)} | "
                f"exit_ip={validator_exit_ip or 'unknown'} | "
                f"validator={proxy_validation_url} | lat={latency_ms}ms | user={username}"
            )
            break

        except Exception as e:
            err_str = str(e).lower()
            if _is_proxy_provider_quota_error(err_str):
                raise RuntimeError(
                    "[Proxy] Provider recusou o tunnel com 402/quota. "
                    "Verifique/adquira bandwidth no Webshare antes de rodar o bot."
                ) from e
            logger.warning(f"[Session] Proxy {ip} falhou: {e}")
            if state_manager:
                state_manager.update_proxy_score(proxy_raw, -10)
            # rotate() já chama ban_proxy() internamente — não chamar duas vezes
            reason = "timeout" if "timeout" in err_str else "connection"
            proxy_raw = proxy_lease_manager.rotate(
                username, proxy_raw, proxy_list, reason=reason
            )
            if not proxy_raw:
                break

    if transport is None or not proxy_raw:
        raise RuntimeError(
            f"[Session] {username}: nenhum dos {len(attempted_proxies) or MAX_PROXY_ROTATIONS} "
            f"proxy(s) testado(s) respondeu "
            f"({', '.join(attempted_proxies) if attempted_proxies else 'sem detalhes'}). "
            f"Timeout preflight={proxy_test_timeout:.0f}s; verifique qualidade dos proxies."
        )

    # ── PASSO 3: Construir cliente httpx com headers dinamicos ────────────────
    headers = get_main_headers(user_agent)
    session = httpx.Client(
        headers=headers,
        timeout=httpx.Timeout(connect=30.0, read=300.0, write=30.0, pool=30.0),
        http2=False,
        follow_redirects=True,
        transport=transport,
        limits=httpx.Limits(
            max_keepalive_connections=3,
            max_connections=5,
            keepalive_expiry=15.0,
        ),
    )
    return session, proxy_raw
def solve_recaptcha_v2(proxy_raw: str, user_agent: str, captcha_key_index: int = 0, page_url: str = None, page_action: str = None, enterprise_action: str = None) -> str:
    """
    DUAL-SERVICE CAPTCHA com monitorização completa.
    
    Estratégia por prioridade:
      1. Anti-Captcha + 2Captcha em paralelo (threads) → quem responder primeiro ganha
      2. CapMonster como backup
      3. CapSolver como último recurso
    
    Monitorização: tempo médio, taxa de sucesso, wins por provider.
    Todas as keys do config são suportadas (anti-captcha x7, 2captcha x2, capmonster x2, capsolver x1).
    """
    import time as _time
    import concurrent.futures
    import threading

    # BUG C4 FIX: scraper_settings pode ser None se chamado cedo
    if scraper_settings is None:
        raise RuntimeError('[CAPTCHA] scraper_settings ainda nao carregado — aguardar inicio do worker.')
    SITE_KEY = scraper_settings.get('SITE_KEY', '6LdOB9crAAAAADT4RFruc5sPmzLKIgvJVfL830d4')
    PAGE_URL = page_url or 'https://pedidodevistos.mne.gov.pt/VistosOnline/Authentication.jsp'
    _page_action = str(page_action or "").strip().lower()
    _enterprise_page_action = str(enterprise_action or "").strip()
    if not _enterprise_page_action:
        if _page_action == "login":
            _enterprise_page_action = "LOGIN_EVISA"
        elif _page_action == "schedule":
            _enterprise_page_action = "SCHEDULE_EVISA"
    _safe_token_age_s = max(
        15.0,
        float(scraper_settings.get('captcha_max_token_age_seconds', 110.0) or 110.0)
    )
    _timeout_primary_s = max(
        10.0,
        float(scraper_settings.get('captcha_timeout_primary', 60) or 60)
    )
    _timeout_secondary_s = max(
        10.0,
        float(scraper_settings.get('captcha_timeout_secondary', 60) or 60)
    )
    _timeout_fallback_s = max(
        10.0,
        float(scraper_settings.get('captcha_timeout_fallback', 90) or 90)
    )
    _conservative_login_captcha = (
        _page_action == "login"
        and _cfg_bool("captcha_skip_backup_providers_on_login", True)
    )
    _post_solve_buffer_s = 5.0
    if _page_action == "schedule":
        # On the schedule page we inject the token immediately into the slots
        # callback, so we can spend more of the safe token-age budget waiting
        # for the solver than we can during login.
        _post_solve_buffer_s = 1.0
        _schedule_safe_token_age_s = max(
            _safe_token_age_s,
            float(scraper_settings.get('captcha_max_token_age_seconds_schedule', 119.0) or 119.0)
        )
        _schedule_wait_budget_s = max(
            10.0,
            min(_schedule_safe_token_age_s - _post_solve_buffer_s, 118.0)
        )
        _timeout_primary_s = max(_timeout_primary_s, _schedule_wait_budget_s)
        _timeout_secondary_s = max(_timeout_secondary_s, _schedule_wait_budget_s)
        try:
            logger.info(
                f"[Captcha] Schedule mode ativo: wait_budget={_schedule_wait_budget_s:.0f}s "
                f"(token_age_cap={_schedule_safe_token_age_s:.0f}s, "
                f"buffer pós-solve={_post_solve_buffer_s:.0f}s)"
            )
        except Exception:
            pass
    # O token deixa de ser útil quando se aproxima demasiado do limite seguro
    # configurado para o POST /login. Não faz sentido continuar a bloquear a
    # pipeline de login depois disso.
    _global_deadline = _time.time() + max(10.0, _safe_token_age_s - _post_solve_buffer_s)
    try:
        logger.info(f"[Captcha] websiteURL para task: {PAGE_URL}")
    except Exception:
        pass
    if _enterprise_page_action:
        try:
            logger.info(f"[Captcha] enterprise pageAction para task: {_enterprise_page_action}")
        except Exception:
            pass

    def _normalize_keys(key_value):
        if key_value is None: return []
        if isinstance(key_value, str): return [key_value.strip()] if key_value.strip() else []
        if isinstance(key_value, (list, tuple)): return [str(k).strip() for k in key_value if k and str(k).strip()]
        return []

    # Carregar todas as keys dos 4 providers
    anti_keys     = _normalize_keys(scraper_settings.get('anti_captcha_api_key'))
    twocap_keys   = _normalize_keys(scraper_settings.get('twocaptcha_api_key'))
    capmon_keys   = _normalize_keys(scraper_settings.get('capmonster_api_key'))
    capsolver_keys= _normalize_keys(scraper_settings.get('capsolver_api_key'))

    # Seleccionar key por índice (rotação entre utilizadores)
    anti_key     = anti_keys[captcha_key_index % len(anti_keys)]         if anti_keys     else None
    twocap_key   = twocap_keys[captcha_key_index % len(twocap_keys)]     if twocap_keys   else None
    capmon_key   = capmon_keys[captcha_key_index % len(capmon_keys)]     if capmon_keys   else None
    capsolver_key= capsolver_keys[captcha_key_index % len(capsolver_keys)] if capsolver_keys else None

    def validate_token(token):
        return bool(token and isinstance(token, str) and len(token) >= 100)

    # =======================================================================
    # MELHORIA 1.1 + 1.5 — Proxy IP Match no CAPTCHA
    # Extrai os dados do proxy para incluir na task de resolucao.
    # O IP usado para resolver o CAPTCHA passa a ser o MESMO IP do browser.
    # Isso elimina a inconsistencia de IPs que causava falhas de validacao.
    # =======================================================================
    _proxy_task_data = None  # Dados do proxy formatados para a API de CAPTCHA
    if proxy_raw and not _is_direct_proxy(proxy_raw):
        try:
            _parsed_proxy = _parse_proxy_raw(proxy_raw)
            if _parsed_proxy:
                _ip, _port, _puser, _ppwd = _parsed_proxy
                _is_literal_ipv4 = bool(
                    re.fullmatch(r"\d{1,3}(?:\.\d{1,3}){3}", _ip)
                    and all(0 <= int(octet) <= 255 for octet in _ip.split("."))
                )
                if not _is_literal_ipv4 and _cfg_bool("captcha_require_static_proxy_ip", True):
                    raise RuntimeError(
                        "Proxy CAPTCHA/browser IP match requires a static proxy IP; "
                        f"got rotating/superproxy host {_ip}:{_port}. "
                        "Use webshare_mode='direct' with webshare_fetch_method='api', "
                        "or disable captcha_require_static_proxy_ip only for diagnostics."
                    )
                if _is_literal_ipv4:
                    _captcha_proxy_type = "http"
                    try:
                        _configured_scheme = str(
                            (scraper_settings or {}).get("proxy_scheme") or "http"
                        ).strip().lower()
                        if _configured_scheme in ("socks5", "socks5h"):
                            _captcha_proxy_type = "socks5"
                    except Exception:
                        pass
                    _proxy_task_data = {
                        "proxyType": _captcha_proxy_type,
                        "proxyAddress": _ip,
                        "proxyPort": int(_port),
                        "proxyLogin": _puser,
                        "proxyPassword": _ppwd,
                    }
                    logger.info(f"[Captcha] 🔗 Proxy IP Match ativo: {_ip}:{_port}")
                else:
                    logger.info(
                        f"[Captcha] Proxy {_ip}:{_port} e hostname/superproxy; "
                        "providers como Anti-Captcha exigem IP literal. "
                        "A task CAPTCHA sera enviada em modo proxyless."
                    )
        except Exception as _pe:
            logger.warning(f"[Captcha] Nao foi possivel preparar proxy para CAPTCHA: {_pe}")
    # =======================================================================

    def _apply_enterprise_payload(task_data: dict) -> dict:
        """Pass the same Enterprise render parameters visible on the page."""
        if _enterprise_page_action and "Enterprise" in str(task_data.get("type", "")):
            task_data["pageAction"] = _enterprise_page_action
            payload = task_data.get("enterprisePayload")
            if not isinstance(payload, dict):
                payload = {}
            # The page renders the widget with data-action=LOGIN_EVISA
            # (anchor URL parameter sa=LOGIN_EVISA). Enterprise solvers expect
            # render parameters here; keeping pageAction also supports providers
            # that accept that shortcut directly.
            payload.setdefault("action", _enterprise_page_action)
            task_data["enterprisePayload"] = payload
            task_data.setdefault("apiDomain", "www.google.com")
        return task_data

    def _solve_single(provider: str, api_key: str, task_type: str,
                      create_url: str, result_url: str,
                      timeout_budget_s: float,
                      cancel_event: threading.Event | None = None) -> str | None:
        """Resolve CAPTCHA num unico provider e regista estatisticas.
        Usa o mesmo proxy do browser (Proxy IP Match) para evitar detecao por IP diferente.
        """
        t_start = _time.time()
        local_deadline = min(_global_deadline, t_start + max(5.0, float(timeout_budget_s)))
        try:
            if cancel_event and cancel_event.is_set():
                return None
            if _time.time() >= local_deadline:
                logger.warning(f"[Captcha] {provider} ignorado — sem orçamento de tempo restante.")
                return None
            # ── Versoes de task com e sem proxy ──────────────────────────────
            # Os providers usam "ProxylessTask" quando nao ha proxy.
            # Com proxy, mudamos para a versao com proxy da task.
            task_type_with_proxy = task_type.replace("Proxyless", "")

            # Construir payload
            if provider == "anti-captcha":
                if _proxy_task_data:
                    # Com proxy: IP do CAPTCHA = IP do browser
                    task_data = {
                        "type": task_type_with_proxy,
                        "websiteURL": PAGE_URL,
                        "websiteKey": SITE_KEY,
                        **_proxy_task_data,
                    }
                else:
                    task_data = {"type": task_type, "websiteURL": PAGE_URL, "websiteKey": SITE_KEY}
                if user_agent:
                    task_data["userAgent"] = user_agent
                _apply_enterprise_payload(task_data)
                payload = {"clientKey": api_key, "task": task_data}

            elif provider == "2captcha":
                if _proxy_task_data:
                    task_data = {
                        "type": task_type_with_proxy,
                        "websiteURL": PAGE_URL,
                        "websiteKey": SITE_KEY,
                        **_proxy_task_data,
                    }
                else:
                    task_data = {"type": task_type, "websiteURL": PAGE_URL, "websiteKey": SITE_KEY}
                _apply_enterprise_payload(task_data)
                payload = {"clientKey": api_key, "task": task_data}

            elif provider == "capmonster":
                if _proxy_task_data:
                    task_data = {
                        "type": task_type_with_proxy,
                        "websiteURL": PAGE_URL,
                        "websiteKey": SITE_KEY,
                        **_proxy_task_data,
                    }
                else:
                    task_data = {"type": task_type, "websiteURL": PAGE_URL, "websiteKey": SITE_KEY}
                _apply_enterprise_payload(task_data)
                payload = {"clientKey": api_key, "task": task_data}

            else:  # capsolver
                if _proxy_task_data:
                    task_data = {
                        "websiteURL": PAGE_URL,
                        "websiteKey": SITE_KEY,
                        **_proxy_task_data,
                    }
                    task_data["type"] = task_type_with_proxy
                else:
                    task_data = {"websiteURL": PAGE_URL, "websiteKey": SITE_KEY}
                    task_data["type"] = task_type
                if user_agent:
                    task_data["userAgent"] = user_agent
                _apply_enterprise_payload(task_data)
                payload = {"clientKey": api_key, "task": task_data}

            # Criar task (sem proxy no httpx — o proxy e passado DENTRO do payload)
            _create_timeout = max(3.0, min(12.0, local_deadline - _time.time()))
            with httpx.Client(timeout=_create_timeout, trust_env=False) as client:
                if cancel_event and cancel_event.is_set():
                    return None
                resp = client.post(create_url, json=payload)
                resp.raise_for_status()
                task_resp = resp.json()

            task_id = task_resp.get("taskId")
            if not task_id:
                _captcha_record(provider, False, _time.time() - t_start)
                logger.warning(
                    f"[Captcha] {provider} createTask sem taskId: "
                    f"{str(task_resp)[:240]}"
                )
                return None

            # Polling (~90s max); intervalo menor = token mais cedo quando pronto
            _poll = _cfg_float("captcha_poll_interval_sec", 1.5)
            _max_polls = _cfg_int("captcha_max_poll_iterations", 60)
            _poll_error_logged = False
            for _ in range(_max_polls):
                if cancel_event and cancel_event.is_set():
                    return None
                if _time.time() >= local_deadline:
                    logger.warning(
                        f"[Captcha] {provider} excedeu o orçamento de {timeout_budget_s:.0f}s "
                        "antes de ficar pronto."
                    )
                    return None
                _time.sleep(_poll)
                if cancel_event and cancel_event.is_set():
                    return None
                remaining = local_deadline - _time.time()
                if remaining <= 0:
                    logger.warning(
                        f"[Captcha] {provider} sem tempo restante durante o polling."
                    )
                    return None
                try:
                    _poll_timeout = max(2.5, min(6.0, remaining))
                    with httpx.Client(timeout=_poll_timeout, trust_env=False) as client:
                        if cancel_event and cancel_event.is_set():
                            return None
                        result = client.post(result_url, json={
                            "clientKey": api_key, "taskId": task_id
                        }).json()
                    if result.get("errorId") and not _poll_error_logged:
                        _poll_error_logged = True
                        logger.warning(
                            f"[Captcha] {provider} getTaskResult erro: "
                            f"{str(result)[:240]}"
                        )
                        return None
                    if result.get("status") == "ready":
                        token = result.get("solution", {}).get("gRecaptchaResponse")
                        if validate_token(token):
                            elapsed = _time.time() - t_start
                            _captcha_record(provider, True, elapsed)
                            # 3.1: alimentar o CAPTCHARouter com stats em tempo real
                            captcha_router.record(provider, True, elapsed)
                            return token
                except Exception:
                    pass

            _captcha_record(provider, False, _time.time() - t_start)
            captcha_router.record(provider, False, _time.time() - t_start)
            return None

        except Exception as e:
            _captcha_record(provider, False, _time.time() - t_start)
            captcha_router.record(provider, False, _time.time() - t_start)
            logger.warning(f"[Captcha] {provider} erro: {str(e)[:220]}")
            return None

    # ─── FASE 1: DUAL-SERVICE em paralelo (Anti-Captcha + 2Captcha) ─────────────
    phase1_providers = []
    if anti_key:
        phase1_providers.append({
            "provider": "anti-captcha",
            "api_key": anti_key,
            "task_type": "RecaptchaV2EnterpriseTaskProxyless",
            "create_url": "https://api.anti-captcha.com/createTask",
            "result_url": "https://api.anti-captcha.com/getTaskResult",
        })
    if twocap_key:
        phase1_providers.append({
            "provider": "2captcha",
            "api_key": twocap_key,
            "task_type": "RecaptchaV2EnterpriseTaskProxyless",
            "create_url": "https://api.2captcha.com/createTask",
            "result_url": "https://api.2captcha.com/getTaskResult",
        })
    parallel_login_backups = (
        _page_action == "login"
        and not _conservative_login_captcha
        and _cfg_bool("captcha_parallel_backups_on_login", True)
    )
    if parallel_login_backups and capmon_key:
        phase1_providers.append({
            "provider": "capmonster",
            "api_key": capmon_key,
            "task_type": "RecaptchaV2EnterpriseTaskProxyless",
            "create_url": "https://api.capmonster.cloud/createTask",
            "result_url": "https://api.capmonster.cloud/getTaskResult",
        })
    if parallel_login_backups and capsolver_key:
        phase1_providers.append({
            "provider": "capsolver",
            "api_key": capsolver_key,
            "task_type": "ReCaptchaV2EnterpriseTaskProxyless",
            "create_url": "https://api.capsolver.com/createTask",
            "result_url": "https://api.capsolver.com/getTaskResult",
        })

    # 3.1 — Reordenar pela performance histórica: o melhor provider vai primeiro
    # Após dados suficientes, o router escolhe o mais rápido com rate >= 80%.
    best_p1 = captcha_router.get_best_service([p["provider"] for p in phase1_providers])
    if best_p1:
        phase1_providers.sort(key=lambda p: 0 if p["provider"] == best_p1 else 1)
        logger.info(f"[Captcha] 🎯 CAPTCHARouter: provider preferido = {best_p1}")

    if phase1_providers:
        n = len(phase1_providers)
        logger.info(f"[Captcha] Step 1/2: Race ({', '.join(p['provider'] for p in phase1_providers)}) em paralelo...")
        phase1_cancel_event = threading.Event()
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=n)
        try:
            futures = {
                executor.submit(
                    _solve_single,
                    p["provider"], p["api_key"], p["task_type"],
                    p["create_url"], p["result_url"],
                    (
                        _timeout_primary_s if p["provider"] == "anti-captcha"
                        else _timeout_secondary_s if p["provider"] == "2captcha"
                        else _timeout_fallback_s
                    ),
                    phase1_cancel_event
                ): p["provider"]
                for p in phase1_providers
            }
            winner_token = None
            winner_provider = None
            phase1_wait_s = max(
                1.0,
                min(
                    max(_timeout_primary_s, _timeout_secondary_s) + 5.0,
                    _global_deadline - _time.time() + 1.0,
                )
            )
            try:
                for future in concurrent.futures.as_completed(futures, timeout=phase1_wait_s):
                    provider_name = futures[future]
                    try:
                        token = future.result()
                        if token and not winner_token:
                            winner_token = token
                            winner_provider = provider_name
                            phase1_cancel_event.set()
                            logger.info(f"[Captcha] ✅ Solved: {provider_name} (WINNER dual-service)")
                            _captcha_record(provider_name, True, 0, winner=True)
                            for other_future in futures:
                                if other_future is not future:
                                    other_future.cancel()
                            break
                    except Exception:
                        pass
            except concurrent.futures.TimeoutError:
                logger.warning(
                    "[Captcha] Dual-service excedeu o tempo maximo configurado; "
                    "a abortar fase primaria para nao prender o login."
                )
        finally:
            phase1_cancel_event.set()
            executor.shutdown(wait=False, cancel_futures=True)

        if winner_token:
            # Log estatísticas a cada 10 solves (stats legacy + router)
            total_wins = sum(s["wins"] for s in captcha_stats.values())
            if total_wins % 10 == 0:
                logger.info(captcha_stats_report())
                logger.info(captcha_router.report())
            return winner_token

        if _conservative_login_captcha:
            logger.warning(
                "[Captcha] Login em modo conservador: nenhum provider primário "
                "resolveu a tempo. Vou abortar antes de tentar CapMonster/"
                "CapSolver para não gastar uma tentativa /login com fallback "
                "menos confiável."
            )
            raise CaptchaTokenExpired(
                "login CAPTCHA unresolved by primary providers within safe budget; "
                "backup solvers skipped to protect remaining MNE reCAPTCHA allowance"
            )

        if parallel_login_backups:
            logger.warning(
                "[Captcha] Todos os providers configurados para login paralelo "
                "falharam/expiraram dentro do orçamento seguro; não há fallback tardio útil."
            )
            logger.error(captcha_stats_report())
            raise Exception("[Captcha] Todos os providers paralelos falharam no login.")

    # ─── FASE 2: BACKUP — CapMonster ────────────────────────────────────────────
    if capmon_key:
        remaining_budget = _global_deadline - _time.time()
        if remaining_budget <= 5:
            logger.warning("[Captcha] Sem tempo util restante para CapMonster backup.")
        else:
            logger.info("[Captcha] Step 2/2: CapMonster (backup)...")
            token = _solve_single(
                "capmonster", capmon_key,
                "RecaptchaV2EnterpriseTaskProxyless",
                "https://api.capmonster.cloud/createTask",
                "https://api.capmonster.cloud/getTaskResult",
                min(_timeout_fallback_s, remaining_budget),
            )
            if token:
                logger.info("[Captcha] ✅ Solved: CapMonster")
                _captcha_record("capmonster", True, 0, winner=True)
                return token

    # ─── FASE 3: ÚLTIMO RECURSO — CapSolver ─────────────────────────────────────
    if capsolver_key:
        remaining_budget = _global_deadline - _time.time()
        if remaining_budget <= 5:
            logger.warning("[Captcha] Sem tempo util restante para CapSolver fallback.")
        else:
            logger.info("[Captcha] Step 3/3: CapSolver (último recurso)...")
            token = _solve_single(
                "capsolver", capsolver_key,
                "ReCaptchaV2EnterpriseTaskProxyless",
                "https://api.capsolver.com/createTask",
                "https://api.capsolver.com/getTaskResult",
                min(_timeout_fallback_s, remaining_budget),
            )
            if token:
                logger.info("[Captcha] ✅ Solved: CapSolver")
                _captcha_record("capsolver", True, 0, winner=True)
                return token

    # Todos falharam
    logger.error(captcha_stats_report())
    raise Exception("[Captcha] Todos os providers falharam (Anti-Captcha, 2Captcha, CapMonster, CapSolver).")
    # --- FUNÇÃO UNIFICADA DE PREENCHIMENTO (SMART FILL) ---
# (NÍVEL GLOBAL - SEM INDENTAÇÃO)
async def smart_fill_field(page, selector: str, value: str, description: str = "Campo"):
    """
    Preenche qualquer campo, forçando remoção de readonly/disabled.
    """
    try:
        locator = page.locator(selector)
        
        # 1. Espera o elemento existir no DOM
        await locator.wait_for(state="attached", timeout=5000)
        
        # 2. INJEÇÃO AGRESSIVA: Remove bloqueios via JS
        # Isso resolve o erro "element is not enabled" e "readonly"
        await page.evaluate(f"""
            (sel) => {{
                let el = document.querySelector(sel);
                if(el) {{
                    el.removeAttribute('readonly');
                    el.removeAttribute('disabled');
                    el.removeAttribute('aria-disabled');
                    el.classList.remove('disabled');
                    el.style.display = 'block';
                    el.style.visibility = 'visible';
                    el.style.pointerEvents = 'auto';
                }}
            }}
        """, selector)

        # Pequena pausa para o JS processar
        await page.wait_for_timeout(100)

        # 3. Detecta Tipo
        tag_name = await locator.evaluate("el => el.tagName")
        
        if tag_name == "SELECT":
            # --- DROPDOWNS ---
            # Tenta seleção forçada
            await locator.select_option(value=str(value), force=True, timeout=3000)
            
            # Verifica se funcionou
            current_val = await locator.input_value()
            if current_val == str(value):
                await locator.evaluate("el => { el.dispatchEvent(new Event('change', { bubbles: true })); }")
                logger.info(f"[Form] ✅ {description} selecionado: {value}")
                return True
            else:
                # Fallback: Injeta valor direto no select (JS Puro)
                await page.evaluate(f"""
                    ([sel, val]) => {{
                        let el = document.querySelector(sel);
                        if(el) {{
                            el.value = val;
                            el.dispatchEvent(new Event('change', {{ bubbles: true }}));
                        }}
                    }}
                """, [selector, value])
                logger.info(f"[Form] ✅ {description} forçado via JS: {value}")
                return True
        else:
            # --- INPUTS ---
            # Tenta clicar (pode falhar se ainda tiver bloqueio visual)
            try:
                await locator.click(force=True, timeout=1000)
            except:
                pass # Ignora erro de clique, vamos direto para injeção

            # Limpa e injeta valor (Funciona mesmo em readonly)
            await page.evaluate(f"""
                ([sel, val]) => {{
                    let el = document.querySelector(sel);
                    if(el) {{
                        el.value = val;
                        el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        el.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    }}
                }}
            """, [selector, value])
            
            logger.info(f"[Form] ✅ {description} injetado: {value}")
            return True

    except Exception as e:
        logger.warning(f"[Form] ❌ Erro em {description}: {e}")
        return False


async def _wait_select_ready(
    page,
    selector: str,
    description: str,
    expected_value: str = None,
    timeout_ms: int = 8000,
    poll_ms: int = 150,
):
    """
    Espera que um <select> esteja realmente PRONTO para ser preenchido:
      1) existe no DOM,
      2) está visível (display!=none, offsetParent!=null),
      3) está habilitado (não disabled, não readonly),
      4) tem >1 option (i.e. as options já foram populadas pelo JS da página).
    Se `expected_value` for passado, exige também que essa option exista no <select>.

    Isto resolve o caso em que campos dependentes (cascading dropdowns) são
    preenchidos antes da página os ter realmente gerado/povoado, o que faz o
    Questionário aceitar o submit, redirecciona o URL para /Formulario, mas o
    servidor devolve novamente o HTML do Questionário (shadow-redirect / soft-block).
    """
    import time as _t
    deadline = _t.monotonic() + (timeout_ms / 1000.0)
    last_state = {"exists": False, "visible": False, "enabled": False, "options": 0, "has_expected": False}

    while _t.monotonic() < deadline:
        try:
            state = await page.evaluate(
                """
                ([sel, expected]) => {
                    const el = document.querySelector(sel);
                    if (!el) return {exists:false, visible:false, enabled:false, options:0, has_expected:false};
                    const cs = window.getComputedStyle(el);
                    const visible = cs.display !== 'none'
                                 && cs.visibility !== 'hidden'
                                 && el.offsetParent !== null;
                    const enabled = !el.disabled && !el.hasAttribute('readonly');
                    const opts = el.options ? el.options.length : 0;
                    let has_expected = true;
                    if (expected !== null && expected !== undefined && expected !== '') {
                        has_expected = false;
                        for (let i = 0; i < opts; i++) {
                            if (el.options[i].value === expected) { has_expected = true; break; }
                        }
                    }
                    return {exists:true, visible, enabled, options:opts, has_expected};
                }
                """,
                [selector, expected_value],
            )
        except Exception:
            state = last_state
        last_state = state
        if state.get("exists") and state.get("visible") and state.get("enabled") \
                and state.get("options", 0) > 1 and state.get("has_expected"):
            logger.info(
                f"[Form] ⏳→✅ {description} pronto: "
                f"options={state['options']} visível={state['visible']} "
                f"habilitado={state['enabled']} has_expected={state['has_expected']}"
            )
            return True
        await page.wait_for_timeout(poll_ms)

    logger.warning(
        f"[Form] ⏰ {description} NÃO ficou pronto em {timeout_ms}ms — "
        f"estado final: {last_state}. Vai tentar preencher mesmo assim, "
        "mas o submit pode ser rejeitado pelo MNE como sessão inválida."
    )
    return False


async def _fill_questionario_select(
    page,
    selector: str,
    value: str,
    description: str,
    wait_timeout_ms: int = 8000,
):
    """
    Versão consciente de cascading dropdowns: espera o <select> estar pronto
    (visível, habilitado, com options + opção `value` presente) e SÓ DEPOIS
    chama `smart_fill_field`. Verifica no fim se o valor ficou aplicado.
    Devolve True/False.
    """
    ready = await _wait_select_ready(
        page, selector, description,
        expected_value=value, timeout_ms=wait_timeout_ms,
    )
    ok = await smart_fill_field(page, selector, value, description)
    try:
        actual = await page.evaluate(
            "(sel) => { const el = document.querySelector(sel); return el ? el.value : null; }",
            selector,
        )
    except Exception:
        actual = None
    if actual != value:
        logger.warning(
            f"[Form] ⚠️ {description}: valor após preenchimento={actual!r} "
            f"(esperado={value!r}, ready={ready}). Tentando reaplicar via JS..."
        )
        try:
            await page.evaluate(
                """
                ([sel, val]) => {
                    const el = document.querySelector(sel);
                    if (el) {
                        el.value = val;
                        el.dispatchEvent(new Event('change', {bubbles:true}));
                    }
                }
                """,
                [selector, value],
            )
            await page.wait_for_timeout(150)
            actual = await page.evaluate(
                "(sel) => { const el = document.querySelector(sel); return el ? el.value : null; }",
                selector,
            )
        except Exception:
            pass
    if actual == value:
        return True
    logger.error(
        f"[Form] ❌ {description}: NÃO foi possível aplicar valor {value!r} "
        f"(actual={actual!r}). Este campo vai falhar a validação no MNE."
    )
    return False


async def _ensure_questionario_progression(
    page,
    selector: str,
    value: str,
    description: str,
    next_selector: str = None,
    wait_timeout_ms: int = 7000,
):
    """
    Em alguns estados do Questionário, mudar o `<select>` não chega para
    disparar a próxima pergunta dependente. Quando sabemos qual é o próximo
    selector esperado e ele ainda não apareceu, forçamos `goNext(...)` uma vez.
    """
    if not next_selector:
        return True

    try:
        state = await page.evaluate(
            """
            ([sel, nextSel]) => {
                const match = sel.match(/#cb_question_(\\d+)$/);
                const rows = document.querySelectorAll('#table_quest tbody tr').length;
                return {
                    qid: match ? Number(match[1]) : null,
                    has_go_next: typeof goNext === 'function',
                    next_exists: !!(nextSel && document.querySelector(nextSel)),
                    row_count: rows,
                };
            }
            """,
            [selector, next_selector],
        )
    except Exception as exc:
        logger.warning(
            f"[Playwright] Questionário chain: falha ao inspecionar {description}: {exc}"
        )
        return False

    if not state or not state.get("qid") or not state.get("has_go_next"):
        return False
    if state.get("next_exists"):
        return True

    qid = int(state["qid"])
    logger.info(
        f"[Playwright] Questionário chain: forçando goNext({qid}, {value!r}) "
        f"após {description} -> espera {next_selector}"
    )
    for chain_attempt in range(1, 4):
        try:
            before_state = await page.evaluate(
                """
                (nextSel) => {
                    const rows = document.querySelectorAll('#table_quest tbody tr').length;
                    return {
                        row_count: rows,
                        next_exists: !!(nextSel && document.querySelector(nextSel)),
                    };
                }
                """,
                next_selector,
            )
        except Exception:
            before_state = {"row_count": None, "next_exists": False}

        try:
            await page.evaluate(
                """
                ([sel, val, qid]) => {
                    const el = document.querySelector(sel);
                    if (!el) return false;

                    el.value = val;
                    el.dispatchEvent(new Event('input', { bubbles: true }));
                    el.dispatchEvent(new Event('change', { bubbles: true }));

                    if (typeof goNext === 'function') {
                        goNext(qid, val);
                        return true;
                    }

                    return true;
                }
                """,
                [selector, value, qid],
            )

            await page.wait_for_function(
                """
                ([nextSel, previousRows]) => {
                    const rows = document.querySelectorAll('#table_quest tbody tr').length;
                    return !!(
                        (nextSel && document.querySelector(nextSel)) ||
                        (typeof previousRows === 'number' && rows > previousRows)
                    );
                }
                """,
                arg=[next_selector, before_state.get("row_count")],
                timeout=wait_timeout_ms,
            )

            try:
                after_state = await page.evaluate(
                    """
                    (nextSel) => {
                        const rows = document.querySelectorAll('#table_quest tbody tr').length;
                        return {
                            row_count: rows,
                            next_exists: !!(nextSel && document.querySelector(nextSel)),
                        };
                    }
                    """,
                    next_selector,
                )
            except Exception:
                after_state = {"row_count": None, "next_exists": False}

            if after_state.get("next_exists"):
                logger.info(
                    f"[Playwright] ✅ Questionário chain avançou após {description}: "
                    f"{next_selector} (tentativa {chain_attempt}/3)"
                )
                return True

            logger.info(
                f"[Playwright] Questionário chain: houve mutação após {description} "
                f"(rows {before_state.get('row_count')} -> {after_state.get('row_count')}), "
                f"mas {next_selector} ainda não apareceu. Vou tentar novamente."
            )
        except Exception as exc:
            logger.warning(
                f"[Playwright] Questionário chain não avançou após {description} "
                f"-> {next_selector} (tentativa {chain_attempt}/3): {exc}"
            )

        await page.wait_for_timeout(500 * chain_attempt)

    return False


async def _bootstrap_questionario_from_nationality(
    page,
    nationality_value: str,
    context_label: str = "",
):
    """
    Em alguns estados do Questionário, o MNE renderiza apenas a pergunta de
    nacionalidade já pré-seleccionada e não dispara automaticamente o AJAX que
    gera os restantes dropdowns dependentes. Forçamos esse bootstrap antes de
    esperar por `#cb_question_21` e afins.
    """
    label_suffix = f" ({context_label})" if context_label else ""
    try:
        state = await page.evaluate(
            """
            () => {
                const cb1 = document.querySelector('#cb_question_1');
                const cb21 = document.querySelector('#cb_question_21');
                const cb2 = document.querySelector('#cb_question_2');
                const rows = document.querySelectorAll('#table_quest tbody tr').length;
                return {
                    has_cb1: !!cb1,
                    cb1_value: cb1 ? cb1.value : null,
                    has_dependent: !!(cb21 || cb2),
                    row_count: rows,
                    has_go_next: typeof goNext === 'function',
                };
            }
            """
        )
    except Exception as exc:
        logger.warning(
            f"[Playwright] Bootstrap Questionário{label_suffix} falhou ao "
            f"inspeccionar o DOM: {exc}"
        )
        return False

    if not state.get("has_cb1"):
        logger.warning(
            f"[Playwright] Bootstrap Questionário{label_suffix}: "
            "#cb_question_1 não existe no DOM."
        )
        return False

    if state.get("has_dependent"):
        return True

    current_nat = state.get("cb1_value")
    target_nat = (
        current_nat
        if current_nat not in (None, "", "-1", "0")
        else str(nationality_value or "CPV")
    )

    if current_nat in (None, "", "-1", "0"):
        ok = await _fill_questionario_select(
            page,
            "#cb_question_1",
            target_nat,
            f"Nacionalidade{label_suffix}",
            wait_timeout_ms=8000,
        )
        if not ok:
            return False

    logger.info(
        f"[Playwright] Bootstrap Questionário{label_suffix}: "
        f"forçando cadeia AJAX a partir da nacionalidade={target_nat!r} "
        f"(rows={state.get('row_count')}, goNext={state.get('has_go_next')})."
    )
    try:
        await page.evaluate(
            """
            (nat) => {
                const cb1 = document.querySelector('#cb_question_1');
                if (!cb1) return false;
                if (nat && nat !== '-1' && nat !== '0') {
                    cb1.value = nat;
                }
                if (typeof goNext === 'function') {
                    goNext(1, cb1.value);
                } else {
                    cb1.dispatchEvent(new Event('change', { bubbles: true }));
                }
                return true;
            }
            """,
            target_nat,
        )
    except Exception as exc:
        logger.warning(
            f"[Playwright] Bootstrap Questionário{label_suffix} não conseguiu "
            f"disparar o onchange de nacionalidade: {exc}"
        )
        return False

    for bootstrap_try in range(2):
        try:
            await page.wait_for_function(
                """
                () => {
                    return !!document.querySelector('#cb_question_21')
                        || !!document.querySelector('#cb_question_2');
                }
                """,
                timeout=7000,
            )
            logger.info(
                f"[Playwright] ✅ Bootstrap Questionário{label_suffix}: "
                "perguntas dependentes geradas."
            )
            return True
        except Exception:
            if bootstrap_try == 0:
                logger.warning(
                    f"[Playwright] Bootstrap Questionário{label_suffix}: "
                    "o AJAX pareceu responder mas os selectors dependentes "
                    "não surgiram; vou disparar goNext(1, nacionalidade) "
                    "uma segunda vez."
                )
                try:
                    await page.evaluate(
                        """
                        (nat) => {
                            const cb1 = document.querySelector('#cb_question_1');
                            if (!cb1) return false;
                            if (nat && nat !== '-1' && nat !== '0') {
                                cb1.value = nat;
                            }
                            if (typeof goNext === 'function') {
                                goNext(1, cb1.value);
                                return true;
                            }
                            cb1.dispatchEvent(new Event('change', { bubbles: true }));
                            return true;
                        }
                        """,
                        target_nat,
                    )
                    await page.wait_for_timeout(500)
                    continue
                except Exception as exc:
                    logger.warning(
                        f"[Playwright] Bootstrap Questionário{label_suffix}: "
                        f"segunda tentativa de goNext falhou: {exc}"
                    )
            logger.warning(
                f"[Playwright] Bootstrap Questionário{label_suffix}: "
                "perguntas dependentes não apareceram a tempo."
            )
            return False


async def _questionario_runtime_state(page):
    """
    Inspecciona rapidamente o HTML servido em `/Questionario` para distinguir:
    formulário real, página de sessão perdida, ou outro estado intermédio.
    """
    try:
        return await page.evaluate(
            """
            () => {
                const body = document.body ? document.body.innerText : '';
                const text = body || '';
                const sessionLost = /Perdeu a sessão|Session lost|Session perdue|Сесія втрачена|Сессия потеряна/i.test(text);
                return {
                    url: window.location.href,
                    title: document.title || '',
                    has_quest_form: !!document.querySelector('#questForm'),
                    has_visto_form: !!document.querySelector('#vistoForm'),
                    session_lost: sessionLost,
                    text: text.slice(0, 4000),
                };
            }
            """
        )
    except Exception as exc:
        return {
            "url": page.url,
            "title": "",
            "has_quest_form": False,
            "has_visto_form": False,
            "session_lost": False,
            "text": f"<runtime_state_error: {exc}>",
        }


async def _recover_questionario_session_lost(page):
    """
    Algumas sessões validam a homepage mas `/Questionario` devolve momentaneamente
    o HTML "Perdeu a sessão". Tentamos UMA recuperação leve refrescando a
    homepage antes de repetir a navegação.
    """
    logger.warning(
        "[Playwright] /Questionario devolveu página de sessão perdida. "
        "Tentando recuperar a sessão pela homepage antes de desistir."
    )
    try:
        await page.goto(
            f"{BASE_URL}/VistosOnline/",
            wait_until="domcontentloaded",
            timeout=45000,
        )
    except Exception as exc:
        logger.warning(
            f"[Playwright] Recovery Questionario/session-lost falhou ao abrir homepage: {exc}"
        )
        return False

    try:
        await page.wait_for_timeout(1200)
        state = await _questionario_runtime_state(page)
        cur_url = state.get("url") or page.url
        text_norm = _short_normalized_text(state.get("text") or "")
        if "Authentication.jsp" in cur_url or "sessionLost" in cur_url or state.get("session_lost"):
            logger.warning(
                "[Playwright] Recovery Questionario/session-lost não restaurou "
                f"a sessão. URL={cur_url} text={text_norm!r}"
            )
            return False

        unavailable, title, text = await _page_service_unavailable_snapshot(page)
        if unavailable:
            logger.warning(
                "[Playwright] Recovery Questionario/session-lost encontrou "
                f"indisponibilidade. title={title[:80]!r} text={_short_normalized_text(text)!r}"
            )
            return False

        logger.info(
            f"[Playwright] ✅ Recovery Questionario/session-lost restaurou contexto na homepage: {cur_url}"
        )
        return True
    except Exception as exc:
        logger.warning(
            f"[Playwright] Recovery Questionario/session-lost falhou a validar homepage: {exc}"
        )
        return False


async def _open_questionario_via_portal_nav(page):
    """
    Tenta abrir o Questionario usando a navegação já presente no portal autenticado
    em vez de fazer outro GET directo ao endpoint.
    """
    logger.info(
        "[Playwright] Recovery Questionario/session-lost: "
        "tentando abrir via navegação do portal."
    )
    try:
        nav_result = await page.evaluate(
            """
            () => {
                const normalize = (value) =>
                    (value || '')
                        .normalize('NFD')
                        .replace(/[\\u0300-\\u036f]/g, '')
                        .toUpperCase()
                        .replace(/\\s+/g, ' ')
                        .trim();

                const wantedTexts = [
                    'SOLICITAR PEDIDO DE VISTO',
                    'QUESTIONARIO',
                    'QUESTIONARIO PARA OBTENCAO DO TIPO DE VISTO'
                ];

                const isGoodLabel = (text) =>
                    !!text &&
                    text.length <= 90 &&
                    wantedTexts.some((wanted) => text === wanted || text.startsWith(wanted + ' '));

                const hrefNode = document.querySelector('a[href*="Questionario"]');
                if (hrefNode && typeof hrefNode.click === 'function') {
                    hrefNode.click();
                    return { clicked: true, mode: 'href', text: normalize(hrefNode.innerText || hrefNode.textContent || '') };
                }

                const directClickables = Array.from(
                    document.querySelectorAll('a, button, [role="button"]')
                );
                for (const node of directClickables) {
                    const text = normalize(node.innerText || node.textContent || '');
                    if (!isGoodLabel(text)) continue;
                    if (typeof node.click === 'function') {
                        node.click();
                        return { clicked: true, mode: 'direct', text };
                    }
                }

                const textNodes = Array.from(
                    document.querySelectorAll('span, li, div')
                );
                for (const node of textNodes) {
                    const text = normalize(node.innerText || node.textContent || '');
                    if (!isGoodLabel(text)) continue;

                    const clickable =
                        node.closest('a, button, [role="button"], li') || node;
                    const clickableText = normalize(
                        clickable.innerText || clickable.textContent || ''
                    );
                    if (
                        clickable &&
                        clickable !== document.body &&
                        isGoodLabel(clickableText) &&
                        typeof clickable.click === 'function'
                    ) {
                        clickable.click();
                        return { clicked: true, mode: 'text', text };
                    }
                }

                return { clicked: false, mode: 'none', text: '' };
            }
            """
        )
    except Exception as exc:
        logger.warning(
            f"[Playwright] Recovery Questionario/session-lost: "
            f"falha ao tentar clicar nav do portal: {exc}"
        )
        return False

    if not (nav_result or {}).get("clicked"):
        logger.warning(
            "[Playwright] Recovery Questionario/session-lost: "
            "nav do portal não encontrada/clicável."
        )
        return False

    logger.info(
        "[Playwright] Recovery Questionario/session-lost: "
        f"nav clicada via {nav_result.get('mode')} "
        f"(texto={nav_result.get('text', '')[:80]!r})."
    )

    try:
        await page.wait_for_load_state("domcontentloaded", timeout=15000)
    except Exception:
        pass

    try:
        await page.wait_for_function(
            """
            () => {
                const text = document.body ? document.body.innerText || '' : '';
                return (
                    /Questionario/i.test(window.location.href) ||
                    !!document.querySelector('#questForm') ||
                    /Perdeu a sessão|Session lost|Session perdue|Сесія втрачена|Сессия потеряна/i.test(text)
                );
            }
            """,
            timeout=15000,
        )
    except Exception:
        pass

    state = await _questionario_runtime_state(page)
    cur_url = state.get("url") or page.url
    logger.info(
        "[Playwright] Recovery Questionario/session-lost: "
        f"estado após clique nav -> url={cur_url} "
        f"title={state.get('title', '')[:80]!r} "
        f"questForm={state.get('has_quest_form')} "
        f"session_lost={state.get('session_lost')}"
    )

    if "Authentication.jsp" in cur_url or "sessionLost" in cur_url:
        return False
    if state.get("has_quest_form") or "Questionario" in cur_url:
        return True
    if state.get("session_lost"):
        return True
    return False


async def playwright_login(username: str, password: str, solve_recaptcha_v2, proxy_raw: str, user_agent: str, captcha_key_index: int = 0):
    """
    Enhanced login using Playwright with playwright-stealth for improved CAPTCHA handling and form submission.
    Optimized for heavy load with semaphore-based concurrency control and resource management.
    
    Note: On first run, Playwright will download the browser binaries (~100-200MB).
    This is a one-time download that gets cached for future runs.
    """
    import time as time_module
    login_start_time = time_module.time()
    
    async with _get_playwright_semaphore():
        return await _playwright_login_internal(username, password, solve_recaptcha_v2, proxy_raw, user_agent, login_start_time, time_module, captcha_key_index)

async def _playwright_fill_second_form(page, user_agent: str, proxy_raw: str, captcha_key_index: int, username: str = None) -> bool:
    """
    Fill and submit the second visa application form (vistoForm) using Playwright,
    based on the mapping in second_form_mapping_2.json.
    Only fills empty/required fields (does not modify pre-populated fields).
    Implements human-like behavior similar to login form.
    """
    logger.info("[Playwright] Filling second form (vistoForm) via browser with human-like behavior...")
    # Aguardar vistoForm com timeout curto + retry. Antes eram 3×30s (=90s
    # cego), o que torrava tempo mesmo quando o MNE já tinha decidido não
    # servir o Formulario (shadow-redirect que mantém a URL /Formulario mas
    # devolve o HTML do Questionário — ver
    # browser_error_reports/grace6496_form_flow_error_20260417_063330.json).
    # Agora: 3×10s com inspecção activa da página entre tentativas.
    visto_loaded = False
    copy_questionario_submitted = False
    null_copy_restart_attempted = False

    async def _attempt_null_copy_restart() -> bool:
        """
        Algumas contas entram em /Formulario com o Questionário "por cópia do nº null".
        Antes tratávamos isso como fatal imediato. Em Windows voltou a aparecer de
        forma consistente, por isso tentamos UMA recuperação controlada:
          1. Restaurar a homepage autenticada
          2. Preferir a navegação do portal ("SOLICITAR PEDIDO DE VISTO")
          3. Fallback para GET directo de /Questionario
          4. Repreencher o Questionário uma única vez na mesma sessão
        Se mesmo assim não chegar ao #vistoForm, desistimos sem loop infinito.
        """
        cfg = scraper_settings or {}
        nationality_value = str(cfg.get("nationality_of_country", "CPV") or "CPV")
        country_of_residence = str(cfg.get("country_of_residence", "CPV") or "CPV")
        duration_str = str(cfg.get("duration_of_stay", "7") or "7")
        try:
            duration_days = int(duration_str.strip())
        except Exception:
            duration_days = 7
        stay_code = "SCH" if duration_days <= 90 else "TRAT"
        passport_type_code = "01"
        seasonal_work_code = "O"
        purpose_of_stay_code = "10"
        eu_family_code = "FAM_N"

        logger.warning(
            "[Playwright] 🔁 /Formulario em modo cópia com fonte 'null' — "
            "vou tentar UMA recuperação limpa via homepage autenticada -> "
            "nav do portal -> Questionario, sem novo login."
        )

        homepage_restored = await _recover_questionario_session_lost(page)
        if not homepage_restored:
            logger.warning(
                "[Playwright] Recovery null-copy: não foi possível restaurar a "
                "homepage autenticada. Vou tentar abrir o Questionario na mesma "
                "sessão como fallback."
            )

        clicked_nav = False
        if homepage_restored:
            clicked_nav = await _open_questionario_via_portal_nav(page)

        if clicked_nav:
            try:
                await page.wait_for_load_state("domcontentloaded", timeout=15000)
            except Exception:
                pass
            try:
                await page.wait_for_load_state("networkidle", timeout=8000)
            except Exception:
                pass
        else:
            logger.warning(
                "[Playwright] Recovery null-copy: nav do portal não abriu o "
                "Questionario — fallback para GET directo de /Questionario."
            )
            try:
                await page.goto(
                    f"{BASE_URL}/VistosOnline/Questionario",
                    timeout=45000,
                    wait_until="domcontentloaded",
                )
            except Exception as goto_questionario_err:
                logger.warning(
                    f"[Playwright] GET directo de /Questionario falhou no recovery: "
                    f"{goto_questionario_err}"
                )
                return False

        cur_url = page.url
        if "Authentication" in cur_url or "sessionLost" in cur_url:
            logger.warning(
                f"[Playwright] Recovery null-copy perdeu a sessão. URL actual: {cur_url}"
            )
            return False

        try:
            await page.wait_for_selector("#questForm", timeout=15000)
        except Exception as quest_wait_err:
            try:
                await page.wait_for_selector("#vistoForm", timeout=3000)
                logger.info(
                    "[Playwright] ✅ Recovery null-copy caiu directamente no #vistoForm."
                )
                return True
            except Exception:
                logger.warning(
                    f"[Playwright] Recovery null-copy não chegou ao Questionário limpo: "
                    f"{quest_wait_err}"
                )
                return False

        await _bootstrap_questionario_from_nationality(
            page, nationality_value, "recovery null-copy"
        )

        questionario_fields = []
        try:
            current_nat = await page.evaluate(
                "() => { const el = document.querySelector('#cb_question_1'); return el ? el.value : null; }"
            )
        except Exception:
            current_nat = None

        if current_nat in (None, "", "-1", "0"):
            questionario_fields.append(
                ("#cb_question_1", nationality_value, "Nacionalidade (recovery)")
            )
        questionario_fields.extend([
            ("#cb_question_21", country_of_residence, "País Residência (recovery)"),
            ("#cb_question_2", passport_type_code, "Tipo Passaporte (recovery)"),
            ("#cb_question_3", stay_code, "Duração Estadia (recovery)"),
        ])
        if country_of_residence == "FRA":
            questionario_fields.append(
                ("#cb_question_22", "N", "Questão Residência (recovery/FRA)")
            )
        questionario_fields.extend([
            ("#cb_question_5", seasonal_work_code, "Trabalho Sazonal (recovery)"),
            ("#cb_question_6", purpose_of_stay_code, "Propósito Estadia (recovery)"),
            ("#cb_question_16", eu_family_code, "Familiar UE (recovery)"),
        ])

        recovery_results = []
        for idx, (sel, val, desc) in enumerate(questionario_fields):
            ok = await _fill_questionario_select(page, sel, val, desc, wait_timeout_ms=8000)
            recovery_results.append((sel, val, desc, ok))
            if ok:
                next_sel = (
                    questionario_fields[idx + 1][0]
                    if idx + 1 < len(questionario_fields) else None
                )
                await _ensure_questionario_progression(
                    page, sel, val, desc, next_sel
                )
            await page.wait_for_timeout(200)

        try:
            recovery_snapshot = await page.evaluate(
                """
                (selectors) => selectors.map(sel => {
                    const el = document.querySelector(sel);
                    return {
                        sel,
                        value: el ? el.value : null,
                        options: el && el.options ? el.options.length : 0,
                    };
                })
                """,
                [sel for sel, _v, _d, _ok in recovery_results],
            )
        except Exception:
            recovery_snapshot = []

        recovery_missing = []
        for (sel, val, desc, _ok), state in zip(recovery_results, recovery_snapshot):
            if state.get("value") != val:
                recovery_missing.append(
                    f"{desc} ({sel}): esperado={val!r} actual={state.get('value')!r} "
                    f"options={state.get('options')}"
                )
        if recovery_missing:
            logger.error(
                "[Playwright] ⛔ Recovery null-copy: Questionário não validado — "
                + " | ".join(recovery_missing)
            )
            return False

        try:
            btn_visible = await page.evaluate(
                "() => { const btn = document.getElementById('btnContinue'); "
                "return !!(btn && btn.offsetParent !== null && btn.style.display !== 'none'); }"
            )
        except Exception:
            btn_visible = False
        if not btn_visible:
            try:
                await page.evaluate(
                    "() => { const btn = document.getElementById('btnContinue'); if (btn) btn.style.display = 'block'; }"
                )
                await page.wait_for_timeout(300)
            except Exception:
                pass

        try:
            await page.locator("#btnContinue").click()
        except Exception as recovery_click_err:
            logger.warning(
                f"[Playwright] Recovery null-copy: falha ao clicar Continuar: {recovery_click_err}"
            )
            return False

        try:
            await page.wait_for_url("**/Formulario**", timeout=45000)
        except Exception:
            pass
        try:
            await page.wait_for_load_state("domcontentloaded", timeout=20000)
        except Exception:
            pass
        try:
            await page.wait_for_load_state("networkidle", timeout=10000)
        except Exception:
            pass

        try:
            await page.wait_for_selector("#vistoForm", timeout=15000)
            logger.info("[Playwright] ✅ Recovery null-copy conseguiu abrir #vistoForm.")
            return True
        except Exception as recovery_visto_err:
            try:
                recovery_title = (await page.title()) or ""
                recovery_body = await page.evaluate(
                    "() => document.body ? document.body.innerText.slice(0, 1200) : ''"
                )
            except Exception:
                recovery_title, recovery_body = "", ""
            recovery_body = _normalize_server_text(recovery_body)
            if (
                "Erro no acesso ao sistema" in recovery_body
                or "Error in access to the system" in recovery_body
            ):
                raise PostLoginFailure(
                    "[Playwright] Recovery null-copy reabriu o Questionario, mas o "
                    "servidor voltou a responder com a página 'Erro no acesso ao "
                    "sistema' em /Formulario?copy=true. A conta/sessão continuou "
                    "presa no ramo de cópia inválido."
                ) from recovery_visto_err
            logger.warning(
                f"[Playwright] Recovery null-copy não chegou ao #vistoForm: "
                f"{recovery_visto_err} | title={recovery_title!r} | url={page.url}"
            )
            return False

    for _attempt in range(3):
        try:
            await page.wait_for_selector("#vistoForm", timeout=10000)
            visto_loaded = True
            break
        except Exception:
            current_url = page.url
            if "sessionLost" in current_url or "Authentication" in current_url:
                raise RuntimeError(f"Sessão perdida ao aguardar vistoForm. URL: {current_url}")

            # Detectar shadow-redirect do WAF: URL=/Formulario mas conteúdo do
            # Questionário. Nesse caso o #vistoForm nunca vai aparecer.
            try:
                title = (await page.title()) or ""
                has_quest_form = await page.evaluate(
                    "() => !!document.querySelector('#questForm, form[name=\"questForm\"], #table_quest, #cb_question_1, #cb_question_21')"
                )
                page_html = await page.content()
            except Exception:
                title, has_quest_form, page_html = "", False, ""

            logger.warning(
                f"[Playwright] #vistoForm não visível (tentativa {_attempt+1}/3) — "
                f"url={current_url} | title={title[:80]!r} | questForm_presente={has_quest_form}"
            )

            if "/Formulario" in current_url and (
                "Questionário" in title or "Questionario" in title or has_quest_form
            ):
                # IMPORTANTE: NÃO submeter este Questionário de novo.
                # Logs anteriores (indlop3931 @ 13:49–13:50) provaram que
                # filling+POST aqui resulta em
                #   POST /VistosOnline/Formulario?copy=true
                #   →  "Erro no acesso ao sistema, tente mais tarde"
                # ou seja, é um SEGUNDO POST do mesmo fluxo, que o
                # servidor rejeita como duplicado / inválido.
                #
                # O texto "Novo pedido por cópia do nº null" indica que
                # esta conta NÃO tem um pedido anterior para copiar:
                # /Formulario abre em modo cópia mas sem source nº, e
                # nenhum preenchimento + submit por nós conseguirá
                # avançar daí. É uma decisão server-side baseada no
                # estado da conta.
                #
                # Acção correcta: fail fast e parquear o utilizador.
                # NÃO clicar múltiplas vezes nem fazer forcing em campos já
                # populados. No entanto, quando o MNE devolve um Questionário
                # "por cópia" legítimo dentro de /Formulario, podemos tentar
                # UMA continuação controlada usando o mesmo gating de campos
                # do Questionário principal, e só então desistir.
                try:
                    copy_mode_state = await page.evaluate(
                        """
                        () => {
                            const cb1 = document.getElementById('cb_question_1');
                            const cb21 = document.getElementById('cb_question_21');
                            const btn = document.getElementById('btnContinue');
                            const body = document.body ? document.body.innerText : '';
                            const rootText = document.documentElement ? (document.documentElement.innerText || '') : '';
                            const html = document.documentElement ? document.documentElement.outerHTML : '';
                            const haystack = [body, rootText, html].filter(Boolean).join('\\n');
                            const m = haystack.match(/por\\s+c[óo]pia\\s+do\\s+n[ºo]\\s*([A-Za-z0-9]+)/i);
                            return {
                                has_cb1: !!cb1 || html.indexOf('cb_question_1') !== -1,
                                cb1_options: cb1 && cb1.options ? cb1.options.length : 0,
                                cb1_value: cb1 ? (cb1.value || '') : null,
                                has_cb21: !!cb21 || html.indexOf('cb_question_21') !== -1,
                                cb21_value: cb21 ? (cb21.value || '') : null,
                                btn_continue_visible: !!(btn && btn.offsetParent !== null),
                                copy_text_present:
                                    /por\\s+c[óo]pia/i.test(haystack) ||
                                    /novo\\s+pedido\\s+por\\s+c[óo]pia/i.test(haystack),
                                copy_source_id: m ? m[1] : null,
                                asks_nacionalidade:
                                    haystack.indexOf('Qual a sua nacionalidade') !== -1 ||
                                    haystack.indexOf('cb_question_1') !== -1,
                            };
                        }
                        """
                    )
                except Exception:
                    copy_mode_state = {
                        "has_cb1": False, "cb1_options": 0,
                        "cb1_value": None, "has_cb21": False,
                        "cb21_value": None, "btn_continue_visible": False,
                        "copy_text_present": False, "copy_source_id": None,
                        "asks_nacionalidade": False,
                    }

                if (
                    not copy_mode_state.get("copy_text_present")
                    and page_html
                    and ("por cópia" in page_html or "por copia" in page_html or "Novo pedido por cópia" in page_html)
                ):
                    m = re.search(
                        r"por\s+c[óo]pia\s+do\s+n[ºo]\s*([A-Za-z0-9]+)",
                        page_html,
                        re.IGNORECASE,
                    )
                    copy_mode_state["copy_text_present"] = True
                    copy_mode_state["copy_source_id"] = m.group(1) if m else copy_mode_state.get("copy_source_id")

                if copy_mode_state.get("copy_text_present"):
                    src = copy_mode_state.get("copy_source_id")
                    src_norm = str(src).strip() if src is not None else ""
                    if src_norm.lower() in ("", "null"):
                        if not null_copy_restart_attempted:
                            null_copy_restart_attempted = True
                            recovered = await _attempt_null_copy_restart()
                            if recovered:
                                visto_loaded = True
                                break
                        raise PostLoginFailure(
                            f"[Playwright] /Formulario abriu em modo cópia com fonte "
                            f"inexistente ({src!r}). Conta sem pedido anterior copiável; "
                            "recovery via Questionario limpo não resolveu o estado server-side."
                        )
                    if copy_questionario_submitted:
                        raise PostLoginFailure(
                            f"[Playwright] /Formulario continuou em modo cópia após uma única "
                            f"tentativa controlada (fonte={src!r}). Evitando novo POST."
                        )

                    cfg = scraper_settings or {}
                    nationality_value = str(cfg.get("nationality_of_country", "CPV") or "CPV")
                    country_of_residence = str(cfg.get("country_of_residence", "CPV") or "CPV")
                    duration_str = str(cfg.get("duration_of_stay", "7") or "7")
                    try:
                        duration_days = int(duration_str.strip())
                    except Exception:
                        duration_days = 7
                    stay_code = "SCH" if duration_days <= 90 else "TRAT"
                    passport_type_code = "01"
                    seasonal_work_code = "O"
                    purpose_of_stay_code = "10"
                    eu_family_code = "FAM_N"

                    logger.warning(
                        "[Playwright] 🔁 /Formulario em modo cópia com fonte real detectado "
                        f"(fonte={src!r}, cb1={copy_mode_state.get('cb1_value')!r}, "
                        f"cb21={copy_mode_state.get('cb21_value')!r}). "
                        "Vou tentar uma continuação controlada do Questionário, "
                        "sem forcing em campos já preenchidos e com apenas 1 clique."
                    )

                    await _bootstrap_questionario_from_nationality(
                        page, nationality_value, "copy-mode"
                    )

                    copy_questionario_fields = []
                    current_nat = copy_mode_state.get("cb1_value")
                    if current_nat in (None, "", "-1", "0"):
                        copy_questionario_fields.append(
                            ("#cb_question_1", nationality_value, "Nacionalidade (cópia)")
                        )
                    else:
                        logger.info(
                            "[Playwright] Copy-mode: nacionalidade já definida no DOM "
                            f"({current_nat!r}) — não vou forçar novo valor."
                        )
                    copy_questionario_fields.extend([
                        ("#cb_question_21", country_of_residence, "País Residência (cópia)"),
                        ("#cb_question_2", passport_type_code, "Tipo Passaporte (cópia)"),
                        ("#cb_question_3", stay_code, "Duração Estadia (cópia)"),
                    ])
                    if country_of_residence == "FRA":
                        copy_questionario_fields.append(
                            ("#cb_question_22", "N", "Questão Residência (cópia/FRA)")
                        )
                    copy_questionario_fields.extend([
                        ("#cb_question_5", seasonal_work_code, "Trabalho Sazonal (cópia)"),
                        ("#cb_question_6", purpose_of_stay_code, "Propósito Estadia (cópia)"),
                        ("#cb_question_16", eu_family_code, "Familiar UE (cópia)"),
                    ])

                    copy_field_results = []
                    for idx, (sel, val, desc) in enumerate(copy_questionario_fields):
                        ok = await _fill_questionario_select(
                            page, sel, val, desc, wait_timeout_ms=8000
                        )
                        copy_field_results.append((sel, val, desc, ok))
                        if ok:
                            next_sel = (
                                copy_questionario_fields[idx + 1][0]
                                if idx + 1 < len(copy_questionario_fields) else None
                            )
                            await _ensure_questionario_progression(
                                page, sel, val, desc, next_sel
                            )
                        await page.wait_for_timeout(200)

                    try:
                        copy_snapshot = await page.evaluate(
                            """
                            (selectors) => selectors.map(sel => {
                                const el = document.querySelector(sel);
                                return {
                                    sel,
                                    value: el ? el.value : null,
                                    options: el && el.options ? el.options.length : 0,
                                    visible: !!(el && el.offsetParent !== null),
                                };
                            })
                            """,
                            [sel for sel, _v, _d, _ok in copy_field_results],
                        )
                    except Exception:
                        copy_snapshot = []

                    copy_missing = []
                    for (sel, val, desc, _ok), state in zip(copy_field_results, copy_snapshot):
                        if state.get("value") != val:
                            copy_missing.append(
                                f"{desc} ({sel}): esperado={val!r} "
                                f"actual={state.get('value')!r} options={state.get('options')}"
                            )
                    if copy_missing:
                        logger.error(
                            "[Playwright] ⛔ Questionário de cópia incompleto antes do Continuar — "
                            "NÃO vou clicar:\n  - " + "\n  - ".join(copy_missing)
                        )
                        raise PostLoginFailure(
                            "[Playwright] Questionário de cópia não pôde ser validado: "
                            + " | ".join(copy_missing)
                        )

                    logger.info(
                        f"[Playwright] ✅ Questionário de cópia pronto: "
                        f"{len(copy_field_results)} campos validados."
                    )

                    if not copy_mode_state.get("btn_continue_visible"):
                        try:
                            await page.evaluate(
                                "() => { const btn = document.getElementById('btnContinue'); if (btn) btn.style.display = 'block'; }"
                            )
                            await page.wait_for_timeout(300)
                        except Exception:
                            pass

                    copy_continue_clicks = 0
                    copy_continue_posts = 0

                    def _on_copy_request(req):
                        nonlocal copy_continue_posts
                        try:
                            if req.method == "POST" and ("/Questionario" in req.url or "/Formulario" in req.url):
                                copy_continue_posts += 1
                                logger.info(
                                    f"[Playwright] [copy-continue-count] POST observado "
                                    f"#{copy_continue_posts}: {req.method} {req.url}"
                                )
                        except Exception:
                            pass

                    try:
                        page.on("request", _on_copy_request)
                    except Exception:
                        pass

                    try:
                        btn_locator = page.locator("#btnContinue")
                        copy_continue_clicks += 1
                        copy_questionario_submitted = True
                        logger.info(
                            f"[Playwright] [copy-continue-count] Click #{copy_continue_clicks} "
                            "no Continuar do Questionário de cópia (esperado: exactamente 1)."
                        )
                        await btn_locator.click()
                        logger.info(
                            f"[Playwright] [copy-continue-count] Click #{copy_continue_clicks} "
                            "concluído. Aguardando resposta do fluxo de cópia..."
                        )
                        try:
                            await page.wait_for_load_state("domcontentloaded", timeout=20000)
                        except Exception as _copy_dom_err:
                            logger.warning(
                                f"[Playwright] domcontentloaded após copy-continue demorou >20s: "
                                f"{_copy_dom_err}"
                            )
                        try:
                            await page.wait_for_load_state("networkidle", timeout=15000)
                        except Exception:
                            pass

                        try:
                            await page.wait_for_selector("#vistoForm", timeout=15000)
                            visto_loaded = True
                            logger.info(
                                f"[Playwright] [copy-continue-count] ✅ vistoForm apareceu "
                                f"após o modo cópia: clicks={copy_continue_clicks} | "
                                f"POSTs={copy_continue_posts}."
                            )
                            break
                        except Exception as _copy_visto_err:
                            try:
                                copy_title_after = (await page.title()) or ""
                                copy_body_after = await page.evaluate(
                                    "() => document.body ? document.body.innerText.slice(0, 1200) : ''"
                                )
                            except Exception:
                                copy_title_after, copy_body_after = "", ""
                            if "Erro no acesso ao sistema" in copy_body_after:
                                raise PostLoginFailure(
                                    "[Playwright] /Formulario?copy devolveu 'Erro no acesso ao sistema' "
                                    "mesmo após continuação controlada do Questionário de cópia."
                                ) from _copy_visto_err
                            raise PostLoginFailure(
                                f"[Playwright] vistoForm não apareceu após o Questionário de cópia "
                                f"(fonte={src!r}, title={copy_title_after!r}, url={page.url})."
                            ) from _copy_visto_err
                    finally:
                        try:
                            page.remove_listener("request", _on_copy_request)
                        except Exception:
                            pass
                    if visto_loaded:
                        break

                # Não é o padrão "por cópia" mas mostra Questionário no
                # /Formulario — soft-block / sessão rejeitada.
                raise PostLoginFailure(
                    f"[Playwright] /Formulario devolveu conteúdo do Questionário "
                    f"(title={title!r}, questForm_presente={has_quest_form}, "
                    f"copy_mode={copy_mode_state}) — provável soft-block do MNE "
                    "ou estado de conta não suportado pelo bot. Sem segundo POST."
                )

            await page.wait_for_timeout(3000)
    if not visto_loaded:
        raise RuntimeError("[Playwright] #vistoForm não apareceu após 3 tentativas (~33s total)")
    
    reading_time = random.randint(1500, 3000)
    logger.info(f"[Playwright] Simulating form reading time: {reading_time/1000:.1f}s")
    await page.wait_for_timeout(reading_time)
    
    try:
        await page.mouse.move(random.randint(200, 800), random.randint(200, 600), steps=random.randint(10, 25))
        await page.wait_for_timeout(random.randint(200, 400))
        if random.random() < 0.3:
            await page.mouse.move(random.randint(300, 700), random.randint(300, 500), steps=random.randint(8, 20))
            await page.wait_for_timeout(random.randint(150, 300))
    except Exception:
        pass

    mapping_path = os.path.join(WORKING_DIR, "second_form_mapping_2.json")
    if not os.path.exists(mapping_path):
        raise FileNotFoundError(f"Second form mapping JSON not found: {mapping_path}")

    with open(mapping_path, "r", encoding="utf-8") as f:
        mapping_data = json.load(f)

    if scraper_settings:
        if 'consular_post_id' in scraper_settings:
            consular_post_id = scraper_settings['consular_post_id']
            if 'consular_post_id' in mapping_data and isinstance(mapping_data['consular_post_id'], list) and len(mapping_data['consular_post_id']) >= 2:
                mapping_data['consular_post_id'][1] = consular_post_id
                logger.info(f"[Playwright] Overriding consular_post_id (f0sf1) with config value: {consular_post_id}")
            for key, cfg in mapping_data.items():
                if isinstance(cfg, list) and len(cfg) >= 2 and cfg[0] == 'f0sf1':
                    cfg[1] = consular_post_id
                    logger.info(f"[Playwright] Overriding f0sf1 with config value: {consular_post_id}")
        
        if 'country_of_residence' in scraper_settings:
            country_of_residence = scraper_settings['country_of_residence']
            for key, cfg in mapping_data.items():
                if isinstance(cfg, list) and len(cfg) >= 2 and cfg[0] == 'pais_residencia':
                    cfg[1] = country_of_residence
                    logger.info(f"[Playwright] Overriding pais_residencia (country_of_residence) with config value: {country_of_residence}")
        
        if 'intended_date_of_arrival' in scraper_settings:
            intended_date = str(scraper_settings['intended_date_of_arrival']).replace('-', '/')
            for key, cfg in mapping_data.items():
                if isinstance(cfg, list) and len(cfg) >= 2 and cfg[0] == 'f30':
                    cfg[1] = intended_date
                    logger.info(f"[Playwright] Overriding f30 (intended_date_of_arrival) with config value: {intended_date}")
            
            if 'duration_of_stay' in scraper_settings:
                try:
                    date_parts = intended_date.split('/')
                    arrival_date = datetime(int(date_parts[0]), int(date_parts[1]), int(date_parts[2]))
                    days_to_stay = int(scraper_settings['duration_of_stay'])
                    departure_date = arrival_date + timedelta(days=days_to_stay)
                    departure_date_str = departure_date.strftime('%Y/%m/%d')
                    logger.info(
                        "[Playwright] Calculated f31 preview from config: %s "
                        "(readonly field will be left for page JS to auto-populate from f30/f25)",
                        departure_date_str,
                    )
                except Exception as e:
                    logger.warning(f"[Playwright] Error calculating departure date: {e}")
        
        if 'duration_of_stay' in scraper_settings:
            duration_of_stay = str(scraper_settings['duration_of_stay'])
            for key, cfg in mapping_data.items():
                if isinstance(cfg, list) and len(cfg) >= 2 and cfg[0] == 'f25':
                    cfg[1] = duration_of_stay
                    logger.info(f"[Playwright] Overriding f25 (duration_of_stay) with config value: {duration_of_stay}")

    field_values: Dict[str, str] = {}
    file_fields = {"foto", "file1", "file2", "file3", "file4"}
    for _, cfg in mapping_data.items():
        if not isinstance(cfg, list) or len(cfg) < 2:
            continue
        name, value = cfg[0], cfg[1]
        if name in file_fields:
            continue
        if value is None or value == "":
            continue
        field_values[name] = str(value)

    if field_values.get("f30") and field_values.get("f25") and "f31" in field_values:
        skipped_f31 = field_values.pop("f31")
        logger.info(
            "[Playwright] Skipping direct fill of readonly f31=%s; "
            "waiting for page JS to derive departure date from f30/f25.",
            skipped_f31,
        )

    logger.info(f"[Playwright] Will fill {len(field_values)} second-form fields across 6 tabs (only empty/required fields)...")
    audited_field_names = (
        "f0sf1", "f25", "f29", "f30", "f31",
        "cmbReferencia", "f34", "f34sf2", "f34sf5",
        "f45", "f46",
    )

    async def audit_second_form(stage: str):
        try:
            snapshot = await page.evaluate(
                """
                (names) => {
                    const activeTab = document.querySelector('li.active')?.id || null;
                    const fields = names.map((name) => {
                        let el = document.querySelector(`[name="${name}"]`);
                        if (!el) {
                            el = document.getElementById(name);
                        }
                        if (!el) {
                            return { name, missing: true };
                        }
                        return {
                            name,
                            value: el.value || '',
                            readOnly: !!el.readOnly,
                            disabled: !!el.disabled,
                            visible: !!(el.offsetParent !== null),
                            tagName: el.tagName || '',
                        };
                    });
                    return { activeTab, fields };
                }
                """,
                list(audited_field_names)
            )
            compact = " | ".join(
                (
                    f"{item['name']}=<missing>"
                    if item.get("missing")
                    else (
                        f"{item['name']}={item.get('value', '')!r} "
                        f"(vis={item.get('visible')}, ro={item.get('readOnly')}, "
                        f"dis={item.get('disabled')}, tag={item.get('tagName')})"
                    )
                )
                for item in snapshot.get("fields", [])
            )
            logger.info(
                f"[SecondFormAudit] {stage} | active_tab={snapshot.get('activeTab')}: {compact}"
            )
        except Exception as audit_err:
            logger.warning(f"[SecondFormAudit] Failed at stage '{stage}': {audit_err}")

    async def save_second_form_debug(stage: str):
        """Persist HTML/screenshot when key form values do not stick."""
        try:
            stamp = time.strftime("%Y%m%d_%H%M%S")
            safe_user = (username or "unknown").replace("/", "_").replace("\\", "_")

            html_dir = os.path.join(WORKING_DIR, "debug_html")
            os.makedirs(html_dir, exist_ok=True)
            html_path = os.path.join(html_dir, f"{safe_user}_second_form_{stage}_{stamp}.html")
            with open(html_path, "w", encoding="utf-8") as fh:
                fh.write(await page.content())
            logger.info("[SecondFormDebug] Saved HTML snapshot: %s", html_path)

            shot_dir = os.path.join(WORKING_DIR, "debug_screenshots")
            os.makedirs(shot_dir, exist_ok=True)
            shot_path = os.path.join(shot_dir, f"{safe_user}_second_form_{stage}_{stamp}.png")
            await page.screenshot(path=shot_path, full_page=True)
            logger.info("[SecondFormDebug] Saved screenshot: %s", shot_path)
        except Exception as dbg_err:
            logger.warning("[SecondFormDebug] Failed at stage '%s': %s", stage, dbg_err)

    async def ensure_key_second_form_fields(stage: str):
        expected = {
            name: field_values.get(name)
            for name in ("f0sf1", "f25", "f30")
            if field_values.get(name) not in (None, "")
        }
        if not expected:
            return True
        tracked_names = list(expected.keys())
        if "f31" not in tracked_names:
            tracked_names.append("f31")

        def _selector_for(name: str) -> str:
            return f'[name="{name}"]'

        async def _read_values():
            return await page.evaluate(
                """
                (names) => {
                    const result = {};
                    for (const name of names) {
                        let el = document.querySelector(`[name="${name}"]`);
                        if (!el) {
                            el = document.getElementById(name);
                        }
                        result[name] = {
                            missing: !el,
                            value: el ? (el.value || '') : '',
                            readOnly: !!(el && el.readOnly),
                            disabled: !!(el && el.disabled),
                            tagName: el ? (el.tagName || '') : '',
                        };
                    }
                    return result;
                }
                """,
                tracked_names,
            )

        current_values = await _read_values()
        missing_or_mismatch = [
            name
            for name, expected_value in expected.items()
            if current_values.get(name, {}).get("value", "") != str(expected_value)
        ]

        if not missing_or_mismatch:
            return True

        logger.warning(
            "[Playwright] Key second-form fields need repair at %s: %s",
            stage,
            {
                name: {
                    "expected": expected[name],
                    "actual": current_values.get(name, {}).get("value", ""),
                    "missing": current_values.get(name, {}).get("missing", True),
                }
                for name in missing_or_mismatch
            },
        )
        await save_second_form_debug(f"{stage}_needs_repair")

        label_map = {
            "f0sf1": "Consular Post",
            "f25": "Duration of stay",
            "f30": "Intended arrival date",
        }

        for name in missing_or_mismatch:
            await smart_fill_field(
                page,
                _selector_for(name),
                str(expected[name]),
                label_map.get(name, name),
            )

        await page.evaluate(
            """
            (expected) => {
                const byName = (name) => document.querySelector(`[name="${name}"]`) || document.getElementById(name);
                const dispatchAll = (el) => {
                    if (!el) return;
                    el.dispatchEvent(new Event('input', { bubbles: true }));
                    el.dispatchEvent(new Event('change', { bubbles: true }));
                    if (typeof el.onchange === 'function') {
                        try { el.onchange(); } catch (e) { console.warn('onchange error', e); }
                    }
                    el.dispatchEvent(new Event('blur', { bubbles: true }));
                    if (typeof el.onblur === 'function') {
                        try { el.onblur(); } catch (e) { console.warn('onblur error', e); }
                    }
                };

                for (const [name, value] of Object.entries(expected)) {
                    const el = byName(name);
                    if (!el) continue;
                    el.removeAttribute('readonly');
                    el.removeAttribute('disabled');
                    el.removeAttribute('aria-disabled');
                    if (el.tagName === 'SELECT') {
                        el.value = value;
                        el.setAttribute('value', value);
                        const opt = Array.from(el.options || []).find((option) => option.value === value);
                        if (opt) opt.selected = true;
                    } else {
                        el.value = value;
                        el.setAttribute('value', value);
                    }
                    dispatchAll(el);

                    if (name === 'f25' && typeof verifMaxDuracaoEstadia === 'function') {
                        try { verifMaxDuracaoEstadia(el, 'PT'); } catch (e) { console.warn('verifMaxDuracaoEstadia error', e); }
                    }
                    if (name === 'f30' && typeof validarChegadaPartida === 'function') {
                        try { validarChegadaPartida(el, 'PT', typeof tolerancia !== 'undefined' ? tolerancia : 5); } catch (e) { console.warn('validarChegadaPartida error', e); }
                    }
                }

                if (expected.f0sf1 && typeof ajaxFunction === 'function') {
                    try { ajaxFunction(expected.f0sf1); } catch (e) { console.warn('ajaxFunction error', e); }
                }
            }
            """,
            expected,
        )
        await page.wait_for_timeout(random.randint(250, 450))
        if expected.get("f30"):
            try:
                await page.wait_for_function(
                    """
                    () => {
                        const el = document.querySelector('[name="f31"]') || document.getElementById('f31');
                        return !!(el && (el.value || '').trim().length >= 10);
                    }
                    """,
                    timeout=5000,
                )
                logger.info("[Playwright] f31 auto-populated after f30 repair/validation.")
            except Exception as auto_departure_err:
                logger.warning(
                    "[Playwright] f31 did not auto-populate after f30 repair: %s",
                    auto_departure_err,
                )
        await audit_second_form(f"{stage}_repaired")

        final_values = await _read_values()
        final_mismatches = [
            f"{name}: expected={expected[name]!r}, actual={final_values.get(name, {}).get('value', '')!r}"
            for name in expected
            if final_values.get(name, {}).get("value", "") != str(expected[name])
        ]
        if final_mismatches:
            await save_second_form_debug(f"{stage}_final_mismatch")
            raise RuntimeError(
                "Core second-form fields not stable before submit: "
                + "; ".join(final_mismatches)
            )
        if expected.get("f30") and not final_values.get("f31", {}).get("value", "").strip():
            await save_second_form_debug(f"{stage}_f31_missing")
            raise RuntimeError(
                "Readonly departure field f31 stayed empty after filling f30/f25; "
                "site JS did not derive the date."
            )
        return True

    await audit_second_form("initial")
    
    async def switch_to_tab(tab_number: int):
        """Switch to the next tab by calling mudarTab() directly via JS — same as clicking 'Próxima página'."""
        tab_li_id = f"li{tab_number}"

        try:
            is_active = await page.evaluate(
                "(liId) => { const li = document.getElementById(liId); return li && li.classList.contains('active'); }",
                tab_li_id
            )

            if is_active:
                logger.debug(f"[Playwright] Tab {tab_number} already active, skipping switch...")
                return True

            # Call mudarTab(prev, current) directly — same as the 'Próxima página' footer button
            prev_tab = tab_number - 1
            await page.evaluate(f"mudarTab({prev_tab}, {tab_number})")
            await page.wait_for_timeout(random.randint(300, 600))

            is_now_active = await page.evaluate(
                "(liId) => { const li = document.getElementById(liId); return li && li.classList.contains('active'); }",
                tab_li_id
            )

            if is_now_active:
                logger.info(f"[Playwright] ✅ Switched to tab {tab_number}")
                return True
            else:
                logger.warning(f"[Playwright] Tab {tab_number} did not become active after mudarTab()")
                return False

        except Exception as e:
            logger.warning(f"[Playwright] Error switching to tab {tab_number}: {e}")
            return False
    
    async def fill_field_human_like(field_name: str, field_value: str):
        """Fill a single field with human-like mouse movement, clicking, and typing."""
        try:
            try:
                await page.wait_for_selector(f'[name="{field_name}"]', timeout=2000, state="attached")
            except Exception:
                pass
            
            field_locator = page.locator(f'[name="{field_name}"]')
            field_count = await field_locator.count()
            
            if field_count == 0:
                try:
                    await page.wait_for_selector(f'#{field_name}', timeout=2000, state="attached")
                except Exception:
                    pass
                field_locator = page.locator(f'#{field_name}')
                field_count = await field_locator.count()
            
            if field_count == 0:
                logger.info(f"[Playwright] Field '{field_name}' not found (tried name and ID), skipping...")
                return False
            
            is_populated = await page.evaluate(
                """
                (name) => {
                    // Try name first, then ID
                    let el = document.querySelector(`[name="${name}"]`);
                    if (!el) {
                        el = document.getElementById(name);
                    }
                    if (!el) return false;
                    
                    // Readonly/disabled text inputs like f31 may start empty and
                    // still need JS-assisted filling. Only skip them when they
                    // already carry a real value.
                    if (el.readOnly || (el.disabled && el.tagName !== 'SELECT')) {
                        if (el.type === 'checkbox' || el.type === 'radio') {
                            return el.checked;
                        }
                        return !!(el.value && el.value !== '');
                    }
                    
                    if (el.tagName === 'SELECT') {
                        // For select, empty string, '-1', '0', or default empty option means not populated
                        const value = el.value || '';
                        const isEmptyValue = !value || value === '' || value === '-1' || value === '0';
                        
                        // Check if it's the default empty option (first option with empty value)
                        const isDefaultEmpty = el.options.length > 0 && 
                                             el.options[0].value === '' && 
                                             value === '';
                        
                        // If empty or default empty, it's not populated - should fill
                        if (isEmptyValue || isDefaultEmpty) {
                            return false; // Not populated, should fill
                        }
                        
                        // Has a real value, don't modify
                        return true;
                    } else if (el.type === 'checkbox' || el.type === 'radio') {
                        return el.checked;
                    } else {
                        return el.value && el.value !== '';
                    }
                }
                """,
                field_name
            )
            
            if is_populated:
                logger.debug(f"[Playwright] Field '{field_name}' already populated or readonly, skipping...")
                return False

            # Skip fields that exist in DOM but are not visible (belong to another tab)
            field_box = await field_locator.bounding_box()
            if not field_box:
                logger.debug(f"[Playwright] Field '{field_name}' not visible (hidden/other tab), skipping...")
                return False

            try:
                field_box = await field_locator.bounding_box()
                if field_box:
                    target_x = field_box['x'] + field_box['width'] / 2 + random.randint(-10, 10)
                    target_y = field_box['y'] + field_box['height'] / 2 + random.randint(-5, 5)
                    await page.mouse.move(target_x, target_y, steps=random.randint(10, 20))
                    await page.wait_for_timeout(random.randint(150, 300))
            except Exception:
                pass
            
            field_type = await page.evaluate(
                """
                (name) => {
                    // Try name first, then ID
                    let el = document.querySelector(`[name="${name}"]`);
                    if (!el) {
                        el = document.getElementById(name);
                    }
                    if (!el) return 'unknown';
                    if (el.tagName === 'SELECT') return 'select';
                    if (el.type === 'checkbox' || el.type === 'radio') return 'checkbox';
                    return 'input';
                }
                """,
                field_name
            )
            
            if field_type == 'select':
                await field_locator.click(delay=random.randint(50, 150))
                await page.wait_for_timeout(random.randint(200, 400))
                
                option_check = await page.evaluate(
                    """
                    ([name, value]) => {
                        // Try name first, then ID
                        let el = document.querySelector(`[name="${name}"]`);
                        if (!el) {
                            el = document.getElementById(name);
                        }
                        if (!el || el.tagName !== 'SELECT') {
                            return {exists: false, reason: 'not a select element'};
                        }
                        const options = Array.from(el.options);
                        const matching = options.filter(opt => opt.value === value);
                        const allOptions = options.map(opt => ({ value: opt.value, text: opt.text.trim().substring(0, 50) }));
                        return {
                            exists: matching.length > 0,
                            optionCount: options.length,
                            allOptions: allOptions.slice(0, 10), // First 10 for logging
                            currentValue: el.value || ''
                        };
                    }
                    """,
                    [field_name, field_value]
                )
                
                if option_check.get('exists'):
                    try:
                        select_locator = page.locator(f'[name="{field_name}"]')
                        
                        await select_locator.select_option(value=field_value, timeout=30000, force=True)
                        
                        await page.wait_for_timeout(random.randint(100, 200))
                        
                        selected_value = None
                        for verify_attempt in range(3):
                            selected_value = await page.evaluate(
                                """
                                (name) => {
                                    // Try name first, then ID
                                    let el = document.querySelector(`[name="${name}"]`);
                                    if (!el) {
                                        el = document.getElementById(name);
                                    }
                                    return el ? el.value : null;
                                }
                                """,
                                field_name
                            )
                            if selected_value == field_value:
                                break
                            await page.wait_for_timeout(100)
                        
                        if selected_value == field_value:
                            await page.evaluate(
                                """
                                (name) => {
                                    // Try name first, then ID
                                    let el = document.querySelector(`[name="${name}"]`);
                                    if (!el) {
                                        el = document.getElementById(name);
                                    }
                                    if (el) {
                                        // Trigger change event to ensure onchange handlers are called
                                        const changeEvent = new Event('change', { bubbles: true });
                                        el.dispatchEvent(changeEvent);
                                        // Also call onchange directly if it exists
                                        if (el.onchange) {
                                            try {
                                                el.onchange();
                                            } catch (e) {
                                                console.warn('onchange error:', e);
                                            }
                                        }
                                    }
                                }
                                """,
                                field_name
                            )
                            logger.info(f"[Playwright] Selected '{field_name}': {field_value}")
                            if field_name in audited_field_names:
                                await audit_second_form(f"after_fill_{field_name}")
                            await page.wait_for_timeout(random.randint(500, 1000))
                            return True
                        else:
                            logger.warning(f"[Playwright] Selection verification failed for '{field_name}': expected '{field_value}', got '{selected_value}'")
                            option_check['exists'] = False
                    except Exception as select_err:
                        logger.warning(f"[Playwright] Failed to select '{field_name}' with value '{field_value}': {select_err}")
                        option_check['exists'] = False
                else:
                    logger.warning(f"[Playwright] Option '{field_value}' not found in '{field_name}'. Available options ({option_check.get('optionCount', 0)} total): {option_check.get('allOptions', [])[:5]}")
                
                if not option_check.get('exists'):
                    logger.warning(f"[Playwright] Option '{field_value}' not found in '{field_name}', selecting last available option...")
                    last_option_value = await page.evaluate(
                        """
                        (name) => {
                            // Try name first, then ID
                            let el = document.querySelector(`[name="${name}"]`);
                            if (!el) {
                                el = document.getElementById(name);
                            }
                            if (!el || el.tagName !== 'SELECT') return null;
                            const options = Array.from(el.options).filter(opt => opt.value && opt.value !== '' && opt.value !== '-1');
                            if (options.length === 0) return null;
                            return options[options.length - 1].value;
                        }
                        """,
                        field_name
                    )
                    if last_option_value:
                        select_locator = page.locator(f'[name="{field_name}"]')
                        await select_locator.select_option(value=last_option_value, timeout=30000, force=True)
                        await page.evaluate(
                            """
                            (name) => {
                                // Try name first, then ID
                                let el = document.querySelector(`[name="${name}"]`);
                                if (!el) {
                                    el = document.getElementById(name);
                                }
                                if (el) {
                                    const changeEvent = new Event('change', { bubbles: true });
                                    el.dispatchEvent(changeEvent);
                                    if (el.onchange) {
                                        try {
                                            el.onchange();
                                        } catch (e) {
                                            console.warn('onchange error:', e);
                                        }
                                    }
                                }
                            }
                            """,
                            field_name
                        )
                        logger.info(f"[Playwright] Selected '{field_name}' with fallback option: {last_option_value}")
                        if field_name in audited_field_names:
                            await audit_second_form(f"after_fill_{field_name}_fallback")
                        await page.wait_for_timeout(random.randint(500, 1000))
                        return True
                    else:
                        logger.warning(f"[Playwright] No valid options found in '{field_name}', skipping...")
                        return False
            else:
                await page.evaluate(
                    """
                    (name) => {
                        let el = document.querySelector(`[name="${name}"]`);
                        if (!el) {
                            el = document.getElementById(name);
                        }
                        if (!el) return;
                        el.removeAttribute('readonly');
                        el.removeAttribute('disabled');
                        el.removeAttribute('aria-disabled');
                    }
                    """,
                    field_name
                )
                await field_locator.click(delay=random.randint(50, 150))
                await page.wait_for_timeout(random.randint(200, 400))
            
            if field_type == 'checkbox':
                truthy = field_value not in ['0', 'N', 'false', 'False', '']
                await page.evaluate(
                    """
                    ([name, checked]) => {
                        const el = document.querySelector(`[name="${name}"]`);
                        if (el) {
                            el.checked = checked;
                            el.dispatchEvent(new Event('change', { bubbles: true }));
                        }
                    }
                    """,
                    [field_name, truthy]
                )
                logger.info(f"[Playwright] Set checkbox '{field_name}': {truthy}")
            else:
                await field_locator.fill(field_value)
                await page.evaluate(
                    """
                    ([name, value]) => {
                        let el = document.querySelector(`[name="${name}"]`);
                        if (!el) {
                            el = document.getElementById(name);
                        }
                        if (!el) return null;
                        el.value = value;
                        el.setAttribute('value', value);
                        el.dispatchEvent(new Event('input', { bubbles: true }));
                        el.dispatchEvent(new Event('change', { bubbles: true }));
                        if (typeof el.onchange === 'function') {
                            try {
                                el.onchange();
                            } catch (e) {
                                console.warn('onchange error:', e);
                            }
                        }
                        el.dispatchEvent(new Event('blur', { bubbles: true }));
                        if (typeof el.onblur === 'function') {
                            try {
                                el.onblur();
                            } catch (e) {
                                console.warn('onblur error:', e);
                            }
                        }
                        return el.value || '';
                    }
                    """,
                    [field_name, field_value]
                )
                logger.info(f"[Playwright] Filled '{field_name}'")
                if field_name == "f30":
                    try:
                        await field_locator.press("Tab", timeout=1500)
                    except Exception:
                        pass
                    try:
                        await page.wait_for_function(
                            """
                            () => {
                                const el = document.querySelector('[name="f31"]') || document.getElementById('f31');
                                return !!(el && (el.value || '').trim().length >= 10);
                            }
                            """,
                            timeout=5000,
                        )
                        logger.info("[Playwright] f31 auto-populated after filling f30.")
                    except Exception as auto_departure_err:
                        logger.warning(
                            "[Playwright] f31 did not auto-populate after filling f30: %s",
                            auto_departure_err,
                        )
                        try:
                            await page.evaluate(
                                """
                                ([arrivalValue, durationValue]) => {
                                    const form = document.forms['vistoForm'] || document.vistoForm;
                                    const f25 = (form && form.f25) || document.querySelector('[name="f25"]') || document.getElementById('f25');
                                    const f30 = (form && form.f30) || document.querySelector('[name="f30"]') || document.getElementById('f30');
                                    if (f25 && durationValue) {
                                        f25.value = durationValue;
                                        f25.setAttribute('value', durationValue);
                                        f25.dispatchEvent(new Event('input', { bubbles: true }));
                                        f25.dispatchEvent(new Event('change', { bubbles: true }));
                                        f25.dispatchEvent(new Event('blur', { bubbles: true }));
                                        if (typeof verifMaxDuracaoEstadia === 'function') {
                                            try { verifMaxDuracaoEstadia(f25, 'PT'); } catch (e) { console.warn('verifMaxDuracaoEstadia retry error', e); }
                                        }
                                    }
                                    if (f30) {
                                        f30.value = arrivalValue;
                                        f30.setAttribute('value', arrivalValue);
                                        if (form && form.f30) {
                                            form.f30.value = arrivalValue;
                                        }
                                        f30.focus();
                                        f30.dispatchEvent(new Event('input', { bubbles: true }));
                                        f30.dispatchEvent(new Event('change', { bubbles: true }));
                                        if (typeof validarChegadaPartida === 'function') {
                                            try { validarChegadaPartida(f30, 'PT', typeof tolerancia !== 'undefined' ? tolerancia : 5); } catch (e) { console.warn('validarChegadaPartida retry error', e); }
                                        }
                                        f30.dispatchEvent(new Event('blur', { bubbles: true }));
                                    }
                                }
                                """,
                                [field_value, field_values.get("f25", "")],
                            )
                            await page.wait_for_function(
                                """
                                () => {
                                    const el = document.querySelector('[name="f31"]') || document.getElementById('f31');
                                    return !!(el && (el.value || '').trim().length >= 10);
                                }
                                """,
                                timeout=3000,
                            )
                            logger.info("[Playwright] f31 auto-populated after fallback retry on f30.")
                        except Exception as retry_departure_err:
                            logger.warning(
                                "[Playwright] f30 fallback retry still did not populate f31: %s",
                                retry_departure_err,
                            )
                if field_name in audited_field_names:
                    await audit_second_form(f"after_fill_{field_name}")
                if field_name in ("f25", "f30"):
                    await page.wait_for_timeout(random.randint(250, 450))

            await page.wait_for_timeout(random.randint(100, 250))
            return True
            
        except Exception as e:
            logger.warning(f"[Playwright] Error filling field '{field_name}': {e}")
            return False
    
    tab_names = {
        1: "Identification",
        2: "Journey Doc.",
        3: "Journey",
        4: "Visa",
        5: "References",
        6: "Attachments"
    }
    
    total_filled = 0
    for tab_num in range(1, 7):
        tab_name = tab_names.get(tab_num, f"Tab {tab_num}")
        logger.info(f"[Playwright] Processing Tab {tab_num}: {tab_name}")

        if not await switch_to_tab(tab_num):
            logger.warning(f"[Playwright] Failed to switch to tab {tab_num}, continuing...")
            continue

        # Wait for tab content to actually be active/visible, not just a blind sleep
        try:
            await page.wait_for_selector('.tab_contents_active', timeout=4000)
            logger.debug(f"[Playwright] Tab {tab_num} content is active and ready")
        except Exception:
            logger.debug(f"[Playwright] Tab {tab_num} active selector not found, using fallback wait")
            await page.wait_for_timeout(500)

        tab_filled = 0
        field_items = list(enumerate(field_values.items()))
        tab_priority = {}
        if tab_num == 4:
            # On the visa tab, ensure duration is stable before validating arrival date.
            tab_priority = {"f24": 0, "f25": 1, "f30": 2, "f31": 3}
        field_items.sort(
            key=lambda item: (tab_priority.get(item[1][0], 1000), item[0])
        )
        for _, (field_name, field_value) in field_items:
            success = await fill_field_human_like(field_name, field_value)
            if success:
                tab_filled += 1
                total_filled += 1

        logger.info(f"[Playwright] ✅ Tab {tab_num} ({tab_name}): {tab_filled} fields filled")
        if tab_num == 4:
            await ensure_key_second_form_fields("after_tab_4")
        if tab_num in (3, 4, 5):
            await audit_second_form(f"after_tab_{tab_num}")

        if tab_num < 6:
            await page.wait_for_timeout(random.randint(400, 800))

    logger.info(f"[Playwright] Total: {total_filled} fields filled across all tabs")
    await ensure_key_second_form_fields("before_submit")
    await audit_second_form("before_submit")

    alert_count = 0
    expected_dialogs = 2
    alerts_handled = []
    dialog_complete = asyncio.Event()
    
    async def handle_dialog(dialog):
        nonlocal alert_count, alerts_handled, dialog_complete
        alert_count += 1
        dialog_type = dialog.type
        message = dialog.message
        logger.info(f"[Playwright] Confirm dialog #{alert_count}/{expected_dialogs} detected: type={dialog_type}, message={message[:200]}...")
        
        alerts_handled.append({
            'number': alert_count,
            'type': dialog_type,
            'message': message
        })
        
        await dialog.accept()
        logger.info(f"[Playwright] ✅ Confirm dialog #{alert_count} confirmed/accepted")
        
        if alert_count >= expected_dialogs:
            dialog_complete.set()
            logger.info(f"[Playwright] ✅ Both confirm dialogs have been handled")
    
    page.on("dialog", handle_dialog)
    logger.info("[Playwright] Dialog handler registered - will auto-confirm 2 confirm dialogs when submit button is clicked")

    review_time = random.randint(1000, 2000)
    logger.info(f"[Playwright] Simulating form review time before submit: {review_time/1000:.1f}s")
    await page.wait_for_timeout(review_time)
    
    btn_submit_locator = page.locator("#btnSubmit")
    await page.wait_for_selector("#btnSubmit", timeout=15000)
    
    button_state = await page.evaluate("""
        () => {
            const btn = document.querySelector('#btnSubmit');
            if (!btn) return { exists: false };
            return {
                exists: true,
                disabled: btn.disabled,
                visible: btn.offsetParent !== null,
                display: window.getComputedStyle(btn).display,
                visibility: window.getComputedStyle(btn).visibility,
                type: btn.type,
                tagName: btn.tagName
            };
        }
    """)
    
    logger.info(f"[Playwright] Submit button state: {button_state}")
    
    if not button_state.get('exists'):
        raise RuntimeError("Submit button #btnSubmit not found!")
    
    if button_state.get('disabled'):
        logger.warning("[Playwright] Submit button is disabled! Checking form validation...")
        await audit_second_form("submit_disabled")
        validation_errors = await page.evaluate("""
            () => {
                const errors = [];
                // Check for visible error messages
                const errorElements = document.querySelectorAll('.error, .alert-danger, [class*="error"], [class*="invalid"]');
                errorElements.forEach(el => {
                    if (el.offsetParent !== null) {
                        errors.push(el.textContent.trim());
                    }
                });
                // Check for required fields that are empty
                const requiredFields = document.querySelectorAll('[required], .obrigatorio');
                requiredFields.forEach(field => {
                    if (field.tagName === 'SELECT' && (!field.value || field.value === '')) {
                        errors.push(`Required select ${field.name || field.id} is empty`);
                    } else if (field.tagName === 'INPUT' && field.type !== 'checkbox' && field.type !== 'radio' && !field.value) {
                        errors.push(`Required input ${field.name || field.id} is empty`);
                    }
                });
                return errors;
            }
        """)
        if validation_errors:
            logger.warning(f"[Playwright] Form validation errors found: {validation_errors}")
        raise RuntimeError(f"Submit button is disabled. Validation errors: {validation_errors}")
    
    try:
        btn_box = await btn_submit_locator.bounding_box()
        if btn_box:
            target_x = btn_box['x'] + btn_box['width'] / 2 + random.randint(-8, 8)
            target_y = btn_box['y'] + btn_box['height'] / 2 + random.randint(-5, 5)
            await page.mouse.move(target_x, target_y, steps=random.randint(10, 20))
            await page.wait_for_timeout(random.randint(200, 400))
    except Exception:
        pass
    
    # Contador dedicado ao submit final do vistoForm (terceira "confirmação"
    # do fluxo: 1) login, 2) Continuar Questionário, 3) #btnSubmit do
    # vistoForm). Garantimos UM ÚNICO click + observamos POSTs na rede.
    final_submit_clicks = 0
    final_submit_posts = 0

    def _on_finalsubmit_req(req):
        nonlocal final_submit_posts
        try:
            if req.method == "POST" and (
                "/SubmeterVisto" in req.url
                or "/Formulario" in req.url
                or "/CriaPDF" in req.url
            ):
                final_submit_posts += 1
                logger.info(
                    f"[Playwright] [finalsubmit-count] POST "
                    f"#{final_submit_posts}: {req.method} {req.url}"
                )
        except Exception:
            pass
    try:
        page.on("request", _on_finalsubmit_req)
    except Exception:
        pass
    
    logger.info("[Playwright] Clicking #btnSubmit - this will trigger confirm dialogs that will be auto-accepted...")
    
    try:
        final_submit_clicks += 1
        logger.info(
            f"[Playwright] [finalsubmit-count] Click #{final_submit_clicks} no "
            "#btnSubmit do vistoForm (esperado: exactamente 1)."
        )
        await btn_submit_locator.click(delay=random.randint(100, 250))
        logger.info(
            f"[Playwright] [finalsubmit-count] Click #{final_submit_clicks} concluído "
            "— a aguardar diálogo de confirmação..."
        )
    except Exception as click_err:
        logger.warning(f"[Playwright] Button click error: {click_err}")
        try:
            page.remove_listener("request", _on_finalsubmit_req)
        except Exception:
            pass
        raise RuntimeError(f"Failed to click submit button: {click_err}")
    
    try:
        await asyncio.wait_for(dialog_complete.wait(), timeout=10.0)
        logger.info("[Playwright] ✅ Both confirm dialogs have been handled successfully")
    except asyncio.TimeoutError:
        logger.warning(f"[Playwright] ⚠️ Timeout waiting for confirm dialogs. Handled {alert_count}/{expected_dialogs} dialogs")
        if alert_count == 0:
            logger.warning("[Playwright] No dialogs were detected - files may have been attached, or form submitted differently")
        elif alert_count < expected_dialogs:
            logger.warning(f"[Playwright] Only {alert_count} dialog(s) appeared (expected {expected_dialogs}) - continuing anyway")
    
    await page.wait_for_timeout(random.randint(1000, 2000))
    
    if alert_count > 0:
        logger.info(f"[Playwright] ✅ Handled {alert_count} confirm dialog(s)")
        for alert_info in alerts_handled:
            logger.info(f"[Playwright]   - Dialog #{alert_info['number']}: {alert_info['type']} - {alert_info['message'][:150]}...")
    
    logger.info("[Playwright] Waiting for redirect after second form submission...")
    try:
        await page.wait_for_load_state("networkidle", timeout=30000)
        
        try:
            await page.wait_for_url(
                lambda url: "Formulario" not in url or "schedule" in url.lower() or "agendamento" in url.lower() or "captcha" in url.lower(),
                timeout=30000,
                wait_until="networkidle"
            )
        except Exception:
            await page.wait_for_timeout(3000)
        
        await page.wait_for_timeout(2000)
    except Exception as nav_err:
        logger.warning(f"[Playwright] Navigation wait error: {nav_err}, waiting with timeout...")
        await page.wait_for_timeout(5000)
    
    try:
        final_url = page.url
        logger.info(f"[Playwright] Second form submitted, current URL: {final_url}")
        
        if "chrome-error://" in final_url or "error" in final_url.lower():
            logger.warning(f"[Playwright] ⚠️ Detected error page URL: {final_url}")
            logger.info("[Playwright] Waiting longer for proper redirect...")
            await page.wait_for_timeout(5000)
            
            try:
                final_url = page.url
                logger.info(f"[Playwright] URL after additional wait: {final_url}")
            except Exception:
                logger.error("[Playwright] Page may have closed or navigated away")
    except Exception as url_err:
        logger.error(f"[Playwright] Error getting URL: {url_err}")
        final_url = None

    slots_data = None
    pdf_downloaded = False
    pdf_content_bytes = None
    
    async def handle_schedule_response(response):
        nonlocal slots_data, pdf_downloaded, pdf_content_bytes
        try:
            content_type = (response.headers.get('content-type') or '').lower()
            if response.status == 200 and 'application/pdf' in content_type:
                try:
                    body = await response.body()
                    if body and body.startswith(b'%PDF'):
                        pdf_content_bytes = body
                        pdf_downloaded = True
                        logger.info(f"[Playwright] ✅ PDF content received from {response.url[:80]}... ({len(pdf_content_bytes)} bytes)")
                        return
                except Exception:
                    pass
        except Exception:
            pass
        if '/VistosOnline/slots' in response.url:
            try:
                slots_data = await response.json()
                logger.info(f"[Playwright] 📋 Slots API Response: {slots_data}")
                logger.info(f"[Playwright] Available dates: {len(slots_data) if isinstance(slots_data, list) else 'N/A'}")
                if isinstance(slots_data, list) and len(slots_data) > 0:
                    logger.info(f"[Playwright] First date entry: {slots_data[0]}")
            except Exception as e:
                logger.warning(f"[Playwright] Could not parse slots response: {e}")
                try:
                    text = await response.text()
                    logger.info(f"[Playwright] Slots API Response (text): {text[:500]}")
                    _err_match = re.search(
                        r'"error"\s*:\s*"?(ReCaptchaError|error|secblock|RGPDError)"?',
                        text or "",
                        re.IGNORECASE,
                    )
                    if _err_match:
                        slots_data = {"error": _err_match.group(1)}
                        logger.warning(
                            "[Playwright] Normalized malformed slots error response into %r",
                            slots_data,
                        )
                except Exception:
                    pass
        elif '/VistosOnline/SubmeterVistoCriaPDF' in response.url:
            logger.info(f"[Playwright] 📄 PDF Request Response Status: {response.status}")
            if response.status == 200:
                try:
                    ct = response.headers.get('content-type', '')
                    if 'application/pdf' in ct or 'pdf' in ct.lower():
                        pdf_content_bytes = await response.body()
                        if pdf_content_bytes.startswith(b'%PDF'):
                            pdf_downloaded = True
                            logger.info(f"[Playwright] ✅ PDF content received ({len(pdf_content_bytes)} bytes)")
                        else:
                            logger.warning(f"[Playwright] Response is not a valid PDF (starts with: {pdf_content_bytes[:20]})")
                    else:
                        response_text = await response.text()
                        if 'MostrarPdf' in response_text or 'pdf' in response_text.lower():
                            logger.info("[Playwright] Response contains PDF reference - PDF may load in separate request")
                            pdf_downloaded = True
                        else:
                            logger.info(f"[Playwright] PDF Response preview: {response_text[:500]}")
                except Exception as pdf_err:
                    logger.warning(f"[Playwright] Error checking PDF response: {pdf_err}")
    
    page.on("response", handle_schedule_response)
    
    try:
        await _ui_wait(page, 2000)
        try:
            await page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass  # page may still be loading; continue to detect CAPTCHA anyway

        schedule_url = page.url
        logger.info(f"[Playwright] URL após vistoForm submit: {schedule_url}")
        # Auditoria final do submit do vistoForm
        try:
            page.remove_listener("request", _on_finalsubmit_req)
        except Exception:
            pass
        if final_submit_clicks != 1 or final_submit_posts > 1:
            logger.warning(
                f"[Playwright] [finalsubmit-count] AUDITORIA #btnSubmit: "
                f"clicks_nosso_lado={final_submit_clicks} | "
                f"POSTs_observados={final_submit_posts} (esperado: 1, POSTs ≤ 1)."
            )
        else:
            logger.info(
                f"[Playwright] [finalsubmit-count] ✅ #btnSubmit OK: "
                f"clicks=1 | POSTs={final_submit_posts}."
            )
        
        # Aguardar widget CAPTCHA do Schedule antes de detectar
        if 'Schedule' in schedule_url or 'posto_id' in schedule_url:
            try:
                await page.wait_for_selector('iframe[src*="recaptcha"], #captchaDiv, .g-recaptcha', timeout=15000, state="attached")
                await _ui_wait(page, 1500)
                logger.info("[Playwright] ✅ Schedule CAPTCHA widget detectado")
            except Exception as _sw:
                logger.warning(f"[Playwright] Schedule widget não apareceu: {_sw}")
                await _ui_wait(page, 3000)

        html = await page.content()
        lower = html.lower()
        current_url = page.url
        
        captcha_info = await page.evaluate("""
            () => {
                const result = {
                    type: null,
                    siteKey: null,
                    action: null,
                    hasRecaptcha: false,
                    hasHcaptcha: false,
                    hasRecaptchaV3: false,
                    details: {}
                };
                
                // Check for reCAPTCHA v2
                const recaptchaDiv = document.querySelector('.g-recaptcha[data-sitekey]');
                const recaptchaIframe = document.querySelector('iframe[src*="recaptcha"], iframe[src*="google.com/recaptcha"]');
                
                if (recaptchaDiv || recaptchaIframe) {
                    result.hasRecaptcha = true;
                    result.type = 'recaptcha_v2';
                    
                    if (recaptchaDiv) {
                        result.siteKey = recaptchaDiv.getAttribute('data-sitekey');
                        result.action = recaptchaDiv.getAttribute('data-action');
                    }
                    
                    if (recaptchaIframe && recaptchaIframe.src) {
                        const siteKeyMatch = recaptchaIframe.src.match(/[?&]k=([^&]+)/);
                        if (siteKeyMatch) result.siteKey = siteKeyMatch[1];
                        
                        const actionMatch = recaptchaIframe.src.match(/[?&]sa=([^&]+)/);
                        if (actionMatch) result.action = actionMatch[1];
                    }
                    
                    // Check if it's Enterprise (has enterprise in script or iframe)
                    const scripts = Array.from(document.querySelectorAll('script[src*="recaptcha"]'));
                    const hasEnterprise = scripts.some(s => s.src.includes('enterprise') || s.src.includes('enterprise.js'));
                    if (hasEnterprise || (window.grecaptcha && window.grecaptcha.enterprise)) {
                        result.type = 'recaptcha_v2_enterprise';
                    }
                }
                
                // Check for reCAPTCHA v3 (usually has action attribute and no visible checkbox)
                if (window.grecaptcha && typeof window.grecaptcha.execute === 'function') {
                    result.hasRecaptchaV3 = true;
                    if (!result.type) {
                        result.type = 'recaptcha_v3';
                    }
                }
                
                // Check for hCaptcha
                const hcaptchaDiv = document.querySelector('[data-sitekey][class*="h-captcha"], .h-captcha, iframe[src*="hcaptcha.com"]');
                if (hcaptchaDiv) {
                    result.hasHcaptcha = true;
                    result.type = 'hcaptcha';
                    result.siteKey = hcaptchaDiv.getAttribute('data-sitekey');
                }
                
                // Additional details
                result.details.grecaptchaExists = typeof window.grecaptcha !== 'undefined';
                result.details.hcaptchaExists = typeof window.hcaptcha !== 'undefined';
                result.details.recaptchaScripts = Array.from(document.querySelectorAll('script[src*="recaptcha"]')).map(s => s.src);
                result.details.hcaptchaScripts = Array.from(document.querySelectorAll('script[src*="hcaptcha"]')).map(s => s.src);
                
                return result;
            }
        """)
        
        captcha_type = captcha_info.get('type')
        site_key = captcha_info.get('siteKey')
        captcha_action = (captcha_info.get('action') or '').strip() or None

        logger.info(f"[Playwright] CAPTCHA type: {captcha_type}, sitekey: {site_key}")
        if captcha_action:
            logger.info(f"[Playwright] CAPTCHA action: {captcha_action}")
        
        if captcha_type:
            logger.info(f"[Playwright] 🔒 CAPTCHA detected after second form submission. Type: {captcha_type}")
            
            try:
                if captcha_type.startswith('recaptcha'):
                    await page.wait_for_selector('.g-recaptcha, iframe[src*="recaptcha"]', timeout=10000, state="attached")
                elif captcha_type == 'hcaptcha':
                    await page.wait_for_selector('[data-sitekey][class*="h-captcha"], .h-captcha, iframe[src*="hcaptcha.com"]', timeout=10000, state="attached")
                await page.wait_for_timeout(1000)
            except Exception:
                logger.warning("[Playwright] CAPTCHA widget not found immediately, proceeding anyway...")
            
            if not site_key and scraper_settings:
                site_key = scraper_settings.get('SITE_KEY')
            if not site_key:
                site_key = '6LdOB9crAAAAADT4RFruc5sPmzLKIgvJVfL830d4'
            
            logger.info(f"[Playwright] Starting CAPTCHA solving for type: {captcha_type}...")
            
            _sch_url = page.url if page.url and 'Schedule' in page.url else f"https://pedidodevistos.mne.gov.pt/VistosOnline/Schedule.jsp?posto_id={consular_post_id}"
            if captcha_type in ['recaptcha_v2', 'recaptcha_v2_enterprise']:
                captcha_token = solve_recaptcha_v2(
                    proxy_raw,
                    user_agent,
                    captcha_key_index=captcha_key_index,
                    page_url=_sch_url,
                    page_action="schedule",
                    enterprise_action=captcha_action,
                )
            elif captcha_type == 'recaptcha_v3':
                logger.warning("[Playwright] reCAPTCHA v3 detected - this may require different solving approach")
                captcha_token = solve_recaptcha_v2(
                    proxy_raw,
                    user_agent,
                    captcha_key_index=captcha_key_index,
                    page_url=_sch_url,
                    page_action="schedule",
                    enterprise_action=captcha_action,
                )
            elif captcha_type == 'hcaptcha':
                logger.error("[Playwright] hCaptcha detected - hCaptcha solving not yet implemented!")
                raise RuntimeError("hCaptcha solving is not yet implemented. Please solve manually.")
            else:
                logger.warning(f"[Playwright] Unknown CAPTCHA type: {captcha_type}, trying reCAPTCHA v2 solver...")
                captcha_token = solve_recaptcha_v2(
                    proxy_raw,
                    user_agent,
                    captcha_key_index=captcha_key_index,
                    page_url=_sch_url,
                    page_action="schedule",
                    enterprise_action=captcha_action,
                )
            
            if not captcha_token or len(captcha_token) < 100:
                raise RuntimeError(f"Invalid CAPTCHA token received (length: {len(captcha_token) if captcha_token else 0})")
            
            logger.info(f"[Playwright] ✅ CAPTCHA token obtained (length: {len(captcha_token)}) - injecting into page...")

            injection_result = await page.evaluate(
                """
                (token) => {
                    try {
                        if (!window.grecaptcha) {
                            return {success: false, error: 'grecaptcha not found'};
                        }
                        
                        // Store original getResponse if it exists
                        let originalGetResponse = null;
                        if (typeof window.grecaptcha.getResponse === 'function') {
                            originalGetResponse = window.grecaptcha.getResponse.bind(window.grecaptcha);
                        }
                        
                        // Override getResponse function
                        const overrideGetResponse = function(widgetId) {
                            if (typeof widgetId === 'undefined' || widgetId === null || widgetId === 0) {
                                return token;
                            }
                            if (typeof window.captchaWidget !== 'undefined' && window.captchaWidget !== null && widgetId === window.captchaWidget) {
                                return token;
                            }
                            if (originalGetResponse) {
                                try {
                                    const response = originalGetResponse(widgetId);
                                    if (response && response.length > 100) {
                                        return response;
                                    }
                                } catch (e) {
                                    return token;
                                }
                            }
                            return token;
                        };
                        
                        window.grecaptcha.getResponse = overrideGetResponse;
                        
                        // Also override enterprise if it exists
                        if (window.grecaptcha.enterprise) {
                            window.grecaptcha.enterprise.getResponse = overrideGetResponse;
                        }
                        
                        // Set token in hidden textarea
                        try {
                            const textarea = document.querySelector('textarea[name="g-recaptcha-response"]');
                            if (textarea) {
                                textarea.value = token;
                                textarea.dispatchEvent(new Event('input', { bubbles: true }));
                                textarea.dispatchEvent(new Event('change', { bubbles: true }));
                            }
                        } catch (e) {
                            console.warn('Could not set textarea value:', e);
                        }
                        
                        // Update reCAPTCHA container styling
                        try {
                            const recaptchaContainer = document.querySelector('.g-recaptcha');
                            if (recaptchaContainer) {
                                recaptchaContainer.classList.add('recaptcha-checked');
                                recaptchaContainer.setAttribute('data-checked', 'true');
                            }
                        } catch (e) {
                            console.warn('Could not update reCAPTCHA container:', e);
                        }
                        
                        // Verify token can be retrieved
                        let testResponse = null;
                        try {
                            testResponse = window.grecaptcha.getResponse(0);
                        } catch (e) {
                            testResponse = token;
                        }
                        
                        return {
                            success: true, 
                            tokenLength: testResponse ? testResponse.length : token.length,
                            textareaSet: !!document.querySelector('textarea[name="g-recaptcha-response"]')?.value
                        };
                    } catch (e) {
                        return {success: false, error: e.message};
                    }
                }
                """,
                captcha_token
            )

            if not injection_result.get("success"):
                raise RuntimeError(f"Failed to inject CAPTCHA token: {injection_result.get('error', 'Unknown error')}")

            logger.info(f"[Playwright] ✅ CAPTCHA token injected (length: {injection_result.get('tokenLength', 0)})")
            
            await page.wait_for_timeout(300)
            
            if captcha_type in ['recaptcha_v2', 'recaptcha_v2_enterprise']:
                checkbox_updated = False
                try:
                    recaptcha_iframe = None
                    for frame in page.frames:
                        frame_url = frame.url.lower()
                        if 'recaptcha' in frame_url or ('google.com' in frame_url and 'recaptcha' in frame_url):
                            recaptcha_iframe = frame
                            logger.info(f"[Playwright] Found reCAPTCHA iframe: {frame.url}")
                            break
                    
                    if recaptcha_iframe:
                        try:
                            checkbox_anchor = recaptcha_iframe.locator('#recaptcha-anchor')
                            await checkbox_anchor.wait_for(state='attached', timeout=2000)
                            
                            await checkbox_anchor.evaluate("""
                                (el) => {
                                    el.setAttribute('aria-checked', 'true');
                                    el.classList.remove('recaptcha-checkbox-unchecked');
                                    el.classList.add('recaptcha-checkbox-checked');
                                    
                                    const border = el.querySelector('.recaptcha-checkbox-border');
                                    if (border) {
                                        border.classList.remove('recaptcha-checkbox-border');
                                        border.classList.add('recaptcha-checkbox-border-checked');
                                    }
                                    
                                    const event = new Event('recaptcha-state-change', { bubbles: true });
                                    el.dispatchEvent(event);
                                }
                            """)
                            checkbox_updated = True
                            logger.info("[Playwright] ✅ CAPTCHA checkbox ticked in iframe")
                        except Exception as iframe_error:
                            logger.warning(f"[Playwright] Could not update iframe checkbox: {iframe_error}")
                    else:
                        logger.warning("[Playwright] Could not find reCAPTCHA iframe in page frames")
                except Exception as frame_error:
                    logger.warning(f"[Playwright] Error accessing iframe: {frame_error}")
                
                try:
                    await page.evaluate("""
                        () => {
                            const recaptchaContainer = document.querySelector('.g-recaptcha');
                            if (recaptchaContainer) {
                                recaptchaContainer.classList.add('recaptcha-checked');
                                recaptchaContainer.setAttribute('data-checked', 'true');
                            }
                            
                            const recaptchaIframe = document.querySelector('iframe[src*="recaptcha"]');
                            if (recaptchaIframe && recaptchaIframe.parentElement) {
                                recaptchaIframe.parentElement.classList.add('recaptcha-solved');
                                recaptchaIframe.parentElement.setAttribute('data-solved', 'true');
                            }
                        }
                    """)
                except Exception:
                    pass
            elif captcha_type == 'recaptcha_v3':
                logger.info("[Playwright] reCAPTCHA v3 detected - no checkbox to tick (v3 is invisible)")
                try:
                    await page.evaluate("""
                        () => {
                            // Trigger any callbacks that might be waiting for the token
                            if (window.grecaptcha && typeof window.grecaptcha.execute === 'function') {
                                // v3 might auto-execute, but we've already injected the token
                                console.log('reCAPTCHA v3 token injected');
                            }
                        }
                    """)
                except Exception:
                    pass
            else:
                logger.info(f"[Playwright] CAPTCHA type {captcha_type} - skipping checkbox tick (not applicable)")
            
            await page.wait_for_timeout(500)
            
            logger.info("[Playwright] ✅ CAPTCHA solved and checkbox ticked. Triggering callback to fetch slots...")
            
            
            consular_post_id = scraper_settings.get('consular_post_id', '5084') if scraper_settings else '5084'
            try:
                current_url = page.url
                if 'posto_id=' in current_url:
                    import re
                    match = re.search(r'posto_id=(\d+)', current_url)
                    if match:
                        consular_post_id = match.group(1)
            except Exception:
                pass
            
            callback_triggered = await page.evaluate("""
                ([token, postoId]) => {
                    try {
                        // Check if onCaptchaSuccess function exists
                        if (typeof window.onCaptchaSuccess === 'function') {
                            window.onCaptchaSuccess(token);
                            return {success: true, method: 'onCaptchaSuccess'};
                        }
                        // Fallback: call getSlots directly if available
                        else if (typeof window.getSlots === 'function') {
                            window.getSlots(postoId, token);
                            return {success: true, method: 'getSlots'};
                        }
                        // Last resort: manually trigger the callback via grecaptcha
                        else if (window.grecaptcha && window.grecaptcha.enterprise) {
                            // Try to find the widget and trigger callback
                            const recaptchaDiv = document.querySelector('.g-recaptcha[data-sitekey]');
                            if (recaptchaDiv) {
                                const callback = recaptchaDiv.getAttribute('data-callback');
                                if (callback && typeof window[callback] === 'function') {
                                    window[callback](token);
                                    return {success: true, method: 'callback_attribute'};
                                }
                            }
                        }
                        return {success: false, error: 'No callback function found'};
                    } catch (e) {
                        return {success: false, error: e.message};
                    }
                }
            """, [captcha_token, consular_post_id])
            
            if callback_triggered.get('success'):
                logger.info(f"[Playwright] ✅ Triggered CAPTCHA callback via {callback_triggered.get('method')}")
            else:
                logger.warning(f"[Playwright] ⚠️ Could not trigger callback: {callback_triggered.get('error')}")
                logger.info("[Playwright] Making manual POST request to /VistosOnline/slots...")
                try:
                    slots_response = await page.request.post(
                        f"{BASE_URL}/VistosOnline/slots?posto_id={consular_post_id}",
                        data={
                            "posto_id": consular_post_id,
                            "captcha": captcha_token
                        },
                        headers={
                            "Content-Type": "application/x-www-form-urlencoded"
                        }
                    )
                    logger.info(f"[Playwright] Slots API Response Status: {slots_response.status}")

                    if slots_response.status == 200:
                        logger.info("[Playwright] ✅ Manual slots request successful")
                        slots_data = await slots_response.json()
                        logger.info(f"[Playwright] 📋 Slots API Response: {slots_data}")
                        logger.info(f"[Playwright] Available dates: {len(slots_data) if isinstance(slots_data, list) else 'N/A'}")
                        if isinstance(slots_data, list) and len(slots_data) > 0:
                            logger.info(f"[Playwright] First date entry: {slots_data[0]}")
                        
                        await page.evaluate("""
                            ([data, postoId]) => {
                                // Hide captchaDiv and show calendarDiv
                                const captchaDiv = document.getElementById('captchaDiv');
                                const calendarDiv = document.getElementById('calendarDiv');
                                if (captchaDiv) captchaDiv.style.display = 'none';
                                if (calendarDiv) calendarDiv.style.display = 'block';
                                
                                // Store slots data globally for the calendar
                                if (typeof window !== 'undefined') {
                                    window._slotsData = data;
                                    // Also set the global 'data' variable that ajaxFunctionPeriodos uses
                                    if (typeof window !== 'undefined') {
                                        window.data = data;
                                    }
                                }
                                
                                // Reset CAPTCHA
                                if (window.grecaptcha && window.grecaptcha.enterprise) {
                                    try {
                                        window.grecaptcha.enterprise.reset();
                                    } catch (e) {
                                        console.warn('Could not reset CAPTCHA:', e);
                                    }
                                }
                            }
                        """, [slots_data, consular_post_id])
                    else:
                        response_text = await slots_response.text()
                        logger.warning(f"[Playwright] Manual slots request failed: {slots_response.status}")
                        logger.warning(f"[Playwright] Response: {response_text[:500]}")
                except Exception as manual_err:
                    logger.warning(f"[Playwright] Manual slots request error: {manual_err}")

            # ── wait for slots API response from the callback ──────────────────────
            logger.info("[Playwright] Waiting for slots API response from CAPTCHA callback...")
            for _wait_tick in range(16):  # up to 8 s (16 × 500 ms)
                if slots_data is not None:
                    break
                await page.wait_for_timeout(500)

            # ── retry if server rejected our token (ReCaptchaError) ────────────────
            _captcha_retry = 0
            while (isinstance(slots_data, dict) and
                   slots_data.get('error') in ('ReCaptchaError', 'error', 'secblock', 'RGPDError') and
                   _captcha_retry < 2):
                _captcha_retry += 1
                _err_name = slots_data.get('error', 'unknown')
                logger.warning(
                    "[Playwright] ⚠️ Slots API returned %r — CAPTCHA retry %d/2...",
                    _err_name, _captcha_retry
                )
                slots_data = None  # clear so the response handler can fill it again

                # reset grecaptcha widget so it accepts a new token
                try:
                    await page.evaluate("""
                        () => {
                            if (window.grecaptcha) {
                                try { window.grecaptcha.reset(); } catch(e) {}
                                if (window.grecaptcha.enterprise) {
                                    try { window.grecaptcha.enterprise.reset(); } catch(e) {}
                                }
                            }
                        }
                    """)
                except Exception:
                    pass
                await page.wait_for_timeout(1000)

                # re-solve
                _retry_token = None
                try:
                    _sch_url_r = page.url if page.url and 'Schedule' in page.url else f"https://pedidodevistos.mne.gov.pt/VistosOnline/Schedule.jsp?posto_id={consular_post_id}"
                    _retry_token = solve_recaptcha_v2(
                        proxy_raw,
                        user_agent,
                        captcha_key_index=captcha_key_index,
                        page_url=_sch_url_r,
                        page_action="schedule",
                        enterprise_action=captcha_action,
                    )
                except Exception as _re_solve_err:
                    logger.error("[Playwright] ❌ Re-solve failed on retry %d/2: %s", _captcha_retry, _re_solve_err)
                    break

                if not _retry_token or len(_retry_token) < 100:
                    logger.error("[Playwright] ❌ Invalid CAPTCHA token on retry %d/2 — stopping", _captcha_retry)
                    break

                logger.info("[Playwright] ✅ Retry CAPTCHA token obtained (length: %d)", len(_retry_token))

                # re-inject token
                _retry_inject = await page.evaluate("""
                    (token) => {
                        try {
                            if (!window.grecaptcha) return {success: false, error: 'grecaptcha not found'};
                            const fn = () => token;
                            window.grecaptcha.getResponse = fn;
                            if (window.grecaptcha.enterprise) window.grecaptcha.enterprise.getResponse = fn;
                            const ta = document.querySelector('textarea[name="g-recaptcha-response"]');
                            if (ta) { ta.value = token; ta.dispatchEvent(new Event('change', {bubbles: true})); }
                            return {success: true, tokenLength: token.length};
                        } catch(e) { return {success: false, error: e.message}; }
                    }
                """, _retry_token)

                if not _retry_inject.get('success'):
                    logger.warning("[Playwright] Retry injection failed: %s — stopping", _retry_inject.get('error'))
                    break

                logger.info("[Playwright] ✅ Retry token injected (length: %d)", _retry_inject.get('tokenLength', 0))
                await page.wait_for_timeout(500)

                # re-trigger onCaptchaSuccess callback
                _retry_cb = await page.evaluate("""
                    ([token, postoId]) => {
                        try {
                            if (typeof window.onCaptchaSuccess === 'function') {
                                window.onCaptchaSuccess(token);
                                return {success: true, method: 'onCaptchaSuccess'};
                            }
                            if (typeof window.getSlots === 'function') {
                                window.getSlots(postoId, token);
                                return {success: true, method: 'getSlots'};
                            }
                            return {success: false, error: 'No callback found'};
                        } catch(e) { return {success: false, error: e.message}; }
                    }
                """, [_retry_token, consular_post_id])

                if _retry_cb.get('success'):
                    logger.info("[Playwright] ✅ Retry callback triggered via %s", _retry_cb.get('method'))
                else:
                    logger.warning("[Playwright] ⚠️ Retry callback failed: %s — stopping", _retry_cb.get('error'))
                    break

                # wait for slots response again
                for _wait_tick in range(16):  # up to 8 s
                    if slots_data is not None:
                        break
                    await page.wait_for_timeout(500)

                if isinstance(slots_data, list):
                    logger.info(
                        "[Playwright] ✅ Valid slots data received on retry %d/2 (%d entries)",
                        _captcha_retry, len(slots_data)
                    )
                    break
                elif isinstance(slots_data, dict) and slots_data.get('error'):
                    logger.warning(
                        "[Playwright] Still %r on retry %d/2 — %s",
                        slots_data.get('error'), _captcha_retry,
                        "will retry" if _captcha_retry < 2 else "max retries reached"
                    )
                    # while condition decides whether to loop again
                else:
                    logger.info("[Playwright] No slots response on retry %d/2 — proceeding to calendar", _captcha_retry)
                    break

            logger.info("[Playwright] Waiting for calendar to appear...")
            try:
                await page.wait_for_selector('#calendarDiv', timeout=15000, state="visible")
                logger.info("[Playwright] ✅ Calendar div is now visible!")
                
                await page.wait_for_function(
                    """
                    () => {
                        const captchaDiv = document.getElementById('captchaDiv');
                        return captchaDiv && captchaDiv.style.display === 'none';
                    }
                    """,
                    timeout=10000
                )
                logger.info("[Playwright] ✅ CAPTCHA div is now hidden!")
            except Exception as wait_err:
                logger.warning(f"[Playwright] Timeout waiting for calendar: {wait_err}")
            
            try:
                await page.wait_for_load_state("networkidle", timeout=30000)
                await page.wait_for_timeout(2000)
            except Exception:
                await page.wait_for_timeout(5000)
            
            if slots_data is None:
                try:
                    slots_data = await page.evaluate("""
                        () => {
                            if (typeof window !== 'undefined' && window._slotsData) {
                                return window._slotsData;
                            }
                            if (typeof data !== 'undefined') {
                                return data;
                            }
                            return null;
                        }
                    """)
                    if slots_data:
                        logger.info(f"[Playwright] 📋 Retrieved slots data from page: {slots_data}")
                except Exception:
                    pass
            
            final_url_after_captcha = page.url
            calendar_visible = await page.evaluate("""
                () => {
                    const calendarDiv = document.getElementById('calendarDiv');
                    return calendarDiv && calendarDiv.style.display !== 'none';
                }
            """)
            
            logger.info(f"[Playwright] After CAPTCHA solve, current URL: {final_url_after_captcha}, Calendar visible: {calendar_visible}")
            
            if calendar_visible:
                logger.info("[Playwright] ✅ Successfully solved CAPTCHA and calendar is now visible!")
            else:
                logger.warning("[Playwright] ⚠️ Calendar not visible - CAPTCHA solve may not have completed successfully")
        else:
            logger.info("[Playwright] No CAPTCHA detected after second form; continuing to schedule page.")
    except Exception as captcha_err:
        logger.error(f"[Playwright] ❌ Error during CAPTCHA detection/solving after second form: {captcha_err}")
        logger.error(f"[Playwright] Current URL: {page.url}")
    
    logger.info("[Playwright] Waiting for redirect after second form submission...")
    try:
        await page.wait_for_url(
            lambda url: "Formulario" not in url or url != final_url,
            timeout=30000
        )
        redirect_url = page.url
        logger.info(f"[Playwright] Redirected after second form to: {redirect_url}")
    except Exception as redirect_err:
        logger.warning(f"[Playwright] No redirect detected or timeout: {redirect_err}")
        redirect_url = page.url
    
    try:
        await page.wait_for_load_state("networkidle", timeout=15000)
    except Exception:
        await page.wait_for_timeout(3000)
    
    logger.info("[Playwright] Checking for schedule page and slots API...")
    
    await page.wait_for_timeout(2000)
    
    try:
        current_url = page.url
        logger.info(f"[Playwright] Current URL after form submission: {current_url}")
        
        if "chrome-error://" in current_url or "error" in current_url.lower():
            logger.warning(f"[Playwright] ⚠️ Detected error page URL: {current_url}")
            logger.info("[Playwright] Waiting for proper redirect to schedule page...")
            
            try:
                await page.wait_for_url(
                    lambda url: ("schedule" in url.lower() or "agendamento" in url.lower() or 
                                "pedidodevistos.mne.gov.pt" in url.lower()) and 
                               "chrome-error://" not in url.lower(),
                    timeout=30000,
                    wait_until="networkidle"
                )
                current_url = page.url
                logger.info(f"[Playwright] Redirected to: {current_url}")
            except Exception as nav_err:
                logger.warning(f"[Playwright] Navigation wait failed: {nav_err}")
                try:
                    await page.wait_for_timeout(5000)
                    current_url = page.url
                    logger.info(f"[Playwright] URL after additional wait: {current_url}")
                except Exception:
                    logger.error("[Playwright] Page may have closed or navigated away")
                    current_url = None
    except Exception as url_err:
        logger.error(f"[Playwright] Error getting URL: {url_err}")
        current_url = None
    
    is_schedule_page = current_url and (
        "schedule" in current_url.lower() or 
        "agendamento" in current_url.lower() or
        ("pedidodevistos.mne.gov.pt" in current_url.lower() and "formulario" not in current_url.lower())
    )
    
    if is_schedule_page:
        logger.info("[Playwright] On schedule page - checking for calendar and slots...")
        try:
            _dbg_dir = os.path.join(WORKING_DIR, "debug_html")
            os.makedirs(_dbg_dir, exist_ok=True)
            _dbg_ts = time.strftime("%Y%m%d_%H%M%S")
            _dbg_user = (username or "unknown").replace("/", "_").replace("\\", "_")
            _dbg_path = os.path.join(_dbg_dir, f"{_dbg_user}_schedule_loaded_{_dbg_ts}.html")
            with open(_dbg_path, "w", encoding="utf-8") as _dbg_f:
                _dbg_f.write(await page.content())
            logger.info("[Debug] Saved schedule page HTML (on load): %s", _dbg_path)
        except Exception as _dbg_err:
            logger.warning("[Debug] Could not save schedule_loaded HTML: %s", _dbg_err)

        calendar_visible = await page.evaluate("""
            () => {
                const calendarDiv = document.getElementById('calendarDiv');
                return calendarDiv && calendarDiv.style.display !== 'none';
            }
        """)
        
        if not calendar_visible:
            captcha_visible = await page.evaluate("""
                () => {
                    const captchaDiv = document.getElementById('captchaDiv');
                    return captchaDiv && captchaDiv.style.display !== 'none';
                }
            """)
            if captcha_visible:
                logger.info("[Playwright] CAPTCHA is visible on schedule page — solving now...")
                try:
                    # Wait for reCAPTCHA widget to be ready
                    try:
                        await page.wait_for_selector('.g-recaptcha, iframe[src*="recaptcha"]', timeout=15000, state="attached")
                        await page.wait_for_timeout(1000)
                    except Exception:
                        logger.warning("[Playwright] reCAPTCHA widget not ready immediately, proceeding anyway...")

                    # Extract posto_id from URL
                    import re as _re2
                    _m2 = _re2.search(r'posto_id=(\d+)', page.url)
                    _sch_post_id = _m2.group(1) if _m2 else (scraper_settings.get('consular_post_id', '5084') if scraper_settings else '5084')

                    for _sch_attempt in range(1, 4):  # up to 3 attempts
                        if _sch_attempt > 1:
                            logger.info("[Playwright] 🔄 Schedule CAPTCHA attempt %d/3...", _sch_attempt)
                            slots_data = None
                            try:
                                await page.evaluate("() => { if (window.grecaptcha) { try { window.grecaptcha.reset(); } catch(e) {} if (window.grecaptcha.enterprise) { try { window.grecaptcha.enterprise.reset(); } catch(e) {} } } }")
                            except Exception:
                                pass
                            await page.wait_for_timeout(1000)

                        _sch_url_attempt = page.url if page.url and 'Schedule' in page.url else f"https://pedidodevistos.mne.gov.pt/VistosOnline/Schedule.jsp?posto_id={_sch_post_id}"
                        _sch_token = solve_recaptcha_v2(
                            proxy_raw,
                            user_agent,
                            captcha_key_index=captcha_key_index,
                            page_url=_sch_url_attempt,
                            page_action="schedule",
                            enterprise_action=captcha_action,
                        )
                        if not _sch_token or len(_sch_token) < 100:
                            logger.error("[Playwright] ❌ Invalid token on schedule CAPTCHA attempt %d/3", _sch_attempt)
                            continue

                        logger.info("[Playwright] ✅ Schedule CAPTCHA token obtained (length: %d, attempt %d/3)", len(_sch_token), _sch_attempt)

                        # Inject token
                        await page.evaluate("""
                            (token) => {
                                if (!window.grecaptcha) return;
                                const fn = () => token;
                                window.grecaptcha.getResponse = fn;
                                if (window.grecaptcha.enterprise) window.grecaptcha.enterprise.getResponse = fn;
                                const ta = document.querySelector('textarea[name="g-recaptcha-response"]');
                                if (ta) { ta.value = token; ta.dispatchEvent(new Event('change', {bubbles: true})); }
                            }
                        """, _sch_token)
                        await page.wait_for_timeout(500)

                        # Trigger onCaptchaSuccess
                        _sch_cb = await page.evaluate("""
                            ([token, postoId]) => {
                                try {
                                    if (typeof window.onCaptchaSuccess === 'function') {
                                        window.onCaptchaSuccess(token);
                                        return {success: true, method: 'onCaptchaSuccess'};
                                    }
                                    if (typeof window.getSlots === 'function') {
                                        window.getSlots(postoId, token);
                                        return {success: true, method: 'getSlots'};
                                    }
                                    return {success: false, error: 'No callback found'};
                                } catch(e) { return {success: false, error: e.message}; }
                            }
                        """, [_sch_token, _sch_post_id])

                        if _sch_cb.get('success'):
                            logger.info("[Playwright] ✅ Schedule CAPTCHA callback triggered via %s", _sch_cb.get('method'))
                        else:
                            logger.warning("[Playwright] Schedule CAPTCHA callback failed: %s — retrying", _sch_cb.get('error'))
                            continue

                        # Wait for slots API response
                        logger.info("[Playwright] Waiting for slots API response (schedule, attempt %d/3)...", _sch_attempt)
                        for _w in range(16):  # up to 8 s
                            if slots_data is not None:
                                break
                            await page.wait_for_timeout(500)

                        if isinstance(slots_data, list):
                            logger.info("[Playwright] ✅ Schedule CAPTCHA accepted — %d slots received", len(slots_data))
                            break
                        elif isinstance(slots_data, dict) and slots_data.get('error'):
                            logger.warning("[Playwright] Schedule slots returned %r (attempt %d/3)", slots_data.get('error'), _sch_attempt)
                            slots_data = None
                            continue
                        else:
                            logger.info("[Playwright] No slots data yet — proceeding to calendar check")
                            break

                    # Wait for calendar to appear
                    try:
                        await page.wait_for_selector('#calendarDiv', timeout=15000, state="visible")
                        calendar_visible = True
                        logger.info("[Playwright] ✅ Calendar visible after schedule CAPTCHA solve")
                    except Exception:
                        logger.warning("[Playwright] Calendar did not appear after schedule CAPTCHA solve")
                        try:
                            _dbg_dir2 = os.path.join(WORKING_DIR, "debug_html")
                            os.makedirs(_dbg_dir2, exist_ok=True)
                            _dbg_ts2 = time.strftime("%Y%m%d_%H%M%S")
                            _dbg_user2 = (username or "unknown").replace("/", "_").replace("\\", "_")
                            _dbg_path2 = os.path.join(_dbg_dir2, f"{_dbg_user2}_schedule_captcha_still_visible_{_dbg_ts2}.html")
                            with open(_dbg_path2, "w", encoding="utf-8") as _dbg_f2:
                                _dbg_f2.write(await page.content())
                            logger.info("[Debug] Saved schedule page HTML (CAPTCHA still visible): %s", _dbg_path2)
                        except Exception as _dbg_err2:
                            logger.warning("[Debug] Could not save schedule_captcha_still_visible HTML: %s", _dbg_err2)
                except Exception as _sch_err:
                    logger.error("[Playwright] Error solving schedule page CAPTCHA: %s", _sch_err)
        
        if calendar_visible:
            logger.info("[Playwright] ✅ Calendar is visible - proceeding with date/period selection...")
            
            if slots_data is None:
                try:
                    slots_data = await page.evaluate("""
                        () => {
                            if (typeof window !== 'undefined' && window._slotsData) {
                                return window._slotsData;
                            }
                            if (typeof data !== 'undefined') {
                                return data;
                            }
                            return null;
                        }
                    """)
                    if slots_data:
                        logger.info(f"[Playwright] 📋 Retrieved slots data from page: {slots_data}")
                except Exception:
                    pass
            
            if slots_data and isinstance(slots_data, list) and len(slots_data) > 0:
                logger.info("[Playwright] Selecting available date and period...")
                
                selected_date = None
                selected_period = None

                # =============================================================
                # FILTRO DE DATA — REGRAS (aplicadas em conjunto):
                #
                #   1. A data de agendamento deve ser < data de chegada (config)
                #      O servidor rejeita slots >= data de chegada prevista.
                #
                #   2. A data de agendamento deve estar dentro de 90 dias
                #      a partir de HOJE. Slots mais distantes nao sao validos
                #      para o processo de visto e serao rejeitados.
                #
                # Se nao existir nenhum slot que satisfaca AMBAS as regras,
                # o bot envia alerta Telegram e NAO submete o formulario
                # (evita desperdiciar um CAPTCHA e causar ban por submit invalido).
                # =============================================================
                _today = date.today()
                _max_date = _today + timedelta(days=90)  # limite de 90 dias

                # Ler data de chegada do config (opcional — restringe ainda mais)
                _arrival_cutoff = None
                try:
                    _raw_arrival = scraper_settings.get('intended_date_of_arrival') if scraper_settings else None
                    if _raw_arrival:
                        # Normalizar separadores: aceita YYYY/MM/DD e YYYY-MM-DD
                        _arr_str = str(_raw_arrival).strip().replace('/', '-')
                        _arrival_cutoff = datetime.strptime(_arr_str, '%Y-%m-%d').date()
                        logger.info(
                            f"[DateFilter] Hoje={_today} | Limite 90d={_max_date} "
                            f"| Chegada config={_arrival_cutoff}"
                        )
                except Exception as _de:
                    logger.warning(f"[DateFilter] Nao foi possivel ler data de chegada do config: {_de}")

                logger.info(f"[DateFilter] Hoje={_today} | Limite 90 dias={_max_date}")

                _slots_analisados   = 0
                _slots_muito_longe  = 0
                _slots_apos_chegada = 0
                _slots_no_passado   = 0

                for date_entry in slots_data:
                    if not isinstance(date_entry, dict) or 'date' not in date_entry:
                        continue
                    date_str = date_entry['date']
                    periods  = date_entry.get('periods', [])
                    if not periods:
                        continue

                    _slots_analisados += 1

                    try:
                        _slot_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                    except Exception:
                        continue  # formato inesperado — saltar

                    # Regra 0: slot nao pode ser no passado
                    if _slot_date < _today:
                        _slots_no_passado += 1
                        continue

                    # Regra 1: slot deve estar dentro de 90 dias
                    if _slot_date > _max_date:
                        _slots_muito_longe += 1
                        # Slots ordenados cronologicamente — todos os seguintes
                        # tambem estao fora do limite. Parar o loop.
                        break

                    # Regra 2: slot deve ser ANTERIOR a data de chegada (se configurada)
                    if _arrival_cutoff is not None and _slot_date >= _arrival_cutoff:
                        _slots_apos_chegada += 1
                        continue

                    # ✅ Slot valido — selecionar e sair
                    selected_date   = date_str
                    selected_period = periods[0].get('id') if isinstance(periods[0], dict) else periods[0]
                    logger.info(
                        f"[DateFilter] ✅ Slot valido: {selected_date} (period={selected_period}) "
                        f"[{(_slot_date - _today).days} dias a partir de hoje]"
                    )
                    break

                # Relatorio de filtragem
                logger.info(
                    f"[DateFilter] Analisados={_slots_analisados} | "
                    f"No passado={_slots_no_passado} | "
                    f"Alem de 90d={_slots_muito_longe} | "
                    f"Apos chegada={_slots_apos_chegada} | "
                    f"Selecionado={'✅ ' + selected_date if selected_date else '❌ NENHUM'}"
                )

                if selected_date is None:
                    # Nao ha slots validos — alertar e NAO submeter
                    _earliest = slots_data[0].get('date', 'N/A') if slots_data else 'N/A'
                    _msg = (
                        f"⚠️ <b>SEM SLOTS VALIDOS</b> para <b>{username}</b>\n"
                        f"📅 Data mais proxima disponivel: <b>{_earliest}</b>\n"
                        f"🗓️ Limite 90 dias: <b>{_max_date}</b>\n"
                        f"✈️ Data de chegada config: <b>{_arrival_cutoff or 'nao definida'}</b>\n"
                        f"🔢 Total slots recebidos: <b>{len(slots_data)}</b>\n"
                        f"❌ Nenhum slot satisfaz as regras — formulario NAO submetido."
                    )
                    logger.warning(f"[DateFilter] {_msg.replace('<b>', '').replace('</b>', '')}")
                    try:
                        await send_telegram_alert(_msg)
                    except Exception:
                        pass
                    # Nao submeter — sair do fluxo de agendamento
                    return False
                
                if selected_date and selected_period:
                    try:
                        date_formatted = selected_date.replace('-', '/')
                        logger.info(f"[Playwright] Setting date field via JavaScript: {date_formatted}")
                        
                        await page.evaluate("""
                            ([postoId, dateStr]) => {
                                const input = document.getElementById('f_date_c');
                                if (input) {
                                    // Remove readonly attribute temporarily to set value
                                    const wasReadonly = input.hasAttribute('readonly');
                                    if (wasReadonly) {
                                        input.removeAttribute('readonly');
                                    }
                                    
                                    // Set the value
                                    input.value = dateStr;
                                    
                                    // Restore readonly attribute
                                    if (wasReadonly) {
                                        input.setAttribute('readonly', '1');
                                    }
                                    
                                    // Trigger change event to notify the form
                                    input.dispatchEvent(new Event('change', { bubbles: true }));
                                    
                                    // Call validation functions if available
                                    if (typeof validarDataPosterior === 'function') {
                                        validarDataPosterior(input);
                                    }
                                    if (typeof validarDataChegada === 'function') {
                                        validarDataChegada(input);
                                    }
                                    
                                    // Call ajaxFunctionPeriodos to populate the period dropdown
                                    if (typeof ajaxFunctionPeriodos === 'function') {
                                        ajaxFunctionPeriodos(postoId, dateStr);
                                    }
                                    
                                    return true;
                                }
                                return false;
                            }
                        """, [consular_post_id, date_formatted])
                        
                        logger.info(f"[Playwright] ✅ Date field set: {date_formatted}")

                        logger.info("[Playwright] Waiting for period dropdown to be populated...")
                        await _ui_wait(page, 1500)
                        
                        await page.wait_for_selector('#inputPeriodos, #cmbPeriodo', timeout=5000)
                        period_select = page.locator('#inputPeriodos, #cmbPeriodo').first
                        
                        await page.wait_for_function(
                            """
                            () => {
                                const select = document.getElementById('inputPeriodos') || document.getElementById('cmbPeriodo');
                                return select && !select.disabled;
                            }
                            """,
                            timeout=10000
                        )
                        
                        await period_select.select_option(value=str(selected_period))
                        logger.info(f"[Playwright] ✅ Selected period: {selected_period}")
                        
                        await _ui_wait(page, 500)
                        
                        submit_button = page.locator('#btnSubmit').first
                        await submit_button.wait_for(state="visible", timeout=5000)
                        
                        logger.info("[Playwright] Clicking #btnSubmit to open modal...")
                        await submit_button.click()
                        
                        try:
                            await page.wait_for_selector('#popup', timeout=5000, state="visible")
                            await page.wait_for_selector('#previstoSubmit', timeout=5000, state="visible")
                            logger.info("[Playwright] ✅ Modal popup appeared")
                            
                            await page.wait_for_timeout(500)
                            
                            def is_pdf_response(resp):
                                try:
                                    ct = (resp.headers.get("content-type") or "").lower()
                                    if resp.status == 200 and "application/pdf" in ct:
                                        return True
                                    if "MostrarPdf" in resp.url and resp.status == 200:
                                        return True
                                    return False
                                except Exception:
                                    return False
                            
                            modal_submit = page.locator('#previstoSubmit').first
                            logger.info("[Playwright] Clicking #previstoSubmit in modal to submit form and get PDF...")
                            async with page.expect_response(is_pdf_response, timeout=45000) as pdf_response_info:
                                await modal_submit.click()
                            try:
                                pdf_response = await pdf_response_info.value
                                body = await pdf_response.body()
                                if body and body.startswith(b'%PDF'):
                                    pdf_content_bytes = body
                                    pdf_downloaded = True
                                    logger.info(f"[Playwright] ✅ PDF received via expect_response ({len(pdf_content_bytes)} bytes)")
                            except Exception as pdf_wait_err:
                                logger.warning(f"[Playwright] Could not get PDF from expect_response: {pdf_wait_err}")
                            
                            logger.info("[Playwright] Waiting for PDF response...")
                            await page.wait_for_timeout(5000)
                            
                            if not pdf_content_bytes:
                                try:
                                    context = page.context
                                    for p in context.pages:
                                        if p != page and ("MostrarPdf" in p.url or "application/pdf" in (p.url or "").lower()):
                                            logger.info(f"[Playwright] PDF may have opened in new tab: {p.url[:80]}...")
                                            pdf_url = p.url
                                            if pdf_url and not pdf_url.startswith("chrome-error"):
                                                resp = await page.request.get(pdf_url, timeout=30000)
                                                if resp.status == 200:
                                                    body = await resp.body()
                                                    if body and body.startswith(b'%PDF'):
                                                        pdf_content_bytes = body
                                                        pdf_downloaded = True
                                                        logger.info(f"[Playwright] ✅ PDF fetched from new tab URL ({len(pdf_content_bytes)} bytes)")
                                            break
                                except Exception as new_tab_err:
                                    logger.warning(f"[Playwright] Could not get PDF from new tab: {new_tab_err}")
                            
                            if not pdf_content_bytes:
                                await page.wait_for_timeout(5000)
                            
                            if not pdf_content_bytes and page.url and "MostrarPdf" in page.url:
                                try:
                                    logger.info("[Playwright] Page navigated to PDF URL - fetching PDF...")
                                    resp = await page.request.get(page.url, timeout=30000)
                                    if resp.status == 200:
                                        body = await resp.body()
                                        if body and body.startswith(b'%PDF'):
                                            pdf_content_bytes = body
                                            pdf_downloaded = True
                                            logger.info(f"[Playwright] ✅ PDF fetched from current page URL ({len(pdf_content_bytes)} bytes)")
                                except Exception as nav_fetch_err:
                                    logger.warning(f"[Playwright] Could not fetch PDF from page URL: {nav_fetch_err}")
                            
                            try:
                                await page.wait_for_load_state("networkidle", timeout=30000)
                                
                                if pdf_downloaded and pdf_content_bytes:
                                    logger.info("[Playwright] ✅✅✅ SUCCESS: PDF downloaded! Saving PDF file...")
                                    
                                    if username:
                                        try:
                                            os.makedirs(OUTPUT_DIR, exist_ok=True)
                                            
                                            pdf_filename = f"output_{username}.pdf"
                                            pdf_path = os.path.join(OUTPUT_DIR, pdf_filename)
                                            
                                            with open(pdf_path, 'wb') as pdf_file:
                                                pdf_file.write(pdf_content_bytes)
                                            
                                            logger.info(f"[Playwright] ✅ PDF saved to: {pdf_path}")
                                            
                                            try:
                                                update_csv_status(username, 'success')
                                                logger.info(f"[Playwright] ✅ Updated CSV: {username} marked as success")
                                            except Exception as csv_err:
                                                logger.warning(f"[Playwright] Failed to update CSV: {csv_err}")
                                            
                                        except Exception as save_err:
                                            logger.error(f"[Playwright] Failed to save PDF: {save_err}")
                                    
                                    try:
                                        logger.info("[Playwright] Visiting logout page to clear session...")
                                        await page.goto(f"{BASE_URL}/VistosOnline/logout", timeout=30000, wait_until="networkidle")
                                        await page.wait_for_timeout(2000)
                                        logger.info("[Playwright] ✅ Logged out successfully")
                                    except Exception as logout_err:
                                        logger.warning(f"[Playwright] Error during logout: {logout_err}")
                                    
                                    return True
                                else:
                                    await page.wait_for_timeout(3000)
                                    if not pdf_content_bytes:
                                        await page.wait_for_load_state("networkidle", timeout=10000)
                                    page_content = await page.content()
                                    if 'MostrarPdf' in page_content or 'application/pdf' in page_content.lower() or '%PDF' in page_content[:100]:
                                        logger.info("[Playwright] ✅ PDF reference found in page - attempting to download PDF...")
                                        
                                        if not pdf_content_bytes:
                                            try:
                                                pdf_url = await page.evaluate("""
                                                    () => {
                                                        const iframe = document.querySelector('iframe[src*="MostrarPdf"], iframe[src*="pdf"], iframe[src*="SubmeterVisto"]');
                                                        if (iframe && iframe.src) return iframe.src;
                                                        const a = document.querySelector('a[href*="MostrarPdf"], a[href*=".pdf"]');
                                                        if (a && a.href) return a.href;
                                                        const obj = document.querySelector('object[data*="MostrarPdf"], object[data*=".pdf"]');
                                                        if (obj && obj.data) return obj.data;
                                                        return null;
                                                    }
                                                """)
                                                if pdf_url:
                                                    if not pdf_url.startswith('http'):
                                                        pdf_url = BASE_URL + ('/' if not pdf_url.startswith('/') else '') + pdf_url
                                                    logger.info(f"[Playwright] Fetching PDF from URL: {pdf_url[:80]}...")
                                                    resp = await page.request.get(pdf_url, timeout=30000)
                                                    if resp.status == 200:
                                                        pdf_content_bytes = await resp.body()
                                                        if pdf_content_bytes and pdf_content_bytes.startswith(b'%PDF'):
                                                            pdf_downloaded = True
                                                            logger.info(f"[Playwright] ✅ PDF fetched from page URL ({len(pdf_content_bytes)} bytes)")
                                            except Exception as fetch_err:
                                                logger.warning(f"[Playwright] Could not fetch PDF from page URL: {fetch_err}")
                                        
                                        if pdf_content_bytes and username:
                                            try:
                                                os.makedirs(OUTPUT_DIR, exist_ok=True)
                                                pdf_filename = f"output_{username}.pdf"
                                                pdf_path = os.path.join(OUTPUT_DIR, pdf_filename)
                                                with open(pdf_path, 'wb') as pdf_file:
                                                    pdf_file.write(pdf_content_bytes)
                                                logger.info(f"[Playwright] ✅ PDF saved to: {pdf_path}")
                                                try:
                                                    update_csv_status(username, 'success')
                                                    logger.info(f"[Playwright] ✅ Updated CSV: {username} marked as success")
                                                except Exception as csv_err:
                                                    logger.warning(f"[Playwright] Failed to update CSV: {csv_err}")
                                                try:
                                                    logger.info("[Playwright] Visiting logout page to clear session...")
                                                    await page.goto(f"{BASE_URL}/VistosOnline/logout", timeout=30000, wait_until="networkidle")
                                                    await page.wait_for_timeout(2000)
                                                    logger.info("[Playwright] ✅ Logged out successfully")
                                                except Exception as logout_err:
                                                    logger.warning(f"[Playwright] Error during logout: {logout_err}")
                                                return True
                                            except Exception as save_err:
                                                logger.error(f"[Playwright] Failed to save PDF: {save_err}")
                                    else:
                                        logger.warning("[Playwright] ⚠️ PDF download status unclear - checking response...")
                                        try:
                                            response_check = await page.evaluate("""
                                                () => {
                                                    // Check if document was rewritten with PDF content
                                                    return document.body && document.body.textContent && 
                                                           (document.body.textContent.includes('PDF') || 
                                                            document.body.textContent.includes('%PDF'));
                                                }
                                            """)
                                            if response_check:
                                                logger.info("[Playwright] PDF content detected in page")
                                                pdf_downloaded = True
                                        except Exception:
                                            pass
                            except Exception as pdf_wait_err:
                                logger.warning(f"[Playwright] Timeout waiting for PDF: {pdf_wait_err}")
                        except Exception as modal_err:
                            logger.error(f"[Playwright] Error handling modal: {modal_err}")
                            import traceback
                            logger.error(f"[Playwright] Traceback: {traceback.format_exc()}")
                            
                    except Exception as form_err:
                        logger.error(f"[Playwright] Error filling form or submitting: {form_err}")
                        import traceback
                        logger.error(f"[Playwright] Traceback: {traceback.format_exc()}")
                else:
                    logger.warning("[Playwright] No available dates/periods found in slots data")
            else:
                logger.warning("[Playwright] No slots data available - cannot select date/period")
        else:
            logger.warning("[Playwright] Calendar not visible - cannot proceed with date selection")
    else:
        if current_url:
            logger.info(f"[Playwright] Not on schedule page (current URL: {current_url}) - may need to wait for redirect")
        else:
            logger.warning("[Playwright] Could not determine current URL - page may have closed or navigated away")
        
        if not pdf_downloaded and current_url and "chrome-error://" not in current_url:
            logger.info("[Playwright] Waiting for redirect to schedule page...")
            try:
                await page.wait_for_url(
                    lambda url: "schedule" in url.lower() or "agendamento" in url.lower(),
                    timeout=15000
                )
                logger.info(f"[Playwright] ✅ Redirected to schedule page")
                is_schedule_page = True
            except Exception:
                logger.warning("[Playwright] No redirect to schedule page detected")
    
    return False

async def _playwright_login_internal(username: str, password: str, solve_recaptcha_v2, proxy_raw: str, user_agent: str, login_start_time: float, time_module, captcha_key_index: int = 0):
    """
    Internal login implementation with proper resource management.
    """
    # Tráfego direto: um único marcador __DIRECT__ partilhado — chave por utilizador
    # para o pool não fechar o browser de outro login em paralelo.
    _browser_pool_key = (
        f"{DIRECT_PROXY_MARKER}:{username}" if _is_direct_proxy(proxy_raw) else proxy_raw
    )
    await asyncio.sleep(random.uniform(0.5, 1.5))

    if _is_direct_proxy(proxy_raw):
        proxy_config = None
    else:
        proxy_config = _proxy_to_playwright_config(proxy_raw)
        if not proxy_config:
            raise RuntimeError(f"[Playwright] Formato de proxy invalido: {proxy_raw}")

    _cdp_endpoint = ""
    if scraper_settings:
        _cdp_endpoint = str(scraper_settings.get("cdp_endpoint") or "").strip()
    if not _cdp_endpoint:
        _cdp_endpoint = str(os.environ.get("CDP_ENDPOINT") or "").strip()
    _cdp_mode = bool(_cdp_endpoint)

    language = scraper_settings.get('language', 'PT') if scraper_settings else 'PT'
    language = str(language).strip() or "PT"
    login_url = f"{BASE_URL}/VistosOnline/Authentication.jsp?language={language}"
    _lang_upper = language.upper()

    is_mobile = "Mobile" in user_agent or "Android" in user_agent
    if "Windows" in user_agent:
        platform = "Windows"
    elif "Macintosh" in user_agent:
        platform = "macOS"
    elif "Android" in user_agent or "Linux" in user_agent:
        platform = "Linux" if not is_mobile else "Android"
    else:
        platform = "Windows"

    # Accept-Language alinhado com ?language= na página de login (evita inconsistência com o servidor)
    if _lang_upper == "EN":
        _accept_lang = "en-GB,en;q=0.9,pt;q=0.8"
    else:
        _accept_lang = "pt-BR,pt;q=0.9"
    extra_headers = {
        "Accept-Language": _accept_lang,
    }
    
    if "Firefox" not in user_agent:
        chrome_version_match = re.search(r'Chrome/(\d+)\.', user_agent)
        if chrome_version_match:
            chrome_version = chrome_version_match.group(1)
        else:
            chrome_version = "143"
        
        # Formato exato do sec-ch-ua do Chrome 146+ (Not-A.Brand em vez de Not_A Brand)
        sec_ch_ua = f'"Google Chrome";v="{chrome_version}", "Chromium";v="{chrome_version}", "Not A(Brand";v="24"'
        extra_headers.update({
            "sec-ch-ua": sec_ch_ua,
            "sec-ch-ua-mobile": "?1" if is_mobile else "?0",
            "sec-ch-ua-platform": f'"{platform}"',
        })

    if is_mobile:
        viewport_size = {"width": 412, "height": 915}
        screen_size = {"width": 412, "height": 915}
        device_scale_factor = 2.625
    else:
        viewport_size = {"width": 1920, "height": 1080}
        screen_size = {"width": 1920, "height": 1080}
        device_scale_factor = 1

    # --- CORREÇÃO CRÍTICA AQUI ---
    stealth_script = None 
    # ------------------------------

    headless_cfg = True
    try:
        if scraper_settings is not None:
            headless_cfg = bool(scraper_settings.get('headless_mode', True))
    except Exception as e:
        logger.warning(
            f"[Playwright] Could not read headless_mode from config, defaulting to True: {e}"
        )

    _use_browser_pool = bool(browser_context_pool is not None and not _cdp_mode and headless_cfg)
    if browser_context_pool is not None and not _cdp_mode and not headless_cfg:
        logger.info(
            "[BrowserPool] Headed mode detected — disabling context reuse to avoid "
            "extra visible browser windows during shutdown."
        )

    logger.info("[Playwright] Initializing browser (Ghost Mode Activated)...")

    # =======================================================================
    # MELHORIA 3.6 — Persistent Browser Context Pool
    # Verificar se ja existe um contexto valido para este proxy.
    # Se sim, limpa cookies e reutiliza — evita criar browser novo.
    # Se nao, cria browser + context normalmente e guarda no pool.
    # =======================================================================
    _reusing_context = False
    playwright = None
    browser    = None
    context    = None
    page       = None
    _tls_client = None
    pool_entry_registered = False
    pool_should_invalidate = False

    if _use_browser_pool:
        existing = await browser_context_pool.get(_browser_pool_key)
        if existing:
            try:
                browser    = existing["browser"]
                context    = existing["context"]
                # Limpar cookies da sessao anterior sem fechar o browser
                await context.clear_cookies()
                page       = existing["page"]
                user_agent = existing["user_agent"]
                # Verificar se a pagina ainda responde
                _ = await page.evaluate("1 + 1")
                _reusing_context = True
                pool_entry_registered = True
                logger.info(
                    f"[BrowserPool] ✅ Reutilizando contexto existente para "
                    f"{_proxy_log_label(proxy_raw)} (browser nao foi recriado)"
                )
            except Exception as _reuse_err:
                logger.warning(f"[BrowserPool] Contexto existente invalido: {_reuse_err} — criando novo")
                await browser_context_pool.invalidate(_browser_pool_key)
                _reusing_context = False
                browser = context = page = None

    if not _reusing_context:
        # Fluxo normal: criar playwright + browser + context
        playwright = await async_playwright().start()
        browser    = None
    
    # Flag que transforma qualquer excepção posterior ao "Login Aceito" em
    # PostLoginFailure. Evita que Login() / main() recomecem o fluxo (novo
    # CAPTCHA + novo POST /login) e disparem o WAF do MNE.
    login_post_accepted = False
    login_post_submitted = False
    login_post_click_count = 0
    login_post_network_count = 0

    try:
        # ── 3.6 / CDP: launch local OU anexar via remote debugging ─────────────
        if not _reusing_context:
            if _cdp_mode:
                logger.info(f"[Playwright] CDP attach -> {_cdp_endpoint}")
                try:
                    browser = await playwright.chromium.connect_over_cdp(_cdp_endpoint)
                except Exception as cdp_e:
                    await playwright.stop()
                    raise RuntimeError(
                        f"CDP connect falhou ({_cdp_endpoint}). "
                        "Inicie Chrome/Chromium com --remote-debugging-port=9222 "
                        f"(ou use ws://...). Erro: {cdp_e}"
                    ) from cdp_e

                _tls_client = TLSClient(
                    user_agent=user_agent,
                    proxy_raw=None if _is_direct_proxy(proxy_raw) else proxy_raw,
                )
                tls_result = await _tls_client.preflight_tls(f"{BASE_URL}/VistosOnline/")
                logger.info(
                    f"[TLSClient] Preflight: status={tls_result['status']} "
                    f"cookies={list(tls_result['cookies'].keys())}"
                )
                if int(tls_result.get("status") or 0) >= 500:
                    raise RuntimeError(
                        "MNE devolveu página de manutenção/indisponibilidade no preflight TLS. "
                        f"URL: {BASE_URL}/VistosOnline/ | status={tls_result.get('status')} | "
                        f"text={_short_normalized_text(tls_result.get('text') or '')!r}"
                    )
                if not _cfg_bool("tls_preflight_inject_cookies", False):
                    _tls_client._cookies = {}
                    logger.info(
                        "[TLSClient] Cookie injection disabled; Playwright will "
                        "establish its own session cookies on the browser proxy connection."
                    )
                proxy_timezone = (
                    "Europe/Lisbon"
                    if _is_direct_proxy(proxy_raw)
                    else get_timezone_from_proxy(proxy_raw)
                )
                context, page = await _tls_client.stealth_context(
                    browser,
                    extra_http_headers=extra_headers,
                    viewport_size=viewport_size,
                    locale="pt-BR",
                    timezone_id=proxy_timezone,
                    proxy_config=proxy_config,
                )
                logger.info(
                    "[Playwright] CDP: novo contexto Playwright criado "
                    "(proxy aplicado ao contexto; disconnect nao fecha o seu Chrome)"
                )
            else:
                ANTI_DETECTION_ARGS = [
                    '--disable-blink-features=AutomationControlled',
                    '--disable-features=IsolateOrigins,site-per-process',
                    '--disable-infobars',
                    '--no-first-run',
                    '--disable-extensions',
                    '--disable-component-update',
                    '--disable-background-networking',
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                ]

                # Cheap probe before launching Chrome. If MNE already returns
                # maintenance/503 for this proxy exit, rotate without paying the
                # cost of browser startup, screenshots, and context setup.
                _tls_client = TLSClient(
                    user_agent=user_agent,
                    proxy_raw=None if _is_direct_proxy(proxy_raw) else proxy_raw,
                )
                tls_result = await _tls_client.preflight_tls(f"{BASE_URL}/VistosOnline/")
                logger.info(
                    f"[TLSClient] Preflight: status={tls_result['status']} "
                    f"cookies={list(tls_result['cookies'].keys())}"
                )
                if int(tls_result.get("status") or 0) >= 500:
                    raise RuntimeError(
                        "MNE devolveu página de manutenção/indisponibilidade no preflight TLS. "
                        f"URL: {BASE_URL}/VistosOnline/ | status={tls_result.get('status')} | "
                        f"text={_short_normalized_text(tls_result.get('text') or '')!r}"
                    )

                logger.info("[Playwright] Launching REAL Chrome/Edge browser...")
                channel_to_use = "chrome"
                try:
                    browser = await playwright.chromium.launch(
                        headless=headless_cfg,
                        proxy=proxy_config if proxy_config else None,
                        channel=channel_to_use,
                        args=ANTI_DETECTION_ARGS,
                        timeout=60000,
                    )
                    logger.info(f"[Playwright] ✅ Navegador iniciado: {channel_to_use}")
                except Exception as e:
                    logger.warning(f"[Playwright] Chrome nao encontrado ({e}). Tentando Edge...")
                    channel_to_use = "msedge"
                    try:
                        browser = await playwright.chromium.launch(
                            headless=headless_cfg,
                            proxy=proxy_config if proxy_config else None,
                            channel=channel_to_use,
                            args=ANTI_DETECTION_ARGS,
                            timeout=60000,
                        )
                        logger.info(f"[Playwright] ✅ Navegador iniciado: {channel_to_use}")
                    except Exception as final_e:
                        await playwright.stop()
                        raise RuntimeError(f"Nem Chrome nem Edge encontrados. Erro: {final_e}")

                # ── TLS/JA3 PREFLIGHT ────────────────────────────────────────────────
                if not _cfg_bool("tls_preflight_inject_cookies", False):
                    _tls_client._cookies = {}
                    logger.info(
                        "[TLSClient] Cookie injection disabled; Playwright will "
                        "establish its own session cookies on the browser proxy connection."
                    )

                proxy_timezone = (
                    "Europe/Lisbon"
                    if _is_direct_proxy(proxy_raw)
                    else get_timezone_from_proxy(proxy_raw)
                )
                context, page = await _tls_client.stealth_context(
                    browser,
                    extra_http_headers=extra_headers,
                    viewport_size=viewport_size,
                    locale="pt-BR",
                    timezone_id=proxy_timezone,
                    proxy_config=proxy_config,
                )
                logger.info("[TLSClient] ✅ stealth_context criado")
        else:
            logger.info("[BrowserPool] ♻️ Contexto reutilizado — skip browser launch e new_context")
            _tls_client = None
        # ────────────────────────────────────────────────────────────────────────

        async def _save_debug_html(label: str):
            """Save current page HTML to debug_html/ folder for inspection."""
            try:
                debug_dir = os.path.join(WORKING_DIR, "debug_html")
                os.makedirs(debug_dir, exist_ok=True)
                ts = time_module.strftime("%Y%m%d_%H%M%S")
                safe_user = (username or "unknown").replace("/", "_").replace("\\", "_")
                filename = os.path.join(debug_dir, f"{safe_user}_{label}_{ts}.html")
                html_content = await page.content()
                with open(filename, "w", encoding="utf-8") as f:
                    f.write(html_content)
                logger.info(f"[Debug] HTML snapshot saved: {filename}")
            except Exception as snap_err:
                logger.warning(f"[Debug] Failed to save HTML snapshot '{label}': {snap_err}")

        async def _choose_and_prune_context_page(preferred_page=None, reason: str = "context_state"):
            """Keep one live page and close extras to avoid duplicate headed windows/tabs."""
            ctx = context
            if ctx is None:
                return preferred_page

            live_pages = []
            for candidate in ctx.pages:
                try:
                    if not candidate.is_closed():
                        live_pages.append(candidate)
                except Exception:
                    continue

            if not live_pages:
                return preferred_page

            keep_page = None
            if preferred_page is not None:
                try:
                    if preferred_page in live_pages and not preferred_page.is_closed():
                        keep_page = preferred_page
                except Exception:
                    keep_page = None

            if keep_page is None:
                keep_page = next(
                    (
                        candidate
                        for candidate in reversed(live_pages)
                        if (candidate.url or "").strip()
                        and not (candidate.url or "").startswith("about:blank")
                    ),
                    live_pages[-1],
                )

            extras = [candidate for candidate in live_pages if candidate != keep_page]
            if extras:
                logger.warning(
                    "[Playwright] %s: closing %d extra page(s)/window(s) to avoid duplicate visible browsers.",
                    reason,
                    len(extras),
                )
                for extra_page in extras:
                    try:
                        logger.info(
                            "[Playwright] Closing extra page during %s: %s",
                            reason,
                            (extra_page.url or "about:blank")[:200],
                        )
                        await extra_page.close()
                    except Exception as extra_close_err:
                        logger.warning(
                            "[Playwright] Failed to close extra page during %s: %s",
                            reason,
                            extra_close_err,
                        )
            return keep_page

        # =======================================================================
        # MELHORIA 3.7 — Asset Blocking Agressivo
        # =======================================================================
        _BLOCKED_RESOURCE_TYPES = {"image", "font", "media", "ping"}
        _BLOCKED_URL_PATTERNS = (
            "google-analytics.com", "googletagmanager.com", "doubleclick.net",
            "facebook.net", "facebook.com/tr", "connect.facebook",
            "analytics.", "tracking.", "telemetry.", "metrics.",
            "hotjar.com", "clarity.ms", "mouseflow.com", "fullstory.com",
            "/beacon", "/pixel", "/collect", "/track",
            "ads.yahoo.com", "advertising.com", "scorecardresearch.com",
            "quantserve.com", "moatads.com",
            "sentry.io", "bugsnag.com", "rollbar.com", "newrelic.com",
            "datadog-browser-agent",
        )
        _ALLOWED_DOMAINS = (
            "pedidodevistos.mne.gov.pt",
            "google.com/recaptcha",
            "gstatic.com",
            "googleapis.com",
        )

        async def _block_assets(route):
            req = route.request
            url = req.url.lower()
            if any(d in url for d in _ALLOWED_DOMAINS):
                await route.continue_()
                return
            if req.resource_type in _BLOCKED_RESOURCE_TYPES:
                await route.abort()
                return
            if any(p in url for p in _BLOCKED_URL_PATTERNS):
                await route.abort()
                return
            await route.continue_()

        # ── 3.6: só regista o route handler e cria page se for contexto novo ──
        if not _reusing_context:
            await context.route("**/*", _block_assets)

            # stealth_context() já criou a page — não criar de novo.
            # Registar route na page existente (route do context já cobre, mas
            # registar também na page garante cobertura mesmo após navegações).
            # Pega o User Agent real do browser lançado
            actual_user_agent = await page.evaluate("navigator.userAgent")
            user_agent = actual_user_agent
            logger.info(f"[Playwright] User-Agent Real em uso: {user_agent}")

            # Fechar TLSClient (sessão curl_cffi) — já cumpriu o seu papel
            if _tls_client is not None:
                _tls_client.close()

            # Guardar no pool para reutilização futura (3.6) — nunca com CDP (browser externo)
            if _use_browser_pool:
                await browser_context_pool.store(_browser_pool_key, browser, context, page, user_agent)
                pool_entry_registered = True
                logger.info(
                    f"[BrowserPool] Contexto guardado no pool para {_proxy_log_label(proxy_raw)}"
                )
        else:
            # Contexto reutilizado: navegar para about:blank para limpar estado visual
            try:
                await page.goto("about:blank", wait_until="commit", timeout=5000)
            except Exception:
                pass
            logger.info(f"[BrowserPool] User-Agent reutilizado: {user_agent}")

        # --- CORREÇÃO CRÍTICA: INICIAR FUTURES AQUI ---
        login_response_future = asyncio.Future()
        login_request_future = asyncio.Future()
        # ----------------------------------------------

        console_logs = []
        network_failures = []
        
        def handle_console(msg):
            msg_text_lower = msg.text.lower()
            location_str = f"{msg.location.get('url', 'unknown')}:{msg.location.get('lineNumber', 'unknown')}" if msg.location else 'unknown'
            
            console_logs.append({
                'type': msg.type,
                'text': msg.text,
                'location': location_str,
                'timestamp': time_module.time()
            })

            if scraper_settings and scraper_settings.get("log_browser_console"):
                try:
                    logger.info(f"[BrowserConsole] {msg.type}: {msg.text[:8000]}")
                except Exception:
                    pass

            if len(console_logs) <= 5:
                logger.debug(f"[Playwright] Console handler triggered: type={msg.type}, text={msg.text[:100]}")
            
            if msg.type in ['error', 'warning']:
                is_csp_warning = (
                    'content-security-policy' in msg_text_lower and 
                    ('ignoring' in msg_text_lower or 'strict-dynamic' in msg_text_lower or 'nonce-source' in msg_text_lower)
                )
                is_harmless_warning = (
                    'unsupported entrytypes: longtask' in msg_text_lower
                )
                
                if msg.type == 'error' or (msg.type == 'warning' and not is_csp_warning and not is_harmless_warning):
                    if 'recaptcha' in msg_text_lower or 'grecaptcha' in msg_text_lower:
                        logger.warning(f"[Playwright] Console {msg.type} (reCAPTCHA related): {msg.text}")
        
        _BLOCKED_TYPES = {"image", "font", "media"}

        def handle_request_failed(request):
            nonlocal login_post_submitted
            url = request.url
            failure = request.failure or 'unknown'
            if '/VistosOnline/login' in url and request.method == 'POST':
                login_post_submitted = True
                logger.error(f"[Playwright] ❌ Login POST FAILED at network level: {failure} — account may be blocked or proxy issue")
                if not login_response_future.done():
                    login_response_future.set_exception(
                        LoginPostSubmittedFailure(
                            f"Login POST submitted but network failed: {failure}"
                        )
                    )
                return
            if 'recaptcha' in url.lower() or 'gstatic.com' in url.lower() or 'google.com/recaptcha' in url.lower():
                if request.resource_type in _BLOCKED_TYPES or failure in (
                    'net::ERR_FAILED', 'net::ERR_ABORTED', 'NS_BINDING_ABORTED', 'NS_ERROR_ABORT'
                ):
                    logger.debug(f"[Playwright] Blocked/aborted (expected): {url.split('/')[-1]}")
                    return
                network_failures.append({'url': url, 'method': request.method, 'failure': failure})
                logger.error(f"[Playwright] reCAPTCHA request failed: {request.method} {url}")
                logger.error(f"[Playwright] Failure reason: {failure}")
        # -------------------------------------------------------------
        # Anexa os manipuladores de eventos
        page.on("console", handle_console)
        page.on("requestfailed", handle_request_failed)
        
        # --- NOVA LÓGICA: GHOST MODE DINÂMICO (2.1 + 2.2 + 2.3 + 2.4 + 2.5) ---
        main_page_url = f"{BASE_URL}/VistosOnline/"

        selected_vendor, selected_renderer = random.choice(GPU_PROFILES)
        # 2.4: escolher hardware consistente com o User-Agent
        selected_hw = pick_hardware_profile(user_agent)
        dynamic_stealth_script = get_dynamic_stealth_script_full(
            selected_vendor, selected_renderer, selected_hw
        )
        await page.add_init_script(dynamic_stealth_script)
        logger.info(
            f"[Playwright] 👻 GhostMode Ativado: {selected_renderer} | "
            f"CPU={selected_hw['cores']}c RAM={selected_hw['memory']}GB "
            f"platform={selected_hw['platform']} [{selected_hw['label']}]"
        )
        
        logger.info(f"[Playwright] Visiting main page to establish session cookies...")
        try:
            main_page_response = await page.goto(main_page_url, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_selector("body", timeout=3000)
            logger.info(f"[Playwright] Main page loaded (status: {main_page_response.status if main_page_response else 'N/A'})")
            _main_unavailable, _main_title, _main_text = await _page_service_unavailable_snapshot(page)
            if (main_page_response and main_page_response.status >= 500) or _main_unavailable:
                raise RuntimeError(
                    "MNE devolveu página de manutenção/indisponibilidade ao abrir a página inicial. "
                    f"URL: {page.url} | status={main_page_response.status if main_page_response else 'N/A'} | "
                    f"title={_main_title[:80]!r} | text={_short_normalized_text(_main_text)!r}"
                )
        except Exception as main_page_error:
            if _is_site_unavailable_error(main_page_error):
                raise
            logger.warning(f"[Playwright] Main page visit failed (non-critical): {main_page_error}")

        # Aceitar cookie consent popup se visível
        try:
            cookie_btn = page.locator('#allowAllCookiesBtn')
            if await cookie_btn.is_visible(timeout=3000):
                await cookie_btn.click()
                logger.debug("[Playwright] Accepted cookie consent popup")
                await page.wait_for_timeout(150)
        except Exception:
            pass

        # Aguardar que o desafio PoW (/ch/v) seja resolvido e os cookies estejam presentes
        # O servidor define _USER_CONSENT (path /) após o PoW — sem ele o login falha
        logger.info("[Playwright] Aguardando cookies de sessão completos (_USER_CONSENT PoW)...")
        for _cw in range(20):  # até 5 segundos; se não vier, seguimos sem bloquear o login
            all_cookies = await context.cookies()
            cookie_names = [c['name'] for c in all_cookies]
            has_session = 'cookiesession1' in cookie_names
            has_consent = any(c['name'] == '_USER_CONSENT' and c['path'] == '/' for c in all_cookies)
            # Avança se tiver sessão (com ou sem cookie PoW — o Chrome real resolve o PoW automaticamente)
            if has_session:
                if has_consent:
                    logger.info(f"[Playwright] ✅ Cookies prontos (com PoW): {len(all_cookies)} cookies ({cookie_names})")
                else:
                    logger.info(f"[Playwright] ✅ Sessão pronta (sem PoW cookie visível): {len(all_cookies)} cookies ({cookie_names})")
                break
            if _cw % 8 == 0:
                logger.info(f"[Playwright] Aguardando cookies... ({_cw * 0.25:.1f}s) — session={has_session}, consent_pow={has_consent}")
            await page.wait_for_timeout(250)
        else:
            all_cookies = await context.cookies()
            logger.warning(f"[Playwright] ⚠️ Timeout aguardando cookies. Presentes: {[c['name'] for c in all_cookies]}")
            # Continuar mesmo sem o cookie PoW — o Chrome real deve ter passado o desafio
            # O cookie pode ter path diferente ou o servidor pode aceitar assim mesmo
            logger.info("[Playwright] A continuar para login sem cookie PoW — Chrome real deve ter passado o desafio")

        logger.info(f"[Playwright] Navigating to login page: {login_url}")
        nav_start_time = time_module.time()

        # Prewarm do solver: reduz o tempo "morto" entre os campos já
        # preenchidos e o aparecimento do check do reCAPTCHA. O solve começa
        # durante a navegação para a Authentication.jsp, em vez de só arrancar
        # depois da página estar totalmente pronta.
        captcha_future = None
        captcha_start_time = None
        captcha_ready_time = None
        captcha_launch_seq = 0
        captcha_stale_retry_used = False

        def _start_captcha_solver(log_message=None):
            nonlocal captcha_future, captcha_start_time, captcha_ready_time, captcha_launch_seq
            _cp_loop = asyncio.get_running_loop()
            captcha_start_time = time_module.time()
            captcha_ready_time = None
            captcha_launch_seq += 1
            _launch_seq = captcha_launch_seq
            captcha_future = _cp_loop.run_in_executor(
                None,
                functools.partial(
                    solve_recaptcha_v2,
                    proxy_raw,
                    user_agent,
                    captcha_key_index=captcha_key_index,
                    page_url=login_url,
                    page_action="login",
                ),
            )

            def _mark_captcha_ready(_fut, _launch_seq=_launch_seq):
                nonlocal captcha_ready_time
                if _launch_seq != captcha_launch_seq:
                    return
                captcha_ready_time = time_module.time()

            try:
                captcha_future.add_done_callback(_mark_captcha_ready)
            except Exception:
                pass

            if log_message:
                logger.info(log_message)
            return captcha_future

        _cp_prewarm = (scraper_settings or {}).get(
            "captcha_prewarm_on_login_navigation", True
        )
        if isinstance(_cp_prewarm, str):
            _cp_prewarm = _cp_prewarm.strip().lower() in ("1", "true", "yes", "on")
        else:
            _cp_prewarm = bool(_cp_prewarm)
        if _cp_prewarm:
            logger.info(
                "[Captcha] Prewarm configurado, mas login agora inicia CAPTCHA "
                "somente apos concluir o preenchimento dos campos."
            )
        
        max_nav_retries = 3
        nav_success = False
        last_error = None
        response = None
        
        for nav_attempt in range(max_nav_retries):
            try:
                logger.info(f"[Playwright] Navegando para login (Tentativa {nav_attempt + 1}/{max_nav_retries}) - MODO TURBO...")

                # TENTA CARREGAR A PÁGINA (Muito mais rápido que networkidle)
                response = await page.goto(login_url, wait_until="domcontentloaded", timeout=60000)
                _login_unavailable, _login_title, _login_text = await _page_service_unavailable_snapshot(page)
                if _login_unavailable:
                    raise RuntimeError(
                        "MNE devolveu página de manutenção/indisponibilidade ao abrir login. "
                        f"URL: {page.url} | title={_login_title[:80]!r} | "
                        f"text={_short_normalized_text(_login_text)!r}"
                    )

                # ESPERA INTELIGENTE: Aguarda o campo de usuário aparecer (máx 5s)
                try:
                    await page.wait_for_selector('input[name="username"]', timeout=5000)
                    nav_success = True
                    logger.info("[Playwright] ✅ Página de login pronta!")
                    break # SUCESSO - Sai do loop imediatamente
                except Exception as login_field_wait_err:
                    # Se o campo não apareceu, verifica se caímos na página certa mas está lento
                    current_url_check = page.url
                    if "Authentication.jsp" in current_url_check:
                        logger.info("[Playwright] Página correta, mas lenta. Esperando mais um pouco...")
                        try:
                            await page.wait_for_selector('input[name="username"]', timeout=10000)
                            nav_success = True
                            break
                        except Exception as login_field_wait_retry_err:
                            _login_unavailable, _login_title, _login_text = await _page_service_unavailable_snapshot(page)
                            if _login_unavailable:
                                raise RuntimeError(
                                    "MNE devolveu página de manutenção/indisponibilidade ao abrir login. "
                                    f"URL: {page.url} | title={_login_title[:80]!r} | "
                                    f"text={_short_normalized_text(_login_text)!r}"
                                ) from login_field_wait_retry_err
                            raise
                    _login_unavailable, _login_title, _login_text = await _page_service_unavailable_snapshot(page)
                    if _login_unavailable:
                        raise RuntimeError(
                            "MNE devolveu página de manutenção/indisponibilidade ao abrir login. "
                            f"URL: {page.url} | title={_login_title[:80]!r} | "
                            f"text={_short_normalized_text(_login_text)!r}"
                        ) from login_field_wait_err
                    raise RuntimeError("Campo de login não encontrado.") from login_field_wait_err

            except Exception as nav_error:
                last_error = nav_error
                error_str = str(nav_error).lower()
                if _is_site_unavailable_error(nav_error):
                    raise RuntimeError(
                        f"Navegação falhou: MNE indisponível/manutenção detectado sem retries adicionais: {nav_error}"
                    ) from nav_error

                # TRATAMENTO DE REDIRECT (Interrompido)
                if "interrupted" in error_str or "net::err_aborted" in error_str:
                    logger.info(f"[Playwright] Navegação interrompida (Redirect?). Verificando...")
                    try:
                        await page.wait_for_load_state("domcontentloaded", timeout=5000)
                        if await page.locator('input[name="username"]').count() > 0:
                            nav_success = True
                            logger.info("[Playwright] ✅ Login recuperado após interrupção.")
                            break
                    except Exception:
                        pass # Deixa cair no retry abaixo

                # LÓGICA DE RETENTATIVA
                if nav_attempt < max_nav_retries - 1:
                    wait_time = (nav_attempt + 1) * 3
                    logger.warning(f"[Playwright] Falha na navegação. Tentando novamente em {wait_time}s... Erro: {nav_error}")
                    await page.wait_for_timeout(wait_time * 1000)

                    # Se for erro de conexão (Proxy ruim), recria a página
                    if any(x in error_str for x in ["connection", "ssl", "ns_error", "closed"]):
                        logger.warning("[Playwright] Erro de conexão detectado. Reiniciando página...")
                        try:
                            await page.close()
                        except:
                            pass
                        
                        page = await context.new_page()
                        
                        # --- REINJETAR STEALTH (Obrigatorio na nova pagina) ---
                        # Reutiliza o MESMO perfil de hardware/GPU da sessao (consistencia)
                        sel_v, sel_r = random.choice(GPU_PROFILES)
                        dyn_script = get_dynamic_stealth_script_full(sel_v, sel_r, selected_hw)
                        await page.add_init_script(dyn_script)
                        logger.info(f"[Playwright] 👻 GhostMode Re-Ativado (Recovery): {sel_r} | hw={selected_hw['label']}")
                        
                        page.on("console", handle_console)
                        page.on("requestfailed", handle_request_failed)
                        # -----------------------------------------------------
                else:
                    # ÚLTIMA TENTATIVA FALHOU
                    # Deixar o outer except/finally tratar do fecho para a captura
                    # de erro ainda conseguir ler URL/HTML/screenshot da página.
                    raise RuntimeError(f"Navegação falhou após {max_nav_retries} tentativas: {last_error}")
               
        if not nav_success:
            # Não fechar aqui: o outer except precisa da página viva para gerar
            # um bundle útil em browser_error_reports/.
            raise RuntimeError(f"Navigation failed: {last_error}")
        
        if response is None:
            response = type('Response', (), {'status': 200})()
            logger.info("[Playwright] Navigation succeeded but response was None, created mock response")
        
        if response is not None and response.status not in (200, 302):
            # Preservar a página para captura antes de a finally fechar.
            raise RuntimeError(f"Navigation failed: {response.status if response else 'no response'}")

        current_url = page.url
        nav_time = time_module.time() - nav_start_time
        logger.info(f"[Playwright] Current page URL: {current_url} (navigation took {nav_time:.2f}s)")
        
        initial_cookies = await context.cookies()
        logger.info(f"[Playwright] Captured {len(initial_cookies)} cookies from initial page load")

        vistos_sid_cookie = next((c for c in initial_cookies if c['name'] == 'Vistos_sid'), None)
        cookiesession1_cookie = next((c for c in initial_cookies if c['name'] == 'cookiesession1'), None)

        if not vistos_sid_cookie:
            logger.warning("[Playwright] Vistos_sid cookie not found - waiting...")
            for _cw in range(10):
                await page.wait_for_timeout(500)
                initial_cookies = await context.cookies()
                vistos_sid_cookie = next((c for c in initial_cookies if c['name'] == 'Vistos_sid'), None)
                if vistos_sid_cookie:
                    break
            if not vistos_sid_cookie:
                logger.warning("[Playwright] Vistos_sid still missing after 5s")

        if not cookiesession1_cookie:
            logger.warning("[Playwright] cookiesession1 cookie not found - login may fail!")

        logger.info("[Playwright] Checking if reCAPTCHA widget is present on authentication page...")
        
        quick_widget_check = await page.evaluate("""
            () => {
                const hasRecaptchaScript = Array.from(document.querySelectorAll('script')).some(s => 
                    s.src && (s.src.includes('recaptcha') || s.src.includes('gstatic.com/recaptcha'))
                );
                const hasRecaptchaDiv = document.querySelectorAll('[class*="recaptcha"], [id*="recaptcha"], [data-sitekey]').length > 0;
                const hasRecaptchaIframe = document.querySelectorAll('iframe[src*="recaptcha"], iframe[src*="google.com/recaptcha"]').length > 0;
                const hasGrecaptcha = typeof window.grecaptcha !== 'undefined' && window.grecaptcha !== null;
                return hasRecaptchaScript || hasRecaptchaDiv || hasRecaptchaIframe || hasGrecaptcha;
            }
        """)

        # =======================================================================
        # MELHORIA 3.5 — Async Pipeline: CAPTCHA + Form Fill em paralelo
        #
        # Arquitectura anterior (sequencial):
        #   1. Lança CAPTCHA solver em background
        #   2. Preenche username/password (bloqueia até terminar)
        #   3. Aguarda CAPTCHA resolver (pode já estar pronto ou ainda demorar)
        #
        # Nova arquitectura (pipeline):
        #   asyncio.gather(
        #       _fill_login_form()   ← preenche campos (async, usa await interno)
        #       _wait_captcha()      ← aguarda executor (corre em paralelo)
        #   )
        #   → Quando ambos terminam → injeta token + submete
        #
        # Resultado esperado: tempo total = max(fill_time, captcha_time)
        # em vez de fill_time + captcha_time.
        # =======================================================================

        # Coroutine de preenchimento do formulário (isolada para o gather)
        async def _fill_login_form() -> float:
            """Preenche username e password com comportamento humano.
            Retorna o tempo de preenchimento em segundos."""
            await page.wait_for_selector('input[name="username"]', timeout=40000)
            await page.wait_for_timeout(random.randint(500, 1000))

            # Movimento inicial do rato
            try:
                await page.mouse.move(
                    random.randint(200, 800), random.randint(200, 600),
                    steps=random.randint(10, 25)
                )
                await page.wait_for_timeout(random.randint(200, 400))
                if random.random() < 0.3:
                    await page.mouse.move(
                        random.randint(300, 700), random.randint(300, 500),
                        steps=random.randint(8, 20)
                    )
                    await page.wait_for_timeout(random.randint(150, 300))
            except Exception:
                pass

            t0 = time_module.time()
            logger.info("[Pipeline] Form fill a correr em paralelo com CAPTCHA solver...")

            # ── Username ──────────────────────────────────────────────────────
            username_input = page.locator('input[name="username"]')
            username_box = None
            try:
                username_box = await username_input.bounding_box()
                if username_box:
                    tx = username_box['x'] + username_box['width'] / 2 + random.randint(-15, 15)
                    ty = username_box['y'] + username_box['height'] / 2 + random.randint(-10, 10)
                    await page.mouse.move(tx, ty, steps=random.randint(15, 30))
                    await page.wait_for_timeout(random.randint(200, 400))
            except Exception:
                pass

            await username_input.click(delay=random.randint(20, 60))
            await page.wait_for_timeout(random.randint(80, 150))
            for i, char in enumerate(username):
                await username_input.type(char, delay=random.randint(5, 15))
                if random.random() < 0.06 and i > 0:
                    await page.wait_for_timeout(random.randint(20, 60))
            await page.wait_for_timeout(random.randint(100, 200))

            # ── Password ──────────────────────────────────────────────────────
            password_input = page.locator('input[name="password"]')
            try:
                password_box = await password_input.bounding_box()
                if password_box and username_box:
                    tx = password_box['x'] + password_box['width'] / 2 + random.randint(-12, 12)
                    ty = password_box['y'] + password_box['height'] / 2 + random.randint(-8, 8)
                    mx = (tx + username_box['x'] + username_box['width'] / 2) / 2 + random.randint(-20, 20)
                    my = (ty + username_box['y'] + username_box['height'] / 2) / 2 + random.randint(-15, 15)
                    await page.mouse.move(mx, my, steps=random.randint(5, 12))
                    await page.wait_for_timeout(random.randint(50, 150))
                    await page.mouse.move(tx, ty, steps=random.randint(8, 18))
                    await page.wait_for_timeout(random.randint(100, 200))
            except Exception:
                pass

            await password_input.click(delay=random.randint(20, 60))
            await page.wait_for_timeout(random.randint(80, 150))
            for i, char in enumerate(password):
                await password_input.type(char, delay=random.randint(25, 60))
                if random.random() < 0.06 and i > 0:
                    await page.wait_for_timeout(random.randint(20, 70))
            await page.wait_for_timeout(random.randint(150, 300))

            fill_time = time_module.time() - t0
            logger.info(f"[Pipeline] ✅ Form fill concluído em {fill_time:.2f}s")
            return fill_time

        # Fill login fields first, then start CAPTCHA. Some providers reject
        # early tasks before the browser has completed the page interaction.
        if quick_widget_check:
            logger.info("[Pipeline] ✅ CAPTCHA detectado — preenchendo formulario antes do solver...")
        else:
            logger.info("[Pipeline] CAPTCHA widget não detectado ainda — preenchendo formulario primeiro...")

        # ── Fill first; CAPTCHA starts after input is complete ────────────────
        pipeline_start = time_module.time()
        try:
            fill_result = await _fill_login_form()
        except Exception as fill_exc:
            logger.error(f"[Pipeline] Form fill falhou antes do CAPTCHA: {fill_exc}")
            raise

        pipeline_elapsed = time_module.time() - pipeline_start
        logger.info(
            f"[Pipeline] ✅ Form fill concluído em {pipeline_elapsed:.2f}s; "
            "aguardando readiness do reCAPTCHA antes do solver."
        )

        fill_time = fill_result
        fill_start_time = time_module.time() - fill_time  # compatibilidade com código abaixo
        logger.info(f"[Playwright] Form filling took {fill_time:.2f}s")

        logger.info("[Playwright] Short settle after form interaction...")
        await page.wait_for_timeout(120)
        
        logger.info("[Playwright] Waiting for reCAPTCHA widget...")
        widget_ready = False
        widget_id = 0
        max_widget_wait_attempts = 5
        widget_info = {}
        widget_ready_timeout_ms = 8000 if quick_widget_check else 15000

        try:
            await page.wait_for_function(
                """() => {
                    const hasGrecaptcha = typeof window.grecaptcha !== 'undefined'
                                      && window.grecaptcha !== null
                                      && typeof window.grecaptcha.getResponse === 'function';
                    const hasIframe = !!document.querySelector(
                        'iframe[src*="recaptcha"], iframe[src*="google.com/recaptcha"]'
                    );
                    return hasGrecaptcha || hasIframe;
                }""",
                timeout=widget_ready_timeout_ms,
            )
            widget_ready = True
            logger.info("[Playwright] ✅ reCAPTCHA widget ready")
        except Exception:
            logger.warning("[Playwright] wait_for_function timed out — falling back to polling loop...")

        for attempt in range(max_widget_wait_attempts):
            try:
                widget_info = await page.evaluate("""
                    () => {
                        const result = {
                            grecaptcha_loaded: false,
                            grecaptcha_function: false,
                            captchaWidget_defined: false,
                            iframe_found: false,
                            widgetId: null,
                            found: false,
                            details: {
                                scriptTags: [],
                                scriptErrors: [],
                                networkStatus: {},
                                domReady: document.readyState,
                                windowKeys: []
                            }
                        };
                        
                        // Check for reCAPTCHA script tags in DOM
                        const scripts = document.querySelectorAll('script[src*="recaptcha"], script[src*="gstatic.com/recaptcha"]');
                        scripts.forEach(script => {
                            result.details.scriptTags.push({
                                src: script.src || 'inline',
                                async: script.async,
                                defer: script.defer,
                                loaded: script.complete || (script.src && script.readyState === 'complete')
                            });
                        });
                        
                        // Check for script tags that should load grecaptcha
                        const allScripts = document.querySelectorAll('script');
                        allScripts.forEach(script => {
                            const src = script.src || '';
                            if (src.includes('recaptcha') || src.includes('gstatic.com')) {
                                result.details.scriptTags.push({
                                    src: src || script.textContent.substring(0, 100),
                                    async: script.async,
                                    defer: script.defer,
                                    type: script.type
                                });
                            }
                        });
                        
                        // Check for window keys related to recaptcha
                        Object.keys(window).forEach(key => {
                            if (key.toLowerCase().includes('recaptcha') || key.toLowerCase().includes('captcha')) {
                                result.details.windowKeys.push(key);
                            }
                        });
                        
                        // Check if grecaptcha is loaded
                        result.grecaptcha_loaded = typeof window.grecaptcha !== 'undefined' && window.grecaptcha !== null;
                        if (result.grecaptcha_loaded) {
                            result.grecaptcha_function = typeof window.grecaptcha.getResponse === 'function';
                            // Get more details about grecaptcha object
                            try {
                                result.details.grecaptchaKeys = Object.keys(window.grecaptcha).slice(0, 10);
                            } catch (e) {
                                result.details.grecaptchaError = e.message;
                            }
                        }
                        
                        // Check for captchaWidget variable
                        result.captchaWidget_defined = typeof window.captchaWidget !== 'undefined' && window.captchaWidget !== null;
                        if (result.captchaWidget_defined) {
                            result.widgetId = window.captchaWidget;
                        }
                        
                        // Check for reCAPTCHA iframes
                        const iframes = document.querySelectorAll('iframe[src*="recaptcha"], iframe[src*="google.com/recaptcha"]');
                        result.iframe_found = iframes.length > 0;
                        if (result.iframe_found) {
                            result.details.iframeCount = iframes.length;
                            result.details.iframeSrcs = Array.from(iframes).slice(0, 3).map(i => i.src);
                        }
                        
                        // Check for reCAPTCHA divs
                        const recaptchaDivs = document.querySelectorAll('[class*="recaptcha"], [id*="recaptcha"], [data-sitekey]');
                        result.details.recaptchaDivs = recaptchaDivs.length;
                        if (recaptchaDivs.length > 0) {
                            result.details.recaptchaDivData = Array.from(recaptchaDivs).slice(0, 3).map(div => ({
                                className: div.className,
                                id: div.id,
                                sitekey: div.getAttribute('data-sitekey')
                            }));
                        }
                        
                        // Widget is ready if grecaptcha is loaded and functional, OR iframe is present
                        // This matches the previous implementation - more lenient
                        result.found = (result.grecaptcha_loaded && result.grecaptcha_function) || result.iframe_found;
                        
                        // If widget ID not set but grecaptcha is ready, default to 0
                        if (result.found && result.widgetId === null && result.grecaptcha_loaded) {
                            result.widgetId = 0;
                        }
                        
                        return result;
                    }
                """)
                
                if attempt % 3 == 0 or not widget_info.get('grecaptcha_loaded'):
                    logger.info(
                        f"[Playwright] Widget check {attempt + 1}/{max_widget_wait_attempts}: "
                        f"grecaptcha={widget_info.get('grecaptcha_loaded')}, "
                        f"iframe={widget_info.get('iframe_found')}"
                    )

                logger.info(f"[Playwright] Widget check attempt {attempt + 1}/{max_widget_wait_attempts}: "
                           f"grecaptcha={widget_info.get('grecaptcha_loaded')}, "
                           f"function={widget_info.get('grecaptcha_function')}, "
                           f"iframe={widget_info.get('iframe_found')}, "
                           f"found={widget_info.get('found')}")
                
                if widget_info.get('found'):
                    widget_id = widget_info.get('widgetId', 0)
                    logger.info(f"[Playwright] ✅ reCAPTCHA widget detected and ready! "
                              f"(Widget ID: {widget_id}, "
                              f"iframes: {widget_info.get('details', {}).get('iframeCount', 0)})")
                    widget_ready = True
                    break
                else:
                    if widget_info.get('grecaptcha_loaded') and not widget_info.get('grecaptcha_function'):
                        logger.info("[Playwright] grecaptcha loaded but getResponse not ready yet...")

                if attempt < max_widget_wait_attempts - 1:
                    wait_time = 1500
                    await page.wait_for_timeout(wait_time)
                    if attempt % 3 == 0:
                        logger.info(f"[Playwright] Widget not ready yet, attempt {attempt + 1}/{max_widget_wait_attempts}...")
            except Exception as e:
                logger.warning(f"[Playwright] Widget check error (attempt {attempt + 1}): {e}")
                if attempt < max_widget_wait_attempts - 1:
                    await page.wait_for_timeout(1000)

        if not widget_ready:
            logger.warning("[Playwright] Widget detection failed, attempting fallback detection...")
            fallback_check = await page.evaluate("""
                () => {
                    return typeof window.grecaptcha !== 'undefined' && window.grecaptcha !== null;
                }
            """)
            if fallback_check:
                recaptcha_network_failures = [
                    nf for nf in network_failures
                    if "recaptcha" in (nf.get("url", "").lower())
                    or "gstatic" in (nf.get("url", "").lower())
                    or "google.com" in (nf.get("url", "").lower())
                ]
                fallback_widget_healthy = bool(
                    widget_info.get('grecaptcha_function') or widget_info.get('iframe_found')
                )
                if recaptcha_network_failures and not fallback_widget_healthy:
                    failure_preview = "; ".join(
                        f"{nf.get('method', 'GET')} {nf.get('url', '')} -> {nf.get('failure', 'unknown')}"
                        for nf in recaptcha_network_failures[:3]
                    )
                    logger.error(
                        "[Playwright] ⛔ reCAPTCHA assets falharam via rede/proxy e o widget "
                        "não ficou saudável. Abortando antes do POST /login."
                    )
                    raise RuntimeError(
                        "reCAPTCHA assets failed to load cleanly over proxy before submit: "
                        f"{failure_preview}"
                    )
                logger.warning("[Playwright] Proceeding with fallback: grecaptcha exists but widget detection failed")
                widget_ready = True
                widget_id = 0
            else:
                raise RuntimeError("reCAPTCHA widget failed to initialize after multiple attempts. Cannot proceed with login.")

        await page.wait_for_timeout(500)

        captcha_info = await page.evaluate("""
            () => {
                const recaptchaDiv = document.querySelector('.g-recaptcha[data-sitekey]');
                const result = { siteKey: null, action: null };
                
                if (recaptchaDiv) {
                    result.siteKey = recaptchaDiv.getAttribute('data-sitekey');
                    result.action = recaptchaDiv.getAttribute('data-action');
                } else {
                    const iframe = document.querySelector('iframe[src*="recaptcha"]');
                    if (iframe && iframe.src) {
                        const siteKeyMatch = iframe.src.match(/[?&]k=([^&]+)/);
                        if (siteKeyMatch) result.siteKey = siteKeyMatch[1];
                        
                        const actionMatch = iframe.src.match(/[?&]sa=([^&]+)/);
                        if (actionMatch) result.action = actionMatch[1];
                    }
                }
                return result;
            }
        """)

        site_key = captcha_info.get('siteKey')
        if not site_key and scraper_settings:
            site_key = scraper_settings.get('SITE_KEY')
        if not site_key:
            site_key = '6LdOB9crAAAAADT4RFruc5sPmzLKIgvJVfL830d4'

        if site_key:
            logger.info(f"[Playwright] Site key: {site_key[:20]}...")

        if captcha_future is None:
            logger.info("[Playwright] CAPTCHA widget detected but solving not started yet, starting now...")
            _start_captcha_solver()
        else:
            logger.info("[Playwright] CAPTCHA solving already in progress, awaiting result...")
        
        widget_id = None
        try:
            widget_info = await page.evaluate("""
                () => {
                    const result = {
                        captchaWidget_defined: false,
                        captchaWidget_value: null,
                        widget_id: 0
                    };
                    
                    // Check if captchaWidget is defined
                    if (typeof window.captchaWidget !== 'undefined' && window.captchaWidget !== null) {
                        result.captchaWidget_defined = true;
                        result.captchaWidget_value = window.captchaWidget;
                        result.widget_id = window.captchaWidget;
                    } else {
                        // captchaWidget is not set - this is a problem!
                        // The website's doLogin function uses grecaptcha.getResponse(captchaWidget)
                        // If captchaWidget is undefined, it will cause an error
                        // We need to set it to a valid widget ID
                        result.captchaWidget_defined = false;
                        
                        // Try to find if there's already a widget rendered
                        // Check if there are any widgets registered
                        if (window.grecaptcha && window.grecaptcha.getResponse) {
                            // Default widget ID is 0 for the first widget
                            result.widget_id = 0;
                            // Set captchaWidget to 0 if it's not defined
                            window.captchaWidget = 0;
                            result.captchaWidget_value = 0;
                        }
                    }
                    
                    return result;
                }
            """)
            
            if not widget_info.get('captchaWidget_defined'):
                logger.warning(f"[Playwright] captchaWidget was not defined, setting it to {widget_info.get('widget_id', 0)}")
            else:
                logger.info(f"[Playwright] captchaWidget is defined: {widget_info.get('captchaWidget_value')}")
            
            widget_id = widget_info.get('widget_id', 0)
        except Exception as e:
            logger.warning(f"[Playwright] Error checking captchaWidget: {e}, defaulting to 0")
            widget_id = 0
            try:
                await page.evaluate("""
                    () => {
                        if (typeof window.captchaWidget === 'undefined' || window.captchaWidget === null) {
                            window.captchaWidget = 0;
                        }
                    }
                """)
            except Exception:
                pass
        
        try:
            _stale_threshold = float(
                (scraper_settings or {}).get("captcha_max_token_age_seconds", 110.0)
            )
        except Exception:
            _stale_threshold = 110.0

        logger.info(f"[Playwright] Waiting for CAPTCHA solving to complete...")
        captcha = None
        captcha_solve_duration = 0.0
        captcha_token_age = 0.0
        for _captcha_wait_attempt in range(2):
            try:
                _captcha_safe_limit = _stale_threshold
                if captcha_start_time is not None:
                    _captcha_elapsed_before_wait = time_module.time() - captcha_start_time
                    _captcha_wait_budget = max(
                        1.0,
                        (_captcha_safe_limit - 5.0) - _captcha_elapsed_before_wait
                    )
                else:
                    _captcha_wait_budget = max(5.0, _captcha_safe_limit - 5.0)
                captcha = await asyncio.wait_for(captcha_future, timeout=_captcha_wait_budget)
            except asyncio.TimeoutError as e:
                raise RuntimeError(
                    f"CAPTCHA solving timed out after {_captcha_wait_budget:.1f}s "
                    "of remaining safe wait budget"
                ) from e
            except CaptchaTokenExpired:
                raise
            except Exception as e:
                raise RuntimeError(f"CAPTCHA solving failed: {e}")

            if captcha_start_time is None:
                captcha_start_time = time_module.time()
                logger.warning(
                    "[Playwright] CAPTCHA start time not tracked, using current time for duration calculation"
                )
            captcha_received_time = time_module.time()
            if captcha_ready_time is None:
                captcha_ready_time = captcha_received_time
                logger.warning(
                    "[Playwright] CAPTCHA ready time not tracked, defaulting to receipt time"
                )
            captcha_solve_duration = max(0.0, captcha_ready_time - captcha_start_time)
            captcha_token_age = max(0.0, captcha_received_time - captcha_ready_time)

            if not captcha or len(captcha) < 50:
                raise RuntimeError("Invalid CAPTCHA token received from solver")

            if captcha_token_age < _stale_threshold:
                break

            if captcha_stale_retry_used:
                logger.error(
                    f"[Playwright] ⛔ CAPTCHA chegou tarde demais: token envelheceu "
                    f"{captcha_token_age:.1f}s antes da injecao "
                    f"(solver demorou {captcha_solve_duration:.1f}s, "
                    f"limite {_stale_threshold:.0f}s, TTL Google 120s). "
                    "Abortando antes da injecao para nao perder tempo nem gastar POST /login."
                )
                raise CaptchaTokenExpired(
                    f"reCAPTCHA token already stale on receipt: age {captcha_token_age:.1f}s "
                    f"(solver runtime {captcha_solve_duration:.1f}s, "
                    f"safe limit {_stale_threshold:.0f}s, Google TTL 120s)"
                )

            captcha_stale_retry_used = True
            logger.warning(
                f"[Playwright] CAPTCHA prewarmed ficou velho antes da injecao "
                f"(idade={captcha_token_age:.1f}s, solver={captcha_solve_duration:.1f}s). "
                "Vou descartar este token e relancar o solver uma vez agora que a pagina esta pronta."
            )
            _start_captcha_solver(
                "[Captcha] ♻️ Relancando solver porque o token prewarmed envelheceu durante a espera da pagina."
            )
        
        valid_chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_'
        invalid_chars = [c for c in captcha[:100] if c not in valid_chars]
        if invalid_chars:
            logger.warning(f"[Playwright] ⚠️ Token contains invalid characters: {set(invalid_chars)}")
        if len(captcha) < 100:
            logger.error(f"[Playwright] ❌ Token too short ({len(captcha)} chars)")
        elif len(captcha) > 5000:
            logger.warning(f"[Playwright] ⚠️ Token unusually long ({len(captcha)} chars)")
        logger.info(f"[Playwright] CAPTCHA token received ({len(captcha)} chars)")
        
        captcha_elapsed_since_login_start = time_module.time() - login_start_time
        logger.info(
            f"[Playwright] ✅ CAPTCHA solver devolveu token em {captcha_solve_duration:.1f}s "
            f"(idade ao receber={captcha_token_age:.1f}s, "
            f"elapsed total desde início do login={captcha_elapsed_since_login_start:.1f}s) — "
            "injecting token..."
        )

        inject_start_time = time_module.time()
        
        logger.info("[Playwright] Verifying grecaptcha is available before token injection...")
        
        grecaptcha_available = False
        for retry in range(3):
            grecaptcha_check = await page.evaluate("""
                () => {
                    return typeof window.grecaptcha !== 'undefined' && window.grecaptcha !== null;
                }
            """)
            
            if grecaptcha_check:
                grecaptcha_available = True
                logger.info("[Playwright] grecaptcha verified, ready for injection")
                break
            else:
                if retry < 2:
                    logger.info(f"[Playwright] grecaptcha not found yet, waiting... (retry {retry + 1}/3)")
                    await page.wait_for_timeout(250)
        
        if not grecaptcha_available:
            logger.warning("[Playwright] grecaptcha not found after retries, creating mock grecaptcha object...")
            mock_result = await page.evaluate("""
                () => {
                    // Create a minimal mock grecaptcha object if it doesn't exist
                    window.grecaptcha = window.grecaptcha || {};
                    if (!window.grecaptcha.getResponse) {
                        window.grecaptcha.getResponse = function() { return ''; };
                    }
                    if (!window.grecaptcha.enterprise) {
                        window.grecaptcha.enterprise = {};
                    }
                    if (!window.grecaptcha.enterprise.getResponse) {
                        window.grecaptcha.enterprise.getResponse = function() { return ''; };
                    }
                    return {created: true};
                }
            """)
            logger.info("[Playwright] Mock grecaptcha object created, proceeding with injection")

        logger.info("[Playwright] Injecting solved CAPTCHA token...")
        injection_result = await page.evaluate(
            """
            (token) => {
                try {
                    if (!window.grecaptcha) {
                        return {success: false, error: 'grecaptcha not found'};
                    }
                    
                    // Store original getResponse if it exists
                    let originalGetResponse = null;
                    let originalFunctionProperties = {};
                    if (typeof window.grecaptcha.getResponse === 'function') {
                        originalGetResponse = window.grecaptcha.getResponse.bind(window.grecaptcha);
                        
                        // RECOMMENDATION #7: Preserve original function properties to avoid detection
                        // Copy function properties (name, length, toString, etc.) from original
                        try {
                            originalFunctionProperties = {
                                name: originalGetResponse.name || 'getResponse',
                                length: originalGetResponse.length || 1,
                                toString: originalGetResponse.toString.bind(originalGetResponse),
                                // Also try to get other properties that might exist
                                prototype: originalGetResponse.prototype
                            };
                        } catch (e) {
                            console.warn('Could not preserve all original function properties:', e);
                        }
                    }
                    
                    // Store injected token for comparison with what doLogin retrieves
                    window._injectedCaptchaToken = token;
                    
                    // Override getResponse function - simplified and robust
                    // The website calls: grecaptcha.getResponse(captchaWidget)
                    // CRITICAL: Hook to monitor what doLogin actually retrieves
                    // RECOMMENDATION #7: Preserve function signature to match original
                    const overrideGetResponse = function(widgetId) {
                        let returnedToken = null;
                        
                        // Always return our token if no widgetId, null, or 0 (default widget)
                        if (typeof widgetId === 'undefined' || widgetId === null || widgetId === 0) {
                            returnedToken = token;
                        }
                        // If captchaWidget is defined and matches the widgetId
                        else if (typeof window.captchaWidget !== 'undefined' && window.captchaWidget !== null && widgetId === window.captchaWidget) {
                            returnedToken = token;
                        }
                        // Try original getResponse first (in case there's a real widget response)
                        else if (originalGetResponse) {
                            try {
                                const response = originalGetResponse(widgetId);
                                // If original returns a valid response, use it; otherwise use our token
                                if (response && response.length > 100) {
                                    returnedToken = response;
                                } else {
                                    returnedToken = token;
                                }
                            } catch (e) {
                                // If original fails, use our token
                                returnedToken = token;
                            }
                        }
                        // Fallback: always return our token for any widget ID
                        else {
                            returnedToken = token;
                        }
                        
                        // CRITICAL: Monitor what token is being returned (for debugging)
                        // This helps identify if doLogin retrieves the correct token
                        // Store the retrieved token to compare with injected token
                        if (returnedToken && returnedToken.length > 100) {
                            window._doLoginRetrievedToken = returnedToken;
                            window._doLoginTokenLength = returnedToken.length;
                            window._doLoginHookFired = true;
                            
                            // Compare with injected token
                            if (window._injectedCaptchaToken) {
                                if (returnedToken !== window._injectedCaptchaToken) {
                                    console.warn('[Hook] Token mismatch: Retrieved token differs from injected token!');
                                    console.warn('[Hook] Injected length:', window._injectedCaptchaToken.length);
                                    console.warn('[Hook] Retrieved length:', returnedToken.length);
                                } else {
                                    console.log('[Hook] Token match: Retrieved token matches injected token');
                                }
                            }
                        }
                        
                        return returnedToken;
                    };
                    
                    // RECOMMENDATION #7: Preserve original function properties to avoid detection
                    // Copy properties from original function to make override less detectable
                    if (originalGetResponse && Object.keys(originalFunctionProperties).length > 0) {
                        try {
                            // Set function name (if possible)
                            if (originalFunctionProperties.name) {
                                Object.defineProperty(overrideGetResponse, 'name', {
                                    value: originalFunctionProperties.name,
                                    writable: false,
                                    configurable: true
                                });
                            }
                            
                            // Preserve function length (number of parameters)
                            if (originalFunctionProperties.length !== undefined) {
                                Object.defineProperty(overrideGetResponse, 'length', {
                                    value: originalFunctionProperties.length,
                                    writable: false,
                                    configurable: true
                                });
                            }
                            
                            // CRITICAL: Preserve toString() to match original function signature
                            // This prevents detection by checking function.toString()
                            if (originalFunctionProperties.toString) {
                                overrideGetResponse.toString = originalFunctionProperties.toString;
                            }
                            
                            // Copy any other enumerable properties
                            try {
                                const originalProps = Object.getOwnPropertyNames(originalGetResponse);
                                for (const prop of originalProps) {
                                    if (prop !== 'length' && prop !== 'name' && prop !== 'prototype') {
                                        try {
                                            const descriptor = Object.getOwnPropertyDescriptor(originalGetResponse, prop);
                                            if (descriptor) {
                                                Object.defineProperty(overrideGetResponse, prop, descriptor);
                                            }
                                        } catch (e) {
                                            // Skip properties that can't be copied
                                        }
                                    }
                                }
                            } catch (e) {
                                console.warn('Could not copy all function properties:', e);
                            }
                        } catch (e) {
                            console.warn('Error preserving function properties:', e);
                        }
                    }
                    
                    // Assign the override function
                    window.grecaptcha.getResponse = overrideGetResponse;
                    
                    // CRITICAL: Override enterprise.getResponse to use the same function
                    // The website may call grecaptcha.enterprise.getResponse() with NO parameters
                    // Enterprise reCAPTCHA requires special handling - it must return token even when called with no params
                    if (window.grecaptcha.enterprise) {
                        // Create a wrapper that handles both no-param and with-param calls
                        const enterpriseGetResponse = function(widgetId) {
                            // If called with no parameters or undefined/null, return token immediately
                            if (typeof widgetId === 'undefined' || widgetId === null) {
                                return token;
                            }
                            // Otherwise use the main getResponse function
                            return overrideGetResponse(widgetId);
                        };
                        
                        // Preserve original if it exists
                        if (window.grecaptcha.enterprise.getResponse) {
                            const originalEnterpriseGetResponse = window.grecaptcha.enterprise.getResponse.bind(window.grecaptcha.enterprise);
                            // Try to preserve function properties
                            try {
                                Object.defineProperty(enterpriseGetResponse, 'name', {
                                    value: originalEnterpriseGetResponse.name || 'getResponse',
                                    writable: false,
                                    configurable: true
                                });
                                Object.defineProperty(enterpriseGetResponse, 'length', {
                                    value: originalEnterpriseGetResponse.length || 1,
                                    writable: false,
                                    configurable: true
                                });
                            } catch (e) {
                                // Ignore property setting errors
                            }
                        }
                        
                        window.grecaptcha.enterprise.getResponse = enterpriseGetResponse;
                    } else {
                        // Create enterprise object if it doesn't exist
                        window.grecaptcha.enterprise = {
                            getResponse: function(widgetId) {
                                if (typeof widgetId === 'undefined' || widgetId === null) {
                                    return token;
                                }
                                return overrideGetResponse(widgetId);
                            }
                        };
                    }
                    
                    // CRITICAL: Set the token in the hidden textarea (g-recaptcha-response)
                    // This is what reCAPTCHA does when solved naturally, and some forms read directly from textarea
                    try {
                        const textarea = document.querySelector('textarea[name="g-recaptcha-response"]');
                        if (textarea) {
                            textarea.value = token;
                            // Trigger input and change events to notify any listeners
                            textarea.dispatchEvent(new Event('input', { bubbles: true, cancelable: true }));
                            textarea.dispatchEvent(new Event('change', { bubbles: true, cancelable: true }));
                        }
                    } catch (e) {
                        console.warn('Could not set textarea value:', e);
                    }
                    
                    // CRITICAL: Ensure captchaWidget is set (doLogin uses grecaptcha.getResponse(captchaWidget))
                    if (typeof window.captchaWidget === 'undefined' || window.captchaWidget === null) {
                        window.captchaWidget = 0;
                    }
                    
                    // CRITICAL: Call onCaptchaSuccess callback (this is what happens when manual solving succeeds)
                    // This hides the error message and triggers any other state changes
                    if (typeof window.onCaptchaSuccess === 'function') {
                        try {
                            window.onCaptchaSuccess(token);
                        } catch (e) {
                            console.warn('onCaptchaSuccess callback failed:', e);
                        }
                    }
                    
                    // RECOMMENDATION #3: Update Widget State - Add 'recaptcha-checked' class and 'data-checked' attribute
                    // This is what the website does after manual CAPTCHA solving
                    try {
                        const recaptchaContainer = document.querySelector('.g-recaptcha');
                        if (recaptchaContainer) {
                            recaptchaContainer.classList.add('recaptcha-checked');
                            recaptchaContainer.setAttribute('data-checked', 'true');
                            
                            // RECOMMENDATION #3: Try harder to update checkbox state in iframe
                            // Try to access and update the iframe's checkbox state (may fail due to cross-origin)
                            try {
                                const iframe = recaptchaContainer.querySelector('iframe');
                                if (iframe) {
                                    // Try to access iframe content (will fail if cross-origin, but worth trying)
                                    try {
                                        const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
                                        const checkbox = iframeDoc.querySelector('#recaptcha-anchor, .recaptcha-checkbox');
                                        if (checkbox) {
                                            checkbox.classList.add('recaptcha-checkbox-checked');
                                            checkbox.setAttribute('aria-checked', 'true');
                                            checkbox.setAttribute('data-checked', 'true');
                                            console.log('[Injection] Successfully updated iframe checkbox state');
                                        }
                                    } catch (crossOriginError) {
                                        // Cross-origin restriction - this is expected and normal
                                        // We can't access Google's iframe content, but we've updated the container
                                        console.debug('[Injection] Cannot update iframe checkbox (cross-origin restriction - this is normal)');
                                    }
                                }
                            } catch (iframeError) {
                                console.warn('[Injection] Could not access iframe:', iframeError);
                            }
                        }
                    } catch (e) {
                        console.warn('Could not update reCAPTCHA container:', e);
                    }
                    
                    // Hide captcha error if it exists (onCaptchaSuccess should do this, but ensure it's hidden)
                    try {
                        const captchaError = document.getElementById('captchaError');
                        if (captchaError) {
                            captchaError.style.display = 'none';
                        }
                    } catch (e) {
                        console.warn('Could not hide captcha error:', e);
                    }
                    
                    // Verify token can be retrieved (with fallback if getResponse doesn't work yet)
                    let testResponse = null;
                    try {
                        testResponse = window.grecaptcha.getResponse(0);
                    } catch (e) {
                        // If getResponse fails, that's okay - we've set it up, it will work when called
                        testResponse = token;
                    }
                    
                    return {
                        success: true, 
                        tokenLength: testResponse ? testResponse.length : token.length,
                        textareaSet: !!document.querySelector('textarea[name="g-recaptcha-response"]')?.value
                    };
                } catch (e) {
                    return {success: false, error: e.message};
                }
            }
            """,
            captcha,
        )

        if not injection_result.get("success"):
            raise RuntimeError(f"Failed to inject CAPTCHA token: {injection_result.get('error', 'Unknown error')}")

        inject_time = time_module.time() - inject_start_time
        logger.info(f"[Playwright] CAPTCHA token injected (length: {injection_result.get('tokenLength', 0)}) (injection took {inject_time:.2f}s)")
        
        try:
            await page.evaluate("""
                () => {
                    const recaptchaContainer = document.querySelector('.g-recaptcha');
                    if (recaptchaContainer) {
                        recaptchaContainer.classList.add('recaptcha-checked');
                        recaptchaContainer.setAttribute('data-checked', 'true');
                    }
                    const recaptchaIframe = document.querySelector('iframe[src*="recaptcha"]');
                    if (recaptchaIframe && recaptchaIframe.parentElement) {
                        recaptchaIframe.parentElement.classList.add('recaptcha-solved');
                        recaptchaIframe.parentElement.setAttribute('data-solved', 'true');
                    }
                }
            """)
        except Exception:
            pass

        async def _wait_for_captcha_completion_state(timeout_ms: int = 12000) -> dict:
            """Wait for token + browser-visible CAPTCHA completion before submit."""
            require_visual = _cfg_bool("captcha_require_visual_checkmark_before_submit", True)
            deadline = time_module.time() + max(1.0, timeout_ms / 1000.0)
            last_state = {}
            visual_mark_attempted = False

            async def _frame_checked_state() -> dict:
                frame_state = {
                    "frame_checked": False,
                    "frame_seen": False,
                    "mark_attempted": visual_mark_attempted,
                    "mark_ok": False,
                }
                for frame in page.frames:
                    frame_url = str(getattr(frame, "url", "") or "").lower()
                    if "recaptcha" not in frame_url:
                        continue
                    frame_state["frame_seen"] = True
                    try:
                        checked = await frame.evaluate("""
                            () => {
                                const anchor = document.querySelector('#recaptcha-anchor');
                                return !!(
                                    anchor &&
                                    (
                                        anchor.getAttribute('aria-checked') === 'true' ||
                                        anchor.classList.contains('recaptcha-checkbox-checked')
                                    )
                                );
                            }
                        """)
                        if checked:
                            frame_state["frame_checked"] = True
                            return frame_state
                    except Exception:
                        continue
                return frame_state

            async def _mark_visual_if_possible() -> bool:
                for frame in page.frames:
                    frame_url = str(getattr(frame, "url", "") or "").lower()
                    if "recaptcha" not in frame_url:
                        continue
                    try:
                        marked = await frame.evaluate("""
                            () => {
                                const anchor = document.querySelector('#recaptcha-anchor');
                                if (!anchor) return false;
                                anchor.setAttribute('aria-checked', 'true');
                                anchor.classList.remove('recaptcha-checkbox-unchecked');
                                anchor.classList.add('recaptcha-checkbox-checked');
                                const border = anchor.querySelector('.recaptcha-checkbox-border');
                                if (border) {
                                    border.classList.remove('recaptcha-checkbox-border');
                                    border.classList.add('recaptcha-checkbox-border-checked');
                                }
                                const checkmark = anchor.querySelector('.recaptcha-checkbox-checkmark');
                                if (checkmark) {
                                    checkmark.style.display = 'block';
                                    checkmark.style.opacity = '1';
                                }
                                anchor.dispatchEvent(new Event('recaptcha-state-change', { bubbles: true }));
                                return true;
                            }
                        """)
                        if marked:
                            return True
                    except Exception:
                        continue
                return False

            while time_module.time() < deadline:
                try:
                    page_state = await page.evaluate("""
                        () => {
                            let token = '';
                            try {
                                if (window.grecaptcha?.enterprise?.getResponse) {
                                    token = window.grecaptcha.enterprise.getResponse() || '';
                                }
                            } catch (e) {}
                            if ((!token || token.length < 100) && window.grecaptcha?.getResponse) {
                                try {
                                    token = window.grecaptcha.getResponse(window.captchaWidget || 0) || '';
                                } catch (e) {}
                            }
                            const textarea = document.querySelector('textarea[name="g-recaptcha-response"]');
                            const textareaValue = textarea ? (textarea.value || '') : '';
                            if ((!token || token.length < 100) && textareaValue) token = textareaValue;
                            const container = document.querySelector('.g-recaptcha');
                            const captchaError = document.getElementById('captchaError');
                            return {
                                token_length: token ? token.length : 0,
                                textarea_length: textareaValue.length,
                                container_checked: !!(
                                    container &&
                                    (
                                        container.classList.contains('recaptcha-checked') ||
                                        container.getAttribute('data-checked') === 'true'
                                    )
                                ),
                                captcha_error_visible: !!(
                                    captchaError &&
                                    captchaError.offsetParent !== null &&
                                    getComputedStyle(captchaError).display !== 'none'
                                ),
                                iframe_count: document.querySelectorAll('iframe[src*="recaptcha"]').length,
                            };
                        }
                    """)
                    frame_state = await _frame_checked_state()
                    last_state = {**(page_state or {}), **frame_state}
                    token_ok = int(last_state.get("token_length") or 0) >= 100
                    iframe_present = bool(last_state.get("frame_seen") or last_state.get("iframe_count"))
                    visual_ok = bool(
                        last_state.get("frame_checked") or
                        (not iframe_present and last_state.get("container_checked"))
                    )

                    if token_ok and visual_ok and not last_state.get("captcha_error_visible"):
                        logger.info(
                            "[Playwright] ✅ CAPTCHA completion state ready before submit: "
                            f"token_len={last_state.get('token_length')} "
                            f"frame_checked={last_state.get('frame_checked')} "
                            f"container_checked={last_state.get('container_checked')}"
                        )
                        return last_state

                    if token_ok and require_visual and not visual_ok and not visual_mark_attempted:
                        visual_mark_attempted = True
                        mark_ok = await _mark_visual_if_possible()
                        last_state["mark_attempted"] = True
                        last_state["mark_ok"] = mark_ok
                        logger.info(
                            "[Playwright] CAPTCHA token ready; attempted visual checkmark sync: "
                            f"mark_ok={mark_ok}"
                        )

                    if token_ok and not require_visual and not last_state.get("captcha_error_visible"):
                        logger.info(
                            "[Playwright] CAPTCHA token ready; visual checkmark not required by config."
                        )
                        return last_state
                except Exception as state_err:
                    last_state = {"error": str(state_err)[:200]}

                await page.wait_for_timeout(500)

            raise RuntimeError(
                "CAPTCHA completion state not ready before submit: "
                f"{last_state}"
            )

        captcha_completion_state = await _wait_for_captcha_completion_state()
        logger.info(f"[Playwright] CAPTCHA completion gate passed: {captcha_completion_state}")

        submit_button = page.locator('#NewloginForm-d button#loginFormSubmitButton')
        await submit_button.wait_for(state='visible', timeout=10000)

        login_response_future = asyncio.Future()
        login_request_future = asyncio.Future()
        
        time_since_captcha = time_module.time() - captcha_received_time
        total_time = time_module.time() - login_start_time
        logger.info(f"[Playwright] Time since CAPTCHA received: {time_since_captcha:.2f}s")
        logger.info(f"[Playwright] Total time so far: {total_time:.1f}s, CAPTCHA-to-submit: {time_since_captcha:.1f}s")
        
        # Route handler UNIFICADO: Injeta headers reais do Chrome + valida POST data
        # IMPORTANTE: Não registramos route aqui! O force_login_headers (mais abaixo)
        # já faz o route.continue_() com os headers corretos. Este bloco apenas loga.
        # O route registration foi removido para evitar conflito com force_login_headers.
        logger.info("[Playwright] Interceptação do POST /login configurada abaixo (log ou override de headers)")
        
        def handle_request(request):
            nonlocal login_post_submitted, login_post_network_count
            url = request.url
            if '/VistosOnline/login' in url and request.method == 'POST':
                login_post_submitted = True
                login_post_network_count += 1
                if login_post_network_count > 1:
                    logger.error(
                        f"[Playwright] ⚠️ POST /login DUPLICADO detectado pela rede "
                        f"(total={login_post_network_count}). O botão de login só devia "
                        "disparar UM POST — investigar causa (double-click, JS submit "
                        "extra, retry interno)."
                    )
                else:
                    logger.info(
                        f"[Playwright] [submit-count] POST /login #{login_post_network_count} "
                        "capturado pela rede (esperado: exactamente 1)."
                    )
                try:
                    if not login_request_future.done():
                        request_headers = request.headers
                        cookie_header = request_headers.get('cookie', '')
                        if cookie_header:
                            has_vistos_sid = 'Vistos_sid' in cookie_header
                            has_cookiesession1 = 'cookiesession1' in cookie_header
                            if not has_vistos_sid or not has_cookiesession1:
                                logger.error("[Playwright] ERROR: Critical cookies missing from login request! (Vistos_sid=%s, cookiesession1=%s)", has_vistos_sid, has_cookiesession1)
                        else:
                            logger.error("[Playwright] ERROR: No cookies in login request!")                        
                       
                        try:
                            post_data = request.post_data
                            logger.info(f"[Playwright] Login request captured: {url} ({request.method})")
                            if not post_data:
                                logger.warning(f"[Playwright] Request body is empty!")
                        except Exception as data_error:
                            logger.warning(f"[Playwright] Could not get POST data from request: {data_error}")

                        login_request_future.set_result(request)
                except Exception as e:
                    logger.info(f"[Playwright] Error capturing login request: {e}")
        
        def handle_response(response):
            url = response.url
            request_url = response.request.url if response.request else ''
            
            is_login_endpoint = (
                '/VistosOnline/login' in url or 
                '/VistosOnline/login' in request_url or
                (response.request and response.request.method == 'POST' and '/VistosOnline/login' in response.request.url)
            )
            
            if is_login_endpoint and not login_response_future.done():
                try:
                    # --- REGRA 1: SE FOR 403, É BANIMENTO IMEDIATO ---
                    if response.status == 403:
                        logger.error(f"[Playwright] ❌ BANIMENTO TOTAL (403). IP Bloqueado.")
                        # Define a exceção imediatamente para parar o processo
                        login_response_future.set_exception(RuntimeError("HTTP 403 - Proxy/IP Banned"))
                        return
                    # ------------------------------------------------

                    logger.info(f"[Playwright] Login response: status={response.status}, URL={url}")
                    
                    # Se for redirect (302), deixamos passar para ver para onde vai
                    if response.status in [301, 302, 303, 307, 308]:
                        location = response.headers.get('location', '')
                        logger.info(f"[Playwright] Login redirect (status {response.status}) to: {location}")
                        login_response_future.set_result(response)
                    elif response.status == 403:
                        login_response_future.set_exception(RuntimeError("HTTP 403 - Proxy/IP Banned"))
                    else:
                        # The async response handler below reads the AJAX body before
                        # resolving the future. Resolving here races it and loses the
                        # real server JSON, which previously made the bot guess success.
                        logger.info(
                            "[Playwright] Login response seen; waiting for AJAX body capture "
                            "before deciding success/failure."
                        )
                except Exception as e:
                    logger.error(f"[Playwright] Error capturing login response: {e}")
            elif '/VistosOnline/login' in url or '/VistosOnline/login' in request_url:
                logger.info(f"[Playwright] Login response detected but future already done: {url} (status: {response.status})")
        
        page.on("request", handle_request)
        page.on("response", handle_response)

        language = scraper_settings.get('language', 'PT') if scraper_settings else 'PT'

        logger.info("[Playwright] Fast pre-submit readiness check...")
        fast_submit_state = await page.evaluate(
            """
            ([expectedUsername, expectedPasswordLength]) => {
                const result = {
                    form_exists: false,
                    username_ok: false,
                    password_ok: false,
                    jquery_available: false,
                    submit_button_exists: false,
                    submit_button_visible: false,
                    submit_button_enabled: false,
                    captchaWidget_value: null,
                    token_length: 0,
                    token_source: null,
                    errors: [],
                };

                try {
                    const form = document.getElementById('NewloginForm-d');
                    result.form_exists = !!form;
                    if (!form) {
                        result.errors.push('Login form not found');
                        return result;
                    }

                    if (typeof window.captchaWidget === 'undefined' || window.captchaWidget === null) {
                        window.captchaWidget = 0;
                    }
                    result.captchaWidget_value = window.captchaWidget;

                    const usernameInput = form.querySelector('input[name="username"]');
                    const passwordInput = form.querySelector('input[name="password"]');
                    const submitButton = form.querySelector('button#loginFormSubmitButton');

                    const usernameValue = usernameInput ? (usernameInput.value || '') : '';
                    const passwordValue = passwordInput ? (passwordInput.value || '') : '';
                    result.username_ok = !!usernameValue && usernameValue === expectedUsername;
                    result.password_ok = passwordValue.length > 0 && passwordValue.length === expectedPasswordLength;

                    result.jquery_available =
                        (typeof window.$ !== 'undefined' && typeof window.$.ajax === 'function') ||
                        (typeof window.jQuery !== 'undefined' && typeof window.jQuery.ajax === 'function');

                    result.submit_button_exists = !!submitButton;
                    if (submitButton) {
                        result.submit_button_visible = submitButton.offsetParent !== null;
                        if (submitButton.disabled) {
                            submitButton.disabled = false;
                            submitButton.removeAttribute('disabled');
                        }
                        result.submit_button_enabled = !submitButton.disabled;
                    }

                    let token = '';
                    try {
                        if (window.grecaptcha && window.grecaptcha.enterprise && typeof window.grecaptcha.enterprise.getResponse === 'function') {
                            token = window.grecaptcha.enterprise.getResponse() || '';
                            if (token && token.length >= 100) {
                                result.token_source = 'enterprise';
                            }
                        }
                    } catch (e) {}

                    if ((!token || token.length < 100) && window.grecaptcha && typeof window.grecaptcha.getResponse === 'function') {
                        try {
                            token = window.grecaptcha.getResponse(window.captchaWidget || 0) || '';
                            if (token && token.length >= 100) {
                                result.token_source = 'regular';
                            }
                        } catch (e) {}
                    }

                    if (!token || token.length < 100) {
                        const textarea = document.querySelector('textarea[name="g-recaptcha-response"]');
                        if (textarea && textarea.value) {
                            token = textarea.value;
                            if (token.length >= 100) {
                                result.token_source = 'textarea';
                            }
                        }
                    }
                    result.token_length = token ? token.length : 0;

                    let rgpd = form.querySelector('[name="rgpd"]');
                    if (!rgpd) {
                        rgpd = document.createElement('input');
                        rgpd.type = 'hidden';
                        rgpd.name = 'rgpd';
                        form.appendChild(rgpd);
                    }
                    rgpd.value = 'Y';

                    window.event = {
                    preventDefault: () => {},
                    stopPropagation: () => {},
                    target: form,
                    currentTarget: form,
                    type: 'submit'
                };

                    if (!result.username_ok) result.errors.push('Username field mismatch/empty');
                    if (!result.password_ok) result.errors.push('Password field mismatch/empty');
                    if (!result.jquery_available) result.errors.push('jQuery ajax unavailable');
                    if (!result.submit_button_exists) result.errors.push('Submit button missing');
                    if (!result.submit_button_visible) result.errors.push('Submit button not visible');
                    if (result.token_length < 100) result.errors.push('CAPTCHA token missing');

                    return result;
                        } catch (e) {
                    result.errors.push(e.message);
                    return result;
                }
            }
            """,
            [username, len(password)]
        )

        logger.info(
            f"[Playwright] Fast pre-submit: user_ok={fast_submit_state.get('username_ok')} "
            f"pass_ok={fast_submit_state.get('password_ok')} "
            f"captcha_len={fast_submit_state.get('token_length', 0)} "
            f"src={fast_submit_state.get('token_source')} "
            f"jquery={fast_submit_state.get('jquery_available')} "
            f"button_visible={fast_submit_state.get('submit_button_visible')} "
            f"button_enabled={fast_submit_state.get('submit_button_enabled')}"
        )

        if not fast_submit_state.get('jquery_available'):
            logger.info(
                "[Playwright] Fast pre-submit: jQuery/ajax ainda indisponivel; "
                "vou aguardar uma hidratacao faseada antes de desistir."
            )
            for hydrate_attempt, hydrate_timeout_ms in enumerate((4000, 6000, 8000), start=1):
                if fast_submit_state.get('jquery_available'):
                    break

                try:
                    await page.wait_for_function(
                        """
                        () => {
                            return !!(
                                typeof window.$ !== 'undefined' &&
                                window.$ &&
                                typeof window.$.ajax === 'function'
                            );
                        }
                        """,
                        timeout=hydrate_timeout_ms,
                    )
                except Exception:
                    pass

                try:
                    hydrate_state = await page.evaluate(
                        """
                        () => {
                            const form = document.querySelector('#NewloginForm-d, form[id="NewloginForm-d"], form[name="NewloginForm-d"], form');
                            const submitButton =
                                document.querySelector('#NewloginForm-d button[type="submit"], #NewloginForm-d input[type="submit"]') ||
                                document.querySelector('#loginSubmit') ||
                                document.querySelector('button[type="submit"], input[type="submit"]');

                            let token = '';
                            try {
                                if (window.grecaptcha && window.grecaptcha.enterprise && typeof window.grecaptcha.enterprise.getResponse === 'function') {
                                    token = window.grecaptcha.enterprise.getResponse() || '';
                                }
                            } catch (e) {}
                            if ((!token || token.length < 100) && window.grecaptcha && typeof window.grecaptcha.getResponse === 'function') {
                                try {
                                    token = window.grecaptcha.getResponse(window.captchaWidget || 0) || '';
                                } catch (e) {}
                            }
                            if (!token || token.length < 100) {
                                const textarea = document.querySelector('textarea[name="g-recaptcha-response"]');
                                if (textarea && textarea.value) token = textarea.value;
                            }

                            return {
                                jquery_available: !!(typeof window.$ !== 'undefined' && window.$ && typeof window.$.ajax === 'function'),
                                submit_button_exists: !!submitButton,
                                submit_button_visible: !!(submitButton && submitButton.offsetParent !== null),
                                submit_button_enabled: !!(submitButton && !submitButton.disabled),
                                token_length: token ? token.length : 0,
                                popup_visible: !!(
                                    document.querySelector('#popup') &&
                                    document.querySelector('#popup').offsetParent !== null
                                ),
                                form_exists: !!form,
                                ready_state: document.readyState || '',
                            };
                        }
                        """
                    )
                    fast_submit_state.update(hydrate_state or {})
                    logger.info(
                        f"[Playwright] Fast pre-submit recheck {hydrate_attempt}/3: "
                        f"jquery={fast_submit_state.get('jquery_available')} "
                        f"captcha_len={fast_submit_state.get('token_length', 0)} "
                        f"button_visible={fast_submit_state.get('submit_button_visible')} "
                        f"popup_visible={fast_submit_state.get('popup_visible')} "
                        f"readyState={fast_submit_state.get('ready_state')}"
                    )
                except Exception as hydrate_err:
                    logger.warning(
                        f"[Playwright] Fast pre-submit recheck {hydrate_attempt}/3 falhou: {hydrate_err}"
                    )

        fast_errors = fast_submit_state.get('errors', [])
        if fast_submit_state.get('jquery_available'):
            fast_errors = [err for err in fast_errors if err != 'jQuery ajax unavailable']
        if fast_errors:
            logger.warning(
                f"[Playwright] Fast pre-submit detected {len(fast_errors)} issue(s): "
                + "; ".join(str(e) for e in fast_errors[:6])
            )

        if (
            not fast_submit_state.get('form_exists')
            or not fast_submit_state.get('username_ok')
            or not fast_submit_state.get('password_ok')
            or not fast_submit_state.get('jquery_available')
            or not fast_submit_state.get('submit_button_exists')
            or not fast_submit_state.get('submit_button_visible')
            or int(fast_submit_state.get('token_length', 0) or 0) < 100
        ):
            raise RuntimeError(
                "Fast pre-submit readiness failed: "
                + "; ".join(str(e) for e in fast_errors[:6])
            )

        logger.info("[Playwright] Immediate submit path armed — avoiding legacy re-check loops.")
        
        logger.info("[Playwright] Injecting hook to capture login AJAX response...")
        await page.evaluate("""
            () => {
                // Hook into jQuery AJAX to capture login response
                // This will intercept the AJAX call made by doLogin
                if (typeof $ !== 'undefined' && typeof $.ajax === 'function') {
                    const originalAjax = $.ajax;
                    $.ajax = function(options) {
                        // Check if this is the login request
                        if (options.url && options.url.includes('/VistosOnline/login')) {
                            const originalSuccess = options.success;
                            const originalError = options.error;
                            options.success = function(data, textStatus, jqXHR) {
                                try {
                                    // Store the result for later retrieval
                                    let resultObj = null;
                                    window._lastLoginAjaxSeen = true;
                                    window._lastLoginAjaxSuccess = true;
                                    window._lastLoginAjaxStatus = jqXHR ? jqXHR.status : null;
                                    window._lastLoginAjaxTextStatus = textStatus || '';
                                    window._lastLoginRaw = (typeof data === 'string') ? data : JSON.stringify(data || null);
                                    if (typeof data === 'string') {
                                        resultObj = JSON.parse(data);
                                    } else if (typeof data === 'object') {
                                        resultObj = data;
                                    }
                                    
                                    if (resultObj) {
                                        window._lastLoginResult = resultObj;
                                        window._lastLoginResultType = resultObj.type || 'unknown';
                                        window._lastLoginResultDesc = resultObj.description || 'N/A';
                                        console.log('[Hook] Login AJAX success intercepted - type:', resultObj.type, 'description:', resultObj.description);
                                    }
                                } catch (e) {
                                    console.warn('[Hook] Failed to parse login AJAX result:', e);
                                }

                                // Do NOT call the site's original success callback here.
                                // That callback immediately calls location.reload(), which
                                // destroys these captured variables before Playwright can
                                // inspect the real login result.
                                window._loginAjaxOriginalSuccessSuppressed = true;
                                return undefined;
                            };
                            options.error = function(jqXHR, textStatus, errorThrown) {
                                try {
                                    window._lastLoginAjaxSeen = true;
                                    window._lastLoginAjaxError = true;
                                    window._lastLoginAjaxStatus = jqXHR ? jqXHR.status : null;
                                    window._lastLoginAjaxTextStatus = textStatus || '';
                                    window._lastLoginAjaxErrorThrown = errorThrown ? String(errorThrown) : '';
                                    window._lastLoginRaw = jqXHR && jqXHR.responseText ? jqXHR.responseText : '';
                                    console.warn('[Hook] Login AJAX error intercepted - status:', window._lastLoginAjaxStatus, 'textStatus:', textStatus);
                                } catch (e) {
                                    console.warn('[Hook] Failed to capture login AJAX error:', e);
                                }
                                // Same as success: avoid site alert/reload side effects until
                                // Python has recorded the actual error state.
                                window._loginAjaxOriginalErrorSuppressed = true;
                                return undefined;
                            };
                        }
                        // Call original ajax
                        return originalAjax.apply(this, arguments);
                    };
                    console.log('[Hook] jQuery AJAX hook installed');
                } else {
                    console.log('[Hook] jQuery not available yet, hook will be installed when jQuery loads');
                }
            }
        """)
        
             # --- PREPARAÇÃO DO CLIQUE (ASSINATURA DIGITAL PERFEITA) ---
        # Baseado na captura F12: Headers EXATOS que o site espera.
        
        # 1. Interceptador do POST /login
        # Por defeito só regista o corpo; o browser mantém os headers nativos do jQuery.
        # Forçar headers a partir de um HAR antigo pode falhar validação no servidor.
        # Ative login_post_header_override = true no TOML para o modo legado.
        async def _login_post_log_only(route, request):
            try:
                post_data = request.post_data
                if post_data:
                    from urllib.parse import parse_qs
                    parsed = parse_qs(post_data)
                    captcha_val = (parsed.get("captchaResponse") or [""])[0]
                    post_user = (parsed.get("username") or [""])[0]
                    post_pass = (parsed.get("password") or [""])[0]
                    post_language = (parsed.get("language") or [""])[0]
                    post_rgpd = (parsed.get("rgpd") or [""])[0]
                    logger.info(
                        f"[Playwright] Login POST: {len(post_data)} chars, captcha len={len(captcha_val)}"
                    )
                    logger.info(
                        "[Playwright] Login POST fields: "
                        f"user_ok={post_user == username} "
                        f"pass_len_ok={len(post_pass) == len(password)} "
                        f"language={post_language or '-'} rgpd={post_rgpd or '-'}"
                    )
                    if len(captcha_val) < 100:
                        logger.error(
                            f"[Playwright] CAPTCHA token too short in POST ({len(captcha_val)} chars)"
                        )
            except Exception as parse_error:
                logger.warning(f"[Playwright] Could not parse POST data: {parse_error}")
            await route.continue_()

        async def force_login_headers(route, request):
            headers = request.headers.copy()

            headers["accept"] = "*/*"
            headers["accept-encoding"] = "gzip, deflate, br, zstd"
            if _lang_upper == "EN":
                headers["accept-language"] = "en-GB,en;q=0.9,pt;q=0.8"
            else:
                headers["accept-language"] = "pt-BR,pt;q=0.9"
            headers["content-type"] = "application/x-www-form-urlencoded; charset=UTF-8"
            headers["origin"] = SITE_ORIGIN
            headers["referer"] = (
                f"{SITE_ORIGIN}/VistosOnline/Authentication.jsp?language={language}"
            )
            headers["sec-fetch-dest"] = "empty"
            headers["sec-fetch-mode"] = "cors"
            headers["sec-fetch-site"] = "same-origin"
            headers["x-requested-with"] = "XMLHttpRequest"

            try:
                post_data = request.post_data
                if post_data:
                    from urllib.parse import parse_qs
                    parsed = parse_qs(post_data)
                    captcha_val = (parsed.get("captchaResponse") or [""])[0]
                    post_user = (parsed.get("username") or [""])[0]
                    post_pass = (parsed.get("password") or [""])[0]
                    post_language = (parsed.get("language") or [""])[0]
                    post_rgpd = (parsed.get("rgpd") or [""])[0]
                    logger.info(
                        f"[Playwright] Login POST: {len(post_data)} chars, captcha len={len(captcha_val)}"
                    )
                    logger.info(
                        "[Playwright] Login POST fields: "
                        f"user_ok={post_user == username} "
                        f"pass_len_ok={len(post_pass) == len(password)} "
                        f"language={post_language or '-'} rgpd={post_rgpd or '-'}"
                    )
                    if len(captcha_val) < 100:
                        logger.error(
                            f"[Playwright] CAPTCHA token too short in POST ({len(captcha_val)} chars)"
                        )
            except Exception as parse_error:
                logger.warning(f"[Playwright] Could not parse POST data: {parse_error}")

            await route.continue_(headers=headers)

        _use_hdr_override = bool(
            (scraper_settings or {}).get("login_post_header_override", False)
        )
        await page.route(
            "**/VistosOnline/login",
            force_login_headers if _use_hdr_override else _login_post_log_only,
        )
        if _use_hdr_override:
            logger.info(
                "[Playwright] login_post_header_override=ON — headers AJAX forçados no POST /login"
            )
        else:
            logger.info(
                "[Playwright] POST /login — headers nativos (login_post_header_override=OFF)"
            )
        
        # 2. O fast pre-submit readiness check acima já validou o token, a
        # visibilidade do botão e a presença de rgpd=Y. Daqui em diante
        # seguimos directamente para o click único, sem re-checks nem pausas.

        # 5. Configura Captura de Resposta AJAX
        async def handle_login_response(response):
            try:
                if '/VistosOnline/login' in response.url and response.request.method == 'POST':
                    if not login_response_future.done():
                        # Banimento Imediato
                        if response.status == 403:
                            login_response_future.set_exception(RuntimeError("HTTP 403 - Proxy Banned"))
                            return
                        
                        # Salva corpo
                        try:
                            body = _normalize_server_text(await response.text())
                            try:
                                page._login_result = json.loads(body)
                            except:
                                page._login_result = {"raw": body}
                            login_response_future.set_result(response)
                            logger.info(f"[Playwright] ✅ Resposta AJAX Capturada: Status {response.status}")
                        except Exception as e:
                            logger.warning(f"[Playwright] Erro ao ler resposta: {e}")
                            try:
                                page._login_result = None
                                page._login_body_read_error = str(e)
                            except Exception:
                                pass
                            if not login_response_future.done():
                                login_response_future.set_result(response)
            except Exception:
                pass

        page.on("response", handle_login_response)

        # 6.0. Guard de token CAPTCHA expirado.
        # reCAPTCHA tokens só são válidos 120s a contar do momento em que a
        # Google os emite (e isso acontece DURANTE o solve, não no fim). Se
        # o solver demorou tanto que mesmo somando o tempo até aqui o token
        # já passou ~115s, abortamos antes de gastar o POST /login. Sem
        # isto, o MNE devolve a mensagem genérica "Foi encontrado um erro
        # ao executar a operação." (ver doLogin AjaxFailed), que parece um
        # bloqueio de proxy mas é só o token caducado — foi exactamente o
        # que aconteceu no log de 06:57:55→07:01:25 (181s de solve + 30s
        # de overhead → token com >210s antes do POST, rejeição imediata).
        try:
            _stale_threshold = float(
                (scraper_settings or {}).get("captcha_max_token_age_seconds", 110.0)
            )
        except Exception:
            _stale_threshold = 110.0
        try:
            _real_age = time_module.time() - (captcha_start_time or time_module.time())
        except Exception:
            _real_age = 0.0
        if _real_age >= _stale_threshold:
            logger.error(
                f"[Playwright] ⛔ Abortando POST /login — token CAPTCHA tem "
                f"{_real_age:.1f}s (limite {_stale_threshold:.0f}s, TTL Google 120s). "
                "Submeter agora seria gastar a tentativa para nada e penalizar o proxy."
            )
            raise CaptchaTokenExpired(
                f"reCAPTCHA token age {_real_age:.1f}s exceeds safe limit "
                f"{_stale_threshold:.0f}s (Google TTL 120s); solver too slow"
            )

        # 6. O CLIQUE REAL (O navegador gera o restante dos headers automaticamente)
        # GUARDA: só permitimos um único click. Se por qualquer razão este bloco
        # for re-entrado (não devia, mas auditamos), abortamos antes de fazer
        # outro POST /login.
        if login_post_click_count > 0:
            logger.error(
                f"[Playwright] ⛔ Tentativa de re-clicar o botão de login "
                f"(clicks_anteriores={login_post_click_count}). Abortando para "
                "não duplicar POST /login."
            )
            raise LoginPostSubmittedFailure(
                f"Login submit click already performed {login_post_click_count} time(s); "
                "refusing duplicate click."
            )
        login_post_click_count += 1
        logger.info(
            f"[Playwright] [submit-count] Click #{login_post_click_count} no botão de login "
            "(esperado: exactamente 1 click → 1 POST /login)."
        )
        await submit_button.click(delay=random.randint(20, 40))
        logger.info(
            f"[Playwright] [submit-count] Click #{login_post_click_count} concluído. "
            "Aguardando POST /login na rede..."
        )
        
        # 7. Processa o resultado
        try:
            login_response = await asyncio.wait_for(login_response_future, timeout=30.0)
            login_http_status = getattr(login_response, "status", None)

            # Ler o body da resposta capturada
            result_data = None
            body_text = ""
            try:
                body_bytes = await login_response.body()
                body_text  = _normalize_server_text(
                    body_bytes.decode('utf-8', errors='replace').strip()
                )
                if body_text:
                    try:
                        result_data = json.loads(body_text)
                        logger.info(f"[Playwright] 📋 Resposta do servidor (JSON): {result_data}")
                    except json.JSONDecodeError:
                        # Nao e JSON — pode ser HTML de redirect ou mensagem simples
                        result_data = {"raw": body_text}
                        logger.info(f"[Playwright] 📋 Resposta do servidor (raw): {body_text[:300]}")
                else:
                    logger.info("[Playwright] 📋 Resposta vazia — provavelmente redirect imediato (OK)")
            except Exception as _body_err:
                logger.warning(f"[Playwright] Nao foi possivel ler body da resposta: {_body_err}")

            if result_data is None:
                captured_result = getattr(page, "_login_result", None)
                if captured_result:
                    result_data = captured_result
                    logger.info(f"[Playwright] 📋 Resposta AJAX recuperada do handler: {result_data}")

            if result_data is None:
                ajax_state = {}
                for ajax_wait in range(24):
                    try:
                        ajax_state = await page.evaluate("""
                            () => {
                                const raw = window._lastLoginRaw || '';
                                let parsed = window._lastLoginResult || null;
                                if (!parsed && raw) {
                                    try { parsed = JSON.parse(raw); } catch (e) {}
                                }
                                return {
                                    seen: !!window._lastLoginAjaxSeen,
                                    error: !!window._lastLoginAjaxError,
                                    status: window._lastLoginAjaxStatus || null,
                                    textStatus: window._lastLoginAjaxTextStatus || '',
                                    errorThrown: window._lastLoginAjaxErrorThrown || '',
                                    success: !!window._lastLoginAjaxSuccess,
                                    suppressedSuccess: !!window._loginAjaxOriginalSuccessSuppressed,
                                    suppressedError: !!window._loginAjaxOriginalErrorSuppressed,
                                    result: parsed,
                                    resultType: window._lastLoginResultType || (parsed && parsed.type) || '',
                                    resultDesc: window._lastLoginResultDesc || (parsed && parsed.description) || '',
                                    rawPreview: raw ? raw.slice(0, 800) : '',
                                    url: window.location.href,
                                };
                            }
                        """)
                    except Exception:
                        ajax_state = {}

                    if ajax_state.get("result") or ajax_state.get("error") or ajax_state.get("seen"):
                        break
                    await page.wait_for_timeout(500)

                if ajax_state.get("result"):
                    result_data = ajax_state.get("result")
                    logger.info(f"[Playwright] 📋 Resposta AJAX capturada via browser hook: {result_data}")
                elif ajax_state.get("error"):
                    logger.error(f"[Playwright] ❌ AJAX /login falhou no browser: {ajax_state}")
                    raise RuntimeError(
                        "Login AJAX failed in browser: "
                        f"status={ajax_state.get('status')} "
                        f"textStatus={ajax_state.get('textStatus')} "
                        f"error={ajax_state.get('errorThrown')}"
                    )
                elif ajax_state.get("seen"):
                    raw_preview = ajax_state.get("rawPreview") or ""
                    if raw_preview:
                        result_data = {"raw": raw_preview}
                        logger.info(
                            "[Playwright] 📋 AJAX /login visto sem JSON parseável; "
                            f"raw={raw_preview[:300]}"
                        )
                else:
                    logger.warning(f"[Playwright] AJAX /login não expôs resultado no browser hook: {ajax_state}")

            if login_http_status == 429:
                logger.error(
                    "[Playwright] HTTP 429 no POST /login — limite de tentativas / bloqueio"
                )
                await _save_debug_html("login_429")
                try:
                    await capture_browser_error_bundle(
                        page, "login_rate_limited", username,
                        RuntimeError("HTTP 429 no login"),
                        extra_context={
                            "http_status": 429,
                            "response_body_preview": (body_text or "")[:800],
                            "triage_hint": (
                                "Site pode ter bloqueado o utilizador ou IP/proxy por excesso "
                                "de tentativas."
                            ),
                        },
                    )
                except Exception:
                    pass
                raise RuntimeError(
                    "Login HTTP 429 — possível bloqueio por taxa / utilizador bloqueado"
                )

            if login_http_status and login_http_status >= 500:
                logger.error(f"[Playwright] HTTP {login_http_status} no POST /login")
                await _save_debug_html("login_5xx")
                try:
                    await capture_browser_error_bundle(
                        page, "login_server_http_error", username,
                        RuntimeError(f"HTTP {login_http_status} no login"),
                        extra_context={
                            "http_status": login_http_status,
                            "response_body_preview": (body_text or "")[:800],
                            "triage_hint": (
                                "Erro no servidor MNE; pode ser temporário. Retentar mais tarde "
                                "ou outro proxy."
                            ),
                        },
                    )
                except Exception:
                    pass
                raise RuntimeError(f"Login falhou com HTTP {login_http_status}")

            if result_data and isinstance(result_data, dict):
                r_type = result_data.get('type', '').lower()
                r_desc = _normalize_server_text(result_data.get('description', ''))
                raw_response = _normalize_server_text(str(result_data.get('raw') or ''))
                if raw_response and (
                    'NewloginForm-d' in raw_response
                    or 'Authentication.jsp' in raw_response
                    or 'Iniciar Sessão' in raw_response
                    or 'Perdeu a sessão' in raw_response
                    or 'Session lost' in raw_response
                ):
                    logger.error(
                        "[Playwright] ❌ POST /login devolveu HTML de login/sessão perdida, "
                        "não é login aceite."
                    )
                    await _save_debug_html("login_returned_authentication_html")
                    raise RuntimeError(
                        "Login rejected/unknown: /login returned authentication or session-lost HTML"
                    )
                
                if r_type in ['error', 'recaptchaerror', 'secblock', 'warning', 'redirect', 'rgpderror']:
                    logger.error(
                        f"[Playwright] ❌ SERVIDOR REJEITOU: http={login_http_status} "
                        f"tipo={r_type}, desc={r_desc}"
                    )
                    await _save_debug_html("login_rejected")
                    _generic_pt = (
                        "foi encontrado um erro ao executar" in (r_desc or "").lower()
                    )
                    try:
                        await capture_browser_error_bundle(
                            page, "login_rejected_server", username,
                            RuntimeError(f"{r_type}: {r_desc}"),
                            extra_context={
                                "http_status": login_http_status,
                                "response_body_preview": (body_text or "")[:800],
                                "server_message_type": r_type,
                                "server_message_description": (r_desc or "")[:2000],
                                "triage_hint": (
                                    "Mensagem genérica do site: frequentemente credenciais "
                                    "inválidas, conta bloqueada, sessão/captcha inválido, ou "
                                    "falha backend. Ver HTTP status e body_preview; testar login "
                                    "manual no mesmo proxy."
                                    if _generic_pt
                                    else "Ver descrição do servidor e testar login manual se necessário."
                                ),
                            },
                        )
                    except Exception:
                        pass
                    raise RuntimeError(f"Login Rejeitado pelo Site: {r_type} - {r_desc}")
                
                if not r_type and r_desc:
                    logger.warning(f"[Playwright] ⚠️ Resposta sem tipo mas com descrição: {r_desc}")
                
                result_str = str(result_data).lower()
                if 'error' in result_str or 'invalid' in result_str or 'blocked' in result_str or 'captcha' in result_str:
                    # Verificar se e raw HTML (pode ter "error" em scripts) — nao e erro real
                    if result_data.get('raw') and len(result_data['raw']) > 500:
                        logger.info("[Playwright] Resposta raw longa — provavelmente HTML de redirect (OK)")
                    else:
                        logger.error(f"[Playwright] ❌ Possível erro na resposta: {result_data}")
                        await _save_debug_html("login_rejected_suspect")
                        try:
                            await capture_browser_error_bundle(
                                page, "login_rejected_suspect", username,
                                RuntimeError(str(result_data)[:2000]),
                                extra_context={
                                    "http_status": login_http_status,
                                    "response_body_preview": (body_text or "")[:800],
                                },
                            )
                        except Exception:
                            pass
                        raise RuntimeError(f"Login possivelmente rejeitado: {result_data}")
                
                logger.info(f"[Playwright] ✅ Login Aceito! Tipo: {r_type or 'redirect/OK'}")
                login_post_accepted = True
            else:
                current_after_login = ""
                try:
                    current_after_login = page.url
                except Exception:
                    pass
                if "Authentication.jsp" in current_after_login:
                    logger.error(
                        "[Playwright] ❌ Resultado do login desconhecido: POST /login respondeu, "
                        "mas nenhum JSON/AJAX foi capturado e a página continua no login."
                    )
                    await _save_debug_html("login_unknown_still_authentication")
                    raise RuntimeError(
                        "Login outcome unknown: no trustworthy AJAX response and still on Authentication.jsp"
                    )
                logger.info(
                    "[Playwright] ✅ Login aceito por navegação/redirect confirmado "
                    f"(URL atual={current_after_login or 'unknown'})"
                )
                login_post_accepted = True
            
        except asyncio.TimeoutError:
             logger.error("[Playwright] ❌ TIMEOUT após clique.")
             await _save_debug_html("timeout_submit")
             try:
                 await capture_browser_error_bundle(
                     page, "login_submit_timeout", username, asyncio.TimeoutError(),
                 )
             except Exception:
                 pass
             raise RuntimeError("Timeout no Submit")             
        submit_time = time_module.time() - login_start_time
        logger.info(
            "[Playwright] ✅ Login submitted in %.1fs total"
            "  | page-load=%.1fs"
            "  | typing=%.1fs"
            "  | captcha-solve=%.1fs"
            "  | inject+submit=%.1fs"
            "  | waits/human=%.1fs",
            submit_time,
            nav_time,
            fill_time,
            captcha_solve_duration,
            time_module.time() - inject_start_time,
            max(0.0, submit_time - nav_time - fill_time - captcha_solve_duration
                - (time_module.time() - inject_start_time)),
        )
        # Auditoria final do submit do login: clicks no nosso lado vs POSTs
        # observados na rede. Em condições normais ambos devem ser exactamente 1.
        if login_post_click_count != 1 or login_post_network_count != 1:
            logger.warning(
                f"[Playwright] [submit-count] AUDITORIA login submit: "
                f"clicks_nosso_lado={login_post_click_count} | "
                f"POSTs_observados_na_rede={login_post_network_count} "
                "(esperado: 1/1)."
            )
        else:
            logger.info(
                f"[Playwright] [submit-count] ✅ Login submit OK: "
                f"clicks=1 | POST /login=1 (sem duplicação)."
        )

        try:
            await page.wait_for_load_state('domcontentloaded', timeout=10000)
        except Exception:
            await page.wait_for_timeout(1000)

        pages = context.pages
        if not pages:
            raise RuntimeError("No pages available in browser after form submission")
        
        current_page = await _choose_and_prune_context_page(pages[-1], "post_login_submit")
        try:
            _live_page_count = len([p for p in context.pages if not p.is_closed()])
        except Exception:
            _live_page_count = len(context.pages)
        logger.info(f"[Playwright] Pages in browser after submission: {_live_page_count}")
        
        # Inicializa a variável ANTES dos try/except para evitar erros
        final_url = None
        
        try:
            await current_page.wait_for_load_state('domcontentloaded', timeout=10000)
        except Exception:
            await current_page.wait_for_timeout(500)

        try:
            # Espera a URL mudar para a área logada
            await current_page.wait_for_function(
                "() => window.location.href.includes('/VistosOnline') && !window.location.href.includes('Authentication.jsp')",
                timeout=15000
            )
            final_url = current_page.url
            logger.info(f"[Playwright] Successfully redirected to: {final_url}")
        except Exception as wait_error:
            logger.info(f"[Playwright] URL wait timeout: {wait_error}, checking current URL")
            try:
                final_url = current_page.url
                if 'Authentication.jsp' in final_url:
                    logger.info("[Playwright] Still on login page, waiting for JavaScript redirect...")
                    await current_page.wait_for_timeout(1500)
                    final_url = current_page.url
            except Exception as e:
                logger.warning(f"[Playwright] Cannot get final URL: {e}")    

        # Pós-login: verificar cookies e navegar directamente para o Questionario
        # NÃO fazer GET à homepage nem ao profile.jsp — cada navegação extra
        # arrisca encontrar o desafio /ch/v e perder a sessão
        try:
            # Verificar cookies actuais — o redirect do login já renovou o Vistos_sid
            current_cookies = await context.cookies()
            vistos_sid_ok = any(c['name'] == 'Vistos_sid' for c in current_cookies)
            pow_cookie_ok = any(c['name'] == '_USER_CONSENT' and c.get('path', '') == '/' for c in current_cookies)
            cookie_names = [c['name'] for c in current_cookies]
            logger.info(f"[Playwright] Cookies pós-login: {len(current_cookies)} — Vistos_sid={'ok' if vistos_sid_ok else 'MISSING'} — PoW={'ok' if pow_cookie_ok else 'MISSING'} — {cookie_names}")

            if not vistos_sid_ok:
                logger.error("[Playwright] ❌ Vistos_sid ausente após login — login provavelmente rejeitado")
                raise RuntimeError("Login rejeitado pelo servidor — Vistos_sid não definido")
            
            # OBRIGATÓRIO: GET /VistosOnline/ após login
            # O servidor requer esta navegação para validar a sessão antes de aceitar /Questionario
            # Sem este passo o servidor responde "Perdeu a sessão" ao tentar aceder ao Questionario
            logger.info("[Playwright] GET /VistosOnline/ pós-login (obrigatório para validar sessão)...")
            try:
                # Navegar para homepage — pode encontrar o desafio PoW
                await current_page.goto(f"{BASE_URL}/VistosOnline/", wait_until="domcontentloaded", timeout=60000)
                
                # Aguardar que o PoW resolva e a página carregue completamente
                # O PoW faz reload automático — precisamos esperar que a URL final seja /VistosOnline/
                # e que o Vistos_sid esteja presente (confirmando sessão válida)
                for _hw in range(20):  # até 10 segundos
                    home_url = current_page.url
                    current_cookies = await context.cookies()
                    vistos_sid_ok = any(c['name'] == 'Vistos_sid' for c in current_cookies)
                    
                    if 'Authentication.jsp' in home_url:
                        logger.error(f"[Playwright] ❌ Redirecionado para login em /VistosOnline/: {home_url}")
                        raise RuntimeError("Sessão inválida — redirecionado para login ao visitar homepage")
                    
                    # Sessão válida quando: URL é /VistosOnline/ e Vistos_sid presente
                    if '/VistosOnline/' in home_url and vistos_sid_ok and 'ch/v' not in home_url:
                        logger.info(f"[Playwright] ✅ Homepage validada: {home_url} — {len(current_cookies)} cookies")
                        break
                    
                    if _hw % 4 == 0:
                        logger.info(f"[Playwright] Aguardando homepage carregar ({_hw/2:.0f}s)... URL: {home_url}")
                    await current_page.wait_for_timeout(500)
                else:
                    home_url = current_page.url
                    logger.warning(f"[Playwright] ⚠️ Homepage timeout — URL: {home_url} — continuando")
                
            except RuntimeError:
                raise
            except Exception as home_err:
                logger.warning(f"[Playwright] ⚠️ GET /VistosOnline/ falhou: {home_err} — continuando")

            # Verificar URL actual — o login é AJAX, o redirect pode demorar alguns segundos
            current_url_check = current_page.url
            if 'Authentication.jsp' in current_url_check:
                # Temos Vistos_sid = servidor aceitou o login, mas o JS ainda não fez redirect
                # Aguardar até 15s pelo redirect JavaScript
                logger.info(f"[Playwright] Vistos_sid ok mas ainda em Authentication.jsp — aguardando redirect JS...")
                for _rw in range(30):  # 15 segundos
                    await current_page.wait_for_timeout(500)
                    current_url_check = current_page.url
                    if 'Authentication.jsp' not in current_url_check:
                        logger.info(f"[Playwright] ✅ Redirect JS detectado: {current_url_check}")
                        break
                    if _rw % 6 == 0:
                        logger.info(f"[Playwright] Ainda em Authentication.jsp ({_rw/2:.0f}s)... aguardando redirect")
                else:
                    # Após 15s ainda em Authentication.jsp mas temos Vistos_sid
                    # O servidor aceitou — navegar directamente para o Questionario
                    logger.warning(f"[Playwright] ⚠️ JS redirect não aconteceu após 15s — navegando directamente para Questionario")
                    current_url_check = current_page.url

            logger.info(f"[Playwright] ✅ Sessão válida. URL actual: {current_url_check}")

            # MELHORIA 3.3 — Guardar cookies no ProxyCookiePool após login valido
            # Na proxima chamada para este proxy, reutilizamos estes cookies
            # em vez de fazer um login novo (reduz deteção e tempo de arranque)
            try:
                if proxy_cookie_pool is not None:
                    fresh_cookies = await context.cookies()
                    proxy_cookie_pool.save(
                        _cookie_pool_key(proxy_raw, username),
                        fresh_cookies,
                        user_agent,
                    )
                    logger.info(
                        f"[CookiePool] ✅ Cookies guardados para "
                        f"{_cookie_pool_key(proxy_raw, username)} "
                        f"({len(fresh_cookies)} cookies)"
                    )
            except Exception as _cpe:
                logger.warning(f"[CookiePool] Nao foi possivel guardar cookies: {_cpe}")

            # --- ALERTA DE LOGIN BEM SUCEDIDO ---
            try:
                await send_telegram_alert(f"✅ <b>LOGIN BEM SUCEDIDO!</b>\n👤 Usuário: {username}")
            except Exception: pass

            # --- NAVEGAÇÃO PARA O QUESTIONÁRIO ---
            # Preferir a navegação do portal autenticado. Um subconjunto de
            # contas acaba em `/Formulario?copy=true` quando saltamos
            # directamente para `/Questionario`; clicar "SOLICITAR PEDIDO DE
            # VISTO" tende a manter o estado server-side consistente. Mantemos
            # o GET directo como fallback.
            questionario_url = f"{BASE_URL}/VistosOnline/Questionario"
            logger.info(f"[Playwright] Navigating to Questionario at {questionario_url}...")
            questionario_ready = False
            questionario_last_err = None
            max_questionario_nav_retries = 3
            questionario_session_recovery_attempted = False
            questionario_try_portal_nav = True

            for q_attempt in range(max_questionario_nav_retries):
                try:
                    used_portal_nav = False
                    if questionario_try_portal_nav:
                        used_portal_nav = await _open_questionario_via_portal_nav(current_page)
                        if not used_portal_nav:
                            logger.warning(
                                "[Playwright] Nav do portal não abriu o Questionario "
                                "nesta tentativa — fallback para GET directo."
                            )

                    if not used_portal_nav:
                        await current_page.goto(
                            questionario_url,
                            timeout=60000,
                            wait_until="domcontentloaded",
                        )
                except Exception as nav_err:
                    questionario_last_err = nav_err
                    logger.error(
                        f"[Playwright] Erro ao navegar para Questionario "
                        f"(tentativa {q_attempt + 1}/{max_questionario_nav_retries}): {nav_err}"
                    )
                    cur_url = current_page.url
                    if "sessionLost" in cur_url or "Authentication" in cur_url:
                        raise RuntimeError("Sessão perdida ao navegar para Questionario.")
                    if q_attempt < max_questionario_nav_retries - 1:
                        await current_page.wait_for_timeout(1500 * (q_attempt + 1))
                        continue
                    raise RuntimeError(f"Falha de conexão ao carregar Questionario: {nav_err}")

                # Verificar URL — se redirecionou para login a sessão perdeu-se
                url_after_nav = current_page.url
                if 'Authentication.jsp' in url_after_nav:
                    logger.error(f"[Playwright] ❌ Sessão perdida ao navegar para Questionario — URL: {url_after_nav}")
                    cookies_now = await context.cookies()
                    logger.error(f"[Playwright] Cookies actuais: {[c['name'] for c in cookies_now]}")
                    raise RuntimeError(f"Sessão perdida ao abrir Questionario. URL: {url_after_nav}")
                
                if 'sessionLost' in url_after_nav:
                    raise RuntimeError(f"Sessão expirada ao abrir Questionario. URL: {url_after_nav}")

                _questionario_unavailable, _questionario_title, _questionario_text = await _page_service_unavailable_snapshot(current_page)
                if _questionario_unavailable:
                    raise RuntimeError(
                        "MNE devolveu página de manutenção/indisponibilidade em /Questionario. "
                        f"URL: {url_after_nav} | title={_questionario_title[:80]!r} | "
                        f"text={_short_normalized_text(_questionario_text)!r}"
                    )

                questionario_state = await _questionario_runtime_state(current_page)
                if questionario_state.get("session_lost"):
                    questionario_last_err = RuntimeError(
                        "MNE devolveu a página 'Perdeu a sessão' em /Questionario."
                    )
                    logger.warning(
                        "[Playwright] /Questionario serviu HTML de sessão perdida "
                        f"(tentativa {q_attempt + 1}/{max_questionario_nav_retries}) "
                        f"title={questionario_state.get('title', '')!r} "
                        f"text={_short_normalized_text(questionario_state.get('text') or '')!r}"
                    )
                    if not questionario_session_recovery_attempted:
                        questionario_session_recovery_attempted = True
                        recovered = await _recover_questionario_session_lost(current_page)
                        if recovered:
                            questionario_try_portal_nav = True
                            await current_page.wait_for_timeout(1200)
                            continue
                    raise RuntimeError(
                        "Sessão perdida ao abrir Questionario "
                        "(servidor devolveu página 'Perdeu a sessão')."
                    )

                # Espera o formulário do Questionario.
                try:
                    await current_page.wait_for_selector("#questForm", timeout=15000)
                    questionario_ready = True
                    logger.info(
                        f"[Playwright] Questionario form loaded "
                        f"(tentativa {q_attempt + 1}/{max_questionario_nav_retries})."
                    )
                    break
                except Exception as form_wait_err:
                    questionario_last_err = form_wait_err
                    logger.warning(
                        f"[Playwright] Questionario ainda não ficou pronto "
                        f"(tentativa {q_attempt + 1}/{max_questionario_nav_retries}): {form_wait_err}"
                    )
                    cur_url = current_page.url
                    if 'Authentication.jsp' in cur_url:
                        raise RuntimeError(f"Sessão perdida ao abrir Questionario. URL: {cur_url}")
                    if 'sessionLost' in cur_url:
                        raise RuntimeError(f"Sessão expirada ao abrir Questionario. URL: {cur_url}")
                    _questionario_unavailable, _questionario_title, _questionario_text = await _page_service_unavailable_snapshot(current_page)
                    if _questionario_unavailable:
                        raise RuntimeError(
                            "MNE devolveu página de manutenção/indisponibilidade em /Questionario. "
                            f"URL: {cur_url} | title={_questionario_title[:80]!r} | "
                            f"text={_short_normalized_text(_questionario_text)!r}"
                        ) from form_wait_err
                    questionario_state = await _questionario_runtime_state(current_page)
                    if questionario_state.get("session_lost"):
                        questionario_last_err = RuntimeError(
                            "MNE devolveu a página 'Perdeu a sessão' em /Questionario."
                        )
                        logger.warning(
                            "[Playwright] /Questionario ficou em página de sessão perdida "
                            f"após esperar #questForm "
                            f"(tentativa {q_attempt + 1}/{max_questionario_nav_retries})."
                        )
                        if not questionario_session_recovery_attempted:
                            questionario_session_recovery_attempted = True
                            recovered = await _recover_questionario_session_lost(current_page)
                            if recovered:
                                questionario_try_portal_nav = True
                                await current_page.wait_for_timeout(1200)
                                continue
                        raise RuntimeError(
                            "Sessão perdida ao abrir Questionario "
                            "(servidor devolveu página 'Perdeu a sessão')."
                        ) from form_wait_err
                    if q_attempt < max_questionario_nav_retries - 1:
                        await current_page.wait_for_timeout(1000 * (q_attempt + 1))
                        continue

            if not questionario_ready:
                await _save_debug_html("questionario_fail")
                raise RuntimeError(
                    f"Questionario form (#questForm) não encontrado após "
                    f"{max_questionario_nav_retries} tentativas. Último erro: {questionario_last_err}"
                )

            await current_page.wait_for_timeout(random.randint(1500, 3000))

            # Configurações
            cfg = scraper_settings or {}
            nationality_value = str(cfg.get("nationality_of_country", "CPV") or "CPV")
            country_of_residence = cfg.get("country_of_residence", "CPV")
            logger.info(f"[Playwright] Questionario: country_of_residence={country_of_residence} (do config)")
            duration_str = cfg.get("duration_of_stay", "7")
            try: duration_days = int(str(duration_str).strip())
            except: duration_days = 7
            
            stay_code = "SCH" if duration_days <= 90 else "TRAT"
            passport_type_code = "01"
            seasonal_work_code = "O"
            purpose_of_stay_code = "10"
            eu_family_code = "FAM_N"

            # Preenchimento — cada campo espera estar VISÍVEL+HABILITADO+POVOADO
            # antes de ser preenchido. Cascading dropdowns no Questionário do MNE
            # aparecem condicionalmente: se preenchermos antes da página os ter
            # gerado, o submit é aceite mas /Formulario devolve o HTML do
            # Questionário (shadow-redirect / soft-block).
            await _bootstrap_questionario_from_nationality(
                current_page, nationality_value, "main"
            )
            questionario_field_results = []
            questionario_fields = [
                ("#cb_question_21", country_of_residence, "País Residência"),
                ("#cb_question_2",  passport_type_code,  "Tipo Passaporte"),
                ("#cb_question_3",  stay_code,           "Duração Estadia"),
            ]
            if country_of_residence == "FRA":
                questionario_fields.append(("#cb_question_22", "N", "Questão Residência (FRA)"))
            questionario_fields.extend([
                ("#cb_question_5",  seasonal_work_code,  "Trabalho Sazonal"),
                ("#cb_question_6",  purpose_of_stay_code,"Propósito Estadia"),
                ("#cb_question_16", eu_family_code,      "Familiar UE"),
            ])

            for idx, (sel, val, desc) in enumerate(questionario_fields):
                ok = await _fill_questionario_select(
                    current_page, sel, val, desc, wait_timeout_ms=8000,
                )
                questionario_field_results.append((sel, val, desc, ok))
                if ok:
                    next_sel = (
                        questionario_fields[idx + 1][0]
                        if idx + 1 < len(questionario_fields) else None
                    )
                    await _ensure_questionario_progression(
                        current_page, sel, val, desc, next_sel
                    )
                # Pequena pausa para a página actualizar dependentes; deixamos
                # `_fill_questionario_select` fazer o gating do PRÓXIMO campo
                # (ele espera options>1) em vez de adivinhar com sleeps.
                await current_page.wait_for_timeout(200)

            # Pre-submit validation: lê o estado REAL de cada campo no DOM.
            # Se algum campo obrigatório não tem o valor esperado, NÃO clicamos
            # em Continuar — submeter um Questionário meio-validado é o que
            # provoca o /Formulario shadow-Questionário.
            try:
                snapshot = await current_page.evaluate(
                    """
                    (selectors) => selectors.map(sel => {
                        const el = document.querySelector(sel);
                        return {
                            sel,
                            value: el ? el.value : null,
                            options: el && el.options ? el.options.length : 0,
                            visible: !!(el && el.offsetParent !== null),
                        };
                    })
                    """,
                    [sel for sel, _v, _d, _ok in questionario_field_results],
                )
            except Exception:
                snapshot = []

            missing = []
            for (sel, val, desc, ok), state in zip(questionario_field_results, snapshot):
                if state.get("value") != val:
                    missing.append(f"{desc} ({sel}): esperado={val!r} actual={state.get('value')!r} options={state.get('options')}")

            if missing:
                logger.error(
                    "[Playwright] ⛔ Questionário incompleto antes do Continuar — NÃO vou clicar:\n  - "
                    + "\n  - ".join(missing)
                )
                # Tentar uma 2ª passagem rápida para os que falharam
                for sel, val, desc, ok in questionario_field_results:
                    state = next((s for s in snapshot if s.get("sel") == sel), {})
                    if state.get("value") != val:
                        logger.info(f"[Playwright] Retry Questionário field: {desc}")
                        await _fill_questionario_select(
                            current_page, sel, val, desc, wait_timeout_ms=4000,
                        )
                # Re-snapshot
                try:
                    snapshot2 = await current_page.evaluate(
                        """
                        (selectors) => selectors.map(sel => {
                            const el = document.querySelector(sel);
                            return {sel, value: el ? el.value : null};
                        })
                        """,
                        [sel for sel, _v, _d, _ok in questionario_field_results],
                    )
                except Exception:
                    snapshot2 = []
                still_missing = []
                for (sel, val, desc, _ok), state in zip(questionario_field_results, snapshot2):
                    if state.get("value") != val:
                        still_missing.append(f"{desc} ({sel}): esperado={val!r} actual={state.get('value')!r}")
                if still_missing:
                    raise PostLoginFailure(
                        "[Playwright] Questionário não pôde ser totalmente preenchido (cascading "
                        "dropdowns não foram gerados a tempo). Campos em falta: "
                        + " | ".join(still_missing)
                    )
                logger.info("[Playwright] ✅ Questionário recuperado após retry — todos os campos OK.")
            else:
                logger.info(
                    f"[Playwright] ✅ Questionário pronto: {len(questionario_field_results)} "
                    "campos validados (valores no DOM == esperado)."
                )

            # Revisão e Botão Continuar
            await current_page.wait_for_timeout(random.randint(1000, 2000))
            
            btn_continue_visible = await current_page.evaluate("() => { const btn = document.getElementById('btnContinue'); return btn && btn.style.display !== 'none' && btn.offsetParent !== null; }")
            if not btn_continue_visible:
                await current_page.evaluate("() => { const btn = document.getElementById('btnContinue'); if (btn) btn.style.display = 'block'; }")
                await current_page.wait_for_timeout(300)
            
            btn_locator = current_page.locator("#btnContinue")
            # Mouse move
            try:
                box = await btn_locator.bounding_box()
                if box:
                    await current_page.mouse.move(box['x'] + box['width']/2, box['y'] + box['height']/2, steps=10)
            except: pass

            # Click counter dedicado para o Continuar do Questionário, para
            # provar nos logs que clicamos UMA SÓ vez.
            questionario_continue_click_count = 0
            questionario_continue_post_count = 0

            def _on_quest_request(req):
                nonlocal questionario_continue_post_count
                try:
                    if req.method == "POST" and ("/Questionario" in req.url or "/Formulario" in req.url):
                        questionario_continue_post_count += 1
                        logger.info(
                            f"[Playwright] [continue-count] POST observado #{questionario_continue_post_count} "
                            f"durante Continuar: {req.method} {req.url}"
                        )
                except Exception:
                    pass

            try:
                current_page.on("request", _on_quest_request)
            except Exception:
                pass

            questionario_continue_click_count += 1
            logger.info(
                f"[Playwright] [continue-count] Click #{questionario_continue_click_count} "
                "no botão Continuar do Questionário (esperado: exactamente 1)."
            )
            await btn_locator.click()
            logger.info(
                f"[Playwright] [continue-count] Click #{questionario_continue_click_count} concluído. "
                "Aguardando navegação para /Formulario..."
            )

            # Espera navegação para o Formulario
            try:
                await current_page.wait_for_url("**/Formulario**", timeout=45000)
                logger.info(f"[Playwright] ✅ URL mudou para /Formulario: {current_page.url}")
                # IMPORTANTE: wait_for_url só espera pela mudança de URL, não
                # garante que a resposta do POST acabou de chegar nem que o
                # DOM da nova página foi parseado. Antes de qualquer
                # verificação ao conteúdo (vistoForm vs Questionário), temos
                # de esperar que a resposta server-side estabilize. Sem
                # isto, o bot pode julgar uma página meio-carregada.
                try:
                    await current_page.wait_for_load_state(
                        "domcontentloaded", timeout=20000
                    )
                except Exception as _ds_err:
                    logger.warning(
                        f"[Playwright] domcontentloaded em /Formulario demorou >20s: {_ds_err}"
                    )
                try:
                    await current_page.wait_for_load_state(
                        "networkidle", timeout=15000
                    )
                except Exception:
                    # networkidle pode falhar com long-polls; não é fatal.
                    pass
                logger.info(
                    f"[Playwright] ✅ /Formulario estabilizado (DOM + rede). "
                    f"URL final: {current_page.url}"
                )
                # Auditoria final do Continuar
                if questionario_continue_click_count != 1 or questionario_continue_post_count > 1:
                    logger.warning(
                        f"[Playwright] [continue-count] AUDITORIA Continuar: "
                        f"clicks_nosso_lado={questionario_continue_click_count} | "
                        f"POSTs_observados={questionario_continue_post_count} (esperado: 1/1)."
                    )
                else:
                    logger.info(
                        f"[Playwright] [continue-count] ✅ Continuar OK: "
                        f"clicks=1 | POSTs={questionario_continue_post_count}."
                    )
                try:
                    current_page.remove_listener("request", _on_quest_request)
                except Exception:
                    pass
            except Exception as nav_err:
                current_url = current_page.url
                logger.warning(f"[Playwright] wait_for_url Formulario timeout — URL actual: {current_url}")
                # Verificar se já está no Formulario mesmo com timeout
                if "Formulario" not in current_url:
                    if "sessionLost" in current_url or "Authentication" in current_url:
                        raise RuntimeError(f"Sessão perdida após submit do Questionario. URL: {current_url}")
                    if "Questionario" in current_url:
                        raise RuntimeError(f"Questionario submit falhou — ainda na mesma página. URL: {current_url}")
                    # Tentar esperar mais um pouco
                    await current_page.wait_for_timeout(3000)
                    current_url = current_page.url
                    if "Formulario" not in current_url:
                        raise RuntimeError(f"Não chegou ao Formulario. URL: {current_url}")

            current_url = current_page.url
            if "sessionLost" in current_url:
                raise RuntimeError("Sessão perdida após submit.")

            # Sucesso - Segundo Form
            pdf_success = await _playwright_fill_second_form(current_page, user_agent, proxy_raw, captcha_key_index, username)
            
            if pdf_success:
                logger.info("[Playwright] ✅ PDF process completed.")
                return (PDF_SUCCESS_SENTINEL,)

        except Exception as form_flow_error:
            try:
                _cap_page = locals().get("current_page") or locals().get("page")
                if _cap_page:
                    await capture_browser_error_bundle(
                        _cap_page, "form_flow_error", username, form_flow_error
                    )
            except Exception as _cap_err:
                logging.getLogger().debug(f"[BrowserCapture] form_flow: {_cap_err}")
            # Esta fase só ocorre depois do login aceite. Usar PostLoginFailure
            # impede Login()/main() de reiniciar todo o fluxo (novo CAPTCHA +
            # novo POST /login), que é o que dispara o WAF do MNE.
            if login_post_accepted:
                raise PostLoginFailure(
                    f"[Playwright] Failed during profile/first/second form flow: {form_flow_error}"
                ) from form_flow_error
            raise RuntimeError(f"[Playwright] Failed during profile/first/second form flow: {form_flow_error}")

        pool_should_invalidate = True
        # Segundo form devolveu False sem excepção: continua a ser uma falha
        # pós-login. Não devolver None aqui (faria Login() rodar proxy e pedir
        # outro CAPTCHA); subir como PostLoginFailure para main() parquear o
        # utilizador em failed_retry_later sem gastar mais solver credits.
        if login_post_accepted:
            raise PostLoginFailure(
                "second form returned False after successful login — no retry"
            )
        return None
    
     # --- CAPTURA: resposta visível do browser (JSON + screenshot) + fallback PNG legado ---
    except Exception as e:
        pool_should_invalidate = True
        logger.error(f"[Playwright Internal] Erro critico: {e}")
        try:
            _pg = locals().get("page")
            if _pg and not _playwright_login_error_already_bundled(e):
                await capture_browser_error_bundle(_pg, "critical_playwright", username, e)
            elif _pg and _playwright_login_error_already_bundled(e):
                logger.info(
                    "[BrowserCapture] Skip critical_playwright — login já registado "
                    f"({type(e).__name__})"
                )
        except Exception as _cap_err:
            logger.debug(f"[BrowserCapture] critical: {_cap_err}")
        try:
            debug_dir = os.path.join(WORKING_DIR, "debug_screenshots")
            os.makedirs(debug_dir, exist_ok=True)
            ts = time.strftime("%Y%m%d_%H%M%S")
            safe_user = (username or "unknown").replace("/", "_").replace("\\", "_")
            path = os.path.join(debug_dir, f"{safe_user}_CRITICAL_ERROR_{ts}.png")
            _pg2 = locals().get("page")
            if _pg2:
                await _pg2.screenshot(path=path, full_page=True)
                logger.info(f"[Debug] Screenshot de ERRO legado: {path}")
        except Exception:
            pass
        # Se o POST /login já tinha sido aceite, qualquer excepção aqui é
        # uma falha pós-login. Subir como PostLoginFailure para que
        # Login()/main() NÃO recomecem o fluxo completo (o que gastaria
        # outra solução de CAPTCHA e dispararia o WAF do MNE).
        if login_post_accepted and not isinstance(e, PostLoginFailure):
            raise PostLoginFailure(f"post-login step failed: {e}") from e
        # Se o servidor já respondeu explicitamente ao /login (ex.: JSON
        # {"type":"ReCaptchaError"} ou "HTTP 403 - Proxy/IP Banned"),
        # isto JÁ é uma resposta aplicacional confiável. NÃO reclassificar
        # como LoginPostSubmittedFailure, porque isso ativa o caminho de
        # "network abort" e acaba por banir o proxy / prender o utilizador
        # como se a ligação tivesse morrido antes da resposta existir.
        if (
            login_post_submitted
            and not isinstance(e, (PostLoginFailure, LoginPostSubmittedFailure))
            and not _login_fatal_skip_captcha_key_rotate(str(e))
        ):
            raise LoginPostSubmittedFailure(
                f"submitted POST /login failed before trustworthy response: {e}"
            ) from e
        raise
    # ---------------------------------------------------
    finally:
        # Fechar TLSClient se ainda estiver aberto (ex: excepção antes do close normal)
        try:
            if '_tls_client' in dir() and _tls_client is not None:
                _tls_client.close()
        except Exception:
            pass
        try:
            if pool_entry_registered and _use_browser_pool:
                if pool_should_invalidate:
                    await browser_context_pool.invalidate(_browser_pool_key)
                    logger.info(
                        f"[BrowserPool] Contexto invalidado para {_proxy_log_label(proxy_raw)}"
                    )
                else:
                    await browser_context_pool.release(_browser_pool_key)
                    logger.info(
                        f"[BrowserPool] Contexto liberado para {_proxy_log_label(proxy_raw)}"
                    )
            elif browser is not None:
                try:
                    await browser.close()
                except Exception:
                    pass
        except Exception:
            pass
        try:
            if playwright is not None:
                await playwright.stop()
        except Exception:
            pass
        gc.collect()
def _classify_proxy_error(error_str: str) -> str:
    """Classifica o tipo de erro para decidir como penalizar o proxy."""
    if _is_site_unavailable_error(error_str):
        return 'site_unavailable'  # Indisponibilidade do MNE; proxy inocente
    error_str = error_str.lower()
    if any(x in error_str for x in ['err_tunnel_connection_failed', 'err_proxy_connection_failed',
                                      'tunnel connection failed', 'proxy connection failed']):
        return 'tunnel_fail'   # Proxy morto / porta fechada
    if any(x in error_str for x in [
        'err_aborted', 'net::err_aborted', 'ns_binding_aborted',
        'err_empty_response', 'net::err_empty_response', 'empty_response',
    ]):
        return 'aborted'       # Proxy abortou a ligação
    if any(x in error_str for x in [
        'err_connection_refused', 'connection refused',
        'err_connection_reset', 'connection reset', 'econnreset',
    ]):
        return 'refused'       # Proxy recusou
    if any(x in error_str for x in ['err_connection_timed_out', 'connection timed out',
                                      'timed out', 'timeout']):
        return 'timeout'       # Proxy lento / morto
    if any(x in error_str for x in ['403', 'forbidden']):
        return 'banned'        # IP banido pelo site
    if any(x in error_str for x in ['recaptchaerror', 'secblock', 'rgpderror']):
        return 'captcha'       # CAPTCHA rejeitado
    if any(x in error_str for x in ['ssl', 'certificate', 'tls']):
        return 'ssl'           # Problema SSL do proxy
    return 'generic'


async def Login(client: httpx.Client, username: str, password: str, user_agent: str,
                proxy_raw: str, captcha_key_index: int = 0, proxy_list: list = None):
    """Login com rotação automática de proxy em caso de falha."""
    retry = max(1, min(5, _cfg_int("login_playwright_retry_max", 2)))
    current_proxy = proxy_raw
    current_client = client

    while retry > 0:
        try:
            if not await check_api_balance():
                logger.warning("[Login] Saldo baixo, esperando...")
                await asyncio.sleep(float(scraper_settings.get("captcha_balance_wait_sec", 120)) if scraper_settings else 120)
                continue

            logger.info(f"[Login] Attempting login (retries remaining: {retry}, proxy: {current_proxy.split(':')[0] if current_proxy else 'N/A'})...")
            login_result = await playwright_login(username, password, solve_recaptcha_v2,
                                                  current_proxy, user_agent, captcha_key_index)

            if login_result is None:
                logger.warning("[Login] Playwright login returned None — rotating proxy...")
                if current_proxy and state_manager:
                    state_manager.update_proxy_score(current_proxy, -10)
                current_proxy, current_client = _rotate_proxy(
                    proxy_list, current_proxy, user_agent, "none_result",
                    username=username
                )
                retry -= 1
                if retry > 0:
                    await asyncio.sleep(
                        float((scraper_settings or {}).get("login_proxy_retry_sleep_sec", 45))
                    )
                continue

            if isinstance(login_result, tuple) and len(login_result) >= 1 and login_result[0] == PDF_SUCCESS_SENTINEL:
                logger.info("[Login] PDF downloaded - user complete.")
                if current_proxy and state_manager:
                    state_manager.update_proxy_score(current_proxy, 10)
                return (PDF_SUCCESS_SENTINEL, current_client)

            retry -= 1
            if retry > 0:
                await asyncio.sleep(5)
            continue

        except PostLoginFailure as ple:
            # POST /login já foi aceite pelo MNE; repetir o fluxo completo
            # só gasta outro CAPTCHA e dispara o WAF por múltiplos logins
            # do mesmo utilizador. Libertar proxy e propagar para main().
            logger.error(
                f"[Login] {username}: post-login failure — parar retry loop "
                f"(teria gasto outro CAPTCHA): {str(ple)[:180]}"
            )
            if proxy_lease_manager and username:
                proxy_lease_manager.rotate(
                    username, current_proxy, proxy_list, reason="post_login_failure"
                )
            raise

        except LoginPostSubmittedFailure as lpsf:
            # O POST /login já saiu do browser, mas falhou antes de uma
            # resposta aplicacional confiável (ex.: ERR_EMPTY_RESPONSE).
            # NÃO repetir o fluxo completo no mesmo run: o pedido pode ter
            # chegado ao edge do MNE e uma segunda tentativa imediata tende
            # a parecer automação. Penalizar o proxy que largou o POST e
            # propagar para main()/worker pararem.
            logger.error(
                f"[Login] {username}: POST /login já submetido — parar retry loop "
                f"(retry gastaria outro CAPTCHA): {str(lpsf)[:180]}"
            )
            if current_proxy and state_manager:
                state_manager.update_proxy_score(current_proxy, -20)
            if proxy_lease_manager and current_proxy:
                try:
                    proxy_lease_manager.ban_proxy(current_proxy, reason="aborted")
                except Exception:
                    pass
                if username:
                    proxy_lease_manager.release(username)
            raise

        except CaptchaTokenExpired as cte:
            # O token CAPTCHA caducou antes de chegarmos a submetê-lo —
            # o solver foi demasiado lento (>110s). NÃO penalizar o proxy:
            # ele nem sequer foi tocado nesta tentativa. Soltar o proxy
            # para que outro user o possa usar e propagar a excepção.
            logger.error(
                f"[Login] {username}: CAPTCHA token expirado antes do POST "
                f"({str(cte)[:160]}) — proxy {current_proxy.split(':')[0] if current_proxy else 'N/A'} NÃO penalizado."
            )
            if proxy_lease_manager and username:
                proxy_lease_manager.release(username)
            raise

        except Exception as e:
            error_str = str(e)
            if _login_fatal_skip_captcha_key_rotate(error_str):
                raise
            error_type = _classify_proxy_error(error_str)
            logger.error(f"[Login] Erro ({error_type}): {error_str[:120]}")

            # Penalização por tipo de erro
            penalty = {
                'tunnel_fail': -60, 'refused': -60, 'ssl': -40,
                'aborted': -20, 'timeout': -15,
                'banned': -80, 'captcha': -20,
                'site_unavailable': 0, 'generic': -10
            }.get(error_type, -10)

            if current_proxy and state_manager:
                state_manager.update_proxy_score(current_proxy, penalty)
                if error_type in ('tunnel_fail', 'refused', 'ssl', 'banned'):
                    state_manager.check_and_burn_bad_proxy(current_proxy, error_type)
                    logger.warning(f"[Proxy] 🔥 Proxy {current_proxy.split(':')[0]} banido ({error_type})")

            # Erros de proxy → rodar imediatamente para proxy novo EXCLUSIVO
            if error_type in ('tunnel_fail', 'refused', 'ssl', 'aborted', 'timeout'):
                logger.info(f"[Proxy] Erro de conexao — rotacionando proxy para {username}...")
                if proxy_lease_manager and username:
                    new_proxy = proxy_lease_manager.rotate(
                        username, current_proxy, proxy_list, reason=error_type
                    )
                    if new_proxy:
                        current_proxy = new_proxy
                        try:
                            current_client, actual_proxy = create_session(
                                proxy_list, user_agent, username=username
                            )
                            if actual_proxy:
                                if actual_proxy != current_proxy:
                                    logger.warning(
                                        "[Proxy] Proxy sincronizado apos preflight: "
                                        f"{':'.join(str(current_proxy).split(':')[:2])} -> "
                                        f"{':'.join(str(actual_proxy).split(':')[:2])}"
                                    )
                                current_proxy = actual_proxy
                        except Exception as create_session_err:
                            logger.warning(
                                f"[Proxy] create_session falhou apos rotate para {username}: "
                                f"{create_session_err}"
                            )
                else:
                    current_proxy, current_client = _rotate_proxy(
                        proxy_list, current_proxy, user_agent, error_type,
                        username=username
                    )

            # Ban HTTP 403 / IP: não retentar com outra chave Anti-Captcha (mesmo IP).
            elif error_type == 'banned':
                if proxy_lease_manager and username:
                    proxy_lease_manager.rotate(username, current_proxy, proxy_list, reason="banned")
                logger.warning(
                    f"[Login] {error_type} para {username} — paragem imediata "
                    "(pausa longa aplicada pelo worker após actualizar CSV)."
                )
                raise

            # Falhas do solver — pausa larga para não martelar o site / quota
            elif error_type == 'captcha':
                if proxy_lease_manager and username:
                    proxy_lease_manager.rotate(username, current_proxy, proxy_list, reason="banned")
                logger.warning(
                    f"[Login] {error_type} para {username} — sem throttle global; "
                    "devolvendo controlo ao worker."
                )
                return None

            retry -= 1
            if retry > 0:
                wait_time = (4 - retry) * 5
                await asyncio.sleep(wait_time)

    logger.error("[Login] All login attempts failed")
    return None


def _rotate_proxy(proxy_list: list, bad_proxy: str, user_agent: str,
                  reason: str, username: str = None):
    """
    Selecciona um proxy diferente via PLM (se username disponivel) ou
    por seleccao directa filtrada de proxies nao banidos.
    SEMPRE passa username para garantir exclusividade.
    """
    if not proxy_list:
        return bad_proxy, None

    # Usar PLM se disponivel — garante exclusividade e regista ban
    if proxy_lease_manager and username:
        new_proxy = proxy_lease_manager.rotate(
            username, bad_proxy, proxy_list, reason=reason
        )
        if new_proxy:
            try:
                new_client, actual_proxy = create_session(
                    proxy_list, user_agent, username=username
                )
                synced_proxy = actual_proxy or new_proxy
                if actual_proxy and actual_proxy != new_proxy:
                    logger.warning(
                        "[Proxy] Proxy sincronizado apos create_session: "
                        f"{':'.join(str(new_proxy).split(':')[:2])} -> "
                        f"{':'.join(str(actual_proxy).split(':')[:2])}"
                    )
                _new_id = ":".join(str(synced_proxy).split(":")[:2])
                logger.info(f"[Proxy] ✅ Novo proxy via PLM: {_new_id} (motivo: {reason})")
                return synced_proxy, new_client
            except Exception as e:
                logger.warning(f"[Proxy] create_session falhou apos PLM rotate: {e}")

    # Fallback: seleccao directa sem PLM
    def _is_valid(p):
        if p == bad_proxy:
            return False
        if proxy_lease_manager and proxy_lease_manager.is_banned(p):
            return False
        if state_manager and state_manager.r:
            try:
                return not state_manager.r.exists(f"proxy_banned:{p}")
            except Exception:
                pass
        return True

    candidates = [p for p in proxy_list if _is_valid(p)]
    if not candidates:
        candidates = [p for p in proxy_list if p != bad_proxy] or proxy_list
        logger.warning("[Proxy] ⚠️ Todos os proxies banidos — usando fallback sem filtro")

    for attempt in range(min(3, len(candidates))):
        try:
            new_client, new_proxy = create_session(candidates, user_agent,
                                                   username=username)
            if new_proxy != bad_proxy:
                _new_id = ":".join(new_proxy.split(":")[:2])
                logger.info(f"[Proxy] ✅ Novo proxy: {_new_id} (motivo: {reason})")
                return new_proxy, new_client
        except Exception as e:
            logger.warning(f"[Proxy] Tentativa {attempt+1}/3 falhou: {e}")
            time.sleep(1)

    logger.warning("[Proxy] Nao foi possivel rodar proxy — reutilizando actual")
    return bad_proxy, None
async def main(username, password, proxy_list, process_id: int = 0):
    """
    Main flow for one user. process_id is used to rotate CAPTCHA API keys across concurrent runs.
    """
    try:
        data_file = os.path.join(os.getcwd(), 'second_form_mapping_2.json')
        user_agent = random.choice(user_agents)
        if not os.path.exists(data_file):
            logger.error("Place the Data file inside the current Directory")

        # --- NOVA LÓGICA DE ROTAÇÃO DE CHAVES ---
        raw_anti = scraper_settings.get('anti_captcha_api_key')
        anti_keys = raw_anti if isinstance(raw_anti, list) else [raw_anti]
        num_keys = len(anti_keys)

        # 1. Define a chave BASE baseada no ID do processo
        base_captcha_index = process_id % num_keys
        
        _rot_cap = max(1, _cfg_int("max_captcha_key_rotations", 2))
        max_login_attempts = min(num_keys, max(1, _rot_cap))
        mne_unavailable_proxy_retries = max(
            0,
            min(20, _cfg_int("mne_unavailable_proxy_retries", 4)),
        )
        mne_unavailable_retry_sleep = max(
            0.5,
            _cfg_float("mne_unavailable_proxy_retry_sleep_sec", 3.0),
        )
        total_login_slots = max_login_attempts + mne_unavailable_proxy_retries
        captcha_failure_count = 0
        mne_unavailable_count = 0
        
        new_client = None
        
        for login_attempt in range(total_login_slots):
            # 2. Calcula o índice atual. Falhas de manutenção/503 antes do
            # formulário não gastam CAPTCHA, por isso não avançam a rotação.
            captcha_key_index = (base_captcha_index + captcha_failure_count) % num_keys
            
            logger.info(
                f"[Login] Attempt {login_attempt + 1}/{total_login_slots} "
                f"(Using Key Index {captcha_key_index}, Process ID {process_id}, "
                f"mne_503_retries={mne_unavailable_count}/{mne_unavailable_proxy_retries})"
            )
            
            client = None
            _sess_tries = max(1, min(8, _cfg_int("create_session_max_tries", 2)))
            for i in range(_sess_tries):
                try:
                    # PROXY EXCLUSIVO: passa username para garantir 1 proxy : 1 user
                    client, proxy_raw = create_session(proxy_list, user_agent,
                                                       username=username)
                    if client is not None:
                        break
                except Exception as e:
                    logger.warning(f"[main] Session creation attempt {i+1}/{_sess_tries} failed: {e}")
                if i < _sess_tries - 1:
                    await asyncio.sleep(random.uniform(1.0, 2.0))
            
            if client is None:
                logger.error("[main] Could not create session (no proxy available?)")
                if login_attempt < max_login_attempts - 1:
                    continue
                return False
            
            try:
                # Passamos o índice calculado para a função de login
                login_result = await Login(client, username, password, user_agent, proxy_raw, captcha_key_index, proxy_list=proxy_list)
                
                if login_result is None:
                    logger.warning(f"Login attempt {login_attempt + 1} returned None. Rotating API key...")
                    captcha_failure_count += 1
                    if captcha_failure_count < max_login_attempts:
                        logger.info("Will retry with next API key index.")
                        await asyncio.sleep(5)
                    else:
                        break
                    continue
                
                login_response, new_client = login_result
                if login_response == PDF_SUCCESS_SENTINEL:
                    # --- CORREÇÃO: Usar state_manager ---
                    # Recompensa o proxy bom (latência já foi medida no teste, aqui damos pontos de sucesso)
                    state_manager.update_proxy_score(proxy_raw, 10)
                    logger.info("PDF downloaded successfully - user complete.")
                    return True
                    
            except TypeError as e:
                logger.error(f"Login attempt {login_attempt + 1} failed: Cannot unpack login result - {e}")
                continue
            except PostLoginFailure as ple:
                # Login aceite pelo servidor mas passo pós-login falhou.
                # NÃO rodar chave CAPTCHA nem reiniciar o fluxo — isso gastaria
                # outro solve e dispararia o WAF do MNE por logins repetidos
                # do mesmo utilizador em poucos segundos.
                # Propagar para process_single_user() que também interrompe o
                # seu max_user_attempts loop (sem esta propagação, main() devolve
                # False e o worker recomeça tudo, incluindo novo POST /login +
                # novo solve de CAPTCHA — foi exactamente isso que o log de
                # 06:33:43 mostrou).
                logger.error(
                    f"[main] {username}: post-login failure — NÃO rotacionar "
                    f"CAPTCHA key nem retry de login ({str(ple)[:200]})"
                )
                raise
            except LoginPostSubmittedFailure as lpsf:
                # O POST /login já foi enviado mas a tentativa morreu antes de
                # obtermos uma resposta confiável. Não rodar key nem lançar
                # novo login no mesmo run.
                logger.error(
                    f"[main] {username}: POST /login submetido mas tentativa "
                    f"falhou antes da resposta final ({str(lpsf)[:200]})"
                )
                raise
            except CaptchaTokenExpired as cte:
                # Token CAPTCHA caducou — solver demasiado lento. NÃO rodar
                # chave (não foi a chave que falhou, foi a SLA do solver).
                # Propagar para que process_single_user marque failed_retry_later
                # SEM penalizar o proxy.
                logger.error(
                    f"[main] {username}: CAPTCHA token expirado — solver demasiado "
                    f"lento ({str(cte)[:200]})"
                )
                raise
            except Exception as e:
                if _is_site_unavailable_error(str(e)) and mne_unavailable_count < mne_unavailable_proxy_retries:
                    mne_unavailable_count += 1
                    _current_proxy = None
                    if proxy_lease_manager:
                        try:
                            _current_proxy = proxy_lease_manager.current_proxy_of(username)
                        except Exception as _cp_err:
                            logger.warning(
                                f"[main] {username}: falha ao ler proxy actual "
                                f"apos MNE 503: {_cp_err}"
                            )
                    _current_proxy = _current_proxy or proxy_raw
                    if proxy_lease_manager and _current_proxy and not _is_direct_proxy(_current_proxy):
                        try:
                            proxy_lease_manager.ban_proxy(
                                _current_proxy,
                                reason="site_unavailable",
                            )
                            proxy_lease_manager.release(username)
                        except Exception as _rot_err:
                            logger.warning(
                                f"[main] {username}: falha ao libertar/soft-ban "
                                f"proxy apos MNE 503: {_rot_err}"
                            )
                    try:
                        if client is not None:
                            client.close()
                    except Exception:
                        pass
                    logger.warning(
                        f"[main] {username}: MNE devolveu 503/manutencao via "
                        f"{_proxy_safe_label(_current_proxy)}; tentando outro proxy "
                        f"({mne_unavailable_count}/{mne_unavailable_proxy_retries}) "
                        f"apos {mne_unavailable_retry_sleep:.1f}s."
                    )
                    await asyncio.sleep(mne_unavailable_retry_sleep)
                    continue
                if _login_fatal_skip_captcha_key_rotate(str(e)):
                    raise
                captcha_failure_count += 1
                logger.exception(f"Login attempt {login_attempt + 1} failed with error: {e}")
                if captcha_failure_count < max_login_attempts:
                    logger.info("Will retry with next API key index.")
                    await asyncio.sleep(5)
                else:
                    break
        else:
            logger.error("Login failed after trying all available API keys. Marking as failed.")
            return False
        logger.error("Login failed after trying configured login/proxy attempts. Marking as failed.")
        return False
    except (PostLoginFailure, CaptchaTokenExpired, LoginPostSubmittedFailure):
        raise
    except Exception as e:
        if _login_fatal_skip_captcha_key_rotate(str(e)):
            raise
        logger.error(f"Error occurred: {e}")
        return False
    finally:
        if 'client' in locals() and client is not None:
            try:
                client.close()
            except:
                pass
        if 'new_client' in locals() and new_client is not None:
            try:
                new_client.close()
            except:
                pass
        gc.collect()

def chunkify(lst: List[Any], n: int) -> List[List[Any]]:
    """Splits list lst into n nearly equal chunks."""
    if n <= 0:
        raise ValueError("Number of chunks must be positive")
    if not lst:
        return [[] for _ in range(n)]
    chunk_size = len(lst) // n
    remainder = len(lst) % n
    chunks = []
    start = 0
    for i in range(n):
        current_chunk_size = chunk_size + (1 if i < remainder else 0)
        chunks.append(lst[start:start + current_chunk_size])
        start += current_chunk_size
    return chunks

# =================================================================================
# DYNAMIC WORK QUEUE — cada worker claim users do Redis em vez de chunks fixos
#
# Arquitectura anterior (PROBLEMA):
#   main divide 6 users em 8 chunks fixos → 6 processos com 1 user, 2 idle
#   Quando um processo acaba, fica PARADO — nao pega utilizadores dos outros
#
# Nova arquitectura (SOLUCAO):
#   Redis Queue "wq:pending" contem todos os usernames pendentes
#   Cada worker pede o proximo username com BLPOP (bloqueante, atomico)
#   Se um worker termina o seu user, pega imediatamente o proximo da queue
#   Todos os N workers ficam SEMPRE a trabalhar enquanto houver users pendentes
#   Com 6 users e 8 workers: os 6 primeiros workers trabalham, os 2 extras idle
#   Com 100 users e 8 workers: todos os 8 workers trabalhao em paralelo continuo
#
# Fluxo:
#   1. main_execution_continuous() carrega CSV, empurra usernames para Redis queue
#   2. Cada worker() faz loop: BLPOP username → processa → BLPOP proximo
#   3. Se o user falha, volta para a queue (com contador de tentativas)
#   4. Se o user tem sucesso, remove da queue (nunca volta)
#   5. Reload do CSV detecta novos users e empurra para a queue
# =================================================================================

# Chaves Redis para a Work Queue
_WQ_PENDING   = "wq:pending"       # Lista de usernames pendentes (LPUSH/BLPOP)
_WQ_PROCESSING= "wq:processing:{}" # Set com workers a processar este user
_WQ_ATTEMPTS  = "wq:attempts:{}"   # Contador de tentativas por user
_WQ_KNOWN     = "wq:known"         # Set de todos os users ja conhecidos
_WQ_ACTIVE    = "wq:active"        # Set de users ACTIVAMENTE em processamento
_MAX_ATTEMPTS = 5                   # Max tentativas antes de marcar como falha


class WorkQueue:
    """
    Fila de trabalho distribuida via Redis.
    Thread-safe e process-safe — multiplos workers podem usar ao mesmo tempo.
    """

    def __init__(self, redis_client=None):
        self._r = redis_client
        # Fallback in-memory se Redis nao disponivel
        self._mem_queue:   list = []
        self._mem_known:   set  = set()
        self._mem_active:  set  = set()   # users activamente em processamento
        self._mem_lock = threading.Lock()

    def _jail_ttl(self, username: str) -> int:
        """
        TTL do jail Redis em segundos.
        >0  = ainda preso
        -2  = key inexistente
        -1  = key sem TTL
         0  = Redis indisponivel / erro
        """
        if not self._r or not username:
            return 0
        try:
            return int(self._r.ttl(f"jail:{username}") or 0)
        except Exception:
            return 0

    def push_users(self, rows: list) -> int:
        """
        Adiciona users pendentes a queue (idempotente — nao duplica).
        rows: lista de dicts com 'username', 'password', 'status'.
        Retorna o numero de users novos adicionados.

        GARANTIA: users com status processing no CSV OU no set Redis
        _WQ_ACTIVE nunca sao adicionados, evitando que outro worker
        os roube enquanto ja estao a ser processados.
        """
        added = 0
        for row in rows:
            username = str(row.get("username", "")).strip()
            status   = str(row.get("status", "")).strip().lower()
            if not username:
                continue
            # Nao adicionar users ja completos, em progresso, ou bloqueados no site
            if status in CSV_STATUS_EXCLUDE_FROM_QUEUE:
                continue
            if self._r:
                try:
                    jail_ttl = self._jail_ttl(username)
                    if jail_ttl > 0:
                        # User continua em jail Redis: não o enfileirar ainda.
                        # Também limpamos qualquer entrada stale para evitar o
                        # loop "claim -> em jail -> repush -> exauriu tentativas".
                        self._r.lrem(_WQ_PENDING, 0, username)
                        self._r.srem(_WQ_KNOWN, username)
                        self._r.delete(_WQ_ATTEMPTS.format(username))
                        continue
                    # Verificar tambem o set de activos no Redis
                    # (o CSV pode estar desatualizado quando outro worker
                    # acabou de fazer claim mas ainda nao escreveu no CSV)
                    if self._r.sismember(_WQ_ACTIVE, username):
                        continue  # ja esta a ser processado — ignorar
                    # SADD retorna 1 se foi novo, 0 se ja existia
                    is_new = self._r.sadd(_WQ_KNOWN, username)
                    if is_new:
                        self._r.rpush(_WQ_PENDING, username)
                        added += 1
                except Exception as e:
                    safe_print(f"[WQ] Redis push erro: {e}")
            else:
                with self._mem_lock:
                    if username not in self._mem_known and username not in self._mem_active:
                        self._mem_known.add(username)
                        self._mem_queue.append(username)
                        added += 1
        return added

    def mark_active(self, username: str):
        """Regista que um worker esta activamente a processar este user."""
        if self._r:
            try:
                self._r.sadd(_WQ_ACTIVE, username)
                # TTL de seguranca — limpa automaticamente se o worker crashar
                self._r.expire(_WQ_ACTIVE, 3600)
            except Exception:
                pass
        else:
            with self._mem_lock:
                self._mem_active.add(username)

    def unmark_active(self, username: str):
        """Remove o user do set de activos (chamado no finally do worker)."""
        if self._r:
            try:
                self._r.srem(_WQ_ACTIVE, username)
            except Exception:
                pass
        else:
            with self._mem_lock:
                self._mem_active.discard(username)

    def repush_user(self, username: str):
        """Volta a colocar um user na queue (apos falha recuperavel)."""
        self.unmark_active(username)
        if self._r:
            try:
                attempts = int(self._r.get(_WQ_ATTEMPTS.format(username)) or 0)
                if attempts < _MAX_ATTEMPTS:
                    # Manter em KNOWN para push_users (apos CSV reload) nao duplicar RPUSH
                    self._r.sadd(_WQ_KNOWN, username)
                    self._r.rpush(_WQ_PENDING, username)
                else:
                    safe_print(f"[WQ] {username} exauriu {_MAX_ATTEMPTS} tentativas — descartado")
            except Exception as e:
                safe_print(f"[WQ] Redis repush erro: {e}")
        else:
            with self._mem_lock:
                self._mem_known.discard(username)
                self._mem_queue.append(username)

    def claim_next(self, timeout_s: int = 10) -> Optional[str]:
        """
        Pede o proximo username da queue.
        Bloqueia ate timeout_s segundos se a queue estiver vazia.
        Retorna None se nao houver nenhum no timeout.
        """
        if self._r:
            try:
                result = self._r.blpop(_WQ_PENDING, timeout=timeout_s)
                if result:
                    _, username = result
                    # Incrementar contador de tentativas
                    key = _WQ_ATTEMPTS.format(username)
                    self._r.incr(key)
                    self._r.expire(key, 3600)
                    # Registar como activo (protege contra re-claim)
                    self.mark_active(username)
                    return username
                return None
            except Exception as e:
                safe_print(f"[WQ] Redis claim erro: {e}")
        # Fallback in-memory
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            with self._mem_lock:
                if self._mem_queue:
                    username = self._mem_queue.pop(0)
                    self._mem_active.add(username)
                    return username
            time.sleep(0.5)
        return None

    def mark_done(self, username: str):
        """Marca o user como concluido — nunca mais volta para a queue."""
        self.unmark_active(username)
        if self._r:
            try:
                self._r.delete(_WQ_ATTEMPTS.format(username))
                # Manter no KNOWN para nao ser re-adicionado
            except Exception:
                pass

    def drop_user(self, username: str):
        """Purge um utilizador da queue/known/active.

        Isto limpa entradas stale de Redis quando o CSV já o marcou como
        `failed_retry_later`, `blocked_site`, etc. Se o operador voltar a
        pôr o status em `false`, o reload do CSV adiciona-o novamente.
        """
        self.unmark_active(username)
        if self._r:
            try:
                self._r.lrem(_WQ_PENDING, 0, username)
                self._r.srem(_WQ_KNOWN, username)
                self._r.delete(_WQ_ATTEMPTS.format(username))
            except Exception as e:
                safe_print(f"[WQ] Redis drop erro: {e}")
        else:
            with self._mem_lock:
                self._mem_queue = [u for u in self._mem_queue if u != username]
                self._mem_known.discard(username)
                self._mem_active.discard(username)

    def reset_for_reload(self):
        """
        Limpa apenas a lista de users CONHECIDOS que nao estao activos.
        Users em _WQ_ACTIVE nunca sao removidos — ficam protegidos.
        Isso permite re-adicionar users que voltaram a pending no CSV
        sem interferir com os que estao a ser processados agora.
        """
        if self._r:
            try:
                # Nao retirar da KNOWN quem ainda esta na lista PENDING — senao
                # push_users volta a RPUSH e duplica entradas (monitor inflado).
                def _dec(x):
                    return x.decode() if isinstance(x, bytes) else str(x)

                pending_raw = self._r.lrange(_WQ_PENDING, 0, -1)
                pending_set = {_dec(p) for p in pending_raw}
                known = {_dec(k) for k in self._r.smembers(_WQ_KNOWN)}
                active = {_dec(a) for a in self._r.smembers(_WQ_ACTIVE)}
                to_remove = known - active - pending_set
                if to_remove:
                    self._r.srem(_WQ_KNOWN, *to_remove)
            except Exception:
                pass
        else:
            with self._mem_lock:
                # Manter known = activos ∪ fila pendente. O reset antigo (known & active)
                # removia usernames que ainda estavam só em _mem_queue, e o push_users
                # seguinte voltava a acrescentá-los — duplicados na fila in-memory.
                self._mem_known = set(self._mem_active) | set(self._mem_queue)

    def qsize(self) -> int:
        """Numero de users pendentes na queue."""
        if self._r:
            try:
                return self._r.llen(_WQ_PENDING)
            except Exception:
                pass
        with self._mem_lock:
            return len(self._mem_queue)

    def stats(self) -> str:
        return f"[WQ] {self.qsize()} users pendentes na queue"


# Instancia global (inicializada no worker)
work_queue: Optional[WorkQueue] = None


def worker(proxy_chunk: List[str], process_id: int,
           credentials_file_path: str, settings_dict: Dict,
           check_interval: int = 10, total_processes: int = 8):
    """
    Worker baseado em Dynamic Work Queue.

    Em vez de receber um chunk fixo de users, cada worker pede dinamicamente
    o proximo user disponivel da Redis Queue. Isso garante que:
      - Todos os workers ficam ocupados enquanto houver users pendentes
      - Nao ha processos idle enquanto outros estao sobrecarregados
      - Adicionar users ao CSV em runtime funciona automaticamente
    """
    import pandas as pd
    _install_graceful_signal_handlers()
    global logger, scraper_settings
    logger = setup_logging(process_id, settings_dict)
    scraper_settings = settings_dict

    max_concurrency = scraper_settings.get('max_concurrent_users_per_process', 3)

    # Inicializar globais do processo
    global state_manager
    state_manager = StateManager()

    global _PLAYWRIGHT_SEMAPHORE
    _PLAYWRIGHT_SEMAPHORE = None

    global proxy_lease_manager
    proxy_lease_manager = ProxyLeaseManager(redis_client=state_manager.r)

    global proxy_cookie_pool
    proxy_cookie_pool = ProxyCookiePool(redis_client=state_manager.r)

    global browser_context_pool
    browser_context_pool = BrowserContextPool()

    # Work Queue — partilhada entre todos os workers via Redis
    global work_queue
    work_queue = WorkQueue(redis_client=state_manager.r)

    if work_queue._r is None:
        try:
            df_seed = pd.read_csv(credentials_file_path, encoding='utf-8')
            if 'status' not in df_seed.columns:
                df_seed['status'] = 'false'
            df_seed['status'] = (
                df_seed['status'].astype(str).str.strip().str.lower()
            )
            reclaimed = _reclaim_stale_processing_rows(df_seed, credentials_file_path)
            if reclaimed:
                logger.info(
                    f"[Process-{process_id}] Sem Redis: {reclaimed} linha(s) "
                    "'processing' recuperadas antes de preencher fila local."
                )
            seeded = work_queue.push_users(df_seed.to_dict('records'))
            logger.info(
                f"[Process-{process_id}] Sem Redis: {seeded} utilizadores pendentes "
                f"carregados do CSV para fila local."
            )
        except Exception as _seed_err:
            logger.error(
                f"[Process-{process_id}] Falha ao preencher fila local (sem Redis): {_seed_err}"
            )
        _cap = min(max_concurrency, 3)
        if _cap < max_concurrency:
            logger.info(
                f"[Process-{process_id}] Sem Redis: max_concurrency "
                f"{max_concurrency} -> {_cap} (menos browsers em paralelo)."
            )
        max_concurrency = _cap

    safe_print(f"[Process-{process_id}] 🚀 Iniciado | proxies={len(proxy_chunk)} | {work_queue.stats()}")
    safe_print(f"[Process-{process_id}] {proxy_lease_manager.stats()}")

    if not proxy_chunk:
        logger.error(f"[Process-{process_id}] ❌ CRITICO: lista de proxies VAZIA!")
        return

    # Escalonamento de arranque — evitar que todos os workers batam ao mesmo tempo
    if process_id > 0:
        delay = random.randint(2, min(15, process_id * 3))
        logger.info(f"[Process-{process_id}] Aguardando {delay}s antes de iniciar...")
        time.sleep(delay)

    async def process_single_user(username: str, password: str):
        """Processa um unico utilizador e actualiza o CSV."""
        if state_manager.is_user_jailed(username):
            jail_ttl = 0
            try:
                if state_manager and state_manager.r:
                    jail_ttl = int(state_manager.r.ttl(f"jail:{username}") or 0)
            except Exception:
                jail_ttl = 0
            ttl_msg = f" ({jail_ttl}s restantes)" if jail_ttl > 0 else ""
            logger.info(
                f"[Process-{process_id}] {username} em jail{ttl_msg} — "
                "removendo da queue ate expirar"
            )
            work_queue.drop_user(username)
            return

        # Marcar como processing no CSV (lock atomico)
        claimed = update_csv_status(
            username, 'processing', credentials_file_path,
            expected_old_status='false'
        )
        if not claimed:
            claimed = update_csv_status(
                username, 'processing', credentials_file_path,
                expected_old_status='pending'
            )
        if not claimed:
            logger.warning(
                f"[Process-{process_id}] Claim CSV falhou para {username} "
                "(esperado false/pending). A tentar recuperar de 'processing' preso..."
            )
            if update_csv_status(
                username, 'false', credentials_file_path,
                expected_old_status='processing',
            ):
                logger.info(f"[Process-{process_id}] CSV: {username} reposto a 'false' (recovery).")
            else:
                logger.info(
                    f"[Process-{process_id}] {username} nao sera re-enfileirado "
                    "automaticamente; o CSV define se volta ao fluxo."
                )
            work_queue.unmark_active(username)
            return


        logger.info(f"[Process-{process_id}] 🔄 Claimed: {username}")

        max_user_attempts = _cfg_int("max_user_attempts", 4)
        final_status = 'failed_retry_later'

        try:
            for attempt in range(max_user_attempts):
                try:
                    if attempt > 0:
                        wait = min(10 * (2 ** (attempt - 1)), 60) * random.uniform(0.8, 1.5)
                        await asyncio.sleep(wait)
                    else:
                        await asyncio.sleep(random.uniform(0.5, 2.0))

                    result = await main(username, password, proxy_chunk, process_id)

                    if result is True:
                        final_status = 'true'
                        logger.info(f"[Process-{process_id}] ✅ SUCCESS: {username}")
                        work_queue.mark_done(username)
                        break

                    final_status = 'false'
                    logger.warning(
                        f"[Process-{process_id}] ⚠️ Tentativa {attempt+1}/{max_user_attempts} "
                        f"falhou: {username}"
                    )

                except PostLoginFailure as ple:
                    if (
                        _post_login_failure_allows_full_retry(ple)
                        and attempt < max_user_attempts - 1
                    ):
                        logger.warning(
                            f"[Process-{process_id}] {username}: post-login failure "
                            "específica de sessão no Questionario — permitir "
                            f"mais 1 tentativa completa com novo proxy/login "
                            f"({str(ple)[:200]})"
                        )
                        final_status = 'false'
                        continue

                    # O login chegou a ser aceite pelo servidor mas um passo
                    # pós-login falhou (Questionário/Formulario/vistoForm/PDF).
                    # Repetir o ciclo completo gastaria outro CAPTCHA e faria outro
                    # POST /login com o mesmo utilizador em <1min — que é
                    # exactamente o padrão que dispara o WAF do MNE. Parquear o
                    # utilizador como failed_retry_later e deixar o jail soft
                    # (configurado em config1.toml) fazer o resto.
                    soft_pause = float(
                        (scraper_settings or {}).get(
                            "global_throttle_minutes_after_soft_captcha", 10
                        )
                    )
                    state_manager.send_to_jail(username, duration_minutes=soft_pause)
                    logger.error(
                        f"[Process-{process_id}] {username}: post-login failure — "
                        f"parar loop de tentativas (retry completo gastaria outro "
                        f"CAPTCHA e dispararia o WAF): {str(ple)[:200]}"
                    )
                    final_status = 'failed_retry_later'
                    break

                except LoginPostSubmittedFailure as lpsf:
                    # O POST /login já foi submetido mas morreu antes de termos
                    # resposta confiável. Não tentar novo login completo no mesmo
                    # run: isso só queima outro CAPTCHA e duplica requests sobre o
                    # mesmo utilizador.
                    soft_pause = float(
                        (scraper_settings or {}).get(
                            "global_throttle_minutes_after_soft_captcha", 10
                        )
                    )
                    state_manager.send_to_jail(username, duration_minutes=soft_pause)
                    logger.error(
                        f"[Process-{process_id}] {username}: POST /login já tinha sido "
                        f"submetido mas a tentativa falhou ({str(lpsf)[:180]}) — "
                        "parar loop e marcar failed_retry_later."
                    )
                    final_status = 'failed_retry_later'
                    break

                except CaptchaTokenExpired as cte:
                    # O solver foi demasiado lento e o token caducou antes de
                    # podermos submeter. NÃO chamar record_server_rejection: o
                    # proxy está inocente, o problema foi a SLA do 2captcha/
                    # anti-captcha. Pequena pausa (3 min) e marcar o utilizador
                    # em failed_retry_later sem penalizar o proxy.
                    logger.error(
                        f"[Process-{process_id}] {username}: CAPTCHA token expirado "
                        f"({str(cte)[:160]}) — solver demasiado lento. Proxy NÃO penalizado; "
                        "utilizador marcado em failed_retry_later."
                    )
                    state_manager.send_to_jail(username, duration_minutes=3.0)
                    final_status = 'failed_retry_later'
                    break

                except Exception as e:
                    logger.error(f"[Process-{process_id}] ❌ Excecao para {username}: {e}")
                    err = str(e)
                    err_l = err.lower()

                    if any(
                        x in err_l
                        for x in (
                            "recaptchaerror",
                            "http error 403",
                            "garantir a possibilidade",
                            "http 403",
                            "proxy/ip banned",
                        )
                    ) or _is_site_unavailable_error(err):
                        _jail_403 = float(
                            (scraper_settings or {}).get("global_throttle_minutes_on_403", 15)
                        )
                        _jail_rc = float(
                            (scraper_settings or {}).get(
                                "global_throttle_minutes_on_recaptcha_quota", 20
                            )
                        )
                        _jail_blk = float(
                            (scraper_settings or {}).get(
                                "global_throttle_minutes_on_blocked_site", 10
                            )
                        )

                        if "403" in err_l or "proxy/ip banned" in err_l:
                            _cp = None
                            if proxy_lease_manager:
                                try:
                                    _cp = proxy_lease_manager.current_proxy_of(username)
                                except Exception as _cp_err:
                                    logger.warning(
                                        f"[Process-{process_id}] Falha a ler proxy actual "
                                        f"de {username} após 403: {_cp_err}"
                                    )

                            if attempt < max_user_attempts - 1:
                                _next_proxy = None
                                if proxy_lease_manager and _cp:
                                    try:
                                        _next_proxy = proxy_lease_manager.rotate(
                                            username, _cp, proxy_chunk, reason="403"
                                        )
                                    except Exception as _rot403_err:
                                        logger.warning(
                                            f"[Process-{process_id}] Falha a rodar proxy "
                                            f"apos 403 para {username}: {_rot403_err}"
                                        )
                                        try:
                                            proxy_lease_manager.ban_proxy(_cp, reason="403")
                                            proxy_lease_manager.release(username)
                                        except Exception as _ban403_err:
                                            logger.warning(
                                                f"[Process-{process_id}] Falha a libertar/banir "
                                                f"proxy apos 403: {_ban403_err}"
                                            )

                                _curr_ip = _cp.split(':')[0] if _cp else "desconhecido"
                                if _next_proxy:
                                    logger.warning(
                                        f"[Process-{process_id}] {username}: 403 do proxy/IP "
                                        f"na tentativa {attempt+1}/{max_user_attempts}. "
                                        f"Proxy actual {_curr_ip} banido; proxima tentativa "
                                        f"vai sair com {_next_proxy.split(':')[0]}."
                                    )
                                else:
                                    logger.warning(
                                        f"[Process-{process_id}] {username}: 403 do proxy/IP "
                                        f"na tentativa {attempt+1}/{max_user_attempts}. "
                                        f"Proxy actual {_curr_ip} banido/libertado; sem "
                                        "proxy alternativo pre-reservado."
                                    )
                                final_status = 'false'
                                continue

                            if proxy_lease_manager and _cp:
                                try:
                                    proxy_lease_manager.ban_proxy(_cp, reason="403")
                                except Exception as _ban403_err:
                                    logger.warning(
                                        f"[Process-{process_id}] Falha a aplicar ban 403 "
                                        f"ao proxy de {username}: {_ban403_err}"
                                    )
                            state_manager.send_to_jail(username, duration_minutes=_jail_403)
                            final_status = 'banned_403'

                        elif _is_recaptcha_quota_exhausted_msg(err):
                            if proxy_lease_manager:
                                try:
                                    _cp = proxy_lease_manager.current_proxy_of(username)
                                    if _cp:
                                        proxy_lease_manager.ban_proxy(
                                            _cp, reason="recaptcha_server_quota"
                                        )
                                        logger.warning(
                                            f"[Process-{process_id}] {username}: "
                                            f"proxy {_cp.split(':')[0]} em cooldown "
                                            "por ReCaptchaError com 0 tentativas."
                                        )
                                except Exception as _rcq_err:
                                    logger.warning(
                                        f"[Process-{process_id}] Falha a aplicar cooldown "
                                        f"de proxy após recaptcha_quota: {_rcq_err}"
                                    )
                            state_manager.send_to_jail(username, duration_minutes=_jail_rc)
                            final_status = 'recaptcha_quota'

                        elif _is_soft_recaptcha_server_warning(err):
                            remaining = _extract_remaining_recaptcha_attempts(err)
                            soft_pause = float(
                                (scraper_settings or {}).get(
                                    "global_throttle_minutes_after_soft_captcha", 10
                                )
                            )
                            if proxy_lease_manager:
                                try:
                                    _cp = proxy_lease_manager.current_proxy_of(username)
                                    if _cp:
                                        proxy_lease_manager.ban_proxy(
                                            _cp, reason="recaptcha_server_soft"
                                        )
                                        logger.warning(
                                            f"[Process-{process_id}] {username}: "
                                            f"proxy {_cp.split(':')[0]} em cooldown "
                                            f"curto por ReCaptchaError soft "
                                            f"({remaining} tentativa(s) restante(s))."
                                        )
                                except Exception as _rcs_err:
                                    logger.warning(
                                        f"[Process-{process_id}] Falha a aplicar cooldown "
                                        f"de proxy após soft ReCaptchaError: {_rcs_err}"
                                    )
                            state_manager.send_to_jail(username, duration_minutes=soft_pause)
                            logger.warning(
                                f"[Process-{process_id}] {username} recebeu ReCaptchaError com "
                                f"{remaining} tentativa(s) restante(s) — pausando em failed_retry_later."
                            )
                            final_status = 'failed_retry_later'

                        else:
                            if _is_site_unavailable_error(err):
                                logger.warning(
                                    f"[Process-{process_id}] {username}: MNE indisponível/manutenção "
                                    "detectado — parar já e marcar blocked_site sem retries adicionais."
                                )
                            state_manager.send_to_jail(username, duration_minutes=_jail_blk)
                            final_status = 'blocked_site'

                        break

                    if _is_server_login_rejection(err):
                        logger.warning(
                            f"[Process-{process_id}] {username} rejeitado pelo servidor; "
                            "pausando em failed_retry_later ate ajuste manual."
                        )
                        # Cada vez que vemos esta mensagem genérica, o proxy
                        # actualmente arrendado ganha 1 ponto. Quando vários
                        # users seguidos são rejeitados pelo mesmo proxy, é
                        # quase sempre o MNE a silenciar esse IP — banimos
                        # localmente para parar de queimar CAPTCHA solves nele
                        # (ver browser_error_reports/*_login_rejected_server_*
                        # — o proxy 50.7.248.98 acumulou 20+ rejeições idênticas
                        # com 4 utilizadores diferentes em 24h).
                        if proxy_lease_manager:
                            try:
                                proxy_lease_manager.record_server_rejection(
                                    username, threshold=3
                                )
                            except Exception as _q_err:
                                logger.warning(
                                    f"[Process-{process_id}] Falha a registar "
                                    f"server-rejection no PLM: {_q_err}"
                                )
                        final_status = 'failed_retry_later'
                        break

                    final_status = 'false'

                if final_status == 'false' and attempt >= max_user_attempts - 1:
                    final_status = 'failed_retry_later'
                    logger.warning(
                        f"[Process-{process_id}] {username}: max_user_attempts esgotado; "
                        "marcando failed_retry_later para nao re-enfileirar no mesmo run."
                    )

                if attempt < max_user_attempts - 1:
                    await asyncio.sleep(5)
        except asyncio.CancelledError:
            logger.warning(
                f"[Process-{process_id}] {username}: task cancelada durante processamento — "
                "a limpar estado e marcar failed_retry_later para evitar 'processing' preso."
            )
            final_status = 'failed_retry_later'
            raise
        finally:
            update_csv_status(username, final_status, credentials_file_path)

        # Liberta o proxy exclusivo deste utilizador
        if proxy_lease_manager:
            proxy_lease_manager.release(username)
            logger.info(
                f"[Process-{process_id}] 🔓 Proxy libertado: {username} "
                f"(status={final_status})"
            )

            # Se o estado final exclui da queue, limpar qualquer entrada stale
            # que ainda exista em Redis. Sem isto, um username parado em
            # failed_retry_later pode reaparecer minutos depois via fila antiga.
            if final_status in CSV_STATUS_EXCLUDE_FROM_QUEUE:
                work_queue.drop_user(username)
            else:
                work_queue.repush_user(username)
                logger.info(f"[Process-{process_id}] 🔁 {username} devolvido a queue para retry")

    async def worker_async_loop():
        """
        Loop principal do worker.
        Pede continuamente users da queue e processa-os em paralelo
        ate ao limite max_concurrency.
        """
        logger.info(
            f"[Process-{process_id}] 🏃 Worker loop iniciado "
            f"(concurrency={max_concurrency})"
        )
        active_tasks: set = set()
        shutdown_requested = False
        last_csv_reload = 0.0
        CSV_RELOAD_INTERVAL = 30.0  # recarrega CSV a cada 30s

        while True:
            try:
                # ── Limpar tasks concluidas ───────────────────────────────────
                active_tasks = {t for t in active_tasks if not t.done()}

                # ── Reload do CSV para detetar novos users ────────────────────
                now = time.time()
                if now - last_csv_reload > CSV_RELOAD_INTERVAL:
                    try:
                        df_fresh = pd.read_csv(
                            credentials_file_path, encoding='utf-8'
                        )
                        if 'status' not in df_fresh.columns:
                            df_fresh['status'] = 'false'
                        df_fresh['status'] = (
                            df_fresh['status'].astype(str).str.strip().str.lower()
                        )
                        rows = df_fresh.to_dict('records')
                        # Resetar known para permitir re-adicionar users que voltaram a pending
                        work_queue.reset_for_reload()
                        new_count = work_queue.push_users(rows)
                        if new_count > 0:
                            logger.info(
                                f"[Process-{process_id}] 📥 {new_count} users novos/pendentes "
                                f"adicionados a queue"
                            )
                        last_csv_reload = now
                    except Exception as csv_err:
                        logger.warning(
                            f"[Process-{process_id}] Erro ao recarregar CSV: {csv_err}"
                        )

                # ── Se nao ha espaco para nova task, aguardar ─────────────────
                if len(active_tasks) >= max_concurrency:
                    await asyncio.sleep(0.5)
                    continue

                # ── Pedir proximo user da queue ───────────────────────────────
                username = work_queue.claim_next(timeout_s=check_interval)

                if username is None:
                    # Queue vazia — aguardar e tentar recarregar
                    logger.debug(
                        f"[Process-{process_id}] Queue vazia — aguardando {check_interval}s"
                    )
                    continue  # claim_next ja bloqueou check_interval segundos

                # ── Ler password do CSV ───────────────────────────────────────
                try:
                    df_cur = pd.read_csv(credentials_file_path, encoding='utf-8')
                    row = df_cur[df_cur['username'] == username]
                    if row.empty:
                        logger.warning(
                            f"[Process-{process_id}] {username} nao encontrado no CSV — ignorando"
                        )
                        continue
                    password = str(row.iloc[0]['password'])
                    status   = str(row.iloc[0].get('status', 'false')).strip().lower()

                    # Se a queue ainda contiver uma entrada stale mas o CSV já
                    # diz que este user não deve correr, descartá-la aqui.
                    # 'processing' é tratado à parte para não limpar
                    # acidentalmente o lock activo de outro worker vivo.
                    if status == 'processing':
                        logger.info(
                            f"[Process-{process_id}] {username} já está em "
                            "processing no CSV — ignorando claim stale."
                        )
                        continue
                    if status in CSV_STATUS_EXCLUDE_FROM_QUEUE:
                        logger.info(
                            f"[Process-{process_id}] {username} com status CSV "
                            f"'{status}' — removendo entrada stale da queue"
                        )
                        work_queue.drop_user(username)
                        continue

                except Exception as csv_err:
                    logger.error(
                        f"[Process-{process_id}] Erro ao ler CSV para {username}: {csv_err}"
                    )
                    work_queue.repush_user(username)
                    continue

                # ── Lancar task para este user ────────────────────────────────
                task = asyncio.create_task(
                    process_single_user(username, password),
                    name=f"user-{username}"
                )
                active_tasks.add(task)

                def _task_done(t: asyncio.Task, uname=username):
                    try:
                        active_tasks.discard(t)
                        if t.cancelled():
                            logger.info(
                                f"[Process-{process_id}] Task cancelada: {uname} "
                                f"({len(active_tasks)}/{max_concurrency} slots ocupados)"
                            )
                            return
                        exc = t.exception()
                        if exc is not None:
                            logger.error(
                                f"[Process-{process_id}] Task {uname} falhou: {exc}",
                                exc_info=exc,
                            )
                        else:
                            logger.info(
                                f"[Process-{process_id}] ✅ Task finalizada: {uname} "
                                f"({len(active_tasks)}/{max_concurrency} slots ocupados)"
                            )
                    except Exception as _cb_err:
                        logger.error(f"[Process-{process_id}] task callback: {_cb_err}")

                task.add_done_callback(_task_done)
                logger.info(
                    f"[Process-{process_id}] ▶️ Task iniciada: {username} "
                    f"({len(active_tasks)}/{max_concurrency} slots ocupados)"
                )
                await asyncio.sleep(0)

            except KeyboardInterrupt:
                    shutdown_requested = True
                    logger.info(
                        f"[Process-{process_id}] Interrompido — a cancelar "
                        f"{len(active_tasks)} task(s) activa(s) antes de sair."
                    )
                    for task in list(active_tasks):
                        task.cancel()
                    if active_tasks:
                        done, pending = await asyncio.wait(
                            active_tasks, timeout=5.0
                        )
                        if pending:
                            logger.warning(
                                f"[Process-{process_id}] {len(pending)} task(s) "
                                "ainda nao terminaram apos cancelamento; "
                                "worker vai encerrar sem aguardar mais."
                            )
                            active_tasks = set(pending)
                        else:
                            active_tasks.clear()
                    break
            except Exception as e:
                logger.error(f"[Process-{process_id}] Erro no loop: {e}")
                await asyncio.sleep(10)

        # Aguardar tasks activas terminarem antes de sair
        active_tasks = {t for t in active_tasks if not t.done()}
        if active_tasks and not shutdown_requested:
            logger.info(
                f"[Process-{process_id}] Aguardando {len(active_tasks)} tasks activas..."
            )
            await asyncio.gather(*active_tasks, return_exceptions=True)
        elif active_tasks:
            logger.info(
                f"[Process-{process_id}] Encerrando com {len(active_tasks)} task(s) "
                "ainda pendente(s) apos o cancelamento."
            )

    try:
        asyncio.run(worker_async_loop())
    except KeyboardInterrupt:
        logger.info(f"[Process-{process_id}] Sinal de paragem recebido — worker a encerrar.")


def fetch_webshare_proxy_list(settings: Dict, api_key: str) -> List[str]:
    """
    Fetch proxies from Webshare at startup and normalize them to the bot format:
    host:port:username:password
    """
    mode = str(settings.get("webshare_mode", "backbone") or "backbone").strip().lower()
    if mode not in ("backbone", "direct"):
        raise ValueError("webshare_mode deve ser 'backbone' ou 'direct'.")

    try:
        page_size = int(settings.get("webshare_page_size", 100) or 100)
    except (TypeError, ValueError):
        page_size = 100
    page_size = max(1, min(page_size, 100))

    try:
        max_proxies = int(settings.get("webshare_max_proxies", 0) or 0)
    except (TypeError, ValueError):
        max_proxies = 0

    plan_id = str(settings.get("webshare_plan_id", "") or "").strip()
    timeout = float(settings.get("webshare_api_timeout_sec", 20) or 20)
    country_codes = str(settings.get("webshare_country_codes", "") or "").strip()
    backbone_port = str(settings.get("webshare_backbone_port", "80") or "80").strip()
    if not backbone_port.isdigit():
        backbone_port = "80"
    excluded_country_codes = {
        code.strip().upper()
        for code in str(settings.get("webshare_excluded_country_codes", "") or "").split(",")
        if code.strip()
    }
    fetch_method = str(settings.get("webshare_fetch_method", "download") or "download").strip().lower()

    if fetch_method in ("download", "auto"):
        try:
            proxies = fetch_webshare_proxy_download_list(
                settings=settings,
                api_key=api_key,
                mode=mode,
                country_codes=country_codes,
                excluded_country_codes=excluded_country_codes,
                max_proxies=max_proxies,
                timeout=timeout,
            )
            if proxies:
                return proxies
        except Exception as e:
            if fetch_method == "download":
                raise
            logger.warning(f"[Webshare] Download endpoint falhou ({e}); tentando JSON list.")

    headers = {"Authorization": f"Token {api_key}"}
    params = {"mode": mode, "page": 1, "page_size": page_size}
    if plan_id:
        params["plan_id"] = plan_id
    if country_codes and country_codes not in ("-", "*", "all"):
        params["country_code__in"] = country_codes

    proxies: List[str] = []
    residential_backbone_fallbacks = 0
    base_url = "https://proxy.webshare.io/api/v2/proxy/list/"

    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        while True:
            response = client.get(base_url, headers=headers, params=params)
            response.raise_for_status()
            payload = response.json()
            results = payload.get("results") or []

            for item in results:
                if item.get("valid") is False:
                    continue
                item_country = str(item.get("country_code") or "").strip().upper()
                if item_country and item_country in excluded_country_codes:
                    continue
                host = str(item.get("proxy_address") or "").strip()
                port = str(item.get("port") or "").strip()
                username = str(item.get("username") or "").strip()
                password = str(item.get("password") or "").strip()
                if mode == "backbone":
                    host = "p.webshare.io"
                    port = backbone_port
                elif not host and username and password:
                    # Residential pool filters do not expose direct IPs in the API.
                    # Webshare documents these as Backbone-only via p.webshare.io.
                    host = "p.webshare.io"
                    port = backbone_port
                    residential_backbone_fallbacks += 1
                if host and port and username and password:
                    proxies.append(f"{host}:{port}:{username}:{password}")
                if max_proxies and len(proxies) >= max_proxies:
                    break

            if max_proxies and len(proxies) >= max_proxies:
                break
            if not payload.get("next"):
                break
            params["page"] = int(params["page"]) + 1

    if not proxies:
        raise ValueError("Webshare API retornou 0 proxies validos.")

    random.shuffle(proxies)
    country_counts: Dict[str, int] = {}
    for proxy_line in proxies:
        country = _webshare_country_from_proxy_line(proxy_line) or "??"
        country_counts[country] = country_counts.get(country, 0) + 1
    country_summary = ",".join(
        f"{country}:{count}"
        for country, count in sorted(country_counts.items())
    )
    logger.info(
        f"[Webshare] Loaded {len(proxies)} proxies via API "
        f"(mode={mode}, countries={country_codes or 'all'}, "
        f"excluded={','.join(sorted(excluded_country_codes)) or 'none'}, "
        f"loaded_countries={country_summary or 'unknown'})."
    )
    if residential_backbone_fallbacks:
        logger.warning(
            f"[Webshare] {residential_backbone_fallbacks} residential API item(s) "
            "sem proxy_address directo foram carregados via p.webshare.io "
            f"(backbone_port={backbone_port}). Direct mode nao fornece IP fixo "
            "para residential pool_filter."
        )
    return proxies


def fetch_webshare_proxy_download_list(
    settings: Dict,
    api_key: str,
    mode: str,
    country_codes: str,
    excluded_country_codes: set,
    max_proxies: int,
    timeout: float,
) -> List[str]:
    """
    Preferred Webshare loader. The download endpoint returns the same usable lines
    as the dashboard download: p.webshare.io:80:generated_username:password.
    """
    token = str(settings.get("webshare_download_token", "") or "").strip()
    plan_id = str(settings.get("webshare_plan_id", "") or "").strip()
    headers = {"Authorization": f"Token {api_key}"}

    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        if not token and plan_id:
            cfg_resp = client.get(
                "https://proxy.webshare.io/api/v3/proxy/config",
                headers=headers,
                params={"plan_id": plan_id},
            )
            cfg_resp.raise_for_status()
            token = str(cfg_resp.json().get("proxy_list_download_token") or "").strip()

        if not token:
            token_resp = client.post(
                "https://proxy.webshare.io/api/v2/download_token/proxy_list/",
                headers=headers,
            )
            token_resp.raise_for_status()
            token = str(token_resp.json().get("key") or "").strip()

        if not token:
            raise ValueError("Nao foi possivel obter webshare_download_token.")

        effective_country_codes = country_codes
        if (
            not effective_country_codes
            or effective_country_codes in ("-", "*", "all")
        ) and excluded_country_codes:
            available_country_codes = _fetch_webshare_available_country_codes(
                client=client,
                headers=headers,
                mode=mode,
                plan_id=plan_id,
            )
            allowed_country_codes = [
                code for code in available_country_codes
                if code not in excluded_country_codes
            ]
            if allowed_country_codes:
                effective_country_codes = ",".join(allowed_country_codes)

        country_path = "-"
        if effective_country_codes and effective_country_codes not in ("-", "*", "all"):
            country_path = "-".join(
                code.strip().upper()
                for code in effective_country_codes.split(",")
                if code.strip()
            ) or "-"

        download_url = (
            "https://proxy.webshare.io/api/v2/proxy/list/download/"
            f"{token}/{country_path}/any/username/{mode}/-/"
        )
        download_params = {"plan_id": plan_id} if plan_id else None
        download_resp = client.get(download_url, params=download_params)
        download_resp.raise_for_status()

    proxies: List[str] = []
    for raw_line in download_resp.text.splitlines():
        line = raw_line.strip()
        if not line or line.count(":") < 3:
            continue
        line_country = _webshare_country_from_proxy_line(line)
        if line_country and line_country in excluded_country_codes:
            continue
        proxies.append(line)
        if max_proxies and len(proxies) >= max_proxies:
            break

    if not proxies:
        raise ValueError("Webshare download retornou 0 proxies validos.")

    logger.info(
        f"[Webshare] Loaded {len(proxies)} proxies via download "
        f"(mode={mode}, countries={effective_country_codes or 'all'}, "
        f"excluded={','.join(sorted(excluded_country_codes)) or 'none'})."
    )
    return proxies


def _fetch_webshare_available_country_codes(
    client: httpx.Client,
    headers: Dict[str, str],
    mode: str,
    plan_id: str = "",
) -> List[str]:
    """Read available country codes so blacklist mode can still use download URLs."""
    params = {"mode": mode, "page": 1, "page_size": 100}
    if plan_id:
        params["plan_id"] = plan_id

    countries = set()
    while True:
        response = client.get(
            "https://proxy.webshare.io/api/v2/proxy/list/",
            headers=headers,
            params=params,
        )
        response.raise_for_status()
        payload = response.json()
        for item in payload.get("results") or []:
            code = str(item.get("country_code") or "").strip().upper()
            if code:
                countries.add(code)
        if not payload.get("next"):
            break
        params["page"] = int(params["page"]) + 1

    return sorted(countries)


def _webshare_country_from_proxy_line(proxy_line: str) -> Optional[str]:
    """Infer Webshare country code from generated username like base-gb-1."""
    try:
        parts = proxy_line.strip().split(":")
        if len(parts) < 4:
            return None
        username = parts[2].strip().lower()
        match = re.search(r"-([a-z]{2})(?:-\d+|-rotate)?$", username)
        return match.group(1).upper() if match else None
    except Exception:
        return None


def _soax_slug(value: str) -> str:
    """Normalize SOAX username parameters without touching already URL-safe text."""
    value = str(value or "").strip().lower()
    value = re.sub(r"\s+", "+", value)
    return re.sub(r"[^a-z0-9+_.%-]+", "", value)


def _verify_soax_geo_api(settings: Dict, package_key: str, country: str) -> None:
    """Best-effort SOAX API check for the selected country/connection type."""
    api_key = str(
        settings.get("soax_api_key")
        or os.environ.get("SOAX_API_KEY")
        or ""
    ).strip()
    if not api_key or not country:
        return

    conn_type = str(settings.get("soax_conn_type", "wifi") or "wifi").strip().lower()
    if conn_type not in ("wifi", "mobile"):
        conn_type = "wifi"

    try:
        response = httpx.get(
            "https://api.soax.com/api/get-country-regions",
            params={
                "api_key": api_key,
                "package_key": package_key,
                "country_iso": country,
                "conn_type": conn_type,
            },
            timeout=float(settings.get("soax_api_timeout_sec", 15) or 15),
        )
        response.raise_for_status()
        regions = response.json()
        region_count = len(regions) if isinstance(regions, list) else 0
        logger.info(
            f"[SOAX API] Geo OK: country={country}, conn_type={conn_type}, "
            f"regions={region_count}."
        )
    except Exception as exc:
        logger.warning(
            f"[SOAX API] Geo check failed for country={country}, conn_type={conn_type}: "
            f"{str(exc)[:160]}"
        )


def fetch_soax_proxy_list(settings: Dict) -> List[str]:
    """
    Build SOAX proxy entries in the bot's host:port:username:password format.

    SOAX access is through proxy.soax.com:5000 with targeting encoded in the
    username, so there is no downloadable proxy list like Webshare.
    """
    host = str(settings.get("soax_host", "proxy.soax.com") or "proxy.soax.com").strip()
    port = str(settings.get("soax_port", "5000") or "5000").strip()
    exact_username = str(settings.get("soax_username", "") or "").strip()
    package_id = str(settings.get("soax_package_id", "") or "").strip()
    password = str(
        settings.get("soax_password")
        or settings.get("soax_package_key")
        or os.environ.get("SOAX_PASSWORD")
        or os.environ.get("SOAX_PACKAGE_KEY")
        or ""
    ).strip()
    if not host or not port or not password or (not exact_username and not package_id):
        raise ValueError(
            "proxy_source=soax requer soax_username ou soax_package_id, alem de "
            "soax_password, soax_host e soax_port."
        )

    base_username = exact_username or f"package-{package_id}"
    country = _soax_slug(settings.get("soax_country_iso", ""))
    region = _soax_slug(settings.get("soax_region", ""))
    city = _soax_slug(settings.get("soax_city", ""))
    isp = _soax_slug(settings.get("soax_isp", ""))
    _verify_soax_geo_api(settings, password, country)
    if exact_username:
        sticky = "sessionid-" in exact_username
        session_length_match = re.search(r"-sessionlength-(\d+)", exact_username)
        session_length = int(session_length_match.group(1)) if session_length_match else 0
        proxies = [f"{host}:{port}:{exact_username}:{password}"]
        logger.info(
            f"[SOAX] Loaded 1 exact proxy session "
            f"(host={host}:{port}, package={package_id or 'from_username'}, "
            f"sticky={sticky}, length={session_length or 'default'}s)."
        )
        return proxies

    if country:
        base_username += f"-country-{country}"
    if region:
        base_username += f"-region-{region}"
    if city:
        base_username += f"-city-{city}"
    if isp:
        base_username += f"-isp-{isp}"

    try:
        count = int(settings.get("soax_session_count", 1) or 1)
    except (TypeError, ValueError):
        count = 1
    count = max(1, min(count, 500))

    try:
        session_length = int(settings.get("soax_session_length_sec", 300) or 300)
    except (TypeError, ValueError):
        session_length = 300
    session_length = max(10, min(session_length, 3600))

    sticky = _coerce_bool(settings.get("soax_sticky_sessions", True), True)
    session_prefix = _soax_slug(settings.get("soax_session_prefix", "visa"))
    if not session_prefix:
        session_prefix = "visa"

    proxies: List[str] = []
    for idx in range(1, count + 1):
        username = base_username
        if sticky:
            username += f"-sessionid-{session_prefix}{idx}-sessionlength-{session_length}"
        proxies.append(f"{host}:{port}:{username}:{password}")

    logger.info(
        f"[SOAX] Loaded {len(proxies)} proxy session(s) "
        f"(host={host}:{port}, package={package_id}, "
        f"country={country or 'random'}, sticky={sticky}, length={session_length}s)."
    )
    return proxies


def precheck_mne_reachable_proxies(proxy_list: List[str], settings: Dict) -> List[str]:
    """
    Probe a bounded proxy sample against MNE before claiming users.

    If Webshare returns valid proxies but MNE serves the same 503 maintenance page
    for every sampled exit, continuing would only burn time and user attempts.
    """
    if not proxy_list or proxy_list == [DIRECT_PROXY_MARKER]:
        return proxy_list
    if not _coerce_bool(settings.get("mne_proxy_precheck_enabled", True), True):
        return proxy_list

    try:
        max_checks = int(settings.get("mne_proxy_precheck_max", 12) or 12)
    except (TypeError, ValueError):
        max_checks = 12
    max_checks = max(1, min(max_checks, len(proxy_list)))

    try:
        timeout = float(settings.get("mne_proxy_precheck_timeout_sec", 12) or 12)
    except (TypeError, ValueError):
        timeout = 12.0
    timeout = max(3.0, min(timeout, 30.0))

    candidates = list(proxy_list)
    random.shuffle(candidates)
    sampled = candidates[:max_checks]
    reachable: List[str] = []
    blocked: List[str] = []

    logger.info(
        f"[MNE Precheck] Testing {len(sampled)}/{len(proxy_list)} proxy exits "
        "against /VistosOnline before claiming users."
    )
    for proxy_raw in sampled:
        proxy_url = _proxy_to_http_url(proxy_raw)
        if not proxy_url:
            continue
        label = _proxy_safe_label(proxy_raw)
        exit_ip = "unknown"
        try:
            try:
                ip_resp = curl_requests.get(
                    "https://api.ipify.org?format=json",
                    proxies={"http": proxy_url, "https": proxy_url},
                    impersonate="chrome120",
                    timeout=timeout,
                    allow_redirects=True,
                )
                if ip_resp.status_code == 200:
                    exit_ip = str((ip_resp.json() or {}).get("ip") or "unknown")
            except Exception:
                pass

            resp = curl_requests.get(
                f"{BASE_URL}/VistosOnline/",
                proxies={"http": proxy_url, "https": proxy_url},
                impersonate="chrome124",
                timeout=timeout,
                allow_redirects=True,
            )
            text = str(resp.text or "")
            if resp.status_code < 500 and not _is_mne_service_unavailable_text(text):
                reachable.append(proxy_raw)
                logger.info(
                    f"[MNE Precheck] ✅ {label} exit_ip={exit_ip} "
                    f"status={resp.status_code}"
                )
            else:
                blocked.append(f"{label}@{exit_ip}:{resp.status_code}")
                logger.warning(
                    f"[MNE Precheck] ❌ {label} exit_ip={exit_ip} "
                    f"status={resp.status_code} (maintenance/blocked)"
                )
        except Exception as exc:
            if _is_proxy_provider_quota_error(str(exc)):
                raise ValueError(
                    "[MNE Precheck] Proxy provider devolveu 402/quota antes de chegar ao MNE. "
                    "A bandwidth/allowance do Webshare parece esgotada ou o plano ainda nao permite tunnel. "
                    f"Primeiro proxy afectado: {label}@{exit_ip}. Reponha bandwidth e tente novamente."
                ) from exc
            blocked.append(f"{label}@{exit_ip}:ERR")
            logger.warning(
                f"[MNE Precheck] ❌ {label} exit_ip={exit_ip} erro={str(exc)[:140]}"
            )

    if reachable:
        logger.info(
            f"[MNE Precheck] {len(reachable)} proxy(s) reached MNE; "
            "using only those for this run."
        )
        return reachable

    raise ValueError(
        "[MNE Precheck] Nenhum proxy testado conseguiu abrir /VistosOnline sem 503. "
        f"Amostra bloqueada/indisponivel: {', '.join(blocked[:8])}. "
        "Troque/substitua a pool Webshare por exits que MNE aceite antes de rodar users."
    )


def validate_files_and_config(working_dir: str, scraper_settings: Dict) -> tuple:
    """Validate all required files exist and load data."""
    import pandas as pd

    use_px = scraper_settings.get("use_proxy", True)
    if isinstance(use_px, str):
        use_px = str(use_px).strip().lower() in ("1", "true", "yes", "on")

    if not use_px:
        _allow_direct = scraper_settings.get("allow_direct_traffic", False)
        if isinstance(_allow_direct, str):
            _allow_direct = str(_allow_direct).strip().lower() in ("1", "true", "yes", "on")
        if not _allow_direct:
            raise ValueError(
                "use_proxy=false está desactivado por segurança. O tráfego directo expõe o seu IP "
                "e repetidas tentativas de login levam a bloqueios (WAF / ReCaptcha). "
                "Use use_proxy=true com proxies válidos, ou defina allow_direct_traffic=true no TOML "
                "apenas para um teste pontual consciente."
            )
        proxy_list = [DIRECT_PROXY_MARKER]
        logger.warning(
            "use_proxy=false — tráfego DIRECTO (allow_direct_traffic=true). Risco elevado para o IP."
        )
    else:
        proxy_list = []
        proxy_source = str(scraper_settings.get("proxy_source", "file") or "file").strip().lower()
        webshare_key = str(
            scraper_settings.get("webshare_api_key")
            or os.environ.get("WEBSHARE_API_KEY")
            or ""
        ).strip()
        use_webshare = bool(webshare_key) and proxy_source in ("webshare_api", "webshare", "auto")

        if proxy_source in ("soax", "soax_api"):
            proxy_list = fetch_soax_proxy_list(scraper_settings)
        elif use_webshare and webshare_key:
            try:
                proxy_list = fetch_webshare_proxy_list(scraper_settings, webshare_key)
            except Exception as e:
                fallback_enabled = _coerce_bool(
                    scraper_settings.get("webshare_api_fallback_to_file", True),
                    True,
                )
                if not fallback_enabled or proxy_source in ("webshare_api", "webshare"):
                    raise ValueError(f"Erro critico ao carregar proxies da Webshare API: {e}")
                logger.warning(
                    f"[Webshare] Falha ao carregar API ({e}); usando proxy_file_path como fallback."
                )
        elif proxy_source in ("webshare_api", "webshare"):
            raise ValueError(
                "proxy_source=webshare_api mas webshare_api_key esta vazio. "
                "Preencha webshare_api_key no config1.toml ou defina WEBSHARE_API_KEY."
            )

        if not proxy_list:
            proxies_file = os.path.join(working_dir, scraper_settings["proxy_file_path"])
            if not os.path.exists(proxies_file):
                raise FileNotFoundError(
                    f"Proxy file {scraper_settings['proxy_file_path']} not found."
                )

            try:
                with open(proxies_file, "r", encoding="utf-8", errors="ignore") as f:
                    lines_pf = f.readlines()
                for line in lines_pf:
                    clean_line = line.strip()
                    if clean_line and clean_line.count(":") >= 3:
                        proxy_list.append(clean_line)
            except Exception as e:
                raise ValueError(f"Erro critico ao ler arquivo de proxies: {e}")

        if not proxy_list:
            raise ValueError(
                "Nenhum proxy válido no ficheiro — adicione linhas ip:port:user:pass a "
                f"{scraper_settings['proxy_file_path']} ou restaure uma cópia de segurança. "
                "Tráfego directo (use_proxy=false) martela o seu IP residencial: evite."
            )

        proxy_list = [p for p in proxy_list if p]
        proxy_list = precheck_mne_reachable_proxies(proxy_list, scraper_settings)
        logger.info(f"LOADED {len(proxy_list)} VALID PROXIES.")


    credentials_file = os.path.join(working_dir, scraper_settings['creds_file_path'])
    if not os.path.exists(credentials_file):
        raise FileNotFoundError(f"Credentials file {scraper_settings['creds_file_path']} not found.")
    try:
        df = pd.read_csv(credentials_file, encoding='utf-8')
        initial_count = len(df)
        df = df.drop_duplicates(subset=['username'], keep='last')
        if len(df) < initial_count:
            logger.warning(f"⚠️ Removidos {initial_count - len(df)} usuarios duplicados do CSV.")
            df.to_csv(credentials_file, index=False, encoding='utf-8')
    except Exception as e:
        raise ValueError(f"Error reading credentials file: {e}")

    required_columns = ['username', 'password']
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}")

    if 'status' not in df.columns:
        df['status'] = 'False'
    df['status'] = df['status'].astype(str).str.strip().str.lower()

    return proxy_list, df, credentials_file


def main_execution_continuous():
    """
    Ponto de entrada principal.

    1. Carrega config, proxies e CSV
    2. Cria a Work Queue Redis e empurra todos os users pendentes
    3. Lanca N workers (processos) — cada um pede users da queue dinamicamente
    4. Monitoriza processos e reinicia se crasharem
    """
    global logger, scraper_settings
    logger = setup_logging()

    try:
        multiprocessing.freeze_support()
        logger.info(f"Iniciando Scraper com Dynamic Work Queue em: {WORKING_DIR}")

        # ── Carregar configuracoes ────────────────────────────────────────────
        setting_file_path = os.path.join(WORKING_DIR, 'config1.toml')
        if not os.path.exists(setting_file_path):
            raise FileNotFoundError("Arquivo config1.toml nao encontrado")
        with open(setting_file_path, 'rb') as f:
            scraper_settings = tomllib.load(f)
        logger = setup_logging(settings=scraper_settings)
        logger.info(f"Iniciando Scraper com Dynamic Work Queue em: {WORKING_DIR}")
        _cleanup_orphaned_bot_processes(scraper_settings)
        _cleanup_orphaned_playwright_browsers(scraper_settings)

        # ── Carregar proxies e CSV ────────────────────────────────────────────
        proxy_list, df, credentials_file = validate_files_and_config(
            WORKING_DIR, scraper_settings
        )
        total_users = len(df)
        logger.info(f"📋 {total_users} utilizadores carregados do CSV.")

        # Recuperar linhas presas em 'processing' de runs anteriores que
        # crasharam ou foram interrompidas (Ctrl+C). Sem isto o bot termina
        # logo no arranque seguinte porque queue_elegiveis=0 — foi
        # exactamente o sintoma observado em 06:39:04 do log.
        try:
            _reclaim_stale_processing_rows(df, credentials_file)
        except Exception as _rec_err:
            logger.warning(
                f"[Recovery] falha ao reclamar linhas 'processing' presas: {_rec_err}"
            )

        status_counts, pending_users = _csv_status_summary(df)
        _known_statuses = (
            "false", "pending", "<empty>", "processing",
            "failed_retry_later", "blocked_site", "banned_403",
            "recaptcha_quota", "success", "true",
        )
        summary_parts = [
            f"queue_elegiveis={pending_users}",
            f"false={status_counts.get('false', 0)}",
            f"pending={status_counts.get('pending', 0)}",
            f"empty={status_counts.get('<empty>', 0)}",
            f"failed_retry_later={status_counts.get('failed_retry_later', 0)}",
            f"processing={status_counts.get('processing', 0)}",
            f"banned_403={status_counts.get('banned_403', 0)}",
            f"recaptcha_quota={status_counts.get('recaptcha_quota', 0)}",
            f"blocked_site={status_counts.get('blocked_site', 0)}",
            f"success={status_counts.get('success', 0)}",
            f"true={status_counts.get('true', 0)}",
        ]
        other_statuses = {
            key: value for key, value in status_counts.items()
            if key not in _known_statuses
        }
        if other_statuses:
            extra = ", ".join(f"{k}={v}" for k, v in sorted(other_statuses.items()))
            summary_parts.append(f"other=[{extra}]")
        logger.info(f"📊 CSV status summary: {' | '.join(summary_parts)}")

        if pending_users == 0:
            logger.warning(
                "Nenhum utilizador elegivel para a queue. "
                "O bot vai terminar sem iniciar workers."
            )
            logger.warning(
                "Todos os registos no CSV estao concluidos, em pausa, "
                "ou bloqueados. Para voltar a testar, mude manualmente "
                "pelo menos um status para 'false' ou 'pending'."
            )
            return 0

        # ── Inicializar Work Queue e carregar users pendentes ─────────────────
        _r_init = None
        try:
            _r_init = redis.Redis(
                host=os.getenv('REDIS_HOST', 'localhost'),
                port=int(os.getenv('REDIS_PORT', 6379)),
                decode_responses=True
            )
            _r_init.ping()
        except Exception as _re:
            logger.warning(f"Redis nao disponivel ({_re}) — usando queue in-memory")
            _r_init = None

        wq_init = WorkQueue(redis_client=_r_init)
        _redis_available = _r_init is not None

        # Limpar queue anterior (evitar duplicados de execucoes anteriores)
        if _r_init:
            try:
                _r_init.delete(_WQ_PENDING)
                _r_init.delete(_WQ_KNOWN)
                _r_init.delete(_WQ_ACTIVE)
                logger.info("🗑️ Queue Redis limpa (inicio limpo).")
            except Exception:
                pass

        rows = df.to_dict('records')
        pushed = wq_init.push_users(rows)
        logger.info(f"📥 {pushed} users adicionados a Work Queue. {wq_init.stats()}")
        jailed_skipped = 0
        if _r_init:
            try:
                for row in rows:
                    _u = str(row.get("username", "")).strip()
                    _st = str(row.get("status", "")).strip().lower()
                    if not _u or _st in CSV_STATUS_EXCLUDE_FROM_QUEUE:
                        continue
                    try:
                        if int(_r_init.ttl(f"jail:{_u}") or 0) > 0:
                            jailed_skipped += 1
                    except Exception:
                        pass
            except Exception:
                jailed_skipped = 0
        if pushed == 0 and jailed_skipped > 0:
            logger.warning(
                f"⚠️ Nenhum user entrou na Work Queue porque {jailed_skipped} "
                "utilizador(es) elegível/eis continuam em jail Redis. O bot "
                "vai ficar idle até o jail expirar ou ser limpo."
            )

        # ── Definir numero de workers ─────────────────────────────────────────
        # Usar o minimo entre: cpu_count, users pendentes, max configurado
        max_workers_cfg = int(scraper_settings.get('max_workers', 8))
        if not _redis_available:
            if max_workers_cfg > 1:
                logger.warning(
                    "Redis indisponivel: com multiprocessing (spawn) a fila in-memory "
                    "nao e partilhada entre processos. Forçando 1 worker; instale e "
                    "inicie redis-server para varios workers em paralelo."
                )
            max_workers_cfg = 1
        max_workers = min(
            max_workers_cfg,
            multiprocessing.cpu_count(),
            max(1, pending_users),  # nao criar mais workers do que users
        )
        logger.info(
            f"⚙️ Workers: {max_workers} "
            f"(cpu={multiprocessing.cpu_count()}, "
            f"users_pendentes={pending_users}, "
            f"max_cfg={max_workers_cfg})"
        )

        # Um único proxy (ou __DIRECT__): _chunkify com N>1 deixa workers com chunk [].
        proxy_list_for_workers = proxy_list
        if len(proxy_list) == 1 and max_workers > 1:
            proxy_list_for_workers = [proxy_list[0]] * max_workers
            logger.info(
                f"[Proxies] Entrada única replicada para {max_workers} workers "
                "(evita chunks de proxy vazios)."
            )

        # ── Dividir proxies uniformemente entre workers ───────────────────────
        def _chunkify(lst, n):
            if n <= 0 or not lst:
                return [lst] if lst else [[]]
            k, m = divmod(len(lst), n)
            chunks, start = [], 0
            for i in range(n):
                end = start + k + (1 if i < m else 0)
                chunks.append(lst[start:end])
                start = end
            return chunks

        proxy_chunks = _chunkify(proxy_list_for_workers, max_workers)
        logger.info(
            f"🔌 Proxy chunks: {[len(c) for c in proxy_chunks]} "
            f"({len(proxy_list_for_workers)} alocados para chunking, "
            f"{len(proxy_list)} na config)"
        )

        _queue_check = int(scraper_settings.get("queue_check_interval", 3))

        # ── Lancar workers (Ctrl+C: shutdown wait=False) ─────────────────────
        executor = ProcessPoolExecutor(max_workers=max_workers)
        shutdown_interrupted = False
        try:
            future_to_id = {
                executor.submit(
                    worker,
                    pc,           # proxy_chunk (SEM user_chunk!)
                    i,            # process_id
                    credentials_file,
                    scraper_settings,
                    _queue_check,  # check_interval (segundos de BLPOP timeout)
                    max_workers,
                ): i
                for i, pc in enumerate(proxy_chunks)
            }
            logger.info(
                f"[OK] {max_workers} workers iniciados em modo Dynamic Work Queue."
            )

            while True:
                try:
                    time.sleep(30)

                    if _r_init:
                        pending_q = _r_init.llen(_WQ_PENDING)
                        logger.info(
                            f"[Monitor] Queue: {pending_q} users pendentes | "
                            f"Workers: {sum(1 for f in future_to_id if not f.done())} activos"
                        )

                    for fut, pid in list(future_to_id.items()):
                        if fut.done():
                            exc = fut.exception()
                            if exc:
                                logger.error(
                                    f"[Monitor] Worker {pid} crashou: {exc} — reiniciando"
                                )
                                pc = proxy_chunks[pid] if pid < len(proxy_chunks) else proxy_chunks[0]
                                new_fut = executor.submit(
                                    worker, pc, pid,
                                    credentials_file, scraper_settings,
                                    _queue_check, max_workers
                                )
                                future_to_id[new_fut] = pid
                                del future_to_id[fut]

                except KeyboardInterrupt:
                    shutdown_interrupted = True
                    logger.info(
                        "Interrompido — encerrando pool e a terminar workers activos."
                    )
                    break
        finally:
            try:
                terminated, killed = _force_stop_process_pool(executor)
                if terminated or killed:
                    logger.info(
                        f"[Shutdown] Workers terminados={terminated}, "
                        f"kill_forcado={killed}"
                    )
            except Exception as shutdown_err:
                logger.warning(f"[Shutdown] Falha ao terminar workers: {shutdown_err}")
            if shutdown_interrupted and _r_init:
                try:
                    interrupted_users = sorted(_r_init.smembers(_WQ_ACTIVE))
                except Exception as active_err:
                    interrupted_users = []
                    logger.warning(
                        f"[Shutdown] Falha ao ler users activos para cleanup: {active_err}"
                    )
                if interrupted_users:
                    logger.info(
                        f"[Shutdown] A limpar estado interrompido de "
                        f"{len(interrupted_users)} user(s): {', '.join(interrupted_users)}"
                    )
                    for interrupted_user in interrupted_users:
                        _cleanup_interrupted_user_state(
                            interrupted_user,
                            credentials_file,
                            redis_client=_r_init,
                            reset_status="false",
                        )
            elif shutdown_interrupted:
                try:
                    import pandas as pd
                    df_cleanup = pd.read_csv(credentials_file, encoding="utf-8")
                    reclaimed = _reclaim_stale_processing_rows(df_cleanup, credentials_file)
                    if reclaimed:
                        logger.info(
                            f"[Shutdown] Recuperadas {reclaimed} linha(s) processing "
                            "apos interrupcao sem Redis."
                        )
                except Exception as csv_cleanup_err:
                    logger.warning(
                        f"[Shutdown] Falha a limpar CSV apos interrupcao sem Redis: "
                        f"{csv_cleanup_err}"
                    )
            try:
                executor.shutdown(wait=False, cancel_futures=True)
            except TypeError:
                executor.shutdown(wait=False)
            try:
                cleaned = _cleanup_orphaned_playwright_browsers(scraper_settings)
                if cleaned:
                    logger.info(
                        f"[Shutdown] Playwright browsers orfaos removidos={cleaned}."
                    )
            except Exception as browser_cleanup_err:
                logger.warning(
                    f"[Shutdown] Falha a limpar browsers Playwright: {browser_cleanup_err}"
                )
            try:
                cleaned_bots = _cleanup_orphaned_bot_processes(scraper_settings)
                if cleaned_bots:
                    logger.info(
                        f"[Shutdown] Bot workers orfaos removidos={cleaned_bots}."
                    )
            except Exception as bot_cleanup_err:
                logger.warning(
                    f"[Shutdown] Falha a limpar workers Python orfaos: {bot_cleanup_err}"
                )
    except Exception as e:
        logger.critical(f"🚨 Excecao critica: {e}", exc_info=True)
        return 1
    return 0


if __name__ == "__main__":
    # BUG C5 FIX: set_start_method DEVE ser a primeira instrucao do __main__
    # ANTES de qualquer objeto multiprocessing ser criado.
    # force=True garante que funciona mesmo em imports parciais do modulo.
    import multiprocessing as _mp_bootstrap
    _mp_bootstrap.set_start_method('spawn', force=True)
    _install_graceful_signal_handlers()
    
    # Executar a funcao principal
    try:
        main_execution_continuous()
    except KeyboardInterrupt:
        pass
