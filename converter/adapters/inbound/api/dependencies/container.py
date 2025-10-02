from typing import Any

from fastapi import Request

from converter.shared.di import Container


def get_container_dependency(request: Request) -> Container:
    app_state: Any = request.app.state  # type: ignore

    return app_state.container
