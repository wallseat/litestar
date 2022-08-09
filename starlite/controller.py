import inspect
from copy import copy
from typing import TYPE_CHECKING, Dict, List, Optional, Union, cast

from starlite.handlers import BaseRouteHandler
from starlite.utils import normalize_path

if TYPE_CHECKING:
    from typing import Type

    from pydantic.fields import FieldInfo

    from starlite.datastructures import Cookie, ResponseHeader
    from starlite.provide import Provide
    from starlite.response import Response
    from starlite.router import Router
    from starlite.types import (
        AfterRequestHandler,
        AfterResponseHandler,
        BeforeRequestHandler,
        ExceptionHandler,
        Guard,
        Middleware,
    )


class Controller:
    """
    The Starlite Controller class is the basic 'view' component of Starlite.

    Subclass Controller to use OOP based route handling.
    """

    __slots__ = (
        "after_request",
        "after_response",
        "before_request",
        "dependencies",
        "exception_handlers",
        "guards",
        "middleware",
        "owner",
        "parameters",
        "path",
        "response_class",
        "response_cookies",
        "response_headers",
        "tags",
    )

    after_request: Optional["AfterRequestHandler"]
    """
        A sync or async function executed before a [Request][starlite.connection.Request] is passed to any route handler.
        If this function returns a value, the request will not reach the route handler, and instead this value will be used.
    """
    after_response: Optional["AfterResponseHandler"]
    """
        A sync or async function called after the response has been awaited.
        It receives the [Request][starlite.connection.Request] instance and should not return any values.
    """
    before_request: Optional["BeforeRequestHandler"]
    """
        A sync or async function called immediately before calling the route handler.
        It receives the [Request][starlite.connection.Request] instance and any
        non-`None` return value is used for the response, bypassing the route handler.
    """
    dependencies: Optional[Dict[str, "Provide"]]
    """
        A string/[Provider][starlite.provide.Provide] dictionary that maps dependency providers.
    """
    exception_handlers: Optional[Dict[Union[int, "Type[Exception]"], "ExceptionHandler"]]
    """
        A dictionary that maps handler functions to status codes and/or exception types.
    """
    guards: Optional[List["Guard"]]
    """
        A list of [Guard][starlite.types.Guard] callables.
    """
    middleware: Optional[List["Middleware"]]
    """
        A list of [Middleware][starlite.types.Middleware].
    """
    owner: "Router"
    """
        The [Router][starlite.router.Router] or [Starlite][starlite.app.Starlite] app that owns the controller.
        This value is set internally by Starlite and it should not be set when subclassing the controller.
    """
    parameters: Optional[Dict[str, "FieldInfo"]]
    """
        A mapping of [Parameter][starlite.params.Parameter] definitions available to all application paths.
    """
    path: str
    """
        A path fragment for the controller.
        All route handlers under the controller will have the fragment appended to them.
        If not set it defaults to '/'.
    """
    response_class: Optional["Type[Response]"]
    """
        A custom subclass of [starlite.response.Response] to be used as the default response
        for all route handlers under the controller.
    """
    response_cookies: Optional[List["Cookie"]]
    """
        A list of [Cookie](starlite.datastructures.Cookie] instances.
    """
    response_headers: Optional[Dict[str, "ResponseHeader"]]
    """
        A string keyed dictionary mapping [ResponseHeader][starlite.datastructures.ResponseHeader] instances.
    """
    tags: Optional[List[str]]
    """
        A list of string tags that will be appended to the schema of all route handlers under the controller.
    """

    def __init__(self, owner: "Router"):
        for key in self.__slots__:
            if not hasattr(self, key):
                setattr(self, key, None)

        self.path = normalize_path(self.path or "/")
        self.owner = owner
        self._unbind_lifecycle_hook_functions()

    def _unbind_lifecycle_hook_functions(self) -> None:
        """
        Functions assigned to class variables will be bound as instance methods on instantiation of the controller.
        Left unchecked, this results in a `TypeError` when the handlers are called as any function satisfying the type
        annotation of the lifecycle hook attributes can only receive a single positional argument, but will receive two
        positional arguments if called as an instance method (`self` and the hook argument)`.

        Overwrites the bound method with the original function.
        """
        for hook_key in ("after_request", "after_response", "before_request"):
            hook_class_var = getattr(type(self), hook_key, None)
            if not hook_class_var:
                continue
            if inspect.isfunction(hook_class_var):
                setattr(self, hook_key, hook_class_var)

    def get_route_handlers(self) -> List["BaseRouteHandler"]:
        """
        Returns a list of route handlers defined on the controller
        """
        route_handlers: List["BaseRouteHandler"] = []
        route_handler_fields = [
            f_name
            for f_name in dir(self)
            if f_name not in dir(Controller) and isinstance(getattr(self, f_name), BaseRouteHandler)
        ]
        for f_name in route_handler_fields:
            source_route_handler = cast("BaseRouteHandler", getattr(self, f_name))
            route_handler = copy(source_route_handler)
            route_handler.owner = self
            route_handlers.append(route_handler)
        return route_handlers
