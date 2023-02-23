from pathlib import Path

from starlite import Starlite
from starlite.config.template import TemplateConfig
from starlite.contrib.jinja import JinjaTemplateEngine

app = Starlite(
    route_handlers=[],
    template_config=TemplateConfig(
        directory=Path("templates"),
        engine=JinjaTemplateEngine,
    ),
)