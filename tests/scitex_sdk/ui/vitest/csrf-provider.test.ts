/** Project providers send the rendered token through actual HTTP requests. */
import { createServer } from "node:http";
import { afterEach, expect, it } from "vitest";
import { httpProjectProvider as sourceProvider } from "../../../../src/scitex_sdk/ui/static/scitex_sdk/ui/ts/app/project-selector/provider";
import { httpProjectProvider as shippedProvider } from "../../../../src/scitex_sdk/ui/static/scitex_sdk/ui/js/app/project-selector.js";

const httpProjectProvider = process.env.STX_PICKER_TEST_RUNTIME === "shipped" ? shippedProvider : sourceProvider;
const servers: ReturnType<typeof createServer>[] = [];
afterEach(async () => {
  document.body.innerHTML = "";
  await Promise.all(servers.splice(0).map(server => new Promise<void>(done => {
    server.closeAllConnections(); server.close(() => done());
  })));
});

it.each(["project", "scope"])("%s persistence sends the rendered Django token", async (mode) => {
  // Arrange
  document.body.innerHTML = '<input type="hidden" name="csrfmiddlewaretoken" value="rendered-token">';
  const headers: unknown[] = [];
  const server = createServer(async (request, response) => {
    response.setHeader("Content-Type", "application/json");
    if (request.method === "GET") {
      response.end(JSON.stringify({projects: [{id: "owned", name: "Owned"}], current: "owned", current_scope: "project", allow_user_scope: true}));
      return;
    }
    headers.push(request.headers["x-csrftoken"]);
    const chunks = []; for await (const chunk of request) chunks.push(chunk);
    const body = JSON.parse(Buffer.concat(chunks).toString());
    response.statusCode = request.headers["x-csrftoken"] === "rendered-token" ? 200 : 403;
    response.end(JSON.stringify({current_scope: body.scope, current: body.id}));
  });
  servers.push(server);
  await new Promise<void>(done => server.listen(0, "127.0.0.1", done));
  const address = server.address() as {port: number};
  const provider = httpProjectProvider(`http://127.0.0.1:${address.port}/projects`, {allowUserScope: mode === "scope"});
  await provider.listProjects();
  // Act
  const persisted = mode === "scope"
    ? provider.rememberScope!({scope: "project", id: "owned"})
    : provider.rememberProject!("owned");
  // Assert
  await expect(persisted.then(() => headers)).resolves.toEqual(["rendered-token"]);
});
