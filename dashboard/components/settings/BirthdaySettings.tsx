import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { AlertCircle } from "lucide-react"
import { ConfigData } from "./types"

interface BirthdaySettingsProps {
  config: ConfigData
  updateConfig: (path: string[], value: any) => void
}

export function BirthdaySettings({ config, updateConfig }: BirthdaySettingsProps) {
  const limits = config.messaging_limits || {}
  const delays = config.delays || {}
  const filter = config.birthday_filter || {}
  const messages = config.messages || {}

  return (
    <div className="space-y-6">
      <Card className="bg-slate-900 border-slate-800">
        <CardHeader>
          <CardTitle className="text-slate-200">Activation & Mode</CardTitle>
          <CardDescription>Configuration principale du bot d&apos;anniversaire</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
           <div className="space-y-2">
            <Label htmlFor="bot_mode">Stratégie d&apos;envoi</Label>
            <Select
              value={config.bot_mode}
              onValueChange={(val) => updateConfig(['bot_mode'], val)}
            >
              <SelectTrigger className="bg-slate-950 border-slate-800">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="standard">Standard (Strictement limité)</SelectItem>
                <SelectItem value="unlimited">Illimité (Mode rattrapage massif)</SelectItem>
              </SelectContent>
            </Select>
            <p className="text-xs text-slate-400">
                Le mode Standard respecte strictement les limites quotidiennes. Le mode Illimité tente d&apos;envoyer le maximum de messages.
            </p>
          </div>
        </CardContent>
      </Card>

      <Card className="bg-slate-900 border-slate-800">
        <CardHeader>
          <CardTitle className="text-slate-200">Limites & Sécurité</CardTitle>
          <CardDescription>Quotas pour éviter les blocages LinkedIn</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="space-y-2">
              <Label htmlFor="daily_limit">Max par jour</Label>
              <Input
                id="daily_limit"
                type="number"
                value={limits.daily_message_limit ?? 50}
                onChange={(e) => updateConfig(['messaging_limits', 'daily_message_limit'], parseInt(e.target.value))}
                className="bg-slate-950 border-slate-800"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="weekly_limit">Max par semaine</Label>
              <Input
                id="weekly_limit"
                type="number"
                value={limits.weekly_message_limit ?? 100}
                onChange={(e) => updateConfig(['messaging_limits', 'weekly_message_limit'], parseInt(e.target.value))}
                className="bg-slate-950 border-slate-800"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="run_limit">Max par exécution</Label>
              <Input
                id="run_limit"
                type="number"
                value={limits.max_messages_per_run ?? 10}
                onChange={(e) => updateConfig(['messaging_limits', 'max_messages_per_run'], parseInt(e.target.value))}
                className="bg-slate-950 border-slate-800"
              />
            </div>
          </div>
          {(limits.weekly_message_limit > 100) && (
             <div className="flex items-start gap-2 p-2 bg-amber-950/50 border border-amber-700 rounded text-xs text-amber-300">
                <AlertCircle className="h-4 w-4 flex-shrink-0 mt-0.5" />
                <span>Attention : > 100 messages/semaine augmente le risque de détection.</span>
             </div>
          )}
        </CardContent>
      </Card>

      <Card className="bg-slate-900 border-slate-800">
        <CardHeader>
          <CardTitle className="text-slate-200">Fichiers de Messages</CardTitle>
          <CardDescription>Chemins vers les templates de messages</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
            <div className="space-y-2">
                <Label htmlFor="msg_file">Fichier Anniversaire (Jour J)</Label>
                <Input
                    id="msg_file"
                    value={messages.messages_file || '/app/data/messages.txt'}
                    onChange={(e) => updateConfig(['messages', 'messages_file'], e.target.value)}
                    className="bg-slate-950 border-slate-800"
                />
            </div>
            <div className="space-y-2">
                <Label htmlFor="late_msg_file">Fichier Retard</Label>
                <Input
                    id="late_msg_file"
                    value={messages.late_messages_file || '/app/data/late_messages.txt'}
                    onChange={(e) => updateConfig(['messages', 'late_messages_file'], e.target.value)}
                    className="bg-slate-950 border-slate-800"
                />
            </div>
             <div className="space-y-2">
                <Label htmlFor="avoid_years">Éviter répétition (Années)</Label>
                <Input
                    id="avoid_years"
                    type="number"
                    value={messages.avoid_repetition_years ?? 2}
                    onChange={(e) => updateConfig(['messages', 'avoid_repetition_years'], parseInt(e.target.value))}
                    className="bg-slate-950 border-slate-800 w-32"
                />
                <p className="text-xs text-slate-400">Ne pas renvoyer de message à la même personne si contactée dans les X dernières années.</p>
            </div>
        </CardContent>
      </Card>

      <Card className="bg-slate-900 border-slate-800">
        <CardHeader>
          <CardTitle className="text-slate-200">Filtres de Dates</CardTitle>
          <CardDescription>Configuration de la fenêtre de tir</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
           <div className="flex items-center justify-between">
                <Label>Traiter Aujourd&apos;hui</Label>
                <Switch
                    checked={filter.process_today ?? true}
                    onCheckedChange={(val) => updateConfig(['birthday_filter', 'process_today'], val)}
                />
           </div>
           <div className="flex items-center justify-between">
                <Label>Traiter Retards</Label>
                <Switch
                    checked={filter.process_late ?? true}
                    onCheckedChange={(val) => updateConfig(['birthday_filter', 'process_late'], val)}
                />
           </div>
           {filter.process_late && (
               <div className="space-y-2 pt-2">
                    <Label htmlFor="max_days">Jours de retard maximum acceptés</Label>
                    <Input
                        id="max_days"
                        type="number"
                        value={filter.max_days_late ?? 7}
                        onChange={(e) => updateConfig(['birthday_filter', 'max_days_late'], parseInt(e.target.value))}
                        className="bg-slate-950 border-slate-800 w-32"
                    />
               </div>
           )}
        </CardContent>
      </Card>

      <Card className="bg-slate-900 border-slate-800">
        <CardHeader>
          <CardTitle className="text-slate-200">Délais d&apos;Envoi</CardTitle>
          <CardDescription>Temporisation entre chaque message (secondes)</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
             <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                    <Label>Min Delay</Label>
                    <Input
                        type="number"
                        value={delays.min_delay_seconds ?? 60}
                        onChange={(e) => updateConfig(['delays', 'min_delay_seconds'], parseInt(e.target.value))}
                        className="bg-slate-950 border-slate-800"
                    />
                </div>
                <div className="space-y-2">
                    <Label>Max Delay</Label>
                    <Input
                        type="number"
                        value={delays.max_delay_seconds ?? 180}
                        onChange={(e) => updateConfig(['delays', 'max_delay_seconds'], parseInt(e.target.value))}
                        className="bg-slate-950 border-slate-800"
                    />
                </div>
             </div>
        </CardContent>
      </Card>
    </div>
  )
}
