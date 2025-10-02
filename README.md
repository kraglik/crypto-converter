# Crypto Currency Conversion Estimator

This project provides currency conversion estimates based on Binance API rates, updated once every 30 seconds.


## Prerequisites

- docker-compose

## Quick Start

1.  **Create an environment file:**
    Use `.env.example` as a basis for a new `.env` file in the project root.
    ```bash
    POSTGRES_PASSWORD=postgres_dev
    API_USER_PASSWORD=api_dev_pass
    CONSUMER_USER_PASSWORD=consumer_dev_pass
    ```

2.  **Start the services:**
    ```bash
    docker-compose up --build
    ```

3.  **Check Service Health:**
    ```bash
    curl http://localhost:8000/health
    ```

4.  **Get conversion estimates:**
    Give `quote-consumer` 30-40 seconds to fetch latest rates.
    ```bash
    curl -G http://localhost:8000/convert \
      --data-urlencode "from=BTC" \
      --data-urlencode "to=USDT" \
      --data-urlencode "amount=1.5"
    ```

For more details about its API, visit [API Reference](./docs/api_reference.md).

## Architecture

This project uses Hexagonal Architecture with CQRS.
For detailed description, please see the [Architecture](./docs/architecture.md) page.

To run all tests:
```bash
./scripts/test.sh
```

## Development

For development, Python 3.13 installation is required.
This project uses Poetry (v.2.2.1 in `docker/app/Dockerfile`).
