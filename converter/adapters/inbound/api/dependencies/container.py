from typing import Any, cast

from fastapi import Request

from converter.shared.di import Container


def get_container_dependency(request: Request) -> Container:
    app_state: Any = request.app.state

    return cast(Container, app_state.container)
