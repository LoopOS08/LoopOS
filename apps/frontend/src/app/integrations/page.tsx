"use client"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import Link from "next/link"

const INTEGRATIONS = [
  {
    id: "slack",
    name: "Slack",
    icon: "💬",
    description: "Messages, channels, reactions, and file uploads",
    status: "available",
    features: ["Events API", "Web API polling", "Thread support", "Reaction tracking"]
  },
  {
    id: "gmail",
    name: "Gmail",
    icon: "📧",
    description: "Emails, threads, calendar events, and meet recordings",
    status: "available",
    features: ["Push notifications", "History API", "Privacy controls", "Thread conversations"]
  },
  {
    id: "github",
    name: "GitHub",
    icon: "🐙",
    description: "Commits, pull requests, issues, and workflow runs",
    status: "available",
    features: ["Webhooks", "REST API", "PR tracking", "CI/CD monitoring"]
  },
  {
    id: "linear",
    name: "Linear",
    icon: "📋",
    description: "Issues, projects, cycles, and sprint metrics",
    status: "available",
    features: ["GraphQL API", "Webhooks", "Sprint tracking", "Cycle management"]
  },
  {
    id: "hubspot",
    name: "HubSpot",
    icon: "🚀",
    description: "Deals, contacts, companies, and CRM data",
    status: "available",
    features: ["CRM webhooks", "Search API", "Pipeline tracking", "Deal monitoring"]
  },
  {
    id: "notion",
    name: "Notion",
    icon: "📝",
    description: "Pages, databases, documents, and meeting notes",
    status: "available",
    features: ["API polling", "Document chunking", "Database sync", "Rich text support"]
  }
]

export default function IntegrationsPage() {
  return (
    <div className="container mx-auto p-8">
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-bold">Integrations</h1>
          <p className="text-muted-foreground mt-2">
            Connect your tools to enable cross-platform intelligence
          </p>
        </div>
        <Button>Add Integration</Button>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {INTEGRATIONS.map((integration) => (
          <Card key={integration.id} className="hover:shadow-lg transition-shadow">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <span className="text-2xl">{integration.icon}</span>
                {integration.name}
                <Badge variant="outline" className="ml-auto">
                  {integration.status}
                </Badge>
              </CardTitle>
              <CardDescription>{integration.description}</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                <div className="text-sm">
                  <div className="font-medium mb-2">Features:</div>
                  <div className="flex flex-wrap gap-1">
                    {integration.features.map((feature) => (
                      <Badge key={feature} variant="secondary" className="text-xs">
                        {feature}
                      </Badge>
                    ))}
                  </div>
                </div>
                <div className="flex gap-2 pt-2">
                  <Button variant="outline" size="sm" className="flex-1">
                    Connect
                  </Button>
                  <Button variant="ghost" size="sm">
                    Learn More
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
        
        <Link href="/integrations/mcp">
          <Card className="hover:shadow-lg transition-shadow cursor-pointer border-primary/20">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <span className="text-2xl">🔌</span>
                MCP Server Bridge
                <Badge className="ml-auto">Phase 4</Badge>
              </CardTitle>
              <CardDescription>Connect any MCP-compatible server</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="text-sm space-y-2">
                <div className="flex flex-wrap gap-1">
                  <Badge variant="secondary" className="text-xs">Model Context Protocol</Badge>
                  <Badge variant="secondary" className="text-xs">SSE Transport</Badge>
                  <Badge variant="secondary" className="text-xs">Stdio Transport</Badge>
                  <Badge variant="secondary" className="text-xs">Tool Discovery</Badge>
                </div>
              </div>
            </CardContent>
          </Card>
        </Link>

        <Link href="/integrations/rest">
          <Card className="hover:shadow-lg transition-shadow cursor-pointer border-primary/20">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <span className="text-2xl">🌐</span>
                REST API Connector
                <Badge className="ml-auto">Phase 4</Badge>
              </CardTitle>
              <CardDescription>Generic REST API data source</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="text-sm space-y-2">
                <div className="flex flex-wrap gap-1">
                  <Badge variant="secondary" className="text-xs">JSONPath Mapping</Badge>
                  <Badge variant="secondary" className="text-xs">OAuth2 Support</Badge>
                  <Badge variant="secondary" className="text-xs">Pagination</Badge>
                  <Badge variant="secondary" className="text-xs">Scheduled Polling</Badge>
                </div>
              </div>
            </CardContent>
          </Card>
        </Link>

        <Link href="/integrations/zapier">
          <Card className="hover:shadow-lg transition-shadow cursor-pointer border-primary/20">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <span className="text-2xl">⚡</span>
                Zapier / Make Bridge
                <Badge className="ml-auto">Phase 4</Badge>
              </CardTitle>
              <CardDescription>5,000+ apps via webhooks</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="text-sm space-y-2">
                <div className="flex flex-wrap gap-1">
                  <Badge variant="secondary" className="text-xs">Zapier</Badge>
                  <Badge variant="secondary" className="text-xs">Make (Integromat)</Badge>
                  <Badge variant="secondary" className="text-xs">HMAC Auth</Badge>
                  <Badge variant="secondary" className="text-xs">Source Detection</Badge>
                </div>
              </div>
            </CardContent>
          </Card>
        </Link>

        <Card className="border-dashed">
          <CardHeader>
            <CardTitle>Coming Soon</CardTitle>
            <CardDescription>More integrations in Phase 3</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2 text-sm text-muted-foreground">
              <div>🗓️ Google Calendar</div>
              <div>☁️ Google Drive</div>
              <div>🎥 Zoom</div>
              <div>📊 Salesforce</div>
              <div>📈 Jira</div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}