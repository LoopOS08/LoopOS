import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"

export default function AgentsPage() {
  return (
    <div className="container mx-auto p-8">
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-3xl font-bold">Agents</h1>
        <Button>Configure Agents</Button>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Operations Agent</CardTitle>
            <CardDescription>Status: Active</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2 text-sm">
              <div className="text-muted-foreground">
                Task coordination and workflow automation
              </div>
              <div className="text-muted-foreground">
                Actions today: 24
              </div>
              <div className="text-muted-foreground">
                Success rate: 94%
              </div>
            </div>
            <div className="mt-4">
              <Button variant="outline" size="sm" className="w-full">View Activity</Button>
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader>
            <CardTitle>Customer Intelligence Agent</CardTitle>
            <CardDescription>Status: Active</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2 text-sm">
              <div className="text-muted-foreground">
                Customer behavior analysis and health scoring
              </div>
              <div className="text-muted-foreground">
                Actions today: 18
              </div>
              <div className="text-muted-foreground">
                Success rate: 91%
              </div>
            </div>
            <div className="mt-4">
              <Button variant="outline" size="sm" className="w-full">View Activity</Button>
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader>
            <CardTitle>Knowledge Agent</CardTitle>
            <CardDescription>Status: Active</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2 text-sm">
              <div className="text-muted-foreground">
                Decision extraction and knowledge management
              </div>
              <div className="text-muted-foreground">
                Actions today: 12
              </div>
              <div className="text-muted-foreground">
                Success rate: 97%
              </div>
            </div>
            <div className="mt-4">
              <Button variant="outline" size="sm" className="w-full">View Activity</Button>
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader>
            <CardTitle>Revenue Agent</CardTitle>
            <CardDescription>Status: Paused</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2 text-sm">
              <div className="text-muted-foreground">
                Sales pipeline monitoring and revenue tracking
              </div>
              <div className="text-muted-foreground">
                Actions today: 0
              </div>
              <div className="text-muted-foreground">
                Success rate: 89%
              </div>
            </div>
            <div className="mt-4">
              <Button variant="outline" size="sm" className="w-full">View Activity</Button>
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader>
            <CardTitle>Finance Agent</CardTitle>
            <CardDescription>Status: Active</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2 text-sm">
              <div className="text-muted-foreground">
                Financial metrics and anomaly detection
              </div>
              <div className="text-muted-foreground">
                Actions today: 8
              </div>
              <div className="text-muted-foreground">
                Success rate: 95%
              </div>
            </div>
            <div className="mt-4">
              <Button variant="outline" size="sm" className="w-full">View Activity</Button>
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader>
            <CardTitle>Alignment Agent</CardTitle>
            <CardDescription>Status: Active</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2 text-sm">
              <div className="text-muted-foreground">
                Engineering-business alignment monitoring
              </div>
              <div className="text-muted-foreground">
                Actions today: 6
              </div>
              <div className="text-muted-foreground">
                Success rate: 92%
              </div>
            </div>
            <div className="mt-4">
              <Button variant="outline" size="sm" className="w-full">View Activity</Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}