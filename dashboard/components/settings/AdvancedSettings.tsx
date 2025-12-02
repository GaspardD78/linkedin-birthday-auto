import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Textarea } from "@/components/ui/textarea"

interface AdvancedSettingsProps {
  yamlContent: string
  setYamlContent: (val: string) => void
}

export function AdvancedSettings({ yamlContent, setYamlContent }: AdvancedSettingsProps) {
  return (
    <Card className="bg-slate-900 border-slate-800 h-[calc(100vh-250px)]">
        <CardHeader>
            <CardTitle className="text-slate-200">Éditeur Configuration Avancée</CardTitle>
            <CardDescription>
                Modifiez directement le fichier config.yaml.
                <span className="text-amber-400 ml-2">Attention : respectez la syntaxe YAML.</span>
            </CardDescription>
        </CardHeader>
        <CardContent className="h-full pb-16">
            <Textarea
                className="h-full font-mono text-sm bg-slate-950 border-slate-800 focus-visible:ring-emerald-500"
                value={yamlContent}
                onChange={(e) => setYamlContent(e.target.value)}
                spellCheck={false}
            />
        </CardContent>
    </Card>
  )
}
