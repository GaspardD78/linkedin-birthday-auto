export default function LogsPage() {
  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold text-white">Logs & Console</h1>
      </div>
      <div className="p-6 rounded-xl bg-slate-900 border border-slate-800 font-mono text-sm text-slate-400 h-[600px] overflow-y-auto">
        <div className="border-b border-slate-800 pb-2 mb-2">System Logs</div>
        <div>Waiting for logs stream...</div>
      </div>
    </div>
  )
}
