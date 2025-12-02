import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { ConfigData } from "./types"

interface GlobalSettingsProps {
  config: ConfigData
  updateConfig: (path: string[], value: any) => void
}

export function GlobalSettings({ config, updateConfig }: GlobalSettingsProps) {
  // Helpers to safely access nested properties even if they are undefined in partial state
  const browser = config.browser || {}
  const scheduling = config.scheduling || {}
  const debug = config.debug || {}
  const monitoring = config.monitoring || {}
  const proxy = config.proxy || {}

  return (
    <div className="space-y-6">
      {/* General Settings */}
      <Card className="bg-slate-900 border-slate-800">
        <CardHeader>
          <CardTitle className="text-slate-200">Général & Navigateur</CardTitle>
          <CardDescription>Paramètres globaux du bot et du navigateur</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label>Mode Test (Dry Run)</Label>
              <p className="text-xs text-slate-400">Simule les actions sans envoyer de messages ni visiter réellement</p>
            </div>
            <Switch
              checked={config.dry_run}
              onCheckedChange={(val) => updateConfig(['dry_run'], val)}
            />
          </div>

          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label>Mode Headless</Label>
              <p className="text-xs text-slate-400">Masquer le navigateur (recommandé pour Docker/Pi)</p>
            </div>
            <Switch
              checked={browser.headless ?? true}
              onCheckedChange={(val) => updateConfig(['browser', 'headless'], val)}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="browser_locale">Langue du navigateur</Label>
            <Input
              id="browser_locale"
              value={browser.locale || 'fr-FR'}
              onChange={(e) => updateConfig(['browser', 'locale'], e.target.value)}
              className="bg-slate-950 border-slate-800"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="timezone">Fuseau horaire (Navigateur & Planification)</Label>
            <Input
              id="timezone"
              value={browser.timezone || scheduling.timezone || 'Europe/Paris'}
              onChange={(e) => {
                  updateConfig(['browser', 'timezone'], e.target.value)
                  updateConfig(['scheduling', 'timezone'], e.target.value)
              }}
              className="bg-slate-950 border-slate-800"
            />
          </div>
        </CardContent>
      </Card>

      {/* Scheduling (Global) */}
      <Card className="bg-slate-900 border-slate-800">
        <CardHeader>
          <CardTitle className="text-slate-200">Plage Horaire d&apos;Activité</CardTitle>
          <CardDescription>Heures pendant lesquelles le bot est autorisé à tourner</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="start_hour">Heure de début</Label>
              <Input
                id="start_hour"
                type="number"
                min="0"
                max="23"
                value={scheduling.daily_start_hour ?? 8}
                onChange={(e) => updateConfig(['scheduling', 'daily_start_hour'], parseInt(e.target.value))}
                className="bg-slate-950 border-slate-800"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="end_hour">Heure de fin</Label>
              <Input
                id="end_hour"
                type="number"
                min="0"
                max="23"
                value={scheduling.daily_end_hour ?? 19}
                onChange={(e) => updateConfig(['scheduling', 'daily_end_hour'], parseInt(e.target.value))}
                className="bg-slate-950 border-slate-800"
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Monitoring & Proxy */}
      <Card className="bg-slate-900 border-slate-800">
        <CardHeader>
          <CardTitle className="text-slate-200">Monitoring & Réseau</CardTitle>
          <CardDescription>Configuration avancée réseau et surveillance</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label>Activer Monitoring (Prometheus)</Label>
              <p className="text-xs text-slate-400">Expose les métriques sur le port {monitoring.prometheus_port || 9090}</p>
            </div>
            <Switch
              checked={monitoring.enabled ?? false}
              onCheckedChange={(val) => {
                  updateConfig(['monitoring', 'enabled'], val)
                  updateConfig(['monitoring', 'prometheus_enabled'], val)
              }}
            />
          </div>

          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label>Activer Proxy</Label>
              <p className="text-xs text-slate-400">Utiliser la configuration proxy_config.json</p>
            </div>
            <Switch
              checked={proxy.enabled ?? false}
              onCheckedChange={(val) => updateConfig(['proxy', 'enabled'], val)}
            />
          </div>
        </CardContent>
      </Card>

      {/* Debug */}
      <Card className="bg-slate-900 border-slate-800">
        <CardHeader>
          <CardTitle className="text-slate-200">Débogage</CardTitle>
          <CardDescription>Configuration des logs et captures</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
                <Label htmlFor="log_level">Niveau de Log</Label>
                <Select
                    value={debug.log_level || 'INFO'}
                    onValueChange={(val) => updateConfig(['debug', 'log_level'], val)}
                >
                    <SelectTrigger className="bg-slate-950 border-slate-800">
                        <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                        <SelectItem value="DEBUG">DEBUG</SelectItem>
                        <SelectItem value="INFO">INFO</SelectItem>
                        <SelectItem value="WARNING">WARNING</SelectItem>
                        <SelectItem value="ERROR">ERROR</SelectItem>
                    </SelectContent>
                </Select>
            </div>
          </div>
          <div className="flex items-center justify-between mt-4">
            <div className="space-y-0.5">
              <Label>Sauvegarder Screenshots (Erreur)</Label>
            </div>
            <Switch
              checked={debug.save_screenshots ?? true}
              onCheckedChange={(val) => updateConfig(['debug', 'save_screenshots'], val)}
            />
          </div>
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label>Sauvegarder HTML</Label>
            </div>
            <Switch
              checked={debug.save_html ?? false}
              onCheckedChange={(val) => updateConfig(['debug', 'save_html'], val)}
            />
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
