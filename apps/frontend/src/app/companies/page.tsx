import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Company } from "@loopos/types"

export default function CompaniesPage() {
  return (
    <div className="container mx-auto p-8">
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-3xl font-bold">Companies</h1>
        <Button>Create Company</Button>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Acme Corporation</CardTitle>
            <CardDescription>Created on Jan 15, 2024</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <div className="text-sm text-muted-foreground">
                <span className="font-medium">Users:</span> 12
              </div>
              <div className="text-sm text-muted-foreground">
                <span className="font-medium">Integrations:</span> 5
              </div>
              <div className="text-sm text-muted-foreground">
                <span className="font-medium">Artifacts:</span> 1,234
              </div>
            </div>
            <div className="mt-4 space-x-2">
              <Button variant="outline" size="sm">Manage</Button>
              <Button variant="outline" size="sm">Settings</Button>
            </div>
          </CardContent>
        </Card>
        
        <Card className="border-dashed">
          <CardHeader>
            <CardTitle>Add New Company</CardTitle>
            <CardDescription>Create a new organization</CardDescription>
          </CardHeader>
          <CardContent>
            <Button className="w-full">Create Company</Button>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}