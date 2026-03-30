#!/usr/bin/env node

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { registerPrompts } from "./api/prompts.js";
import { registerTools } from "./api/tools.js";

const server = new Server(
  {
    name: "forgewright-mcp",
    version: "1.0.0",
  },
  {
    capabilities: {
      prompts: {},
      tools: {},
    },
  }
);

registerPrompts(server);
registerTools(server);

async function run() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("Forgewright Native MCP Server running on stdio");
}

run().catch((error) => {
  console.error("Failed to start server:", error);
  process.exit(1);
});
