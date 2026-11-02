"""Literal SDK API declaration; resolving it does not start a server."""

from scitex_sdk.app.api_plugin import (
    ApiError,
    ApiField,
    ApiPlugin,
    ApiRoute,
    ApiSchema,
    AuthScope,
    RateLimit,
)

plugin = ApiPlugin(
    id="scitex-sdk",
    title="SciTeX SDK",
    api_version="1",
    routes=(
        ApiRoute(
            path="skills",
            methods=("GET",),
            rate=RateLimit(rate_class="free", compute_cost="low"),
            response=ApiSchema(
                name="BundledSdkSkills",
                fields=(
                    ApiField(name="package", enum=("scitex-sdk",)),
                    ApiField(
                        name="skills",
                        type="object",
                        description="Relative skill IDs grouped by scitex-sdk, scitex-app and scitex-ui.",
                    ),
                ),
            ),
            errors=(
                ApiError(
                    code="method_not_allowed",
                    status=405,
                    message="Use GET for the bundled skills catalog.",
                ),
                ApiError(
                    code="bundled_skills_unavailable",
                    status=503,
                    message="Bundled SDK skill resources are unavailable.",
                ),
            ),
            auth=AuthScope(public=True, project_scope="none"),
            handler="scitex_sdk._web._views:bundled_skills",
            read_only=True,
        ),
    ),
)
