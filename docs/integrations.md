# Project Integrations

## Stock UMKM (Laravel) & POS Cashier (Next.js)

- **Product & Inventory Lookup**: POS Cashier queries `GET /api/v1/integrations/stock-umkm/products` and `GET /api/v1/integrations/stock-umkm/inventory` using a backend API key with `inventory:read` scope.
- **Event Publication**: Stock UMKM publishes committed events (`inventory.updated`) to `POST /api/v1/integrations/stock-umkm/events` with a unique `event_id`.
- **Idempotency**: Duplicate deliveries with the same `event_id` are detected via `integration_events` and safely acknowledged without duplicating downstream state changes or webhook deliveries.

## ESP32, Mosquitto MQTT, and Prometheus

- Topic convention: `pap/iot/{device_id}/telemetry`, `pap/iot/{device_id}/status`, `pap/iot/{device_id}/command`, `pap/iot/{device_id}/config`.
- Validated telemetry updates bounded-label Prometheus gauges (`pap_iot_device_temperature_celsius`, `pap_iot_device_counter_value`, `pap_iot_device_current_amperes`) exposed at `/metrics`.
- Grafana queries Prometheus (`:9001`) directly; applications requiring controlled metrics access query PAP's `/api/v1/metrics/prometheus/*` endpoints.

