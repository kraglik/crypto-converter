# API Reference

The Crypto Converter API provides endpoints for currency conversion and health checks.

**Base URL**: `http://localhost:8000`

---

## Endpoints

### Convert Currency

Performs a currency conversion based on the most recent available rates. For historical conversions, a `timestamp` can be provided.

- **Endpoint**: `GET /convert`
- **Method**: `GET`
- **Success Response**: `200 OK`

#### Query Parameters

| Parameter   | Type   | Description                                                                                            | Required | Example                |
|-------------|--------|--------------------------------------------------------------------------------------------------------|----------|------------------------|
| `from`      | string | The currency code to convert from.                                                                     | Yes      | `BTC`                  |
| `to`        | string | The currency code to convert to.                                                                       | Yes      | `USDT`                 |
| `amount`    | number | The amount of the `from` currency to convert. Must be greater than 0.                                  | Yes      | `1.5`                  |
| `timestamp` | string | Optional ISO 8601 timestamp (UTC) for a historical conversion. Cannot be in the future or > 7 days old. | No       | `2025-10-02T10:00:00Z` |

#### Example Request

Latest:
```bash
curl -G http://localhost:8000/convert \
  --data-urlencode "from=BTC" \
  --data-urlencode "to=USDT" \
  --data-urlencode "amount=1.5"
```

With timestamp reference:
```bash
curl -G http://localhost:8000/convert \
  --data-urlencode "from=BTC" \
  --data-urlencode "to=USDT" \
  --data-urlencode "amount=1.5"
  --data-urlencode "timestamp=2025-10-02T19:43:00Z"
```

#### Example Success Response

```json
{
  "amount": "99375.75000000",
  "rate": "66250.50000000",
  "timestamp": "2025-10-02T10:30:05.123Z"
}
```

#### Error Responses

**404 Not Found**: Returned if no quote is available for the requested currency pair.

```json
{
  "detail": "No quote found for pair BTCXYZ"
}
```

**422 Unprocessable Entity**: Returned for validation errors (e.g., amount is 0, future timestamp) or if the found quote is too stale.

```json
{
  "detail": "Quote for BTCUSDT is too old: 75.2s old"
}
```

**400 Bad Request**: Returned for invalid domain-level values, like malformed currency codes.

---

### Health Check

Checks the status of both API and its downstream dependencies (PostgreSQL, Redis).

- **Endpoint**: `GET /health`
- **Method**: `GET`

#### Example Healthy Response

```json
{
  "status": "healthy",
  "checks": {
    "postgres": {
      "status": "healthy",
      "error": null
    },
    "redis": {
      "status": "healthy",
      "error": null
    }
  }
}
```

#### Example Unhealthy Response

```json
{
  "status": "unhealthy",
  "checks": {
    "postgres": {
      "status": "unhealthy",
      "error": "connection failed"
    },
    "redis": {
      "status": "healthy",
      "error": null
    }
  }
}
```
