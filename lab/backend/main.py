"""API inicial de pedidos. Almacenamiento en memoria solo para pruebas locales.

Antes de usar múltiples instancias, sustituir ORDERS por almacenamiento compartido.
"""

import json
import math
import os
import random
import threading
import time
import uuid

ORDERS = {}
LOCK = threading.Lock()


def dispatch(request):
    parts = request.path.strip('/').split('/')
    payload = request.get_json(silent=True)
    attributes = payload if isinstance(payload, dict) else {}
    if parts == ['orders'] and request.method == 'POST':
        amount = attributes.get('amount')
        if (
            not isinstance(amount, (int, float)) or isinstance(amount, bool)
            or not math.isfinite(amount) or amount <= 0
            or attributes.get('category') not in ('electronics', 'books', 'clothing')
            or attributes.get('customer_tier') not in ('standard', 'premium')
        ):
            return {'error': 'invalid_payload'}, 400, attributes
        order = {key: attributes[key] for key in ('amount', 'category', 'customer_tier')}
        order.update(id=str(uuid.uuid4()), status='created')
        with LOCK:
            ORDERS[order['id']] = order
        return dict(order), 201, order

    is_get = len(parts) == 2 and request.method == 'GET'
    is_cancel = len(parts) == 3 and parts[2] == 'cancel' and request.method == 'POST'
    if parts[0] == 'orders' and (is_get or is_cancel):
        with LOCK:
            order = ORDERS.get(parts[1])
            if order is None:
                return {'error': 'order_not_found'}, 404, attributes
            if is_cancel:
                if order['status'] == 'cancelled':
                    return {'error': 'invalid_state'}, 409, dict(order)
                order['status'] = 'cancelled'
            return dict(order), 200, dict(order)
    return {'error': 'route_not_found'}, 404, attributes


def handle(request):
    """Entrada HTTP usada por Functions Framework y Cloud Run functions."""
    started = time.perf_counter()
    request_id = request.headers.get('X-Request-ID') or str(uuid.uuid4())
    payload = request.get_json(silent=True)
    attributes = payload if isinstance(payload, dict) else {}
    try:
        time.sleep(max(0, float(os.getenv('EXTRA_LATENCY_MS', '0'))) / 1000)
        if random.random() < float(os.getenv('FAILURE_RATE', '0.02')):
            body, status = {'error': 'simulated_failure'}, 500
        else:
            body, status, attributes = dispatch(request)
    except Exception:
        body, status = {'error': 'internal_error'}, 500
    outcome = 'server_error' if status >= 500 else 'client_error' if status >= 400 else 'success'
    print(json.dumps({
        'severity': 'ERROR' if status >= 500 else 'WARNING' if status >= 400 else 'INFO',
        'message': 'request_completed',
        'request_id': request_id,
        'endpoint': request.path,
        'status_code': status,
        'outcome': outcome,
        'error_type': body.get('error'),
        'latency_ms': round((time.perf_counter() - started) * 1000, 3),
        'customer_tier': attributes.get('customer_tier'),
        'category': attributes.get('category'),
        'amount': attributes.get('amount'),
    }), flush=True)
    return json.dumps(body), status, {'Content-Type': 'application/json', 'X-Request-ID': request_id}
