import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"

export default function IntegrationsPage() {
  return (
    <div className="container mx-auto p-8">
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-3xl font-bold">Integrations</h1>
        <Button>Add Integration</Button>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <span className="text-2xl">💬</span> Slack
            </CardTitle>
            <CardDescription>Status: Connected</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2 text-sm">
              <div className="text-muted-foreground">
                Last sync: 5 minutes ago
              </div>
              <div className="text-muted-foreground">
                Channels: 12
              </div>
            </div>
            <div className="mt-4 space-x-2">
              <Button variant="outline" size="sm">Configure</Button>
              <Button variant="outline" size="sm">Disconnect</Button>
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <span className="text-2xl">📧</span> Gmail
            </CardTitle>
            <CardDescription>Status: Connected</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2 text-sm">
              <div className="text-muted-foreground">
                Last sync: 10 minutes ago
              </div>
              <div className="text-muted-foreground">
                Accounts: 8
              </div>
            </div>
            <div className="mt-4 space-x-2">
              <Button variant="outline" size="sm">Configure</Button>
              <Button variant="outline" size="sm">Disconnect</Button>
            </div>
          </CardContent>
        </Card>
        
        <Card className="border-dashed">
          <CardHeader>
            <CardTitle>Add Integration</CardTitle>
            <CardDescription>Connect a new tool</CardDescription>
          </CardHeader>
          <CardContent>
            <Button className="w-full">Browse Integrations</Button>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}