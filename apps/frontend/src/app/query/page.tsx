"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"

export default function QueryPage() {
  const [query, setQuery] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [results, setResults] = useState<any>(null)

  const handleQuery = async () => {
    if (!query.trim()) return
    
    setIsLoading(true)
    // In production, this would call the API
    setTimeout(() => {
      setResults({
        answer: "Based on your connected tools, here's what I found...",
        sources: [
          {
            tool: "Slack",
            type: "message",
            author: "Sarah Chen",
            date: "2024-01-15 10:30",
            preview: "We should prioritize the auth bug over the new dashboard feature...",
            similarity: 0.89
          },
          {
            tool: "Linear",
            type: "ticket",
            author: "John Smith",
            date: "2024-01-14 15:45",
            preview: "Fix authentication bug in login flow...",
            similarity: 0.85
          }
        ],
        confidence: 0.87,
        caveats: ["Results limited to: Slack, Linear", "Most recent result is 5 days old"]
      })
      setIsLoading(false)
    }, 1000)
  }

  const suggestions = [
    "What did we decide about pricing last week?",
    "Which customers are at risk this month?",
    "What are the top priorities for engineering?",
    "Show me recent decisions about product roadmap",
    "What's the status of the current sprint?"
  ]

  return (
    <div className="container mx-auto p-8 max-w-4xl">
      <div className="mb-8">
        <h1 className="text-3xl font-bold">Unified Query</h1>
        <p className="text-muted-foreground mt-2">
          Ask questions across all your connected tools
        </p>
      </div>

      <Card className="mb-6">
        <CardContent className="pt-6">
          <div className="flex gap-2">
            <Input
              placeholder="Ask anything... (e.g., 'What did we decide about pricing?')"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleQuery()}
              className="flex-1"
            />
            <Button onClick={handleQuery} disabled={isLoading}>
              {isLoading ? "Searching..." : "Query"}
            </Button>
          </div>
          
          <div className="mt-4">
            <div className="text-sm font-medium mb-2">Suggestions:</div>
            <div className="flex flex-wrap gap-2">
              {suggestions.map((suggestion) => (
                <Badge
                  key={suggestion}
                  variant="outline"
                  className="cursor-pointer hover:bg-secondary"
                  onClick={() => setQuery(suggestion)}
                >
                  {suggestion}
                </Badge>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>

      {results && (
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Answer</CardTitle>
              <CardDescription>
                Confidence: {Math.round(results.confidence * 100)}%
              </CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-sm">{results.answer}</p>
              
              {results.caveats.length > 0 && (
                <div className="mt-4 p-3 bg-muted rounded-md">
                  <div className="text-sm font-medium mb-2">Notes:</div>
                  <ul className="text-sm text-muted-foreground space-y-1">
                    {results.caveats.map((caveat: string, index: number) => (
                      <li key={index}>• {caveat}</li>
                    ))}
                  </ul>
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Sources</CardTitle>
              <CardDescription>
                {results.sources.length} relevant artifacts found
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {results.sources.map((source: any, index: number) => (
                  <div key={index} className="p-4 border rounded-md">
                    <div className="flex items-center gap-2 mb-2">
                      <Badge variant="secondary">{source.tool}</Badge>
                      <Badge variant="outline">{source.type}</Badge>
                      <span className="text-sm text-muted-foreground ml-auto">
                        {Math.round(source.similarity * 100)}% match
                      </span>
                    </div>
                    <div className="text-sm mb-2">
                      <span className="font-medium">{source.author}</span>
                      <span className="text-muted-foreground"> • {source.date}</span>
                    </div>
                    <p className="text-sm text-muted-foreground">{source.preview}</p>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  )
}
