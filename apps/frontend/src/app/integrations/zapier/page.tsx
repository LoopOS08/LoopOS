"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"

export default function ZapierPage() {
  const [configs, setConfigs] = useState<any[]>([])
  const [form, setForm] = useState({
    source_tool: "zapier",
    artifact_type: "message",
  })

  const createConfig = () => {
    const webhookSecret = Array.from({ length: 32 }, () => Math.random().toString(36)[2]).join("")
    const urlPath = `${Date.now()}/${form.source_tool}/${Math.random().toString(36).slice(2, 10)}`

    setConfigs([
      ...configs,
      {
        id: Date.now().toString(),
        ...form,
        webhook_secret: webhookSecret,
        webhook_url: `/api/webhooks/${form.source_tool}`,
        webhook_url_path: urlPath,
        enabled: true,
        created_at: new Date().toISOString(),
      },
    ])
  }

  return (
    <div className="container mx-auto p-8">
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-bold">Zapier / Make Bridge</h1>
          <p className="text-muted-foreground mt-2">
            Connect 5,000+ apps via Zapier and Make webhooks
          </p>
        </div>
        <Button onClick={createConfig}>Generate Webhook URL</Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
        <Card>
          <CardHeader>
            <CardTitle>Zapier</CardTitle>
            <CardDescription>Connect via Zapier Webhooks</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div>
              <label className="text-sm font-medium">Platform</label>
              <select
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                value={form.source_tool}
                onChange={(e) => setForm({ ...form, source_tool: e.target.value })}
              >
                <option value="zapier">Zapier</option>
                <option value="make">Make (Integromat)</option>
              </select>
            </div>
            <div>
              <label className="text-sm font-medium">Default Artifact Type</label>
              <select
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                value={form.artifact_type}
                onChange={(e) => setForm({ ...form, artifact_type: e.target.value })}
              >
                <option value="message">Message</option>
                <option value="email">Email</option>
                <option value="ticket">Ticket</option>
                <option value="deal">Deal</option>
                <option value="document">Document</option>
              </select>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Setup Instructions</CardTitle>
            <CardDescription>How to connect</CardDescription>
          </CardHeader>
          <CardContent className="text-sm space-y-2 text-muted-foreground">
            <p><strong>Zapier:</strong> Create a new Zap with "Webhooks by Zapier" as the trigger. Select "Catch Hook" and use the webhook URL below. POST JSON data with fields like content, author, email, and timestamp.</p>
            <p><strong>Make:</strong> Create a new scenario with a "Webhook" module. Select "Custom Webhook" and use the webhook URL. Configure the data structure to match your needs.</p>
          </CardContent>
        </Card>
      </div>

      {configs.map((config) => (
        <Card key={config.id} className="mb-4">
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center gap-2">
                {config.source_tool === "zapier" ? "Zapier" : "Make"} Webhook
                <Badge variant={config.enabled ? "default" : "secondary"}>
                  {config.enabled ? "Active" : "Disabled"}
                </Badge>
              </CardTitle>
            </div>
            <CardDescription>Artifact Type: {config.artifact_type}</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div>
                <label className="text-sm font-medium">Webhook URL</label>
                <div className="flex gap-2">
                  <Input value={`https://your-instance.com${config.webhook_url}`} readOnly />
                  <Button variant="outline" size="sm" onClick={() => navigator.clipboard.writeText(`https://your-instance.com${config.webhook_url}`)}>
                    Copy
                  </Button>
                </div>
              </div>
              <div>
                <label className="text-sm font-medium">Webhook Secret (for HMAC-SHA256 signature)</label>
                <div className="flex gap-2">
                  <Input value={config.webhook_secret} readOnly type="password" />
                  <Button variant="outline" size="sm" onClick={() => navigator.clipboard.writeText(config.webhook_secret)}>
                    Copy
                  </Button>
                </div>
              </div>
              <p className="text-xs text-muted-foreground">
                Include the webhook secret as an HMAC-SHA256 signature in the x-hook-signature header.
                The signature format is: sha256=&lt;hex-encoded-hmac&gt;
              </p>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}
