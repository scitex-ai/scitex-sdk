#!/usr/bin/env python3
"""``{% scitex_panes %}``: panes side by side on desktop, one per screen on phones.

    {% load i18n scitex_panes %}
    {% scitex_panes "figrecipe" columns="280px 1fr 320px" %}
      {% scitex_pane "data" label=_("Data") icon="📊" order=1 %}…{% endscitex_pane %}
      {% scitex_pane "plot" label=_("Plot") icon="📈" order=2 %}…{% endscitex_pane %}
    {% endscitex_panes %}

The wrapper loads ``css/app/panes.css`` and ``js/app/panes.js``; the script
builds the phone tab bar and exposes ``window.stxPanes.show("plot")``.
``layout="app"`` keeps the app's own desktop layout instead of the grid.
"""

from __future__ import annotations

from django import template
from django.utils.html import format_html, format_html_join

from .scitex_static import versioned_static

register = template.Library()


def _resolve(kwargs, context):
    return {key: value.resolve(context) for key, value in kwargs.items()}


def _split(parser, token, allowed):
    bits = token.split_contents()
    name, rest = bits[0], bits[1:]
    if not rest:
        raise template.TemplateSyntaxError(f"{name} needs an id as its first argument")
    ident = parser.compile_filter(rest[0])
    kwargs = template.base.token_kwargs(rest[1:], parser, support_legacy=False)
    if len(kwargs) != len(rest) - 1:
        raise template.TemplateSyntaxError(f"{name} takes key=value arguments after the id")
    unknown = set(kwargs) - set(allowed)
    if unknown:
        raise template.TemplateSyntaxError(f"{name} got unknown arguments: {sorted(unknown)}")
    return ident, kwargs


class PanesNode(template.Node):
    def __init__(self, app, kwargs, nodelist):
        self.app, self.kwargs, self.nodelist = app, kwargs, nodelist

    def render(self, context):
        options = _resolve(self.kwargs, context)
        css = " ".join(filter(None, ("stx-panes", options.get("css_class"))))
        attrs = [("class", css), ("data-stx-panes", self.app.resolve(context))]
        if options.get("active"):
            attrs.append(("data-stx-active", options["active"]))
        if options.get("layout"):
            attrs.append(("data-stx-panes-layout", options["layout"]))
        if options.get("columns"):
            attrs.append(("style", f"--stx-panes-columns: {options['columns']}"))
        return format_html(
            '<link rel="stylesheet" href="{}">\n<div {}>{}</div>\n'
            '<script type="module" src="{}"></script>',
            versioned_static("scitex_sdk/ui/css/app/panes.css"),
            format_html_join(" ", '{}="{}"', attrs),
            self.nodelist.render(context),
            versioned_static("scitex_sdk/ui/js/app/panes.js"),
        )


class PaneNode(template.Node):
    def __init__(self, ident, kwargs, nodelist):
        self.ident, self.kwargs, self.nodelist = ident, kwargs, nodelist

    def render(self, context):
        options = _resolve(self.kwargs, context)
        ident = self.ident.resolve(context)
        attrs = [
            ("data-stx-pane", ident),
            ("data-stx-label", options.get("label") or ident),
        ]
        if options.get("icon"):
            attrs.append(("data-stx-icon", options["icon"]))
        if options.get("order") not in (None, ""):
            attrs.append(("data-stx-order", options["order"]))
        if options.get("css_class"):
            attrs.append(("class", options["css_class"]))
        return format_html(
            "<section {}>{}</section>",
            format_html_join(" ", '{}="{}"', attrs),
            self.nodelist.render(context),
        )


@register.tag("scitex_panes")
def scitex_panes(parser, token):
    app, kwargs = _split(parser, token, ("columns", "active", "layout", "css_class"))
    nodelist = parser.parse(("endscitex_panes",))
    parser.delete_first_token()
    return PanesNode(app, kwargs, nodelist)


@register.tag("scitex_pane")
def scitex_pane(parser, token):
    ident, kwargs = _split(parser, token, ("label", "icon", "order", "css_class"))
    nodelist = parser.parse(("endscitex_pane",))
    parser.delete_first_token()
    return PaneNode(ident, kwargs, nodelist)


# EOF
