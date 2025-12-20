"use client"

import { useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Plus, Calendar } from "lucide-react"
import { ScheduledJob } from "@/types/scheduler"
import { JobList } from "./JobList"
import { JobForm } from "./JobForm"

export function SchedulerSettings() {
  const [mode, setMode] = useState<'list' | 'create' | 'edit'>('list')
  const [editingJob, setEditingJob] = useState<ScheduledJob | null>(null)
  const [refreshTrigger, setRefreshTrigger] = useState(0)

  const handleCreateJob = () => {
    setEditingJob(null)
    setMode('create')
  }

  const handleEditJob = (job: ScheduledJob) => {
    setEditingJob(job)
    setMode('edit')
  }

  const handleSuccess = () => {
    setMode('list')
    setEditingJob(null)
    // Trigger refresh of job list
    setRefreshTrigger(prev => prev + 1)
  }

  const handleCancel = () => {
    setMode('list')
    setEditingJob(null)
  }

  return (
    <div className="space-y-6">
      {mode === 'list' ? (
        <>
          {/* Header */}
          <Card className="bg-slate-900 border-slate-800">
            <CardHeader>
              <div className="flex items-start justify-between">
                <div>
                  <CardTitle className="text-slate-200 flex items-center gap-2">
                    <Calendar className="h-5 w-5 text-blue-400" />
                    Automatisation des Bots
                  </CardTitle>
                  <CardDescription className="mt-2">
                    Planifiez l&apos;exécution automatique de vos bots Birthday et Visitor.
                    Créez des jobs récurrents avec des horaires personnalisés.
                  </CardDescription>
                </div>
                <Button
                  onClick={handleCreateJob}
                  className="bg-blue-600 hover:bg-blue-700"
                >
                  <Plus className="h-4 w-4 mr-2" />
                  Nouveau Job
                </Button>
              </div>
            </CardHeader>
          </Card>

          {/* Job List */}
          <JobList
            onCreateJob={handleCreateJob}
            onEditJob={handleEditJob}
            refreshTrigger={refreshTrigger}
          />
        </>
      ) : (
        <>
          {/* Form Header */}
          <Card className="bg-slate-900 border-slate-800">
            <CardHeader>
              <CardTitle className="text-slate-200">
                {mode === 'create' ? 'Créer un Nouveau Job' : 'Modifier le Job'}
              </CardTitle>
              <CardDescription>
                {mode === 'create'
                  ? 'Configurez un nouveau job d\'automatisation pour planifier vos bots.'
                  : `Modifiez la configuration de "${editingJob?.name}".`}
              </CardDescription>
            </CardHeader>
          </Card>

          {/* Form */}
          <JobForm
            job={editingJob}
            onSuccess={handleSuccess}
            onCancel={handleCancel}
          />
        </>
      )}
    </div>
  )
}
