"use client"

import { Breadcrumbs } from "@/components/ui/breadcrumbs"
import { ConfigFileEditor } from "@/components/dashboard/ConfigFileEditor"

export default function ConfigEditorPage() {
  return (
    <div className="container mx-auto py-8 space-y-8">
      <Breadcrumbs
        items={[
          { label: "Paramètres", href: "/settings" },
          { label: "Éditeur Config" }
        ]}
      />

      <div>
        <h1 className="text-3xl font-bold tracking-tight">Éditeur de Configuration</h1>
        <p className="text-muted-foreground mt-2">
          Modifiez directement le fichier config.yaml avec validation en temps réel.
        </p>
      </div>

      <ConfigFileEditor />

      {/* Warning Banner */}
      <div className="p-4 rounded-lg bg-amber-500/10 border border-amber-500/30">
        <h3 className="text-sm font-semibold text-amber-500 mb-2">⚠️ Attention</h3>
        <ul className="text-xs text-amber-200/80 space-y-1 list-disc list-inside">
          <li>Les modifications prennent effet immédiatement</li>
          <li>Une configuration invalide peut empêcher les bots de fonctionner</li>
          <li>Téléchargez une sauvegarde avant de faire des modifications importantes</li>
          <li>Consultez la documentation si vous n&apos;êtes pas sûr d&apos;une valeur</li>
        </ul>
      </div>
    </div>
  )
}
