import { PageNavigation } from "@/components/layout/PageNavigation"
import { LogsWidget } from "@/components/dashboard/LogsWidget"

export default function LogsPage() {
  return (
    <div className="space-y-6">
      <PageNavigation
        title="Logs & Console"
        description="Logs système en temps réel"
        showBackButton={false}
        breadcrumbs={[{ label: "Logs & Console" }]}
      />

      <div className="min-h-[700px]">
        <LogsWidget />
      </div>
    </div>
  )
}
