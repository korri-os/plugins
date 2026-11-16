#!/usr/bin/env python3
"""A paired GameStream client that falls silent during TLS close (korri#443).

It asks Sunshine's HTTPS port for serverinfo, reads the answer and
Sunshine's close_notify, and then stops: it never sends its own close_notify
and keeps its TCP connection open. A handheld that sleeps on Wi-Fi in the
middle of a close looks like this to Sunshine.

Usage: test-https-silent-peer.py HOST PORT CERT KEY READY_FILE HOLD_SECONDS

READY_FILE is written once Sunshine has sent its close_notify, which is the
moment Sunshine starts to close the connection. A TCP close without
close_notify fails the script, so the check also proves that Sunshine still
closes TLS properly.
"""

import pathlib
import socket
import ssl
import sys
import time


def main() -> None:
    host, port, cert, key, ready, hold = sys.argv[1:]
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    context.load_cert_chain(cert, key)

    raw = socket.create_connection((host, int(port)), timeout=30)
    # A bare TCP close raises SSLEOFError instead of reading as b"".
    peer = context.wrap_socket(raw, suppress_ragged_eofs=False)
    peer.sendall(b"GET /serverinfo?uniqueid=0123456789ABCDEF HTTP/1.1\r\nHost: sunshine\r\n\r\n")

    answer = b""
    while True:
        chunk = peer.recv(65536)
        if not chunk:
            # Sunshine's close_notify. OpenSSL does not answer it unless the
            # application calls SSL_shutdown, and this peer never does.
            break
        answer += chunk
    if b"<PairStatus>1</PairStatus>" not in answer:
        sys.exit(f"the silent peer is not paired: {answer!r}")

    pathlib.Path(ready).write_text("silent\n")
    time.sleep(float(hold))
    # Keep both objects alive until here, so nothing closes the socket early.
    del peer, raw


if __name__ == "__main__":
    main()
