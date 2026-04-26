from collections import defaultdict
import httpx
import math  # <--- Adicione esta linha
import csv  # <--- Adicione esta linha
import time
import logging
import random
import os
from lxml import etree
import asyncio
import re
from datetime import date, timedelta, datetime
import json
import string
import sys
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
            parts = proxy_raw.strip().split(":")
            if len(parts) < 4:
                return
            ip, port, user, pwd = parts[0], parts[1], parts[2], parts[3]
            proxy_url = f"http://{user}:{pwd}@{ip}:{port}"
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

            safe_print(
                f"[TLSClient] ✅ Preflight OK — status={resp.status_code} "
                f"ja3={self.impersonate} cookies={list(self._cookies.keys())}"
            )
            return {
                "status":  resp.status_code,
                "ja3":     self.impersonate,
                "cookies": self._cookies,
                "headers": self._resp_headers,
            }
        except Exception as e:
            safe_print(f"[TLSClient] ⚠️ Preflight falhou (nao critico): {e}")
            return {"status": 0, "ja3": self.impersonate, "cookies": {}, "headers": {}}

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

        context = await browser.new_context(
            viewport=vp,
            user_agent=self.user_agent,
            extra_http_headers=merged_headers,
            locale=locale,
            timezone_id=timezone_id,
        )

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

PDF_SUCCESS_SENTINEL = "PDF_SUCCESS"

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

    # --- GLOBAL THROTTLE ---
    def check_global_throttle(self) -> bool:
        if not self.r: return False
        return self.r.exists("global_throttle")

    def trigger_global_throttle(self, duration_minutes: float = 5):
        if not self.r: return
        # Redis exige int — converter float para int (arredondar para cima)
        ex_seconds = max(1, int(duration_minutes * 60))
        self.r.set("global_throttle", "1", ex=ex_seconds)
        safe_print(f"[Throttle] 🛑 Pausa global por {duration_minutes} min ({ex_seconds}s).")

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
    _BAN_REPEAT_S   = [60, 300, 900]  # 1m, 5m, 15m para falhas de ligação (menos agressivo)

    # Chaves Redis
    _K_LEASE        = "plm:lease:{}"      # valor = username
    _K_USER         = "plm:user:{}"       # valor = proxy_raw
    _K_BAN          = "plm:ban:{}"        # valor = "1"
    _K_FAILS        = "plm:fails:{}"      # valor = contador
    _K_USES         = "plm:uses:{}"       # valor = total usos historicos
    _K_SCORE        = "plm:score:{}"      # valor = score de qualidade

    def __init__(self, redis_client=None):
        self._r    = redis_client
        self._lock = threading.Lock()
        # Fallback in-memory (por processo)
        self._leases:     Dict[str, str] = {}  # proxy -> username
        self._user_proxy: Dict[str, str] = {}  # username -> proxy
        self._banned_mem: Dict[str, float] = {}  # proxy -> ban_until timestamp

    # ─────────────────────────────────────────────────────────────────────────
    # INTERFACE PUBLICA
    # ─────────────────────────────────────────────────────────────────────────

    def acquire(self, username: str, proxy_list: list) -> Optional[str]:
        """
        Adquire proxy EXCLUSIVO para este utilizador.
        Retorna o proxy_raw ou None se nenhum estiver livre.
        Thread-safe e process-safe via Redis NX.
        """
        if self._r:
            try:
                return self._acquire_redis(username, proxy_list)
            except Exception as e:
                safe_print(f"[PLM] Redis acquire erro: {e} — usando memory")
        return self._acquire_memory(username, proxy_list)

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
        403/cloudflare = 30 min. Falhas repetidas = progressivo.
        """
        if reason in ("403", "cloudflare", "banned"):
            ttl = self._BAN_403_S
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
            safe_print(
                f"[PLM] 🚫 BAN(mem) {proxy_raw.split(':')[0]} "
                f"por {ttl//60}min (motivo={reason})"
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
        if not available:
            # Fallback: usar lista COMPLETA excepto o proxy mau
            # (os bans podem ter expirado, ou o PLM pode adquirir e verificar de novo)
            available = [p for p in proxy_list if p != bad_proxy]
            if available:
                safe_print(
                    f"[PLM] ⚠️ Todos os {len(proxy_list)} proxies banidos — "
                    f"tentando {len(available)} sem filtro ban"
                )
            else:
                safe_print(f"[PLM] ⚠️ Sem proxies alternativos para {username}")
                return None
        new_proxy = self.acquire(username, available)
        # Log com ip:port para nao enganar quando hostname e o mesmo
        _bad_id  = ":".join(bad_proxy.split(":")[:2]) if bad_proxy else "?"
        _new_id  = ":".join(new_proxy.split(":")[:2]) if new_proxy else "NENHUM"
        safe_print(
            f"[PLM] ROTATE {username}: "
            f"{_bad_id} -> {_new_id} "
            f"(motivo={reason})"
        )
        return new_proxy

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
                return f"[PLM] {leases} proxies em uso | {bans} banidos (Redis)"
            except Exception:
                pass
        with self._lock:
            bans = sum(1 for t in self._banned_mem.values() if time.time() < t)
            return (f"[PLM] {len(self._leases)} em uso | "
                    f"{bans} banidos (memory)")

    # ─────────────────────────────────────────────────────────────────────────
    # IMPLEMENTACAO REDIS
    # ─────────────────────────────────────────────────────────────────────────

    def _acquire_redis(self, username: str, proxy_list: list) -> Optional[str]:
        # 1. Verificar se ja tem proxy arrendado e ainda valido
        user_key = self._K_USER.format(username)
        existing = self._r.get(user_key)
        if existing and existing in proxy_list:
            lease_key = self._K_LEASE.format(existing)
            if self._r.get(lease_key) == username and not self.is_banned(existing):
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
            if banned:
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

    def _acquire_memory(self, username: str, proxy_list: list) -> Optional[str]:
        with self._lock:
            # Verificar arrendamento existente
            existing = self._user_proxy.get(username)
            if (existing and existing in proxy_list
                    and self._leases.get(existing) == username
                    and not self._is_banned_mem(existing)):
                return existing

            # Construir candidatos
            candidates = []
            for p in proxy_list:
                if self._is_banned_mem(p):
                    continue
                owner = self._leases.get(p)
                if owner and owner != username:
                    continue
                candidates.append(p)

            if not candidates:
                return None

            chosen = candidates[0]  # primeiro = menos usos (lista ja ordenada)
            self._leases[chosen]       = username
            self._user_proxy[username] = chosen
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
    Mapeia proxy_raw -> {cookies, user_agent, last_used, health}.
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
        parts = proxy_raw.split(":")
        if len(parts) < 4: return False
        
        ip, port, user, pwd = parts[0], parts[1], parts[2], parts[3]
        proxy_url = f"http://{user}:{pwd}@{ip}:{port}"
        
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
    Envia mensagem para o Telegram lendo credenciais do config1.toml.
    """
    # Tenta carregar as configurações do Telegram do arquivo global
    try:
        # scraper_settings é carregado globalmente no início do script/processo
        telegram_cfg = scraper_settings.get('telegram', {})
        BOT_TOKEN = telegram_cfg.get('bot_token')
        CHAT_ID = telegram_cfg.get('chat_id')
    except Exception as e:
        # Fallback caso scraper_settings não esteja disponível (raro)
        try:
            logger.warning(f"[Telegram] Configurações não carregadas: {e}")
        except NameError:
            print(f"[Telegram] Configurações não carregadas: {e}")
        return

    # Verifica se as chaves existem antes de tentar enviar
    if not BOT_TOKEN or not CHAT_ID:
        try:
            logger.warning("[Telegram] ⚠️ Bot Token ou Chat ID não encontrados no config1.toml. Pulando alerta.")
        except NameError:
            print("[Telegram] ⚠️ Bot Token ou Chat ID não encontrados no config1.toml.")
        return

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        async with httpx.AsyncClient() as client:
            payload = {
                "chat_id": CHAT_ID,
                "text": message,
                "parse_mode": "HTML"
            }
            await client.post(url, data=payload, timeout=10.0)
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
        logger.warning(f"Não foi possível checar saldo: {e}")
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
            await asyncio.sleep(random.uniform(0.001, 0.005))

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
                await asyncio.sleep(random.uniform(0.1, 0.3))
            
            await self.page.mouse.down()
            await asyncio.sleep(random.uniform(0.05, 0.15))
            await self.page.mouse.up()
            
            await asyncio.sleep(random.uniform(0.2, 0.5))
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
            await asyncio.sleep(random.uniform(0.1, 0.2))
            await self.page.keyboard.down("Control")
            await self.page.keyboard.press("A")
            await self.page.keyboard.up("Control")
            await asyncio.sleep(random.uniform(0.05, 0.1))
            await self.page.keyboard.press("Backspace")
            await asyncio.sleep(random.uniform(0.1, 0.2))

            # 3. MELHORIA: Usar insert_text nativo do Playwright
            # Isso evita erros de permissão do clipboard e é mais rápido
            await self.page.keyboard.insert_text(text)
            
            # 4. Small post-fill delay
            await asyncio.sleep(random.uniform(0.1, 0.3))
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
                await asyncio.sleep(random.uniform(0.1, 0.2))
                await self.page.keyboard.down("Control")
                await self.page.keyboard.press("A")
                await self.page.keyboard.up("Control")
                await self.page.keyboard.press("Backspace")

            for char in str(text):
                delay = random.uniform(0.01, 0.08)
                if random.random() < 0.05: # Occasional thinking pause
                    delay += random.uniform(0.3, 0.5)
                
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
            await asyncio.sleep(random.uniform(0.2, 0.4))

            # Use Playwright's select option but ensure events trigger
            await self.page.select_option(selector, value)
            
            # Trigger change event explicitly for legacy JS frameworks
            await self.page.dispatchEvent(selector, "change")
            await asyncio.sleep(random.uniform(0.2, 0.4))
            return True
            
        except Exception as e:
            logger.warning(f"[HumanSim] Select failed: {e}")
            return False

scraper_settings = None

def safe_print(*args, **kwargs):
    """Print function that handles Unicode encoding errors on Windows console."""
    try:
        print(*args, **kwargs)
    except UnicodeEncodeError:
        safe_args = [str(arg).encode('ascii', 'replace').decode('ascii') if isinstance(arg, str) else arg for arg in args]
        print(*safe_args, **kwargs)

def setup_logging(process_id: int = 0):
    """Setup logging for each process with Process ID prefix"""
    handler = colorlog.StreamHandler()
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
    logger.setLevel(logging.INFO)
    logger.handlers = []
    logger.addHandler(handler)
    
    # Adiciona o process_id ao logger para ser usado no formato
    logger = colorlog.getLogger()
    logger.setLevel(logging.INFO)
    logger.handlers = []
    logger.addHandler(handler)
    
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
    return logger

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
        parts = proxy_raw.strip().split(":")
        if len(parts) < 4: return "Europe/Lisbon"
        
        ip, port, user, pwd = parts[0], parts[1], parts[2], parts[3]
        proxy_url = f"http://{user}:{pwd}@{ip}:{port}"
        
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
            parts = proxy_raw.strip().split(":")
            if len(parts) < 4: continue
                
            ip, port, user, pwd = parts[0], parts[1], parts[2], parts[3]
            proxy_url = f"http://{user}:{pwd}@{ip}:{port}"
            
            # TESTE AGRESSIVO: 5 Segundos total para carregar a página inicial
            # Isso simula a paciência de um usuário real e a velocidade de um sniper bot
            start_time = time.time()
            
            response = curl_requests.get(
                "https://pedidodevistos.mne.gov.pt/VistosOnline/", 
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

    if not proxy_lease_manager:
        raise RuntimeError("[Session] CRITICO: proxy_lease_manager nao inicializado.")

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

    logger.info(f"[Session] 🔒 Proxy exclusivo adquirido: {username} -> {proxy_raw.split(':')[0]}")

    # ── PASSO 2: Testar conectividade — ate 3 proxies diferentes se necessario ─
    # Se o proxy adquirido nao responder, rodar para um novo (ban + novo acquire)
    MAX_PROXY_ROTATIONS = 3
    transport = None

    for _rot in range(MAX_PROXY_ROTATIONS):
        parts = proxy_raw.strip().split(":")
        if len(parts) < 4:
            logger.error(f"[Session] Formato invalido: {proxy_raw}")
            proxy_raw = proxy_lease_manager.rotate(
                username, proxy_raw, proxy_list, reason="invalid_format"
            )
            if not proxy_raw:
                break
            continue

        ip, port, puser, ppwd = parts[0], parts[1], parts[2], parts[3]
        proxy_url = f"http://{puser}:{ppwd}@{ip}:{port}"

        try:
            start_t = time.time()
            resp = curl_requests.get(
                "https://pedidodevistos.mne.gov.pt/VistosOnline/",
                proxies={"http": proxy_url, "https": proxy_url},
                impersonate="chrome120",
                timeout=8.0,
                allow_redirects=True,
            )
            latency_ms = int((time.time() - start_t) * 1000)

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
                logger.warning(f"[Session] HTTP {resp.status_code} em {ip} — rotacionando...")
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
                f"[Session] ✅ Proxy OK: {ip} | "
                f"lat={latency_ms}ms | user={username}"
            )
            break

        except Exception as e:
            err_str = str(e).lower()
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
            f"[Session] {username}: nenhum dos {MAX_PROXY_ROTATIONS} proxies tentados respondeu. "
            f"Verifique qualidade dos proxies."
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
def solve_recaptcha_v2(proxy_raw: str, user_agent: str, captcha_key_index: int = 0, page_url: str = None, page_action: str = None) -> str:
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

    # BUG C4 FIX: scraper_settings pode ser None se chamado cedo
    if scraper_settings is None:
        raise RuntimeError('[CAPTCHA] scraper_settings ainda nao carregado — aguardar inicio do worker.')
    SITE_KEY = scraper_settings.get('SITE_KEY', '6LdOB9crAAAAADT4RFruc5sPmzLKIgvJVfL830d4')
    PAGE_URL = page_url or 'https://pedidodevistos.mne.gov.pt/VistosOnline/Authentication.jsp'

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
    if proxy_raw:
        try:
            _parts = proxy_raw.strip().split(":")
            if len(_parts) >= 4:
                _ip, _port, _puser, _ppwd = _parts[0], _parts[1], _parts[2], _parts[3]
                _proxy_task_data = {
                    "proxyType": "http",
                    "proxyAddress": _ip,
                    "proxyPort": int(_port),
                    "proxyLogin": _puser,
                    "proxyPassword": _ppwd,
                }
                logger.info(f"[Captcha] 🔗 Proxy IP Match ativo: {_ip}:{_port}")
        except Exception as _pe:
            logger.warning(f"[Captcha] Nao foi possivel preparar proxy para CAPTCHA: {_pe}")
    # =======================================================================

    def _solve_single(provider: str, api_key: str, task_type: str,
                      create_url: str, result_url: str) -> str | None:
        """Resolve CAPTCHA num unico provider e regista estatisticas.
        Usa o mesmo proxy do browser (Proxy IP Match) para evitar detecao por IP diferente.
        """
        t_start = _time.time()
        try:
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
                payload = {"clientKey": api_key, "task": task_data}

            # Criar task (sem proxy no httpx — o proxy e passado DENTRO do payload)
            with httpx.Client(timeout=20, trust_env=False) as client:
                resp = client.post(create_url, json=payload)
                resp.raise_for_status()
                task_resp = resp.json()

            task_id = task_resp.get("taskId")
            if not task_id:
                _captcha_record(provider, False, _time.time() - t_start)
                return None

            # Polling ate 90s
            for _ in range(30):
                _time.sleep(3)
                try:
                    with httpx.Client(timeout=15, trust_env=False) as client:
                        result = client.post(result_url, json={
                            "clientKey": api_key, "taskId": task_id
                        }).json()
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
            logger.debug(f"[Captcha] {provider} erro: {e}")
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
            "task_type": "RecaptchaV2EnterpriseTask",
            "create_url": "https://api.2captcha.com/createTask",
            "result_url": "https://api.2captcha.com/getTaskResult",
        })

    # 3.1 — Reordenar pela performance histórica: o melhor provider vai primeiro
    # Após dados suficientes, o router escolhe o mais rápido com rate >= 80%.
    best_p1 = captcha_router.get_best_service([p["provider"] for p in phase1_providers])
    if best_p1:
        phase1_providers.sort(key=lambda p: 0 if p["provider"] == best_p1 else 1)
        logger.info(f"[Captcha] 🎯 CAPTCHARouter: provider preferido = {best_p1}")

    if phase1_providers:
        n = len(phase1_providers)
        logger.info(f"[Captcha] Step 1/2: Dual-service ({', '.join(p['provider'] for p in phase1_providers)}) em paralelo...")
        with concurrent.futures.ThreadPoolExecutor(max_workers=n) as executor:
            futures = {
                executor.submit(
                    _solve_single,
                    p["provider"], p["api_key"], p["task_type"],
                    p["create_url"], p["result_url"]
                ): p["provider"]
                for p in phase1_providers
            }
            winner_token = None
            winner_provider = None
            for future in concurrent.futures.as_completed(futures):
                provider_name = futures[future]
                try:
                    token = future.result()
                    if token and not winner_token:
                        winner_token = token
                        winner_provider = provider_name
                        logger.info(f"[Captcha] ✅ Solved: {provider_name} (WINNER dual-service)")
                        _captcha_record(provider_name, True, 0, winner=True)
                except Exception:
                    pass

        if winner_token:
            # Log estatísticas a cada 10 solves (stats legacy + router)
            total_wins = sum(s["wins"] for s in captcha_stats.values())
            if total_wins % 10 == 0:
                logger.info(captcha_stats_report())
                logger.info(captcha_router.report())
            return winner_token

    # ─── FASE 2: BACKUP — CapMonster ────────────────────────────────────────────
    if capmon_key:
        logger.info("[Captcha] Step 2/2: CapMonster (backup)...")
        token = _solve_single(
            "capmonster", capmon_key,
            "RecaptchaV2EnterpriseTaskProxyless",
            "https://api.capmonster.cloud/createTask",
            "https://api.capmonster.cloud/getTaskResult",
        )
        if token:
            logger.info("[Captcha] ✅ Solved: CapMonster")
            _captcha_record("capmonster", True, 0, winner=True)
            return token

    # ─── FASE 3: ÚLTIMO RECURSO — CapSolver ─────────────────────────────────────
    if capsolver_key:
        logger.info("[Captcha] Step 3/3: CapSolver (último recurso)...")
        token = _solve_single(
            "capsolver", capsolver_key,
            "ReCaptchaV2EnterpriseTaskProxyless",
            "https://api.capsolver.com/createTask",
            "https://api.capsolver.com/getTaskResult",
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
    # Aguardar vistoForm com timeout maior e retry — o formulário pode demorar a carregar
    visto_loaded = False
    for _attempt in range(3):
        try:
            await page.wait_for_selector("#vistoForm", timeout=30000)
            visto_loaded = True
            break
        except Exception:
            logger.warning(f"[Playwright] #vistoForm não visível (tentativa {_attempt+1}/3) — aguardar 3s...")
            await page.wait_for_timeout(3000)
            # Verificar se a página navegou para outro sítio
            current_url = page.url
            if "sessionLost" in current_url or "Authentication" in current_url:
                raise RuntimeError(f"Sessão perdida ao aguardar vistoForm. URL: {current_url}")
    if not visto_loaded:
        raise RuntimeError("[Playwright] #vistoForm não apareceu após 3 tentativas (90s total)")
    
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
                    for key, cfg in mapping_data.items():
                        if isinstance(cfg, list) and len(cfg) >= 2 and cfg[0] == 'f31':
                            cfg[1] = departure_date_str
                            logger.info(f"[Playwright] Calculated and overriding f31 (intended_date_of_departure) with: {departure_date_str}")
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

    logger.info(f"[Playwright] Will fill {len(field_values)} second-form fields across 6 tabs (only empty/required fields)...")
    
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
                    
                    // Check if field is readonly or disabled (but still allow filling disabled selects if they're empty)
                    if (el.readOnly) return true;
                    if (el.disabled && el.tagName !== 'SELECT') return true; // Allow disabled selects to be filled if empty
                    
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
                        await page.wait_for_timeout(random.randint(500, 1000))
                        return True
                    else:
                        logger.warning(f"[Playwright] No valid options found in '{field_name}', skipping...")
                        return False
            else:
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
                logger.info(f"[Playwright] Filled '{field_name}'")

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
        for field_name, field_value in field_values.items():
            success = await fill_field_human_like(field_name, field_value)
            if success:
                tab_filled += 1
                total_filled += 1

        logger.info(f"[Playwright] ✅ Tab {tab_num} ({tab_name}): {tab_filled} fields filled")

        if tab_num < 6:
            await page.wait_for_timeout(random.randint(400, 800))

    logger.info(f"[Playwright] Total: {total_filled} fields filled across all tabs")

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
    
    logger.info("[Playwright] Clicking #btnSubmit - this will trigger confirm dialogs that will be auto-accepted...")
    
    try:
        await btn_submit_locator.click(delay=random.randint(100, 250))
        logger.info("[Playwright] Submit button clicked - waiting for confirm dialogs to appear...")
    except Exception as click_err:
        logger.warning(f"[Playwright] Button click error: {click_err}")
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
        await page.wait_for_timeout(2000)
        try:
            await page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass  # page may still be loading; continue to detect CAPTCHA anyway

        schedule_url = page.url
        logger.info(f"[Playwright] URL após vistoForm submit: {schedule_url}")
        
        # Aguardar widget CAPTCHA do Schedule antes de detectar
        if 'Schedule' in schedule_url or 'posto_id' in schedule_url:
            try:
                await page.wait_for_selector('iframe[src*="recaptcha"], #captchaDiv, .g-recaptcha', timeout=15000, state="attached")
                await page.wait_for_timeout(1500)
                logger.info("[Playwright] ✅ Schedule CAPTCHA widget detectado")
            except Exception as _sw:
                logger.warning(f"[Playwright] Schedule widget não apareceu: {_sw}")
                await page.wait_for_timeout(3000)

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

        logger.info(f"[Playwright] CAPTCHA type: {captcha_type}, sitekey: {site_key}")
        
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
            
            if captcha_type in ['recaptcha_v2', 'recaptcha_v2_enterprise']:
                _sch_url = page.url if page.url and 'Schedule' in page.url else f"https://pedidodevistos.mne.gov.pt/VistosOnline/Schedule.jsp?posto_id={consular_post_id}"
                captcha_token = solve_recaptcha_v2(proxy_raw, user_agent, captcha_key_index=captcha_key_index, page_url=_sch_url)
            elif captcha_type == 'recaptcha_v3':
                logger.warning("[Playwright] reCAPTCHA v3 detected - this may require different solving approach")
                captcha_token = solve_recaptcha_v2(proxy_raw, user_agent, captcha_key_index=captcha_key_index)
            elif captcha_type == 'hcaptcha':
                logger.error("[Playwright] hCaptcha detected - hCaptcha solving not yet implemented!")
                raise RuntimeError("hCaptcha solving is not yet implemented. Please solve manually.")
            else:
                logger.warning(f"[Playwright] Unknown CAPTCHA type: {captcha_type}, trying reCAPTCHA v2 solver...")
                captcha_token = solve_recaptcha_v2(proxy_raw, user_agent, captcha_key_index=captcha_key_index)
            
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
                    _retry_token = solve_recaptcha_v2(proxy_raw, user_agent, captcha_key_index=captcha_key_index, page_url=_sch_url_r)
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

                        _sch_token = solve_recaptcha_v2(proxy_raw, user_agent, captcha_key_index=captcha_key_index)
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
                            (dateStr) => {
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
                                        ajaxFunctionPeriodos(dateStr);
                                    }
                                    
                                    return true;
                                }
                                return false;
                            }
                        """, date_formatted)
                        
                        logger.info(f"[Playwright] ✅ Date field set: {date_formatted}")

                        logger.info("[Playwright] Waiting for period dropdown to be populated...")
                        await page.wait_for_timeout(1500)
                        
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
                        
                        await page.wait_for_timeout(500)
                        
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
    await asyncio.sleep(random.uniform(0.5, 1.5))
    
    ip, port, proxy_user, proxy_pwd = proxy_raw.split(":")
    proxy_config = {
        "server": f"http://{ip}:{port}",
        "username": proxy_user,
        "password": proxy_pwd,
    }

    language = scraper_settings.get('language', 'PT') if scraper_settings else 'PT'
    login_url = f"{BASE_URL}/VistosOnline/Authentication.jsp?language={language}"

    is_mobile = "Mobile" in user_agent or "Android" in user_agent
    if "Windows" in user_agent:
        platform = "Windows"
    elif "Macintosh" in user_agent:
        platform = "macOS"
    elif "Android" in user_agent or "Linux" in user_agent:
        platform = "Linux" if not is_mobile else "Android"
    else:
        platform = "Windows"

    # Headers do contexto do Playwright - Devem casar com o Chrome real (pt-PT locale)
    extra_headers = {
        "Accept-Language": "pt-BR,pt;q=0.9",
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

    if browser_context_pool is not None:
        existing = await browser_context_pool.get(proxy_raw)
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
                logger.info(
                    f"[BrowserPool] ✅ Reutilizando contexto existente para "
                    f"{proxy_raw.split(':')[0]} (browser nao foi recriado)"
                )
            except Exception as _reuse_err:
                logger.warning(f"[BrowserPool] Contexto existente invalido: {_reuse_err} — criando novo")
                await browser_context_pool.invalidate(proxy_raw)
                _reusing_context = False
                browser = context = page = None

    if not _reusing_context:
        # Fluxo normal: criar playwright + browser + context
        playwright = await async_playwright().start()
        browser    = None
    
    try:
        headless_cfg = True
        try:
            if scraper_settings is not None:
                headless_cfg = bool(scraper_settings.get('headless_mode', True))
        except Exception as e:
            logger.warning(f"[Playwright] Could not read headless_mode from config, defaulting to True: {e}")

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

        # ── 3.6: só cria browser/context/page se NAO estamos a reutilizar ──────
        if not _reusing_context:
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
            # GET com JA3 Chrome120 real via curl_cffi:
            #   1. Resolve o desafio PoW inicial do servidor
            #   2. Obtém cookies de sessao (_USER_CONSENT, cookiesession1, Vistos_sid)
            #   3. Aquece a ligacao do proxy com TLS fingerprint limpo
            # Os cookies sao depois injetados via stealth_context()
            _tls_client = TLSClient(user_agent=user_agent, proxy_raw=proxy_raw)
            tls_result  = await _tls_client.preflight_tls(f"{BASE_URL}/VistosOnline/")
            logger.info(
                f"[TLSClient] Preflight: status={tls_result['status']} "
                f"cookies={list(tls_result['cookies'].keys())}"
            )

            # ── stealth_context: substitui new_context manual ────────────────────
            # Cria contexto com UA consistente, cookies do preflight injetados
            # e init script anti-detecao (webdriver, chrome runtime, CDP cleanup)
            proxy_timezone = get_timezone_from_proxy(proxy_raw)
            context, page = await _tls_client.stealth_context(
                browser,
                extra_http_headers=extra_headers,
                viewport_size=viewport_size,
                locale="pt-BR",
                timezone_id=proxy_timezone,
                proxy_config=proxy_config,
            )
            logger.info("[TLSClient] ✅ stealth_context criado com cookies do preflight injetados")
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

            # Guardar no pool para reutilização futura (3.6)
            if browser_context_pool is not None:
                await browser_context_pool.store(proxy_raw, browser, context, page, user_agent)
                logger.info(f"[BrowserPool] Contexto guardado no pool para {proxy_raw.split(':')[0]}")
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
            url = request.url
            failure = request.failure or 'unknown'
            if '/VistosOnline/login' in url and request.method == 'POST':
                logger.error(f"[Playwright] ❌ Login POST FAILED at network level: {failure} — account may be blocked or proxy issue")
                if not login_response_future.done():
                    login_response_future.set_exception(RuntimeError(f"Login POST network failure: {failure}"))
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
        
        # -------------------------------------------------------
        # 🚨 REMOVA OU COMENTE ESTE BLOCO ABAIXO PARA EVITAR CONFLITO 🚨          
        # -------------------------------------------------------
        logger.info(f"[Playwright] Visiting main page to establish session cookies...")
        try:
            main_page_response = await page.goto(main_page_url, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(500)
            logger.info(f"[Playwright] Main page loaded (status: {main_page_response.status if main_page_response else 'N/A'})")
        except Exception as main_page_error:
            logger.warning(f"[Playwright] Main page visit failed (non-critical): {main_page_error}")

        # Aceitar cookie consent popup se visível
        try:
            cookie_btn = page.locator('#allowAllCookiesBtn')
            if await cookie_btn.is_visible(timeout=3000):
                await cookie_btn.click()
                logger.debug("[Playwright] Accepted cookie consent popup")
                await page.wait_for_timeout(500)
        except Exception:
            pass

        # Aguardar que o desafio PoW (/ch/v) seja resolvido e os cookies estejam presentes
        # O servidor define _USER_CONSENT (path /) após o PoW — sem ele o login falha
        logger.info("[Playwright] Aguardando cookies de sessão completos (_USER_CONSENT PoW)...")
        for _cw in range(30):  # até 15 segundos
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
            if _cw % 5 == 0:
                logger.info(f"[Playwright] Aguardando cookies... ({_cw/2:.0f}s) — session={has_session}, consent_pow={has_consent}")
            await page.wait_for_timeout(500)
        else:
            all_cookies = await context.cookies()
            logger.warning(f"[Playwright] ⚠️ Timeout aguardando cookies. Presentes: {[c['name'] for c in all_cookies]}")
            # Continuar mesmo sem o cookie PoW — o Chrome real deve ter passado o desafio
            # O cookie pode ter path diferente ou o servidor pode aceitar assim mesmo
            logger.info("[Playwright] A continuar para login sem cookie PoW — Chrome real deve ter passado o desafio")

        logger.info(f"[Playwright] Navigating to login page: {login_url}")
        nav_start_time = time_module.time()
        
        max_nav_retries = 3
        nav_success = False
        last_error = None
        response = None
        
        for nav_attempt in range(max_nav_retries):
            try:
                logger.info(f"[Playwright] Navegando para login (Tentativa {nav_attempt + 1}/{max_nav_retries}) - MODO TURBO...")

                # TENTA CARREGAR A PÁGINA (Muito mais rápido que networkidle)
                response = await page.goto(login_url, wait_until="domcontentloaded", timeout=60000)

                # ESPERA INTELIGENTE: Aguarda o campo de usuário aparecer (máx 5s)
                try:
                    await page.wait_for_selector('input[name="username"]', timeout=5000)
                    nav_success = True
                    logger.info("[Playwright] ✅ Página de login pronta!")
                    break # SUCESSO - Sai do loop imediatamente
                except Exception:
                    # Se o campo não apareceu, verifica se caímos na página certa mas está lento
                    current_url_check = page.url
                    if "Authentication.jsp" in current_url_check:
                        logger.info("[Playwright] Página correta, mas lenta. Esperando mais um pouco...")
                        await page.wait_for_selector('input[name="username"]', timeout=10000)
                        nav_success = True
                        break
                    raise RuntimeError("Campo de login não encontrado.")

            except Exception as nav_error:
                last_error = nav_error
                error_str = str(nav_error).lower()

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
                    await browser.close()
                    await playwright.stop()
                    raise RuntimeError(f"Navegação falhou após {max_nav_retries} tentativas: {last_error}")
               
        if not nav_success:
            await browser.close()
            await playwright.stop()
            raise RuntimeError(f"Navigation failed: {last_error}")
        
        if response is None:
            response = type('Response', (), {'status': 200})()
            logger.info("[Playwright] Navigation succeeded but response was None, created mock response")
        
        if response is not None and response.status not in (200, 302):
            await browser.close()
            await playwright.stop()
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
        captcha_future = None
        captcha_start_time = None
        
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

        # Lançar CAPTCHA solver em background ANTES de iniciar o gather
        loop = asyncio.get_running_loop()
        captcha_start_time = time_module.time()
        if quick_widget_check:
            logger.info("[Pipeline] ✅ CAPTCHA detectado — lançando solver + form fill em paralelo...")
        else:
            logger.info("[Pipeline] CAPTCHA widget não detectado ainda — lançando pipeline mesmo assim...")

        captcha_future = loop.run_in_executor(
            None,
            functools.partial(solve_recaptcha_v2, proxy_raw, user_agent,
                              captcha_key_index=captcha_key_index),
        )

        # Wrapper async para o future do executor (compatível com gather)
        async def _wait_captcha_future():
            return await captcha_future

        # ── gather: form fill e CAPTCHA solver correm em simultâneo ──────────
        pipeline_start = time_module.time()
        fill_result, _ = await asyncio.gather(
            _fill_login_form(),
            _wait_captcha_future(),
            return_exceptions=True,
        )
        pipeline_elapsed = time_module.time() - pipeline_start
        logger.info(f"[Pipeline] ✅ Pipeline concluída em {pipeline_elapsed:.2f}s "
                    f"(fill={'OK' if not isinstance(fill_result, Exception) else fill_result})")

        fill_time = fill_result if isinstance(fill_result, float) else 0.0
        fill_start_time = time_module.time() - fill_time  # compatibilidade com código abaixo
        logger.info(f"[Playwright] Form filling took {fill_time:.2f}s")

        logger.info("[Playwright] Waiting for page to settle after form interaction...")
        try:
            await page.wait_for_load_state('domcontentloaded', timeout=3000)
        except Exception:
            pass
        
        logger.info("[Playwright] Waiting for reCAPTCHA widget...")
        widget_ready = False
        widget_id = 0
        max_widget_wait_attempts = 5

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
                timeout=45000,
            )
            widget_ready = True
            logger.info("[Playwright] ✅ reCAPTCHA widget ready")
            if captcha_future is None:
                loop = asyncio.get_running_loop()
                captcha_start_time = time_module.time()
                captcha_future = loop.run_in_executor(
                    None,
                    functools.partial(solve_recaptcha_v2, proxy_raw, user_agent, captcha_key_index=captcha_key_index),
                )
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
                
                if widget_info.get('found') and captcha_future is None:
                    logger.info("[Playwright] ✅ CAPTCHA widget detected during wait! Starting background CAPTCHA solving now...")
                    loop = asyncio.get_running_loop()
                    captcha_start_time = time_module.time()
                    captcha_future = loop.run_in_executor(
                        None,
                        functools.partial(solve_recaptcha_v2, proxy_raw, user_agent, captcha_key_index=captcha_key_index),
                    )
                
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
                        if captcha_future is None and (widget_info.get('iframe_found') or widget_info.get('details', {}).get('recaptchaDivs', 0) > 0):
                            logger.info("[Playwright] CAPTCHA widget elements detected, starting background solving...")
                            loop = asyncio.get_running_loop()
                            captcha_start_time = time_module.time()
                            captcha_future = loop.run_in_executor(
                                None,
                                functools.partial(solve_recaptcha_v2, proxy_raw, user_agent, captcha_key_index=captcha_key_index),
                            )

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
            loop = asyncio.get_running_loop()
            captcha_start_time = time_module.time()
            captcha_future = loop.run_in_executor(
                None,
                functools.partial(solve_recaptcha_v2, proxy_raw, user_agent, captcha_key_index=captcha_key_index),
            )
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
        
        logger.info(f"[Playwright] Waiting for CAPTCHA solving to complete...")
        try:
            captcha = await captcha_future
        except Exception as e:
            await browser.close()
            raise RuntimeError(f"CAPTCHA solving failed: {e}")
        
        if captcha_start_time is None:
            captcha_start_time = time_module.time()
            logger.warning("[Playwright] CAPTCHA start time not tracked, using current time for duration calculation")
        captcha_solve_duration = time_module.time() - captcha_start_time
        captcha_received_time = time_module.time()
        
        if not captcha or len(captcha) < 50:
            await browser.close()
            raise RuntimeError("Invalid CAPTCHA token received from solver")
        
        valid_chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_'
        invalid_chars = [c for c in captcha[:100] if c not in valid_chars]
        if invalid_chars:
            logger.warning(f"[Playwright] ⚠️ Token contains invalid characters: {set(invalid_chars)}")
        if len(captcha) < 100:
            logger.error(f"[Playwright] ❌ Token too short ({len(captcha)} chars)")
        elif len(captcha) > 5000:
            logger.warning(f"[Playwright] ⚠️ Token unusually long ({len(captcha)} chars)")
        logger.info(f"[Playwright] CAPTCHA token received ({len(captcha)} chars)")
        
        if captcha_solve_duration < 15:
            additional_delay = random.randint(100, 250)
            logger.info(f"[Playwright] CAPTCHA solved quickly ({captcha_solve_duration:.1f}s), adding tiny delay: {additional_delay}ms")
            await page.wait_for_timeout(additional_delay)
        
        captcha_solve_time = time_module.time() - login_start_time
        logger.info(f"[Playwright] ✅ CAPTCHA solved in {captcha_solve_time:.1f}s — injecting token...")

        inject_start_time = time_module.time()
        
        logger.info("[Playwright] Verifying grecaptcha is available before token injection...")
        
        grecaptcha_available = False
        for retry in range(5):
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
                if retry < 4:
                    logger.info(f"[Playwright] grecaptcha not found yet, waiting... (retry {retry + 1}/5)")
                    await page.wait_for_timeout(1000)
        
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
            await browser.close()
            raise RuntimeError(f"Failed to inject CAPTCHA token: {injection_result.get('error', 'Unknown error')}")

        inject_time = time_module.time() - inject_start_time
        logger.info(f"[Playwright] CAPTCHA token injected (length: {injection_result.get('tokenLength', 0)}) (injection took {inject_time:.2f}s)")
        
        token_verification = await page.evaluate("""
            () => {
                const results = {
                    via_getResponse: null,
                    via_enterprise_getResponse: null,
                    via_textarea: null,
                    all_valid: false
                };
                
                try {
                    if (window.grecaptcha && window.grecaptcha.getResponse) {
                        results.via_getResponse = window.grecaptcha.getResponse(0);
                    }
                } catch (e) {
                    results.via_getResponse = 'error: ' + e.message;
                }
                
                try {
                    if (window.grecaptcha && window.grecaptcha.enterprise && window.grecaptcha.enterprise.getResponse) {
                        results.via_enterprise_getResponse = window.grecaptcha.enterprise.getResponse();
                    }
                } catch (e) {
                    results.via_enterprise_getResponse = 'error: ' + e.message;
                }
                
                try {
                    const textarea = document.querySelector('textarea[name="g-recaptcha-response"]');
                    if (textarea) {
                        results.via_textarea = textarea.value;
                    }
                } catch (e) {
                    results.via_textarea = 'error: ' + e.message;
                }
                
                // Check if all methods return valid tokens (length > 100)
                results.all_valid = (
                    results.via_getResponse && results.via_getResponse.length > 100 &&
                    results.via_enterprise_getResponse && results.via_enterprise_getResponse.length > 100 &&
                    results.via_textarea && results.via_textarea.length > 100
                );
                
                return results;
            }
        """)
        
        if not token_verification.get("all_valid"):
            logger.warning(f"[Playwright] ⚠️ Token verification incomplete:")
            logger.warning(f"  - getResponse(0): {len(token_verification.get('via_getResponse', '')) if isinstance(token_verification.get('via_getResponse'), str) else 'N/A'} chars")
            logger.warning(f"  - enterprise.getResponse(): {len(token_verification.get('via_enterprise_getResponse', '')) if isinstance(token_verification.get('via_enterprise_getResponse'), str) else 'N/A'} chars")
            logger.warning(f"  - textarea: {len(token_verification.get('via_textarea', '')) if isinstance(token_verification.get('via_textarea'), str) else 'N/A'} chars")
        else:
            logger.info(f"[Playwright] ✅ Token verified via all methods (getResponse, enterprise.getResponse, textarea)")
        
        await page.wait_for_timeout(random.randint(300, 600))
        
        checkbox_updated = False
        try:
            await page.wait_for_timeout(100)
            
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
                            
                            // Update border element if it exists
                            const border = el.querySelector('.recaptcha-checkbox-border');
                            if (border) {
                                border.classList.remove('recaptcha-checkbox-border');
                                border.classList.add('recaptcha-checkbox-border-checked');
                            }
                            
                            // Trigger state change event
                            const event = new Event('recaptcha-state-change', { bubbles: true });
                            el.dispatchEvent(event);
                        }
                    """)
                    checkbox_updated = True
                    logger.info("[Playwright] ✓ Updated reCAPTCHA checkbox in iframe")
                except Exception as iframe_error:
                    logger.info(f"[Playwright] Could not update iframe checkbox: {iframe_error}")
            else:
                logger.info("[Playwright] Could not find reCAPTCHA iframe in page frames")
        except Exception as frame_error:
            logger.info(f"[Playwright] Error accessing iframe: {frame_error}")
        
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
        
        await page.wait_for_timeout(200)
        
        if checkbox_updated:
            try:
                for frame in page.frames:
                    if 'recaptcha' in frame.url.lower():
                        try:
                            checkbox_anchor = frame.locator('#recaptcha-anchor')
                            if await checkbox_anchor.count() > 0:
                                aria_checked = await checkbox_anchor.get_attribute('aria-checked')
                                has_checked_class = await checkbox_anchor.evaluate("""
                                    (el) => el.classList.contains('recaptcha-checkbox-checked')
                                """)
                                if aria_checked == 'true' or has_checked_class:
                                    logger.info(f"[Playwright] ✓ reCAPTCHA checkbox verified as checked in iframe")
                                else:
                                    logger.info(f"[Playwright] ⚠️  reCAPTCHA checkbox state: aria-checked={aria_checked}, has-class={has_checked_class}")
                        except Exception:
                            pass
                        break
            except Exception:
                pass
        
        await page.wait_for_timeout(100)
        
        token_verification = await page.evaluate("""
            () => {
                try {
                    if (!window.grecaptcha) {
                        return {verified: false, error: 'grecaptcha not available'};
                    }
                    // Check if getResponse exists and returns our token
                    if (typeof window.grecaptcha.getResponse === 'function') {
                        try {
                            // Try with widget ID first
                            const widgetId = (typeof window.captchaWidget !== 'undefined' && window.captchaWidget !== null) ? window.captchaWidget : 0;
                            let response = window.grecaptcha.getResponse(widgetId);
                            if (!response || response.length < 100) {
                                // Fallback to 0
                                response = window.grecaptcha.getResponse(0);
                            }
                            if (response && response.length > 100) {
                                return {verified: true, tokenLength: response.length, source: 'getResponse'};
                            }
                        } catch (e) {
                            // If getResponse fails, check textarea as fallback
                            const textarea = document.querySelector('textarea[name="g-recaptcha-response"]');
                            if (textarea && textarea.value && textarea.value.length > 100) {
                                return {verified: true, tokenLength: textarea.value.length, source: 'textarea'};
                            }
                            return {verified: false, error: e.message};
                        }
                    }
                    // Fallback: check textarea
                    const textarea = document.querySelector('textarea[name="g-recaptcha-response"]');
                    if (textarea && textarea.value && textarea.value.length > 100) {
                        return {verified: true, tokenLength: textarea.value.length, source: 'textarea'};
                    }
                    return {verified: false, error: 'Token not found in getResponse or textarea'};
                } catch (e) {
                    return {verified: false, error: e.message};
                }
            }
        """)
        
        if not token_verification.get('verified'):
            logger.warning(f"[Playwright] Token verification failed before submission: {token_verification.get('error')}, but proceeding")
        else:
            logger.info(f"[Playwright] Token verified before submission (length: {token_verification.get('tokenLength', 0)}, source: {token_verification.get('source', 'getResponse')})")

        submit_button = page.locator('#NewloginForm-d button#loginFormSubmitButton')
        await submit_button.wait_for(state='visible', timeout=10000)

        button_enabled = False
        for retry in range(15):
            try:
                enabled_check = await page.evaluate("""
                    () => {
                        const btn = document.querySelector('#loginFormSubmitButton');
                        return btn && !btn.disabled && btn.offsetParent !== null; // Also check visibility
                    }
                """)
                if enabled_check:
                    button_enabled = True
                    logger.info(f"[Playwright] Submit button is enabled (attempt {retry + 1})")
                    break
            except Exception:
                pass
            await page.wait_for_timeout(500)
        
        if not button_enabled:
            logger.warning("[Playwright] Button may still be disabled or not visible, proceeding anyway")

        login_response_future = asyncio.Future()
        login_request_future = asyncio.Future()
        
        final_captcha_check = await page.evaluate("""
            () => {
                try {
                    const widgetId = (typeof window.captchaWidget !== 'undefined' && window.captchaWidget !== null) ? window.captchaWidget : 0;
                    let token = null;
                    
                    // Try to get token via getResponse (this is what doLogin uses)
                    if (window.grecaptcha && window.grecaptcha.getResponse) {
                        token = window.grecaptcha.getResponse(widgetId);
                        if (!token || token.length < 100) {
                            token = window.grecaptcha.getResponse(0); // Fallback to 0
                        }
                    }
                    
                    // Also check textarea
                    if (!token || token.length < 100) {
                        const textarea = document.querySelector('textarea[name="g-recaptcha-response"]');
                        if (textarea && textarea.value && textarea.value.length > 100) {
                            token = textarea.value;
                        }
                    }
                    
                    return {
                        available: token && token.length > 100,
                        length: token ? token.length : 0,
                        preview: token ? token.substring(0, 50) + '...' + token.substring(token.length - 50) : 'N/A',
                        widgetId: widgetId
                    };
                } catch (e) {
                    return {available: false, error: e.message, length: 0};
                }
            }
        """)
        
        if not final_captcha_check.get('available'):
            logger.error(f"[Playwright] ❌ CRITICAL: CAPTCHA token not available right before submission!")
            logger.error(f"[Playwright] Error: {final_captcha_check.get('error', 'Token not found')}")
            logger.error(f"[Playwright] Token length: {final_captcha_check.get('length', 0)}")
            await browser.close()
            raise RuntimeError("CAPTCHA token not available - cannot submit login")
        else:
            logger.info(f"[Playwright] ✓ CAPTCHA token before submission: len={final_captcha_check.get('length')}, widget={final_captcha_check.get('widgetId')}")
        
        time_since_captcha = time_module.time() - captcha_received_time
        logger.info(f"[Playwright] Time since CAPTCHA received: {time_since_captcha:.2f}s")
        
        await page.wait_for_timeout(200)
        
        total_time = time_module.time() - login_start_time
        time_since_captcha_total = time_module.time() - captcha_received_time
        logger.info(f"[Playwright] Total time so far: {total_time:.1f}s, CAPTCHA-to-submit: {time_since_captcha_total:.1f}s")

        try:
            button_box = await submit_button.bounding_box()
            if button_box:
                await page.mouse.move(
                    button_box['x'] + button_box['width'] / 2 + random.randint(-5, 5),
                    button_box['y'] + button_box['height'] / 2 + random.randint(-5, 5)
                )
                await page.wait_for_timeout(random.randint(100, 200))
        except Exception:
            pass
        
        time_since_captcha = time_module.time() - captcha_received_time
        if time_since_captcha > 120:
            logger.error(f"[Playwright] ❌ CAPTCHA token is {time_since_captcha:.2f}s old — likely EXPIRED (>120s)!")
        elif time_since_captcha > 90:
            logger.warning(f"[Playwright] ⚠️  CAPTCHA token is {time_since_captcha:.2f}s old — may be close to expiration!")
        else:
            logger.info(f"[Playwright] Token age OK ({time_since_captcha:.2f}s)")
        
        final_token_check = await page.evaluate("""
            () => {
                try {
                    const widgetId = (typeof window.captchaWidget !== 'undefined' && window.captchaWidget !== null) ? window.captchaWidget : 0;
                    let token = null;
                    let source = 'none';
                    
                    if (window.grecaptcha && window.grecaptcha.getResponse) {
                        token = window.grecaptcha.getResponse(widgetId);
                        if (token && token.length > 100) {
                            source = 'getResponse';
                        }
                    }
                    // Check textarea as backup
                    if (!token || token.length < 100) {
                        const textarea = document.querySelector('textarea[name="g-recaptcha-response"]');
                        if (textarea && textarea.value && textarea.value.length > 100) {
                            token = textarea.value;
                            source = 'textarea';
                        }
                    }
                    
                    if (token && token.length > 100) {
                        return {
                            valid: true, 
                            length: token.length,
                            source: source,
                            preview: token.substring(0, 50) + '...' + token.substring(token.length - 50)
                        };
                    }
                    return {valid: false, error: 'Token not found or too short', length: token ? token.length : 0};
                } catch (e) {
                    return {valid: false, error: e.message, length: 0};
                }
            }
        """)
        
        if final_token_check.get('valid'):
            logger.info(f"[Playwright] Token valid pre-submission (len={final_token_check.get('length')}, src={final_token_check.get('source')})")
        else:
            logger.error(f"[Playwright] ❌ Token invalid right before submission! Error: {final_token_check.get('error')} (len={final_token_check.get('length', 0)})")
        
        if not final_token_check.get('valid'):
            logger.info("[Playwright] Attempting emergency token re-injection...")
            emergency_reinjection = await page.evaluate(
            """
            (token) => {
                    try {
                        if (window.grecaptcha && window.grecaptcha.getResponse) {
                            const widgetId = (typeof window.captchaWidget !== 'undefined' && window.captchaWidget !== null) ? window.captchaWidget : 0;
                            window.grecaptcha.getResponse = function(id) {
                                if (typeof id === 'undefined' || id === null || id === 0 || id === widgetId) {
                        return token;
                    }
                                return token; // Always return token regardless
                            };
                        }
                        const textarea = document.querySelector('textarea[name="g-recaptcha-response"]');
                        if (textarea) {
                            textarea.value = token;
                            textarea.dispatchEvent(new Event('input', { bubbles: true }));
                            textarea.dispatchEvent(new Event('change', { bubbles: true }));
                        }
                        return {success: true};
                    } catch (e) {
                        return {success: false, error: e.message};
                }
            }
            """,
                captcha
            )
            if emergency_reinjection.get('success'):
                logger.info("[Playwright] Emergency token re-injection successful")
                await page.wait_for_timeout(random.randint(300, 600))
            else:
                logger.error(f"[Playwright] Emergency token re-injection failed: {emergency_reinjection.get('error')}")
                await browser.close()
                raise RuntimeError("Token lost before submission - cannot proceed")
        else:
            logger.info(f"[Playwright] Final token check passed (length: {final_token_check.get('length', 0)})")
        
        time_since_captcha_check = time_module.time() - captcha_received_time
        if time_since_captcha_check > 30:
            logger.warning(f"[Playwright] ⚠️  WARNING: {time_since_captcha_check:.2f}s since CAPTCHA solve - token may be expiring soon!")
        await page.wait_for_timeout(random.randint(500, 1000))
        
        # Route handler UNIFICADO: Injeta headers reais do Chrome + valida POST data
        # IMPORTANTE: Não registramos route aqui! O force_login_headers (mais abaixo)
        # já faz o route.continue_() com os headers corretos. Este bloco apenas loga.
        # O route registration foi removido para evitar conflito com force_login_headers.
        logger.info("[Playwright] Login route handler será configurado pelo force_login_headers (abaixo)")
        
        def handle_request(request):
            url = request.url
            if '/VistosOnline/login' in url and request.method == 'POST':
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
                except Exception as e:
                    logger.error(f"[Playwright] Error capturing login response: {e}")
            elif '/VistosOnline/login' in url or '/VistosOnline/login' in request_url:
                logger.info(f"[Playwright] Login response detected but future already done: {url} (status: {response.status})")
        
        page.on("request", handle_request)
        page.on("response", handle_response)

        logger.info("[Playwright] Verifying form data before submission...")
        
        captchaWidget_check = await page.evaluate("""
            () => {
                if (typeof window.captchaWidget === 'undefined' || window.captchaWidget === null) {
                    window.captchaWidget = 0;
                    return {wasUndefined: true, value: 0};
                }
                return {wasUndefined: false, value: window.captchaWidget};
            }
        """)
        
        if captchaWidget_check.get('wasUndefined'):
            logger.warning(f"[Playwright] CRITICAL: captchaWidget was undefined before submission! Set it to {captchaWidget_check.get('value')}")
        else:
            logger.info(f"[Playwright] captchaWidget is properly defined: {captchaWidget_check.get('value')}")
        
        logger.info("[Playwright] Waiting for doLogin function and jQuery to be available...")
        doLogin_available = False
        for attempt in range(10):
            check_result = await page.evaluate("""
                () => {
                    // Check for doLogin in various scopes
                    let hasDoLogin = false;
                    try {
                        hasDoLogin = typeof window.doLogin === 'function' || typeof doLogin === 'function';
                    } catch (e) {
                        // Function might not be accessible
                    }
                    
                    return {
                        hasDoLoginWindow: typeof window.doLogin === 'function',
                        hasDoLoginGlobal: typeof doLogin === 'function',
                        hasDoLogin: hasDoLogin,
                        hasJQuery: typeof $ !== 'undefined',
                        hasJQueryReady: typeof $ !== 'undefined' && typeof $(document).ready === 'function',
                        hasForm: !!document.getElementById('NewloginForm-d'),
                        captchaWidgetDefined: typeof window.captchaWidget !== 'undefined' && window.captchaWidget !== null,
                        captchaWidgetValue: (typeof window.captchaWidget !== 'undefined' && window.captchaWidget !== null) ? window.captchaWidget : null
                    };
                }
            """)
            logger.info(f"[Playwright] Function check (attempt {attempt + 1}): {check_result}")
            if check_result.get('hasDoLogin') or check_result.get('hasDoLoginGlobal'):
                doLogin_available = True
                logger.info(f"[Playwright] doLogin function found (attempt {attempt + 1})")
                break
            if check_result.get('hasJQuery') and attempt >= 3:
                logger.info(f"[Playwright] jQuery available, will try form submit (attempt {attempt + 1})")
                break
            await page.wait_for_timeout(500)
        
        if not doLogin_available:
            logger.info("[Playwright] doLogin not on window scope — using form submit (expected for this site)")
        
        form_data_check = await page.evaluate("""
            () => {
                try {
                    const form = document.getElementById('NewloginForm-d');
                    if (!form) {
                        return {success: false, error: 'Form not found'};
                    }
                    
                    const username = form.querySelector('input[name="username"]').value;
                    const password = form.querySelector('input[name="password"]').value;
                    
                    let captchaResponse = '';
                    // Use captchaWidget if defined (matching doLogin's behavior: grecaptcha.getResponse(captchaWidget))
                    const widgetId = (typeof window.captchaWidget !== 'undefined' && window.captchaWidget !== null) ? window.captchaWidget : 0;
                    if (window.grecaptcha && window.grecaptcha.enterprise) {
                        captchaResponse = window.grecaptcha.enterprise.getResponse(widgetId);
                    } else if (window.grecaptcha && window.grecaptcha.getResponse) {
                        captchaResponse = window.grecaptcha.getResponse(widgetId);
                    }
                    
                    // Fallback to 0 if widgetId didn't work
                    if (!captchaResponse || captchaResponse === '') {
                        if (window.grecaptcha && window.grecaptcha.getResponse) {
                            captchaResponse = window.grecaptcha.getResponse(0);
                        }
                    }
                    
                    // Final fallback: check textarea
                    if (!captchaResponse || captchaResponse === '') {
                        const textarea = document.querySelector('textarea[name="g-recaptcha-response"]');
                        if (textarea && textarea.value) {
                            captchaResponse = textarea.value;
                        }
                    }
                    
                    return {
                        success: true,
                        hasUsername: !!username,
                        hasPassword: !!password,
                        hasCaptcha: !!captchaResponse && captchaResponse.length > 0,
                        captchaLength: captchaResponse ? captchaResponse.length : 0,
                        usernameLength: username ? username.length : 0,
                        hasDoLogin: typeof window.doLogin === 'function'
                    };
                } catch (e) {
                    return {success: false, error: e.message};
                }
            }
        """)
        
        logger.info(f"[Playwright] Form data check: {form_data_check}")
        
        if not form_data_check.get('success'):
            await browser.close()
            raise RuntimeError(f"Form data check failed: {form_data_check.get('error', 'Unknown error')}")
        
        if not form_data_check.get('hasUsername'):
            await browser.close()
            raise RuntimeError("Username field is empty")
        
        if not form_data_check.get('hasPassword'):
            await browser.close()
            raise RuntimeError("Password field is empty")
        
        if not form_data_check.get('hasCaptcha'):
            await browser.close()
            raise RuntimeError("CAPTCHA token is missing or empty")
        
        language = scraper_settings.get('language', 'PT') if scraper_settings else 'PT'
        
        logger.info("[Playwright] Verifying CAPTCHA is solved successfully before submission...")
        
        captcha_verification = await page.evaluate("""
            () => {
                try {
                    const result = {
                        verified: false,
                        tokenLength: 0,
                        source: null,
                        error: null,
                        widgetId: null,
                        grecaptchaAvailable: false,
                        getResponseAvailable: false
                    };
                    
                    // Check if grecaptcha is available
                    result.grecaptchaAvailable = typeof window.grecaptcha !== 'undefined' && window.grecaptcha !== null;
                    
                    if (!result.grecaptchaAvailable) {
                        result.error = 'grecaptcha not available';
                        return result;
                    }
                    
                    // Check if getResponse is available
                    result.getResponseAvailable = typeof window.grecaptcha.getResponse === 'function';
                    
                    if (!result.getResponseAvailable) {
                        result.error = 'grecaptcha.getResponse is not a function';
                        return result;
                    }
                    
                    // Get widget ID
                    const widgetId = (typeof window.captchaWidget !== 'undefined' && window.captchaWidget !== null) 
                        ? window.captchaWidget 
                        : 0;
                    result.widgetId = widgetId;
                    
                    // Try to get token via getResponse
                    let token = null;
                    try {
                        token = window.grecaptcha.getResponse(widgetId);
                        if (token && token.length > 100) {
                            result.verified = true;
                            result.tokenLength = token.length;
                            result.source = 'getResponse';
                            return result;
                        }
                    } catch (e) {
                        result.error = `getResponse failed: ${e.message}`;
                    }
                    
                    // Fallback: check textarea
                    const textarea = document.querySelector('textarea[name="g-recaptcha-response"]');
                    if (textarea && textarea.value && textarea.value.length > 100) {
                        result.verified = true;
                        result.tokenLength = textarea.value.length;
                        result.source = 'textarea';
                        return result;
                    }
                    
                    // If we get here, token is not available
                    if (!result.error) {
                        result.error = 'Token not found in getResponse or textarea';
                    }
                    
                    return result;
                } catch (e) {
                    return {
                        verified: false,
                        tokenLength: 0,
                        source: null,
                        error: e.message,
                        widgetId: null,
                        grecaptchaAvailable: false,
                        getResponseAvailable: false
                    };
                }
            }
        """)
        
        if not captcha_verification.get('verified'):
            error_msg = captcha_verification.get('error', 'Unknown error')
            logger.error(f"[Playwright] CRITICAL: CAPTCHA verification failed before submission!")
            logger.error(f"[Playwright] Error: {error_msg}")
            logger.error(f"[Playwright] grecaptcha available: {captcha_verification.get('grecaptchaAvailable')}")
            logger.error(f"[Playwright] getResponse available: {captcha_verification.get('getResponseAvailable')}")
            logger.error(f"[Playwright] Widget ID: {captcha_verification.get('widgetId')}")
            
            logger.info("[Playwright] Attempting emergency CAPTCHA token re-injection...")
            emergency_result = await page.evaluate(
                """
                (token) => {
                    try {
                        // Re-inject token into getResponse override
                        if (window.grecaptcha) {
                            const widgetId = (typeof window.captchaWidget !== 'undefined' && window.captchaWidget !== null) 
                                ? window.captchaWidget 
                                : 0;
                            
                            window.grecaptcha.getResponse = function(id) {
                                if (typeof id === 'undefined' || id === null || id === 0 || id === widgetId) {
                                    return token;
                                }
                                return token; // Always return token
                            };
                            
                            // Also override enterprise if it exists
                            // CRITICAL: Override enterprise.getResponse to handle no-parameter calls
                            if (window.grecaptcha.enterprise) {
                                window.grecaptcha.enterprise.getResponse = function(widgetId) {
                                    // If called with no parameters (undefined), return token directly
                                    if (typeof widgetId === 'undefined' || widgetId === null) {
                                        return token;
                                    }
                                    // If called with widgetId, use the same logic
                                    if (widgetId === 0) {
                                        return token;
                                    }
                                    // Always return our token as fallback
                                    return token;
                                };
                            }
                        }
                        
                        // Set textarea value
                        const textarea = document.querySelector('textarea[name="g-recaptcha-response"]');
                        if (textarea) {
                            textarea.value = token;
                            textarea.dispatchEvent(new Event('input', { bubbles: true }));
                            textarea.dispatchEvent(new Event('change', { bubbles: true }));
                        }
                        
                        // Verify it's now available
                        if (window.grecaptcha && window.grecaptcha.getResponse) {
                            const widgetId = (typeof window.captchaWidget !== 'undefined' && window.captchaWidget !== null) 
                                ? window.captchaWidget 
                                : 0;
                            const testToken = window.grecaptcha.getResponse(widgetId);
                            if (testToken && testToken.length > 100) {
                                return {success: true, tokenLength: testToken.length};
                            }
                        }
                        
                        return {success: false, error: 'Token still not available after re-injection'};
                    } catch (e) {
                        return {success: false, error: e.message};
                    }
                }
                """,
                captcha
            )
            
            if emergency_result.get('success'):
                logger.info(f"[Playwright] Emergency re-injection successful! Token length: {emergency_result.get('tokenLength')}")
                await page.wait_for_timeout(500)
            else:
                logger.error(f"[Playwright] Emergency re-injection failed: {emergency_result.get('error')}")
                await browser.close()
                raise RuntimeError(f"CAPTCHA verification failed - cannot proceed without valid token. Error: {error_msg}")
        else:
            logger.info(f"[Playwright] CAPTCHA pre-submit ok: len={captcha_verification.get('tokenLength')}, src={captcha_verification.get('source')}")
        
        logger.info("[Playwright] Moving mouse to submit button and clicking like a human...")
        
        submit_button = page.locator('#NewloginForm-d button#loginFormSubmitButton')
        await submit_button.wait_for(state='visible', timeout=10000)
        
        button_enabled = False
        for retry in range(15):
            try:
                enabled_check = await page.evaluate("""
                    () => {
                        const btn = document.querySelector('#loginFormSubmitButton');
                        return btn && !btn.disabled && btn.offsetParent !== null;
                    }
                """)
                if enabled_check:
                    button_enabled = True
                    logger.info(f"[Playwright] Submit button is enabled (attempt {retry + 1})")
                    break
            except Exception:
                pass
            await page.wait_for_timeout(500)
        
        if not button_enabled:
            logger.warning("[Playwright] Button may still be disabled or not visible, proceeding anyway")
        
        await page.wait_for_timeout(random.randint(800, 1500))
        
        try:
            button_box = await submit_button.bounding_box()
            if button_box:
                near_x = button_box['x'] + button_box['width'] / 2 + random.randint(-30, 30)
                near_y = button_box['y'] + button_box['height'] / 2 + random.randint(-20, 20)
                await page.mouse.move(near_x, near_y, steps=random.randint(10, 20))
                await page.wait_for_timeout(random.randint(100, 250))
                
                target_x = button_box['x'] + button_box['width'] / 2 + random.randint(-5, 5)
                target_y = button_box['y'] + button_box['height'] / 2 + random.randint(-5, 5)
                await page.mouse.move(target_x, target_y, steps=random.randint(5, 12))
                await page.wait_for_timeout(random.randint(150, 300))
        except Exception as e:
            logger.warning(f"[Playwright] Could not move mouse to button: {e}, will click directly")
        
        await page.evaluate("""
            () => {
                const form = document.getElementById('NewloginForm-d');
                if (!form) return;
                
                // Create a mock event object that doLogin can access
                const mockEvent = { 
                    preventDefault: () => {},
                    stopPropagation: () => {},
                    target: form,
                    currentTarget: form,
                    type: 'submit'
                };
                window.event = mockEvent;
            }
        """)
        
        final_time_since_captcha = time_module.time() - captcha_received_time
        logger.info(f"[Playwright] Final check: {final_time_since_captcha:.2f}s since CAPTCHA solve")
        if final_time_since_captcha > 90:
            logger.error(f"[Playwright] ❌ ERROR: Token is {final_time_since_captcha:.2f}s old - likely expired!")
            await browser.close()
            raise RuntimeError(f"CAPTCHA token too old ({final_time_since_captcha:.2f}s) - likely expired before submission")
        elif final_time_since_captcha > 60:
            logger.warning(f"[Playwright] ⚠️  WARNING: Token is {final_time_since_captcha:.2f}s old - may be close to expiration!")
        
        logger.info("[Playwright] Verifying CAPTCHA token is accessible before submission...")
        token_verification = await page.evaluate(
            """
            () => {
                const result = {
                    enterprise_available: false,
                    enterprise_getResponse_available: false,
                    token_via_enterprise_no_params: '',
                    token_via_enterprise_widget0: '',
                    token_via_regular: '',
                    token_via_textarea: '',
                    final_token: ''
                };
                
                // Check if enterprise is available
                if (window.grecaptcha && window.grecaptcha.enterprise) {
                    result.enterprise_available = true;
                    if (window.grecaptcha.enterprise.getResponse) {
                        result.enterprise_getResponse_available = true;
                        // CRITICAL: Test with NO parameters (this is what form handler uses)
                        try {
                            result.token_via_enterprise_no_params = window.grecaptcha.enterprise.getResponse();
                        } catch (e) {
                            result.token_via_enterprise_no_params = 'ERROR: ' + e.message;
                        }
                        // Also test with widget 0
                        try {
                            result.token_via_enterprise_widget0 = window.grecaptcha.enterprise.getResponse(0);
                        } catch (e) {
                            result.token_via_enterprise_widget0 = 'ERROR: ' + e.message;
                        }
                    }
                }
                
                // Check regular getResponse
                if (window.grecaptcha && window.grecaptcha.getResponse) {
                    try {
                        result.token_via_regular = window.grecaptcha.getResponse(0);
                    } catch (e) {
                        result.token_via_regular = 'ERROR: ' + e.message;
                    }
                }
                
                // Check textarea
                const textarea = document.querySelector('textarea[name="g-recaptcha-response"]');
                if (textarea && textarea.value) {
                    result.token_via_textarea = textarea.value;
                }
                
                // Determine final token (prioritize enterprise no-params as that's what form handler uses)
                result.final_token = result.token_via_enterprise_no_params || 
                                    result.token_via_enterprise_widget0 || 
                                    result.token_via_regular || 
                                    result.token_via_textarea || 
                                    '';
                
                return result;
            }
            """
        )
        
        logger.info(
            f"[Playwright] Token verify: enterprise={token_verification.get('enterprise_available')}, "
            f"no-params-len={len(token_verification.get('token_via_enterprise_no_params', ''))}, "
            f"regular-len={len(token_verification.get('token_via_regular', ''))}"
        )
        
        if not token_verification.get('token_via_enterprise_no_params') or len(token_verification.get('token_via_enterprise_no_params', '')) < 100:
            logger.error("[Playwright] ❌ CRITICAL ERROR: enterprise.getResponse() with NO parameters returns empty or invalid token!")
            logger.error("[Playwright] The form submit handler will check this FIRST and show error/return early if it's empty!")
            logger.error("[Playwright] This means doLogin will NEVER be called!")
            await browser.close()
            raise RuntimeError("CAPTCHA token not accessible via enterprise.getResponse() with no parameters - form submit handler will fail")
        
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
                            options.success = function(data, textStatus, jqXHR) {
                                try {
                                    // Store the result for later retrieval
                                    let resultObj = null;
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
                                
                                // Call original success callback if it exists
                                if (originalSuccess) {
                                    return originalSuccess.apply(this, arguments);
                                }
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
        
        logger.info("[Playwright] Waiting for jQuery and doLogin function to be available...")
        jquery_and_dologin_ready = False
        for wait_attempt in range(20):
            dependencies_check = await page.evaluate("""
                () => {
                    return {
                        hasJQuery: typeof $ !== 'undefined' && typeof $.ajax === 'function',
                        hasDoLogin: typeof window.doLogin === 'function' || typeof doLogin === 'function',
                        hasCookies: document.cookie && document.cookie.length > 0,
                        pageReady: document.readyState === 'complete' || document.readyState === 'interactive'
                    };
                }
            """)
            
            if dependencies_check.get('hasJQuery'):
                jquery_and_dologin_ready = True
                logger.info(f"[Playwright] jQuery is ready (attempt {wait_attempt + 1}), doLogin={dependencies_check.get('hasDoLogin')}, cookies={dependencies_check.get('hasCookies')}")
                break
            
            if wait_attempt < 19:
                logger.info(f"[Playwright] Waiting for jQuery (attempt {wait_attempt + 1}/20): jQuery={dependencies_check.get('hasJQuery')}, doLogin={dependencies_check.get('hasDoLogin')}, cookies={dependencies_check.get('hasCookies')}")
            await page.wait_for_timeout(500)
        
        if not jquery_and_dologin_ready:
            logger.warning(f"[Playwright] jQuery may not be fully ready after 10 seconds, but proceeding with validation check...")
            final_check = await page.evaluate("""
                () => {
                    return {
                        hasDollar: typeof $ !== 'undefined',
                        hasDollarAjax: typeof $ !== 'undefined' && typeof $.ajax === 'function',
                        hasjQuery: typeof jQuery !== 'undefined',
                        hasjQueryAjax: typeof jQuery !== 'undefined' && typeof jQuery.ajax === 'function',
                        hasWindowDollar: typeof window.$ !== 'undefined',
                        hasWindowjQuery: typeof window.jQuery !== 'undefined',
                        hasDoLogin: typeof window.doLogin === 'function' || typeof doLogin === 'function',
                        hasCookies: document.cookie && document.cookie.length > 0,
                        cookieLength: document.cookie ? document.cookie.length : 0
                    };
                }
            """)
            logger.warning(f"[Playwright] Final dependency check: {final_check}")
        
        logger.info("[Playwright] Performing pre-submission validation...")
        pre_submit_check = await page.evaluate(
            """
            ([username, password]) => {
                const result = {
                    form_exists: false,
                    form_visible: false,
                    username_field_exists: false,
                    username_filled: false,
                    username_value: '',
                    password_field_exists: false,
                    password_filled: false,
                    password_length: 0,
                    submit_button_exists: false,
                    submit_button_enabled: false,
                    submit_button_visible: false,
                    captcha_token_valid: false,
                    captcha_token_length: 0,
                    jquery_available: false,
                    doLogin_available: false,
                    captchaWidget_defined: false,
                    page_ready: false,
                    cookies_present: false,
                    errors: []
                };
                
                try {
                    // Check page ready state
                    result.page_ready = document.readyState === 'complete' || document.readyState === 'interactive';
                    if (!result.page_ready) {
                        result.errors.push('Page not ready - readyState: ' + document.readyState);
                    }
                    
                    // Check form exists
                    const form = document.getElementById('NewloginForm-d');
                    result.form_exists = !!form;
                    if (!form) {
                        result.errors.push('Login form not found (NewloginForm-d)');
                        return result;
                    }
                    
                    // Check form visibility
                    const formStyle = window.getComputedStyle(form);
                    result.form_visible = formStyle.display !== 'none' && formStyle.visibility !== 'hidden';
                    if (!result.form_visible) {
                        result.errors.push('Form is not visible');
                    }
                    
                    // Check username field
                    const usernameInput = form.querySelector('input[name="username"]');
                    result.username_field_exists = !!usernameInput;
                    if (usernameInput) {
                        result.username_value = usernameInput.value || '';
                        result.username_filled = result.username_value.length > 0;
                        // Verify it matches expected username
                        if (result.username_filled && result.username_value !== username) {
                            result.errors.push('Username field value does not match expected value');
                        }
                    } else {
                        result.errors.push('Username input field not found');
                    }
                    
                    // Check password field
                    const passwordInput = form.querySelector('input[name="password"]');
                    result.password_field_exists = !!passwordInput;
                    if (passwordInput) {
                        result.password_length = passwordInput.value ? passwordInput.value.length : 0;
                        result.password_filled = result.password_length > 0;
                        // Verify it matches expected password length (don't check actual value for security)
                        if (result.password_filled && result.password_length !== password.length) {
                            result.errors.push('Password field length does not match expected length');
                        }
                    } else {
                        result.errors.push('Password input field not found');
                    }
                    
                    // Check submit button
                    const submitButton = form.querySelector('button#loginFormSubmitButton');
                    result.submit_button_exists = !!submitButton;
                    if (submitButton) {
                        result.submit_button_enabled = !submitButton.disabled;
                        const buttonStyle = window.getComputedStyle(submitButton);
                        result.submit_button_visible = buttonStyle.display !== 'none' && buttonStyle.visibility !== 'hidden';
                        if (!result.submit_button_enabled) {
                            result.errors.push('Submit button is disabled');
                        }
                        if (!result.submit_button_visible) {
                            result.errors.push('Submit button is not visible');
                        }
                    } else {
                        result.errors.push('Submit button not found (loginFormSubmitButton)');
                    }
                    
                    // Check CAPTCHA token (critical - form handler checks this first)
                    let captchaToken = '';
                    if (window.grecaptcha && window.grecaptcha.enterprise && window.grecaptcha.enterprise.getResponse) {
                        try {
                            captchaToken = window.grecaptcha.enterprise.getResponse(); // NO parameters - this is what form handler uses
                        } catch (e) {
                            result.errors.push('enterprise.getResponse() error: ' + e.message);
                        }
                    }
                    
                    // Fallback check
                    if (!captchaToken || captchaToken === '') {
                        const widgetId = (typeof window.captchaWidget !== 'undefined' && window.captchaWidget !== null) ? window.captchaWidget : 0;
                        if (window.grecaptcha && window.grecaptcha.getResponse) {
                            try {
                                captchaToken = window.grecaptcha.getResponse(widgetId);
                            } catch (e) {
                                result.errors.push('getResponse(' + widgetId + ') error: ' + e.message);
                            }
                        }
                    }
                    
                    result.captcha_token_length = captchaToken ? captchaToken.length : 0;
                    result.captcha_token_valid = captchaToken && captchaToken.length >= 100;
                    if (!result.captcha_token_valid) {
                        result.errors.push('CAPTCHA token invalid or empty (length: ' + result.captcha_token_length + ')');
                    }
                    
                    // Check captchaWidget
                    result.captchaWidget_defined = typeof window.captchaWidget !== 'undefined' && window.captchaWidget !== null;
                    if (!result.captchaWidget_defined) {
                        result.errors.push('captchaWidget is not defined');
                    }
                    
                    // Check jQuery - try multiple methods
                    result.jquery_available = (typeof $ !== 'undefined' && typeof $.ajax === 'function') ||
                                            (typeof jQuery !== 'undefined' && typeof jQuery.ajax === 'function') ||
                                            (typeof window.$ !== 'undefined' && typeof window.$.ajax === 'function') ||
                                            (typeof window.jQuery !== 'undefined' && typeof window.jQuery.ajax === 'function');
                    if (!result.jquery_available) {
                        // More detailed error for debugging
                        let jqCheck = {
                            hasDollar: typeof $ !== 'undefined',
                            hasDollarAjax: typeof $ !== 'undefined' && typeof $.ajax === 'function',
                            hasjQuery: typeof jQuery !== 'undefined',
                            hasjQueryAjax: typeof jQuery !== 'undefined' && typeof jQuery.ajax === 'function',
                            hasWindowDollar: typeof window.$ !== 'undefined',
                            hasWindowjQuery: typeof window.jQuery !== 'undefined'
                        };
                        result.errors.push('jQuery not available (check: ' + JSON.stringify(jqCheck) + ')');
                    }
                    
                    // Check doLogin function - try multiple scopes
                    result.doLogin_available = typeof window.doLogin === 'function' || 
                                             typeof doLogin === 'function' ||
                                             (window.doLogin && typeof window.doLogin === 'function');
                    if (!result.doLogin_available) {
                        let dlCheck = {
                            hasWindowDoLogin: typeof window.doLogin === 'function',
                            hasGlobalDoLogin: typeof doLogin === 'function',
                            windowDoLoginType: typeof window.doLogin
                        };
                        result.errors.push('doLogin function not available (check: ' + JSON.stringify(dlCheck) + ')');
                    }
                    
                    // Check cookies (at least check if document.cookie exists - full cookie check done server-side)
                    result.cookies_present = document.cookie && document.cookie.length > 0;
                    if (!result.cookies_present) {
                        result.errors.push('No cookies present');
                    }
                    
                } catch (e) {
                    result.errors.push('Pre-submission check error: ' + e.message);
                }
                
                return result;
            }
            """,
            [username, password]
        )
        
        logger.info(
            f"[Playwright] Pre-submit: form={pre_submit_check.get('form_exists')}, "
            f"user={'ok' if pre_submit_check.get('username_filled') else 'EMPTY'}, "
            f"pass={'ok' if pre_submit_check.get('password_filled') else 'EMPTY'}, "
            f"captcha={'ok' if pre_submit_check.get('captcha_token_valid') else 'MISSING'} "
            f"(len={pre_submit_check.get('captcha_token_length', 0)}), "
            f"jquery={pre_submit_check.get('jquery_available')}"
        )
        
        errors = [e for e in pre_submit_check.get('errors', []) if 'doLogin' not in e]
        if errors:
            logger.warning(f"[Playwright] Pre-submission validation found {len(errors)} issue(s):")
            for error in errors:
                logger.warning(f"[Playwright]   - {error}")
        
        critical_checks = [
            ('form_exists', 'Login form not found'),
            ('username_field_exists', 'Username field not found'),
            ('username_filled', 'Username field is empty'),
            ('password_field_exists', 'Password field not found'),
            ('password_filled', 'Password field is empty'),
            ('captcha_token_valid', 'CAPTCHA token invalid or empty'),
            ('jquery_available', 'jQuery not available (required for doLogin)'),
        ]
        
        critical_failures = []
        for check_key, error_msg in critical_checks:
            if not pre_submit_check.get(check_key, False):
                critical_failures.append(error_msg)
        
        if critical_failures:
            logger.warning("[Playwright] ⚠️ CRITICAL pre-submission validation failures detected (proceeding anyway):")
            for failure in critical_failures:
                logger.warning(f"[Playwright]   - {failure}")
        
        warning_checks = [
            ('submit_button_enabled', 'Submit button is disabled'),
            ('submit_button_visible', 'Submit button is not visible'),
            ('page_ready', 'Page may not be fully ready'),
        ]
        
        warnings = []
        for check_key, warning_msg in warning_checks:
            if not pre_submit_check.get(check_key, False):
                warnings.append(warning_msg)
        
        if warnings:
            logger.warning("[Playwright] ⚠️  Pre-submission validation warnings (non-critical):")
            for warning in warnings:
                logger.warning(f"[Playwright]   - {warning}")
             # --- PREPARAÇÃO DO CLIQUE (ASSINATURA DIGITAL PERFEITA) ---
        # Baseado na captura F12: Headers EXATOS que o site espera.
        
        # 1. Interceptador de Requisição UNIFICADO (Headers + Validação POST data)
        #    Baseado na captura F12 exata do POST /VistosOnline/login
        #    Este é o ÚNICO route handler para login - evita conflitos.
        async def force_login_headers(route, request):
            headers = request.headers.copy() # Pega os headers que o navegador gerou naturalmente
            
            # FORÇA OS HEADERS CRÍTICOS (A assinatura AJAX do Chrome real)
            headers['accept'] = '*/*'
            headers['accept-encoding'] = 'gzip, deflate, br, zstd'
            headers['accept-language'] = 'pt-BR,pt;q=0.9'
            headers['content-type'] = 'application/x-www-form-urlencoded; charset=UTF-8'
            headers['origin'] = SITE_ORIGIN
            headers['referer'] = SITE_REFERER
            headers['sec-fetch-dest'] = 'empty'
            headers['sec-fetch-mode'] = 'cors'
            headers['sec-fetch-site'] = 'same-origin'
            headers['x-requested-with'] = 'XMLHttpRequest' # Exigido pelo jQuery/Site antigo
            
            # Validação do POST data (antes de enviar)
            try:
                post_data = request.post_data
                if post_data:
                    from urllib.parse import parse_qs
                    parsed = parse_qs(post_data)
                    captcha_val = (parsed.get('captchaResponse') or [''])[0]
                    logger.info(f"[Playwright] Login POST: {len(post_data)} chars, captcha len={len(captcha_val)}")
                    if len(captcha_val) < 100:
                        logger.error(f"[Playwright] ⚠️ CAPTCHA token too short in POST ({len(captcha_val)} chars)")
            except Exception as parse_error:
                logger.warning(f"[Playwright] Could not parse POST data: {parse_error}")
            
            # Continua a requisição com os headers modificados
            await route.continue_(headers=headers)

        # Aplica a rota apenas na URL de login (ÚNICO handler)
        await page.route('**/VistosOnline/login', force_login_headers)
        
        # 2. Garante que o botão está pronto
        submit_button = page.locator('#NewloginForm-d button#loginFormSubmitButton')
        await submit_button.wait_for(state='visible', timeout=10000)
        
        # 3. Move o mouse (Simula hesitação humana)
        try:
            box = await submit_button.bounding_box()
            if box:
                # Move para longe, depois para perto, depois para o centro
                await page.mouse.move(box['x'] - 50, box['y'] - 50, steps=5)
                await page.wait_for_timeout(random.randint(100, 300))
                await page.mouse.move(box['x'] + box['width']/2, box['y'] + box['height']/2, steps=15)
                await page.wait_for_timeout(random.randint(50, 150))
        except Exception:
            pass

        # 4. Validação Final do Token
        token_check = await page.evaluate("""
            () => {
                if(window.grecaptcha && window.grecaptcha.enterprise && window.grecaptcha.enterprise.getResponse) {
                    return window.grecaptcha.enterprise.getResponse();
                }
                return null;
            }
        """)
        
        if not token_check or len(token_check) < 100:
             logger.error("[Playwright] ❌ Token perdido antes do clique!")
             await browser.close()
             raise RuntimeError("Token perdido antes do submit")

        # 4b. Garantir que o campo rgpd está presente no form (enviado pelo doLogin)
        # O HAR real mostra: username, password, language, rgpd=Y, captchaResponse
        try:
            await page.evaluate("""
                () => {
                    // Garantir que rgpd=Y existe no form ou será enviado pelo doLogin
                    const form = document.getElementById('NewloginForm-d');
                    if (form) {
                        // Verificar se já existe
                        let rgpd = form.querySelector('[name="rgpd"]');
                        if (!rgpd) {
                            // Criar campo hidden
                            rgpd = document.createElement('input');
                            rgpd.type = 'hidden';
                            rgpd.name = 'rgpd';
                            rgpd.value = 'Y';
                            form.appendChild(rgpd);
                            console.log('[Bot] Campo rgpd=Y adicionado ao form');
                        } else {
                            rgpd.value = 'Y';
                            console.log('[Bot] Campo rgpd já existia:', rgpd.value);
                        }
                    }
                }
            """)
            logger.info("[Playwright] ✅ Campo rgpd=Y garantido no form")
        except Exception as rgpd_err:
            logger.warning(f"[Playwright] rgpd field error: {rgpd_err}")

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
                            body = await response.text()
                            try:
                                page._login_result = json.loads(body)
                            except:
                                page._login_result = {"raw": body}
                            login_response_future.set_result(response)
                            logger.info(f"[Playwright] ✅ Resposta AJAX Capturada: Status {response.status}")
                        except Exception as e:
                            logger.warning(f"[Playwright] Erro ao ler resposta: {e}")
            except Exception:
                pass

        page.on("response", handle_login_response)

        # 6. O CLIQUE REAL (O navegador gera o restante dos headers automaticamente)
        logger.info("[Playwright] Executando clique REAL com headers forçados...")
        await submit_button.click(delay=random.randint(50, 150))
        
        # 7. Processa o resultado
        try:
            login_response = await asyncio.wait_for(login_response_future, timeout=30.0)

            # Ler o body da resposta capturada
            result_data = None
            try:
                body_bytes = await login_response.body()
                body_text  = body_bytes.decode('utf-8', errors='replace').strip()
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

            if result_data and isinstance(result_data, dict):
                r_type = result_data.get('type', '').lower()
                r_desc = result_data.get('description', '')
                
                if r_type in ['error', 'recaptchaerror', 'secblock', 'warning', 'redirect']:
                    logger.error(f"[Playwright] ❌ SERVIDOR REJEITOU: tipo={r_type}, desc={r_desc}")
                    await _save_debug_html("login_rejected")
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
                        raise RuntimeError(f"Login possivelmente rejeitado: {result_data}")
                
                logger.info(f"[Playwright] ✅ Login Aceito! Tipo: {r_type or 'redirect/OK'}")
            else:
                # result_data é None = body vazio = redirect imediato = login OK
                logger.info("[Playwright] ✅ Login provavelmente aceito (body vazio = redirect)")
            
        except asyncio.TimeoutError:
             logger.error("[Playwright] ❌ TIMEOUT após clique.")
             await _save_debug_html("timeout_submit")
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

        try:
            await page.wait_for_load_state('domcontentloaded', timeout=10000)
        except Exception:
            await page.wait_for_timeout(1000)

        pages = context.pages
        if not pages:
            await browser.close()
            raise RuntimeError("No pages available in browser after form submission")
        
        current_page = pages[-1]
        logger.info(f"[Playwright] Pages in browser after submission: {len(pages)}")
        
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
                await browser.close()
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
                        await browser.close()
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
                    proxy_cookie_pool.save(proxy_raw, fresh_cookies, user_agent)
                    logger.info(
                        f"[CookiePool] ✅ Cookies guardados para proxy "
                        f"{proxy_raw.split(':')[0]} ({len(fresh_cookies)} cookies)"
                    )
            except Exception as _cpe:
                logger.warning(f"[CookiePool] Nao foi possivel guardar cookies: {_cpe}")

            # --- ALERTA DE LOGIN BEM SUCEDIDO ---
            try:
                await send_telegram_alert(f"✅ <b>LOGIN BEM SUCEDIDO!</b>\n👤 Usuário: {username}")
            except Exception: pass

            # --- NAVEGAÇÃO DIRECTA PARA O QUESTIONÁRIO ---
            # Uma única navegação — sem homepage, sem profile.jsp
            questionario_url = f"{BASE_URL}/VistosOnline/Questionario"
            logger.info(f"[Playwright] Navigating to Questionario at {questionario_url}...")
            
            try:
                await current_page.goto(questionario_url, timeout=60000, wait_until="domcontentloaded")
            except Exception as nav_err:
                logger.error(f"[Playwright] Erro ao navegar para Questionario: {nav_err}")
                if "sessionLost" in current_page.url or "Authentication" in current_page.url:
                    raise RuntimeError("Sessão perdida ao navegar para Questionario.")
                try:
                    await current_page.reload(timeout=30000)
                except:
                    raise RuntimeError(f"Falha de conexão ao carregar Questionario: {nav_err}")

            # Verificar URL — se redirecionou para login a sessão perdeu-se
            url_after_nav = current_page.url
            if 'Authentication.jsp' in url_after_nav:
                logger.error(f"[Playwright] ❌ Sessão perdida ao navegar para Questionario — URL: {url_after_nav}")
                # Tentar perceber porquê: verificar cookies
                cookies_now = await context.cookies()
                logger.error(f"[Playwright] Cookies actuais: {[c['name'] for c in cookies_now]}")
                raise RuntimeError(f"Sessão perdida ao abrir Questionario. URL: {url_after_nav}")
            
            if 'sessionLost' in url_after_nav:
                raise RuntimeError(f"Sessão expirada ao abrir Questionario. URL: {url_after_nav}")

            # Espera o formulário
            try:
                await current_page.wait_for_selector("#questForm", timeout=30000)
                logger.info(f"[Playwright] Questionario form loaded.")
            except:
                # Salva HTML para debug se falhar
                await _save_debug_html("questionario_fail")
                raise RuntimeError("Questionario form (#questForm) não encontrado. HTML salvo para debug.")

            logger.info(f"[Playwright] Questionario form loaded.")
            await current_page.wait_for_timeout(random.randint(1500, 3000))

            # Configurações
            cfg = scraper_settings or {}
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

            # Preenchimento
            await smart_fill_field(current_page, "#cb_question_21", country_of_residence, "País Residência")
            await current_page.wait_for_timeout(500)
            await smart_fill_field(current_page, "#cb_question_2", passport_type_code, "Tipo Passaporte")
            await current_page.wait_for_timeout(300)
            await smart_fill_field(current_page, "#cb_question_3", stay_code, "Duração Estadia")
            await current_page.wait_for_timeout(300)
            if country_of_residence == "FRA":
                await smart_fill_field(current_page, "#cb_question_22", "N", "Questão Residência (FRA)")
            await smart_fill_field(current_page, "#cb_question_5", seasonal_work_code, "Trabalho Sazonal")
            await current_page.wait_for_timeout(300)
            await smart_fill_field(current_page, "#cb_question_6", purpose_of_stay_code, "Propósito Estadia")
            await current_page.wait_for_timeout(300)
            await smart_fill_field(current_page, "#cb_question_16", eu_family_code, "Familiar UE")

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

            logger.info("[Playwright] Clicking submit button...")
            await btn_locator.click()

            # Espera navegação para o Formulario
            try:
                await current_page.wait_for_url("**/Formulario**", timeout=45000)
                logger.info(f"[Playwright] ✅ Navegou para Formulario: {current_page.url}")
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
                try: await browser.close()
                except: pass
                return (PDF_SUCCESS_SENTINEL,)

        except Exception as form_flow_error:
            await browser.close()
            raise RuntimeError(f"[Playwright] Failed during profile/first/second form flow: {form_flow_error}")

        return None
    
     # --- NOVA LÓGICA: CAPTURA DE ERRO COM SCREENSHOT ---
    except Exception as e:
        logger.error(f"[Playwright Internal] Erro critico: {e}")
        try:
            # Tira print antes de fechar o navegador
            debug_dir = os.path.join(WORKING_DIR, "debug_screenshots")
            os.makedirs(debug_dir, exist_ok=True)
            ts = time.strftime("%Y%m%d_%H%M%S")
            safe_user = (username or "unknown").replace("/", "_").replace("\\", "_")
            path = os.path.join(debug_dir, f"{safe_user}_CRITICAL_ERROR_{ts}.png")
            await page.screenshot(path=path, full_page=True)
            logger.info(f"[Debug] Screenshot de ERRO salvo: {path}")
        except Exception:
            pass # Ignora se não conseguir tirar print
        raise # Re-levanta o erro para a função Login saber que falhou
    # ---------------------------------------------------
    finally:
        # Fechar TLSClient se ainda estiver aberto (ex: excepção antes do close normal)
        try:
            if '_tls_client' in dir() and _tls_client is not None:
                _tls_client.close()
        except Exception:
            pass
        try:
            if _reusing_context:
                # 3.6: contexto reutilizado — liberar para o pool (NAO fechar)
                if browser_context_pool is not None:
                    await browser_context_pool.release(proxy_raw)
                    logger.info(f"[BrowserPool] Contexto liberado para {proxy_raw.split(':')[0]}")
            else:
                # Contexto novo — invalidar do pool e fechar o browser
                if browser_context_pool is not None:
                    await browser_context_pool.invalidate(proxy_raw)
                if browser is not None:
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
    error_str = error_str.lower()
    if any(x in error_str for x in ['err_tunnel_connection_failed', 'err_proxy_connection_failed',
                                      'tunnel connection failed', 'proxy connection failed']):
        return 'tunnel_fail'   # Proxy morto / porta fechada
    if any(x in error_str for x in ['err_aborted', 'net::err_aborted', 'ns_binding_aborted']):
        return 'aborted'       # Proxy abortou a ligação
    if any(x in error_str for x in ['err_connection_refused', 'connection refused']):
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
    retry = 3
    current_proxy = proxy_raw
    current_client = client

    while retry > 0:
        try:
            if not await check_api_balance():
                logger.warning("[Login] Saldo baixo, esperando...")
                await asyncio.sleep(300)
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
                    await asyncio.sleep(5)
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

        except Exception as e:
            error_str = str(e)
            error_type = _classify_proxy_error(error_str)
            logger.error(f"[Login] Erro ({error_type}): {error_str[:120]}")

            # Penalização por tipo de erro
            penalty = {
                'tunnel_fail': -60, 'refused': -60, 'ssl': -40,
                'aborted': -20, 'timeout': -15,
                'banned': -80, 'captcha': -20, 'generic': -10
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
                            current_client, _ = create_session(proxy_list, user_agent, username=username)
                        except Exception:
                            pass
                else:
                    current_proxy, current_client = _rotate_proxy(
                        proxy_list, current_proxy, user_agent, error_type,
                        username=username
                    )

            # Erros de ban → trocar proxy, throttle curto e sair
            elif error_type in ('banned', 'captcha'):
                if proxy_lease_manager and username:
                    proxy_lease_manager.rotate(username, current_proxy, proxy_list, reason="banned")
                if state_manager:
                    state_manager.trigger_global_throttle(0.5)  # 30 segundos
                logger.warning(f"[Login] {error_type} para {username} — abortando + throttle 30s.")
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
                new_client, _ = create_session(proxy_list, user_agent,
                                               username=username)
                _new_id = ":".join(new_proxy.split(":")[:2])
                logger.info(f"[Proxy] ✅ Novo proxy via PLM: {_new_id} (motivo: {reason})")
                return new_proxy, new_client
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
        
        max_login_attempts = max(3, num_keys)
        
        new_client = None
        
        for login_attempt in range(max_login_attempts):
            # 2. Calcula o índice atual
            captcha_key_index = (base_captcha_index + login_attempt) % num_keys
            
            logger.info(f"[Login] Attempt {login_attempt + 1}/{max_login_attempts} (Using Key Index {captcha_key_index}, Process ID {process_id})")
            
            client = None
            for i in range(5):
                try:
                    # PROXY EXCLUSIVO: passa username para garantir 1 proxy : 1 user
                    client, proxy_raw = create_session(proxy_list, user_agent,
                                                       username=username)
                    if client is not None:
                        break
                except Exception as e:
                    logger.warning(f"[main] Session creation attempt {i+1}/5 failed: {e}")
                if i < 4:
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
                    if login_attempt < max_login_attempts - 1:
                        logger.info("Will retry with next API key index.")
                        await asyncio.sleep(5)
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
            except Exception as e:
                logger.exception(f"Login attempt {login_attempt + 1} failed with error: {e}")
                if login_attempt < max_login_attempts - 1:
                    logger.info("Will retry with next API key index.")
                    await asyncio.sleep(5)
        else:
            logger.error("Login failed after trying all available API keys. Marking as failed.")
            return False
    except Exception as e:
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
            # Nao adicionar users ja completos ou em progresso (CSV)
            if status in ("true", "success", "processing"):
                continue
            if self._r:
                try:
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
                    # Remover do KNOWN para que push_users o possa re-adicionar
                    self._r.srem(_WQ_KNOWN, username)
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

    def reset_for_reload(self):
        """
        Limpa apenas a lista de users CONHECIDOS que nao estao activos.
        Users em _WQ_ACTIVE nunca sao removidos — ficam protegidos.
        Isso permite re-adicionar users que voltaram a pending no CSV
        sem interferir com os que estao a ser processados agora.
        """
        if self._r:
            try:
                # Remover do KNOWN apenas os que NAO estao no ACTIVE
                # Assim podem ser re-avaliados no proximo push_users
                known = self._r.smembers(_WQ_KNOWN)
                active = self._r.smembers(_WQ_ACTIVE)
                to_remove = known - active
                if to_remove:
                    self._r.srem(_WQ_KNOWN, *to_remove)
            except Exception:
                pass
        else:
            with self._mem_lock:
                # Manter activos no known
                self._mem_known = self._mem_known & self._mem_active

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
    global logger, scraper_settings
    logger = setup_logging(process_id)
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
            logger.info(f"[Process-{process_id}] {username} em jail — devolvendo a queue")
            work_queue.repush_user(username)
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
            # Outro worker ja tomou este user (race condition) — ok, descartar
            logger.debug(f"[Process-{process_id}] {username} ja claimed por outro worker")
            return

        logger.info(f"[Process-{process_id}] 🔄 Claimed: {username}")

        max_user_attempts = 2
        final_status = 'failed_retry_later'

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
                else:
                    logger.warning(
                        f"[Process-{process_id}] ⚠️ Tentativa {attempt+1}/{max_user_attempts} "
                        f"falhou: {username}"
                    )

            except Exception as e:
                logger.error(f"[Process-{process_id}] ❌ Excecao para {username}: {e}")
                err = str(e).lower()
                if any(x in err for x in ("recaptchaerror", "http error 403", "garantir a possibilidade")):
                    state_manager.send_to_jail(username, duration_minutes=30)
                    final_status = 'banned_403' if "403" in err else 'blocked_site'
                    break
                if attempt < max_user_attempts - 1:
                    await asyncio.sleep(5)

        update_csv_status(username, final_status, credentials_file_path)

        # Liberta o proxy exclusivo deste utilizador
        if proxy_lease_manager:
            proxy_lease_manager.release(username)
            logger.info(
                f"[Process-{process_id}] 🔓 Proxy libertado: {username} "
                f"(status={final_status})"
            )

        # Se falhou mas pode tentar novamente, volta para a queue
        # repush_user() ja chama unmark_active() internamente
        if final_status not in ('true', 'success', 'banned_403', 'blocked_site'):
            work_queue.repush_user(username)
            logger.info(f"[Process-{process_id}] 🔁 {username} devolvido a queue para retry")
        else:
            # Sucesso ou ban permanente — remover do set activo
            work_queue.unmark_active(username)

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
        last_csv_reload = 0.0
        CSV_RELOAD_INTERVAL = 30.0  # recarrega CSV a cada 30s

        while True:
            try:
                # ── Throttle global ──────────────────────────────────────────
                if state_manager.check_global_throttle():
                    cycles = 0
                    while state_manager.check_global_throttle() and cycles < 60:
                        await asyncio.sleep(5)
                        cycles += 1
                    logger.info(
                        f"[Throttle] ✅ Throttle expirou apos {cycles * 5}s — retomando"
                    )
                    continue

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

                    # Verificar se ja foi concluido entretanto (por outro worker)
                    if status in ('true', 'success'):
                        logger.info(
                            f"[Process-{process_id}] {username} ja concluido — ignorando"
                        )
                        work_queue.mark_done(username)
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
                logger.info(
                    f"[Process-{process_id}] ▶️ Task iniciada: {username} "
                    f"({len(active_tasks)}/{max_concurrency} slots ocupados)"
                )

            except KeyboardInterrupt:
                logger.info(f"[Process-{process_id}] Interrompido pelo utilizador.")
                break
            except Exception as e:
                logger.error(f"[Process-{process_id}] Erro no loop: {e}")
                await asyncio.sleep(10)

        # Aguardar tasks activas terminarem antes de sair
        if active_tasks:
            logger.info(
                f"[Process-{process_id}] Aguardando {len(active_tasks)} tasks activas..."
            )
            await asyncio.gather(*active_tasks, return_exceptions=True)

    try:
        asyncio.run(worker_async_loop())
    except KeyboardInterrupt:
        pass


def validate_files_and_config(working_dir: str, scraper_settings: Dict) -> tuple:
    """Validate all required files exist and load data."""
    import pandas as pd
    
    proxies_file = os.path.join(working_dir, scraper_settings['proxy_file_path'])
    if not os.path.exists(proxies_file):
        raise FileNotFoundError(f"Proxy file {scraper_settings['proxy_file_path']} not found.")
    
    try:
        with open(proxies_file, "r", encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        proxy_list = []
        for line in lines:
            clean_line = line.strip()
            if clean_line and clean_line.count(':') >= 3:
                proxy_list.append(clean_line)
    except Exception as e:
        raise ValueError(f"Erro critico ao ler arquivo de proxies: {e}")

    if not proxy_list:
        raise ValueError("No valid proxies found.")

    proxy_list = [p for p in proxy_list if p]
    logger.info(f"🚀 LOADED {len(proxy_list)} VALID PROXIES.")

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

        # ── Carregar proxies e CSV ────────────────────────────────────────────
        proxy_list, df, credentials_file = validate_files_and_config(
            WORKING_DIR, scraper_settings
        )
        total_users = len(df)
        logger.info(f"📋 {total_users} utilizadores carregados do CSV.")

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

        # ── Definir numero de workers ─────────────────────────────────────────
        # Usar o minimo entre: cpu_count, users pendentes, max configurado
        pending_users = df[
            ~df['status'].isin(['true', 'success', 'processing'])
        ].shape[0]
        max_workers_cfg = scraper_settings.get('max_workers', 8)
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

        proxy_chunks = _chunkify(proxy_list, max_workers)
        logger.info(
            f"🔌 Proxy chunks: {[len(c) for c in proxy_chunks]} "
            f"({len(proxy_list)} total)"
        )

        # ── Lancar workers ────────────────────────────────────────────────────
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            future_to_id = {
                executor.submit(
                    worker,
                    pc,           # proxy_chunk (SEM user_chunk!)
                    i,            # process_id
                    credentials_file,
                    scraper_settings,
                    10,           # check_interval (segundos de BLPOP timeout)
                    max_workers,
                ): i
                for i, pc in enumerate(proxy_chunks)
            }
            logger.info(
                f"✅ {max_workers} workers iniciados em modo Dynamic Work Queue."
            )

            # Monitorizar processos continuamente
            while True:
                try:
                    time.sleep(30)

                    # Verificar se ainda ha trabalho
                    if _r_init:
                        pending_q = _r_init.llen(_WQ_PENDING)
                        logger.info(
                            f"[Monitor] Queue: {pending_q} users pendentes | "
                            f"Workers: {sum(1 for f in future_to_id if not f.done())} activos"
                        )

                    # Reiniciar workers que crasharam
                    for fut, pid in list(future_to_id.items()):
                        if fut.done():
                            exc = fut.exception()
                            if exc:
                                logger.error(
                                    f"[Monitor] ❌ Worker {pid} crashou: {exc} — reiniciando"
                                )
                                pc = proxy_chunks[pid] if pid < len(proxy_chunks) else proxy_chunks[0]
                                new_fut = executor.submit(
                                    worker, pc, pid,
                                    credentials_file, scraper_settings,
                                    10, max_workers
                                )
                                future_to_id[new_fut] = pid
                                del future_to_id[fut]

                except KeyboardInterrupt:
                    logger.info("⛔ Interrompido. Aguardando workers terminarem...")
                    break

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
    
    # Executar a funcao principal
    main_execution_continuous()