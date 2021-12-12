from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Type, Union, cast

from pydantic import BaseModel, Extra, Field, validator
from starlette.responses import Response
from starlette.status import HTTP_200_OK, HTTP_201_CREATED, HTTP_204_NO_CONTENT
from typing_extensions import Literal

from starlite.controller import Controller
from starlite.enums import HttpMethod, MediaType
from starlite.exceptions import ImproperlyConfiguredException
from starlite.provide import Provide

if TYPE_CHECKING:  # pragma: no cover
    from starlite.routing import Router


class RouteHandler(BaseModel):
    class Config:
        arbitrary_types_allowed = True
        extra = Extra.allow

    http_method: Union[HttpMethod, List[HttpMethod]]
    status_code: Optional[int] = None
    include_in_schema: Optional[bool] = None
    media_type: Optional[MediaType] = None
    name: Optional[str] = None
    path: Optional[str] = None
    response_class: Optional[Type[Response]] = None
    response_headers: Optional[Union[dict, BaseModel]] = None
    dependencies: Optional[Dict[str, Provide]] = None

    fn: Optional[Callable] = None
    owner: Optional[Union[Controller, "Router"]] = None

    def __call__(self, *args, **kwargs) -> Any:
        """
        If wrapper is None, set fn from args[0], otherwise, call fn and pass the *args and **kwargs to it
        """
        if self.fn:
            if isinstance(self.owner, Controller):
                return self.fn(self.owner, *args, **kwargs)
            return self.fn(*args, **kwargs)
        self.fn = cast(Callable, args[0])
        return self

    def __eq__(self, other: Any) -> bool:
        try:
            return super().__eq__(other) and self.fn == other.fn
        except (AttributeError, ValueError):
            return False

    @validator("http_method", always=True, pre=True)
    def validate_http_method(  # pylint: disable=no-self-argument,no-self-use
        cls, value: Union[HttpMethod, List[HttpMethod]]
    ) -> Union[HttpMethod, List[HttpMethod]]:
        """Validates that a given value is an HttpMethod enum member or list thereof"""
        if isinstance(value, list):
            if len(value) == 1:
                value = value[0]
            elif value == 0:
                raise ValueError("An http_method parameter is required")
        return value

    @validator("status_code", always=True)
    def validate_status_code(  # pylint: disable=no-self-argument,no-self-use
        cls, value: Optional[int], values: Dict[str, Any]
    ) -> int:
        """
        Validates that status code is set for lists of 2 or more HttpMethods,
        and sets default for other cases where the status_code is not set.
        """
        if value:
            return value

        http_method = values.get("http_method")
        if not http_method:
            raise ValueError("http_method is not set")
        if isinstance(http_method, list):
            raise ValueError("When defining multiple methods for a given path, a status_code is required")
        if http_method == HttpMethod.POST:
            return HTTP_201_CREATED
        if http_method == HttpMethod.DELETE:
            return HTTP_204_NO_CONTENT
        return HTTP_200_OK

    @validator("response_class")
    def validate_response_class(  # pylint: disable=no-self-argument,no-self-use
        cls, value: Any
    ) -> Optional[Type[Response]]:
        """
        Valides that value is either None or subclass of Starlette Response
        """
        if value is None or issubclass(value, Response):
            return value
        raise ValueError("response_class must be a sub-class of starlette.responses.Response")

    @property
    def http_methods(self) -> List[HttpMethod]:
        """
        Returns a list of the RouteHandler's HttpMethod members
        """
        return self.http_method if isinstance(self.http_method, list) else [self.http_method]

    def resolve_dependencies(self) -> Dict[str, Provide]:
        """
        Returns all dependencies that exist in the given handler's scopes
        """
        dependencies_list: List[Dict[str, Provide]] = []
        if self.dependencies:
            dependencies_list.append(self.dependencies)
        cur = self.owner
        while cur is not None:
            if cur.dependencies:
                dependencies_list.append(cur.dependencies)
            cur = cur.owner
        injectables: List[Provide] = []
        resolved_dependencies: Dict[str, Provide] = {}
        for dependencies_dict in dependencies_list:
            for key, value in dependencies_dict.items():
                if key not in resolved_dependencies:
                    if value in injectables:
                        raise ImproperlyConfiguredException(f"injectable dependency with key {key} is already defined")
                    injectables.append(value)
                    resolved_dependencies[key] = value
        return resolved_dependencies


route = RouteHandler


class get(RouteHandler):
    http_method: Literal[HttpMethod.GET] = Field(default=HttpMethod.GET)


class post(RouteHandler):
    http_method: Literal[HttpMethod.POST] = Field(default=HttpMethod.POST)


class put(RouteHandler):
    http_method: Literal[HttpMethod.PUT] = Field(default=HttpMethod.PUT)


class patch(RouteHandler):
    http_method: Literal[HttpMethod.PATCH] = Field(default=HttpMethod.PATCH)


class delete(route):
    http_method: Literal[HttpMethod.DELETE] = Field(default=HttpMethod.DELETE)
