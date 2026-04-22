import { mkdir, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";

const endpoint =
  process.env.REPO_MCP_ENDPOINT ??
  "https://mcp-147298850620.us-central1.run.app/mcp";

const projectId = process.env.REPO_MEMORY_PROJECT_ID ?? "CHP";
const outputPath = resolve(".codex", "memory.latest.json");

async function callMcp(method, params = {}, id = 1) {
  const response = await fetch(endpoint, {
    method: "POST",
    headers: {
      "content-type": "application/json",
      accept: "application/json, text/event-stream",
    },
    body: JSON.stringify({ jsonrpc: "2.0", id, method, params }),
  });

  if (!response.ok) {
    throw new Error(`MCP ${method} failed: ${response.status} ${response.statusText}`);
  }

  const text = await response.text();
  const dataLine = text.split(/\r?\n/).find((line) => line.startsWith("data: "));

  if (!dataLine) {
    throw new Error(`MCP ${method} response did not include a data event.`);
  }

  return JSON.parse(dataLine.slice("data: ".length));
}

await callMcp(
  "initialize",
  {
    protocolVersion: "2025-03-26",
    capabilities: {},
    clientInfo: { name: "repo-startup", version: "1.0.0" },
  },
  1,
);

const memory = await callMcp(
  "tools/call",
  {
    name: "memory_search",
    arguments: {
      project_id: projectId,
      query: "",
    },
  },
  2,
);

await mkdir(dirname(outputPath), { recursive: true });
await writeFile(outputPath, `${JSON.stringify(memory, null, 2)}\n`, "utf8");

const contentText = memory?.result?.content?.[0]?.text ?? "{\"results\":[]}";
const entries = JSON.parse(contentText).results ?? [];

console.log(`Loaded ${entries.length} memory entries from project ${projectId}.`);
console.log(`Saved to ${outputPath}`);
