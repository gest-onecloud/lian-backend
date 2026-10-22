"""Deterministic test policy: external network is forbidden, loopback is allowed."""
import socket
import os
import pytest

_orig_connect=socket.socket.connect
_orig_getaddrinfo=socket.getaddrinfo


def _is_local(host):
    return str(host).lower() in ('127.0.0.1','localhost','::1')

def _guard_connect(self,address):
    host=address[0] if isinstance(address,tuple) and address else ''
    if _is_local(host): return _orig_connect(self,address)
    raise RuntimeError('external network disabled during tests; use provider mocks')

def _guard_getaddrinfo(host,*args,**kwargs):
    if _is_local(host): return _orig_getaddrinfo(host,*args,**kwargs)
    raise socket.gaierror(socket.EAI_AGAIN,'external DNS disabled during tests')

@pytest.fixture(autouse=True,scope='session')
def block_external_network():
    os.environ['LIAN_TEST_MODE']='1'
    socket.socket.connect=_guard_connect
    socket.getaddrinfo=_guard_getaddrinfo
    try: yield
    finally:
        socket.socket.connect=_orig_connect
        os.environ.pop('LIAN_TEST_MODE',None)
        socket.getaddrinfo=_orig_getaddrinfo
