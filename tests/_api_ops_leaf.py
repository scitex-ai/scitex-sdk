"""A tiny leaf declaring operations, for the API operation-layer tests."""

from scitex_sdk.app.api_exec import ApiJob, ApiPage, ApiProblem
from scitex_sdk.app.api_ops import ApiOperation, build_plugin
from scitex_sdk.app.api_plugin import ApiField, ApiSchema

ITEMS = [{"id": f"n{i}", "title": f"Note {i}"} for i in range(5)]
CALLS = []

OPERATIONS = (
    ApiOperation(
        "notes",
        "notes",
        "list",
        f"{__name__}:list_notes",
        summary="Search notes",
        params=(ApiField("q", "string", False, "Text query"),),
        paginated=True,
        default_limit=2,
        max_limit=3,
    ),
    ApiOperation("notes", "notes", "get", f"{__name__}:get_note", summary="One note"),
    ApiOperation(
        "notes",
        "notes",
        "create",
        f"{__name__}:create_note",
        params=(ApiField("title", "string", True),),
        project_scoped=True,
    ),
    ApiOperation(
        "notes",
        "notes",
        "archive",
        f"{__name__}:archive_note",
        item=True,
        response=ApiSchema("Job", (ApiField("id"), ApiField("state"))),
    ),
)
PLUGIN = build_plugin("notes", "Notes API", "1", OPERATIONS)


def list_notes(call):
    CALLS.append(("list", call.params))
    found = [n for n in ITEMS if call.params.get("q", "") in n["title"]]
    page = found[call.offset : call.offset + call.limit]
    return ApiPage(
        page, has_more=call.offset + len(page) < len(found), total=len(found)
    )


def get_note(call):
    for note in ITEMS:
        if note["id"] == call.id:
            return note
    raise ApiProblem(404, "notes.not_found", "no such note")


def create_note(call):
    CALLS.append(("create", call.project.id, call.params["title"]))
    return {"id": "n9", "title": call.params["title"], "project": call.project.id}


def archive_note(call):
    return ApiJob({"id": "job_1", "status": "queued"})
