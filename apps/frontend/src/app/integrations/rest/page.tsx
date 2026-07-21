"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"

export default function RESTConnectorsPage() {
  const [connectors, setConnectors] = useState<any[]>([])
  const [showForm, setShowForm] = useState(false)
  const [step, setStep] = useState(1)
  const [form, setForm] = useState({
    name: "",
    url: "",
    method: "GET",
    headers: "{}",
    auth_type: "none",
    auth_config: "{}",
    field_mappings: "{}",
    pagination: "{}",
    polling_interval_minutes: 60,
  })

  const addConnector = () => {
    setConnectors([
      ...connectors,
      {
        id: Date.now().toString(),
        ...form,
        status: "paused",
        created_at: new Date().toISOString(),
      },
    ])
    setShowForm(false)
    setStep(1)
    setForm({
      name: "", url: "", method: "GET", headers: "{}", auth_type: "none",
      auth_config: "{}", field_mappings: "{}", pagination: "{}",
      polling_interval_minutes: 60,
    })
  }

  return (
    <div className="container mx-auto p-8">
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-bold">REST API Connectors</h1>
          <p className="text-muted-foreground mt-2">
            Connect any REST API as a data source with JSONPath field mapping
          </p>
        </div>
        <Button onClick={() => setShowForm(true)}>Add REST Connector</Button>
      </div>

      {showForm && (
        <Card className="mb-8">
          <CardHeader>
            <CardTitle>New REST Connector</CardTitle>
            <CardDescription>
              Step {step} of 4: {step === 1 ? "Basic Info" : step === 2 ? "Authentication" : step === 3 ? "Field Mapping" : "Schedule"}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {step === 1 && (
                <>
                  <div>
                    <label className="text-sm font-medium">Connector Name</label>
                    <Input placeholder="My API" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
                  </div>
                  <div>
                    <label className="text-sm font-medium">URL</label>
                    <Input placeholder="https://api.example.com/items" value={form.url} onChange={(e) => setForm({ ...form, url: e.target.value })} />
                  </div>
                  <div>
                    <label className="text-sm font-medium">HTTP Method</label>
                    <select className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm" value={form.method} onChange={(e) => setForm({ ...form, method: e.target.value })}>
                      <option value="GET">GET</option>
                      <option value="POST">POST</option>
                      <option value="PUT">PUT</option>
                    </select>
                  </div>
                  <div>
                    <label className="text-sm font-medium">Headers (JSON)</label>
                    <Input placeholder='{"Accept": "application/json"}' value={form.headers} onChange={(e) => setForm({ ...form, headers: e.target.value })} />
                  </div>
                </>
              )}

              {step === 2 && (
                <>
                  <div>
                    <label className="text-sm font-medium">Auth Type</label>
                    <select className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm" value={form.auth_type} onChange={(e) => setForm({ ...form, auth_type: e.target.value })}>
                      <option value="none">None</option>
                      <option value="api_key">API Key (Header)</option>
                      <option value="basic">Basic Auth</option>
                      <option value="bearer">Bearer Token</option>
                      <option value="oauth2_client_credentials">OAuth2 Client Credentials</option>
                    </select>
                  </div>
                  <div>
                    <label className="text-sm font-medium">Auth Config (JSON)</label>
                    <Input placeholder='{"token": "..."} or {"username": "...", "password": "..."}' value={form.auth_config} onChange={(e) => setForm({ ...form, auth_config: e.target.value })} />
                  </div>
                </>
              )}

              {step === 3 && (
                <>
                  <div className="p-4 bg-muted rounded-lg mb-4">
                    <p className="text-sm text-muted-foreground">
                      Map JSONPath expressions to extract fields from the API response.
                      Example for response {"{ \"data\": [{ \"id\": 1, \"title\": \"Hello\", \"author\": \"Alice\" }] }"}:
                    </p>
                    <pre className="text-xs mt-2">
{`{
  "items_path": "$.data",
  "id_path": "$.id",
  "content_path": "$.title",
  "author_path": "$.author",
  "email_path": "$.email",
  "timestamp_path": "$.created_at",
  "artifact_type": "message"
}`}
                    </pre>
                  </div>
                  <div>
                    <label className="text-sm font-medium">Field Mappings (JSON)</label>
                    <Input placeholder='{"items_path": "$.data", "content_path": "$.title"}' value={form.field_mappings} onChange={(e) => setForm({ ...form, field_mappings: e.target.value })} />
                  </div>
                  <div>
                    <label className="text-sm font-medium">Pagination Config (JSON)</label>
                    <Input placeholder='{"strategy": "none"}' value={form.pagination} onChange={(e) => setForm({ ...form, pagination: e.target.value })} />
                  </div>
                </>
              )}

              {step === 4 && (
                <div>
                  <label className="text-sm font-medium">Polling Interval (minutes)</label>
                  <Input type="number" value={form.polling_interval_minutes} onChange={(e) => setForm({ ...form, polling_interval_minutes: parseInt(e.target.value) || 60 })} />
                  <p className="text-xs text-muted-foreground mt-1">How often to fetch new data from this API</p>
                </div>
              )}

              <div className="flex gap-2 justify-between">
                <div>
                  {step > 1 && <Button variant="outline" onClick={() => setStep(step - 1)}>Previous</Button>}
                </div>
                <div className="flex gap-2">
                  <Button variant="outline" onClick={() => { setShowForm(false); setStep(1); }}>Cancel</Button>
                  {step < 4 ? (
                    <Button onClick={() => setStep(step + 1)}>Next</Button>
                  ) : (
                    <Button onClick={addConnector}>Save Connector</Button>
                  )}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-1 gap-6">
        {connectors.length === 0 && !showForm && (
          <Card className="border-dashed">
            <CardHeader>
              <CardTitle>No REST Connectors</CardTitle>
              <CardDescription>
                Add a REST API connector to ingest data from any HTTP API.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">
                Configure URL, auth, and JSONPath field mappings. Data is polled on a schedule
                and normalized into artifacts for agent processing.
              </p>
            </CardContent>
          </Card>
        )}
        {connectors.map((connector) => (
          <Card key={connector.id}>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="flex items-center gap-2">
                  {connector.name}
                  <Badge variant={connector.status === "active" ? "default" : "secondary"}>
                    {connector.status}
                  </Badge>
                </CardTitle>
              </div>
              <CardDescription>{connector.method} {connector.url}</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="text-sm space-y-1">
                <div>Auth: <Badge variant="outline">{connector.auth_type}</Badge></div>
                <div>Polling: every {connector.polling_interval_minutes} minutes</div>
              </div>
              <div className="flex gap-2 mt-4">
                <Button size="sm">Test Connection</Button>
                <Button size="sm" variant="outline">Sync Now</Button>
                <Button size="sm" variant="outline">Activate</Button>
                <Button size="sm" variant="ghost" className="text-destructive">Remove</Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}
