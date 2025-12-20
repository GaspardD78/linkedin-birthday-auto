"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { AlertCircle, Loader2, Save } from "lucide-react"
import {
  ScheduledJob,
  BotType,
  ScheduleType,
  CreateJobRequest,
  UpdateJobRequest,
  formValuesToCreateRequest,
  jobToFormValues,
  JobFormValues
} from "@/types/scheduler"
import { createJob, updateJob } from "@/lib/scheduler-api"
import { useToast } from "@/components/ui/use-toast"

interface JobFormProps {
  job?: ScheduledJob | null
  onSuccess: () => void
  onCancel: () => void
}

export function JobForm({ job, onSuccess, onCancel }: JobFormProps) {
  const isEdit = !!job
  const { toast } = useToast()
  const [saving, setSaving] = useState(false)
  const [values, setValues] = useState<JobFormValues>(() =>
    job ? jobToFormValues(job) : {
      name: '',
      bot_type: BotType.BIRTHDAY,
      enabled: true,
      schedule_type: ScheduleType.CRON,
      cron_expression: '0 9 * * *',
      hour: 9,
      minute: 0,
      day_of_week: 0,
      dry_run: false,
      process_late: false,
      max_days_late: 7,
      max_messages_per_run: 10,
      visitor_limit: 50
    }
  )

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    // Validation
    if (!values.name.trim()) {
      toast({
        variant: "destructive",
        title: "Erreur",
        description: "Le nom du job est requis."
      })
      return
    }

    if (values.schedule_type === ScheduleType.CRON && !values.cron_expression?.trim()) {
      toast({
        variant: "destructive",
        title: "Erreur",
        description: "L&apos;expression cron est requise."
      })
      return
    }

    setSaving(true)
    try {
      if (isEdit && job) {
        const request: UpdateJobRequest = formValuesToCreateRequest(values)
        await updateJob(job.id, request)
        toast({
          title: "Job mis à jour",
          description: `"${values.name}" a été modifié avec succès.`
        })
      } else {
        const request: CreateJobRequest = formValuesToCreateRequest(values)
        await createJob(request)
        toast({
          title: "Job créé",
          description: `"${values.name}" a été créé avec succès.`
        })
      }
      onSuccess()
    } catch (err) {
      toast({
        variant: "destructive",
        title: "Erreur",
        description: err instanceof Error ? err.message : 'Failed to save job'
      })
    } finally {
      setSaving(false)
    }
  }

  const updateValue = <K extends keyof JobFormValues>(key: K, value: JobFormValues[K]) => {
    setValues(prev => ({ ...prev, [key]: value }))
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* Basic Info */}
      <Card className="bg-slate-900 border-slate-800">
        <CardHeader>
          <CardTitle className="text-slate-200">Informations Générales</CardTitle>
          <CardDescription>Identifiez votre job et choisissez le type de bot</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="name">Nom du Job *</Label>
            <Input
              id="name"
              value={values.name}
              onChange={(e) => updateValue('name', e.target.value)}
              placeholder="Ex: Anniversaires quotidiens"
              className="bg-slate-950 border-slate-800"
              required
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="bot_type">Type de Bot *</Label>
            <Select
              value={values.bot_type}
              onValueChange={(val) => updateValue('bot_type', val as BotType)}
            >
              <SelectTrigger className="bg-slate-950 border-slate-800">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={BotType.BIRTHDAY}>🎂 Birthday Bot</SelectItem>
                <SelectItem value={BotType.VISITOR}>👁️ Visitor Bot</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label>Activer le Job</Label>
              <p className="text-xs text-slate-400">Le job sera exécuté selon le planning</p>
            </div>
            <Switch
              checked={values.enabled}
              onCheckedChange={(val) => updateValue('enabled', val)}
            />
          </div>
        </CardContent>
      </Card>

      {/* Schedule */}
      <Card className="bg-slate-900 border-slate-800">
        <CardHeader>
          <CardTitle className="text-slate-200">Planification</CardTitle>
          <CardDescription>Définissez quand le job doit s&apos;exécuter</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="schedule_type">Type de Planification *</Label>
            <Select
              value={values.schedule_type}
              onValueChange={(val) => updateValue('schedule_type', val as ScheduleType)}
            >
              <SelectTrigger className="bg-slate-950 border-slate-800">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={ScheduleType.CRON}>Expression Cron (Avancé)</SelectItem>
                <SelectItem value={ScheduleType.DAILY}>Quotidien</SelectItem>
                <SelectItem value={ScheduleType.WEEKLY}>Hebdomadaire</SelectItem>
                <SelectItem value={ScheduleType.INTERVAL}>Intervalle (Heures)</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {values.schedule_type === ScheduleType.CRON && (
            <div className="space-y-2">
              <Label htmlFor="cron">Expression Cron *</Label>
              <Input
                id="cron"
                value={values.cron_expression || ''}
                onChange={(e) => updateValue('cron_expression', e.target.value)}
                placeholder="0 9 * * * (tous les jours à 9h)"
                className="bg-slate-950 border-slate-800 font-mono"
                required
              />
              <p className="text-xs text-slate-400">
                Format: minute heure jour mois jour_semaine
              </p>
            </div>
          )}

          {values.schedule_type === ScheduleType.DAILY && (
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="hour">Heure</Label>
                <Input
                  id="hour"
                  type="number"
                  min="0"
                  max="23"
                  value={values.hour}
                  onChange={(e) => updateValue('hour', parseInt(e.target.value))}
                  className="bg-slate-950 border-slate-800"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="minute">Minute</Label>
                <Input
                  id="minute"
                  type="number"
                  min="0"
                  max="59"
                  value={values.minute}
                  onChange={(e) => updateValue('minute', parseInt(e.target.value))}
                  className="bg-slate-950 border-slate-800"
                />
              </div>
            </div>
          )}

          {values.schedule_type === ScheduleType.WEEKLY && (
            <>
              <div className="space-y-2">
                <Label htmlFor="day_of_week">Jour de la Semaine</Label>
                <Select
                  value={values.day_of_week?.toString() || '0'}
                  onValueChange={(val) => updateValue('day_of_week', parseInt(val))}
                >
                  <SelectTrigger className="bg-slate-950 border-slate-800">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="0">Lundi</SelectItem>
                    <SelectItem value="1">Mardi</SelectItem>
                    <SelectItem value="2">Mercredi</SelectItem>
                    <SelectItem value="3">Jeudi</SelectItem>
                    <SelectItem value="4">Vendredi</SelectItem>
                    <SelectItem value="5">Samedi</SelectItem>
                    <SelectItem value="6">Dimanche</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="hour">Heure</Label>
                  <Input
                    id="hour"
                    type="number"
                    min="0"
                    max="23"
                    value={values.hour}
                    onChange={(e) => updateValue('hour', parseInt(e.target.value))}
                    className="bg-slate-950 border-slate-800"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="minute">Minute</Label>
                  <Input
                    id="minute"
                    type="number"
                    min="0"
                    max="59"
                    value={values.minute}
                    onChange={(e) => updateValue('minute', parseInt(e.target.value))}
                    className="bg-slate-950 border-slate-800"
                  />
                </div>
              </div>
            </>
          )}

          {values.schedule_type === ScheduleType.INTERVAL && (
            <div className="space-y-2">
              <Label htmlFor="hour">Intervalle (Heures)</Label>
              <Input
                id="hour"
                type="number"
                min="1"
                max="168"
                value={values.hour}
                onChange={(e) => updateValue('hour', parseInt(e.target.value))}
                className="bg-slate-950 border-slate-800"
              />
              <p className="text-xs text-slate-400">
                Le job sera exécuté toutes les X heures
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Bot Configuration */}
      <Card className="bg-slate-900 border-slate-800">
        <CardHeader>
          <CardTitle className="text-slate-200">Configuration du Bot</CardTitle>
          <CardDescription>
            Paramètres spécifiques au type de bot sélectionné
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {values.bot_type === BotType.BIRTHDAY ? (
            <>
              <div className="flex items-center justify-between p-3 bg-amber-950/30 border border-amber-700 rounded">
                <div className="space-y-0.5">
                  <Label>Mode Test (Dry Run)</Label>
                  <p className="text-xs text-slate-400">
                    {values.dry_run
                      ? "🧪 Mode test: aucun message ne sera envoyé"
                      : "🚀 Mode production: les messages seront envoyés"}
                  </p>
                </div>
                <Switch
                  checked={values.dry_run}
                  onCheckedChange={(val) => updateValue('dry_run', val)}
                />
              </div>

              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label>Traiter les Retards</Label>
                  <p className="text-xs text-slate-400">
                    Envoyer des messages pour les anniversaires manqués
                  </p>
                </div>
                <Switch
                  checked={values.process_late}
                  onCheckedChange={(val) => updateValue('process_late', val)}
                />
              </div>

              {values.process_late && (
                <div className="space-y-2">
                  <Label htmlFor="max_days_late">Jours de Retard Maximum</Label>
                  <Input
                    id="max_days_late"
                    type="number"
                    min="1"
                    max="365"
                    value={values.max_days_late}
                    onChange={(e) => updateValue('max_days_late', parseInt(e.target.value))}
                    className="bg-slate-950 border-slate-800"
                  />
                </div>
              )}

              <div className="space-y-2">
                <Label htmlFor="max_messages">Messages Max par Exécution</Label>
                <Input
                  id="max_messages"
                  type="number"
                  min="1"
                  max="500"
                  value={values.max_messages_per_run}
                  onChange={(e) => updateValue('max_messages_per_run', parseInt(e.target.value))}
                  className="bg-slate-950 border-slate-800"
                />
              </div>
            </>
          ) : (
            <>
              <div className="flex items-center justify-between p-3 bg-amber-950/30 border border-amber-700 rounded">
                <div className="space-y-0.5">
                  <Label>Mode Test (Dry Run)</Label>
                  <p className="text-xs text-slate-400">
                    {values.dry_run
                      ? "🧪 Mode test: aucune visite ne sera effectuée"
                      : "🚀 Mode production: les visites seront effectuées"}
                  </p>
                </div>
                <Switch
                  checked={values.dry_run}
                  onCheckedChange={(val) => updateValue('dry_run', val)}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="visitor_limit">Nombre de Visites</Label>
                <Input
                  id="visitor_limit"
                  type="number"
                  min="1"
                  max="500"
                  value={values.visitor_limit}
                  onChange={(e) => updateValue('visitor_limit', parseInt(e.target.value))}
                  className="bg-slate-950 border-slate-800"
                />
              </div>
            </>
          )}

          {!values.dry_run && (
            <div className="flex items-start gap-2 p-3 bg-orange-950/30 border border-orange-700 rounded text-xs text-orange-300">
              <AlertCircle className="h-4 w-4 flex-shrink-0 mt-0.5" />
              <span>
                Attention: Le mode production est activé. Les actions seront réelles (envoi de messages / visites de profils).
              </span>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Actions */}
      <div className="flex gap-3">
        <Button
          type="button"
          variant="outline"
          onClick={onCancel}
          disabled={saving}
          className="flex-1 border-slate-700 hover:bg-slate-800"
        >
          Annuler
        </Button>
        <Button
          type="submit"
          disabled={saving}
          className="flex-1 bg-blue-600 hover:bg-blue-700"
        >
          {saving ? (
            <>
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              Enregistrement...
            </>
          ) : (
            <>
              <Save className="h-4 w-4 mr-2" />
              {isEdit ? 'Mettre à Jour' : 'Créer le Job'}
            </>
          )}
        </Button>
      </div>
    </form>
  )
}
