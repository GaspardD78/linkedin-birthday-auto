import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { ConfigData } from "./types"
import { Separator } from "@/components/ui/separator"
import { Trash2 } from "lucide-react"

interface InvitationSettingsProps {
    config: ConfigData
    updateConfig: (path: string[], value: any) => void
}

export function InvitationSettings({ config, updateConfig }: InvitationSettingsProps) {
    const imConfig = config.invitation_manager || {
        enabled: false,
        threshold_months: 3,
        max_withdrawals_per_run: 30
    }

    return (
        <Card className="border-slate-800 bg-slate-900/50">
            <CardHeader>
                <CardTitle className="flex items-center gap-2">
                    <Trash2 className="h-5 w-5 text-red-400" />
                    Nettoyage des Invitations (Auto-Withdraw)
                </CardTitle>
                <CardDescription>
                    Retire automatiquement les demandes de connexion anciennes restées sans réponse.
                </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
                <div className="flex items-center justify-between p-4 bg-slate-950/50 rounded-lg border border-slate-800">
                    <div className="space-y-1">
                        <Label htmlFor="im-enabled" className="text-base">Activer le nettoyage automatique</Label>
                        <p className="text-sm text-muted-foreground">
                            Le bot vérifiera les invitations en attente et retirera celles qui dépassent le seuil.
                        </p>
                    </div>
                    <Switch
                        id="im-enabled"
                        checked={imConfig.enabled}
                        onCheckedChange={(c) => updateConfig(['invitation_manager', 'enabled'], c)}
                    />
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="space-y-2">
                        <Label htmlFor="im-threshold">Seuil d&apos;ancienneté (mois)</Label>
                        <Input
                            id="im-threshold"
                            type="number"
                            min={1}
                            max={24}
                            value={imConfig.threshold_months}
                            onChange={(e) => updateConfig(['invitation_manager', 'threshold_months'], parseInt(e.target.value) || 1)}
                            className="bg-slate-950 border-slate-800"
                        />
                        <p className="text-xs text-muted-foreground">
                            Toute invitation envoyée il y a plus de <strong>{imConfig.threshold_months} mois</strong> sera retirée.
                        </p>
                    </div>

                    <div className="space-y-2">
                        <Label htmlFor="im-max">Limite par exécution</Label>
                        <Input
                            id="im-max"
                            type="number"
                            min={1}
                            max={100}
                            value={imConfig.max_withdrawals_per_run}
                            onChange={(e) => updateConfig(['invitation_manager', 'max_withdrawals_per_run'], parseInt(e.target.value) || 1)}
                            className="bg-slate-950 border-slate-800"
                        />
                        <p className="text-xs text-muted-foreground">
                            Nombre maximum de retraits par passage (pour éviter le blocage LinkedIn).
                        </p>
                    </div>
                </div>
            </CardContent>
        </Card>
    )
}
