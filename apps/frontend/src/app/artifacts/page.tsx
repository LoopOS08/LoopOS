import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"

export default function ArtifactsPage() {
  return (
    <div className="container mx-auto p-8">
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-3xl font-bold">Artifacts</h1>
        <div className="flex gap-2">
          <Input placeholder="Search artifacts..." className="w-64" />
          <Button>Search</Button>
        </div>
      </div>
      
      <div className="space-y-4">
        <Card>
          <CardHeader>
            <CardTitle>Slack Message</CardTitle>
            <CardDescription>#engineering • Sarah Chen • 2 hours ago</CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-sm mb-4">
              We should prioritize the auth bug over the new dashboard feature. 
              The authentication issue is affecting 15% of our users.
            </p>
            <div className="flex gap-2">
              <Button variant="outline" size="sm">View Context</Button>
              <Button variant="outline" size="sm">Related Artifacts</Button>
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader>
            <CardTitle>Email Thread</CardTitle>
            <CardDescription>Gmail • John Smith • 1 day ago</CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-sm mb-4">
              Re: Q4 Pricing Strategy - I agree with the proposed changes. 
              Let's schedule a call to discuss implementation timeline.
            </p>
            <div className="flex gap-2">
              <Button variant="outline" size="sm">View Context</Button>
              <Button variant="outline" size="sm">Related Artifacts</Button>
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader>
            <CardTitle>GitHub Commit</CardTitle>
            <CardDescription>GitHub • Alex Johnson • 3 hours ago</CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-sm mb-4">
              fix: Resolve authentication token expiration issue (#1234)
            </p>
            <div className="flex gap-2">
              <Button variant="outline" size="sm">View Context</Button>
              <Button variant="outline" size="sm">Related Artifacts</Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}