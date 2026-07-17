import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-24">
      <div className="z-10 max-w-5xl w-full items-center justify-center font-mono text-sm">
        <h1 className="text-4xl font-bold mb-4">LoopOS</h1>
        <p className="text-xl text-muted-foreground mb-8">
          Connective Intelligence Layer for SMB Operations
        </p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Card>
            <CardHeader>
              <CardTitle>Phase 1 Status</CardTitle>
              <CardDescription>Core Infrastructure Development</CardDescription>
            </CardHeader>
            <CardContent>
              <ul className="mt-4 space-y-2 text-sm">
                <li>✅ Monorepo Setup</li>
                <li>✅ Database Schema with pgvector</li>
                <li>✅ Row-Level Security (RLS)</li>
                <li>✅ FastAPI Backend</li>
                <li>✅ Authentication Framework</li>
                <li>✅ OAuth Integration</li>
                <li>✅ Credential Security</li>
                <li>✅ Artifact Pipeline</li>
                <li>✅ Agent Runtime</li>
                <li>✅ Permission Controls</li>
              </ul>
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>Getting Started</CardTitle>
              <CardDescription>Initialize your LoopOS instance</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="mt-4 space-y-2">
                <Button className="w-full">Create Organization</Button>
                <Button variant="outline" className="w-full">Connect Integrations</Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </main>
  )
}