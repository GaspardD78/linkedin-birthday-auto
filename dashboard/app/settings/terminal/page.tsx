"use client"

import { useState, useRef, useEffect } from "react"
import { Breadcrumbs } from "@/components/ui/breadcrumbs"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { useToast } from "@/components/ui/use-toast"
import { Terminal, Play, Trash2, Copy, AlertTriangle } from "lucide-react"

interface CommandOutput {
  command: string
  output: string
  timestamp: Date
  success: boolean
}

export default function TerminalPage() {
  const [command, setCommand] = useState("")
  const [history, setHistory] = useState<CommandOutput[]>([])
  const [executing, setExecuting] = useState(false)
  const terminalRef = useRef<HTMLDivElement>(null)
  const { toast } = useToast()

  const predefinedCommands = [
    { cmd: 'status', desc: 'Voir le statut du système', category: 'Info' },
    { cmd: 'logs', desc: 'Afficher les derniers logs', category: 'Logs' },
    { cmd: 'ps', desc: 'Liste des processus actifs', category: 'Système' },
    { cmd: 'disk', desc: 'Espace disque disponible', category: 'Système' },
    { cmd: 'memory', desc: 'Utilisation de la mémoire', category: 'Système' },
    { cmd: 'restart', desc: 'Redémarrer les services', category: 'Contrôle' },
  ]

  useEffect(() => {
    // Scroll to bottom when new output is added
    if (terminalRef.current) {
      terminalRef.current.scrollTop = terminalRef.current.scrollHeight
    }
  }, [history])

  const executeCommand = async (cmd: string) => {
    if (!cmd.trim()) return

    setExecuting(true)
    try {
      const response = await fetch('/api/terminal/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ command: cmd })
      })

      const data = await response.json()

      const output: CommandOutput = {
        command: cmd,
        output: data.output || data.error || 'No output',
        timestamp: new Date(),
        success: response.ok
      }

      setHistory([...history, output])
      setCommand("")
    } catch (error: any) {
      const output: CommandOutput = {
        command: cmd,
        output: `Error: ${error.message}`,
        timestamp: new Date(),
        success: false
      }
      setHistory([...history, output])
    } finally {
      setExecuting(false)
    }
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    executeCommand(command)
  }

  const clearHistory = () => {
    setHistory([])
    toast({
      title: "Historique effacé",
      description: "Le terminal a été réinitialisé"
    })
  }

  const copyOutput = (output: string) => {
    navigator.clipboard.writeText(output)
    toast({
      title: "Copié",
      description: "La sortie a été copiée dans le presse-papier"
    })
  }

  return (
    <div className="container mx-auto py-8 space-y-8">
      <Breadcrumbs
        items={[
          { label: "Paramètres", href: "/settings" },
          { label: "Terminal" }
        ]}
      />

      <div>
        <h1 className="text-3xl font-bold tracking-tight">Terminal Web</h1>
        <p className="text-muted-foreground mt-2">
          Console d'urgence pour exécuter des commandes système.
        </p>
      </div>

      {/* Warning Banner */}
      <div className="p-4 rounded-lg bg-amber-500/10 border border-amber-500/30">
        <div className="flex items-start gap-3">
          <AlertTriangle className="h-5 w-5 text-amber-500 flex-shrink-0 mt-0.5" />
          <div>
            <h3 className="text-sm font-semibold text-amber-500 mb-2">⚠️ Utilisation Avancée</h3>
            <ul className="text-xs text-amber-200/80 space-y-1 list-disc list-inside">
              <li>Ce terminal est réservé aux cas d'urgence</li>
              <li>Seules certaines commandes prédéfinies sont autorisées pour des raisons de sécurité</li>
              <li>Toutes les commandes sont enregistrées dans les logs</li>
              <li>Privilégiez l'interface graphique pour les opérations courantes</li>
            </ul>
          </div>
        </div>
      </div>

      {/* Quick Commands */}
      <Card className="bg-slate-900 border-slate-800">
        <CardHeader>
          <CardTitle className="text-lg">Commandes Rapides</CardTitle>
          <CardDescription>Cliquez sur une commande pour l'exécuter</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-2">
            {predefinedCommands.map((item, idx) => (
              <Button
                key={idx}
                variant="outline"
                size="sm"
                onClick={() => executeCommand(item.cmd)}
                disabled={executing}
                className="flex flex-col h-auto py-3 items-start gap-1"
              >
                <span className="font-mono text-xs text-cyan-400">{item.cmd}</span>
                <span className="text-[10px] text-slate-500 font-normal">{item.category}</span>
              </Button>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Terminal */}
      <Card className="bg-slate-900 border-slate-800">
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <Terminal className="h-5 w-5 text-cyan-500" />
              Console
            </CardTitle>
            <Button
              variant="ghost"
              size="sm"
              onClick={clearHistory}
              className="gap-2 text-slate-400 hover:text-slate-200"
            >
              <Trash2 className="h-4 w-4" />
              Effacer
            </Button>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Output */}
          <div
            ref={terminalRef}
            className="bg-slate-950 rounded-lg p-4 font-mono text-xs min-h-[400px] max-h-[600px] overflow-y-auto border border-slate-800"
          >
            {history.length === 0 ? (
              <div className="text-slate-600 text-center py-8">
                <Terminal className="h-12 w-12 mx-auto mb-2 opacity-50" />
                <p>Terminal prêt. Tapez une commande ou utilisez les raccourcis ci-dessus.</p>
              </div>
            ) : (
              history.map((entry, idx) => (
                <div key={idx} className="mb-4 last:mb-0">
                  <div className="flex items-center justify-between mb-1">
                    <div className="flex items-center gap-2">
                      <span className="text-slate-500">
                        [{entry.timestamp.toLocaleTimeString()}]
                      </span>
                      <span className="text-cyan-400">$</span>
                      <span className="text-white">{entry.command}</span>
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => copyOutput(entry.output)}
                      className="h-6 px-2"
                    >
                      <Copy className="h-3 w-3" />
                    </Button>
                  </div>
                  <pre className={`whitespace-pre-wrap pl-4 ${entry.success ? 'text-slate-300' : 'text-red-400'}`}>
                    {entry.output}
                  </pre>
                </div>
              ))
            )}
          </div>

          {/* Input */}
          <form onSubmit={handleSubmit} className="flex gap-2">
            <div className="flex-1 flex items-center gap-2 bg-slate-950 rounded-lg px-4 py-2 border border-slate-700">
              <span className="text-cyan-400 font-mono text-sm">$</span>
              <Input
                type="text"
                value={command}
                onChange={(e) => setCommand(e.target.value)}
                placeholder="Tapez une commande..."
                disabled={executing}
                className="flex-1 bg-transparent border-0 focus-visible:ring-0 focus-visible:ring-offset-0 font-mono text-sm"
              />
            </div>
            <Button
              type="submit"
              disabled={executing || !command.trim()}
              className="gap-2 bg-cyan-600 hover:bg-cyan-700"
            >
              {executing ? (
                <>
                  <Play className="h-4 w-4 animate-spin" />
                  Exécution...
                </>
              ) : (
                <>
                  <Play className="h-4 w-4" />
                  Exécuter
                </>
              )}
            </Button>
          </form>

          {/* Help */}
          <div className="text-xs text-slate-500">
            <p><strong>Commandes disponibles :</strong> {predefinedCommands.map(c => c.cmd).join(', ')}</p>
            <p className="mt-1">Tapez <code className="text-cyan-400">help</code> pour plus d'informations</p>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
