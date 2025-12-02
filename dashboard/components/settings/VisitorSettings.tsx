import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import { Textarea } from "@/components/ui/textarea"
import { ConfigData } from "./types"

interface VisitorSettingsProps {
  config: ConfigData
  updateConfig: (path: string[], value: any) => void
}

export function VisitorSettings({ config, updateConfig }: VisitorSettingsProps) {
  const visitor = config.visitor || {}
  const limits = visitor.limits || {}
  const delays = visitor.delays || {}

  // Helper for array inputs (keywords)
  const handleKeywordsChange = (val: string) => {
    const arr = val.split(',').map(s => s.trim()).filter(s => s.length > 0)
    updateConfig(['visitor', 'keywords'], arr)
  }

  return (
    <div className="space-y-6">
      <Card className="bg-slate-900 border-slate-800 border-l-4 border-l-blue-600">
        <CardHeader>
          <CardTitle className="text-slate-200">Activation & Recherche</CardTitle>
          <CardDescription>Critères de ciblage pour les visites</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <Label>Activer le Bot Visiteur</Label>
            <Switch
              checked={visitor.enabled ?? false}
              onCheckedChange={(val) => updateConfig(['visitor', 'enabled'], val)}
            />
          </div>

          <div className="space-y-2">
             <Label htmlFor="keywords">Mots-clés (séparés par des virgules)</Label>
             <Textarea
                id="keywords"
                placeholder="CEO, Founder, Developer, Python..."
                value={visitor.keywords?.join(', ') || ''}
                onChange={(e) => handleKeywordsChange(e.target.value)}
                className="bg-slate-950 border-slate-800 font-mono text-sm"
             />
          </div>

          <div className="space-y-2">
             <Label htmlFor="location">Localisation / GeoURN</Label>
             <Input
                id="location"
                placeholder="France, Paris, 101282230..."
                value={visitor.location || ''}
                onChange={(e) => updateConfig(['visitor', 'location'], e.target.value)}
                className="bg-slate-950 border-slate-800"
             />
          </div>
        </CardContent>
      </Card>

      <Card className="bg-slate-900 border-slate-800">
        <CardHeader>
            <CardTitle className="text-slate-200">Limites de Visite</CardTitle>
            <CardDescription>Plafonds quotidiens pour la sécurité du compte</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="space-y-2">
                    <Label>Profils par Run</Label>
                    <Input
                        type="number"
                        value={limits.profiles_per_run ?? 15}
                        onChange={(e) => updateConfig(['visitor', 'limits', 'profiles_per_run'], parseInt(e.target.value))}
                        className="bg-slate-950 border-slate-800"
                    />
                </div>
                 <div className="space-y-2">
                    <Label>Max Pages Search</Label>
                    <Input
                        type="number"
                        value={limits.max_pages_to_scrape ?? 50}
                        onChange={(e) => updateConfig(['visitor', 'limits', 'max_pages_to_scrape'], parseInt(e.target.value))}
                        className="bg-slate-950 border-slate-800"
                    />
                </div>
                 <div className="space-y-2">
                    <Label>Stop si pas de nouveau (Pages)</Label>
                    <Input
                        type="number"
                        value={limits.max_pages_without_new ?? 3}
                        onChange={(e) => updateConfig(['visitor', 'limits', 'max_pages_without_new'], parseInt(e.target.value))}
                        className="bg-slate-950 border-slate-800"
                    />
                </div>
            </div>
        </CardContent>
      </Card>

      <Card className="bg-slate-900 border-slate-800">
        <CardHeader>
            <CardTitle className="text-slate-200">Délais & Comportement</CardTitle>
            <CardDescription>Simulation humaine lors des visites</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                    <Label>Visite Min (s)</Label>
                    <Input
                        type="number"
                        value={delays.profile_visit_min ?? 15}
                        onChange={(e) => updateConfig(['visitor', 'delays', 'profile_visit_min'], parseInt(e.target.value))}
                        className="bg-slate-950 border-slate-800"
                    />
                </div>
                 <div className="space-y-2">
                    <Label>Visite Max (s)</Label>
                    <Input
                        type="number"
                        value={delays.profile_visit_max ?? 35}
                        onChange={(e) => updateConfig(['visitor', 'delays', 'profile_visit_max'], parseInt(e.target.value))}
                        className="bg-slate-950 border-slate-800"
                    />
                </div>
            </div>
        </CardContent>
      </Card>
    </div>
  )
}
