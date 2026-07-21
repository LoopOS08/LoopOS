"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"

export default function MCPPage() {
  const [servers, setServers] = useState<any[]>([])
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({
    name: "",
    url: "",
    transport_type: "sse",
    command: "",
    auth_token: "",
    polling_interval_minutes: 60,
  })

  const addServer = () => {
    setServers([
      ...servers,
      {
        id: Date.now().toString(),
        ...form,
        status: "disconnected",
        discovered_tools: [],
        created_at: new Date().toISOString(),
      },
    ])
    setShowForm(false)
    setForm({ name: "", url: "", transport_type: "sse", command: "", auth_token: "", polling_interval_minutes: 60 })
  }

  return (
    <div className="container mx-auto p-8">
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-bold">MCP Server Bridge</h1>
          <p className="text-muted-foreground mt-2">
            Connect any MCP-compatible server to ingest tools and resources
          </p>
        </div>
        <Button onClick={() => setShowForm(true)}>Add MCP Server</Button>
      </div>

      {showForm && (
        <Card className="mb-8">
          <CardHeader>
            <CardTitle>New MCP Server</CardTitle>
            <CardDescription>Configure an MCP server connection</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div>
                <label className="text-sm font-medium">Server Name</label>
                <Input
                  placeholder="My MCP Server"
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                />
              </div>
              <div>
                <label className="text-sm font-medium">Transport Type</label>
                <select
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                  value={form.transport_type}
                  onChange={(e) => setForm({ ...form, transport_type: e.target.value })}
                >
                  <option value="sse">SSE (HTTP Server-Sent Events)</option>
                  <option value="stdio">Stdio (Subprocess)</option>
                </select>
              </div>
              {form.transport_type === "sse" ? (
                <div>
                  <label className="text-sm font-medium">Server URL</label>
                  <Input
                    placeholder="https://mcp-server.example.com"
                    value={form.url}
                    onChange={(e) => setForm({ ...form, url: e.target.value })}
                  />
                </div>
              ) : (
                <div>
                  <label className="text-sm font-medium">Command</label>
                  <Input
                    placeholder="/usr/local/bin/mcp-server"
                    value={form.command}
                    onChange={(e) => setForm({ ...form, command: e.target.value })}
                  />
                </div>
              )}
              <div>
                <label className="text-sm font-medium">Auth Token (optional)</label>
                <Input
                  type="password"
                  placeholder="Bearer token or API key"
                  value={form.auth_token}
                  onChange={(e) => setForm({ ...form, auth_token: e.target.value })}
                />
              </div>
              <div>
                <label className="text-sm font-medium">Polling Interval (minutes)</label>
                <Input
                  type="number"
                  value={form.polling_interval_minutes}
                  onChange={(e) => setForm({ ...form, polling_interval_minutes: parseInt(e.target.value) || 60 })}
                />
              </div>
              <div className="flex gap-2">
                <Button onClick={addServer}>Save Server</Button>
                <Button variant="outline" onClick={() => setShowForm(false)}>Cancel</Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-1 gap-6">
        {servers.length === 0 && !showForm && (
          <Card className="border-dashed">
            <CardHeader>
              <CardTitle>No MCP Servers</CardTitle>
              <CardDescription>
                Add an MCP server to start ingesting data. Supports any server implementing the Model Context Protocol.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">
                MCP servers can expose tools, resources, and real-time data from any system.
                Once connected, artifacts are normalized and routed to the agent pipeline.
              </p>
            </CardContent>
          </Card>
        )}
        {servers.map((server) => (
          <Card key={server.id}>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="flex items-center gap-2">
                  {server.name}
                  <Badge variant={server.status === "connected" ? "default" : "secondary"}>
                    {server.status}
                  </Badge>
                </CardTitle>
              </div>
              <CardDescription>
                {server.transport_type === "sse" ? server.url : server.command}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="text-sm space-y-2">
                <div>Transport: <Badge variant="outline">{server.transport_type}</Badge></div>
                <div>Polling: every {server.polling_interval_minutes} minutes</div>
                {server.discovered_tools?.length > 0 && (
                  <div>Discovered: {server.discovered_tools.length} tools</div>
                )}
              </div>
              <div className="flex gap-2 mt-4">
                <Button size="sm">Connect</Button>
                <Button size="sm" variant="outline">Discover Tools</Button>
                <Button size="sm" variant="outline">Sync Now</Button>
                <Button size="sm" variant="ghost" className="text-destructive">Remove</Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}
